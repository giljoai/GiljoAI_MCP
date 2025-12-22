"""
Claude Code Integration Tools

Provides helper functions to map GiljoAI MCP agents to Claude Code sub-agent types
and generate orchestrator prompts that can spawn the appropriate sub-agents.
"""

from typing import Dict

from ..database import DatabaseManager
from ..models import AgentJob, AgentExecution, Project


# Mapping of MCP agent roles to Claude Code agent types
CLAUDE_CODE_AGENT_TYPES = {
    "orchestrator": "orchestrator-coordinator",
    "database": "database-expert",
    "database_expert": "database-expert",
    "backend": "tdd-implementor",
    "backend_developer": "tdd-implementor",
    "implementor": "tdd-implementor",
    "tester": "backend-integration-tester",
    "integration_tester": "backend-integration-tester",
    "researcher": "deep-researcher",
    "research": "deep-researcher",
    "architect": "system-architect",
    "system_architect": "system-architect",
    "frontend": "ux-designer",
    "frontend_developer": "ux-designer",
    "ui_designer": "ux-designer",
    "security": "network-security-engineer",
    "network": "network-security-engineer",
    "documentation": "documentation-manager",
    "docs": "documentation-manager",
    "reviewer": "general-purpose",
    "general": "general-purpose",
}


def get_claude_code_agent_type(mcp_role: str) -> str:
    """
    Map MCP agent role to Claude Code agent type.

    Args:
        mcp_role: The role from GiljoAI MCP (e.g., "database", "backend")

    Returns:
        Claude Code agent type (e.g., "database-expert", "tdd-implementor")
    """
    role_normalized = mcp_role.lower().strip().replace(" ", "_")
    return CLAUDE_CODE_AGENT_TYPES.get(role_normalized, "general-purpose")


def generate_agent_spawn_instructions(project_id: str, tenant_key: str) -> Dict:
    """
    Generate instructions for Claude Code orchestrator to spawn sub-agents.

    This function reads the project's agents from MCP and creates a mapping
    that the orchestrator can use to spawn Claude Code sub-agents with
    the correct missions.

    Args:
        project_id: The project ID
        tenant_key: The tenant key for multi-tenant isolation

    Returns:
        Dictionary with agent spawn instructions
    """
    from sqlalchemy import select

    db_manager = DatabaseManager()
    with db_manager.get_session() as session:
        # Get project
        result = session.execute(select(Project).filter_by(id=project_id, tenant_key=tenant_key))
        project = result.scalar_one_or_none()

        if not project:
            return {"error": "Project not found"}

        # Get all active agent jobs for this project (dual-model: AgentJob + AgentExecution - Handover 0358c)
        result = session.execute(
            select(AgentJob).filter_by(project_id=project_id, tenant_key=tenant_key, status="active")
        )
        agent_jobs = list(result.scalars().all())

        agent_instructions = []
        for job in agent_jobs:
            # Get the latest execution for this job to retrieve agent_id (executor UUID)
            exec_result = session.execute(
                select(AgentExecution)
                .filter_by(job_id=job.job_id, tenant_key=tenant_key)
                .order_by(AgentExecution.started_at.desc().nullslast())
            )
            latest_execution = exec_result.scalars().first()

            claude_type = get_claude_code_agent_type(job.job_type)

            agent_instructions.append(
                {
                    "mcp_agent_id": str(job.id),  # job_id = work order UUID (persistent)
                    "agent_execution_id": str(latest_execution.agent_id) if latest_execution else None,  # agent_id = executor UUID
                    "mcp_agent_name": job.job_type,
                    "mcp_role": job.job_type,
                    "claude_code_type": claude_type,
                    "mission": job.mission or f"Work on {project.name} as {job.job_type}",
                    "context_budget": job.metadata.get("context_budget", 50000) if job.metadata else 50000,
                }
            )

        return {
            "project_id": project_id,
            "project_name": project.name,
            "project_mission": project.mission,
            "total_agents": len(agent_instructions),
            "agents": agent_instructions,
        }


def generate_orchestrator_prompt(project_id: str, tenant_key: str) -> str:
    """
    Generate a ready-to-paste orchestrator prompt for Claude Code.

    This creates a single prompt that the developer can paste into Claude Code CLI.
    The orchestrator will read this, call back to MCP to get agent details,
    and spawn the appropriate sub-agents.

    Args:
        project_id: The project ID
        tenant_key: The tenant key

    Returns:
        Formatted orchestrator prompt string
    """
    instructions = generate_agent_spawn_instructions(project_id, tenant_key)

    if "error" in instructions:
        return f"Error: {instructions['error']}"

    prompt = f"""# GiljoAI MCP Orchestration Request

## Project Details
- **Project ID**: {instructions["project_id"]}
- **Project Name**: {instructions["project_name"]}
- **Mission**: {instructions["project_mission"]}

## Instructions for Orchestrator

You are coordinating a multi-agent project from GiljoAI MCP. Follow these steps:

1. **Verify MCP Connection**: Call `mcp__giljo-mcp__list_agents` to confirm you can read project agents
2. **Spawn Sub-Agents**: For each agent listed below, spawn a Claude Code sub-agent with the specified mission
3. **Coordinate Work**: Manage handoffs, track progress, and ensure completion

## Agents to Spawn ({instructions["total_agents"]} total)

"""

    for i, agent in enumerate(instructions["agents"], 1):
        prompt += f"""
### {i}. {agent["mcp_agent_name"]} ({agent["mcp_role"]})
- **Claude Code Agent Type**: `{agent["claude_code_type"]}`
- **MCP Agent ID**: `{agent["mcp_agent_id"]}`
- **Mission**: {agent["mission"]}
- **Context Budget**: {agent["context_budget"]} tokens

"""

    prompt += """
## Workflow

1. Read full agent details from MCP using `mcp__giljo-mcp__list_agents`
2. Spawn each agent using the `Task` tool with the mapped Claude Code type
3. Coordinate their work according to the project mission
4. Track progress and handle handoffs as needed

Begin orchestration now.
"""

    return prompt


# MCP Tool registration would go here
def register_claude_code_tools(server):
    """Register Claude Code integration tools with MCP server."""

    @server.tool()
    def get_orchestrator_prompt(project_id: str) -> str:
        """
        Generate a Claude Code orchestrator prompt for a project.

        This creates a ready-to-paste prompt that developers can use to
        start multi-agent orchestration in Claude Code CLI.

        Args:
            project_id: The project ID to orchestrate

        Returns:
            Formatted orchestrator prompt
        """
        # In real implementation, get tenant_key from context
        from ..tenant import get_current_tenant_key

        tenant_key = get_current_tenant_key()

        return generate_orchestrator_prompt(project_id, tenant_key)

    @server.tool()
    def get_agent_mapping(mcp_role: str) -> Dict:
        """
        Get the Claude Code agent type for an MCP role.

        Args:
            mcp_role: MCP agent role (e.g., "database", "backend")

        Returns:
            Dictionary with mapping information
        """
        claude_type = get_claude_code_agent_type(mcp_role)
        return {
            "mcp_role": mcp_role,
            "claude_code_type": claude_type,
            "available_types": list(set(CLAUDE_CODE_AGENT_TYPES.values())),
        }
