"""
Agent job repository for AgentJob operations.

Handover 0017: Provides agent job coordination and lifecycle management.
Separate from user tasks - handles agent-to-agent job coordination for agentic orchestration.
"""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

from .base import BaseRepository


class AgentJobRepository:
    """
    Repository for agent job management.

    Handles the complete lifecycle of agent jobs from creation to completion,
    including status transitions, message handling, and context chunk management.
    """

    def __init__(self, db_manager):
        """
        Initialize agent job repository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager
        self.base_repo = BaseRepository(AgentJob, db_manager)

    def create_job(
        self,
        session: Session,
        tenant_key: str,
        agent_display_name: str,
        mission: str,
        spawned_by: str | None = None,
        context_chunks: list[str | None] = None,
    ) -> AgentJob:
        """
        Create a new agent job.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            agent_display_name: Display name of agent (UI label - what humans see)
            mission: Agent mission/instructions
            spawned_by: Optional agent ID that spawned this job
            context_chunks: Optional list of chunk IDs for context loading

        Returns:
            Created AgentJob instance
        """
        return self.base_repo.create(
            session,
            tenant_key,
            agent_display_name=agent_display_name,
            mission=mission,
            status="pending",
            spawned_by=spawned_by,
            context_chunks=context_chunks or [],
        )

    async def get_job_by_job_id(self, session: AsyncSession, tenant_key: str, job_id: str) -> AgentJob | None:
        """
        Get a job by its job_id.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID to retrieve

        Returns:
            AgentJob instance or None if not found
        """
        result = await session.execute(
            select(AgentJob).where(AgentJob.tenant_key == tenant_key, AgentJob.job_id == job_id)
        )
        return result.scalar_one_or_none()

    async def update_status(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
        status: str,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> bool:
        """
        Update job status with optional timestamps.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID to update
            status: New status (pending, active, completed, failed)
            started_at: Optional start timestamp for active status
            completed_at: Optional completion timestamp

        Returns:
            True if job was updated, False if not found
        """
        result = await session.execute(
            select(AgentJob).where(AgentJob.tenant_key == tenant_key, AgentJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if job:
            job.status = status
            if started_at:
                job.started_at = started_at
            elif status == "active" and not job.started_at:
                job.started_at = datetime.now(timezone.utc)

            if completed_at:
                job.completed_at = completed_at
            elif status in ["completed", "failed"] and not job.completed_at:
                job.completed_at = datetime.now(timezone.utc)

            await session.flush()
            return True
        return False

    async def get_active_jobs(
        self, session: AsyncSession, tenant_key: str, agent_display_name: str | None = None
    ) -> list[AgentJob]:
        """
        Get all active jobs (pending or active status).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_display_name: Optional filter by agent display name

        Returns:
            List of active AgentJob instances
        """
        stmt = select(AgentJob).where(AgentJob.tenant_key == tenant_key, AgentJob.status.in_(["pending", "active"]))

        if agent_display_name:
            stmt = stmt.where(AgentJob.agent_display_name == agent_display_name)

        stmt = stmt.order_by(AgentJob.created_at)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_jobs_by_status(self, session: AsyncSession, tenant_key: str, status: str) -> list[AgentJob]:
        """
        Get all jobs with a specific status.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            status: Status to filter by

        Returns:
            List of AgentJob instances with the specified status
        """
        result = await session.execute(
            select(AgentJob)
            .where(AgentJob.tenant_key == tenant_key, AgentJob.status == status)
            .order_by(AgentJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_jobs_by_spawner(self, session: AsyncSession, tenant_key: str, spawned_by: str) -> list[AgentJob]:
        """
        Get all jobs spawned by a specific agent.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            spawned_by: Agent ID that spawned jobs

        Returns:
            List of AgentJob instances spawned by the agent
        """
        result = await session.execute(
            select(AgentJob)
            .where(AgentJob.tenant_key == tenant_key, AgentJob.spawned_by == spawned_by)
            .order_by(AgentJob.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_message(self, session: AsyncSession, tenant_key: str, job_id: str, message: dict[str, Any]) -> bool:
        """
        Add message to job's message array.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID to add message to
            message: Message object to add

        Returns:
            True if message was added, False if job not found
        """
        result = await session.execute(
            select(AgentJob).where(AgentJob.tenant_key == tenant_key, AgentJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if job:
            # Ensure messages is a list
            messages = list(job.messages or [])

            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.now(timezone.utc).isoformat()

            messages.append(message)
            job.messages = messages
            await session.flush()
            return True
        return False

    async def acknowledge_job(self, session: AsyncSession, tenant_key: str, job_id: str) -> bool:
        """
        Mark job as acknowledged (transition to active status).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID to acknowledge

        Returns:
            True if job was acknowledged, False if not found
        """
        result = await session.execute(
            select(AgentJob).where(AgentJob.tenant_key == tenant_key, AgentJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if job:
            # Transition to active status (acknowledgment is implicit in status change)
            if job.status == "pending":
                job.status = "active"
                if not job.started_at:
                    job.started_at = datetime.now(timezone.utc)
            await session.flush()
            return True
        return False

    async def add_context_chunk(self, session: AsyncSession, tenant_key: str, job_id: str, chunk_id: str) -> bool:
        """
        Add a context chunk ID to the job.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: AgentJob ID to add chunk to
            chunk_id: Chunk ID to add

        Returns:
            True if chunk was added, False if job not found
        """
        result = await session.execute(
            select(AgentJob).where(AgentJob.tenant_key == tenant_key, AgentJob.job_id == job_id)
        )
        job = result.scalar_one_or_none()

        if job:
            context_chunks = list(job.context_chunks or [])
            if chunk_id not in context_chunks:
                context_chunks.append(chunk_id)
                job.context_chunks = context_chunks
                await session.flush()
            return True
        return False

    async def get_job_statistics(
        self, session: AsyncSession, tenant_key: str, agent_display_name: str | None = None
    ) -> dict[str, Any]:
        """
        Get job statistics for a tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_display_name: Optional filter by agent display name

        Returns:
            Dictionary with job statistics
        """
        # Count total jobs
        stmt = select(func.count()).select_from(AgentJob).where(AgentJob.tenant_key == tenant_key)
        if agent_display_name:
            stmt = stmt.where(AgentJob.agent_display_name == agent_display_name)
        result = await session.execute(stmt)
        total_jobs = result.scalar()

        # Count by status
        status_stmt = select(AgentJob.status, func.count(AgentJob.id)).where(AgentJob.tenant_key == tenant_key)
        if agent_display_name:
            status_stmt = status_stmt.where(AgentJob.agent_display_name == agent_display_name)
        status_stmt = status_stmt.group_by(AgentJob.status)
        result = await session.execute(status_stmt)
        status_counts = result.all()

        # Count by agent display name
        type_stmt = (
            select(AgentJob.agent_display_name, func.count(AgentJob.id))
            .where(AgentJob.tenant_key == tenant_key)
            .group_by(AgentJob.agent_display_name)
        )
        result = await session.execute(type_stmt)
        type_counts = result.all()

        return {
            "total_jobs": total_jobs,
            "by_status": {status: count for status, count in status_counts},
            "by_agent_display_name": {agent_display_name: count for agent_display_name, count in type_counts},
            "active_jobs": len([s for s, c in status_counts if s in ["pending", "active"]]),
            "completed_jobs": len([s for s, c in status_counts if s == "completed"]),
            "failed_jobs": len([s for s, c in status_counts if s == "failed"]),
        }

    # ============================================================================
    # Agent Execution & AgentJob Methods (Handover 1011 - Phase 4)
    # ============================================================================

    async def get_execution_by_agent_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_id: str,
    ) -> "AgentExecution" | None:
        """
        Get agent execution by agent_id with tenant isolation.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation (REQUIRED)
            agent_id: Agent ID to retrieve

        Returns:
            AgentExecution instance or None if not found

        Example:
            >>> execution = await repo.get_execution_by_agent_id(session, "tenant-1", "agent-123")
            >>> if execution:
            ...     print(execution.status)
        """
        # ORIGINAL QUERY: operations.py lines 226-230 (get_job_health endpoint)
        stmt = select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.agent_id == agent_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_execution_by_job_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> "AgentExecution" | None:
        """
        Get agent execution by job_id with tenant isolation (fallback lookup).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation (REQUIRED)
            job_id: AgentJob ID to retrieve execution for

        Returns:
            AgentExecution instance or None if not found

        Example:
            >>> execution = await repo.get_execution_by_job_id(session, "tenant-1", "job-456")
        """
        # ORIGINAL QUERY: operations.py lines 235-239 (get_job_health endpoint fallback)
        stmt = select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.job_id == job_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_agent_job_by_job_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> "AgentJob" | None:
        """
        Get agent job by job_id with tenant isolation.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation (REQUIRED)
            job_id: AgentJob ID to retrieve

        Returns:
            AgentJob instance or None if not found

        Example:
            >>> job = await repo.get_agent_job_by_job_id(session, "tenant-1", "job-789")
            >>> if job:
            ...     print(job.mission)
        """
        # ORIGINAL QUERY: operations.py lines 318-322 (update_agent_mission endpoint)
        stmt = select(AgentJob).where(
            AgentJob.tenant_key == tenant_key,
            AgentJob.job_id == job_id,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_execution_for_job(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> "AgentExecution" | None:
        """
        Get the latest execution instance for a job (by started_at desc).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation (REQUIRED)
            job_id: AgentJob ID to get latest execution for

        Returns:
            Latest AgentExecution instance or None if not found

        Example:
            >>> execution = await repo.get_latest_execution_for_job(session, "tenant-1", "job-123")
            >>> if execution:
            ...     print(f"Status: {execution.status}")
        """
        # ORIGINAL QUERY: operations.py lines 343-348 (update_agent_mission WebSocket event)
        stmt = (
            select(AgentExecution)
            .where(
                AgentExecution.job_id == job_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .order_by(AgentExecution.started_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ============================================================================
    # Message Counter Methods (Handover 0387e)
    # ============================================================================

    async def increment_sent_count(
        self,
        session: AsyncSession,
        agent_id: str,
        tenant_key: str,
    ) -> None:
        """
        Atomically increment messages_sent_count by 1.

        Args:
            session: Async database session
            agent_id: Agent ID to increment counter for
            tenant_key: Tenant key for isolation (REQUIRED)

        Example:
            >>> await repo.increment_sent_count(session, "agent-123", "tenant-1")
        """
        from giljo_mcp.models.agent_identity import AgentExecution

        stmt = (
            update(AgentExecution)
            .where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .values(messages_sent_count=AgentExecution.messages_sent_count + 1)
        )
        await session.execute(stmt)
        await session.commit()

    async def increment_waiting_count(
        self,
        session: AsyncSession,
        agent_id: str,
        tenant_key: str,
    ) -> None:
        """
        Atomically increment messages_waiting_count by 1.

        Args:
            session: Async database session
            agent_id: Agent ID to increment counter for
            tenant_key: Tenant key for isolation (REQUIRED)

        Example:
            >>> await repo.increment_waiting_count(session, "agent-123", "tenant-1")
        """
        from giljo_mcp.models.agent_identity import AgentExecution

        stmt = (
            update(AgentExecution)
            .where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .values(messages_waiting_count=AgentExecution.messages_waiting_count + 1)
        )
        await session.execute(stmt)
        await session.commit()

    async def decrement_waiting_increment_read(
        self,
        session: AsyncSession,
        agent_id: str,
        tenant_key: str,
    ) -> None:
        """
        Atomically decrement waiting count and increment read count.

        Uses GREATEST(0, count-1) to prevent negative values.

        Args:
            session: Async database session
            agent_id: Agent ID to update counters for
            tenant_key: Tenant key for isolation (REQUIRED)

        Example:
            >>> await repo.decrement_waiting_increment_read(session, "agent-123", "tenant-1")
        """
        from giljo_mcp.models.agent_identity import AgentExecution

        stmt = (
            update(AgentExecution)
            .where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            .values(
                messages_waiting_count=func.greatest(0, AgentExecution.messages_waiting_count - 1),
                messages_read_count=AgentExecution.messages_read_count + 1,
            )
        )
        await session.execute(stmt)
        await session.commit()
