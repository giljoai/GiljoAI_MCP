"""
Agent job repository for AgentJob operations.

Handover 0017: Provides agent job coordination and lifecycle management.
Separate from user tasks - handles agent-to-agent job coordination for agentic orchestration.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

from .base import BaseRepository


class AgentJobRepository:
    """
    Repository for agent job management.

    Handles the complete lifecycle of agent jobs from creation to completion,
    including status transitions and execution tracking.
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
        mission: str,
        job_type: str,
        project_id: str | None = None,
        job_metadata: dict | None = None,
        template_id: str | None = None,
        phase: int | None = None,
    ) -> AgentJob:
        """
        Create a new agent job.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            mission: Agent mission/instructions
            job_type: Job type (orchestrator, analyzer, implementer, tester, etc.)
            project_id: Optional project ID
            job_metadata: Optional job-level metadata
            template_id: Optional template ID
            phase: Optional execution phase for multi-terminal ordering

        Returns:
            Created AgentJob instance
        """
        return self.base_repo.create(
            session,
            tenant_key,
            mission=mission,
            job_type=job_type,
            status="active",
            project_id=project_id,
            job_metadata=job_metadata or {},
            template_id=template_id,
            phase=phase,
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
            status: New status (active, completed, cancelled)
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
            elif status in ["completed", "cancelled"] and not job.completed_at:
                job.completed_at = datetime.now(timezone.utc)

            await session.flush()
            return True
        return False

    async def get_active_jobs(self, session: AsyncSession, tenant_key: str) -> list[AgentJob]:
        """
        Get all active jobs.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            List of active AgentJob instances
        """
        stmt = select(AgentJob).where(AgentJob.tenant_key == tenant_key, AgentJob.status == "active")
        stmt = stmt.order_by(AgentJob.created_at)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ============================================================================
    # Agent Execution & AgentJob Methods (Handover 1011 - Phase 4)
    # ============================================================================

    async def get_execution_by_agent_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_id: str,
    ) -> AgentExecution | None:
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
    ) -> AgentExecution | None:
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
    ) -> AgentJob | None:
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
    ) -> AgentExecution | None:
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
