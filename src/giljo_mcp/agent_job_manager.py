"""
AgentJobManager for GiljoAI MCP Server.

Manages agent job lifecycle: creation, status management, and retrieval.
Provides multi-tenant isolation and job hierarchy tracking.

Handover 0019: Agent Job Management
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import and_, select
from sqlalchemy.orm import Session

from .database import DatabaseManager
from .models import MCPAgentJob
Job = MCPAgentJob  # Alias for backward compatibility (Handover 0233)


logger = logging.getLogger(__name__)


class AgentJobManager:
    """
    Manages MCP agent jobs with multi-tenant isolation.

    Responsibilities:
    - Create and manage agent jobs
    - Track job status transitions
    - Maintain job hierarchy (parent/child relationships)
    - Enforce tenant isolation
    - Manage job messages and metadata

    Valid status transitions (Handover 0113 - 7 State System):
    - waiting -> working (via update_job_status or acknowledge_job)
    - waiting -> failed (via fail_job)
    - waiting -> cancelled (via cancel_job)
    - working -> complete (via complete_job)
    - working -> failed (via fail_job)
    - working -> blocked (via update_job_status)
    - working -> cancelled (via cancel_job)
    - blocked -> working (via update_job_status)
    - blocked -> failed (via fail_job)
    - blocked -> cancelled (via cancel_job)
    - complete -> working (via continue_working - resume project)
    - complete -> decommissioned (via decommission_job - project closeout)
    - failed, cancelled, decommissioned -> [terminal states, no transitions]
    """

    # Valid status transitions (7-state system)
    VALID_TRANSITIONS = {
        "waiting": {"working", "failed", "cancelled"},
        "working": {"complete", "failed", "blocked", "cancelled"},
        "blocked": {"working", "failed", "cancelled"},
        "complete": set(),  # Terminal state
        "failed": set(),  # Terminal state
        "cancelled": set(),  # Terminal state
    }

    # Alias mapping for caller-facing statuses vs DB constraint statuses
    STATUS_INBOUND_ALIASES = {
        "pending": "waiting",
        "active": "working",
        "completed": "complete",
    }
    STATUS_OUTBOUND_ALIASES = {
        "waiting": "pending",
        "working": "active",
        "complete": "completed",
    }

    @classmethod
    def _normalize_status(cls, status: str) -> str:
        """
        Convert caller-facing status aliases to DB-backed statuses.
        """
        return cls.STATUS_INBOUND_ALIASES.get(status, status)

    @classmethod
    def _expose_status(cls, status: str) -> str:
        """
        Convert DB-backed statuses to caller-facing aliases.
        """
        return cls.STATUS_OUTBOUND_ALIASES.get(status, status)

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize AgentJobManager.

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager

    def create_job(
        self,
        tenant_key: str,
        agent_type: str,
        mission: str,
        spawned_by: Optional[str] = None,
        context_chunks: Optional[list[str]] = None,
        job_metadata: Optional[dict[str, Any]] = None,
    ) -> Job:
        """
        Create a new agent job.

        Args:
            tenant_key: Tenant key for isolation
            agent_type: Type of agent (orchestrator, implementer, tester, etc.)
            mission: Mission/instructions for the agent
            spawned_by: Optional job_id of parent job that spawned this job
            context_chunks: Optional list of chunk_ids for context loading
            job_metadata: Optional metadata dict (field_priorities, user_id, tool, etc.)

        Returns:
            Created Job instance

        Raises:
            ValueError: If required parameters are invalid
        """
        # Validate required parameters
        if not tenant_key:
            raise ValueError("tenant_key cannot be empty")
        if not agent_type:
            raise ValueError("agent_type cannot be empty")
        if not mission:
            raise ValueError("mission cannot be empty")

        # Create job
        job = Job(
            tenant_key=tenant_key,
            agent_type=agent_type,
            mission=mission,
            status="waiting",
            spawned_by=spawned_by,
            context_chunks=context_chunks or [],
            messages=[],
            job_metadata=job_metadata or {},
        )

        with self.db_manager.get_session() as session:
            session.add(job)
            session.commit()
            session.refresh(job)

        # Expose pending status to callers while DB stores 'waiting'
        job.status = self._expose_status(job.status)

        logger.info(
            f"Created job {job.job_id} for tenant {tenant_key}, agent_type={agent_type}, spawned_by={spawned_by}"
        )

        return job

    def create_job_batch(
        self,
        tenant_key: str,
        job_specs: list[dict[str, Any]],
    ) -> list[Job]:
        """
        Create multiple jobs in batch.

        Args:
            tenant_key: Tenant key for isolation
            job_specs: List of job specifications, each containing:
                - agent_type (required)
                - mission (required)
                - spawned_by (optional)
                - context_chunks (optional)

        Returns:
            List of created Job instances

        Raises:
            ValueError: If tenant_key or job specs are invalid
        """
        if not tenant_key:
            raise ValueError("tenant_key cannot be empty")

        if not job_specs:
            return []

        jobs = []
        with self.db_manager.get_session() as session:
            for spec in job_specs:
                # Validate spec
                if not spec.get("agent_type"):
                    raise ValueError("agent_type is required in job spec")
                if not spec.get("mission"):
                    raise ValueError("mission is required in job spec")

                # Create job
                job = Job(
                    tenant_key=tenant_key,
                    agent_type=spec["agent_type"],
                    mission=spec["mission"],
                    status="waiting",  # Fixed: was "pending" but constraint only allows "waiting"
                    spawned_by=spec.get("spawned_by"),
                    context_chunks=spec.get("context_chunks", []),
                    messages=[],
                )
                session.add(job)
                jobs.append(job)

            session.commit()

            # Refresh all jobs to get IDs
            for job in jobs:
                session.refresh(job)
                session.expunge(job)

        # Present caller-facing aliases without persisting them
        for job in jobs:
            job.status = self._expose_status(job.status)

        logger.info(f"Created batch of {len(jobs)} jobs for tenant {tenant_key}")

        return jobs

    def acknowledge_job(
        self,
        tenant_key: str,
        job_id: str,
    ) -> Job:
        """
        Acknowledge a job (pending -> active).

        Sets status=working and started_at timestamp.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID to acknowledge

        Returns:
            Updated Job instance

        Raises:
            ValueError: If job not found or status transition invalid
        """
        with self.db_manager.get_session() as session:
            # Get job with tenant isolation
            job = self._get_job_or_raise(session, tenant_key, job_id)

            # If already in working status, return as-is (idempotent)
            if job.status in {"working", "active"}:
                logger.info(f"Job {job_id} already acknowledged, returning current state")
                session.expunge(job)
                job.status = self._expose_status(job.status)
                return job

            # Validate status transition
            if job.status not in {"pending", "blocked", "waiting"}:
                self._validate_status_transition(job.status, "working")

            # Update job
            job.status = "working"
            job.started_at = datetime.now(timezone.utc)

            session.commit()
            session.refresh(job)
            session.expunge(job)

        # Expose active status to callers without persisting alias in DB
        job.status = self._expose_status("working")

        logger.info(f"Acknowledged job {job_id} for tenant {tenant_key}")

        return job

    def update_job_status(
        self,
        tenant_key: str,
        job_id: str,
        status: str,
        metadata: Optional[dict[str, Any]] = None,
    ) -> Job:
        """
        Update job status with optional metadata.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID to update
            status: New status
            metadata: Optional metadata dict. If contains "message" key,
                     will be added to job.messages array

        Returns:
            Updated Job instance

        Raises:
            ValueError: If job not found or status transition invalid
        """
        with self.db_manager.get_session() as session:
            # Get job with tenant isolation
            job = self._get_job_or_raise(session, tenant_key, job_id)

            # Normalize inbound status aliases for DB write
            normalized_status = self._normalize_status(status)

            # Validate status transition
            if job.status != normalized_status:
                self._validate_status_transition(job.status, normalized_status)
                job.status = normalized_status

            # Add message if provided
            if metadata and "message" in metadata:
                message = self._create_message(metadata["message"])
                job.messages = job.messages + [message]

            session.commit()
            session.refresh(job)
            session.expunge(job)

        # Return caller-facing alias
        job.status = self._expose_status(job.status)

        logger.info(f"Updated job {job_id} status to {status} for tenant {tenant_key}")

        return job

    async def update_status(
        self,
        job_id: str,
        new_status: str,
        tenant_key: str,
    ) -> None:
        """
        Async version of update_job_status for WebSocket integration (Handover 0233 Phase 5).

        Updates job status and tracks mission_acknowledged_at when transitioning to 'working'.
        Emits WebSocket events for real-time UI updates.

        Args:
            job_id: Job ID to update
            new_status: New status (waiting, working, complete, failed, blocked, cancelled, decommissioned)
            tenant_key: Tenant key for isolation

        Raises:
            ValueError: If job not found or status transition invalid
        """
        from datetime import datetime, timezone
        from sqlalchemy import and_, select
        from giljo_mcp.models import MCPAgentJob

        async with self.db_manager.get_session_async() as session:
            # Get job with tenant isolation
            result = await session.execute(
                select(MCPAgentJob).where(
                    and_(
                        MCPAgentJob.job_id == job_id,
                        MCPAgentJob.tenant_key == tenant_key,
                    )
                )
            )
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

            normalized_status = self._normalize_status(new_status)

            # Validate status transition
            if job.status != normalized_status:
                self._validate_status_transition(job.status, normalized_status)
                job.status = normalized_status

            await session.commit()

        logger.info(f"Updated job {job_id} status to {new_status} for tenant {tenant_key}")

    def complete_job(
        self,
        tenant_key: str,
        job_id: str,
        result: Optional[dict[str, Any]] = None,
    ) -> Job:
        """
        Mark job as completed (active -> completed).

        Handover 0072: Automatically syncs task status to 'completed'.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID to complete
            result: Optional result data to store in messages

        Returns:
            Updated Job instance

        Raises:
            ValueError: If job not found or status transition invalid
        """
        with self.db_manager.get_session() as session:
            # Get job with tenant isolation
            job = self._get_job_or_raise(session, tenant_key, job_id)

            # Validate status transition
            self._validate_status_transition(job.status, "complete")

            # Update job
            job.status = "complete"
            job.completed_at = datetime.now(timezone.utc)

            # Add result as message
            if result:
                result_msg = self._create_message(
                    {
                        "role": "system",
                        "type": "completion",
                        "content": result,
                    }
                )
                job.messages = job.messages + [result_msg]

            # Handover 0072: Sync task status to completed
            self._sync_task_status(session, job, "completed")

            session.commit()
            session.refresh(job)
            session.expunge(job)

        # Present a friendly status alias without persisting to DB
        job.status = self._expose_status("complete")

        logger.info(f"Completed job {job_id} for tenant {tenant_key}")

        return job

    def fail_job(
        self,
        tenant_key: str,
        job_id: str,
        error: Optional[dict[str, Any]] = None,
        failure_reason: str = "error",
    ) -> MCPAgentJob:
        """
        Mark job as failed (waiting/working/blocked -> failed).

        Handover 0072: Automatically syncs task status to 'blocked'.
        Handover 0113: Added failure_reason parameter for categorizing failures.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID to fail
            error: Optional error data to store in messages
            failure_reason: Reason for failure - 'error', 'timeout', or 'system_error'

        Returns:
            Updated MCPAgentJob instance

        Raises:
            ValueError: If job not found, status transition invalid, or invalid failure_reason
        """
        # Validate failure_reason
        valid_reasons = {"error", "timeout", "system_error"}
        if failure_reason not in valid_reasons:
            raise ValueError(f"Invalid failure_reason '{failure_reason}'. Must be one of: {valid_reasons}")

        with self.db_manager.get_session() as session:
            # Get job with tenant isolation
            job = self._get_job_or_raise(session, tenant_key, job_id)

            # Validate status transition
            self._validate_status_transition(job.status, "failed")

            # Update job
            job.status = "failed"
            job.failure_reason = failure_reason
            job.completed_at = datetime.now(timezone.utc)

            # Add error as message
            if error:
                error_msg = self._create_message(
                    {
                        "role": "system",
                        "type": "error",
                        "content": error,
                        "failure_reason": failure_reason,
                    }
                )
                job.messages = job.messages + [error_msg]

            # Handover 0072: Sync task status to blocked
            self._sync_task_status(session, job, "blocked")

            session.commit()
            session.refresh(job)

        logger.info(f"Failed job {job_id} for tenant {tenant_key}: {failure_reason} - {error}")

        return job

    def continue_working(
        self,
        tenant_key: str,
        job_id: str,
    ) -> MCPAgentJob:
        """
        Resume a completed job (complete -> working).

        Handover 0113: Allows continuing work after project completion without closing out.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID to resume

        Returns:
            Updated MCPAgentJob instance

        Raises:
            ValueError: If job not found or status transition invalid
        """
        with self.db_manager.get_session() as session:
            # Get job with tenant isolation
            job = self._get_job_or_raise(session, tenant_key, job_id)

            # Validate status transition
            self._validate_status_transition(job.status, "working")

            # Update job
            job.status = "working"
            job.completed_at = None  # Clear completion timestamp
            job.started_at = datetime.now(timezone.utc)  # Update start time

            # Add system message
            resume_msg = self._create_message(
                {
                    "role": "system",
                    "type": "status_change",
                    "content": "Job resumed for continued work",
                    "previous_status": "complete",
                    "new_status": "working",
                }
            )
            job.messages = job.messages + [resume_msg]

            session.commit()
            session.refresh(job)

        logger.info(f"Resumed job {job_id} for tenant {tenant_key}")

        return job

    def decommission_job(
        self,
        tenant_key: str,
        job_id: str,
    ) -> MCPAgentJob:
        """
        Decommission a completed job (complete -> decommissioned).

        Handover 0113: Project closeout workflow - marks job as retired.
        Only jobs in 'complete' status can be decommissioned.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID to decommission

        Returns:
            Updated MCPAgentJob instance

        Raises:
            ValueError: If job not found or not in 'complete' status
        """
        with self.db_manager.get_session() as session:
            # Get job with tenant isolation
            job = self._get_job_or_raise(session, tenant_key, job_id)

            # Custom validation: Only completed jobs can be decommissioned
            if job.status != "complete":
                raise ValueError(
                    f"Only completed jobs can be decommissioned. "
                    f"Current status: '{job.status}'"
                )

            # Update job status and timestamp
            job.status = "decommissioned"
            job.decommissioned_at = datetime.now(timezone.utc)

            # Add system message for audit trail
            decommission_msg = self._create_message(
                {
                    "role": "system",
                    "type": "status_change",
                    "content": "Job decommissioned - project closeout",
                    "previous_status": "complete",
                    "new_status": "decommissioned",
                    "timestamp": job.decommissioned_at.isoformat(),
                }
            )
            job.messages = job.messages + [decommission_msg]

            session.commit()
            session.refresh(job)

        logger.info(f"Decommissioned job {job_id} for tenant {tenant_key}")

        return job

    def get_job(
        self,
        tenant_key: str,
        job_id: str,
    ) -> Optional[Job]:
        """
        Get a job by job_id with tenant isolation.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID to retrieve

        Returns:
            Job instance or None if not found
        """
        with self.db_manager.get_session() as session:
            stmt = select(Job).where(
                Job.tenant_key == tenant_key,
                Job.job_id == job_id,
            )
            job = session.execute(stmt).scalar_one_or_none()

            if job:
                # Detach from session before returning
                session.expunge(job)
                job.status = self._expose_status(job.status)

            return job

    def get_pending_jobs(
        self,
        tenant_key: str,
        agent_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Job]:
        """
        Get pending jobs with optional filters.

        Args:
            tenant_key: Tenant key for isolation
            agent_type: Optional filter by agent type
            limit: Optional limit on number of jobs returned

        Returns:
            List of pending Job instances
        """
        with self.db_manager.get_session() as session:
            stmt = select(Job).where(
                Job.tenant_key == tenant_key,
                Job.status == "waiting",
            )

            if agent_type:
                stmt = stmt.where(Job.agent_type == agent_type)

            # Order by created_at to get oldest first
            stmt = stmt.order_by(Job.created_at)

            if limit:
                stmt = stmt.limit(limit)

            jobs = session.execute(stmt).scalars().all()

            # Detach from session before returning
            for job in jobs:
                session.expunge(job)
                job.status = self._expose_status(job.status)

            return list(jobs)

    def get_active_jobs(
        self,
        tenant_key: str,
        agent_type: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[Job]:
        """
        Get active jobs with optional filters.

        Args:
            tenant_key: Tenant key for isolation
            agent_type: Optional filter by agent type
            limit: Optional limit on number of jobs returned

        Returns:
            List of active Job instances
        """
        with self.db_manager.get_session() as session:
            stmt = select(Job).where(
                Job.tenant_key == tenant_key,
                Job.status == "working",
            )

            if agent_type:
                stmt = stmt.where(Job.agent_type == agent_type)

            # Order by started_at to get oldest first
            stmt = stmt.order_by(Job.started_at)

            if limit:
                stmt = stmt.limit(limit)

            jobs = session.execute(stmt).scalars().all()

            # Detach from session before returning
            for job in jobs:
                session.expunge(job)
                job.status = self._expose_status(job.status)

            return list(jobs)

    def get_job_hierarchy(
        self,
        tenant_key: str,
        job_id: str,
    ) -> Optional[dict[str, Any]]:
        """
        Get job hierarchy (parent job + all child jobs).

        Args:
            tenant_key: Tenant key for isolation
            job_id: Parent job ID

        Returns:
            Dict with "parent" and "children" keys, or None if parent not found
        """
        with self.db_manager.get_session() as session:
            # Get parent job
            parent_stmt = select(Job).where(
                Job.tenant_key == tenant_key,
                Job.job_id == job_id,
            )
            parent = session.execute(parent_stmt).scalar_one_or_none()

            if not parent:
                return None

            # Get child jobs spawned by this parent
            children_stmt = (
                select(Job)
                .where(
                    Job.tenant_key == tenant_key,
                    Job.spawned_by == job_id,
                )
                .order_by(Job.created_at)
            )

            children = session.execute(children_stmt).scalars().all()

            # Detach from session before returning
            session.expunge(parent)
            parent.status = self._expose_status(parent.status)
            for child in children:
                session.expunge(child)
                child.status = self._expose_status(child.status)

            return {
                "parent": parent,
                "children": list(children),
            }

    def _get_job_or_raise(
        self,
        session: Session,
        tenant_key: str,
        job_id: str,
    ) -> Job:
        """
        Get job or raise ValueError if not found.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to retrieve

        Returns:
            Job instance

        Raises:
            ValueError: If job not found for this tenant
        """
        stmt = select(Job).where(
            Job.tenant_key == tenant_key,
            Job.job_id == job_id,
        )
        job = session.execute(stmt).scalar_one_or_none()

        if not job:
            raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

        return job

    def _validate_status_transition(
        self,
        current_status: str,
        new_status: str,
    ) -> None:
        """
        Validate status transition.

        Args:
            current_status: Current job status
            new_status: Desired new status

        Raises:
            ValueError: If status transition is invalid
        """
        normalized_current = self._normalize_status(current_status)
        normalized_new = self._normalize_status(new_status)

        valid_transitions = self.VALID_TRANSITIONS.get(normalized_current, set())

        if normalized_new not in valid_transitions:
            raise ValueError(
                f"Invalid status transition from '{normalized_current}' to '{normalized_new}'. "
                f"Valid transitions: {valid_transitions or 'none (terminal state)'}"
            )

    def _create_message(
        self,
        content: Any,
    ) -> dict[str, Any]:
        """
        Create a message object with timestamp.

        Args:
            content: Message content (can be dict or any JSON-serializable type)

        Returns:
            Message dict with timestamp
        """
        message = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        # If content is already a dict, merge it
        if isinstance(content, dict):
            message.update(content)
        else:
            message["content"] = content

        return message

    def _sync_task_status(
        self,
        session,
        job: Job,
        task_status: str,
    ) -> None:
        """
        Synchronize task status when agent job status changes (Handover 0072).

        This enables bidirectional status synchronization between tasks and agent jobs.
        Called automatically when jobs complete or fail.

        Args:
            session: Database session
            job: Job instance
            task_status: Target task status (completed, blocked, etc.)
        """
        from giljo_mcp.models import Task

        try:
            # Find tasks linked to this agent job
            task_query = select(Task).where(and_(Task.agent_job_id == job.job_id, Task.tenant_key == job.tenant_key))
            task_result = session.execute(task_query)
            task = task_result.scalar_one_or_none()

            if task:
                # Update task status
                task.status = task_status

                if task_status == "completed":
                    task.completed_at = datetime.now(timezone.utc)
                    logger.info(f"Task {task.id} marked completed (agent job {job.job_id} finished)")
                elif task_status == "blocked":
                    logger.info(f"Task {task.id} marked blocked (agent job {job.job_id} failed)")

                # Note: We don't commit here - caller is responsible for commit
            else:
                # No task linked to this job - that's fine
                logger.debug(f"No task linked to agent job {job.job_id}")

        except Exception as e:
            logger.error(f"Failed to sync task status for job {job.job_id}: {e}")
            # Don't raise - status sync is best-effort, don't fail the job operation


# Handover 0107: Job Cancellation Functions


async def request_job_cancellation(
    tenant_key: str,
    job_id: str,
    reason: str,
    db_manager: "DatabaseManager",
) -> dict:
    """
    Request graceful cancellation of an agent job (Handover 0107).

    Sets job status to "cancelling" and sends a high-priority cancel message
    to the agent, allowing it to clean up gracefully.

    Args:
        tenant_key: Tenant key for isolation
        job_id: Job ID to cancel
        reason: Reason for cancellation (logged for audit trail)
        db_manager: DatabaseManager instance (injected)

    Returns:
        dict: {
            "success": bool,
            "job_id": str,
            "status": str,
            "message": str
        }

    Raises:
        ValueError: If job not found or invalid parameters
    """
    try:
        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key cannot be empty")

        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        if not reason or not reason.strip():
            raise ValueError("reason cannot be empty")

        # Import required modules
        from .models import MCPAgentJob

        # Try to import websocket_manager, but make it optional for testing
        try:
            from api.websocket import websocket_manager
        except (ImportError, AttributeError):
            websocket_manager = None

        async with db_manager.get_session_async() as session:
            # Get job with tenant isolation
            stmt = select(MCPAgentJob).where(
                MCPAgentJob.tenant_key == tenant_key,
                MCPAgentJob.job_id == job_id,
            )
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

            # Check if job is already in terminal state
            if job.status in ("complete", "failed"):
                return {
                    "success": False,
                    "job_id": job_id,
                    "status": job.status,
                    "message": f"Cannot cancel job in terminal state '{job.status}'",
                }

            # Set status to "cancelled" (Handover 0113: 7-state model, no "cancelling" state)
            old_status = job.status
            job.status = "cancelled"

            # Send cancel message via messages array
            cancel_message = {
                "id": str(datetime.now(timezone.utc).timestamp()),
                "type": "cancel",
                "priority": "critical",
                "reason": reason,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "status": "pending",
            }

            if job.messages is None:
                job.messages = []
            job.messages.append(cancel_message)

            # Commit changes
            await session.commit()
            await session.refresh(job)

            # Broadcast WebSocket event (optional - may be None in tests)
            if websocket_manager:
                try:
                    await websocket_manager.broadcast(
                    {
                        "type": "job:status_changed",
                        "job_id": job_id,
                        "tenant_key": tenant_key,
                        "old_status": old_status,
                        "new_status": "cancelled",
                        "reason": reason,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    )
                except Exception as ws_error:
                    logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")
                    # Non-critical - continue without WebSocket broadcast

            logger.info(
                f"[request_job_cancellation] Job {job_id} cancellation requested: {reason}, tenant={tenant_key}"
            )

            return {
                "success": True,
                "job_id": job_id,
                "status": "cancelled",
                "message": f"Cancellation requested: {reason}",
            }

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[request_job_cancellation] Error requesting cancellation: {e}", exc_info=True)
        raise ValueError(f"Failed to request job cancellation: {e!s}")


async def force_fail_job(
    tenant_key: str,
    job_id: str,
    reason: str,
    db_manager: "DatabaseManager",
) -> dict:
    """
    Force-fail an agent job without waiting for graceful shutdown (Handover 0107).

    Immediately marks job as failed. Use this when agent is unresponsive
    or cancellation request has timed out.

    Args:
        tenant_key: Tenant key for isolation
        job_id: Job ID to force-fail
        reason: Reason for forced failure (logged for audit trail)
        db_manager: DatabaseManager instance (injected)

    Returns:
        dict: {
            "success": bool,
            "job_id": str,
            "status": str,
            "message": str
        }

    Raises:
        ValueError: If job not found or invalid parameters
    """
    try:
        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key cannot be empty")

        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        if not reason or not reason.strip():
            raise ValueError("reason cannot be empty")

        # Import required modules
        from .models import MCPAgentJob

        # Try to import websocket_manager, but make it optional for testing
        try:
            from api.websocket import websocket_manager
        except (ImportError, AttributeError):
            websocket_manager = None

        async with db_manager.get_session_async() as session:
            # Get job with tenant isolation
            stmt = select(MCPAgentJob).where(
                MCPAgentJob.tenant_key == tenant_key,
                MCPAgentJob.job_id == job_id,
            )
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

            # Check if job is already failed
            if job.status == "failed":
                return {
                    "success": False,
                    "job_id": job_id,
                    "status": "failed",
                    "message": "Job is already failed",
                }

            # Mark job as failed
            old_status = job.status
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)

            # Add forced failure message
            failure_message = {
                "id": str(datetime.now(timezone.utc).timestamp()),
                "type": "forced_failure",
                "reason": reason,
                "forced_by": "system",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            if job.messages is None:
                job.messages = []
            job.messages.append(failure_message)

            # Commit changes
            await session.commit()
            await session.refresh(job)

            # Broadcast WebSocket event (optional - may be None in tests)
            if websocket_manager:
                try:
                    await websocket_manager.broadcast(
                    {
                        "type": "job:status_changed",
                        "job_id": job_id,
                        "tenant_key": tenant_key,
                        "old_status": old_status,
                        "new_status": "failed",
                        "reason": reason,
                        "forced": True,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    }
                    )
                except Exception as ws_error:
                    logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")
                    # Non-critical - continue without WebSocket broadcast

            logger.warning(
                f"[force_fail_job] Job {job_id} force-failed: {reason}, tenant={tenant_key}"
            )

            return {
                "success": True,
                "job_id": job_id,
                "status": "failed",
                "message": f"Job force-failed: {reason}",
            }

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[force_fail_job] Error force-failing job: {e}", exc_info=True)
        raise ValueError(f"Failed to force-fail job: {e!s}")
