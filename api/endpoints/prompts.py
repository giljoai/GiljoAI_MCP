"""
Prompt Generation API endpoints for Handover 0073: Static Agent Grid.

Provides REST API for generating executable prompts:
- GET /api/prompts/orchestrator/{tool} - Generate orchestrator prompt
- GET /api/prompts/agent/{agent_id} - Generate agent prompt
- GET /api/prompts/staging/{project_id} - Generate comprehensive orchestrator staging prompt (Handover 0079)

All endpoints enforce multi-tenant isolation and authentication.
"""

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency
from api.schemas.prompt import (
    AgentPromptResponse,
    OrchestratorPromptRequest,
    OrchestratorPromptResponse,
)
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator


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
    stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found or not accessible"
        )

    # Count agents in project (via AgentExecution)
    agent_count_stmt = (
        select(func.count(AgentExecution.agent_id))
        .where(AgentExecution.tenant_key == current_user.tenant_key)
        .join(AgentJob, (AgentJob.job_id == AgentExecution.job_id) & (AgentJob.tenant_key == AgentExecution.tenant_key))
        .where(AgentJob.project_id == project_id)
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
        agent_count=agent_count,
    )


@router.post("/prompts/orchestrator-thin", response_model=OrchestratorPromptResponse)
async def generate_orchestrator_prompt_thin(
    request: OrchestratorPromptRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
) -> OrchestratorPromptResponse:
    """
    Generate a thin orchestrator prompt for GiljoMCP Agent Orchestration.

    Handover 0088: Thin Client Architecture
    - Prompt is only ~300 tokens (down from ~3500)
    - Mission fetched via get_orchestrator_instructions() MCP tool
    - Field priorities applied at MCP tool call time, not prompt generation
    - Context size tracking built into thin client flow

    Handover 0246a (Nov 2025): Further optimizations
    - Staging prompt reduced from ~1600 to 931 tokens (42% reduction)
    - 7-task standardized workflow
    - Clean separation between staging/execution

    Args:
        request: Request containing project_id and tool
        current_user: Currently authenticated user
        db: Database session

    Returns:
        OrchestratorPromptResponse with thin prompt

    Raises:
        HTTPException: If project not found or error occurs
    """
    try:
        project_id = request.project_id
        tool = request.tool or "universal"

        # Create thin prompt generator
        generator = ThinClientPromptGenerator(db, current_user.tenant_key)

        # BUG FIX: Fetch user's field priority configuration from database
        # Extract 'priorities' dict from user's field_priority_config JSONB column
        # Fixed: Was looking for "fields" but should be "priorities"
        user_field_config = current_user.field_priority_config or {}
        field_priorities = user_field_config.get("priorities", {})

        # Generate thin prompt with user field priorities
        result = await generator.generate(
            project_id=project_id,
            user_id=str(current_user.id),  # CRITICAL: Pass user_id for field priorities
            tool=tool,
            field_priorities=field_priorities,  # FIX: Pass user's configured field priorities
        )

        # Broadcast WebSocket event for real-time UI update
        if ws_dep.is_available():
            await ws_dep.broadcast_to_tenant(
                tenant_key=current_user.tenant_key,
                event_type="orchestrator:prompt_generated",
                data={
                    "project_id": project_id,
                    "orchestrator_id": result["orchestrator_id"],
                    "execution_id": result.get("execution_id"),  # UNIQUE row ID for frontend Map key
                    "estimated_tokens": result["estimated_prompt_tokens"],
                    "thin_client": True,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        return OrchestratorPromptResponse(
            success=True,
            orchestrator_id=result["orchestrator_id"],
            prompt=result["thin_prompt"],
            context_budget=result["context_budget"],
            context_used=0,  # New orchestrator starts with 0 context used
            estimated_prompt_tokens=result["estimated_prompt_tokens"],
            thin_client=True,
            status="ready",
        )

    except ValueError as e:
        logger.error(f"Validation error generating thin orchestrator prompt: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e
    except Exception as e:
        logger.error(f"Error generating thin orchestrator prompt: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate orchestrator prompt: {e!s}"
        ) from e


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
    # Get agent execution with job relationship and tenant isolation
    stmt = (
        select(AgentExecution)
        .options(joinedload(AgentExecution.job))
        .where(AgentExecution.agent_id == agent_id, AgentExecution.tenant_key == current_user.tenant_key)
    )
    result = await db.execute(stmt)
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Agent {agent_id} not found or not accessible"
        )

    # Get project for path information (from job relationship)
    project_path = "."
    if agent.job and agent.job.project_id:
        project_stmt = select(Project).where(
            Project.id == agent.job.project_id, Project.tenant_key == current_user.tenant_key
        )
        project_result = await db.execute(project_stmt)
        project = project_result.scalar_one_or_none()
        if project and project.meta_data:
            project_path = project.meta_data.get("path", ".")

    # Generate agent display name if not set
    agent_display_name = agent.agent_name or f"{agent.agent_display_name.title()} Agent"

    # Truncate mission for preview (first 200 chars) - mission is in job
    mission = agent.job.mission if agent.job else ""
    mission_preview = mission[:200] + "..." if len(mission) > 200 else mission

    # Create missions directory if needed
    Path(project_path) / ".missions"

    # Get tool type from agent execution metadata (default to "claude-code")
    tool_type = agent.metadata.get("tool_type", "claude-code") if agent.metadata else "claude-code"

    # Generate universal prompt
    prompt = f"""# Agent: {agent_display_name}
# Type: {agent.agent_display_name}
# Tool: {tool_type}
# Mission: {mission_preview}

## FIRST ACTION (MANDATORY)
# Before executing any work, verify MCP connection:
# Call: mcp__giljo-mcp__health_check()
# Expected: {{"status": "healthy"}} - If failed, STOP and report error

cd {project_path}
export AGENT_ID={agent.agent_id}
export AGENT_DISPLAY_NAME={agent.agent_display_name}
export PROJECT_ID={agent.job.project_id if agent.job else "none"}

# Create mission file
mkdir -p .missions
cat > .missions/{agent.agent_id}.md << 'EOF'
{mission}
EOF

# Execute agent mission
{tool_type.lower()}-agent execute --mission-file=.missions/{agent.agent_id}.md"""

    instructions = f"""Copy the commands above to your terminal to start this agent.

Agent Details:
- Name: {agent_display_name}
- Display Name: {agent.agent_display_name}
- Tool: {tool_type}
- Status: {agent.status}

Prerequisites:
- {tool_type} must be installed and configured
- Agent will read mission from .missions/{agent.agent_id}.md
- Environment variables provide context to the agent"""

    return AgentPromptResponse(
        prompt=prompt,
        agent_id=agent.agent_id,
        agent_name=agent_display_name,
        agent_display_name=agent.agent_display_name,
        tool_type=tool_type,
        instructions=instructions,
        mission_preview=mission_preview,
    )


@router.get("/staging/{project_id}")
async def generate_staging_prompt(
    project_id: str,
    tool: str = Query("claude-code", pattern="^(claude-code|codex|gemini)$"),
    execution_mode: str = Query(
        "multi_terminal",
        pattern="^(multi_terminal|claude_code_cli)$",
        description="Execution mode: 'multi_terminal' (manual) or 'claude_code_cli' (single terminal with Task tool)",
    ),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
):
    """
    Generate thin client orchestrator staging prompt (Handover 0088).

    UPDATED FOR THIN CLIENT ARCHITECTURE:
    - OLD (Handover 0079): Returns 2000-3000 line fat prompt with embedded mission
    - NEW (Handover 0088): Returns ~10 line thin prompt with MCP tool reference

    THE HEART OF GILJOAI - Generates intelligent, token-efficient orchestrator
    prompts that enable AI agents to discover context via MCP, create condensed
    missions, and coordinate multi-agent workflows.

    Process:
    1. Validates project exists and belongs to tenant
    2. Creates orchestrator job in database
    3. Stores condensed mission with user's field priorities
    4. Generates thin prompt with orchestrator_id
    5. Returns ready-to-paste thin prompt (~10 lines)

    Features:
    - Thin client architecture (context prioritization and orchestration ACTIVE)
    - MCP-only data access (remote-safe, no local file reads)
    - Dynamic field priority integration (user-configured)
    - Professional UX (copy 10 lines, not 3000)
    - Multi-tool support (Claude Code, Codex, Gemini)

    Args:
        project_id: Project UUID to generate prompt for
        tool: Target AI tool (claude-code, codex, or gemini)
        current_user: Authenticated user (ensures tenant isolation)
        db: Database session

    Returns:
        ThinPromptResponse: Thin client prompt response with:
            - prompt: Thin orchestrator prompt (~10 lines)
            - orchestrator_id: Created orchestrator job ID
            - project_id: Project UUID
            - project_name: Project name
            - estimated_prompt_tokens: ~50 tokens
            - mcp_tool_name: MCP tool to fetch mission
            - instructions_stored: True (mission in database)
            - thin_client: True

    Raises:
        HTTPException 404: Project not found or not accessible
        HTTPException 400: Invalid tool parameter
        HTTPException 500: Prompt generation error
    """
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    try:
        # Initialize thin client generator
        generator = ThinClientPromptGenerator(db, current_user.tenant_key)

        # BUG FIX: Fetch user's field priority configuration from database
        # Extract 'priorities' dict from user's field_priority_config JSONB column (v2.0 schema)
        user_field_config = current_user.field_priority_config or {}
        field_priorities = user_field_config.get("priorities", {})

        # Generate thin prompt with user field priorities
        result = await generator.generate(
            project_id=project_id,
            user_id=str(current_user.id),  # CRITICAL: Pass user_id for field priorities
            tool=tool,
            field_priorities=field_priorities,  # FIX: Pass user's configured field priorities
        )

        # Use generate_staging_prompt for mode-specific content
        # Handover 0388: Pass agent_id for correct MCP tool call in prompt
        staging_prompt = await generator.generate_staging_prompt(
            orchestrator_id=result["orchestrator_id"],
            project_id=project_id,
            agent_id=result.get("agent_id"),  # WHO - executor ID for MCP tool calls
        )

        # Calculate token estimate for staging prompt (1 token ≈ 4 chars)
        staging_tokens = len(staging_prompt) // 4

        # Broadcast WebSocket event for real-time UI update
        if ws_dep.is_available():
            await ws_dep.broadcast_to_tenant(
                tenant_key=current_user.tenant_key,
                event_type="orchestrator:prompt_generated",
                data={
                    "orchestrator_id": result["orchestrator_id"],
                    "agent_id": result.get("agent_id"),  # Handover 0388: Include agent_id
                    "execution_id": result.get("execution_id"),  # UNIQUE row ID for frontend Map key
                    "project_id": project_id,
                    "thin_client": True,
                    "tool": tool,
                },
            )
            logger.info(f"[STAGING PROMPT THIN] WebSocket broadcast sent for orchestrator {result['orchestrator_id']}")

        # Log successful generation
        logger.info(
            f"[STAGING PROMPT THIN] Generated for project={project_id}, "
            f"tool={tool}, tokens={result['estimated_prompt_tokens']}, "
            f"user={current_user.username}"
        )

        # Return response with 'prompt' key for frontend compatibility
        # Handover 0260: Use staging_prompt (mode-specific) instead of thin_prompt
        # Handover 0388: Include agent_id in response
        return {
            "orchestrator_id": result["orchestrator_id"],
            "agent_id": result.get("agent_id"),  # WHO - executor ID for MCP tool calls
            "prompt": staging_prompt,  # Mode-specific staging prompt
            "context_budget": result["context_budget"],
            "estimated_prompt_tokens": staging_tokens,  # Updated token count for staging prompt
        }

    except ValueError as e:
        # Project not found or invalid tool
        logger.warning(f"[STAGING PROMPT THIN] Validation error for project={project_id}: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from e

    except Exception as e:
        # Unexpected error during generation
        logger.exception(f"[STAGING PROMPT THIN] Generation failed for project={project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate thin staging prompt: {e!s}"
        ) from e


@router.get("/implementation/{project_id}")
async def get_implementation_prompt(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate implementation prompt for CLI mode projects (Handover 0337 - Task 1).

    This endpoint generates the implementation phase prompt for Claude Code CLI mode.
    After staging (where orchestrator plans and spawns agent jobs), the user pastes
    this implementation prompt to have the orchestrator spawn agents via Task tool.

    Requirements:
    - Project must exist and be in CLI mode (execution_mode = 'claude_code_cli')
    - Active orchestrator job must exist (status = 'working')
    - At least one spawned agent job must exist (status in ['waiting', 'working'])
    - Multi-tenant isolation enforced

    Process:
    1. Validate project exists and belongs to tenant
    2. Validate CLI mode execution
    3. Fetch active orchestrator job
    4. Fetch spawned agent jobs
    5. Generate implementation prompt via ThinClientPromptGenerator
    6. Return prompt with metadata

    Args:
        project_id: Project UUID to generate implementation prompt for
        current_user: Authenticated user (ensures tenant isolation)
        db: Database session

    Returns:
        dict: Implementation prompt response with:
            - prompt: Implementation prompt for orchestrator to spawn agents
            - orchestrator_job_id: Orchestrator job UUID
            - agent_count: Number of spawned agents ready to execute

    Raises:
        HTTPException 404: Project not found or no active orchestrator
        HTTPException 400: Not CLI mode or no spawned agents
        HTTPException 403: Tenant isolation violation
        HTTPException 500: Prompt generation error
    """
    from src.giljo_mcp.thin_prompt_generator import ThinClientPromptGenerator

    try:
        # 1. Fetch project with multi-tenant filtering
        project_stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
        project_result = await db.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found or not accessible"
            )

        # 2. Validate CLI mode
        if project.execution_mode != "claude_code_cli":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Project is not in CLI mode. Implementation prompts are only for claude_code_cli execution mode.",
            )

        # 3. Fetch orchestrator execution (waiting after staging, or working during execution)
        orchestrator_stmt = (
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .where(
                AgentExecution.tenant_key == current_user.tenant_key,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.status.in_(["waiting", "working"]),
            )
            .join(
                AgentJob,
                (AgentJob.job_id == AgentExecution.job_id) & (AgentJob.tenant_key == AgentExecution.tenant_key),
            )
            .where(AgentJob.project_id == project_id)
            .order_by(AgentExecution.started_at.desc().nullslast())
        )

        orchestrator_result = await db.execute(orchestrator_stmt)
        orchestrator_execution = orchestrator_result.scalar_one_or_none()

        if not orchestrator_execution:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No orchestrator found for this project. Please ensure staging has been completed.",
            )

        # 4. Fetch spawned agent executions (waiting or working status)
        # First try by spawned_by (agent_id now), then fallback to project_id for legacy data
        agent_executions_stmt = (
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .where(
                AgentExecution.spawned_by == orchestrator_execution.agent_id,
                AgentExecution.tenant_key == current_user.tenant_key,
                AgentExecution.status.in_(["waiting", "working"]),
            )
            .order_by(AgentExecution.started_at.asc().nullsfirst())
        )

        agent_executions_result = await db.execute(agent_executions_stmt)
        agent_executions = agent_executions_result.scalars().all()

        # Fallback: Query by project_id for agents without spawned_by set (legacy data)
        if not agent_executions:
            fallback_stmt = (
                select(AgentExecution)
                .options(joinedload(AgentExecution.job))
                .where(
                    AgentExecution.tenant_key == current_user.tenant_key,
                    AgentExecution.agent_display_name != "orchestrator",  # Exclude orchestrator itself
                    AgentExecution.status.in_(["waiting", "working"]),
                )
                .join(
                    AgentJob,
                    (AgentJob.job_id == AgentExecution.job_id) & (AgentJob.tenant_key == AgentExecution.tenant_key),
                )
                .where(AgentJob.project_id == project_id)
                .order_by(AgentExecution.started_at.asc().nullsfirst())
            )

            fallback_result = await db.execute(fallback_stmt)
            agent_executions = fallback_result.scalars().all()

        if not agent_executions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No agent jobs spawned yet. Please run staging first to create agent jobs.",
            )

        # 5. Generate implementation prompt using existing generator method
        generator = ThinClientPromptGenerator(db, current_user.tenant_key)

        # Build agent jobs list for prompt generator (using executions + jobs)
        [
            {
                "job_id": agent_exec.job_id,
                "agent_display_name": agent_exec.agent_display_name,
                "agent_name": agent_exec.agent_name or agent_exec.agent_display_name,
                "status": agent_exec.status,
                "mission": agent_exec.job.mission if agent_exec.job else "(No mission assigned)",
            }
            for agent_exec in agent_executions
        ]

        # Call the existing implementation prompt generator
        # Handover 0385: Use job_id (not agent_id) for mission retrieval
        prompt = generator._build_claude_code_execution_prompt(
            orchestrator_id=orchestrator_execution.job_id, project=project, agent_jobs=agent_executions
        )

        logger.info(
            f"[IMPLEMENTATION PROMPT] Generated for project={project_id}, "
            f"orchestrator={orchestrator_execution.agent_id}, agents={len(agent_executions)}, "
            f"user={current_user.username}"
        )

        # 6. Return implementation prompt response
        return {
            "prompt": prompt,
            "orchestrator_job_id": orchestrator_execution.agent_id,
            "agent_count": len(agent_executions),
        }

    except Exception as e:
        # Unexpected error during generation
        logger.exception(f"[IMPLEMENTATION PROMPT] Generation failed for project={project_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate implementation prompt: {e!s}"
        ) from e
