"""
Agent Lifecycle Management Tools for GiljoAI MCP
Handles agent operations: ensure, activate, assign_job, decommission
"""

import json
import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp import FastMCP
from sqlalchemy import and_, select, update

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import AgentInteraction, Job, MCPAgentJob, Message, Project, Task
from giljo_mcp.tenant import TenantManager
from giljo_mcp.websocket_client import broadcast_sub_agent_event


logger = logging.getLogger(__name__)


# ============================================================================
# STANDALONE HELPER FUNCTIONS (For Testing and Tenant Isolation)
# ============================================================================


async def launch_agent(
    agent_id: str,
    tenant_key: str,
    session
) -> dict[str, Any]:
    """
    Launch an agent by ID with tenant isolation (testable helper).

    This is a standalone helper function for testing activate_agent logic.

    Args:
        agent_id: Agent job ID to launch
        tenant_key: Tenant isolation key
        session: Database session

    Returns:
        Success/error dictionary
    """
    try:
        # Get the agent with TENANT ISOLATION
        agent_query = select(MCPAgentJob).where(
            and_(
                MCPAgentJob.job_id == agent_id,
                MCPAgentJob.tenant_key == tenant_key
            )
        )
        agent_result = await session.execute(agent_query)
        agent = agent_result.scalar_one_or_none()

        if not agent:
            return {"success": False, "error": "Agent not found or tenant mismatch"}

        # Update agent status to active
        agent.status = "active"
        agent.last_active = datetime.now(timezone.utc)
        await session.commit()

        return {
            "success": True,
            "agent_id": str(agent.job_id),
            "status": "active",
        }

    except Exception as e:
        logger.exception(f"Failed to launch agent: {e}")
        return {"success": False, "error": str(e)}


async def log_interaction_legacy(
    interaction: dict[str, Any],
    tenant_key: str,
    session
) -> dict[str, Any]:
    """
    Log agent interaction with tenant isolation (testable helper).

    This is a simplified version of log_sub_agent_completion logic for testing.

    Args:
        interaction: Interaction data dictionary
        tenant_key: Tenant isolation key
        session: Database session

    Returns:
        Success/error dictionary
    """
    try:
        # Validate tenant matches
        agent_id = interaction.get("agent_id")
        parent_agent_id = interaction.get("parent_agent_id")
        project_id = interaction.get("project_id")

        # Verify project belongs to tenant
        if project_id:
            project_query = select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key
                )
            )
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                return {"success": False, "error": "Project not found or tenant mismatch"}

        # Verify parent agent belongs to tenant (if specified)
        if parent_agent_id:
            parent_query = select(MCPAgentJob).where(
                and_(
                    MCPAgentJob.job_id == parent_agent_id,
                    MCPAgentJob.tenant_key == tenant_key
                )
            )
            parent_result = await session.execute(parent_query)
            parent_agent = parent_result.scalar_one_or_none()

            if not parent_agent:
                return {"success": False, "error": "Parent agent not found or tenant mismatch"}

        # If all checks pass, interaction is valid
        return {"success": True, "message": "Interaction validated"}

    except Exception as e:
        logger.exception(f"Failed to log interaction: {e}")
        return {"success": False, "error": str(e)}


# Helper functions for testing and internal use
async def _ensure_agent(
    project_id: str, agent_name: str, mission: Optional[str] = None, session=None
) -> dict[str, Any]:
    """Internal helper for ensure_agent - used by tests"""
    from giljo_mcp.database import DatabaseManager

    if session is None:
        db_manager = DatabaseManager()
        async with db_manager.get_session_async() as session:
            return await _ensure_agent_with_session(session, project_id, agent_name, mission)
    else:
        return await _ensure_agent_with_session(session, project_id, agent_name, mission)


async def _ensure_agent_with_session(
    session, project_id: str, agent_name: str, mission: Optional[str] = None
) -> dict[str, Any]:
    """Internal helper with session for ensure_agent - Now uses MCPAgentJob"""
    # Check if project exists
    project_query = select(Project).where(Project.id == project_id)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        return {
            "success": False,
            "error": f"Project {project_id} not found",
        }

    # Check if agent job already exists
    agent_query = select(MCPAgentJob).where(
        and_(MCPAgentJob.project_id == project_id, MCPAgentJob.agent_name == agent_name)
    )
    agent_result = await session.execute(agent_query)
    existing_agent = agent_result.scalar_one_or_none()

    if existing_agent:
        return {
            "success": True,
            "agent": agent_name,
            "agent_id": str(existing_agent.job_id),
            "status": existing_agent.status,
            "is_new": False,
            "message": "Returning existing agent job",
        }

    # Create new agent job using AgentJobManager
    from giljo_mcp.agent_job_manager import AgentJobManager

    job_manager = AgentJobManager(tenant_key=project.tenant_key)
    agent_job = await job_manager.create_job(
        agent_type=agent_name,
        mission=mission or f"Agent: {agent_name}",
        project_id=project_id,
        spawned_by=None,  # Human-initiated
        context_chunks=[],
    )

    return {
        "success": True,
        "agent": agent_name,
        "agent_id": str(agent_job.job_id),
        "status": agent_job.status,
        "is_new": True,
        "message": "Agent job created successfully",
    }


async def _decommission_agent(
    agent_name: str, project_id: str, reason: str = "completed", session=None
) -> dict[str, Any]:
    """Internal helper for decommission_agent - used by tests"""
    from giljo_mcp.database import DatabaseManager

    if session is None:
        db_manager = DatabaseManager()
        async with db_manager.get_session_async() as session:
            return await _decommission_agent_with_session(session, agent_name, project_id, reason)
    else:
        return await _decommission_agent_with_session(session, agent_name, project_id, reason)


async def _decommission_agent_with_session(
    session, agent_name: str, project_id: str, reason: str = "completed"
) -> dict[str, Any]:
    """Internal helper with session for decommission_agent - Now uses MCPAgentJob"""
    agent_query = select(MCPAgentJob).where(
        and_(MCPAgentJob.agent_name == agent_name, MCPAgentJob.project_id == project_id)
    )
    agent_result = await session.execute(agent_query)
    agent = agent_result.scalar_one_or_none()

    if not agent:
        return {
            "success": False,
            "error": f"Agent job '{agent_name}' not found in project {project_id}",
        }

    # Use AgentJobManager to decommission properly
    from giljo_mcp.agent_job_manager import AgentJobManager

    project_query = select(Project).where(Project.id == project_id)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        return {
            "success": False,
            "error": f"Project {project_id} not found",
        }

    job_manager = AgentJobManager(tenant_key=project.tenant_key)
    # Decommission requires job to be in 'complete' status first
    if agent.status != "complete":
        agent.status = "complete"
        await session.commit()

    await job_manager.decommission_job(str(agent.job_id))

    return {
        "success": True,
        "agent": agent_name,
        "status": "decommissioned",
        "reason": reason,
    }


async def _get_agent_health(agent_name: Optional[str] = None, session=None) -> dict[str, Any]:
    """Internal helper for agent_health - used by tests"""
    from giljo_mcp.database import DatabaseManager

    if session is None:
        db_manager = DatabaseManager()
        async with db_manager.get_session_async() as session:
            return await _get_agent_health_with_session(session, agent_name)
    else:
        return await _get_agent_health_with_session(session, agent_name)


async def _get_agent_health_with_session(session, agent_name: Optional[str] = None) -> dict[str, Any]:
    """Internal helper with session for agent_health - Now uses MCPAgentJob"""
    if agent_name:
        agent_query = select(MCPAgentJob).where(MCPAgentJob.agent_name == agent_name)
        agent_result = await session.execute(agent_query)
        agent = agent_result.scalar_one_or_none()

        if not agent:
            return {"success": False, "error": f"Agent job '{agent_name}' not found"}

        return {
            "success": True,
            "agent": agent_name,
            "status": agent.status,
            "context_used": 0,  # MCPAgentJob doesn't track context_used
            "last_activity": agent.updated_at.isoformat() if agent.updated_at else None,
        }
    # Return health for all agent jobs
    agents_query = select(MCPAgentJob)
    agents_result = await session.execute(agents_query)
    agents = agents_result.scalars().all()

    return {
        "success": True,
        "total_agents": len(agents),
        "agents": [
            {
                "name": agent.agent_name,
                "status": agent.status,
                "context_used": agent.context_used,
                "project_id": str(agent.project_id),
            }
            for agent in agents
        ],
    }


async def _handoff_agent_work(
    from_agent: str, to_agent: str, project_id: str, context: dict[str, Any], session=None
) -> dict[str, Any]:
    """Internal helper for handoff - used by tests"""
    from giljo_mcp.database import DatabaseManager

    if session is None:
        db_manager = DatabaseManager()
        async with db_manager.get_session_async() as session:
            return await _handoff_agent_work_with_session(session, from_agent, to_agent, project_id, context)
    else:
        return await _handoff_agent_work_with_session(session, from_agent, to_agent, project_id, context)


async def _handoff_agent_work_with_session(
    session, from_agent: str, to_agent: str, project_id: str, context: dict[str, Any]
) -> dict[str, Any]:
    """Internal helper with session for handoff"""
    # Check both agents exist
    from_query = select(MCPAgentJob).where(and_(MCPAgentJob.agent_name == from_agent, MCPAgentJob.project_id == project_id))
    from_result = await session.execute(from_query)
    from_agent_obj = from_result.scalar_one_or_none()

    to_query = select(MCPAgentJob).where(and_(MCPAgentJob.agent_name == to_agent, MCPAgentJob.project_id == project_id))
    to_result = await session.execute(to_query)
    to_agent_obj = to_result.scalar_one_or_none()

    if not from_agent_obj:
        return {"success": False, "error": f"From agent '{from_agent}' not found"}

    if not to_agent_obj:
        return {"success": False, "error": f"To agent '{to_agent}' not found"}

    # Update agent statuses
    from_agent_obj.status = "handed_off"
    to_agent_obj.status = "active"

    await session.commit()

    return {
        "success": True,
        "from_agent": from_agent,
        "to_agent": to_agent,
        "handoff_time": datetime.now(timezone.utc).isoformat(),
        "context_transferred": True,
    }


def register_agent_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register agent management tools with the MCP server"""

    @mcp.tool()
    async def ensure_agent(project_id: str, agent_name: str, mission: Optional[str] = None) -> dict[str, Any]:
        """
        Ensure an agent exists for work on a project (creates if needed, returns if exists)

        IDEMPOTENT: Safe to call multiple times - will not create duplicates.

        Args:
            project_id: UUID of the project
            agent_name: Name of the agent
            mission: Optional mission for the agent

        Returns:
            Agent details and status
        """
        try:
            async with db_manager.get_session_async() as session:
                # Check if project exists
                project_query = select(Project).where(Project.id == project_id)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found",
                    }

                # Check if agent already exists with TENANT ISOLATION
                # Use tenant_key from the project we just fetched
                agent_query = select(MCPAgentJob).where(
                    and_(
                        MCPAgentJob.project_id == project_id,
                        MCPAgentJob.agent_name == agent_name,
                        MCPAgentJob.tenant_key == project.tenant_key  # TENANT ISOLATION
                    )
                )
                agent_result = await session.execute(agent_query)
                existing_agent = agent_result.scalar_one_or_none()

                if existing_agent:
                    # Agent exists, return it
                    logger.info(f"Agent '{agent_name}' already exists in project {project_id}")
                    return {
                        "success": True,
                        "agent": agent_name,
                        "agent_id": str(existing_agent.job_id),
                        "status": existing_agent.status,
                        "is_new": False,
                        "message": "Returning existing agent",
                    }

                # Create new agent
                agent = Agent(
                    project_id=project.id,
                    name=agent_name,
                    role=agent_name,
                    status="idle",
                    mission=mission,
                    context_used=0,
                    created_at=datetime.now(timezone.utc),
                )
                session.add(agent)
                await session.commit()

                logger.info(f"Created agent '{agent_name}' for project {project_id}")

                return {
                    "success": True,
                    "agent": agent_name,
                    "agent_id": str(agent.job_id),
                    "status": "idle",
                    "is_new": True,
                    "message": "Agent created successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to ensure agent: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def activate_agent(project_id: str, agent_name: str, mission: Optional[str] = None) -> dict[str, Any]:
        """
        Activate orchestrator agent - STARTS WORKING IMMEDIATELY

        This function is ORCHESTRATOR-SPECIFIC and triggers immediate discovery workflow.
        For worker agents, use ensure_agent() instead.

        Args:
            project_id: UUID of the project
            agent_name: Name of the agent (typically "orchestrator")
            mission: Optional mission override

        Returns:
            Activation status and agent details
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get project first to obtain tenant_key for isolation
                project_query = select(Project).where(Project.id == project_id)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}

                tenant_key = project.tenant_key

                # First ensure agent exists
                ensure_result = await ensure_agent(project_id, agent_name, mission)

                if not ensure_result["success"]:
                    return ensure_result

                agent_id = ensure_result["agent_id"]

                # Get the agent with TENANT ISOLATION
                agent_query = select(MCPAgentJob).where(
                    and_(
                        MCPAgentJob.job_id == agent_id,
                        MCPAgentJob.tenant_key == tenant_key  # TENANT ISOLATION
                    )
                )
                agent_result = await session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    return {"success": False, "error": "Agent not found after creation or tenant mismatch"}

                # Update agent status to active
                agent.status = "active"
                agent.last_active = datetime.now(timezone.utc)

                # Create discovery job for orchestrator
                if agent_name.lower() == "orchestrator":
                    discovery_job = Job(
                        agent_id=agent.job_id,
                        type="discovery",
                        status="active",
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(discovery_job)

                    # Create initial discovery task
                    discovery_task = Task(
                        job_id=discovery_job.id,
                        description="Analyze project mission and plan implementation",
                        status="pending",
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(discovery_task)

                await session.commit()

                logger.info(f"Activated agent '{agent_name}' for immediate work")

                return {
                    "success": True,
                    "agent": agent_name,
                    "agent_id": str(agent.job_id),
                    "status": "active",
                    "workflow": ("discovery" if agent_name.lower() == "orchestrator" else "ready"),
                    "message": f"Agent activated and {'started discovery' if agent_name.lower() == 'orchestrator' else 'ready for work'}",
                }

        except Exception as e:
            logger.exception(f"Failed to activate agent: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def assign_job(
        agent_name: str,
        job_type: str,
        project_id: str,
        tasks: Optional[list[str]] = None,
        scope_boundary: Optional[str] = None,
        vision_alignment: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Assign a job to an agent with task descriptions and optional scope/vision alignment

        IDEMPOTENT: Updates existing active job if present, creates new one if not.

        Args:
            agent_name: Name of the agent to assign the job to
            job_type: Type of job (e.g., 'analysis', 'implementation', 'testing')
            project_id: UUID of the project
            tasks: List of task DESCRIPTIONS (not IDs) - what the agent should do
            scope_boundary: Clear boundaries of what agent should/shouldn't do
            vision_alignment: How this job aligns with product vision

        Returns:
            Job assignment details
        """
        try:
            async with db_manager.get_session_async() as session:
                # Find the agent
                agent_query = select(MCPAgentJob).where(and_(MCPAgentJob.project_id == project_id, MCPAgentJob.agent_name == agent_name))
                agent_result = await session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    # Try to create the agent first
                    ensure_result = await ensure_agent(project_id, agent_name)
                    if not ensure_result["success"]:
                        return ensure_result

                    # Re-fetch the agent
                    agent_result = await session.execute(agent_query)
                    agent = agent_result.scalar_one_or_none()

                    if not agent:
                        return {"success": False, "error": "Failed to create agent"}

                # Check for existing active job
                job_query = select(Job).where(and_(Job.agent_id == agent.job_id, Job.status == "active"))
                job_result = await session.execute(job_query)
                existing_job = job_result.scalar_one_or_none()

                if existing_job:
                    # Update existing job
                    existing_job.type = job_type
                    existing_job.scope_boundary = scope_boundary
                    existing_job.vision_alignment = vision_alignment
                    job = existing_job
                    logger.info(f"Updated existing job for agent '{agent_name}'")
                else:
                    # Create new job
                    job = Job(
                        agent_id=agent.job_id,
                        type=job_type,
                        status="active",
                        scope_boundary=scope_boundary,
                        vision_alignment=vision_alignment,
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(job)
                    await session.flush()
                    logger.info(f"Created new job for agent '{agent_name}'")

                # Create tasks if provided
                task_ids = []
                if tasks:
                    for task_desc in tasks:
                        task = Task(
                            job_id=job.id,
                            description=task_desc,
                            status="pending",
                            created_at=datetime.now(timezone.utc),
                        )
                        session.add(task)
                        await session.flush()
                        task_ids.append(str(task.id))

                # Update agent status
                agent.status = "active"
                agent.last_active = datetime.now(timezone.utc)

                await session.commit()

                return {
                    "success": True,
                    "agent": agent_name,
                    "job_id": str(job.id),
                    "job_type": job_type,
                    "tasks_created": len(task_ids),
                    "task_ids": task_ids,
                    "scope": scope_boundary,
                    "vision": vision_alignment,
                }

        except Exception as e:
            logger.exception(f"Failed to assign job: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def handoff(from_agent: str, to_agent: str, project_id: str, context: dict[str, Any]) -> dict[str, Any]:
        """
        Transfer work from one agent to another

        Args:
            from_agent: Name of the agent handing off work
            to_agent: Name of the agent receiving work
            project_id: UUID of the project
            context: Context dictionary with handoff information

        Returns:
            Handoff confirmation
        """
        try:
            async with db_manager.get_session_async() as session:
                # Find both agents
                from_query = select(Agent).where(and_(Agent.project_id == project_id, Agent.name == from_agent))
                from_result = await session.execute(from_query)
                from_agent_obj = from_result.scalar_one_or_none()

                if not from_agent_obj:
                    return {
                        "success": False,
                        "error": f"Source agent '{from_agent}' not found",
                    }

                # Ensure target agent exists
                ensure_result = await ensure_agent(project_id, to_agent)
                if not ensure_result["success"]:
                    return ensure_result

                to_query = select(Agent).where(and_(Agent.project_id == project_id, Agent.name == to_agent))
                to_result = await session.execute(to_query)
                to_agent_obj = to_result.scalar_one_or_none()

                if not to_agent_obj:
                    return {
                        "success": False,
                        "error": f"Target agent '{to_agent}' not found",
                    }

                # Create handoff message
                handoff_message = Message(
                    project_id=project_id,
                    from_agent=from_agent,
                    to_agent=to_agent,
                    type="handoff",
                    subject=f"Handoff from {from_agent} to {to_agent}",
                    content=json.dumps(
                        {
                            "handoff_from": from_agent,
                            "handoff_to": to_agent,
                            "context": context,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    ),
                    priority="high",
                    status="pending",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(handoff_message)

                # Update agent statuses
                from_agent_obj.status = "idle"
                to_agent_obj.status = "active"
                to_agent_obj.last_active = datetime.now(timezone.utc)

                await session.commit()

                logger.info(f"Handoff from '{from_agent}' to '{to_agent}' completed")

                return {
                    "success": True,
                    "from_agent": from_agent,
                    "to_agent": to_agent,
                    "message_id": str(handoff_message.id),
                    "context_transferred": True,
                }

        except Exception as e:
            logger.exception(f"Failed to perform handoff: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def agent_health(agent_name: Optional[str] = None) -> dict[str, Any]:
        """
        Check agent health and context usage

        Args:
            agent_name: Optional specific agent name to check

        Returns:
            Health status and metrics
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get current tenant
                tenant_key = tenant_manager.get_current_tenant()
                if not tenant_key:
                    return {
                        "success": False,
                        "error": "No active project. Use switch_project first.",
                    }

                # Find project by tenant key
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Build agent query
                agent_query = select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)

                if agent_name:
                    agent_query = agent_query.where(Agent.name == agent_name)

                agent_result = await session.execute(agent_query)
                agents = agent_result.scalars().all()

                if not agents:
                    return {
                        "success": False,
                        "error": f"No agents found{f' with name {agent_name}' if agent_name else ''}",
                    }

                health_data = []
                for agent in agents:
                    # Count pending messages
                    message_query = select(Message).where(
                        and_(Message.to_agent == agent.agent_name, Message.status == "pending")
                    )
                    message_result = await session.execute(message_query)
                    pending_messages = len(message_result.scalars().all())

                    # Get active job
                    job_query = select(Job).where(and_(Job.agent_id == agent.job_id, Job.status == "active"))
                    job_result = await session.execute(job_query)
                    active_job = job_result.scalar_one_or_none()

                    health_data.append(
                        {
                            "name": agent.agent_name,
                            "status": agent.status,
                            "context_used": agent.context_used,
                            "pending_messages": pending_messages,
                            "active_job": active_job.type if active_job else None,
                            "last_active": (agent.last_active.isoformat() if agent.last_active else None),
                        }
                    )

                return {
                    "success": True,
                    "project_context_usage": f"{project.context_used}/{project.context_budget}",
                    "agents": health_data,
                }

        except Exception as e:
            logger.exception(f"Failed to check agent health: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def decommission_agent(agent_name: str, project_id: str, reason: str = "completed") -> dict[str, Any]:
        """
        Gracefully end an agent's work

        Args:
            agent_name: Name of the agent to decommission
            project_id: UUID of the project
            reason: Reason for decommissioning (completed, failed, cancelled)

        Returns:
            Decommission confirmation
        """
        try:
            async with db_manager.get_session_async() as session:
                # Find the agent
                agent_query = select(MCPAgentJob).where(and_(MCPAgentJob.project_id == project_id, MCPAgentJob.agent_name == agent_name))
                agent_result = await session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    return {
                        "success": False,
                        "error": f"Agent '{agent_name}' not found in project",
                    }

                # Complete any active jobs
                job_update = (
                    update(Job)
                    .where(Job.agent_id == agent.job_id, Job.status == "active")
                    .values(
                        status="completed" if reason == "completed" else reason,
                        completed_at=datetime.now(timezone.utc),
                    )
                )
                await session.execute(job_update)

                # Update agent status
                agent.status = "decommissioned"
                agent.decommission_reason = reason

                await session.commit()

                logger.info(f"Decommissioned agent '{agent_name}' (reason: {reason})")

                return {
                    "success": True,
                    "agent": agent_name,
                    "status": "decommissioned",
                    "reason": reason,
                    "context_used": agent.context_used,
                }

        except Exception as e:
            logger.exception(f"Failed to decommission agent: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def spawn_and_log_sub_agent(
        project_id: str,
        parent_agent_name: str,
        sub_agent_name: str,
        mission: str,
        meta_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Log the spawning of a sub-agent (native Claude Code sub-agent).
        Creates an interaction record for tracking parent-child relationships.

        Args:
            project_id: UUID of the project
            parent_agent_name: Name of the parent agent spawning the sub-agent
            sub_agent_name: Name of the sub-agent being spawned
            mission: Mission/task for the sub-agent
            meta_data: Optional metadata about the spawn

        Returns:
            Interaction details including interaction_id for later completion
        """
        try:
            async with db_manager.get_session_async() as session:
                # Find the parent agent
                parent_query = select(Agent).where(
                    and_(Agent.project_id == project_id, Agent.name == parent_agent_name)
                )
                parent_result = await session.execute(parent_query)
                parent_agent = parent_result.scalar_one_or_none()

                if not parent_agent:
                    # Try to create the parent agent first
                    ensure_result = await ensure_agent(project_id, parent_agent_name)
                    if not ensure_result["success"]:
                        return {
                            "success": False,
                            "error": f"Parent agent '{parent_agent_name}' not found and could not be created",
                        }

                    # Re-fetch the parent agent
                    parent_result = await session.execute(parent_query)
                    parent_agent = parent_result.scalar_one_or_none()

                    if not parent_agent:
                        return {
                            "success": False,
                            "error": "Failed to create parent agent",
                        }

                # Get project for tenant key
                project_query = select(Project).where(Project.id == project_id)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found",
                    }

                # Create the interaction record
                interaction = AgentInteraction(
                    tenant_key=project.tenant_key,
                    project_id=project_id,
                    parent_agent_id=parent_agent.job_id,
                    sub_agent_name=sub_agent_name,
                    interaction_type="SPAWN",
                    mission=mission,
                    start_time=datetime.now(timezone.utc),
                    meta_data=meta_data or {},
                )
                session.add(interaction)

                # Update parent agent context usage (estimate)
                parent_agent.context_used += 500  # Estimate for spawn overhead

                await session.commit()

                logger.info(f"Logged sub-agent spawn: {parent_agent_name} -> {sub_agent_name}")

                # Broadcast WebSocket event
                await broadcast_sub_agent_event(
                    "spawned",
                    interaction_id=str(interaction.id),
                    parent_agent_name=parent_agent_name,
                    sub_agent_name=sub_agent_name,
                    project_id=project_id,
                    mission=mission,
                    start_time=interaction.start_time.isoformat(),
                    meta_data=meta_data,
                )

                return {
                    "success": True,
                    "interaction_id": str(interaction.id),
                    "parent_agent": parent_agent_name,
                    "sub_agent": sub_agent_name,
                    "mission": mission,
                    "start_time": interaction.start_time.isoformat(),
                    "message": f"Sub-agent '{sub_agent_name}' spawn logged successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to log sub-agent spawn: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def log_sub_agent_completion(
        interaction_id: str,
        result: Optional[str] = None,
        tokens_used: Optional[int] = None,
        error_message: Optional[str] = None,
        meta_data: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """
        Log the completion of a sub-agent task.
        Updates the interaction record with results and metrics.

        Args:
            interaction_id: UUID of the interaction record from spawn_and_log_sub_agent
            result: Result/output from the sub-agent (if successful)
            tokens_used: Number of tokens consumed by the sub-agent
            error_message: Error message if sub-agent failed
            meta_data: Optional additional metadata about completion

        Returns:
            Updated interaction details including duration
        """
        try:
            async with db_manager.get_session_async() as session:
                # Find the interaction record
                interaction_query = select(AgentInteraction).where(AgentInteraction.id == interaction_id)
                interaction_result = await session.execute(interaction_query)
                interaction = interaction_result.scalar_one_or_none()

                if not interaction:
                    return {
                        "success": False,
                        "error": f"Interaction {interaction_id} not found",
                    }

                # Check if already completed
                if interaction.end_time:
                    return {
                        "success": False,
                        "error": f"Interaction {interaction_id} already completed",
                    }

                # Update interaction record
                end_time = datetime.now(timezone.utc)
                interaction.end_time = end_time
                interaction.duration_seconds = int((end_time - interaction.start_time).total_seconds())
                interaction.tokens_used = tokens_used

                # Set interaction type based on success/failure
                if error_message:
                    interaction.interaction_type = "ERROR"
                    interaction.error_message = error_message
                else:
                    interaction.interaction_type = "COMPLETE"
                    interaction.result = result

                # Merge metadata
                if meta_data:
                    existing_meta = interaction.meta_data or {}
                    existing_meta.update(meta_data)
                    interaction.meta_data = existing_meta

                # Update parent agent context usage if tokens provided
                if tokens_used and interaction.parent_agent_id:
                    # TENANT ISOLATION: Filter by tenant_key from interaction
                    parent_query = select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.job_id == interaction.parent_agent_id,
                            MCPAgentJob.tenant_key == interaction.tenant_key
                        )
                    )
                    parent_result = await session.execute(parent_query)
                    parent_agent = parent_result.scalar_one_or_none()

                    if parent_agent:
                        parent_agent.context_used += tokens_used

                        # Also update project context usage with TENANT ISOLATION
                        project_query = select(Project).where(
                            and_(
                                Project.id == interaction.project_id,
                                Project.tenant_key == interaction.tenant_key
                            )
                        )
                        project_result = await session.execute(project_query)
                        project = project_result.scalar_one_or_none()

                        if project:
                            project.context_used += tokens_used

                await session.commit()

                status = "error" if error_message else "completed"
                logger.info(f"Logged sub-agent completion: {interaction.sub_agent_name} ({status})")

                # Get parent agent name for WebSocket event with TENANT ISOLATION
                parent_agent_name = "unknown"
                if interaction.parent_agent_id:
                    parent_query = select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.job_id == interaction.parent_agent_id,
                            MCPAgentJob.tenant_key == interaction.tenant_key
                        )
                    )
                    parent_result = await session.execute(parent_query)
                    parent_agent = parent_result.scalar_one_or_none()
                    if parent_agent:
                        parent_agent_name = parent_agent.agent_name

                # Broadcast WebSocket event
                await broadcast_sub_agent_event(
                    status,  # "completed" or "error"
                    interaction_id=interaction_id,
                    sub_agent_name=interaction.sub_agent_name,
                    parent_agent_name=parent_agent_name,
                    project_id=str(interaction.project_id),
                    status=status,
                    duration_seconds=interaction.duration_seconds,
                    tokens_used=tokens_used,
                    result=result,
                    error_message=error_message,
                    meta_data=meta_data,
                )

                return {
                    "success": True,
                    "interaction_id": interaction_id,
                    "sub_agent": interaction.sub_agent_name,
                    "status": status,
                    "duration_seconds": interaction.duration_seconds,
                    "tokens_used": tokens_used,
                    "end_time": interaction.end_time.isoformat(),
                    "message": f"Sub-agent '{interaction.sub_agent_name}' completion logged",
                }

        except Exception as e:
            logger.exception(f"Failed to log sub-agent completion: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Agent management tools registered")
