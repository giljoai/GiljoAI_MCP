"""
Statistics repository for aggregated metrics and monitoring.

Handover 1011: Migrates all statistics queries from api/endpoints/statistics.py
to follow the repository pattern with CRITICAL tenant isolation.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Message, Project, Task
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.config import ApiMetrics


class StatisticsRepository:
    """
    Repository for statistics and monitoring queries.

    Provides aggregated metrics across all system entities with proper
    tenant isolation. All methods MUST include tenant_key parameter.
    """

    def __init__(self, db_manager):
        """
        Initialize statistics repository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager

    # ============================================================================
    # API METRICS DOMAIN
    # ============================================================================

    async def get_api_metrics(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> ApiMetrics | None:
        """
        Get API call metrics for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            ApiMetrics instance or None if not found
        """
        stmt = select(ApiMetrics).where(ApiMetrics.tenant_key == tenant_key)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ============================================================================
    # PROJECT STATISTICS DOMAIN
    # ============================================================================

    async def count_total_projects(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Count total projects for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Total project count
        """
        result = await session.scalar(select(func.count(Project.id)).where(Project.tenant_key == tenant_key))
        return result or 0

    async def count_projects_by_status(
        self,
        session: AsyncSession,
        tenant_key: str,
        status: str,
    ) -> int:
        """
        Count projects with specific status for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            status: Project status to filter by

        Returns:
            Project count for status
        """
        result = await session.scalar(
            select(func.count(Project.id)).where(Project.tenant_key == tenant_key, Project.status == status)
        )
        return result or 0

    async def get_project_context_stats(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> tuple[float, int]:
        """
        Get average and peak context usage across all projects.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Tuple of (average_context_used, peak_context_used)
        """
        avg_context = (
            await session.scalar(select(func.avg(Project.context_used)).where(Project.tenant_key == tenant_key)) or 0.0
        )

        peak_context = (
            await session.scalar(select(func.max(Project.context_used)).where(Project.tenant_key == tenant_key)) or 0
        )

        return (float(avg_context), peak_context)

    async def get_projects_with_pagination(
        self,
        session: AsyncSession,
        tenant_key: str,
        status: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[Project]:
        """
        Get projects with optional status filter and pagination.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            status: Optional status filter
            limit: Maximum number of results
            offset: Number of results to skip

        Returns:
            List of Project instances
        """
        query = select(Project).where(Project.tenant_key == tenant_key)

        if status:
            query = query.where(Project.status == status)

        query = query.offset(offset).limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def count_agents_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> int:
        """
        Count agents associated with a project.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project ID to count agents for

        Returns:
            Agent count for project
        """
        result = await session.scalar(
            select(func.count(AgentExecution.agent_id))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project_id,
                AgentJob.tenant_key == tenant_key,
                AgentExecution.tenant_key == tenant_key,
            )
        )
        return result or 0

    async def count_messages_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> int:
        """
        Count messages for a project.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project ID to count messages for

        Returns:
            Message count for project
        """
        result = await session.scalar(
            select(func.count(Message.id)).where(Message.project_id == project_id, Message.tenant_key == tenant_key)
        )
        return result or 0

    async def count_tasks_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> int:
        """
        Count tasks for a project.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project ID to count tasks for

        Returns:
            Task count for project
        """
        result = await session.scalar(
            select(func.count(Task.id)).where(Task.project_id == project_id, Task.tenant_key == tenant_key)
        )
        return result or 0

    async def count_completed_tasks_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> int:
        """
        Count completed tasks for a project.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project ID to count completed tasks for

        Returns:
            Completed task count for project
        """
        result = await session.scalar(
            select(func.count(Task.id)).where(
                Task.project_id == project_id, Task.tenant_key == tenant_key, Task.status == "completed"
            )
        )
        return result or 0

    async def get_last_activity_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> datetime | None:
        """
        Get timestamp of last message activity for a project.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project ID to check activity for

        Returns:
            Timestamp of last message or None if no messages
        """
        result = await session.scalar(
            select(func.max(Message.created_at)).where(
                Message.project_id == project_id, Message.tenant_key == tenant_key
            )
        )
        return result

    # ============================================================================
    # AGENT STATISTICS DOMAIN
    # ============================================================================

    async def count_total_agents(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Count total agents (AgentExecution instances) for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Total agent execution count
        """
        result = await session.scalar(
            select(func.count(AgentExecution.agent_id)).where(AgentExecution.tenant_key == tenant_key)
        )
        return result or 0

    async def count_active_agents(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Count active agents (status in ['waiting', 'working']).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Active agent count
        """
        result = await session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == tenant_key, AgentExecution.status.in_(["waiting", "working"])
            )
        )
        return result or 0

    async def count_completed_agents(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Count completed agents (status='complete').

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Completed agent count
        """
        result = await session.scalar(
            select(func.count(AgentExecution.agent_id)).where(
                AgentExecution.tenant_key == tenant_key, AgentExecution.status == "complete"
            )
        )
        return result or 0

    async def get_agent_executions_with_filters(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str | None = None,
        status: str | None = None,
        limit: int = 100,
    ) -> list[AgentExecution]:
        """
        Get agent executions with optional filters.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Optional project ID filter
            status: Optional status filter
            limit: Maximum number of results

        Returns:
            List of AgentExecution instances
        """
        query = select(AgentExecution).where(AgentExecution.tenant_key == tenant_key)

        # Join through AgentJob if filtering by project
        if project_id:
            query = query.join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            query = query.where(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key)

        if status:
            # Map legacy status to AgentExecution status
            if status == "active":
                query = query.where(AgentExecution.status.in_(["waiting", "working"]))
            elif status in ["idle", "waiting", "working", "decommissioned", "complete"]:
                query = query.where(AgentExecution.status == status)

        query = query.limit(limit)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def count_messages_sent_by_agent(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_name: str,
    ) -> int:
        """
        Count messages sent by an agent.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_name: Agent name to count messages for

        Returns:
            Message count sent by agent
        """
        # Note: from_agent is stored in meta_data["_from_agent"], not as a column
        result = await session.scalar(
            select(func.count(Message.id)).where(
                Message.meta_data.op("->>")("_from_agent") == agent_name, Message.tenant_key == tenant_key
            )
        )
        return result or 0

    async def count_messages_received_by_agent(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_name: str,
    ) -> int:
        """
        Count messages received by an agent (to_agents contains agent_name).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_name: Agent name to count messages for

        Returns:
            Message count received by agent
        """
        result = await session.scalar(
            select(func.count(Message.id)).where(
                Message.to_agents.contains([agent_name]), Message.tenant_key == tenant_key
            )
        )
        return result or 0

    async def get_last_message_sent_by_agent(
        self,
        session: AsyncSession,
        tenant_key: str,
        agent_name: str,
    ) -> datetime | None:
        """
        Get timestamp of last message sent by agent.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            agent_name: Agent name to check activity for

        Returns:
            Timestamp of last message or None if no messages
        """
        # Note: from_agent is stored in meta_data["_from_agent"], not as a column
        result = await session.scalar(
            select(func.max(Message.created_at)).where(
                Message.meta_data.op("->>")("_from_agent") == agent_name, Message.tenant_key == tenant_key
            )
        )
        return result

    async def get_agent_job_by_job_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentJob | None:
        """
        Get AgentJob by job_id for project lookup.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            job_id: Job ID to retrieve

        Returns:
            AgentJob instance or None if not found
        """
        result = await session.execute(
            select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == tenant_key)
        )
        return result.scalar_one_or_none()

    # ============================================================================
    # MESSAGE STATISTICS DOMAIN
    # ============================================================================

    async def count_total_messages(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Count total messages for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Total message count
        """
        result = await session.scalar(select(func.count(Message.id)).where(Message.tenant_key == tenant_key))
        return result or 0

    async def count_messages_by_status(
        self,
        session: AsyncSession,
        tenant_key: str,
        status: str,
    ) -> int:
        """
        Count messages with specific status for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            status: Message status to filter by

        Returns:
            Message count for status
        """
        result = await session.scalar(
            select(func.count(Message.id)).where(Message.tenant_key == tenant_key, Message.status == status)
        )
        return result or 0

    async def count_messages_with_filters(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str | None = None,
        since: datetime | None = None,
    ) -> int:
        """
        Count messages with optional filters.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Optional project ID filter
            since: Optional timestamp filter (messages after this time)

        Returns:
            Message count matching filters
        """
        query = select(func.count(Message.id)).where(Message.tenant_key == tenant_key)

        if project_id:
            query = query.where(Message.project_id == project_id)

        if since:
            query = query.where(Message.created_at >= since)

        result = await session.scalar(query)
        return result or 0

    async def count_messages_by_status_with_filters(
        self,
        session: AsyncSession,
        tenant_key: str,
        status: str,
        project_id: str | None = None,
        since: datetime | None = None,
    ) -> int:
        """
        Count messages by status with optional filters.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            status: Message status to filter by
            project_id: Optional project ID filter
            since: Optional timestamp filter

        Returns:
            Message count matching filters
        """
        query = select(func.count(Message.id)).where(Message.tenant_key == tenant_key, Message.status == status)

        if project_id:
            query = query.where(Message.project_id == project_id)

        if since:
            query = query.where(Message.created_at >= since)

        result = await session.scalar(query)
        return result or 0

    # ============================================================================
    # TASK STATISTICS DOMAIN
    # ============================================================================

    async def count_total_tasks(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Count total tasks for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Total task count
        """
        result = await session.scalar(select(func.count(Task.id)).where(Task.tenant_key == tenant_key))
        return result or 0

    async def count_completed_tasks(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Count completed tasks for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Completed task count
        """
        result = await session.scalar(
            select(func.count(Task.id)).where(Task.tenant_key == tenant_key, Task.status == "completed")
        )
        return result or 0

    # ============================================================================
    # HEALTH CHECK DOMAIN
    # ============================================================================

    async def execute_health_check(
        self,
        session: AsyncSession,
    ) -> bool:
        """
        Execute simple database health check.

        Args:
            session: Async database session

        Returns:
            True if database is responsive, False otherwise
        """
        try:
            await session.execute(select(1))
            return True
        except (RuntimeError, OSError):
            return False
