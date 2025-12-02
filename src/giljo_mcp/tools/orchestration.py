"""
Orchestration MCP Tools - Extended for Slash Command Support

Provides MCP tools for intelligent multi-agent orchestration with context prioritization and orchestration.
Exposes orchestration capabilities via Model Context Protocol for agent coordination.

This module also provides tools that act as "prompt generators" for slash command workflows,
enabling automated agent setup and project orchestration via Claude Code CLI commands.
"""

import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import uuid4

from fastmcp import FastMCP
from sqlalchemy import and_, select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import AgentTemplate, Job, MCPAgentJob, Product, Project
from giljo_mcp.orchestrator import ProjectOrchestrator


logger = logging.getLogger(__name__)


# Handover 0281 Phase 1: Default configurations for monolithic context
DEFAULT_FIELD_PRIORITIES = {
    "product_core": {"toggle": True, "priority": 1},
    "project_context": {"toggle": True, "priority": 1},
    "vision_documents": {"toggle": True, "priority": 2},
    "tech_stack": {"toggle": True, "priority": 2},
    "architecture": {"toggle": True, "priority": 3},
    "testing_config": {"toggle": True, "priority": 3},
    "memory_360": {"toggle": True, "priority": 2},
    "git_history": {"toggle": False, "priority": 4},
    "agent_templates": {"toggle": True, "priority": 2}
}

DEFAULT_DEPTH_CONFIG = {
    "vision_chunking": "moderate",  # 4 chunks
    "memory_last_n_projects": 5,
    "git_commits": 15,
    "agent_template_detail": "standard"
}


async def _get_user_config(
    user_id: str,
    tenant_key: str,
    session: Any  # AsyncSession type hint would create circular import
) -> Dict[str, Any]:
    """
    Fetch user's field_priority_config and depth_config from database.

    Args:
        user_id: User UUID
        tenant_key: Tenant isolation key
        session: SQLAlchemy AsyncSession

    Returns:
        dict with 'field_priorities' and 'depth_config' keys

    Behavior:
        - Returns user's custom config if exists
        - Falls back to DEFAULT_FIELD_PRIORITIES and DEFAULT_DEPTH_CONFIG if None
        - Ensures multi-tenant isolation (user must belong to tenant_key)
    """
    from giljo_mcp.models.auth import User

    try:
        # Query user with tenant isolation
        result = await session.execute(
            select(User).where(
                and_(
                    User.id == user_id,
                    User.tenant_key == tenant_key,
                    User.is_active == True
                )
            )
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                f"[USER_CONFIG] User {user_id} not found or inactive for tenant {tenant_key}, using defaults",
                extra={"user_id": user_id, "tenant_key": tenant_key}
            )
            return {
                "field_priorities": DEFAULT_FIELD_PRIORITIES.copy(),
                "depth_config": DEFAULT_DEPTH_CONFIG.copy()
            }

        # Get user's custom configs or fall back to defaults
        field_priorities = user.field_priority_config if user.field_priority_config is not None else DEFAULT_FIELD_PRIORITIES.copy()
        depth_config = user.depth_config if user.depth_config is not None else DEFAULT_DEPTH_CONFIG.copy()

        logger.info(
            "[USER_CONFIG] Fetched user configuration",
            extra={
                "user_id": user_id,
                "tenant_key": tenant_key,
                "has_custom_field_priorities": user.field_priority_config is not None,
                "has_custom_depth_config": user.depth_config is not None
            }
        )

        return {
            "field_priorities": field_priorities,
            "depth_config": depth_config
        }

    except Exception as e:
        logger.error(
            f"[USER_CONFIG] Failed to fetch user config: {e}",
            extra={"user_id": user_id, "tenant_key": tenant_key},
            exc_info=True
        )
        # Fall back to defaults on error
        return {
            "field_priorities": DEFAULT_FIELD_PRIORITIES.copy(),
            "depth_config": DEFAULT_DEPTH_CONFIG.copy()
        }



def _infer_execution_mode_from_tool(tool_type: str | None) -> str:
    """
    Infer execution_mode from tool_type when not explicitly specified.

    Args:
        tool_type: Tool type from orchestrator job (claude-code, codex, gemini, universal, None)

    Returns:
        Inferred execution mode ('claude-code' or 'legacy')

    Examples:
        >>> _infer_execution_mode_from_tool('claude-code')
        'claude-code'
        >>> _infer_execution_mode_from_tool('universal')
        'legacy'
        >>> _infer_execution_mode_from_tool(None)
        'legacy'
    """
    if tool_type == "claude-code":
        return "claude-code"
    # Default to legacy for all other cases (codex, gemini, universal, None)
    return "legacy"


def _build_mode_instructions(execution_mode: str, agent_templates: list[dict]) -> str:
    """
    Build mode-specific instructions for orchestrator.

    Args:
        execution_mode: Execution mode ('claude-code' or 'legacy')
        agent_templates: List of agent template dictionaries

    Returns:
        Mode-specific instruction text

    Examples:
        Claude Code mode returns instructions for spawning sub-agents via Task tool.
        Legacy mode returns instructions for manual terminal launches.
    """
    if execution_mode == "claude-code":
        # Claude Code mode - orchestrator spawns sub-agents
        instructions = """**CLAUDE CODE MODE - Sub-Agent Spawning**

You can spawn specialist agents as sub-agents using the Task tool.

**Workflow**:
1. Review agent templates below for available specialists
2. Use spawn_agent_job() MCP tool to create agent job in database
3. Spawn sub-agent via Task tool with agent's launch_instructions
4. Monitor progress via get_workflow_status()

**Example**:
```python
# Step 1: Create agent job via MCP
result = await spawn_agent_job(
    agent_type="implementer",
    agent_name="Backend Implementer",
    mission="Implement user authentication",
    project_id=project_id,
    tenant_key=tenant_key
)

# Step 2: Spawn sub-agent using Task tool with launch_instructions
# Use the launch_instructions from agent template below
```

**Agent Launch Instructions**:
Each agent template below includes launch_instructions showing how to start the agent.
"""
        return instructions
    else:
        # Legacy mode - manual terminal launches
        instructions = """**LEGACY MODE - Manual Agent Launches**

Specialist agents must be launched manually in separate terminals.

**Workflow**:
1. Use spawn_agent_job() MCP tool to create agent jobs
2. Copy each agent's launch_instructions from templates below
3. User manually pastes commands into separate terminal windows
4. Monitor progress via get_workflow_status()

**Agent Launch Instructions**:
Each agent template below includes launch_instructions for manual copying.
"""
        return instructions


def _format_agent_templates(templates: list, execution_mode: str) -> list[dict]:
    """
    Format agent templates with launch_instructions for the given execution mode.

    Args:
        templates: SQLAlchemy AgentTemplate model instances
        execution_mode: Execution mode ('claude-code' or 'legacy')

    Returns:
        List of formatted agent template dictionaries with launch_instructions

    Examples:
        >>> templates = [AgentTemplate(name='implementer', ...)]
        >>> formatted = _format_agent_templates(templates, 'claude-code')
        >>> formatted[0]['launch_instructions']
        'cd $PROJECT_PATH && claude-code --agent implementer'
    """
    formatted_templates = []

    for template in templates:
        template_dict = {
            "name": template.name,
            "role": template.role,
            "description": template.description[:200] if template.description else "",
        }

        # Extract launch_instructions from meta_data
        if template.meta_data and "launch_instructions" in template.meta_data:
            template_dict["launch_instructions"] = template.meta_data["launch_instructions"]
        else:
            # Provide default launch instruction if not specified
            template_dict["launch_instructions"] = (
                f"cd $PROJECT_PATH && {execution_mode} --agent {template.name}"
            )

        formatted_templates.append(template_dict)

    return formatted_templates


def register_orchestration_tools(mcp: FastMCP, db_manager: DatabaseManager) -> None:
    """
    Register orchestration tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        db_manager: Database manager for data access
    """

    # ========================================================================
    # Core Orchestration Tools (existing tools remain unchanged)
    # ========================================================================
    @mcp.tool()
    async def orchestrate_project(project_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Complete project orchestration workflow.

        Triggers the full orchestration pipeline:
        1. Vision processing and analysis
        2. Mission generation for specialized agents
        3. Agent selection based on requirements
        4. Agent job spawning
        5. Workflow coordination

        Args:
            project_id: Project database ID (UUID)
            tenant_key: Tenant isolation key

        Returns:
            Dictionary containing:
            - project_id: Created/used project ID
            - mission_plan: Generated missions for agents
            - selected_agents: List of agent types selected
            - spawned_jobs: List of spawned job IDs
            - workflow_result: Workflow execution result
            - token_reduction: Context prioritization metrics

        Example:
            {
                'project_id': 'proj-123',
                'mission_plan': {...},
                'selected_agents': ['implementer', 'tester'],
                'spawned_jobs': ['job-1', 'job-2'],
                'workflow_result': {...},
                'token_reduction': {'reduction_percent': 70.0}
            }
        """
        try:
            # Validate inputs
            if not project_id or not project_id.strip():
                return {"error": "Project ID is required"}

            if not tenant_key or not tenant_key.strip():
                return {"error": "Tenant key is required"}

            # Get project by ID with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": f"Project '{project_id}' not found"}

                # Ensure project has product_id
                if not project.product_id:
                    return {"error": f"Project '{project_id}' has no associated product"}

                # Initialize orchestrator
                orchestrator = ProjectOrchestrator()

                # Run orchestration workflow
                logger.info(
                    f"Starting orchestration for project {project.id} (name: {project.name}, tenant: {tenant_key})"
                )

                result_dict = await orchestrator.process_product_vision(
                    tenant_key=tenant_key, product_id=project.product_id, project_requirements=project.mission
                )

                # Handover 0118: Send welcome message to all spawned jobs
                try:
                    await orchestrator.send_welcome_broadcast(project_id=project.id)
                except Exception:
                    # Non-fatal; continue returning orchestration result
                    pass

                logger.info(
                    f"Orchestration completed for project {project.id}. "
                    f"Spawned {len(result_dict.get('spawned_jobs', []))} jobs."
                )

                return result_dict

        except ValueError as e:
            logger.error(f"Orchestration validation error: {e}")
            return {"error": str(e)}
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            return {"error": f"Orchestration failed: {e!s}"}

    # --------------------------------------------------------------------
    # Messaging protocol helpers (Handover 0118)
    # --------------------------------------------------------------------

    @mcp.tool()
    async def send_welcome(project_id: str, tenant_key: str) -> dict[str, Any]:
        """Send welcome/directive message to all agents in a project."""
        try:
            orchestrator = ProjectOrchestrator()
            sent = await orchestrator.send_welcome_broadcast(project_id)
            return {"success": True, "sent": sent}
        except Exception as e:
            logger.exception(f"send_welcome failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def broadcast_status(project_id: str, tenant_key: str) -> dict[str, Any]:
        """Broadcast team status summary to all agents."""
        try:
            orchestrator = ProjectOrchestrator()
            res = await orchestrator.broadcast_team_status(project_id)
            return {"success": True, **res}
        except Exception as e:
            logger.exception(f"broadcast_status failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def coordinate_messages(
        project_id: str,
        tenant_key: str,
        iterations: int = 10,
        interval_seconds: float = 3.0,
    ) -> dict[str, Any]:
        """Poll message queues and handle progress/errors for a bounded time."""
        try:
            orchestrator = ProjectOrchestrator()
            res = await orchestrator.poll_and_handle_messages(
                project_id=project_id,
                iterations=iterations,
                interval_seconds=interval_seconds,
            )
            return {"success": True, **res}
        except Exception as e:
            logger.exception(f"coordinate_messages failed: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def get_agent_mission(agent_job_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Fetch agent-specific mission and context (Thin Client Architecture).

        Agents call this to get their targeted mission (not entire project vision).
        Part of Handover 0088 Amendment B - Agent Thin Client Implementation.

        Args:
            agent_job_id: Agent job UUID
            tenant_key: Tenant isolation key

        Returns:
            Dictionary containing:
            - agent_job_id: UUID
            - agent_name: Human-readable name
            - agent_type: Type (backend, frontend, etc.)
            - mission: Agent-specific mission
            - project_context: Relevant project context
            - estimated_tokens: Token count
            - thin_client: True (architecture flag)

        Example:
            mission = await get_agent_mission(
                agent_job_id='agent-123',
                tenant_key='tenant-abc'
            )
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get agent job from MCPAgentJob table
                result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(MCPAgentJob.job_id == agent_job_id, MCPAgentJob.tenant_key == tenant_key)
                    )
                )
                agent_job = result.scalar_one_or_none()

                if not agent_job:
                    return {
                        "error": "NOT_FOUND",
                        "message": f"Agent job {agent_job_id} not found",
                        "troubleshooting": [
                            "Verify agent was spawned successfully",
                            "Check if project was deleted",
                            "Ensure tenant_key matches",
                            f"Check database: SELECT * FROM mcp_agent_jobs WHERE job_id = '{agent_job_id}'",
                        ],
                        "severity": "ERROR",
                    }

                # Mission is stored in job.mission field (thin client pattern)
                estimated_tokens = len(agent_job.mission or "") // 4

                logger.info(
                    f"[THIN CLIENT] Agent mission fetched: {agent_job.agent_type}",
                    extra={"agent_job_id": agent_job_id, "tokens": estimated_tokens},
                )

                return {
                    "success": True,
                    "agent_job_id": agent_job_id,
                    "agent_name": agent_job.agent_type,  # Use agent_type as name
                    "agent_type": agent_job.agent_type,
                    "mission": agent_job.mission or "",
                    "project_id": str(agent_job.project_id),
                    "parent_job_id": str(agent_job.spawned_by) if agent_job.spawned_by else None,
                    "estimated_tokens": estimated_tokens,
                    "status": agent_job.status,
                    "thin_client": True,
                }

        except Exception as e:
            logger.error(f"[ERROR] Failed to get agent mission: {e}", exc_info=True)
            return {
                "error": "INTERNAL_ERROR",
                "message": f"Unexpected error: {e!s}",
                "troubleshooting": [
                    "Check MCP server logs",
                    "Verify database connection",
                    "Contact support if issue persists",
                ],
                "severity": "ERROR",
            }

    @mcp.tool()
    async def get_generic_agent_template(
        agent_id: str,
        job_id: str,
        product_id: str,
        project_id: str,
        tenant_key: str,
    ) -> dict[str, Any]:
        """
        Get generic agent template with injected variables for multi-terminal mode.

        Used by Orchestrator to spawn agents in Generic/Legacy mode.
        Template provides unified protocol for all agent types.

        Handover 0246b: Generic Agent Template Implementation

        Args:
            agent_id: UUID of agent instance
            job_id: UUID of job in MCP_AGENT_JOBS
            product_id: UUID of product context
            project_id: UUID of project context
            tenant_key: Tenant isolation key

        Returns:
            {
                "success": true,
                "template": "<rendered prompt>",
                "variables_injected": {...},
                "protocol_version": "1.0",
                "estimated_tokens": 2400
            }
        """
        try:
            from src.giljo_mcp.templates.generic_agent_template import GenericAgentTemplate

            template = GenericAgentTemplate()
            rendered = template.render(
                agent_id=agent_id,
                job_id=job_id,
                product_id=product_id,
                project_id=project_id,
                tenant_key=tenant_key,
            )

            logger.info(
                "Generic agent template rendered",
                extra={
                    "agent_id": agent_id,
                    "job_id": job_id,
                    "template_version": template.version,
                    "tenant_key": tenant_key,
                },
            )

            return {
                "success": True,
                "template": rendered,
                "variables_injected": {
                    "agent_id": agent_id,
                    "job_id": job_id,
                    "product_id": product_id,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                },
                "protocol_version": template.version,
                "estimated_tokens": len(rendered) // 4,  # Rough estimate
            }

        except Exception as e:
            logger.error(
                f"Failed to render generic agent template: {e}",
                extra={"agent_id": agent_id, "job_id": job_id, "tenant_key": tenant_key},
            )
            return {
                "success": False,
                "error": str(e),
                "agent_id": agent_id,
                "job_id": job_id,
            }

    @mcp.tool()
    async def spawn_agent_job(
        agent_type: str,
        agent_name: str,
        mission: str,
        project_id: str,
        tenant_key: str,
        parent_job_id: Optional[str] = None,
        template_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create specialist agent job for EXECUTION (orchestrator assigns work during STAGING).

        PURPOSE: Orchestrator delegates work to specialist agents who will EXECUTE tasks.
        This tool is called during PROJECT STAGING to create agent jobs. The agents will DO THE WORK.

        ORCHESTRATOR'S WORKFLOW:
        1. CREATE mission plan (analyzed from Project.description)
        2. BREAK DOWN mission into agent-specific work items
        3. SPAWN agents using this tool (delegates execution to specialists)
        4. Each agent receives portion of overall mission as their job

        AGENT'S ROLE (after spawning):
        - Agent calls get_agent_mission() to fetch their job (MCPAgentJob.mission)
        - Agent EXECUTES their assigned work (writes code, runs tests, etc.)
        - Agent reports progress back via MCP tools

        CRITICAL DISTINCTIONS:
        - Orchestrator STAGES (plans & coordinates) during initial setup
        - Specialist agents EXECUTE (do the actual work) after being spawned
        - This tool creates the bridge: orchestrator assigns work → agent executes it

        THIN CLIENT ARCHITECTURE:
        - Mission stored in MCPAgentJob.mission database field
        - Returned prompt is ~10 lines (agent identity only)
        - Agent calls get_agent_mission() to fetch full mission
        - WebSocket broadcast updates UI (agent appears in grid)

        HANDOVER 0244a:
        - template_id links agent job to its source template
        - Enables (i) icon functionality to display template metadata

        Args:
            agent_type: Type of agent (backend-tester, frontend-dev, etc.)
            agent_name: Human-readable name for the agent
            mission: Agent's specific job assignment (portion of overall Project.mission)
            project_id: Project UUID
            tenant_key: Tenant isolation key
            parent_job_id: Optional parent orchestrator ID (for tracking)
            template_id: Optional template ID this job was spawned from (Handover 0244a)

        Returns:
            {
                'success': True,
                'agent_job_id': 'uuid',
                'agent_prompt': '~10 line thin prompt for agent to paste',
                'prompt_tokens': 50,
                'mission_stored': True,  # Mission saved to MCPAgentJob.mission
                'mission_tokens': 2000,
                'thin_client': True
            }
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get project for context
                result = await session.execute(
                    select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": "NOT_FOUND", "message": "Project not found"}

                # ORCHESTRATOR DUPLICATION PREVENTION
                # Check if we're trying to create an orchestrator
                if agent_type == "orchestrator":
                    # Query for existing orchestrators in this project with active statuses
                    result = await session.execute(
                        select(MCPAgentJob).where(
                            and_(
                                MCPAgentJob.project_id == project_id,
                                MCPAgentJob.tenant_key == tenant_key,
                                MCPAgentJob.agent_type == "orchestrator",
                                MCPAgentJob.status.in_(["waiting", "working"])
                            )
                        )
                    )
                    existing_orchestrator = result.scalar_one_or_none()

                    if existing_orchestrator:
                        # Active orchestrator already exists - prevent duplicate
                        logger.warning(
                            f"Orchestrator already exists for project {project_id} with status {existing_orchestrator.status}",
                            extra={
                                "project_id": project_id,
                                "tenant_key": tenant_key,
                                "existing_job_id": existing_orchestrator.job_id,
                                "existing_status": existing_orchestrator.status
                            }
                        )
                        return {
                            "success": False,
                            "error": f"Orchestrator already exists for this project with status '{existing_orchestrator.status}'. "
                                     f"Only one active orchestrator is allowed during staging. Use succession for runtime handover.",
                            "existing_job_id": existing_orchestrator.job_id,
                            "existing_status": existing_orchestrator.status
                        }

                # No duplicate found (or not an orchestrator) - proceed with creation
                agent_job_id = str(uuid4())
                agent_job = MCPAgentJob(
                    job_id=agent_job_id,
                    project_id=project_id,
                    tenant_key=tenant_key,
                    agent_type=agent_type,
                    mission=mission,  # STORED HERE, not in prompt
                    spawned_by=parent_job_id,
                    template_id=template_id,  # Handover 0244a: Link to source template
                    status="waiting",  # Fixed: was "pending" but constraint only allows "waiting"
                    metadata={
                        "created_via": "thin_client_spawn",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "thin_client": True,
                    },
                )

                session.add(agent_job)
                await session.commit()
                await session.refresh(agent_job)

                # Generate THIN agent prompt (~10 lines)
                thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type}) for Project "{project.name}".

IDENTITY:
- Agent ID: {agent_job_id}
- Agent Type: {agent_type}
- Project ID: {project_id}
- Parent Orchestrator: {parent_job_id or "None"}

INSTRUCTIONS:
1. Fetch mission: get_agent_mission(agent_job_id='{agent_job_id}', tenant_key='{tenant_key}')
2. Execute mission
3. Report progress: update_job_progress('{agent_job_id}', percent, message)
4. Coordinate via: send_message(to_agent_id, content)

Begin by fetching your mission.
"""

                # Calculate token estimates
                prompt_tokens = len(thin_agent_prompt) // 4  # ~50 tokens
                mission_tokens = len(mission) // 4  # ~2000 tokens

                # Broadcast agent creation via HTTP bridge (Handover 0111 Issue #1 - FIXED)
                # MCP tools run in separate process, must use HTTP bridge for WebSocket events
                try:
                    import httpx

                    # Use HTTP bridge to emit WebSocket event (cross-process communication)
                    async with httpx.AsyncClient() as client:
                        bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"

                        response = await client.post(
                            bridge_url,
                            json={
                                "event_type": "agent:created",
                                "tenant_key": tenant_key,
                                "data": {
                                    "project_id": project_id,
                                    "agent_id": agent_job_id,
                                    "agent_job_id": agent_job_id,
                                    "agent_type": agent_type,
                                    "agent_name": agent_name,
                                    "status": "pending",
                                    "thin_client": True,
                                    "prompt_tokens": prompt_tokens,
                                    "mission_tokens": mission_tokens,
                                }
                            },
                            timeout=5.0  # 5 second timeout
                        )

                        if response.status_code == 200:
                            logger.info(f"[HTTP BRIDGE] Agent spawned broadcast sent: {agent_name} ({agent_type})")
                        else:
                            logger.warning(f"[HTTP BRIDGE] Broadcast failed with status {response.status_code}")

                except Exception as bridge_error:
                    logger.warning(f"[HTTP BRIDGE] Failed to broadcast agent:created: {bridge_error}")

                return {
                    "success": True,
                    "agent_job_id": agent_job_id,
                    "agent_prompt": thin_agent_prompt,  # ~10 lines
                    "prompt_tokens": prompt_tokens,  # ~50
                    "mission_stored": True,
                    "mission_tokens": mission_tokens,  # ~2000
                    "total_tokens": prompt_tokens + mission_tokens,
                    "thin_client": True,
                }

        except Exception as e:
            logger.error(f"[ERROR] Failed to spawn agent job: {e}", exc_info=True)
            return {"error": "INTERNAL_ERROR", "message": f"Failed to spawn agent: {e!s}", "severity": "ERROR"}

    @mcp.tool()
    async def get_workflow_status(project_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Get current workflow status for a project.

        Provides real-time status of the orchestration workflow including:
        - Active agents (currently working)
        - Completed agents (finished their work)
        - Failed agents (encountered errors)
        - Current workflow stage
        - Overall progress percentage

        Args:
            project_id: Project database ID (UUID)
            tenant_key: Tenant key for isolation

        Returns:
            Dictionary containing:
            - active_agents: Count of agents currently working
            - completed_agents: Count of completed agents
            - failed_agents: Count of failed agents
            - pending_agents: Count of pending agents
            - current_stage: Current workflow stage description
            - progress_percent: Overall progress (0-100)
            - total_agents: Total number of agents

        Example:
            {
                'active_agents': 2,
                'completed_agents': 3,
                'failed_agents': 0,
                'pending_agents': 1,
                'current_stage': 'Implementation',
                'progress_percent': 60.0,
                'total_agents': 6
            }
        """
        try:
            # Validate inputs
            if not project_id or not project_id.strip():
                return {"error": "Project ID is required"}

            if not tenant_key or not tenant_key.strip():
                return {"error": "Tenant key is required"}

            # Verify project exists with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": f"Project '{project_id}' not found"}

                # Get all Jobs for this project/tenant
                # Note: Job doesn't have project_id, so we filter by tenant_key
                jobs_result = await session.execute(select(Job).where(Job.tenant_key == tenant_key))
                jobs = jobs_result.scalars().all()

                # Count by status
                active_count = sum(1 for job in jobs if job.status == "active")
                completed_count = sum(1 for job in jobs if job.status == "completed")
                failed_count = sum(1 for job in jobs if job.status == "failed")
                pending_count = sum(1 for job in jobs if job.status == "pending")
                total_count = len(jobs)

                # Calculate progress percentage
                if total_count > 0:
                    progress_percent = (completed_count / total_count) * 100.0
                else:
                    progress_percent = 0.0

                # Determine current stage
                if total_count == 0:
                    current_stage = "Not started"
                elif completed_count == total_count:
                    current_stage = "Completed"
                elif failed_count > 0:
                    current_stage = f"In Progress (with {failed_count} failure(s))"
                elif active_count > 0:
                    current_stage = "In Progress"
                elif pending_count > 0:
                    current_stage = "Pending"
                else:
                    current_stage = "Unknown"

                logger.info(
                    f"Workflow status for project {project_id}: "
                    f"{completed_count}/{total_count} completed ({progress_percent:.1f}%)"
                )

                return {
                    "active_agents": active_count,
                    "completed_agents": completed_count,
                    "failed_agents": failed_count,
                    "pending_agents": pending_count,
                    "current_stage": current_stage,
                    "progress_percent": round(progress_percent, 2),
                    "total_agents": total_count,
                }

        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}", exc_info=True)
            return {"error": f"Failed to get workflow status: {e!s}"}

    # ========================================================================
    # Slash Command Support Tools (Prompt Generators)
    # These tools return formatted instructions for Claude Code to execute
    # ========================================================================

    @mcp.tool()
    async def get_project_by_alias(alias: str) -> dict[str, Any]:
        """
        Fetch project details using its 6-character alias.

        This tool enables quick project access without needing to remember
        long UUIDs. Each project has a unique 6-character alphanumeric alias.

        Args:
            alias: 6-character project alias (case insensitive)

        Returns:
            Dictionary containing project details or error
        """
        try:
            if not alias or len(alias) != 6:
                return {"error": "Alias must be exactly 6 characters"}

            alias_upper = alias.upper()

            async with db_manager.get_session_async() as session:
                # For now, use project name search as fallback until alias column is added
                result = await session.execute(select(Project).where(Project.name.ilike(f"%{alias_upper}%")))
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": f"Project with alias '{alias_upper}' not found"}

                # Get product details if available
                product_name = None
                if project.product_id:
                    product_result = await session.execute(select(Product).where(Product.id == project.product_id))
                    product = product_result.scalar_one_or_none()
                    if product:
                        product_name = product.name

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "alias": alias_upper,
                    "tenant_key": project.tenant_key,
                    "product_id": str(project.product_id) if project.product_id else None,
                    "product_name": product_name,
                    "mission": project.mission,
                    "status": project.status,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                }

        except Exception as e:
            logger.error(f"Failed to get project by alias '{alias}': {e}", exc_info=True)
            return {"error": f"Failed to fetch project: {e!s}"}

    @mcp.tool()
    async def activate_project_mission(alias: str) -> dict[str, Any]:
        """
        Activate a project and create mission plan for orchestration.

        This tool prepares a project for orchestration by analyzing requirements
        and generating detailed instructions for launching the workflow.

        Args:
            alias: 6-character project alias

        Returns:
            Dictionary with activation status and launch instructions
        """
        try:
            # Get project by alias
            project_result = await get_project_by_alias(alias)

            if "error" in project_result:
                return project_result

            project_id = project_result["project_id"]
            tenant_key = project_result["tenant_key"]
            project_name = project_result["project_name"]

            if not project_result.get("product_id"):
                return {"error": f"Project '{alias}' has no associated product vision"}

            # Generate formatted instructions for mission activation
            instructions = f"""
# Project Mission Activation

**Project**: {project_name} (Alias: {alias.upper()})
**Status**: Ready for orchestration

## Mission Plan Generated

Your project has been analyzed and the following workflow has been prepared:

1. **Orchestrator Agent** - Coordinates all activities
2. **Implementer Agents** - Build features according to specifications  
3. **Tester Agents** - Validate functionality and quality
4. **Reviewer Agents** - Ensure code quality and best practices

## Next Steps

To launch the orchestration workflow, use:
```
/mcp__gil__launch_project {alias.upper()}
```

This will:
- Spawn all required agents with their specific missions
- Begin coordinated development workflow
- Track progress in real-time
- Deliver completed solution

The mission plan has been staged and is ready for execution.
"""

            return {
                "success": True,
                "project_id": project_id,
                "alias": alias.upper(),
                "status": "activated",
                "instructions": instructions,
            }

        except Exception as e:
            logger.error(f"Failed to activate project '{alias}': {e}", exc_info=True)
            return {"error": f"Failed to activate project: {e!s}"}

    @mcp.tool()
    async def get_launch_prompt(alias: str) -> dict[str, Any]:
        """
        Generate orchestration launch instructions for a project.

        Returns formatted instructions that guide Claude Code through
        launching the full orchestration workflow.

        Args:
            alias: 6-character project alias

        Returns:
            Dictionary with launch instructions
        """
        try:
            # Get project details
            project_result = await get_project_by_alias(alias)

            if "error" in project_result:
                return project_result

            project_id = project_result["project_id"]
            tenant_key = project_result["tenant_key"]
            project_name = project_result["project_name"]

            # Format launch instructions
            instructions = f"""
# Launch Project Orchestration

**Project**: {project_name} (Alias: {alias.upper()})

## Executing Orchestration Workflow

I will now launch the full orchestration pipeline for your project.

### What will happen:

1. **Initialize Orchestrator** - Set up coordination framework
2. **Spawn Specialized Agents** - Deploy implementer, tester, and reviewer agents
3. **Distribute Missions** - Each agent receives their specific objectives
4. **Begin Development** - Agents work in coordinated fashion
5. **Track Progress** - Monitor via dashboard at http://localhost:7272

### Orchestration Command:

```python
# Launching orchestration for project {alias.upper()}
result = await orchestrate_project(
    project_id="{project_id}",
    tenant_key="{tenant_key}"
)
```

### Monitoring Progress:

- View real-time status in web dashboard
- Agents will coordinate automatically
- Completion notifications will be sent
- Results will be delivered upon completion

The orchestration workflow is now starting...
"""

            return {"success": True, "project_id": project_id, "alias": alias.upper(), "instructions": instructions}

        except Exception as e:
            logger.error(f"Failed to get launch prompt for '{alias}': {e}", exc_info=True)
            return {"error": f"Failed to generate launch prompt: {e!s}"}

    @mcp.tool()
    async def get_fetch_agents_instructions() -> dict[str, Any]:
        """
        Generate instructions for installing GiljoAI agent templates.

        Provides step-by-step instructions for downloading and installing
        the standard agent templates to enable subagent orchestration.

        Returns:
            Dictionary with installation instructions
        """
        try:
            server_url = os.environ.get("GILJO_SERVER_URL", "http://localhost:7272")

            instructions = f"""
# Install GiljoAI Agent Templates

## Installation Process

I will help you install the standard GiljoAI agent templates to enable 
subagent orchestration capabilities.

### Step 1: Create agents directory
```bash
mkdir -p ~/.claude/agents
```

### Step 2: Download agent templates from server
```bash
cd ~/.claude/agents

# Download core agent templates
curl -o orchestrator.md {server_url}/api/agents/templates/orchestrator.md
curl -o implementer.md {server_url}/api/agents/templates/implementer.md  
curl -o tester.md {server_url}/api/agents/templates/tester.md
curl -o reviewer.md {server_url}/api/agents/templates/reviewer.md
curl -o documenter.md {server_url}/api/agents/templates/documenter.md
```

### Step 3: Verify installation
```bash
ls -la ~/.claude/agents/*.md
```

### Step 4: Restart Claude Code
After installation, restart Claude Code to load the new agent templates.

## Post-Installation

Once agents are installed and Claude Code is restarted:

1. Use `/mcp__gil__activate_project <alias>` to prepare a project
2. Use `/mcp__gil__launch_project <alias>` to start orchestration
3. Monitor progress in the web dashboard

The agent templates include MCP tool integration for seamless coordination.
"""

            return {"success": True, "server_url": server_url, "instructions": instructions}

        except Exception as e:
            logger.error(f"Failed to generate fetch agents instructions: {e}", exc_info=True)
            return {"error": f"Failed to generate instructions: {e!s}"}

    @mcp.tool()
    async def get_update_agents_instructions() -> dict[str, Any]:
        """
        Generate instructions for updating existing agent templates.

        Provides instructions for updating already installed agent templates
        with the latest versions from the server.

        Returns:
            Dictionary with update instructions
        """
        try:
            server_url = os.environ.get("GILJO_SERVER_URL", "http://localhost:7272")
            agents_dir = Path.home() / ".claude" / "agents"

            # Check if agents are already installed
            if not agents_dir.exists():
                return {
                    "success": False,
                    "instructions": "No agents installed. Please run /mcp__gil__fetch_agents first.",
                }

            instructions = f"""
# Update GiljoAI Agent Templates

## Update Process

I will update your existing agent templates with the latest versions.

### Step 1: Backup existing templates
```bash
cd ~/.claude/agents
mkdir -p backup
cp *.md backup/
```

### Step 2: Download latest templates
```bash
# Update all agent templates
curl -o orchestrator.md {server_url}/api/agents/templates/orchestrator.md
curl -o implementer.md {server_url}/api/agents/templates/implementer.md
curl -o tester.md {server_url}/api/agents/templates/tester.md
curl -o reviewer.md {server_url}/api/agents/templates/reviewer.md
curl -o documenter.md {server_url}/api/agents/templates/documenter.md
```

### Step 3: Verify update
```bash
ls -la ~/.claude/agents/*.md
```

### Step 4: Restart Claude Code if agents are active
If you have agents currently running, restart Claude Code to load the updates.

## Update Notes

- Templates are backward compatible
- Existing projects will use updated templates
- New features and improvements included
- Your backup is saved in ~/.claude/agents/backup/

The agent templates are now being updated...
"""

            return {"success": True, "server_url": server_url, "instructions": instructions}

        except Exception as e:
            logger.error(f"Failed to generate update agents instructions: {e}", exc_info=True)
            return {"error": f"Failed to generate instructions: {e!s}"}

    # ========================================================================
    # Thin Client MCP Tools (Handover 0088)
    # Enable context prioritization and orchestration via thin client architecture
    # ========================================================================

    @mcp.tool()
    async def health_check() -> dict[str, Any]:
        """
        MCP server health check.

        Orchestrators call this first to verify MCP connection before fetching mission.

        Returns:
            {
                'status': 'healthy',
                'server': 'giljo-mcp',
                'version': '3.1.0',
                'timestamp': '2025-11-03T...'
            }

        Example:
            health = await health_check()
            if health['status'] == 'healthy':
                # Proceed to fetch mission
        """
        from datetime import datetime, timezone

        return {
            "status": "healthy",
            "server": "giljo-mcp",
            "version": "3.1.0",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "message": "GiljoAI MCP server is operational",
        }

    @mcp.tool()
    async def get_available_agents(tenant_key: str, active_only: bool = True) -> dict[str, Any]:
        """
        Get available agent templates with version metadata (Handover 0246c).

        PURPOSE: Dynamic agent discovery without embedding templates in prompts.
        Orchestrators call this to discover which agents are available for spawning.

        Args:
            tenant_key: Tenant isolation key
            active_only: Filter to active templates only (default: True)

        Returns:
            {
                "success": True,
                "data": {
                    "agents": [
                        {
                            "name": "implementer",
                            "role": "Code Implementation Specialist",
                            "description": "...",
                            "version_tag": "1.2.0",
                            "expected_filename": "implementer_1.2.0.md",
                            "created_at": "2025-11-24T12:00:00"
                        }
                    ],
                    "count": 5,
                    "fetched_at": "2025-11-24T12:30:00",
                    "note": "Templates fetched dynamically (not embedded in prompt)"
                }
            }

        Example:
            agents = await get_available_agents(tenant_key="tk_abc123")
            for agent in agents["data"]["agents"]:
                print(f"Available: {agent['name']} v{agent['version_tag']}")
        """
        from src.giljo_mcp.tools.agent_discovery import get_available_agents as get_agents

        logger.info(
            "Orchestrator requesting available agents",
            extra={"tenant_key": tenant_key, "active_only": active_only}
        )

        async with db_manager.get_session_async() as session:
            result = await get_agents(session, tenant_key)

        if result["success"]:
            logger.info(
                f"Returned {result['data']['count']} available agents",
                extra={"tenant_key": tenant_key}
            )

        return result

    @mcp.tool()
    async def get_orchestrator_instructions(orchestrator_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Fetch context for orchestrator to CREATE mission plan (Handover 0088).

        PURPOSE: PROJECT STAGING (NOT EXECUTION)
        This provides INPUT CONTEXT for the orchestrator to analyze and create a mission plan.
        The orchestrator will READ this data and GENERATE a mission (not execute work itself).

        RETURNS (for orchestrator to analyze):
        - Project.description: User-written requirements (INPUT - what needs to be done)
        - Product context: Product vision and architecture (INPUT - system context)
        - Agent templates: Available specialists (INPUT - who can do the work)
        - Condensed content: context prioritization and orchestration via field priorities

        ORCHESTRATOR'S JOB:
        1. READ returned Project.description (user requirements)
        2. ANALYZE requirements and break down into work items
        3. CREATE mission plan (condensed execution strategy)
        4. PERSIST mission via update_project_mission() tool
        5. SPAWN specialist agents who will EXECUTE the work

        CRITICAL: The orchestrator is STAGING, not EXECUTING. It coordinates specialist agents.

        Args:
            orchestrator_id: Orchestrator job UUID
            tenant_key: Tenant isolation key

        Returns:
            {
                'orchestrator_id': 'uuid',
                'project_id': 'uuid',
                'project_name': 'My Project',
                'project_description': 'User-written requirements (INPUT for analysis)',
                'product_context': 'Product vision and architecture (INPUT)',
                'mission': 'Condensed content with priority fields (context for planning)',
                'context_budget': 150000,
                'context_used': 0,
                'agent_templates': [...],  # Available specialists (INPUT)
                'field_priorities': {...},
                'token_reduction_applied': True,
                'estimated_tokens': 6000
            }

        Example:
            instructions = await get_orchestrator_instructions(
                orchestrator_id='orch-123',
                tenant_key='tenant-abc'
            )
            # Returns condensed mission, not entire vision
        """
        try:
            # Validate inputs (Amendment D: Production-grade error handling)
            if not orchestrator_id or not orchestrator_id.strip():
                return {
                    "error": "VALIDATION_ERROR",
                    "message": "Orchestrator ID is required and cannot be empty",
                    "troubleshooting": [
                        "Check thin prompt for orchestrator_id value",
                        "Verify you copied the entire prompt correctly",
                    ],
                    "severity": "ERROR",
                }

            if not tenant_key or not tenant_key.strip():
                return {
                    "error": "VALIDATION_ERROR",
                    "message": "Tenant key is required for multi-tenant isolation",
                    "troubleshooting": [
                        "Check thin prompt for tenant_key value",
                        "Ensure MCP server is authenticated correctly",
                    ],
                    "severity": "ERROR",
                }

            async with db_manager.get_session_async() as session:
                # Get orchestrator job with tenant isolation
                result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.job_id == orchestrator_id,
                            MCPAgentJob.tenant_key == tenant_key,
                            MCPAgentJob.agent_type == "orchestrator",
                        )
                    )
                )
                orchestrator = result.scalar_one_or_none()

                if not orchestrator:
                    return {
                        "error": "NOT_FOUND",
                        "message": f"Orchestrator {orchestrator_id} not found in database",
                        "details": {
                            "orchestrator_id": orchestrator_id,
                            "tenant_key": tenant_key,
                            "search_performed": True,
                        },
                        "troubleshooting": [
                            "Verify orchestrator was created successfully during staging",
                            "Check if project was deleted",
                            "Ensure tenant_key matches the staging environment",
                            f"Check database: SELECT * FROM mcp_agent_jobs WHERE job_id = '{orchestrator_id}'",
                        ],
                        "severity": "ERROR",
                        "contact_support": "If problem persists: support@giljoai.com",
                    }

                # Handover 0233: Track mission_read_at timestamp (idempotent)
                # Set timestamp on FIRST read only (doesn't overwrite existing)
                if orchestrator.mission_read_at is None:
                    orchestrator.mission_read_at = datetime.now(timezone.utc)
                    await session.commit()
                    logger.info(
                        f"[MISSION_TRACKING] Set mission_read_at for orchestrator {orchestrator_id}",
                        extra={"orchestrator_id": orchestrator_id, "tenant_key": tenant_key}
                    )

                    # Handover 0233 Phase 5: Emit WebSocket event for mission_read
                    try:
                        # Import websocket manager
                        from api.app import state

                        ws_manager = getattr(state, "websocket_manager", None)

                        if ws_manager:
                            await ws_manager.broadcast_to_tenant(
                                tenant_key=tenant_key,
                                event_type="job:mission_read",
                                data={
                                    "job_id": orchestrator_id,
                                    "mission_read_at": orchestrator.mission_read_at.isoformat(),
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                },
                            )
                            logger.info(
                                f"[WEBSOCKET] Broadcasted job:mission_read event",
                                extra={
                                    "orchestrator_id": orchestrator_id,
                                    "tenant_key": tenant_key,
                                    "mission_read_at": orchestrator.mission_read_at.isoformat()
                                }
                            )
                    except Exception as ws_error:
                        # Non-blocking - WebSocket failures shouldn't break MCP tool
                        logger.warning(
                            f"[WEBSOCKET] Failed to broadcast job:mission_read event: {ws_error}",
                            extra={"orchestrator_id": orchestrator_id}
                        )

                # Get project with tenant isolation
                result = await session.execute(
                    select(Project).where(and_(Project.id == orchestrator.project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "error": "NOT_FOUND",
                        "message": "Project not found",
                        "troubleshooting": ["Project may have been deleted", "Check database integrity"],
                        "severity": "ERROR",
                    }

                # Get product (if exists)
                product = None
                if project.product_id:
                    result = await session.execute(
                        select(Product).where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
                    )
                    product = result.scalar_one_or_none()

                # Use MissionPlanner to build condensed mission (context prioritization and orchestration)
                from giljo_mcp.mission_planner import MissionPlanner

                # MissionPlanner requires DatabaseManager (not AsyncSession)
                planner = MissionPlanner(db_manager)

                # Get field priorities from orchestrator job_metadata (Handover 0088)
                # Uses dedicated job_metadata JSONB column for thin client data
                metadata = orchestrator.job_metadata or {}
                field_priorities = metadata.get("field_priorities", {})
                user_id = metadata.get("user_id")

                # Check if Serena is enabled (from config.yaml)
                # Serena toggle is in My Settings → Integrations
                include_serena = False
                try:
                    from pathlib import Path
                    import yaml

                    config_path = Path.cwd() / "config.yaml"
                    if config_path.exists():
                        with open(config_path, encoding="utf-8") as f:
                            config_data = yaml.safe_load(f) or {}
                        include_serena = config_data.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False)
                        if include_serena:
                            logger.info(
                                f"[SERENA] Enabled for orchestrator {orchestrator_id}",
                                extra={"orchestrator_id": orchestrator_id, "project_id": str(project.id)}
                            )
                except Exception as e:
                    logger.warning(f"[SERENA] Failed to read config for Serena toggle: {e}")
                    include_serena = False

                # Generate condensed mission with field priorities applied
                condensed_mission = await planner._build_context_with_priorities(
                    product=product, project=project, field_priorities=field_priorities, user_id=user_id, include_serena=include_serena
                )

                # Handover 0277: Inject simplified Serena MCP notice if enabled
                if include_serena:
                    try:
                        from giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions

                        serena_instructions = generate_serena_instructions(enabled=True)

                        # Prepend Serena instructions to mission
                        condensed_mission = serena_instructions + "\n\n---\n\n" + condensed_mission
                        logger.info(
                            f"[SERENA] Injected simplified Serena notice into orchestrator mission",
                            extra={"orchestrator_id": orchestrator_id, "serena_instructions_length": len(serena_instructions)}
                        )
                    except Exception as e:
                        logger.warning(f"[SERENA] Failed to inject Serena notice: {e}")
                        # Continue without Serena notice if injection fails

                # Handover 0246c: Agent templates no longer embedded
                # Use get_available_agents() MCP tool instead

                # Handover 0270: Inject MCP Tool Catalog if enabled via field priorities
                if field_priorities.get("mcp_tool_catalog", 1) > 0:
                    try:
                        from giljo_mcp.prompt_generation.mcp_tool_catalog import MCPToolCatalogGenerator

                        catalog_gen = MCPToolCatalogGenerator()
                        mcp_catalog = catalog_gen.generate_full_catalog(field_priorities=field_priorities)

                        # Append catalog to mission for orchestrator
                        if mcp_catalog:
                            condensed_mission = condensed_mission + "\n\n---\n\n" + mcp_catalog
                            logger.info(
                                f"[MCP_CATALOG] Injected MCP Tool Catalog into orchestrator mission",
                                extra={"orchestrator_id": orchestrator_id, "catalog_length": len(mcp_catalog)}
                            )
                    except Exception as e:
                        logger.warning(f"[MCP_CATALOG] Failed to inject MCP Tool Catalog: {e}")
                        # Continue without catalog if injection fails

                # Calculate token estimate
                estimated_tokens = len(condensed_mission) // 4  # 1 token ≈ 4 chars

                # Amendment A: Broadcast WebSocket event for real-time UI update
                try:
                    # Import WebSocket manager (avoid circular imports)
                    from api.app import state

                    ws_manager = getattr(state, "websocket_manager", None)

                    if ws_manager:
                        await ws_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="orchestrator:instructions_fetched",
                            data={
                                "orchestrator_id": orchestrator_id,
                                "project_id": str(project.id),
                                "estimated_tokens": estimated_tokens,
                                "status": "active",
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                                "thin_client": True,
                            },
                        )
                        logger.info(
                            f"[WEBSOCKET] Broadcasted orchestrator:instructions_fetched to {tenant_key}",
                            extra={"orchestrator_id": orchestrator_id},
                        )
                    else:
                        logger.debug("[WEBSOCKET] WebSocket manager not available (non-critical)")

                except Exception as ws_error:
                    # Non-blocking - WebSocket failures shouldn't break MCP tool
                    logger.warning(f"[WEBSOCKET] Failed to broadcast event: {ws_error}")

                return {
                    "orchestrator_id": orchestrator_id,
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "project_description": project.description or "",
                    "mission": condensed_mission,
                    "context_budget": orchestrator.context_budget or 150000,
                    "context_used": orchestrator.context_used or 0,
                "agent_discovery_tool": "get_available_agents()",  # Handover 0246c: Reference to discovery tool
                    "field_priorities": field_priorities,
                    "token_reduction_applied": bool(field_priorities),
                    "estimated_tokens": estimated_tokens,
                    "instance_number": orchestrator.instance_number or 1,
                    "thin_client": True,
                }

        except Exception as e:
            logger.error(f"Error fetching orchestrator instructions: {e}", exc_info=True)
            return {
                "error": "INTERNAL_ERROR",
                "message": f"Unexpected error: {e!s}",
                "troubleshooting": [
                    "Check MCP server logs: ~/.giljo_mcp/logs/mcp_adapter.log",
                    "Check API server logs: ~/.giljo_mcp/logs/api.log",
                    "Restart MCP server if issue persists",
                ],
                "severity": "ERROR",
                "contact_support": "support@giljoai.com",
            }


# ========================================================================
# Depth Config Helper Functions (Handover 0281 Phase 3) - REMOVED
# Individual fetch_* functions replaced with monolithic context architecture
# All context fetched via get_orchestrator_instructions() MCP tool
# ========================================================================


# ========================================================================
# Standalone Functions for Testing
# These are test-friendly wrappers that can be imported directly
# ========================================================================


async def health_check() -> dict[str, Any]:
    """
    MCP server health check (standalone for testing).

    Returns:
        Health status dict with server info
    """
    from datetime import datetime, timezone

    return {
        "status": "healthy",
        "server": "giljo-mcp",
        "version": "3.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "connected",
        "message": "GiljoAI MCP server is operational",
    }


async def get_orchestrator_instructions(
    orchestrator_id: str,
    tenant_key: str,
    user_id: Optional[str] = None,  # Handover 0281 Phase 1: User-specific config
    db_manager: "DatabaseManager" = None
) -> dict[str, Any]:
    """
    Fetch orchestrator instructions (standalone for testing).

    This is a test-friendly wrapper around the MCP tool.
    For production use, the MCP tool registered via register_orchestration_tools is used.

    Args:
        orchestrator_id: Orchestrator job UUID
        tenant_key: Tenant isolation key
        user_id: Optional user UUID for fetching user-specific field_priority_config and depth_config (Handover 0281)
        db_manager: Optional DatabaseManager instance (for testing)

    Returns:
        Orchestrator instructions dict
    """
    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.config_manager import get_config

    if db_manager is None:
        # Get database URL from config for test environments
        config = get_config()
        db_url = config.database.database_url
        db_manager = DatabaseManager(database_url=db_url, is_async=True)
    async with db_manager.get_session_async() as session:
        from sqlalchemy import and_, select
        from sqlalchemy.orm import joinedload

        from giljo_mcp.mission_planner import MissionPlanner
        from giljo_mcp.models import AgentTemplate, MCPAgentJob, Product

        try:
            # Validate inputs
            if not orchestrator_id or not orchestrator_id.strip():
                return {"error": "VALIDATION_ERROR", "message": "Orchestrator ID is required"}

            if not tenant_key or not tenant_key.strip():
                return {"error": "VALIDATION_ERROR", "message": "Tenant key is required"}

            # Fetch orchestrator from database with multi-tenant isolation
            result = await session.execute(
                select(MCPAgentJob)
                .options(joinedload(MCPAgentJob.project))
                .where(
                    and_(
                        MCPAgentJob.job_id == orchestrator_id,
                        MCPAgentJob.tenant_key == tenant_key,
                        MCPAgentJob.agent_type == "orchestrator",
                    )
                )
            )
            orchestrator = result.scalar_one_or_none()

            if not orchestrator:
                return {
                    "error": "NOT_FOUND",
                    "message": f"Orchestrator {orchestrator_id} not found for tenant",
                    "troubleshooting": [
                        "Verify orchestrator_id is correct",
                        "Check tenant_key matches project",
                        "Ensure orchestrator was created successfully",
                    ],
                    "severity": "ERROR",
                }

            # Handover 0233: Track mission_read_at timestamp (idempotent)
            # Set timestamp on FIRST read only (doesn't overwrite existing)
            if orchestrator.mission_read_at is None:
                orchestrator.mission_read_at = datetime.now(timezone.utc)
                await session.commit()
                logger.info(
                    f"[MISSION_TRACKING] Set mission_read_at for orchestrator {orchestrator_id}",
                    extra={"orchestrator_id": orchestrator_id, "tenant_key": tenant_key}
                )

                # Handover 0233 Phase 5: Emit WebSocket event for mission_read
                try:
                    # Import websocket manager
                    from api.app import state

                    ws_manager = getattr(state, "websocket_manager", None)

                    if ws_manager:
                        await ws_manager.broadcast_to_tenant(
                            tenant_key=tenant_key,
                            event_type="job:mission_read",
                            data={
                                "job_id": orchestrator_id,
                                "mission_read_at": orchestrator.mission_read_at.isoformat(),
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                        )
                        logger.info(
                            f"[WEBSOCKET] Broadcasted job:mission_read event",
                            extra={
                                "orchestrator_id": orchestrator_id,
                                "tenant_key": tenant_key,
                                "mission_read_at": orchestrator.mission_read_at.isoformat()
                            }
                        )
                except Exception as ws_error:
                    # Non-blocking - WebSocket failures shouldn't break MCP tool
                    logger.warning(
                        f"[WEBSOCKET] Failed to broadcast job:mission_read event: {ws_error}",
                        extra={"orchestrator_id": orchestrator_id}
                    )

            # Get project and product
            project = orchestrator.project
            if not project:
                return {"error": "NOT_FOUND", "message": "Project not found for orchestrator"}

            # Get product with eager loading of relationships (Handover 0281: Fix lazy loading issue)
            if not project.product_id:
                return {"error": "NOT_FOUND", "message": "No product linked to project"}

            result = await session.execute(
                select(Product)
                .options(
                    joinedload(Product.vision_documents),  # Eager load vision documents
                    joinedload(Product.projects)  # Eager load projects
                )
                .where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
            )
            product = result.unique().scalar_one_or_none()

            if not product:
                return {"error": "NOT_FOUND", "message": "Product not found"}

            # Generate condensed mission
            planner = MissionPlanner(db_manager)
            metadata = orchestrator.job_metadata or {}

            # Handover 0281 Phase 1: Fetch user-specific config if user_id provided
            if user_id:
                user_config = await _get_user_config(user_id, tenant_key, session)
                field_priorities = user_config["field_priorities"]
                depth_config = user_config["depth_config"]
                logger.info(
                    "[USER_CONFIG] Applied user-specific configuration to orchestrator instructions",
                    extra={"orchestrator_id": orchestrator_id, "user_id": user_id, "tenant_key": tenant_key}
                )
            else:
                # Fall back to job_metadata or empty dict (existing behavior)
                field_priorities = metadata.get("field_priorities", {})
                depth_config = {}
                logger.debug(
                    "[USER_CONFIG] No user_id provided, using job_metadata field_priorities",
                    extra={"orchestrator_id": orchestrator_id}
                )

            condensed_mission = await planner._build_context_with_priorities(
                product=product, project=project, field_priorities=field_priorities, user_id=user_id
            )

            # Handover 0246c: Agent templates no longer embedded
            # Use get_available_agents() MCP tool instead


            # Calculate token estimate
            estimated_tokens = len(condensed_mission) // 4

            return {
                "orchestrator_id": orchestrator_id,
                "project_id": str(project.id),
                "project_name": project.name,
                "project_description": project.description or "",
                "mission": condensed_mission,
                "context_budget": orchestrator.context_budget or 150000,
                "context_used": orchestrator.context_used or 0,
                "agent_discovery_tool": "get_available_agents()",  # Handover 0246c: Reference to discovery tool
                "field_priorities": field_priorities,
                "token_reduction_applied": bool(field_priorities),
                "estimated_tokens": estimated_tokens,
                "instance_number": orchestrator.instance_number or 1,
                "thin_client": True,
            }

        except Exception as e:
            logger.error(f"Error in get_orchestrator_instructions: {e}", exc_info=True)
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}


async def get_agent_mission(agent_job_id: str, tenant_key: str) -> dict[str, Any]:
    """
    Fetch agent mission (standalone for testing).

    Args:
        agent_job_id: Agent job UUID
        tenant_key: Tenant isolation key

    Returns:
        Agent mission dict
    """
    from giljo_mcp.database import DatabaseManager

    db_manager = DatabaseManager()
    async with db_manager.get_session_async() as session:
        from sqlalchemy import and_, select

        from giljo_mcp.models import MCPAgentJob

        try:
            result = await session.execute(
                select(MCPAgentJob).where(
                    and_(MCPAgentJob.job_id == agent_job_id, MCPAgentJob.tenant_key == tenant_key)
                )
            )
            agent_job = result.scalar_one_or_none()

            if not agent_job:
                return {"error": "NOT_FOUND", "message": f"Agent job {agent_job_id} not found"}

            estimated_tokens = len(agent_job.mission or "") // 4

            return {
                "agent_job_id": agent_job_id,
                "agent_name": agent_job.agent_name,
                "agent_type": agent_job.agent_type,
                "mission": agent_job.mission or "",
                "thin_client": True,
                "estimated_tokens": estimated_tokens,
            }

        except Exception as e:
            logger.error(f"Error in get_agent_mission: {e}", exc_info=True)
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}


async def get_generic_agent_template(
    session: "AsyncSession",
    agent_id: str,
    job_id: str,
    product_id: str,
    project_id: str,
    tenant_key: str,
) -> dict[str, Any]:
    """
    Get generic agent template with injected variables.

    Used by Orchestrator to spawn agents in Generic/Legacy mode.
    Template provides unified protocol for all agent types.

    Handover 0246b: Generic Agent Template Implementation

    Args:
        session: AsyncSession for database operations
        agent_id: UUID of agent instance
        job_id: UUID of job in MCP_AGENT_JOBS
        product_id: UUID of product context
        project_id: UUID of project context
        tenant_key: Tenant isolation key

    Returns:
        {
            "success": true,
            "template": "<rendered prompt>",
            "variables_injected": {
                "agent_id": "...",
                "job_id": "...",
                "product_id": "...",
                "project_id": "...",
                "tenant_key": "..."
            },
            "protocol_version": "1.0",
            "estimated_tokens": 2400
        }
    """
    try:
        from src.giljo_mcp.templates.generic_agent_template import GenericAgentTemplate

        template = GenericAgentTemplate()
        rendered = template.render(
            agent_id=agent_id,
            job_id=job_id,
            product_id=product_id,
            project_id=project_id,
            tenant_key=tenant_key,
        )

        logger.info(
            "Generic agent template rendered",
            extra={
                "agent_id": agent_id,
                "job_id": job_id,
                "template_version": template.version,
                "tenant_key": tenant_key,
            },
        )

        return {
            "success": True,
            "template": rendered,
            "variables_injected": {
                "agent_id": agent_id,
                "job_id": job_id,
                "product_id": product_id,
                "project_id": project_id,
                "tenant_key": tenant_key,
            },
            "protocol_version": template.version,
            "estimated_tokens": len(rendered) // 4,  # Rough estimate
        }

    except Exception as e:
        logger.error(
            f"Failed to render generic agent template: {e}",
            extra={"agent_id": agent_id, "job_id": job_id, "tenant_key": tenant_key},
        )
        return {
            "success": False,
            "error": str(e),
            "agent_id": agent_id,
            "job_id": job_id,
        }


async def spawn_agent_job(
    agent_type: str,
    agent_name: str,
    mission: str,
    project_id: str,
    tenant_key: str,
    parent_job_id: Optional[str] = None,
    db_manager: Optional["DatabaseManager"] = None,
    session: Optional["AsyncSession"] = None,
) -> dict[str, Any]:
    """
    Spawn agent job (standalone for testing).

    Args:
        agent_type: Type of agent
        agent_name: Name of agent
        mission: Agent mission
        project_id: Project UUID
        tenant_key: Tenant isolation key
        parent_job_id: Optional parent job UUID
        db_manager: Optional DatabaseManager instance (for testing)
        session: Optional AsyncSession (for testing with transaction isolation)

    Returns:
        Spawn result dict
    """
    from uuid import uuid4

    from giljo_mcp.database import DatabaseManager
    from giljo_mcp.config_manager import get_config

    # If session is provided, use it directly (for testing with transaction isolation)
    if session is not None:
        return await _spawn_agent_job_impl(
            session, agent_type, agent_name, mission, project_id, tenant_key, parent_job_id
        )

    # Otherwise, create session from db_manager
    if db_manager is None:
        config = get_config()
        db_url = config.database.database_url
        db_manager = DatabaseManager(database_url=db_url, is_async=True)

    async with db_manager.get_session_async() as session:
        return await _spawn_agent_job_impl(
            session, agent_type, agent_name, mission, project_id, tenant_key, parent_job_id
        )


async def _spawn_agent_job_impl(
    session,
    agent_type: str,
    agent_name: str,
    mission: str,
    project_id: str,
    tenant_key: str,
    parent_job_id: Optional[str] = None,
) -> dict[str, Any]:
    """Internal implementation of spawn_agent_job."""
    from uuid import uuid4
    from sqlalchemy import and_, select
    from giljo_mcp.models import MCPAgentJob

    try:
        # ORCHESTRATOR DUPLICATION PREVENTION
        # Check if we're trying to create an orchestrator
        if agent_type == "orchestrator":
            # Query for existing orchestrators in this project with active statuses
            result = await session.execute(
                select(MCPAgentJob).where(
                    and_(
                        MCPAgentJob.project_id == project_id,
                        MCPAgentJob.tenant_key == tenant_key,
                        MCPAgentJob.agent_type == "orchestrator",
                        MCPAgentJob.status.in_(["waiting", "working"])
                    )
                )
            )
            existing_orchestrator = result.scalar_one_or_none()

            if existing_orchestrator:
                # Active orchestrator already exists - prevent duplicate
                logger.warning(
                    f"Orchestrator already exists for project {project_id} with status {existing_orchestrator.status}",
                    extra={
                        "project_id": project_id,
                        "tenant_key": tenant_key,
                        "existing_job_id": existing_orchestrator.job_id,
                        "existing_status": existing_orchestrator.status
                    }
                )
                return {
                    "success": False,
                    "error": f"Orchestrator already exists for this project with status '{existing_orchestrator.status}'. "
                             f"Only one active orchestrator is allowed during staging. Use succession for runtime handover.",
                    "existing_job_id": existing_orchestrator.job_id,
                    "existing_status": existing_orchestrator.status
                }

        # No duplicate found (or not an orchestrator) - proceed with creation
        agent_job_id = str(uuid4())

        agent_job = MCPAgentJob(
            job_id=agent_job_id,
            tenant_key=tenant_key,
            project_id=project_id,
            agent_type=agent_type,
            agent_name=agent_name,
            mission=mission,
            status="waiting",  # Use 'waiting' instead of 'pending'
            context_budget=10000,
            context_used=0,
        )

        session.add(agent_job)
        await session.commit()

        # Generate thin prompt (not full mission)
        thin_prompt = f"""I am {agent_name} for Project.

FETCH MISSION:
mcp__giljo-mcp__get_agent_mission('{agent_job_id}', '{tenant_key}')

Execute mission and report back."""

        mission_tokens = len(mission) // 4
        prompt_tokens = len(thin_prompt) // 4

        return {
            "success": True,
            "agent_job_id": agent_job_id,
            "agent_prompt": thin_prompt,
            "prompt_tokens": prompt_tokens,
            "mission_tokens": mission_tokens,
        }

    except Exception as e:
        logger.error(f"Error in spawn_agent_job: {e}", exc_info=True)
        return {"success": False, "error": f"Failed to spawn agent: {e!s}"}
