# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
TaskRepository - Data access layer for Task entities.

BE-5022d: Extracted from task_service.py and task_conversion_service.py
to enforce the service->repository boundary.

All database reads and writes for Task are routed through this repository.
Tenant isolation is enforced at the query level on every operation.
"""

from __future__ import annotations

import logging

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.models import Project, Task
from giljo_mcp.models.auth import User
from giljo_mcp.models.products import Product


logger = logging.getLogger(__name__)


class TaskRepository:
    """
    Repository for task-domain database operations.

    Methods accept an AsyncSession parameter (session-in pattern) so the
    calling service controls transaction boundaries.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ========================================================================
    # Task reads
    # ========================================================================

    async def get_task_by_id(
        self,
        session: AsyncSession,
        task_id: str,
        tenant_key: str,
    ) -> Task | None:
        """
        Get a task by ID with tenant isolation.

        Args:
            session: Active database session
            task_id: Task UUID
            tenant_key: Tenant key for isolation

        Returns:
            Task ORM instance or None
        """
        stmt = select(Task).where(and_(Task.id == task_id, Task.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_tasks(
        self,
        session: AsyncSession,
        query,
    ) -> list[Task]:
        """
        Execute a pre-built task query and return results.

        Args:
            session: Active database session
            query: SQLAlchemy select statement

        Returns:
            List of Task ORM instances
        """
        result = await session.execute(query)
        return list(result.scalars().all())

    async def find_by_category_and_title(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
        category: str,
        title: str,
    ) -> Task | None:
        """Find a task by category and title with tenant isolation.

        Used for idempotent task creation (e.g., action_required tags).
        BE-5022f.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            product_id: Product scope
            category: Task category to match
            title: Task title to match (exact, case-sensitive)

        Returns:
            Task ORM instance or None if not found
        """
        stmt = select(Task).where(
            and_(
                Task.tenant_key == tenant_key,
                Task.product_id == product_id,
                Task.category == category,
                Task.title == title,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_pending_by_category_and_title(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
        category: str,
        title: str,
    ) -> Task | None:
        """Find a non-completed task by category and title.

        Used for auto-resolving action items on job completion (BE-5022f).

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            product_id: Product scope
            category: Task category to match
            title: Task title to match (exact, case-sensitive)

        Returns:
            Task ORM instance or None if not found or already completed
        """
        stmt = select(Task).where(
            and_(
                Task.tenant_key == tenant_key,
                Task.product_id == product_id,
                Task.category == category,
                Task.title == title,
                Task.status != "completed",
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_project_by_id(
        self,
        session: AsyncSession,
        project_id: str,
        product_id: str,
        tenant_key: str,
    ) -> Project | None:
        """
        Get a project by ID with tenant and product isolation.

        Args:
            session: Active database session
            project_id: Project UUID
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Project ORM instance or None
        """
        stmt = select(Project).where(
            and_(
                Project.id == project_id,
                Project.product_id == product_id,
                Project.tenant_key == tenant_key,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_product(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> Product | None:
        """
        Get the active product for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            Product ORM instance or None
        """
        stmt = select(Product).where(and_(Product.tenant_key == tenant_key, Product.is_active))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(
        self,
        session: AsyncSession,
        user_id: str,
    ) -> User | None:
        """
        Get a user by ID (for permission checks).

        Args:
            session: Active database session
            user_id: User UUID

        Returns:
            User ORM instance or None
        """
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_subtasks(
        self,
        session: AsyncSession,
        parent_task_id: str,
        tenant_key: str,
    ) -> list[Task]:
        """
        Get child tasks for a parent task.

        Args:
            session: Active database session
            parent_task_id: Parent task UUID
            tenant_key: Tenant key for isolation

        Returns:
            List of child Task ORM instances
        """
        stmt = select(Task).where(and_(Task.parent_task_id == parent_task_id, Task.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_project_for_product(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> Project | None:
        """
        Get the active project for a product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Project ORM instance or None
        """
        stmt = select(Project).where(
            and_(
                Project.product_id == product_id,
                Project.status == ProjectStatus.ACTIVE,
                Project.tenant_key == tenant_key,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================================
    # Task writes
    # ========================================================================

    async def add_task(self, session: AsyncSession, task: Task) -> None:
        """
        Add a task to the session.

        Args:
            session: Active database session
            task: Fully constructed Task ORM instance
        """
        session.add(task)

    async def add_and_commit(self, session: AsyncSession, task: Task) -> None:
        """
        Add a task and commit.

        Args:
            session: Active database session
            task: Fully constructed Task ORM instance
        """
        session.add(task)
        await session.commit()

    async def commit(self, session: AsyncSession) -> None:
        """
        Commit the current transaction.

        Args:
            session: Active database session
        """
        await session.commit()

    async def commit_and_refresh(self, session: AsyncSession, entity) -> None:
        """
        Commit and refresh an entity.

        Args:
            session: Active database session
            entity: ORM instance to refresh
        """
        await session.commit()
        await session.refresh(entity)

    async def delete_task(self, session: AsyncSession, task: Task) -> None:
        """
        Delete a task from the session.

        Args:
            session: Active database session
            task: Task ORM instance to delete
        """
        await session.delete(task)

    async def delete_and_commit(self, session: AsyncSession, task: Task) -> None:
        """
        Delete a task and commit.

        Args:
            session: Active database session
            task: Task ORM instance to delete
        """
        await session.delete(task)
        await session.commit()

    # ========================================================================
    # Project writes (for task conversion)
    # ========================================================================

    async def add_project(self, session: AsyncSession, project: Project) -> None:
        """
        Add a project to the session.

        Args:
            session: Active database session
            project: Fully constructed Project ORM instance
        """
        session.add(project)

    async def flush(self, session: AsyncSession) -> None:
        """
        Flush pending changes without committing.

        Args:
            session: Active database session
        """
        await session.flush()

    async def refresh(self, session: AsyncSession, entity) -> None:
        """
        Refresh an entity from the database.

        Args:
            session: Active database session
            entity: ORM instance to refresh
        """
        await session.refresh(entity)
