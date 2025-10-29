"""
Prompt Generation API endpoints for Handover 0073: Static Agent Grid.

Provides REST API for generating executable prompts:
- GET /api/prompts/orchestrator/{tool} - Generate orchestrator prompt
- GET /api/prompts/agent/{agent_id} - Generate agent prompt

All endpoints enforce multi-tenant isolation and authentication.
"""

import logging
from pathlib import Path
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.prompt import AgentPromptResponse, OrchestratorPromptResponse
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import MCPAgentJob, Project, User

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
