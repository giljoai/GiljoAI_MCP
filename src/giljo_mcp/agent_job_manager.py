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
from .models import Job


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

    Valid status transitions:
    - pending -> active (via acknowledge_job)
    - pending -> failed (via fail_job)
    - pending -> blocked (via fail_job, Handover 0066)
    - active -> completed (via complete_job)
    - active -> failed (via fail_job)
    - active -> blocked (via fail_job, Handover 0066)
    - completed -> [terminal state, no transitions]
    - failed -> [terminal state, no transitions]
    - blocked -> [terminal state, no transitions] (Handover 0066)
    """

    # Valid status transitions
    VALID_TRANSITIONS = {
        "pending": {"active", "failed", "blocked"},
        "active": {"completed", "failed", "blocked"},
        "completed": set(),  # Terminal state
        "failed": set(),  # Terminal state
        "blocked": set(),  # Terminal state (Handover 0066)
    }

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
    ) -> Job:
        """
        Create a new agent job.

        Args:
            tenant_key: Tenant key for isolation
            agent_type: Type of agent (orchestrator, implementer, tester, etc.)
            mission: Mission/instructions for the agent
            spawned_by: Optional job_id of parent job that spawned this job
            context_chunks: Optional list of chunk_ids for context loading

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
            status="pending",
            spawned_by=spawned_by,
            context_chunks=context_chunks or [],
            messages=[],
            acknowledged=False,
        )

        with self.db_manager.get_session() as session:
            session.add(job)
            session.commit()
            session.refresh(job)

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
                    status="pending",
                    spawned_by=spec.get("spawned_by"),
                    context_chunks=spec.get("context_chunks", []),
                    messages=[],
                    acknowledged=False,
                )
                session.add(job)
                jobs.append(job)

            session.commit()

            # Refresh all jobs to get IDs
            for job in jobs:
                session.refresh(job)

        logger.info(f"Created batch of {len(jobs)} jobs for tenant {tenant_key}")

        return jobs

    def acknowledge_job(
        self,
        tenant_key: str,
        job_id: str,
    ) -> Job:
        """
        Acknowledge a job (pending -> active).

        Sets acknowledged=True, status=active, and started_at timestamp.

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

            # If already acknowledged, return as-is (idempotent)
            if job.acknowledged and job.status == "active":
                logger.info(f"Job {job_id} already acknowledged, returning current state")
                return job

            # Validate status transition
            if job.status != "pending":
                self._validate_status_transition(job.status, "active")

            # Update job
            job.acknowledged = True
            job.status = "active"
            job.started_at = datetime.now(timezone.utc)

            session.commit()
            session.refresh(job)

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

            # Validate status transition
            if job.status != status:
                self._validate_status_transition(job.status, status)
                job.status = status

            # Add message if provided
            if metadata and "message" in metadata:
                message = self._create_message(metadata["message"])
                job.messages = job.messages + [message]

            session.commit()
            session.refresh(job)

        logger.info(f"Updated job {job_id} status to {status} for tenant {tenant_key}")

        return job

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
            self._validate_status_transition(job.status, "completed")

            # Update job
            job.status = "completed"
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

        logger.info(f"Completed job {job_id} for tenant {tenant_key}")

        return job

    def fail_job(
        self,
        tenant_key: str,
        job_id: str,
        error: Optional[dict[str, Any]] = None,
    ) -> Job:
        """
        Mark job as failed (pending/active -> failed).

        Handover 0072: Automatically syncs task status to 'blocked'.

        Args:
            tenant_key: Tenant key for isolation
            job_id: Job ID to fail
            error: Optional error data to store in messages

        Returns:
            Updated Job instance

        Raises:
            ValueError: If job not found or status transition invalid
        """
        with self.db_manager.get_session() as session:
            # Get job with tenant isolation
            job = self._get_job_or_raise(session, tenant_key, job_id)

            # Validate status transition
            self._validate_status_transition(job.status, "failed")

            # Update job
            job.status = "failed"
            job.completed_at = datetime.now(timezone.utc)

            # Add error as message
            if error:
                error_msg = self._create_message(
                    {
                        "role": "system",
                        "type": "error",
                        "content": error,
                    }
                )
                job.messages = job.messages + [error_msg]

            # Handover 0072: Sync task status to blocked
            self._sync_task_status(session, job, "blocked")

            session.commit()
            session.refresh(job)

        logger.info(f"Failed job {job_id} for tenant {tenant_key}: {error}")

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
                Job.status == "pending",
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
                Job.status == "active",
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
            for child in children:
                session.expunge(child)

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
        valid_transitions = self.VALID_TRANSITIONS.get(current_status, set())

        if new_status not in valid_transitions:
            raise ValueError(
                f"Invalid status transition from '{current_status}' to '{new_status}'. "
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
