"""
Statistics repository for aggregated metrics and monitoring.

Handover 1011: Migrates all statistics queries from api/endpoints/statistics.py
to follow the repository pattern with CRITICAL tenant isolation.

Handover 0839: Dashboard analytics methods (distributions, recent activity, product counts).
"""

from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Message, Project, Task
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.config import ApiMetrics
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import ProjectType
from src.giljo_mcp.models.tasks import MessageRecipient


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

    async def count_projects_staged(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """Count projects with staging_status in ('staged', 'staging_complete') for tenant."""
        result = await session.scalar(
            select(func.count(Project.id)).where(
                Project.tenant_key == tenant_key,
                Project.staging_status.in_(("staged", "staging_complete")),
            )
        )
        return result or 0

    async def get_project_context_stats(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> tuple[float, int]:
        """
        Get average and peak context usage across all projects.

        Returns (0.0, 0) - context tracking columns removed.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Tuple of (0.0, 0) - stub values
        """
        return (0.0, 0)

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

    async def get_project_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> Project | None:
        """
        Get a single project by ID with tenant isolation.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            Project instance or None if not found
        """
        query = select(Project).where(
            Project.tenant_key == tenant_key,
            Project.id == project_id,
        )
        result = await session.execute(query)
        return result.scalar_one_or_none()

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

    # ============================================================================
    # DASHBOARD ANALYTICS DOMAIN (Handover 0839)
    # ============================================================================

    async def get_project_status_distribution(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None = None,
    ) -> dict[str, int]:
        """
        Get project count grouped by status.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Optional product filter

        Returns:
            Dict mapping status to count, e.g. {"active": 5, "completed": 12}
        """
        stmt = (
            select(Project.status, func.count(Project.id))
            .where(Project.tenant_key == tenant_key)
            .group_by(Project.status)
        )
        if product_id:
            stmt = stmt.where(Project.product_id == product_id)
        result = await session.execute(stmt)
        return dict(result.all())

    async def get_project_taxonomy_distribution(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None = None,
    ) -> list[dict]:
        """
        Get project count grouped by project type (taxonomy).

        Includes an "Untyped" entry for projects with no project_type_id.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Optional product filter

        Returns:
            List of dicts with keys: label, color, count
        """
        # Typed projects: join ProjectType, group by label + color
        typed_stmt = (
            select(
                ProjectType.label,
                ProjectType.color,
                func.count(Project.id).label("count"),
            )
            .join(ProjectType, Project.project_type_id == ProjectType.id)
            .where(
                Project.tenant_key == tenant_key,
                Project.project_type_id.is_not(None),
            )
            .group_by(ProjectType.label, ProjectType.color)
        )
        if product_id:
            typed_stmt = typed_stmt.where(Project.product_id == product_id)
        typed_result = await session.execute(typed_stmt)
        rows = [{"label": row.label, "color": row.color, "count": row.count} for row in typed_result.all()]

        # Untyped projects count
        untyped_stmt = select(func.count(Project.id)).where(
            Project.tenant_key == tenant_key,
            Project.project_type_id.is_(None),
        )
        if product_id:
            untyped_stmt = untyped_stmt.where(Project.product_id == product_id)
        untyped_count = await session.scalar(untyped_stmt) or 0

        if untyped_count > 0:
            rows.append({"label": "Untyped", "color": "#9E9E9E", "count": untyped_count})

        return rows

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

    async def get_recent_projects(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get the most recently completed projects.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Optional product filter
            limit: Maximum number of results

        Returns:
            List of dicts with keys: id, name, status, created_at, completed_at,
            taxonomy_alias, project_type_color
        """
        stmt = (
            select(
                Project.id,
                Project.name,
                Project.status,
                Project.created_at,
                Project.completed_at,
                Project.alias,
                Project.project_type_id,
                Project.series_number,
                Project.subseries,
                ProjectType.abbreviation.label("type_abbreviation"),
                ProjectType.color.label("project_type_color"),
                Product.name.label("product_name"),
            )
            .outerjoin(ProjectType, Project.project_type_id == ProjectType.id)
            .outerjoin(Product, Project.product_id == Product.id)
            .where(Project.tenant_key == tenant_key, Project.status == "completed", Project.completed_at.isnot(None))
            .order_by(Project.completed_at.desc())
            .limit(limit)
        )
        if product_id:
            stmt = stmt.where(Project.product_id == product_id)

        result = await session.execute(stmt)
        rows = result.all()

        projects = []
        for row in rows:
            # Build taxonomy_alias from fields (mirrors Project.taxonomy_alias property)
            parts = []
            if row.project_type_id and row.type_abbreviation:
                parts.append(row.type_abbreviation)
            if row.series_number:
                if parts:
                    parts.append("-")
                parts.append(f"{row.series_number:04d}")
                if row.subseries:
                    parts.append(row.subseries)
            taxonomy_alias = "".join(parts) if parts else row.alias

            projects.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "completed_at": row.completed_at.isoformat() if row.completed_at else None,
                    "taxonomy_alias": taxonomy_alias,
                    "project_type_color": row.project_type_color,
                    "product_name": row.product_name,
                }
            )

        return projects

    async def get_recent_memory_entries(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None = None,
        limit: int = 10,
    ) -> list[dict]:
        """
        Get the most recent 360 memory entries.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Optional product filter
            limit: Maximum number of results

        Returns:
            List of dicts with keys: project_name, summary, timestamp, entry_type
        """
        stmt = (
            select(
                ProductMemoryEntry.project_name,
                ProductMemoryEntry.summary,
                ProductMemoryEntry.timestamp,
                ProductMemoryEntry.entry_type,
                ProductMemoryEntry.git_commits,
                Product.name.label("product_name"),
            )
            .outerjoin(Product, ProductMemoryEntry.product_id == Product.id)
            .where(ProductMemoryEntry.tenant_key == tenant_key)
            .order_by(ProductMemoryEntry.timestamp.desc())
            .limit(limit)
        )
        if product_id:
            stmt = stmt.where(ProductMemoryEntry.product_id == product_id)

        result = await session.execute(stmt)
        return [
            {
                "project_name": row.project_name,
                "summary": (row.summary[:200] if row.summary else None),
                "timestamp": row.timestamp.isoformat() if row.timestamp else None,
                "entry_type": row.entry_type,
                "git_commits": row.git_commits or [],
                "product_name": row.product_name,
            }
            for row in result.all()
        ]

    async def get_task_status_distribution(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None = None,
    ) -> dict[str, int]:
        """
        Get task count grouped by status.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Optional product filter

        Returns:
            Dict mapping status to count, e.g. {"pending": 3, "completed": 10}
        """
        stmt = select(Task.status, func.count(Task.id)).where(Task.tenant_key == tenant_key).group_by(Task.status)
        if product_id:
            stmt = stmt.where(Task.product_id == product_id)
        result = await session.execute(stmt)
        return dict(result.all())

    async def get_execution_mode_distribution(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None = None,
    ) -> dict[str, int]:
        """
        Get project count grouped by execution_mode.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            product_id: Optional product filter

        Returns:
            Dict mapping execution_mode to count, e.g. {"multi_terminal": 5, "claude_code_cli": 3}
        """
        stmt = (
            select(Project.execution_mode, func.count(Project.id))
            .where(Project.tenant_key == tenant_key)
            .group_by(Project.execution_mode)
        )
        if product_id:
            stmt = stmt.where(Project.product_id == product_id)
        result = await session.execute(stmt)
        return dict(result.all())

    async def get_product_project_counts(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> list[dict]:
        """
        Get project count per product (for product selector badges).

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            List of dicts with keys: product_id, product_name, project_count
        """
        stmt = (
            select(
                Product.id.label("product_id"),
                Product.name.label("product_name"),
                func.count(Project.id).label("project_count"),
            )
            .outerjoin(Project, Product.id == Project.product_id)
            .where(Product.tenant_key == tenant_key)
            .group_by(Product.id, Product.name)
            .order_by(Product.name)
        )
        result = await session.execute(stmt)
        return [
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "project_count": row.project_count,
            }
            for row in result.all()
        ]
