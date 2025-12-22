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
from datetime import datetime, timezone
from typing import Any, Dict, List

from ..agent_message_queue import AgentMessageQueue as MessageQueue
from ..agent_job_manager import AgentJobManager
from ..database import DatabaseManager


logger = logging.getLogger(__name__)


# Global database manager for module-level functions (set via init or auto-created)
_db_manager_instance = None
_test_session = None


def _get_db_manager() -> DatabaseManager:
    """Get or create database manager instance."""
    global _db_manager_instance
    if _db_manager_instance is None:
        _db_manager_instance = DatabaseManager()
    return _db_manager_instance


def set_db_manager(db_manager: DatabaseManager) -> None:
    """
    Set the database manager for module-level functions.

    This allows tests to inject a specific database manager instance.
    """
    global _db_manager_instance
    _db_manager_instance = db_manager


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
    global _db_manager_instance, _test_session
    _db_manager_instance = db_manager
    _test_session = db_session


# Module-level functions for direct import (Handover 0366c)
async def spawn_agent(
    job_id: str,
    agent_type: str,
    tenant_key: str,
    spawned_by_agent_id: str = None,
) -> Dict[str, Any]:
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
        agent_type: Agent type for this executor (e.g., "implementer", "tester")
        tenant_key: Tenant key for multi-tenant isolation
        spawned_by_agent_id: Parent executor's agent_id (for succession tracking)

    Returns:
        dict: {
            "success": True,
            "job_id": str (work order UUID - persistent),
            "agent_id": str (executor UUID - NEW instance),
            "instance_number": int (succession tracking)
        }

    Security:
        - Only jobs owned by tenant can have executions spawned
        - Validates tenant_key matches job's tenant
        - No cross-tenant spawning possible

    Succession:
        - Increments instance_number automatically
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

        if not agent_type or not agent_type.strip():
            return {
                "success": False,
                "error": "agent_type cannot be empty",
            }

        if not tenant_key or not tenant_key.strip():
            return {
                "success": False,
                "error": "tenant_key cannot be empty",
            }

        # Import models
        from sqlalchemy import select
        from uuid import uuid4
        from ..models.agent_identity import AgentJob, AgentExecution

        # Get database manager
        db_manager = _get_db_manager()

        # Use test session if available (for test isolation), otherwise create new session
        if _test_session is not None:
            session = _test_session
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

            # Get next instance number (count existing executions + 1)
            existing_executions_query = select(AgentExecution).where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == tenant_key,
            )
            existing_result = await session.execute(existing_executions_query)
            existing_executions = existing_result.scalars().all()
            instance_number = len(existing_executions) + 1

            # Create NEW AgentExecution (executor instance)
            new_agent_id = str(uuid4())

            new_execution = AgentExecution(
                agent_id=new_agent_id,
                job_id=job_id,
                tenant_key=tenant_key,
                agent_type=agent_type,
                instance_number=instance_number,
                status="waiting",
                spawned_by=spawned_by_agent_id,  # Link to parent executor
                agent_name=f"{agent_type.title()} #{instance_number}",
                context_used=0,
                context_budget=50000,
                tool_type="universal",
            )

            session.add(new_execution)
            await session.flush()  # Use flush instead of commit for test session
            await session.refresh(new_execution)

            logger.info(
                f"[spawn_agent] Spawned agent_id={new_agent_id} for job_id={job_id}, "
                f"instance={instance_number}, tenant={tenant_key}"
            )

            return {
                "success": True,
                "job_id": job_id,  # Work order (persistent)
                "agent_id": new_agent_id,  # Executor (NEW instance)
                "instance_number": instance_number,
            }
        else:
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
                existing_executions_query = select(AgentExecution).where(
                    AgentExecution.job_id == job_id,
                    AgentExecution.tenant_key == tenant_key,
                )
                existing_result = await session.execute(existing_executions_query)
                existing_executions = existing_result.scalars().all()
                instance_number = len(existing_executions) + 1

                # Create NEW AgentExecution (executor instance)
                new_agent_id = str(uuid4())

                new_execution = AgentExecution(
                    agent_id=new_agent_id,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    agent_type=agent_type,
                    instance_number=instance_number,
                    status="waiting",
                    spawned_by=spawned_by_agent_id,  # Link to parent executor
                    agent_name=f"{agent_type.title()} #{instance_number}",
                    context_used=0,
                    context_budget=50000,
                    tool_type="universal",
                )

                session.add(new_execution)
                await session.commit()
                await session.refresh(new_execution)

                logger.info(
                    f"[spawn_agent] Spawned agent_id={new_agent_id} for job_id={job_id}, "
                    f"instance={instance_number}, tenant={tenant_key}"
                )

                return {
                    "success": True,
                    "job_id": job_id,  # Work order (persistent)
                    "agent_id": new_agent_id,  # Executor (NEW instance)
                    "instance_number": instance_number,
                }

    except Exception as e:
        logger.error(f"[spawn_agent] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
        }


async def get_agent_status(agent_id: str, tenant_key: str) -> Dict[str, Any]:
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
            "instance_number": int,
            "agent_type": str,
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
        if _test_session is not None:
            session = _test_session
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
                "instance_number": execution.instance_number,
                "agent_type": execution.agent_type,
                "agent_name": execution.agent_name,
                "current_task": execution.current_task,
                "started_at": execution.started_at.isoformat() if execution.started_at else None,
                "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                "spawned_by": execution.spawned_by,
                "succeeded_by": execution.succeeded_by,
            }
        else:
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
                    "instance_number": execution.instance_number,
                    "agent_type": execution.agent_type,
                    "agent_name": execution.agent_name,
                    "current_task": execution.current_task,
                    "started_at": execution.started_at.isoformat() if execution.started_at else None,
                    "completed_at": execution.completed_at.isoformat() if execution.completed_at else None,
                    "spawned_by": execution.spawned_by,
                    "succeeded_by": execution.succeeded_by,
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
) -> Dict[str, Any]:
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
                    "agent_type": str (agent role),
                    "status": str (execution status),
                    "instance_number": int (succession tracking),
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
        ...     print(f"{member['agent_type']}: {member['status']}")
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
            test_session=_test_session,  # Use test session if available
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


def register_agent_coordination_tools(tools: dict, db_manager: DatabaseManager) -> None:
    """
    Register agent coordination tools with MCP server.

    Args:
        tools: Dictionary to register tools into
        db_manager: DatabaseManager instance for database operations
    """
    job_manager = AgentJobManager(db_manager)
    comm_queue = AgentMessageQueue(db_manager)  # Using compatibility layer for AgentCommunicationQueue API

    def get_pending_jobs(agent_type: str, tenant_key: str) -> Dict[str, Any]:
        """
        Get pending jobs assigned to this agent type.

        Multi-tenant coordination tool that retrieves jobs waiting for agent acknowledgment.
        Supports job queue pattern for Codex/Gemini CLI agents and hybrid mode for Claude Code.

        Args:
            agent_type: Agent type/role (e.g., "implementer", "tester", "reviewer")
            tenant_key: Tenant identifier for multi-tenant isolation

        Returns:
            dict: {
                "status": "success" | "error",
                "jobs": [
                    {
                        "job_id": str,
                        "agent_type": str,
                        "mission": str,
                        "context_chunks": list[str],
                        "priority": str,
                        "created_at": str (ISO datetime)
                    }
                ],
                "count": int
            }

        Security:
            - Multi-tenant isolation enforced via tenant_key filtering
            - Only returns jobs belonging to the specified tenant
            - No cross-tenant leakage possible

        Performance:
            - Uses database indexes on tenant_key and status
            - Returns max 10 jobs to prevent memory issues
            - Ordered by creation time (FIFO)
        """
        try:
            # Validate input parameters
            if not agent_type or not agent_type.strip():
                return {
                    "status": "error",
                    "error": "agent_type cannot be empty",
                    "jobs": [],
                    "count": 0,
                }

            if not tenant_key or not tenant_key.strip():
                return {
                    "status": "error",
                    "error": "tenant_key cannot be empty",
                    "jobs": [],
                    "count": 0,
                }

            # Get pending jobs with tenant isolation
            jobs = job_manager.get_pending_jobs(tenant_key=tenant_key, agent_type=agent_type, limit=10)

            # Format jobs for response
            formatted_jobs = []
            for job in jobs:
                formatted_jobs.append(
                    {
                        "job_id": job.job_id,
                        "agent_type": job.job_type,
                        "mission": job.mission,
                        "context_chunks": job.context_chunks or [],
                        "priority": "normal",  # Default priority
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                    }
                )

            logger.info(
                f"[get_pending_jobs] Retrieved {len(formatted_jobs)} jobs for "
                f"agent_type={agent_type}, tenant={tenant_key}"
            )

            return {
                "status": "success",
                "jobs": formatted_jobs,
                "count": len(formatted_jobs),
            }

        except Exception as e:
            logger.error(f"[get_pending_jobs] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
                "jobs": [],
                "count": 0,
            }

    def acknowledge_job(job_id: str, agent_id: str, tenant_key: str) -> Dict[str, Any]:
        """
        Claim a job (pending -> active).

        Transitions job from pending to active state and sets acknowledgment timestamp.
        Idempotent operation - safe to call multiple times for same job.

        Args:
            job_id: Job ID to acknowledge
            agent_id: Agent identifier claiming the job
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            dict: {
                "status": "success" | "error",
                "job": {
                    "job_id": str,
                    "agent_type": str,
                    "mission": str,
                    "status": str,
                    "started_at": str (ISO datetime)
                },
                "next_instructions": str
            }

        Security:
            - Only jobs belonging to tenant can be acknowledged
            - Validates tenant_key matches job's tenant
            - No cross-tenant access possible

        Error Conditions:
            - Job not found for tenant
            - Invalid status transition
            - Database errors
        """
        try:
            # Validate input parameters
            if not job_id or not job_id.strip():
                return {
                    "status": "error",
                    "error": "job_id cannot be empty",
                }

            if not agent_id or not agent_id.strip():
                return {
                    "status": "error",
                    "error": "agent_id cannot be empty",
                }

            if not tenant_key or not tenant_key.strip():
                return {
                    "status": "error",
                    "error": "tenant_key cannot be empty",
                }

            # Acknowledge job with tenant isolation
            job = job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job_id)

            # Agent status sync removed (Handover 0116) - Agent model eliminated
            # Previously synced job acknowledgment to legacy agents table
            # AgentJob status is authoritative and updated via AgentJobManager

            logger.info(f"[acknowledge_job] Job {job_id} acknowledged by {agent_id} for tenant {tenant_key}")

            return {
                "status": "success",
                "job": {
                    "job_id": job.job_id,
                    "agent_type": job.job_type,
                    "mission": job.mission,
                    "status": job.status,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                },
                "next_instructions": "Proceed with mission. Report progress incrementally via report_progress().",
            }

        except ValueError as e:
            logger.warning(f"[acknowledge_job] Validation error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"[acknowledge_job] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    async def report_progress(
        job_id: str,
        completed_todo: str,
        files_modified: List[str],
        context_used: int,
        tenant_key: str,
    ) -> Dict[str, Any]:
        """
        Report incremental progress on active job.

        Stores progress update in message queue for orchestrator visibility.
        Provides warnings if context usage is approaching limits.

        Args:
            job_id: Job ID being worked on
            completed_todo: Description of what was completed
            files_modified: List of modified file paths
            context_used: Estimated tokens consumed (approximate)
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            dict: {
                "status": "success" | "error",
                "continue": bool,
                "warnings": list[str],
                "context_remaining": int (estimated)
            }

        Security:
            - Progress can only be reported for jobs owned by tenant
            - Validates tenant_key matches job's tenant
            - Message queue enforces tenant isolation

        Context Management:
            - Warns at 25K tokens (approaching 30K limit)
            - Recommends handoff at 28K tokens
            - Critical warning at 29K tokens
        """
        try:
            # Validate input parameters
            if not job_id or not job_id.strip():
                return {
                    "status": "error",
                    "error": "job_id cannot be empty",
                }

            if not tenant_key or not tenant_key.strip():
                return {
                    "status": "error",
                    "error": "tenant_key cannot be empty",
                }

            if not completed_todo or not completed_todo.strip():
                return {
                    "status": "error",
                    "error": "completed_todo cannot be empty",
                }

            # Validate context_used is non-negative
            if context_used < 0:
                return {
                    "status": "error",
                    "error": "context_used must be non-negative",
                }

            # Store progress in message queue
            async with db_manager.get_session_async() as session:
                result = await comm_queue.send_message(
                    session=session,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    from_agent=job_id,  # Agent identified by job
                    to_agent=None,  # Broadcast (orchestrator will read)
                    message_type="progress",
                    content=completed_todo,
                    priority=1,
                    metadata={
                        "files_modified": files_modified or [],
                        "context_used": context_used,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )

                if result.get("status") != "success":
                    return result

            # Check context limits and generate warnings
            warnings = []
            context_remaining = 30000 - context_used

            if context_used >= 29000:
                warnings.append("CRITICAL: Context usage at 97% - IMMEDIATE handoff required")
            elif context_used >= 28000:
                warnings.append("WARNING: Context usage at 93% - Prepare for handoff soon")
            elif context_used >= 25000:
                warnings.append("NOTICE: Context usage at 83% - Consider handoff after next task")

            logger.info(
                f"[report_progress] Progress reported for job {job_id}, "
                f"context_used={context_used}, tenant={tenant_key}"
            )

            return {
                "status": "success",
                "continue": True,
                "warnings": warnings,
                "context_remaining": context_remaining,
            }

        except Exception as e:
            logger.error(f"[report_progress] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    async def get_next_instruction(job_id: str, agent_type: str, tenant_key: str) -> Dict[str, Any]:
        """
        Check for new instructions, user feedback, or handoff requests.

        Polls message queue for unread messages directed to this agent.
        Supports orchestrator-to-agent communication and user feedback integration.

        Args:
            job_id: Job ID to check messages for
            agent_type: Agent type (for filtering messages)
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            dict: {
                "status": "success" | "error",
                "has_updates": bool,
                "instructions": list[str],
                "handoff_requested": bool,
                "context_warning": bool,
                "message_count": int
            }

        Security:
            - Only messages for jobs owned by tenant are returned
            - Message queue enforces tenant isolation
            - No cross-tenant message leakage

        Message Types:
            - user_feedback: Direct user input requiring attention
            - orchestrator_instruction: Commands from orchestrator
            - handoff_request: Signal to prepare for context handoff
            - context_warning: Approaching context limit
        """
        try:
            # Validate input parameters
            if not job_id or not job_id.strip():
                return {
                    "status": "error",
                    "error": "job_id cannot be empty",
                }

            if not agent_type or not agent_type.strip():
                return {
                    "status": "error",
                    "error": "agent_type cannot be empty",
                }

            if not tenant_key or not tenant_key.strip():
                return {
                    "status": "error",
                    "error": "tenant_key cannot be empty",
                }

            # Get unread messages for this job
            async with db_manager.get_session_async() as session:
                result = await comm_queue.get_messages(
                    session=session,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    to_agent=agent_type,
                    unread_only=True,
                )

                if result.get("status") != "success":
                    return result

            messages = result.get("messages", [])
            has_updates = len(messages) > 0

            # Extract and categorize instructions
            instructions = []
            handoff_requested = False
            context_warning = False

            for msg in messages:
                msg_type = msg.get("type")
                content = msg.get("content")

                if msg_type == "user_feedback":
                    instructions.append(f"USER FEEDBACK: {content}")
                elif msg_type == "orchestrator_instruction":
                    instructions.append(f"ORCHESTRATOR: {content}")
                elif msg_type == "handoff_request":
                    handoff_requested = True
                    instructions.append("HANDOFF REQUESTED: Prepare comprehensive summary and context handoff")
                elif msg_type == "context_warning":
                    context_warning = True
                    instructions.append(f"CONTEXT WARNING: {content} - Plan completion or handoff")
                elif msg_type == "error_recovery":
                    instructions.append(f"ERROR RECOVERY GUIDANCE: {content}")

            logger.info(
                f"[get_next_instruction] Retrieved {len(messages)} unread messages "
                f"for job {job_id}, tenant={tenant_key}"
            )

            return {
                "status": "success",
                "has_updates": has_updates,
                "instructions": instructions,
                "handoff_requested": handoff_requested,
                "context_warning": context_warning,
                "message_count": len(messages),
            }

        except Exception as e:
            logger.error(f"[get_next_instruction] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    def complete_job(job_id: str, result: Dict[str, Any], tenant_key: str) -> Dict[str, Any]:
        """
        Mark job as completed with results.

        Transitions job from active to completed state and stores result data.
        Optionally provides next job information for chaining.

        Args:
            job_id: Job ID to complete
            result: Result data dict with keys:
                - summary: str (required)
                - files_created: list[str] (optional)
                - files_modified: list[str] (optional)
                - tests_written: list[str] (optional)
                - coverage: str (optional)
                - notes: str (optional)
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            dict: {
                "status": "success" | "error",
                "message": str,
                "next_job": Optional[dict] with job_id and mission
            }

        Security:
            - Only jobs owned by tenant can be completed
            - Validates tenant_key matches job's tenant
            - Result data stored in tenant-isolated message queue

        Post-Completion:
            - Checks for next pending job of same agent_type
            - Provides seamless job chaining for agents
        """
        try:
            # Validate input parameters
            if not job_id or not job_id.strip():
                return {
                    "status": "error",
                    "error": "job_id cannot be empty",
                }

            if not tenant_key or not tenant_key.strip():
                return {
                    "status": "error",
                    "error": "tenant_key cannot be empty",
                }

            if not result or not isinstance(result, dict):
                return {
                    "status": "error",
                    "error": "result must be a non-empty dict",
                }

            # Validate result has summary
            if "summary" not in result:
                return {
                    "status": "error",
                    "error": "result must contain 'summary' key",
                }

            # Complete job with tenant isolation
            job = job_manager.complete_job(tenant_key=tenant_key, job_id=job_id, result=result)

            # Agent status sync removed (Handover 0116) - Agent model eliminated
            # Previously synced job completion to legacy agents table
            # AgentJob status is authoritative and updated via AgentJobManager

            # Check for next job (optional chaining)
            next_jobs = job_manager.get_pending_jobs(tenant_key=tenant_key, agent_type=job.job_type, limit=1)

            next_job_info = None
            if next_jobs:
                next_job = next_jobs[0]
                next_job_info = {
                    "job_id": next_job.job_id,
                    "mission": next_job.mission,
                    "agent_type": next_job.job_type,
                }

            logger.info(
                f"[complete_job] Job {job_id} completed for tenant {tenant_key}, "
                f"next_job={'yes' if next_job_info else 'none'}"
            )

            return {
                "status": "success",
                "message": "Job completed successfully",
                "next_job": next_job_info,
            }

        except ValueError as e:
            logger.warning(f"[complete_job] Validation error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"[complete_job] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    async def report_error(
        job_id: str,
        error_type: str,
        error_message: str,
        context: str,
        tenant_key: str,
    ) -> Dict[str, Any]:
        """
        Report error and pause job for orchestrator review.

        Transitions job to failed state and stores error details in message queue.
        Notifies orchestrator for intervention and recovery guidance.

        Args:
            job_id: Job ID encountering error
            error_type: Category of error:
                - build_failure: Build/compile errors
                - test_failure: Test execution failures
                - validation_error: Data validation issues
                - dependency_error: Missing dependencies
                - runtime_error: Runtime exceptions
                - unknown: Uncategorized errors
            error_message: Full error details (stack trace, error output)
            context: What agent was doing when error occurred
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            dict: {
                "status": "success" | "error",
                "message": str,
                "recovery_instructions": str
            }

        Security:
            - Only jobs owned by tenant can report errors
            - Error data stored in tenant-isolated message queue
            - No cross-tenant error visibility

        Error Handling:
            - Job marked as failed (terminal state)
            - Orchestrator notified via high-priority message
            - Recovery guidance provided based on error type
        """
        try:
            # Validate input parameters
            if not job_id or not job_id.strip():
                return {
                    "status": "error",
                    "error": "job_id cannot be empty",
                }

            if not tenant_key or not tenant_key.strip():
                return {
                    "status": "error",
                    "error": "tenant_key cannot be empty",
                }

            if not error_type or not error_type.strip():
                return {
                    "status": "error",
                    "error": "error_type cannot be empty",
                }

            if not error_message or not error_message.strip():
                return {
                    "status": "error",
                    "error": "error_message cannot be empty",
                }

            # Validate error_type is recognized
            valid_error_types = [
                "build_failure",
                "test_failure",
                "validation_error",
                "dependency_error",
                "runtime_error",
                "unknown",
            ]
            if error_type not in valid_error_types:
                return {
                    "status": "error",
                    "error": f"error_type must be one of: {', '.join(valid_error_types)}",
                }

            # Create error data structure
            error_data = {
                "type": error_type,
                "message": error_message,
                "context": context or "No context provided",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Fail job with tenant isolation
            job = job_manager.fail_job(tenant_key=tenant_key, job_id=job_id, error=error_data)

            # Agent status sync removed (Handover 0116) - Agent model eliminated
            # Previously synced job failure to legacy agents table
            # AgentJob status is authoritative and updated via AgentJobManager

            # Store error in message queue for orchestrator visibility
            async with db_manager.get_session_async() as session:
                await comm_queue.send_message(
                    session=session,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    from_agent=job_id,
                    to_agent="orchestrator",
                    message_type="error",
                    content=error_message,
                    priority=2,  # High priority
                    metadata=error_data,
                )

            logger.error(
                f"[report_error] Job {job_id} failed with {error_type} for tenant {tenant_key}: {error_message[:100]}"
            )

            # Generate recovery instructions based on error type
            recovery_instructions = {
                "build_failure": "Build error detected. Orchestrator will review and provide fix guidance.",
                "test_failure": "Test failure detected. Orchestrator will analyze and suggest corrections.",
                "validation_error": "Validation error detected. Orchestrator will review data constraints.",
                "dependency_error": "Dependency issue detected. Orchestrator will check installation requirements.",
                "runtime_error": "Runtime error detected. Orchestrator will review stack trace and provide fix.",
                "unknown": "Unknown error detected. Orchestrator will investigate and provide guidance.",
            }

            return {
                "status": "success",
                "message": "Error reported successfully. Awaiting orchestrator guidance.",
                "recovery_instructions": recovery_instructions.get(error_type, recovery_instructions["unknown"]),
            }

        except ValueError as e:
            logger.warning(f"[report_error] Validation error: {e}")
            return {
                "status": "error",
                "error": str(e),
            }
        except Exception as e:
            logger.error(f"[report_error] Error while reporting error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    async def send_message(
        job_id: str,
        to_agent: str,
        message: str,
        tenant_key: str,
        priority: int = 1,
    ) -> Dict[str, Any]:
        """
        Send message to another agent (inter-agent communication).

        Enables orchestrator-to-agent and agent-to-agent messaging.
        Primarily used by orchestrator to send instructions, feedback, or coordination signals.

        Args:
            job_id: Job ID for context
            to_agent: Agent type to send message to (e.g., "implementer", "tester")
            message: Message content
            tenant_key: Tenant key for multi-tenant isolation
            priority: Message priority:
                - 0: Low priority (informational)
                - 1: Normal priority (default)
                - 2: High priority (urgent action required)

        Returns:
            dict: {
                "status": "success" | "error",
                "message_id": str (UUID)
            }

        Security:
            - Messages can only be sent within tenant's jobs
            - Validates tenant_key matches job's tenant
            - Message queue enforces tenant isolation

        Use Cases:
            - Orchestrator feedback to agent
            - User message relay to agent
            - Cross-agent coordination signals
            - Handoff requests between agents
        """
        try:
            # Validate input parameters
            if not job_id or not job_id.strip():
                return {
                    "status": "error",
                    "error": "job_id cannot be empty",
                }

            if not to_agent or not to_agent.strip():
                return {
                    "status": "error",
                    "error": "to_agent cannot be empty",
                }

            if not message or not message.strip():
                return {
                    "status": "error",
                    "error": "message cannot be empty",
                }

            if not tenant_key or not tenant_key.strip():
                return {
                    "status": "error",
                    "error": "tenant_key cannot be empty",
                }

            # Validate priority
            if priority not in [0, 1, 2]:
                return {
                    "status": "error",
                    "error": "priority must be 0 (low), 1 (normal), or 2 (high)",
                }

            # Send message with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await comm_queue.send_message(
                    session=session,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    from_agent="orchestrator",
                    to_agent=to_agent,
                    message_type="orchestrator_instruction",
                    content=message,
                    priority=priority,
                )

                if result.get("status") != "success":
                    return result

            logger.info(
                f"[send_message] Message sent to {to_agent} for job {job_id}, tenant={tenant_key}, priority={priority}"
            )

            return {
                "status": "success",
                "message_id": result.get("message_id"),
            }

        except Exception as e:
            logger.error(f"[send_message] Error: {e}", exc_info=True)
            return {
                "status": "error",
                "error": str(e),
            }

    # Register all tools (including module-level spawn_agent, get_agent_status, get_team_agents)
    tools["get_pending_jobs"] = get_pending_jobs
    tools["acknowledge_job"] = acknowledge_job
    tools["report_progress"] = report_progress
    tools["get_next_instruction"] = get_next_instruction
    tools["complete_job"] = complete_job
    tools["report_error"] = report_error
    tools["send_message"] = send_message
    tools["spawn_agent"] = spawn_agent
    tools["get_agent_status"] = get_agent_status
    tools["get_team_agents"] = get_team_agents  # Handover 0360 Feature 2

    logger.info("[agent_coordination] Registered 10 agent coordination tools for multi-tool orchestration")
