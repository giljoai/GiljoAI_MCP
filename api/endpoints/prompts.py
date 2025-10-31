"""
Prompt Generation API endpoints for Handover 0073: Static Agent Grid.

Provides REST API for generating executable prompts:
- GET /api/prompts/orchestrator/{tool} - Generate orchestrator prompt
- GET /api/prompts/agent/{agent_id} - Generate agent prompt
- POST /api/prompts/estimate-tokens - Estimate token usage for mission (Handover 0065)
- GET /api/prompts/staging/{project_id} - Generate comprehensive orchestrator staging prompt (Handover 0079)

All endpoints enforce multi-tenant isolation and authentication.
"""

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.prompt import (
    AgentPromptResponse,
    OrchestratorPromptResponse,
    TokenEstimateRequest,
)
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import MCPAgentJob, Project, User
from src.giljo_mcp.prompt_generator import OrchestratorPromptGenerator

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/orchestrator/{tool}", response_model=OrchestratorPromptResponse)
async def generate_orchestrator_prompt(
    tool: Literal["claude-code", "codex-gemini"],
    project_id: str = Query(..., description="Project ID"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate orchestrator prompt for specified AI tool.

    Generates executable bash commands that invoke the orchestrator with
    project context and agent coordination. Supports Claude Code and Codex/Gemini.

    Args:
        tool: AI tool type (claude-code or codex-gemini)
        project_id: Project ID to orchestrate
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        OrchestratorPromptResponse with prompt, instructions, and metadata

    Raises:
        404: Project not found or not accessible
        403: User not authorized to access project
    """
    # Get project with tenant isolation
    stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found or not accessible"
        )

    # Count agents in project
    agent_count_stmt = select(func.count(MCPAgentJob.id)).where(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    agent_count_result = await db.execute(agent_count_stmt)
    agent_count = agent_count_result.scalar() or 0

    # Determine project path (default to current directory if not set)
    project_path = project.meta_data.get("path", ".") if project.meta_data else "."

    # Generate prompt based on tool type
    if tool == "claude-code":
        prompt = f"""cd {project_path}
claude-code orchestrate \\
  --project-id={project.id} \\
  --mission="{project.mission}" \\
  --agents={agent_count}"""

        instructions = """Copy the command above and paste it into your terminal.
Claude Code will orchestrate the project with AI agent coordination.

Prerequisites:
- Claude Code must be installed and configured
- You must be in the project directory or use the cd command above
- Project mission will guide agent collaboration"""

    else:  # codex-gemini
        prompt = f"""cd {project_path}
export PROJECT_ID={project.id}
export MISSION="{project.mission}"
export AGENTS={agent_count}

# For Codex:
# codex orchestrate

# For Gemini:
# gemini orchestrate"""

        instructions = """Copy the export commands and orchestrator invocation to your terminal.
Choose either Codex or Gemini based on your installed tools.

Prerequisites:
- Codex or Gemini CLI must be installed
- Environment variables will be available to the orchestrator
- Uncomment the appropriate orchestrate command"""

    return OrchestratorPromptResponse(
        prompt=prompt,
        tool=tool,
        instructions=instructions,
        project_name=project.name,
        project_id=project.id,
        agent_count=agent_count
    )


@router.get("/agent/{agent_id}", response_model=AgentPromptResponse)
async def generate_agent_prompt(
    agent_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate universal agent prompt (works in any terminal).

    Generates executable bash commands for running an individual agent.
    Prompt works across all AI coding tools (Claude Code, Codex, Gemini).

    Args:
        agent_id: Agent job ID
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        AgentPromptResponse with prompt, agent metadata, and instructions

    Raises:
        404: Agent not found or not accessible
        403: User not authorized to access agent
    """
    # Get agent job with project relationship and tenant isolation
    stmt = (
        select(MCPAgentJob)
        .where(
            MCPAgentJob.job_id == agent_id,
            MCPAgentJob.tenant_key == current_user.tenant_key
        )
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Agent {agent_id} not found or not accessible"
        )

    # Get project for path information
    project_path = "."
    if agent.project_id:
        project_stmt = select(Project).where(
            Project.id == agent.project_id,
            Project.tenant_key == current_user.tenant_key
        )
        project_result = await db.execute(project_stmt)
        project = project_result.scalar_one_or_none()
        if project and project.meta_data:
            project_path = project.meta_data.get("path", ".")

    # Generate agent display name if not set
    agent_display_name = agent.agent_name or f"{agent.agent_type.title()} Agent"

    # Truncate mission for preview (first 200 chars)
    mission_preview = agent.mission[:200] + "..." if len(agent.mission) > 200 else agent.mission

    # Create missions directory if needed
    missions_dir = Path(project_path) / ".missions"

    # Generate universal prompt
    prompt = f"""# Agent: {agent_display_name}
# Type: {agent.agent_type}
# Tool: {agent.tool_type}
# Mission: {mission_preview}

cd {project_path}
export AGENT_ID={agent.job_id}
export AGENT_TYPE={agent.agent_type}
export PROJECT_ID={agent.project_id or 'none'}

# Create mission file
mkdir -p .missions
cat > .missions/{agent.job_id}.md << 'EOF'
{agent.mission}
EOF

# Execute agent mission
{agent.tool_type.lower()}-agent execute --mission-file=.missions/{agent.job_id}.md"""

    instructions = f"""Copy the commands above to your terminal to start this agent.

Agent Details:
- Name: {agent_display_name}
- Type: {agent.agent_type}
- Tool: {agent.tool_type}
- Status: {agent.status}

Prerequisites:
- {agent.tool_type} must be installed and configured
- Agent will read mission from .missions/{agent.job_id}.md
- Environment variables provide context to the agent"""

    return AgentPromptResponse(
        prompt=prompt,
        agent_id=agent.job_id,
        agent_name=agent_display_name,
        agent_type=agent.agent_type,
        tool_type=agent.tool_type,
        instructions=instructions,
        mission_preview=mission_preview
    )


@router.post("/estimate-tokens")
async def estimate_mission_tokens(
    request: TokenEstimateRequest,
    current_user: User = Depends(get_current_active_user),
):
    """
    Estimate token usage for a mission (Handover 0065).

    Calculation:
    - Mission tokens: ~4 chars per token (standard estimate)
    - Context tokens: project_description length / 4
    - Per-agent overhead: 500 tokens per agent (template + tools)
    - Total = mission + context + (agents * overhead)

    Args:
        request: Token estimation request with mission, agent count, and optional project description
        current_user: Authenticated user (ensures multi-tenant isolation)

    Returns:
        dict: Token breakdown with:
            - mission_tokens: Tokens in mission text
            - context_tokens: Tokens in project context
            - agent_overhead: Overhead per agent (templates, tools)
            - total_estimate: Total estimated tokens
            - budget_available: Available token budget
            - within_budget: Boolean indicating if estimate is within budget
            - utilization_percent: Percentage of budget used
    """
    # Token calculation constants
    CHARS_PER_TOKEN = 4
    AGENT_OVERHEAD_TOKENS = 500
    DEFAULT_BUDGET = 10000  # Field priority budget from Handover 0048

    # Calculate mission tokens
    mission_tokens = len(request.mission) // CHARS_PER_TOKEN

    # Calculate context tokens
    context_tokens = 0
    if request.project_description:
        context_tokens = len(request.project_description) // CHARS_PER_TOKEN

    # Calculate agent overhead
    agent_overhead = request.agent_count * AGENT_OVERHEAD_TOKENS

    # Total estimate
    total_estimate = mission_tokens + context_tokens + agent_overhead

    # Budget analysis
    budget_available = DEFAULT_BUDGET
    within_budget = total_estimate <= budget_available
    utilization_percent = round((total_estimate / budget_available) * 100, 1)

    logger.info(
        f"[TOKEN ESTIMATE] User {current_user.username} - "
        f"Mission: {mission_tokens}t, Context: {context_tokens}t, "
        f"Agent Overhead: {agent_overhead}t ({request.agent_count} agents), "
        f"Total: {total_estimate}t ({utilization_percent}%)"
    )

    return {
        "mission_tokens": mission_tokens,
        "context_tokens": context_tokens,
        "agent_overhead": agent_overhead,
        "total_estimate": total_estimate,
        "budget_available": budget_available,
        "within_budget": within_budget,
        "utilization_percent": utilization_percent
    }


@router.get("/staging/{project_id}")
async def generate_staging_prompt(
    project_id: str,
    tool: str = Query("claude-code", regex="^(claude-code|codex|gemini)$"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate comprehensive orchestrator staging prompt (Handover 0079).

    THE HEART OF GILJOAI - Generates intelligent, token-efficient orchestrator
    prompts that enable AI agents to discover context via MCP, create condensed
    missions, and coordinate multi-agent workflows.

    Process:
    1. Validates project exists and belongs to tenant
    2. Gathers context via MCP-simulated queries (product, vision, priorities, templates)
    3. Applies field priorities and token budget management
    4. Generates eloquent 5-phase orchestrator instructions
    5. Returns ready-to-paste comprehensive prompt

    Features:
    - MCP-only data access (remote-safe, no local file reads)
    - Dynamic field priority integration (user-configured)
    - 20K token budget management (Claude 25K limit - 5K safety buffer)
    - 70% token reduction architecture
    - Multi-tool support (Claude Code, Codex, Gemini)
    - Max 8 agent types enforced

    Args:
        project_id: Project UUID to generate prompt for
        tool: Target AI tool (claude-code, codex, or gemini)
        current_user: Authenticated user (ensures tenant isolation)
        db: Database session

    Returns:
        dict: Comprehensive prompt response with:
            - prompt: Full orchestrator staging prompt (2000-3000 lines)
            - token_estimate: Estimated total token usage
            - budget_utilization: Percentage of 20K budget used
            - context_included: Summary of included context
            - warnings: Budget/priority warnings
            - tool: Target tool identifier
            - estimate_details: Detailed token breakdown

    Raises:
        HTTPException 404: Project not found or not accessible
        HTTPException 400: Invalid tool parameter
        HTTPException 500: Prompt generation error

    Example Response:
        {
            "prompt": "ORCHESTRATOR STAGING PROMPT\\n...\\n(comprehensive instructions)",
            "token_estimate": 8500,
            "budget_utilization": "42.5%",
            "context_included": {
                "product_name": "My Product",
                "project_name": "Feature Implementation",
                "vision_chunk_count": 3,
                "field_count": 4,
                "template_count": 6
            },
            "warnings": [],
            "tool": "claude-code"
        }
    """
    try:
        # Initialize prompt generator
        generator = OrchestratorPromptGenerator(db, current_user.tenant_key)

        # Generate comprehensive prompt
        result = await generator.generate(project_id, tool)

        # Log successful generation
        logger.info(
            f"[STAGING PROMPT] Generated for project={project_id}, "
            f"tool={tool}, tokens={result['token_estimate']}, "
            f"utilization={result['budget_utilization']}, "
            f"user={current_user.username}"
        )

        return result

    except ValueError as e:
        # Project not found or invalid tool
        logger.warning(f"[STAGING PROMPT] Validation error for project={project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e)
        )

    except Exception as e:
        # Unexpected error during generation
        logger.exception(f"[STAGING PROMPT] Generation failed for project={project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate staging prompt: {str(e)}"
        )
