"""
Agent job repository for MCPAgentJob operations.

Handover 0017: Provides agent job coordination and lifecycle management.
Separate from user tasks - handles agent-to-agent job coordination for agentic orchestration.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import MCPAgentJob
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
        self.base_repo = BaseRepository(MCPAgentJob, db_manager)

    def create_job(self, session: Session, tenant_key: str,
                   agent_type: str, mission: str,
                   spawned_by: Optional[str] = None,
                   context_chunks: Optional[List[str]] = None) -> MCPAgentJob:
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
            Created MCPAgentJob instance
        """
        return self.base_repo.create(
            session, tenant_key,
            agent_type=agent_type,
            mission=mission,
            status="pending",
            spawned_by=spawned_by,
            context_chunks=context_chunks or []
        )

    def get_job_by_job_id(self, session: Session, tenant_key: str,
                          job_id: str) -> Optional[MCPAgentJob]:
        """
        Get a job by its job_id.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to retrieve

        Returns:
            MCPAgentJob instance or None if not found
        """
        return session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.job_id == job_id
        ).first()

    def update_status(self, session: Session, tenant_key: str,
                      job_id: str, status: str,
                      started_at: Optional[datetime] = None,
                      completed_at: Optional[datetime] = None) -> bool:
        """
        Update job status with optional timestamps.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to update
            status: New status (pending, active, completed, failed)
            started_at: Optional start timestamp for active status
            completed_at: Optional completion timestamp

        Returns:
            True if job was updated, False if not found
        """
        job = session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.job_id == job_id
        ).first()

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

            session.flush()
            return True
        return False

    def get_active_jobs(self, session: Session, tenant_key: str,
                        agent_type: Optional[str] = None) -> List[MCPAgentJob]:
        """
        Get all active jobs (pending or active status).

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            agent_type: Optional filter by agent type

        Returns:
            List of active MCPAgentJob instances
        """
        query = session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.status.in_(["pending", "active"])
        )

        if agent_type:
            query = query.filter(MCPAgentJob.agent_type == agent_type)

        return query.order_by(MCPAgentJob.created_at).all()

    def get_jobs_by_status(self, session: Session, tenant_key: str,
                           status: str) -> List[MCPAgentJob]:
        """
        Get all jobs with a specific status.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            status: Status to filter by

        Returns:
            List of MCPAgentJob instances with the specified status
        """
        return session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.status == status
        ).order_by(MCPAgentJob.created_at.desc()).all()

    def get_jobs_by_spawner(self, session: Session, tenant_key: str,
                            spawned_by: str) -> List[MCPAgentJob]:
        """
        Get all jobs spawned by a specific agent.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            spawned_by: Agent ID that spawned jobs

        Returns:
            List of MCPAgentJob instances spawned by the agent
        """
        return session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.spawned_by == spawned_by
        ).order_by(MCPAgentJob.created_at.desc()).all()

    def add_message(self, session: Session, tenant_key: str,
                    job_id: str, message: Dict[str, Any]) -> bool:
        """
        Add message to job's message array.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to add message to
            message: Message object to add

        Returns:
            True if message was added, False if job not found
        """
        job = session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.job_id == job_id
        ).first()

        if job:
            # Ensure messages is a list
            messages = list(job.messages or [])

            # Add timestamp if not present
            if 'timestamp' not in message:
                message['timestamp'] = datetime.utcnow().isoformat()

            messages.append(message)
            job.messages = messages
            session.flush()
            return True
        return False

    def acknowledge_job(self, session: Session, tenant_key: str,
                        job_id: str) -> bool:
        """
        Mark job as acknowledged.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to acknowledge

        Returns:
            True if job was acknowledged, False if not found
        """
        job = session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.job_id == job_id
        ).first()

        if job:
            job.acknowledged = True
            session.flush()
            return True
        return False

    def add_context_chunk(self, session: Session, tenant_key: str,
                          job_id: str, chunk_id: str) -> bool:
        """
        Add a context chunk ID to the job.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to add chunk to
            chunk_id: Chunk ID to add

        Returns:
            True if chunk was added, False if job not found
        """
        job = session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key,
            MCPAgentJob.job_id == job_id
        ).first()

        if job:
            context_chunks = list(job.context_chunks or [])
            if chunk_id not in context_chunks:
                context_chunks.append(chunk_id)
                job.context_chunks = context_chunks
                session.flush()
            return True
        return False

    def get_job_statistics(self, session: Session, tenant_key: str,
                           agent_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Get job statistics for a tenant.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            agent_type: Optional filter by agent type

        Returns:
            Dictionary with job statistics
        """
        query = session.query(MCPAgentJob).filter(
            MCPAgentJob.tenant_key == tenant_key
        )

        if agent_type:
            query = query.filter(MCPAgentJob.agent_type == agent_type)

        # Count by status
        status_counts = session.query(
            MCPAgentJob.status,
            func.count(MCPAgentJob.id)
        ).filter(
            MCPAgentJob.tenant_key == tenant_key
        )

        if agent_type:
            status_counts = status_counts.filter(MCPAgentJob.agent_type == agent_type)

        status_counts = status_counts.group_by(MCPAgentJob.status).all()

        # Count by agent type
        type_counts = session.query(
            MCPAgentJob.agent_type,
            func.count(MCPAgentJob.id)
        ).filter(
            MCPAgentJob.tenant_key == tenant_key
        ).group_by(MCPAgentJob.agent_type).all()

        total_jobs = query.count()

        return {
            'total_jobs': total_jobs,
            'by_status': {status: count for status, count in status_counts},
            'by_agent_type': {agent_type: count for agent_type, count in type_counts},
            'active_jobs': len([s for s, c in status_counts if s in ['pending', 'active']]),
            'completed_jobs': len([s for s, c in status_counts if s == 'completed']),
            'failed_jobs': len([s for s, c in status_counts if s == 'failed'])
        }