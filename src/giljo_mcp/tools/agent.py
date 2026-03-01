"""
Agent Lifecycle Management Tools for GiljoAI MCP
Handles agent operations: ensure, activate, assign_job, decommission
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, select

from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


logger = logging.getLogger(__name__)


# ============================================================================
# STANDALONE HELPER FUNCTIONS (For Testing and Tenant Isolation)
# ============================================================================


async def launch_agent(agent_id: str, tenant_key: str, session) -> dict[str, Any]:
    """
    Launch an agent by ID with tenant isolation (testable helper).

    This is a standalone helper function for testing activate_agent logic.

    Args:
        agent_id: Agent execution UUID to launch (executor identity)
        tenant_key: Tenant isolation key
        session: Database session

    Returns:
        Success/error dictionary
    """
    try:
        # Get the agent execution with TENANT ISOLATION
        agent_query = select(AgentExecution).where(
            and_(AgentExecution.agent_id == agent_id, AgentExecution.tenant_key == tenant_key)
        )
        agent_result = await session.execute(agent_query)
        agent = agent_result.scalar_one_or_none()

        if not agent:
            raise ResourceNotFoundError("Agent not found or tenant mismatch")

        # Update agent execution status to working
        agent.status = "working"
        agent.last_progress_at = datetime.now(timezone.utc)
        await session.commit()

        return {
            "agent_id": str(agent.agent_id),
            "status": "working",
        }

    except Exception:
        logger.exception("Failed to launch agent")
        raise


async def log_interaction_legacy(interaction: dict[str, Any], tenant_key: str, session) -> dict[str, Any]:
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
        parent_agent_id = interaction.get("parent_agent_id")
        project_id = interaction.get("project_id")

        # Verify project belongs to tenant
        if project_id:
            project_query = select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError("Project not found or tenant mismatch")

        # Verify parent agent belongs to tenant (if specified)
        if parent_agent_id:
            parent_query = select(AgentExecution).where(
                and_(AgentExecution.agent_id == parent_agent_id, AgentExecution.tenant_key == tenant_key)
            )
            parent_result = await session.execute(parent_query)
            parent_agent = parent_result.scalar_one_or_none()

            if not parent_agent:
                raise ResourceNotFoundError("Parent agent not found or tenant mismatch")

        # If all checks pass, interaction is valid
        return None

    except Exception:
        logger.exception("Failed to log interaction")
        raise


# Helper functions for testing and internal use
async def _ensure_agent(
    project_id: str, agent_name: str, mission: Optional[str] = None, tenant_key: Optional[str] = None, session=None
) -> dict[str, Any]:
    """Internal helper for ensure_agent - used by tests"""
    from giljo_mcp.database import DatabaseManager

    if session is None:
        db_manager = DatabaseManager()
        async with db_manager.get_session_async() as db_session:
            return await _ensure_agent_with_session(db_session, project_id, agent_name, mission, tenant_key)
    else:
        return await _ensure_agent_with_session(session, project_id, agent_name, mission, tenant_key)


async def _ensure_agent_with_session(
    session, project_id: str, agent_name: str, mission: Optional[str] = None, tenant_key: Optional[str] = None
) -> dict[str, Any]:
    """Internal helper with session for ensure_agent - Creates AgentJob + AgentExecution"""
    from uuid import uuid4

    # TENANT ISOLATION: Scope Project lookup by tenant_key when provided (Phase D audit fix)
    if tenant_key:
        project_query = select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
    else:
        project_query = select(Project).where(Project.id == project_id)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        return {
            "success": False,
            "error": f"Project {project_id} not found",
        }

    # Check if agent job already exists (by project_id + job_type)
    job_query = select(AgentJob).where(
        and_(
            AgentJob.project_id == project_id,
            AgentJob.job_type == agent_name,
            AgentJob.tenant_key == project.tenant_key,
        )
    )
    job_result = await session.execute(job_query)
    existing_job = job_result.scalar_one_or_none()

    if existing_job:
        # Return existing job with latest execution
        execution_query = (
            select(AgentExecution)
            .where(and_(AgentExecution.job_id == existing_job.job_id, AgentExecution.tenant_key == project.tenant_key))
            .order_by(AgentExecution.started_at.desc())
        )
        execution_result = await session.execute(execution_query)
        existing_execution = execution_result.first()

        if existing_execution:
            execution = existing_execution[0]
            return {
                "success": True,
                "agent": agent_name,
                "job_id": str(existing_job.job_id),
                "agent_id": str(execution.agent_id),
                "status": existing_job.status,
                "is_new": False,
                "message": "Returning existing agent job",
            }

    # Create new agent job (work order)
    job_id = str(uuid4())
    agent_id = str(uuid4())

    agent_job = AgentJob(
        job_id=job_id,
        tenant_key=project.tenant_key,
        project_id=project_id,
        mission=mission or f"Agent: {agent_name}",
        job_type=agent_name,
        status="active",
        job_metadata={},
    )
    session.add(agent_job)
    await session.flush()

    # Create agent execution (executor instance)
    agent_execution = AgentExecution(
        agent_id=agent_id,
        job_id=job_id,
        tenant_key=project.tenant_key,
        agent_display_name=agent_name,
        status="waiting",
        agent_name=agent_name,
        tool_type="claude-code",
    )
    session.add(agent_execution)
    await session.commit()

    return {
        "success": True,
        "agent": agent_name,
        "job_id": job_id,
        "agent_id": agent_id,
        "status": agent_job.status,
        "is_new": True,
        "message": "Agent job created successfully",
    }


async def _decommission_agent(
    agent_name: str, project_id: str, reason: str = "completed", tenant_key: Optional[str] = None, session=None
) -> dict[str, Any]:
    """Internal helper for decommission_agent - used by tests"""
    from giljo_mcp.database import DatabaseManager

    if session is None:
        db_manager = DatabaseManager()
        async with db_manager.get_session_async() as db_session:
            return await _decommission_agent_with_session(db_session, agent_name, project_id, reason, tenant_key)
    else:
        return await _decommission_agent_with_session(session, agent_name, project_id, reason, tenant_key)


async def _decommission_agent_with_session(
    session, agent_name: str, project_id: str, reason: str = "completed", tenant_key: Optional[str] = None
) -> dict[str, Any]:
    """Internal helper with session for decommission_agent - Updates AgentExecution status"""
    # TENANT ISOLATION: Scope Project lookup by tenant_key when provided (Phase D audit fix)
    if tenant_key:
        project_query = select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
    else:
        project_query = select(Project).where(Project.id == project_id)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        return {
            "success": False,
            "error": f"Project {project_id} not found",
        }

    # Find agent execution by agent_name pattern (matches agent_display_name or agent_name)
    execution_query = (
        select(AgentExecution)
        .where(and_(AgentExecution.tenant_key == project.tenant_key, AgentExecution.agent_name.like(f"{agent_name}%")))
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(AgentJob.project_id == project_id)
    )
    execution_result = await session.execute(execution_query)
    execution = execution_result.scalar_one_or_none()

    if not execution:
        return {
            "success": False,
            "error": f"Agent execution '{agent_name}' not found in project {project_id}",
        }

    # Update execution status to decommissioned
    execution.status = "decommissioned"

    # Get the parent job
    job_query = select(AgentJob).where(
        and_(AgentJob.job_id == execution.job_id, AgentJob.tenant_key == project.tenant_key)
    )
    job_result = await session.execute(job_query)
    agent_job = job_result.scalar_one_or_none()

    # Check if all executions for this job are done
    if agent_job:
        all_executions_query = select(AgentExecution).where(
            and_(AgentExecution.job_id == agent_job.job_id, AgentExecution.tenant_key == project.tenant_key)
        )
        all_executions_result = await session.execute(all_executions_query)
        all_executions = all_executions_result.scalars().all()

        # If all executions are decommissioned, mark job as completed
        if all(ex.status == "decommissioned" for ex in all_executions):
            agent_job.status = "completed"

    await session.commit()

    return {
        "success": True,
        "agent": agent_name,
        "status": "decommissioned",
        "reason": reason,
    }


async def _get_agent_health(
    agent_name: Optional[str] = None, tenant_key: Optional[str] = None, session=None
) -> dict[str, Any]:
    """Internal helper for agent_health - used by tests"""
    from giljo_mcp.database import DatabaseManager

    if session is None:
        db_manager = DatabaseManager()
        async with db_manager.get_session_async() as db_session:
            return await _get_agent_health_with_session(db_session, agent_name, tenant_key)
    else:
        return await _get_agent_health_with_session(session, agent_name, tenant_key)


async def _get_agent_health_with_session(
    session, agent_name: Optional[str] = None, tenant_key: Optional[str] = None
) -> dict[str, Any]:
    """Internal helper with session for agent_health - Queries AgentExecution table"""
    if agent_name:
        # TENANT ISOLATION: Filter by tenant_key when provided (Phase D audit fix)
        conditions = [AgentExecution.agent_name.like(f"{agent_name}%")]
        if tenant_key:
            conditions.append(AgentExecution.tenant_key == tenant_key)
        execution_query = select(AgentExecution).where(and_(*conditions))
        execution_result = await session.execute(execution_query)
        execution = execution_result.scalar_one_or_none()

        if not execution:
            raise ResourceNotFoundError(f"Agent execution '{agent_name}' not found")

        return {
            "agent": agent_name,
            "status": execution.status,
            "last_activity": execution.last_progress_at.isoformat() if execution.last_progress_at else None,
            "job_id": str(execution.job_id),
        }

    # Return health for all agent executions
    # TENANT ISOLATION: Filter by tenant_key when provided (Phase D audit fix)
    if tenant_key:
        executions_query = select(AgentExecution).where(AgentExecution.tenant_key == tenant_key)
    else:
        executions_query = select(AgentExecution)
    executions_result = await session.execute(executions_query)
    executions = executions_result.scalars().all()

    # Get associated jobs for project_id
    agents_data = []
    for execution in executions:
        # TENANT ISOLATION: Filter by tenant_key when provided (Phase D audit fix)
        if tenant_key:
            job_query = select(AgentJob).where(
                and_(AgentJob.job_id == execution.job_id, AgentJob.tenant_key == tenant_key)
            )
        else:
            job_query = select(AgentJob).where(AgentJob.job_id == execution.job_id)
        job_result = await session.execute(job_query)
        job = job_result.scalar_one_or_none()

        agents_data.append(
            {
                "name": execution.agent_name,
                "status": execution.status,
                "project_id": str(job.project_id) if job else None,
            }
        )

    return {
        "total_agents": len(executions),
        "agents": agents_data,
    }


async def _handoff_agent_work(
    from_agent: str,
    to_agent: str,
    project_id: str,
    context: dict[str, Any],
    tenant_key: Optional[str] = None,
    session=None,
) -> dict[str, Any]:
    """Internal helper for handoff - used by tests"""
    from giljo_mcp.database import DatabaseManager

    if session is None:
        db_manager = DatabaseManager()
        async with db_manager.get_session_async() as db_session:
            return await _handoff_agent_work_with_session(
                db_session, from_agent, to_agent, project_id, context, tenant_key
            )
    else:
        return await _handoff_agent_work_with_session(session, from_agent, to_agent, project_id, context, tenant_key)


async def _handoff_agent_work_with_session(
    session,
    from_agent: str,
    to_agent: str,
    project_id: str,
    context: dict[str, Any],
    tenant_key: Optional[str] = None,
) -> dict[str, Any]:
    """Internal helper with session for handoff - Creates successor AgentExecution"""
    # TENANT ISOLATION: Scope Project lookup by tenant_key when provided (Phase D audit fix)
    if tenant_key:
        project_query = select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
    else:
        project_query = select(Project).where(Project.id == project_id)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        raise ResourceNotFoundError(f"Project {project_id} not found")

    # Find from_agent execution (match exact agent_name)
    from_query = (
        select(AgentExecution)
        .where(and_(AgentExecution.agent_name == from_agent, AgentExecution.tenant_key == project.tenant_key))
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(AgentJob.project_id == project_id)
    )
    from_result = await session.execute(from_query)
    from_execution = from_result.scalar_one_or_none()

    if not from_execution:
        raise ResourceNotFoundError(f"From agent '{from_agent}' not found")

    # Find to_agent execution (match exact agent_name)
    to_query = (
        select(AgentExecution)
        .where(and_(AgentExecution.agent_name == to_agent, AgentExecution.tenant_key == project.tenant_key))
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(AgentJob.project_id == project_id)
    )
    to_result = await session.execute(to_query)
    to_execution = to_result.scalar_one_or_none()

    if not to_execution:
        raise ResourceNotFoundError(f"To agent '{to_agent}' not found")

    # Update execution statuses
    from_execution.status = "complete"
    from_execution.completed_at = datetime.now(timezone.utc)

    to_execution.status = "working"
    to_execution.spawned_by = from_execution.agent_id
    to_execution.started_at = datetime.now(timezone.utc)

    await session.commit()

    return {
        "from_agent": from_agent,
        "to_agent": to_agent,
        "handoff_time": datetime.now(timezone.utc).isoformat(),
        "context_transferred": True,
    }
