"""Job and agent statistics repository — agent executions, jobs, API metrics, health checks."""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Message, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.config import ApiMetrics
from src.giljo_mcp.models.tasks import MessageRecipient


class JobStatisticsRepository:
    """
    Repository for job and agent statistics queries.

    Covers API metrics, agent execution counts, per-agent message stats,
    job lookups, database health checks, and agent role distribution.
    All methods enforce tenant isolation via tenant_key.
    """

    def __init__(self, db_manager):
        """
        Initialize job statistics repository.

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
    # AGENT STATISTICS DOMAIN
    # ============================================================================

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
            elif status in ["waiting", "working", "blocked", "complete", "silent", "decommissioned"]:
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
        result = await session.scalar(
            select(func.count(Message.id)).where(Message.from_agent_id == agent_name, Message.tenant_key == tenant_key)
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
            select(func.count(Message.id))
            .join(MessageRecipient)
            .where(MessageRecipient.agent_id == agent_name, Message.tenant_key == tenant_key)
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
        result = await session.scalar(
            select(func.max(Message.created_at)).where(
                Message.from_agent_id == agent_name, Message.tenant_key == tenant_key
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

    # ============================================================================
    # DASHBOARD ANALYTICS DOMAIN
    # ============================================================================

    async def get_agent_role_distribution(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None = None,
    ) -> list[dict]:
        """
        Get all configured agent templates with actual execution counts.

        Uses a hybrid resolution strategy:
        1. FK path (AgentJob.template_id) for multi-terminal executions.
        2. Name match (AgentExecution.agent_name = AgentTemplate.name) as
           fallback for single-terminal or legacy jobs without template_id.

        Returns all configured templates (active and inactive) so the chart
        always reflects the full agent roster. Executions that don't match
        any template are excluded (they represent deleted/renamed templates).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Optional product filter

        Returns:
            List of AgentRoleDistItem-shaped dicts, sorted by count descending.
        """
        from src.giljo_mcp.models.templates import AgentTemplate

        # 1. Get all configured templates (scoped by product when filtered)
        tmpl_stmt = select(
            AgentTemplate.id,
            AgentTemplate.name,
            AgentTemplate.background_color,
            AgentTemplate.is_active,
        ).where(AgentTemplate.tenant_key == tenant_key)
        if product_id:
            tmpl_stmt = tmpl_stmt.where(
                or_(
                    AgentTemplate.product_id == product_id,
                    AgentTemplate.product_id.is_(None),
                )
            )
        tmpl_result = await session.execute(tmpl_stmt)
        templates = tmpl_result.all()

        # Build lookup maps: id -> template, name -> template
        tmpl_by_id = {t.id: t for t in templates}
        tmpl_by_name = {t.name: t for t in templates}

        # 2. Count executions via FK path (template_id on AgentJob)
        fk_stmt = (
            select(
                AgentJob.template_id,
                func.count(AgentExecution.id).label("cnt"),
            )
            .join(AgentExecution, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.tenant_key == tenant_key,
                AgentJob.template_id.isnot(None),
            )
            .group_by(AgentJob.template_id)
        )
        if product_id:
            fk_stmt = fk_stmt.join(Project, AgentJob.project_id == Project.id).where(
                Project.tenant_key == tenant_key,
                Project.product_id == product_id,
            )
        fk_result = await session.execute(fk_stmt)
        fk_counts: dict[str, int] = dict(fk_result.all())

        # 3. Count executions via name fallback (jobs without template_id)
        name_stmt = (
            select(
                AgentExecution.agent_name,
                func.count(AgentExecution.id).label("cnt"),
            )
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentExecution.tenant_key == tenant_key,
                AgentJob.template_id.is_(None),
                AgentExecution.agent_name.isnot(None),
            )
            .group_by(AgentExecution.agent_name)
        )
        if product_id:
            name_stmt = name_stmt.join(Project, AgentJob.project_id == Project.id).where(
                Project.tenant_key == tenant_key,
                Project.product_id == product_id,
            )
        name_result = await session.execute(name_stmt)
        name_counts: dict[str, int] = dict(name_result.all())

        # 4. Merge counts per template
        counts_per_tmpl: dict[str, int] = {}
        for tmpl_id, count in fk_counts.items():
            if tmpl_id in tmpl_by_id:
                name = tmpl_by_id[tmpl_id].name
                counts_per_tmpl[name] = counts_per_tmpl.get(name, 0) + count

        for agent_name, count in name_counts.items():
            if agent_name in tmpl_by_name:
                counts_per_tmpl[agent_name] = counts_per_tmpl.get(agent_name, 0) + count

        # 5. Build result: one entry per unique template name
        seen_names: set[str] = set()
        result = []
        for tmpl in templates:
            if tmpl.name in seen_names:
                continue
            seen_names.add(tmpl.name)
            label = tmpl.name.replace("-", " ").replace("_", " ").title()
            result.append(
                {
                    "label": label,
                    "count": counts_per_tmpl.get(tmpl.name, 0),
                    "color": tmpl.background_color or "#9e9e9e",
                    "is_active": tmpl.is_active,
                }
            )

        result.sort(key=lambda x: x["count"], reverse=True)
        return result
