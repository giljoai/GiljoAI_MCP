"""
Agent Job Status Update Tool for GiljoAI MCP

Handover 0066: Agent Self-Navigation for Kanban Board
Enables agents to move themselves between Kanban columns by updating their job status.

Handover 0366c: MCP Tool Standardization
Adds semantic clarity with separate tools for job (WHAT) vs agent (WHO) queries.

This tool supports the 4-column Kanban workflow:
- Pending: Jobs created, waiting for agent to start
- Active: Jobs in progress (agent working)
- Completed: Jobs finished successfully
- Blocked: Jobs failed or waiting for feedback

NO drag-drop functionality - agents move themselves using this MCP tool.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.agent_job_manager import AgentJobManager
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

# Valid statuses for AgentJob (matches database check constraint)
# Note: AgentJob supports: active, completed, cancelled
# AgentExecution has different statuses: waiting, working, blocked, complete, cancelled, failed, decommissioned
VALID_STATUSES = {"active", "completed", "cancelled"}


# Module-level state holder
class _AgentJobStatusState:
    """State holder to avoid global statement."""

    db_manager: Optional[DatabaseManager] = None
    job_manager: Optional[AgentJobManager] = None
    test_session: Optional[Any] = None  # AsyncSession for testing


def init_for_testing(
    db_manager: DatabaseManager,
    test_session: Optional[Any] = None,
    tenant_manager: Optional[TenantManager] = None,
):
    """
    Initialize module-level variables for testing.

    This function is called by tests to initialize the module without going through
    the full MCP registration process.

    Args:
        db_manager: Database manager instance for testing
        test_session: Optional AsyncSession for transaction-based test isolation
        tenant_manager: TenantManager instance for testing (required for AgentJobManager)
    """
    _AgentJobStatusState.db_manager = db_manager
    if tenant_manager is None:
        raise ValueError("tenant_manager is required for initializing AgentJobManager")
    _AgentJobStatusState.job_manager = AgentJobManager(db_manager, tenant_manager)
    _AgentJobStatusState.test_session = test_session


async def get_job_status(
    job_id: str,
    tenant_key: str,
    db_manager: Optional[DatabaseManager] = None,
) -> dict[str, Any]:
    """
    Query work order status (AgentJob table).

    This tool queries the AgentJob table to retrieve the status of a work order.
    Use this when you need to know the overall status of a job/mission.

    The job_id represents the WHAT (work order) - it persists across agent succession.
    Multiple executions (agents) can work on the same job over time.

    Args:
        job_id: Job identifier (UUID of work order)
        tenant_key: Tenant key for multi-tenant isolation
        db_manager: Optional database manager (uses module-level if not provided)

    Returns:
        Dict with success status and job data:
        - job_id: Work order UUID
        - status: Job status (active, completed, cancelled)
        - job_type: Type of job (orchestrator, implementer, etc.)
        - created_at: Timestamp when job was created
        - completed_at: Timestamp when job completed (if applicable)
        - executions: Optional list of all execution instances

    Example:
        # Query job status
        result = await get_job_status(
            job_id="uuid-of-job",
            tenant_key="tenant-key"
        )
        # Returns: {"success": true, "job_id": "...", "status": "active", ...}

    Handover 0366c: Semantic clarification
    - job_id = work order (WHAT) - persistent across succession
    - Response includes execution history to show all agents who worked
    """
    # Use provided db_manager or fall back to module-level
    db_mgr = db_manager if db_manager is not None else _AgentJobStatusState.db_manager

    if db_mgr is None:
        raise RuntimeError("get_job_status called before registration and no db_manager provided")

    try:
        # Input validation
        if not job_id:
            logger.error("Empty job_id provided to get_job_status")
            return {
                "success": False,
                "error": "job_id cannot be empty",
            }

        if not tenant_key:
            logger.error("Empty tenant_key provided to get_job_status")
            return {
                "success": False,
                "error": "tenant_key cannot be empty",
            }

        # Use test session if available (for transaction isolation in tests)
        # Otherwise create new session
        if _AgentJobStatusState.test_session is not None:
            session = _AgentJobStatusState.test_session
            # Process query directly without context manager (test session managed externally)
            return await _get_job_status_impl(session, job_id, tenant_key)
        async with db_mgr.get_session_async() as session:
            return await _get_job_status_impl(session, job_id, tenant_key)

    except Exception as e:
        logger.exception(f"Failed to get status for job {job_id}")
        return {
            "success": False,
            "error": str(e),
        }


async def _get_job_status_impl(session, job_id: str, tenant_key: str) -> dict[str, Any]:
    """
    Implementation of get_job_status that works with a provided session.

    Args:
        session: AsyncSession to use for database queries
        job_id: Job identifier
        tenant_key: Tenant key for isolation

    Returns:
        Dict with job status data
    """
    # Query job with tenant isolation
    stmt = select(AgentJob).where(
        AgentJob.tenant_key == tenant_key,
        AgentJob.job_id == job_id,
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.error(f"Job {job_id} not found for tenant {tenant_key}")
        return {
            "success": False,
            "error": f"Job {job_id} not found for tenant {tenant_key}",
        }

    # Build response
    response = {
        "success": True,
        "job_id": job.job_id,
        "status": job.status,
        "job_type": job.job_type,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }

    if job.completed_at:
        response["completed_at"] = job.completed_at.isoformat()

    # Include execution history (all agents who worked on this job)
    exec_stmt = (
        select(AgentExecution)
        .where(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.job_id == job_id,
        )
        .order_by(AgentExecution.started_at)
    )
    exec_result = await session.execute(exec_stmt)
    executions = exec_result.scalars().all()

    if executions:
        response["executions"] = [
            {
                "agent_id": execution.agent_id,
                "status": execution.status,
                "progress": execution.progress,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
            }
            for execution in executions
        ]

        # Find current agent (most recent by started_at)
        if executions:
            current_exec = max(executions, key=lambda e: e.started_at or datetime.min.replace(tzinfo=timezone.utc))
            response["current_agent_id"] = current_exec.agent_id

    logger.info(f"Retrieved status for job {job_id} (tenant: {tenant_key})")
    return response


async def get_agent_status(
    agent_id: str,
    tenant_key: str,
    db_manager: Optional[DatabaseManager] = None,
) -> dict[str, Any]:
    """
    Query executor status (AgentExecution table).

    This tool queries the AgentExecution table to retrieve the status of a specific
    agent executor instance. Use this when you need to know the status of a particular
    agent (WHO is doing the work).

    The agent_id represents the WHO (executor) - it changes on succession.
    Each agent instance has a unique agent_id, but multiple agents can work on
    the same job_id over time.

    Args:
        agent_id: Agent executor identifier (UUID of execution instance)
        tenant_key: Tenant key for multi-tenant isolation
        db_manager: Optional database manager (uses module-level if not provided)

    Returns:
        Dict with success status and agent execution data:
        - agent_id: Executor UUID
        - job_id: Work order UUID (context - which job is this agent working on)
        - status: Execution status (waiting, working, blocked, complete, etc.)
        - agent_display_name: Type of agent (orchestrator, implementer, etc.)
        - progress: Completion progress (0-100%)
        - current_task: Description of current task
        - spawned_by: Parent agent_id (succession chain)

    Example:
        # Query agent status
        result = await get_agent_status(
            agent_id="uuid-of-agent",
            tenant_key="tenant-key"
        )
        # Returns: {"success": true, "agent_id": "...", "job_id": "...", "status": "working", ...}

    Handover 0366c: Semantic clarification
    - agent_id = executor instance (WHO) - changes on succession
    - Response includes job_id for context (which work order is this agent executing)
    """
    # Use provided db_manager or fall back to module-level
    db_mgr = db_manager if db_manager is not None else _AgentJobStatusState.db_manager

    if db_mgr is None:
        raise RuntimeError("get_agent_status called before registration and no db_manager provided")

    try:
        # Input validation
        if not agent_id:
            logger.error("Empty agent_id provided to get_agent_status")
            return {
                "success": False,
                "error": "agent_id cannot be empty",
            }

        if not tenant_key:
            logger.error("Empty tenant_key provided to get_agent_status")
            return {
                "success": False,
                "error": "tenant_key cannot be empty",
            }

        # Use test session if available (for transaction isolation in tests)
        # Otherwise create new session
        if _AgentJobStatusState.test_session is not None:
            session = _AgentJobStatusState.test_session
            # Process query directly without context manager (test session managed externally)
            return await _get_agent_status_impl(session, agent_id, tenant_key)
        async with db_mgr.get_session_async() as session:
            return await _get_agent_status_impl(session, agent_id, tenant_key)

    except Exception as e:
        logger.exception(f"Failed to get status for agent {agent_id}")
        return {
            "success": False,
            "error": str(e),
        }


async def _get_agent_status_impl(session, agent_id: str, tenant_key: str) -> dict[str, Any]:
    """
    Implementation of get_agent_status that works with a provided session.

    Args:
        session: AsyncSession to use for database queries
        agent_id: Agent identifier
        tenant_key: Tenant key for isolation

    Returns:
        Dict with agent status data
    """
    # Query execution with tenant isolation
    stmt = select(AgentExecution).where(
        AgentExecution.tenant_key == tenant_key,
        AgentExecution.agent_id == agent_id,
    )
    result = await session.execute(stmt)
    execution = result.scalar_one_or_none()

    if not execution:
        logger.error(f"Agent {agent_id} not found for tenant {tenant_key}")
        return {
            "success": False,
            "error": f"Agent {agent_id} not found for tenant {tenant_key}",
        }

    # Build response
    response = {
        "success": True,
        "agent_id": execution.agent_id,
        "job_id": execution.job_id,  # Context: which job is this agent working on
        "status": execution.status,
        "agent_display_name": execution.agent_display_name,
        "progress": execution.progress,
    }

    # Add optional fields
    if execution.current_task:
        response["current_task"] = execution.current_task

    if execution.spawned_by:
        response["spawned_by"] = execution.spawned_by

    if execution.started_at:
        response["started_at"] = execution.started_at.isoformat()

    if execution.completed_at:
        response["completed_at"] = execution.completed_at.isoformat()

    if execution.block_reason:
        response["block_reason"] = execution.block_reason

    logger.info(f"Retrieved status for agent {agent_id} (job: {execution.job_id}, tenant: {tenant_key})")
    return response


async def update_job_status(
    job_id: str,
    tenant_key: str,
    new_status: str,
    reason: Optional[str] = None,
    db_manager: Optional[DatabaseManager] = None,
) -> dict[str, Any]:
    """
    Update job status for agent self-navigation on Kanban board.

    This tool enables agents to move themselves between Kanban columns by
    updating their job status. Agents must call this tool to report progress
    and navigate the workflow.

    Valid Status Transitions:
    - pending -> active: Agent starts work (sets started_at)
    - pending -> blocked: Agent cannot start (early failure detection)
    - active -> completed: Agent finishes successfully (sets completed_at)
    - active -> blocked: Agent encounters blocker (sets completed_at)

    Kanban Columns (4 total):
    1. Pending: Jobs created, waiting for agent to start
    2. Active: Jobs in progress (agent working)
    3. Completed: Jobs finished successfully
    4. Blocked: Jobs failed OR waiting for feedback (combined status)

    Args:
        job_id: Job identifier (UUID from job assignment)
        tenant_key: Tenant key for multi-tenant isolation
        new_status: New status (pending, active, completed, blocked)
        reason: Optional reason for status change (recommended for blocked status)
        db_manager: Optional database manager (uses module-level if not provided)

    Returns:
        Dict with success status, old/new status, and updated timestamps

    Examples:
        # Agent starts work
        mcp.call_tool("update_job_status", {
            "job_id": "uuid",
            "tenant_key": "tenant-key",
            "new_status": "active"
        })

        # Agent encounters blocker
        mcp.call_tool("update_job_status", {
            "job_id": "uuid",
            "tenant_key": "tenant-key",
            "new_status": "blocked",
            "reason": "Need database schema clarification"
        })

        # Agent completes work
        mcp.call_tool("update_job_status", {
            "job_id": "uuid",
            "tenant_key": "tenant-key",
            "new_status": "completed"
        })

    Handover 0066: Agent Self-Navigation
    - Agents move themselves between columns (NO drag-drop by users)
    - Updates trigger WebSocket events for real-time Kanban board updates
    - Multi-tenant isolation enforced at database level

    Handover 0366c: Uses AgentJob model (not deprecated Job model)
    """
    # Use provided db_manager or fall back to module-level
    db_mgr = db_manager if db_manager is not None else _AgentJobStatusState.db_manager

    if db_mgr is None:
        raise RuntimeError("update_job_status called before registration and no db_manager provided")

    try:
        # Input validation
        if not job_id:
            logger.error("Empty job_id provided to update_job_status")
            return {
                "success": False,
                "error": "job_id cannot be empty",
                "job_id": job_id,
            }

        if not tenant_key:
            logger.error("Empty tenant_key provided to update_job_status")
            return {
                "success": False,
                "error": "tenant_key cannot be empty",
                "job_id": job_id,
            }

        # Validate status
        if new_status not in VALID_STATUSES:
            logger.error(f"Invalid status '{new_status}' provided to update_job_status")
            return {
                "success": False,
                "error": f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
                "job_id": job_id,
            }

        # Use test session if available (for transaction isolation in tests)
        # Otherwise create new session
        if _AgentJobStatusState.test_session is not None:
            session = _AgentJobStatusState.test_session
            # Process query directly without context manager (test session managed externally)
            return await _update_job_status_impl(session, job_id, tenant_key, new_status, reason)
        async with db_mgr.get_session_async() as session:
            return await _update_job_status_impl(session, job_id, tenant_key, new_status, reason)

    except ValueError as ve:
        # Handle invalid status transitions
        logger.exception(f"Invalid status transition for job {job_id}")
        return {
            "success": False,
            "error": str(ve),
            "job_id": job_id,
        }
    except Exception as e:
        logger.exception(f"Failed to update status for job {job_id}")
        return {
            "success": False,
            "error": str(e),
            "job_id": job_id,
        }


async def _update_job_status_impl(
    session, job_id: str, tenant_key: str, new_status: str, reason: Optional[str]
) -> dict[str, Any]:
    """
    Implementation of update_job_status that works with a provided session.

    Args:
        session: AsyncSession to use for database queries
        job_id: Job identifier
        tenant_key: Tenant key for isolation
        new_status: New status value
        reason: Optional reason for status change

    Returns:
        Dict with update result
    """
    # Get current job with tenant isolation
    stmt = select(AgentJob).where(
        AgentJob.tenant_key == tenant_key,
        AgentJob.job_id == job_id,
    )
    result = await session.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.error(f"Job {job_id} not found for tenant {tenant_key} in update_job_status")
        return {
            "success": False,
            "error": f"Job {job_id} not found for tenant {tenant_key}",
            "job_id": job_id,
        }

    # Store old status for response
    old_status = job.status

    # Update status based on transition
    # AgentJob supports: active, completed, cancelled
    if new_status in ("completed", "cancelled"):
        job.status = new_status
        if not job.completed_at:
            job.completed_at = datetime.now(timezone.utc)
    elif new_status == "active":
        job.status = "active"
    else:
        # This shouldn't happen given VALID_STATUSES validation
        job.status = new_status

    await session.commit()
    await session.refresh(job)

    # Build response with timestamp information
    response = {
        "success": True,
        "job_id": job_id,
        "old_status": old_status,
        "new_status": job.status,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Add timestamps based on status
    if job.completed_at:
        response["completed_at"] = job.completed_at.isoformat()

    # Add reason to response if provided
    if reason:
        response["reason"] = reason

    reason_part = f" (reason: {reason})" if reason else ""
    logger.info(
        "Job %s status updated: %s -> %s for tenant %s%s",
        job_id,
        old_status,
        job.status,
        tenant_key,
        reason_part,
    )

    return response
