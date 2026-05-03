# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectLifecycleRepository - Data access layer for project lifecycle operations.

BE-5022c: Extracted from ProjectLifecycleService to route all database writes
through the repository layer.

Responsibilities:
- Project state queries (by ID, by status)
- Project status updates (activate, deactivate, complete, cancel, resume)
- Orchestrator fixture creation (AgentJob + AgentExecution)
- Agent execution queries and status transitions

Design Principles:
- Session-in pattern: all methods accept session as parameter
- tenant_key filtering on EVERY query — no exceptions
- No business logic — pure data access
"""

import logging
from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.projects import Project


logger = logging.getLogger(__name__)


class ProjectLifecycleRepository:
    """
    Repository for project lifecycle database operations.

    All methods enforce tenant_key isolation.
    Session is passed in by the caller (service layer).
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # Read Operations
    # ============================================================================

    async def get_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> Project | None:
        """
        Get a project by ID with tenant isolation.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            Project instance or None
        """
        result = await session.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key,
                )
            )
        )
        return result.scalar_one_or_none()

    async def find_active_in_product(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
        exclude_project_id: str,
    ) -> Project | None:
        """
        Find an active project in a product, excluding a specific project.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            product_id: Product UUID
            exclude_project_id: Project ID to exclude

        Returns:
            Active Project instance or None
        """
        result = await session.execute(
            select(Project).where(
                and_(
                    Project.product_id == product_id,
                    Project.status == ProjectStatus.ACTIVE,
                    Project.id != exclude_project_id,
                    Project.tenant_key == tenant_key,
                )
            )
        )
        return result.scalar_one_or_none()

    async def find_existing_orchestrator(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> AgentExecution | None:
        """
        Find non-decommissioned orchestrator execution for a project.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            Orchestrator AgentExecution or None
        """
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project_id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_decommissioned_executions(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list[AgentExecution]:
        """
        Find decommissioned agent executions for a project.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID

        Returns:
            List of decommissioned AgentExecution instances
        """
        result = await session.execute(
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                    AgentExecution.status == "decommissioned",
                )
            )
        )
        return list(result.scalars().all())

    # ============================================================================
    # Write Operations
    # ============================================================================

    async def flush(self, session: AsyncSession) -> None:
        """Flush pending changes."""
        await session.flush()

    async def commit(self, session: AsyncSession) -> None:
        """Commit the current transaction."""
        await session.commit()

    async def refresh(self, session: AsyncSession, entity: Project | AgentJob | AgentExecution) -> None:
        """Refresh an entity from the database."""
        await session.refresh(entity)

    async def cancel_project(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
        reason: str | None = None,
    ) -> int:
        """
        Cancel a project via bulk update.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            reason: Optional cancellation reason

        Returns:
            Number of rows affected (0 or 1)
        """
        update_values: dict = {
            "status": ProjectStatus.CANCELLED,
            "completed_at": datetime.now(UTC),
            "updated_at": datetime.now(UTC),
        }
        if reason:
            update_values["cancellation_reason"] = reason

        result = await session.execute(
            update(Project)
            .where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
            .values(**update_values)
        )
        return result.rowcount

    async def create_orchestrator_fixture(
        self,
        session: AsyncSession,
        tenant_key: str,
        project: Project,
    ) -> dict[str, str]:
        """
        Create orchestrator AgentJob + AgentExecution fixture.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project: Project instance

        Returns:
            Dict with job_id and agent_id
        """
        job_id = str(uuid4())
        agent_id = str(uuid4())

        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",
            job_type="orchestrator",
            status="active",
            job_metadata={
                "created_via": "project_activation_fixture",
                "created_at": datetime.now(UTC).isoformat(),
            },
        )
        session.add(agent_job)

        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="waiting",
            progress=0,
            health_status="unknown",
        )
        session.add(agent_execution)

        await session.commit()
        await session.refresh(agent_job)
        await session.refresh(agent_execution)

        return {
            "job_id": job_id,
            "agent_id": agent_id,
            "execution_id": str(agent_execution.id),
        }

    # ============================================================================
    # BE-5022d: Additional methods for closeout/staging/launch services
    # ============================================================================

    async def get_active_agent_executions(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
        exclude_statuses: list[str] | None = None,
    ) -> list[AgentExecution]:
        """
        Get agent executions for a project, excluding specified statuses.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            exclude_statuses: Statuses to exclude (default: ["complete", "decommissioned"])

        Returns:
            List of AgentExecution instances
        """
        if exclude_statuses is None:
            exclude_statuses = ["complete", "decommissioned"]
        result = await session.execute(
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                    AgentExecution.status.notin_(exclude_statuses),
                )
            )
        )
        return list(result.scalars().all())

    async def get_executions_by_status(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
        statuses: list[str],
    ) -> list[AgentExecution]:
        """
        Get agent executions for a project with specified statuses.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            project_id: Project UUID
            statuses: List of statuses to match

        Returns:
            List of AgentExecution instances
        """
        result = await session.execute(
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.tenant_key == tenant_key,
                    AgentExecution.status.in_(statuses),
                )
            )
        )
        return list(result.scalars().all())

    async def get_agent_status_counts(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> dict:
        """
        Aggregate agent execution status counts for a project.

        Returns:
            Dict mapping status string to count.
        """
        from sqlalchemy import func

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

    async def add_entity(self, session: AsyncSession, entity) -> None:
        """Add an entity to the session."""
        session.add(entity)

    async def find_non_decommissioned_orchestrator(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> AgentExecution | None:
        """Find the latest non-decommissioned orchestrator for a project (ordered by started_at desc)."""
        stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project_id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),
            )
            .order_by(AgentExecution.started_at.desc())
        )
        result = await session.execute(stmt)
        return result.scalars().first()

    async def get_user(
        self,
        session: AsyncSession,
        tenant_key: str,
        user_id: str,
    ):
        """Get a user by ID with tenant isolation."""
        from giljo_mcp.models.auth import User

        result = await session.execute(select(User).where(and_(User.id == user_id, User.tenant_key == tenant_key)))
        return result.scalar_one_or_none()

    async def get_user_field_priorities(
        self,
        session: AsyncSession,
        tenant_key: str,
        user_id: str,
    ) -> list:
        """Get user field priority rows."""
        from giljo_mcp.models.auth import UserFieldPriority

        result = await session.execute(
            select(UserFieldPriority).where(
                and_(
                    UserFieldPriority.user_id == user_id,
                    UserFieldPriority.tenant_key == tenant_key,
                )
            )
        )
        return list(result.scalars().all())
