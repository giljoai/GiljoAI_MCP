"""
MCP Tools for Agent Coordination (Handover 0045).

Provides universal coordination layer for Claude Code, Codex, and Gemini CLI agents.
All tools enforce multi-tenant isolation and integrate with AgentJobManager.

Production-grade features:
- Multi-tenant isolation enforcement
- Comprehensive error handling
- Audit logging for all operations
- Type validation and safety checks
- Integration with existing AgentJobManager and MessageQueue (Handover 0120)
"""

import logging
from typing import Any

from ..database import DatabaseManager


logger = logging.getLogger(__name__)

# Module-level state holder
class _AgentCoordinationState:
    """State holder to avoid global statement."""

    db_manager_instance: Optional[DatabaseManager] = None
    test_session = None


def _get_db_manager() -> DatabaseManager:
    """Get or create database manager instance."""
    if _AgentCoordinationState.db_manager_instance is None:
        _AgentCoordinationState.db_manager_instance = DatabaseManager()
    return _AgentCoordinationState.db_manager_instance


def set_db_manager(db_manager: DatabaseManager) -> None:
    """
    Set the database manager for module-level functions.

    This allows tests to inject a specific database manager instance.
    """
    _AgentCoordinationState.db_manager_instance = db_manager


def init_for_testing(db_manager: DatabaseManager, db_session) -> None:
    """
    Initialize module for testing with shared session (Handover 0366c).

    This allows spawn_agent() and get_agent_status() to use the same
    database session as test fixtures, preventing session isolation issues.

    Args:
        db_manager: DatabaseManager instance for tests
        db_session: Shared AsyncSession for test transaction isolation

    Usage (in conftest.py):
        @pytest_asyncio.fixture(scope="function", autouse=True)
        async def setup_agent_coordination(db_manager, db_session):
            from src.giljo_mcp.tools import agent_coordination
            agent_coordination.init_for_testing(db_manager, db_session)
            yield
    """
    _AgentCoordinationState.db_manager_instance = db_manager
    _AgentCoordinationState.test_session = db_session


# Module-level functions for direct import (Handover 0366c)
async def spawn_agent(
    job_id: str,
    agent_display_name: str,
    tenant_key: str,
    spawned_by_agent_id: str = None,
) -> dict[str, Any]:
    """
    Spawn NEW executor for EXISTING job (Handover 0366c).

    Creates a NEW AgentExecution (executor instance) that references
    an EXISTING AgentJob (work order). Enables agent succession while
    preserving job continuity.

    Semantic Contract:
    - job_id = Work order UUID (the WHAT - persistent across succession)
    - agent_id = Executor UUID (the WHO - changes on succession)
    - Returns BOTH for clarity

    Args:
        job_id: AgentJob UUID to spawn execution for (must exist)
        agent_display_name: Agent display name for this executor (e.g., "implementer", "tester")
        tenant_key: Tenant key for multi-tenant isolation
        spawned_by_agent_id: Parent executor's agent_id (for succession tracking)

    Returns:
        dict: {
            "success": True,
            "job_id": str (work order UUID - persistent),
            "agent_id": str (executor UUID - NEW instance)
        }

    Security:
        - Only jobs owned by tenant can have executions spawned
        - Validates tenant_key matches job's tenant
        - No cross-tenant spawning possible

    Succession:
        - Links to parent executor via spawned_by_agent_id
        - Enables multi-level succession chains
    """
    try:
        # Validate input parameters
        if not job_id or not job_id.strip():
            return {
                "success": False,
                "error": "job_id cannot be empty",
            }

        if not agent_display_name or not agent_display_name.strip():
            return {
                "success": False,
                "error": "agent_display_name cannot be empty",
            }

        if not tenant_key or not tenant_key.strip():
            return {
                "success": False,
                "error": "tenant_key cannot be empty",
            }

        # Import models
        from uuid import uuid4

        from sqlalchemy import select

        from ..models.agent_identity import AgentExecution, AgentJob

        # Get database manager
        db_manager = _get_db_manager()

        # Use test session if available (for test isolation), otherwise create new session
        if _AgentCoordinationState.test_session is not None:
            session = _AgentCoordinationState.test_session
            # Don't use context manager for test session (managed by test fixtures)
            # Verify job exists and belongs to tenant
            job_query = select(AgentJob).where(
                AgentJob.job_id == job_id,
                AgentJob.tenant_key == tenant_key,
            )
            job_result = await session.execute(job_query)
            job = job_result.scalar_one_or_none()

            if not job:
                return {
                    "success": False,
                    "error": f"AgentJob with job_id={job_id} not found for tenant {tenant_key}",
                }

            # Create NEW AgentExecution (executor instance)
            new_agent_id = str(uuid4())

            new_execution = AgentExecution(
                agent_id=new_agent_id,
                job_id=job_id,
                tenant_key=tenant_key,
                agent_display_name=agent_display_name,
                status="waiting",
                spawned_by=spawned_by_agent_id,  # Link to parent executor
                agent_name=agent_display_name.title(),
                context_used=0,
                context_budget=50000,
                tool_type="universal",
            )

            session.add(new_execution)
            await session.flush()  # Use flush instead of commit for test session
            await session.refresh(new_execution)

            logger.info(f"[spawn_agent] Spawned agent_id={new_agent_id} for job_id={job_id}, tenant={tenant_key}")

            return {
                "success": True,
                "job_id": job_id,  # Work order (persistent)
                "agent_id": new_agent_id,  # Executor (NEW instance)
            }
        # Production path: create new session
        async with db_manager.get_session_async() as session:
            # Verify job exists and belongs to tenant
            job_query = select(AgentJob).where(
                AgentJob.job_id == job_id,
                AgentJob.tenant_key == tenant_key,
            )
            job_result = await session.execute(job_query)
            job = job_result.scalar_one_or_none()

            if not job:
                return {
                    "success": False,
                    "error": f"AgentJob with job_id={job_id} not found for tenant {tenant_key}",
                }

            # Get next instance number (count existing executions + 1)
            select(AgentExecution).where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == tenant_key,
            )

            # Create NEW AgentExecution (executor instance)
            new_agent_id = str(uuid4())

            new_execution = AgentExecution(
                agent_id=new_agent_id,
                job_id=job_id,
                tenant_key=tenant_key,
                agent_display_name=agent_display_name,
                status="waiting",
                spawned_by=spawned_by_agent_id,  # Link to parent executor
                agent_name=agent_display_name.title(),
                context_used=0,
                context_budget=50000,
                tool_type="universal",
            )

            session.add(new_execution)
            await session.commit()
            await session.refresh(new_execution)

            logger.info(f"[spawn_agent] Spawned agent_id={new_agent_id} for job_id={job_id}, tenant={tenant_key}")

            return {
                "success": True,
                "job_id": job_id,  # Work order (persistent)
                "agent_id": new_agent_id,  # Executor (NEW instance)
            }

    except Exception as e:
        logger.error(f"[spawn_agent] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def get_agent_status(agent_id: str, tenant_key: str) -> dict[str, Any]:
    """
    Get status for SPECIFIC executor instance (Handover 0366c).

    Queries AgentExecution table by agent_id (executor UUID).
    Returns executor-specific status, progress, and health.

    Semantic Contract:
    - agent_id = Executor UUID (the WHO - specific agent instance)
    - Returns execution-specific data (NOT job-level data)

    Args:
        agent_id: AgentExecution UUID to query (executor instance)
        tenant_key: Tenant key for multi-tenant isolation

    Returns:
        dict: {
            "success": True,
            "agent_id": str (executor UUID),
            "job_id": str (parent work order UUID),
            "status": str (execution status),
            "progress": int (0-100%),
            "health_status": str,
            "agent_display_name": str,
            "agent_name": str
        }

    Security:
        - Only executors owned by tenant can be queried
        - Validates tenant_key matches execution's tenant
        - No cross-tenant executor visibility

    Error Handling:
        - Returns structured error if agent_id not found
        - Clear error messages for debugging
        - No exceptions raised
    """
    try:
        # Validate input parameters
        if not agent_id or not agent_id.strip():
            return {
                "success": False,
                "error": "agent_id cannot be empty",
            }

        if not tenant_key or not tenant_key.strip():
            return {
                "success": False,
                "error": "tenant_key cannot be empty",
            }

        # Import models
        from sqlalchemy import select

        from ..models.agent_identity import AgentExecution

        # Get database manager
        db_manager = _get_db_manager()

        # Use test session if available (for test isolation), otherwise create new session
        if _AgentCoordinationState.test_session is not None:
            session = _AgentCoordinationState.test_session
            # Query AgentExecution by agent_id (executor UUID)
            execution_query = select(AgentExecution).where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            execution_result = await session.execute(execution_query)
            execution = execution_result.scalar_one_or_none()

            if not execution:
                return {
                    "success": False,
                    "error": f"AgentExecution with agent_id={agent_id} not found for tenant {tenant_key}",
                }

            logger.info(
                f"[get_agent_status] Retrieved status for agent_id={agent_id}, "
                f"status={execution.status}, tenant={tenant_key}"
            )

            return {
                "success": True,
                "agent_id": execution.agent_id,  # Executor UUID
                "job_id": execution.job_id,  # Parent work order UUID
                "status": execution.status,
                "progress": execution.progress,
                "health_status": execution.health_status,
                "agent_display_name": execution.agent_display_name,
                "agent_name": execution.agent_name,
                "current_task": execution.current_task,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "spawned_by": execution.spawned_by,
            }
        # Production path: create new session
        async with db_manager.get_session_async() as session:
            # Query AgentExecution by agent_id (executor UUID)
            execution_query = select(AgentExecution).where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            execution_result = await session.execute(execution_query)
            execution = execution_result.scalar_one_or_none()

            if not execution:
                return {
                    "success": False,
                    "error": f"AgentExecution with agent_id={agent_id} not found for tenant {tenant_key}",
                }

            logger.info(
                f"[get_agent_status] Retrieved status for agent_id={agent_id}, "
                f"status={execution.status}, tenant={tenant_key}"
            )

            return {
                "success": True,
                "agent_id": execution.agent_id,  # Executor UUID
                "job_id": execution.job_id,  # Parent work order UUID
                "status": execution.status,
                "progress": execution.progress,
                "health_status": execution.health_status,
                "agent_display_name": execution.agent_display_name,
                "agent_name": execution.agent_name,
                "current_task": execution.current_task,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "spawned_by": execution.spawned_by,
            }

    except Exception as e:
        logger.error(f"[get_agent_status] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def get_team_agents(
    job_id: str,
    tenant_key: str,
    include_inactive: bool = False,
) -> dict[str, Any]:
    """
    List agent executions (teammates) associated with this job.

    Handover 0360 Feature 2: Team Discovery Tool.

    Enables agents to discover teammates working on the same job/project.
    Useful for coordination, status checking, and understanding team composition.

    Semantic Contract:
    - job_id = Work order UUID (the WHAT - identifies the work)
    - Returns list of agent executions (the WHO - all executors for this job)
    - Filtered by active status by default (waiting, working, blocked)

    Args:
        job_id: Job ID to get teammates for
        tenant_key: Tenant key for multi-tenant isolation
        include_inactive: If True, include completed/decommissioned executions

    Returns:
        dict: {
            "success": True,
            "team": [
                {
                    "agent_id": str (executor UUID),
                    "job_id": str (work order UUID),
                    "agent_display_name": str (agent role),
                    "status": str (execution status),
                    "agent_name": str (display name),
                    "tenant_key": str
                },
                ...
            ]
        }

    Security:
        - Only returns executions for jobs owned by tenant
        - Validates tenant_key matches job's tenant
        - No cross-tenant execution visibility

    Use Cases:
        - Check who else is working on this job
        - Identify orchestrator vs specialist agents
        - Track succession history (all instances)
        - Coordinate with specific teammates

    Example:
        >>> result = await get_team_agents(
        ...     job_id="job-uuid-123",
        ...     tenant_key="tenant-abc",
        ...     include_inactive=False
        ... )
        >>> for member in result["team"]:
        ...     print(f"{member['agent_display_name']}: {member['status']}")
    """
    try:
        # Validate input parameters
        if not job_id or not job_id.strip():
            return {
                "success": False,
                "error": "job_id cannot be empty",
            }

        if not tenant_key or not tenant_key.strip():
            return {
                "success": False,
                "error": "tenant_key cannot be empty",
            }

        # Import service and models
        from ..services.agent_job_manager import AgentJobManager
        from ..tenant import TenantManager

        # Get database manager
        db_manager = _get_db_manager()

        # Create AgentJobManager instance
        tenant_manager = TenantManager()
        job_manager = AgentJobManager(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            test_session=_AgentCoordinationState.test_session,  # Use test session if available
        )

        # Call service method
        team_members = await job_manager.list_team_agents(
            job_id=job_id,
            tenant_key=tenant_key,
            include_inactive=include_inactive,
        )

        logger.info(
            f"[get_team_agents] Retrieved {len(team_members)} teammates for job {job_id}, "
            f"include_inactive={include_inactive}, tenant={tenant_key}"
        )

        return {
            "success": True,
            "team": team_members,
        }

    except Exception as e:
        logger.error(f"[get_team_agents] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }
