# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectRepository - Data access layer for core project CRUD and query operations.

BE-5022d: Extracted session operations from ProjectService, ProjectQueryService,
ProjectSummaryService, and ConsolidatedVisionService into repository methods.

All methods enforce tenant_key isolation. Session is passed by the caller.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from giljo_mcp.models.projects import Project, ProjectType
from giljo_mcp.models.tasks import Message


logger = logging.getLogger(__name__)


class ProjectRepository:
    """
    Repository for core project database operations.

    Covers: ProjectService CRUD, ProjectQueryService reads,
    ProjectSummaryService aggregation, ConsolidatedVisionService reads.

    All methods enforce tenant_key isolation.
    Session is passed in by the caller (service layer).
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # Core CRUD
    # ============================================================================

    async def add(self, session: AsyncSession, project: Project) -> None:
        """Add a project to the session."""
        session.add(project)

    async def commit(self, session: AsyncSession) -> None:
        """Commit the current transaction."""
        await session.commit()

    async def refresh(self, session: AsyncSession, entity: Project) -> None:
        """Refresh an entity from the database."""
        await session.refresh(entity)

    async def flush(self, session: AsyncSession) -> None:
        """Flush pending changes."""
        await session.flush()

    # ============================================================================
    # Read Operations — ProjectService
    # ============================================================================

    async def lock_rows_for_series(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None,
        project_type_id: str | None,
    ) -> None:
        """Lock matching project rows for FOR UPDATE to prevent concurrent duplicate series numbers."""
        lock_query = select(Project.id).where(
            Project.tenant_key == tenant_key,
            Project.product_id == product_id,
        )
        if project_type_id:
            lock_query = lock_query.where(Project.project_type_id == project_type_id)
        else:
            lock_query = lock_query.where(Project.project_type_id.is_(None))
        await session.execute(lock_query.with_for_update())

    async def get_next_series_number(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None,
        project_type_id: str | None,
    ) -> int:
        """Get the next series number (max + 1) for a tenant/product/type combo."""
        max_query = select(func.coalesce(func.max(Project.series_number), 0) + 1).where(
            Project.tenant_key == tenant_key,
            Project.product_id == product_id,
        )
        if project_type_id:
            max_query = max_query.where(Project.project_type_id == project_type_id)
        else:
            max_query = max_query.where(Project.project_type_id.is_(None))
        result = await session.execute(max_query)
        return result.scalar_one()

    async def check_duplicate_taxonomy(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None,
        project_type_id: str | None,
        series_number: int,
        subseries: str | None,
    ) -> bool:
        """Check if a taxonomy combination already exists. Returns True if duplicate."""
        dup_query = select(Project.id).where(
            Project.tenant_key == tenant_key,
            Project.product_id == product_id,
            Project.series_number == series_number,
            Project.deleted_at.is_(None),
        )
        if project_type_id:
            dup_query = dup_query.where(Project.project_type_id == project_type_id)
        else:
            dup_query = dup_query.where(Project.project_type_id.is_(None))
        if subseries is not None:
            dup_query = dup_query.where(Project.subseries == subseries)
        else:
            dup_query = dup_query.where(Project.subseries.is_(None))
        dup_result = await session.execute(dup_query)
        return dup_result.scalar_one_or_none() is not None

    async def get_with_project_type(
        self,
        session: AsyncSession,
        project_id: str,
    ) -> Project | None:
        """Get a project with eagerly loaded project_type relationship."""
        result = await session.execute(
            select(Project).options(selectinload(Project.project_type)).where(Project.id == project_id)
        )
        return result.scalar_one()

    async def get_by_id_with_type(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> Project | None:
        """Get a project by ID with tenant isolation and eagerly loaded project_type."""
        result = await session.execute(
            select(Project)
            .options(selectinload(Project.project_type))
            .where(Project.tenant_key == tenant_key, Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> Project | None:
        """Get a project by ID with tenant isolation (no relationship loading)."""
        result = await session.execute(
            select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
        )
        return result.scalar_one_or_none()

    async def get_project_type_by_label(
        self,
        session: AsyncSession,
        tenant_key: str,
        label: str,
    ) -> ProjectType | None:
        """Resolve a project type by label (case-insensitive)."""
        result = await session.execute(
            select(ProjectType).where(
                ProjectType.tenant_key == tenant_key,
                func.lower(ProjectType.label) == label.lower(),
            )
        )
        return result.scalar_one_or_none()

    async def get_project_type_by_abbreviation(
        self,
        session: AsyncSession,
        tenant_key: str,
        abbreviation: str,
    ) -> ProjectType | None:
        """Resolve a project type by abbreviation (case-insensitive)."""
        result = await session.execute(
            select(ProjectType).where(
                ProjectType.tenant_key == tenant_key,
                func.upper(ProjectType.abbreviation) == abbreviation.upper(),
            )
        )
        return result.scalar_one_or_none()

    async def get_agent_pairs_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list:
        """Get agent job/execution pairs for a project."""
        agent_query = (
            select(AgentJob, AgentExecution)
            .join(AgentExecution, AgentJob.job_id == AgentExecution.job_id)
            .where(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key)
            .order_by(AgentJob.created_at)
        )
        agent_result = await session.execute(agent_query)
        return agent_result.all()

    async def list_projects(
        self,
        session: AsyncSession,
        tenant_key: str,
        status: str | None = None,
        include_cancelled: bool = False,
        product_id: str | None = None,
    ) -> list[Project]:
        """List projects for a tenant with optional filters."""
        query = select(Project).options(selectinload(Project.project_type)).where(Project.tenant_key == tenant_key)

        if product_id:
            query = query.where(Project.product_id == product_id)

        if status:
            query = query.where(Project.status == status)
            if status == "deleted":
                query = query.where(Project.deleted_at.isnot(None))
        else:
            query = query.where(Project.deleted_at.is_(None))
            if not include_cancelled:
                query = query.where(Project.status != "cancelled")

        result = await session.execute(query)
        return list(result.scalars().all())

    # ============================================================================
    # Read Operations — ProjectQueryService
    # ============================================================================

    async def get_active_project(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> Project | None:
        """Get the currently active project for a tenant."""
        stmt = (
            select(Project)
            .options(selectinload(Project.project_type))
            .where(and_(Project.tenant_key == tenant_key, Project.status == "active"))
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def count_agent_jobs(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> int:
        """Count agent jobs for a project."""
        stmt = select(func.count(AgentJob.job_id)).where(
            AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def count_messages(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> int:
        """Count messages for a project."""
        stmt = select(func.count(Message.id)).where(Message.project_id == project_id, Message.tenant_key == tenant_key)
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def get_agent_job_type_summary(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list:
        """Get agent job type counts for a project."""
        query = (
            select(AgentJob.job_type, func.count(AgentJob.job_id).label("count"))
            .where(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key)
            .group_by(AgentJob.job_type)
        )
        result = await session.execute(query)
        return result.all()

    async def get_agent_details_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list:
        """Get detailed agent job/execution pairs for a project."""
        query = (
            select(AgentJob, AgentExecution)
            .join(AgentExecution, AgentJob.job_id == AgentExecution.job_id)
            .where(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key)
            .order_by(AgentJob.created_at)
        )
        result = await session.execute(query)
        return result.all()

    async def get_memory_entries_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list[ProductMemoryEntry]:
        """Get 360 memory entries for a project."""
        query = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.project_id == project_id,
                ProductMemoryEntry.tenant_key == tenant_key,
            )
            .order_by(ProductMemoryEntry.sequence)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    async def get_messages_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list[Message]:
        """Get messages for a project ordered by creation time."""
        query = (
            select(Message)
            .where(
                Message.project_id == project_id,
                Message.tenant_key == tenant_key,
            )
            .order_by(Message.created_at)
        )
        result = await session.execute(query)
        return list(result.scalars().all())

    # ============================================================================
    # Read Operations — ProjectSummaryService
    # ============================================================================

    async def get_agent_status_counts(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> dict:
        """Aggregate agent execution status counts for a project."""
        job_counts_result = await session.execute(
            select(AgentExecution.status, func.count(AgentExecution.agent_id).label("count"))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
            .group_by(AgentExecution.status)
        )
        return dict(job_counts_result.all())

    async def get_last_activity_at(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> datetime | None:
        """Get the most recent activity timestamp for a project's agents."""
        last_activity_result = await session.execute(
            select(
                func.greatest(
                    func.max(AgentExecution.completed_at),
                    func.max(AgentExecution.started_at),
                    func.max(AgentExecution.last_progress_at),
                    func.max(AgentExecution.last_activity_at),
                )
            )
            .select_from(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
        )
        return last_activity_result.scalar()

    async def get_product_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
    ):
        """Get a product by ID with tenant isolation."""
        from giljo_mcp.models.products import Product

        result = await session.execute(
            select(Product).where(
                and_(
                    Product.id == product_id,
                    Product.tenant_key == tenant_key,
                )
            )
        )
        return result.scalar_one_or_none()

    # ============================================================================
    # Read Operations — ConsolidatedVisionService
    # ============================================================================

    async def get_product_with_vision_docs(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
    ):
        """Get a product with eagerly loaded vision documents."""
        from giljo_mcp.models.products import Product

        result = await session.execute(
            select(Product)
            .options(selectinload(Product.vision_documents))
            .where(Product.id == product_id, Product.tenant_key == tenant_key)
        )
        return result.scalar_one_or_none()

    # ============================================================================
    # Write Operations — ProjectDeletionService
    # ============================================================================

    async def get_not_deleted(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> Project | None:
        """Get a non-deleted project by ID."""
        stmt = select(Project).where(
            and_(
                Project.id == project_id,
                Project.tenant_key == tenant_key,
                Project.deleted_at.is_(None),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_executions_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list[AgentExecution]:
        """Get non-completed/non-decommissioned executions for a project."""
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                    AgentExecution.status.notin_(["complete", "decommissioned"]),
                )
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_agent_jobs_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list[AgentJob]:
        """Get all agent jobs for a project."""
        stmt = select(AgentJob).where(and_(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_tasks_for_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list:
        """Get all tasks for a project."""
        from giljo_mcp.models.tasks import Task

        stmt = select(Task).where(and_(Task.project_id == project_id, Task.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_messages_for_deletion(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list[Message]:
        """Get all messages for a project (for deletion)."""
        stmt = select(Message).where(and_(Message.project_id == project_id, Message.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def delete_entity(self, session: AsyncSession, entity) -> None:
        """Delete an entity from the session."""
        await session.delete(entity)

    async def get_deleted_projects(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str | None = None,
    ) -> list[Project]:
        """Get all soft-deleted projects for a tenant, optionally scoped to a product."""
        conditions = [Project.tenant_key == tenant_key, Project.status == "deleted", Project.deleted_at.isnot(None)]
        if product_id:
            conditions.append(Project.product_id == product_id)
        stmt = select(Project).where(and_(*conditions))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_expired_deleted_projects(
        self,
        session: AsyncSession,
        cutoff_date: datetime,
    ) -> list[Project]:
        """Get projects deleted before a cutoff date."""
        stmt = select(Project).where(
            Project.deleted_at.isnot(None),
            Project.status == "deleted",
            Project.deleted_at < cutoff_date,
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def restore_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> int:
        """Restore a project to inactive status. Returns rowcount."""
        result = await session.execute(
            update(Project)
            .where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
            .values(
                status="inactive",
                completed_at=None,
                deleted_at=None,
                updated_at=datetime.now(timezone.utc),
            )
        )
        return result.rowcount
