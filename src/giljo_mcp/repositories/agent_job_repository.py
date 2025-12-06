"""
Agent job repository for Job operations.

Handover 0017: Provides agent job coordination and lifecycle management.
Separate from user tasks - handles agent-to-agent job coordination for agentic orchestration.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from ..models import Job
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
        self.base_repo = BaseRepository(Job, db_manager)

    def create_job(
        self,
        session: Session,
        tenant_key: str,
        agent_type: str,
        mission: str,
        spawned_by: Optional[str] = None,
        context_chunks: Optional[List[str]] = None,
    ) -> Job:
        """
        Create a new agent job.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            agent_type: Type of agent (orchestrator, analyzer, implementer, etc.)
            mission: Agent mission/instructions
            spawned_by: Optional agent ID that spawned this job
            context_chunks: Optional list of chunk IDs for context loading

        Returns:
            Created Job instance
        """
        return self.base_repo.create(
            session,
            tenant_key,
            agent_type=agent_type,
            mission=mission,
            status="pending",
            spawned_by=spawned_by,
            context_chunks=context_chunks or [],
        )

    async def get_job_by_job_id(self, session: AsyncSession, tenant_key: str, job_id: str) -> Optional[Job]:
        """
        Get a job by its job_id.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to retrieve

        Returns:
            Job instance or None if not found
        """
        result = await session.execute(select(Job).where(Job.tenant_key == tenant_key, Job.job_id == job_id))
        return result.scalar_one_or_none()

    async def update_status(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> bool:
        """
        Update job status with optional timestamps.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to update
            status: New status (pending, active, completed, failed)
            started_at: Optional start timestamp for active status
            completed_at: Optional completion timestamp

        Returns:
            True if job was updated, False if not found
        """
        result = await session.execute(select(Job).where(Job.tenant_key == tenant_key, Job.job_id == job_id))
        job = result.scalar_one_or_none()

        if job:
            job.status = status
            if started_at:
                job.started_at = started_at
            elif status == "active" and not job.started_at:
                job.started_at = datetime.utcnow()

            if completed_at:
                job.completed_at = completed_at
            elif status in ["completed", "failed"] and not job.completed_at:
                job.completed_at = datetime.utcnow()

            await session.flush()
            return True
        return False

    async def get_active_jobs(self, session: AsyncSession, tenant_key: str, agent_type: Optional[str] = None) -> List[Job]:
        """
        Get all active jobs (pending or active status).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_type: Optional filter by agent type

        Returns:
            List of active Job instances
        """
        stmt = select(Job).where(Job.tenant_key == tenant_key, Job.status.in_(["pending", "active"]))

        if agent_type:
            stmt = stmt.where(Job.agent_type == agent_type)

        stmt = stmt.order_by(Job.created_at)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_jobs_by_status(self, session: AsyncSession, tenant_key: str, status: str) -> List[Job]:
        """
        Get all jobs with a specific status.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            status: Status to filter by

        Returns:
            List of Job instances with the specified status
        """
        result = await session.execute(
            select(Job).where(Job.tenant_key == tenant_key, Job.status == status).order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_jobs_by_spawner(self, session: AsyncSession, tenant_key: str, spawned_by: str) -> List[Job]:
        """
        Get all jobs spawned by a specific agent.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            spawned_by: Agent ID that spawned jobs

        Returns:
            List of Job instances spawned by the agent
        """
        result = await session.execute(
            select(Job).where(Job.tenant_key == tenant_key, Job.spawned_by == spawned_by).order_by(Job.created_at.desc())
        )
        return list(result.scalars().all())

    async def add_message(self, session: AsyncSession, tenant_key: str, job_id: str, message: Dict[str, Any]) -> bool:
        """
        Add message to job's message array.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to add message to
            message: Message object to add

        Returns:
            True if message was added, False if job not found
        """
        result = await session.execute(select(Job).where(Job.tenant_key == tenant_key, Job.job_id == job_id))
        job = result.scalar_one_or_none()

        if job:
            # Ensure messages is a list
            messages = list(job.messages or [])

            # Add timestamp if not present
            if "timestamp" not in message:
                message["timestamp"] = datetime.utcnow().isoformat()

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
            job_id: Job ID to acknowledge

        Returns:
            True if job was acknowledged, False if not found
        """
        result = await session.execute(select(Job).where(Job.tenant_key == tenant_key, Job.job_id == job_id))
        job = result.scalar_one_or_none()

        if job:
            # Transition to active status (acknowledgment is implicit in status change)
            if job.status == "pending":
                job.status = "active"
                if not job.started_at:
                    job.started_at = datetime.utcnow()
            await session.flush()
            return True
        return False

    async def add_context_chunk(self, session: AsyncSession, tenant_key: str, job_id: str, chunk_id: str) -> bool:
        """
        Add a context chunk ID to the job.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to add chunk to
            chunk_id: Chunk ID to add

        Returns:
            True if chunk was added, False if job not found
        """
        result = await session.execute(select(Job).where(Job.tenant_key == tenant_key, Job.job_id == job_id))
        job = result.scalar_one_or_none()

        if job:
            context_chunks = list(job.context_chunks or [])
            if chunk_id not in context_chunks:
                context_chunks.append(chunk_id)
                job.context_chunks = context_chunks
                await session.flush()
            return True
        return False

    async def get_job_statistics(self, session: AsyncSession, tenant_key: str, agent_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get job statistics for a tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_type: Optional filter by agent type

        Returns:
            Dictionary with job statistics
        """
        # Count total jobs
        stmt = select(func.count()).select_from(Job).where(Job.tenant_key == tenant_key)
        if agent_type:
            stmt = stmt.where(Job.agent_type == agent_type)
        result = await session.execute(stmt)
        total_jobs = result.scalar()

        # Count by status
        status_stmt = select(Job.status, func.count(Job.id)).where(Job.tenant_key == tenant_key)
        if agent_type:
            status_stmt = status_stmt.where(Job.agent_type == agent_type)
        status_stmt = status_stmt.group_by(Job.status)
        result = await session.execute(status_stmt)
        status_counts = result.all()

        # Count by agent type
        type_stmt = select(Job.agent_type, func.count(Job.id)).where(Job.tenant_key == tenant_key).group_by(Job.agent_type)
        result = await session.execute(type_stmt)
        type_counts = result.all()

        return {
            "total_jobs": total_jobs,
            "by_status": {status: count for status, count in status_counts},
            "by_agent_type": {agent_type: count for agent_type, count in type_counts},
            "active_jobs": len([s for s, c in status_counts if s in ["pending", "active"]]),
            "completed_jobs": len([s for s, c in status_counts if s == "completed"]),
            "failed_jobs": len([s for s, c in status_counts if s == "failed"]),
        }
