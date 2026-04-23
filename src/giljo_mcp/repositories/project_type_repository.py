# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectTypeRepository - Data access layer for ProjectType entity.

BE-5022c: Extracted from project_type_ops.py to enforce the service->repository
boundary. All database writes for ProjectType are routed through this repository.

Tenant isolation is enforced at the query level on every operation.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.projects import Project, ProjectType


logger = logging.getLogger(__name__)


class ProjectTypeRepository:
    """
    Repository for ProjectType database operations.

    Methods accept an AsyncSession parameter (session-in pattern) so the
    calling service controls transaction boundaries.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def count_for_tenant(self, session: AsyncSession, tenant_key: str) -> int:
        """
        Count project types for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            Number of project types
        """
        result = await session.execute(
            select(func.count()).select_from(ProjectType).where(ProjectType.tenant_key == tenant_key)
        )
        return result.scalar() or 0

    async def add_project_type(self, session: AsyncSession, project_type: ProjectType) -> None:
        """
        Add a project type to the session (no commit).

        Args:
            session: Active database session
            project_type: Fully constructed ProjectType ORM instance
        """
        session.add(project_type)

    async def flush(self, session: AsyncSession) -> None:
        """
        Flush the current session (write to DB without committing).

        Args:
            session: Active database session
        """
        await session.flush()

    async def get_by_abbreviation(
        self,
        session: AsyncSession,
        tenant_key: str,
        abbreviation: str,
    ) -> ProjectType | None:
        """
        Get a project type by abbreviation within a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            abbreviation: ProjectType abbreviation

        Returns:
            ProjectType ORM instance or None
        """
        result = await session.execute(
            select(ProjectType).where(
                ProjectType.tenant_key == tenant_key,
                ProjectType.abbreviation == abbreviation,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        type_id: str,
    ) -> ProjectType | None:
        """
        Get a project type by ID within a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            type_id: ProjectType UUID

        Returns:
            ProjectType ORM instance or None
        """
        result = await session.execute(
            select(ProjectType).where(
                ProjectType.id == type_id,
                ProjectType.tenant_key == tenant_key,
            )
        )
        return result.scalar_one_or_none()

    async def flush_and_refresh(self, session: AsyncSession, project_type: ProjectType) -> ProjectType:
        """
        Flush pending changes and refresh the project type.

        Args:
            session: Active database session
            project_type: ProjectType ORM instance

        Returns:
            Refreshed ProjectType instance
        """
        await session.flush()
        await session.refresh(project_type)
        return project_type

    async def delete_project_type(self, session: AsyncSession, project_type: ProjectType) -> None:
        """
        Delete a project type and flush.

        Args:
            session: Active database session
            project_type: ProjectType ORM instance to delete
        """
        await session.delete(project_type)
        await session.flush()

    # ============================================================================
    # Read Operations — BE-5022d: Moved from project_type_ops.py
    # ============================================================================

    async def list_with_project_counts(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> list[Any]:
        """List all project types with project counts, ordered by sort_order.

        Returns:
            List of (ProjectType, project_count) tuples.
        """
        project_count_subq = (
            select(func.count(Project.id))
            .where(
                Project.project_type_id == ProjectType.id,
                Project.tenant_key == tenant_key,
            )
            .correlate(ProjectType)
            .scalar_subquery()
            .label("project_count")
        )

        stmt = (
            select(ProjectType, project_count_subq)
            .where(ProjectType.tenant_key == tenant_key)
            .order_by(ProjectType.sort_order, ProjectType.abbreviation)
        )

        result = await session.execute(stmt)
        return result.all()

    async def get_project_count_for_type(
        self,
        session: AsyncSession,
        tenant_key: str,
        type_id: str,
    ) -> int:
        """Count projects assigned to a project type.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            type_id: Project type ID

        Returns:
            Number of projects assigned to this type
        """
        result = await session.execute(
            select(func.count(Project.id)).where(
                Project.project_type_id == type_id,
                Project.tenant_key == tenant_key,
            )
        )
        return result.scalar() or 0

    async def get_next_series_number(
        self,
        session: AsyncSession,
        tenant_key: str,
        type_id: str,
        product_id: str | None = None,
    ) -> int:
        """Get the next available series number for a project type within a product.

        Returns max(series_number) + 1, or 1 if no projects exist.
        """
        query = select(func.max(Project.series_number)).where(
            Project.project_type_id == type_id,
            Project.tenant_key == tenant_key,
            Project.deleted_at.is_(None),
        )
        if product_id is not None:
            query = query.where(Project.product_id == product_id)
        result = await session.execute(query)
        max_num = result.scalar()
        return (max_num or 0) + 1

    async def get_used_series_numbers(
        self,
        session: AsyncSession,
        tenant_key: str,
        type_id: str,
        product_id: str | None = None,
    ) -> set[int]:
        """Get all used series numbers for a project type within a product.

        Returns:
            Set of used series numbers.
        """
        query = (
            select(Project.series_number)
            .where(
                Project.project_type_id == type_id,
                Project.tenant_key == tenant_key,
                Project.series_number.is_not(None),
                Project.deleted_at.is_(None),
            )
            .order_by(Project.series_number)
        )
        if product_id is not None:
            query = query.where(Project.product_id == product_id)
        result = await session.execute(query)
        return set(result.scalars().all())

    async def check_series_available(
        self,
        session: AsyncSession,
        tenant_key: str,
        type_id: str | None,
        series_number: int,
        subseries: str | None = None,
        exclude_project_id: str | None = None,
        product_id: str | None = None,
    ) -> bool:
        """Check if a series number combination is available within a product.

        Returns:
            True if available, False if already taken.
        """
        query = select(Project.id).where(
            Project.tenant_key == tenant_key,
            Project.series_number == series_number,
            Project.deleted_at.is_(None),
        )
        if product_id is not None:
            query = query.where(Project.product_id == product_id)
        if type_id:
            query = query.where(Project.project_type_id == type_id)
        else:
            query = query.where(Project.project_type_id.is_(None))

        if subseries is not None:
            query = query.where(Project.subseries == subseries)
        else:
            query = query.where(Project.subseries.is_(None))

        if exclude_project_id:
            query = query.where(Project.id != exclude_project_id)

        result = await session.execute(query)
        return result.first() is None

    async def get_used_subseries(
        self,
        session: AsyncSession,
        tenant_key: str,
        type_id: str | None,
        series_number: int,
        exclude_project_id: str | None = None,
        product_id: str | None = None,
    ) -> list[str]:
        """Get all used subseries letters for a type + series_number within a product.

        Returns:
            Sorted list of used subseries letters.
        """
        query = select(Project.subseries).where(
            Project.tenant_key == tenant_key,
            Project.series_number == series_number,
            Project.subseries.isnot(None),
            Project.deleted_at.is_(None),
        )
        if product_id is not None:
            query = query.where(Project.product_id == product_id)
        if type_id:
            query = query.where(Project.project_type_id == type_id)
        else:
            query = query.where(Project.project_type_id.is_(None))

        if exclude_project_id:
            query = query.where(Project.id != exclude_project_id)

        result = await session.execute(query)
        return sorted([row[0] for row in result.all()])
