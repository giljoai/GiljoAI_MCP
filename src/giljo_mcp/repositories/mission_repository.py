# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
MissionRepository - Data access layer for agent mission operations.

BE-5022d: Extracted session operations from MissionService and
MissionOrchestrationService into repository methods.

All methods enforce tenant_key isolation. Session is passed by the caller.
"""

from __future__ import annotations

import logging

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload, selectinload

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.projects import Project
from giljo_mcp.models.templates import AgentTemplate


logger = logging.getLogger(__name__)


class MissionRepository:
    """
    Repository for agent mission database operations.

    Covers: MissionService reads/writes, MissionOrchestrationService reads.
    All methods enforce tenant_key isolation.
    Session is passed in by the caller (service layer).
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # Core Reads — MissionService
    # ============================================================================

    async def get_job(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentJob | None:
        """Get an agent job by ID with tenant isolation."""
        result = await session.execute(
            select(AgentJob).where(
                and_(
                    AgentJob.job_id == job_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_active_execution(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentExecution | None:
        """Get the latest active (non-terminal) execution for a job."""
        result = await session.execute(
            select(AgentExecution)
            .where(
                and_(
                    AgentExecution.job_id == job_id,
                    AgentExecution.tenant_key == tenant_key,
                    AgentExecution.status.not_in(["complete", "closed", "decommissioned"]),
                )
            )
            .order_by(AgentExecution.started_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_project_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> Project | None:
        """Get a project by ID with tenant isolation."""
        result = await session.execute(
            select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
        )
        return result.scalar_one_or_none()

    async def get_project_executions_with_jobs(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> list:
        """Get all executions with their jobs for a project."""
        result = await session.execute(
            select(AgentExecution, AgentJob)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentExecution.tenant_key == tenant_key,
                )
            )
        )
        return result.all()

    async def get_template_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        template_id: str,
    ) -> AgentTemplate | None:
        """Get an agent template by ID with tenant isolation."""
        result = await session.execute(
            select(AgentTemplate).where(
                and_(
                    AgentTemplate.id == template_id,
                    AgentTemplate.tenant_key == tenant_key,
                )
            )
        )
        return result.scalar_one_or_none()

    async def get_template_by_role(
        self,
        session: AsyncSession,
        tenant_key: str,
        role: str,
    ) -> AgentTemplate | None:
        """Get an active agent template for a role.

        Resolution: tenant-specific -> system default.
        """
        # 1. Tenant-specific
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.role == role,
            AgentTemplate.is_active,
        )
        result = await session.execute(stmt)
        template = result.scalar_one_or_none()
        if template:
            return template

        # 2. System default
        stmt = (
            select(AgentTemplate)
            .where(
                AgentTemplate.role == role,
                AgentTemplate.is_default,
                AgentTemplate.is_active,
            )
            .limit(1)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def commit(self, session: AsyncSession) -> None:
        """Commit the current transaction."""
        await session.commit()

    async def refresh(self, session: AsyncSession, entity) -> None:
        """Refresh an entity from the database."""
        await session.refresh(entity)

    # ============================================================================
    # Reads — MissionService update_agent_mission
    # ============================================================================

    async def count_non_orchestrator_agents(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> int:
        """Count non-orchestrator, non-decommissioned agent executions for a project."""
        result = await session.execute(
            select(func.count())
            .select_from(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project_id,
                AgentJob.tenant_key == tenant_key,
                AgentExecution.agent_display_name != "orchestrator",
                AgentExecution.status.not_in(["decommissioned"]),
            )
        )
        return result.scalar() or 0

    # ============================================================================
    # Reads — MissionOrchestrationService
    # ============================================================================

    async def get_execution_with_job(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentExecution | None:
        """Get execution with eagerly loaded job relationship."""
        result = await session.execute(
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .where(
                and_(
                    AgentExecution.job_id == job_id,
                    AgentExecution.tenant_key == tenant_key,
                )
            )
            .order_by(AgentExecution.started_at.desc())
        )
        return result.scalars().first()

    async def get_project_with_vision_docs(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
    ):
        """Get a product with eagerly loaded vision documents."""
        from giljo_mcp.models.products import Product

        result = await session.execute(
            select(Product)
            .where(and_(Product.id == product_id, Product.tenant_key == tenant_key))
            .options(selectinload(Product.vision_documents))
        )
        return result.scalar_one_or_none()

    async def get_active_templates(
        self,
        session: AsyncSession,
        tenant_key: str,
        limit: int = 8,
    ) -> list[AgentTemplate]:
        """Get active agent templates for a tenant."""
        result = await session.execute(
            select(AgentTemplate)
            .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active))
            .limit(limit)
        )
        return list(result.scalars().all())

    async def get_category_metadata(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
    ) -> tuple[int, object]:
        """Get count and max created_at for product memory entries."""
        from giljo_mcp.models.product_memory_entry import ProductMemoryEntry

        result = await session.execute(
            select(
                func.count(ProductMemoryEntry.id),
                func.max(ProductMemoryEntry.created_at),
            ).where(
                and_(
                    ProductMemoryEntry.product_id == product_id,
                    ProductMemoryEntry.tenant_key == tenant_key,
                    ProductMemoryEntry.deleted_by_user.is_(False),
                )
            )
        )
        row = result.one()
        return row[0], row[1]
