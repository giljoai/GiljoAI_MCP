# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
TemplateRepository - Data access layer for AgentTemplate and related entities.

BE-5022c: Extracted from template_service.py to enforce the service->repository
boundary. All database writes for AgentTemplate, TemplateArchive, and
TemplateUsageStats are routed through this repository.

Tenant isolation is enforced at the query level on every operation.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import and_, func, select, update
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.agent_identity import AgentJob
from giljo_mcp.models.templates import AgentTemplate, TemplateArchive, TemplateUsageStats
from giljo_mcp.system_roles import SYSTEM_MANAGED_ROLES


logger = logging.getLogger(__name__)


class TemplateRepository:
    """
    Repository for template-domain database write operations.

    Methods accept an AsyncSession parameter (session-in pattern) so the
    calling service controls transaction boundaries.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ========================================================================
    # Template CRUD writes
    # ========================================================================

    async def add_template(self, session: AsyncSession, template: AgentTemplate) -> None:
        """
        Add a template to the session (no commit).

        Args:
            session: Active database session
            template: Fully constructed AgentTemplate ORM instance
        """
        session.add(template)

    async def add_and_commit_template(self, session: AsyncSession, template: AgentTemplate) -> AgentTemplate:
        """
        Add a template, commit, and refresh.

        Args:
            session: Active database session
            template: Fully constructed AgentTemplate ORM instance

        Returns:
            Refreshed AgentTemplate instance
        """
        session.add(template)
        await session.commit()
        await session.refresh(template)
        return template

    async def commit(self, session: AsyncSession) -> None:
        """
        Commit the current transaction.

        Args:
            session: Active database session
        """
        await session.commit()

    async def commit_and_refresh_template(self, session: AsyncSession, template: AgentTemplate) -> AgentTemplate:
        """
        Commit pending changes and refresh the template.

        Args:
            session: Active database session
            template: AgentTemplate ORM instance with pending changes

        Returns:
            Refreshed AgentTemplate instance
        """
        await session.commit()
        await session.refresh(template)
        return template

    # ========================================================================
    # Template deletion (CASCADE)
    # ========================================================================

    async def nullify_job_template_refs(self, session: AsyncSession, template_id: str) -> None:
        """
        Set AgentJob.template_id to NULL for all jobs referencing this template.

        Args:
            session: Active database session
            template_id: Template UUID
        """
        await session.execute(update(AgentJob).where(AgentJob.template_id == template_id).values(template_id=None))

    async def delete_usage_stats(self, session: AsyncSession, template_id: str) -> None:
        """
        Delete TemplateUsageStats records for a template.

        Args:
            session: Active database session
            template_id: Template UUID
        """
        await session.execute(sql_delete(TemplateUsageStats).where(TemplateUsageStats.template_id == template_id))

    async def delete_archives(self, session: AsyncSession, template_id: str) -> None:
        """
        Delete TemplateArchive records for a template.

        Args:
            session: Active database session
            template_id: Template UUID
        """
        await session.execute(sql_delete(TemplateArchive).where(TemplateArchive.template_id == template_id))

    async def delete_template(self, session: AsyncSession, template: AgentTemplate) -> None:
        """
        Delete a template entity.

        Args:
            session: Active database session
            template: AgentTemplate ORM instance to delete
        """
        await session.delete(template)

    # ========================================================================
    # Archive operations
    # ========================================================================

    async def add_archive(self, session: AsyncSession, archive: TemplateArchive) -> None:
        """
        Add a template archive record to the session.

        Args:
            session: Active database session
            archive: Fully constructed TemplateArchive ORM instance
        """
        session.add(archive)

    # ========================================================================
    # Bulk update (export tracking)
    # ========================================================================

    async def update_exported_timestamps(
        self,
        session: AsyncSession,
        template_ids: list[str],
        tenant_key: str,
        export_timestamp: datetime,
    ) -> int:
        """
        Update last_exported_at for a set of templates.

        Args:
            session: Active database session
            template_ids: List of template UUIDs
            tenant_key: Tenant key for isolation
            export_timestamp: Timestamp to set

        Returns:
            Number of templates updated
        """
        stmt = (
            update(AgentTemplate)
            .where(
                and_(
                    AgentTemplate.id.in_(template_ids),
                    AgentTemplate.tenant_key == tenant_key,
                )
            )
            .values(last_exported_at=export_timestamp)
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount

    # ========================================================================
    # Read queries (BE-5022d: moved from template_service.py)
    # ========================================================================

    async def list_by_tenant(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> list[AgentTemplate]:
        """
        List all templates for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            List of AgentTemplate ORM instances
        """
        stmt = select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_id(
        self,
        session: AsyncSession,
        template_id: str,
        tenant_key: str,
    ) -> AgentTemplate | None:
        """
        Get a template by ID with tenant isolation.

        Args:
            session: Active database session
            template_id: Template UUID
            tenant_key: Tenant key for isolation

        Returns:
            AgentTemplate ORM instance or None
        """
        stmt = select(AgentTemplate).where(
            and_(AgentTemplate.id == template_id, AgentTemplate.tenant_key == tenant_key)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        session: AsyncSession,
        name: str,
        tenant_key: str,
    ) -> AgentTemplate | None:
        """
        Get a template by name with tenant isolation.

        Args:
            session: Active database session
            name: Template name
            tenant_key: Tenant key for isolation

        Returns:
            AgentTemplate ORM instance or None
        """
        stmt = select(AgentTemplate).where(and_(AgentTemplate.name == name, AgentTemplate.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_with_filters(
        self,
        session: AsyncSession,
        tenant_key: str,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> list[AgentTemplate]:
        """
        List templates for a tenant with optional filters.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            role: Optional role filter
            is_active: Optional active status filter

        Returns:
            List of AgentTemplate ORM instances
        """
        query = select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key)
        if role:
            query = query.where(AgentTemplate.role == role)
        if is_active is not None:
            query = query.where(AgentTemplate.is_active == is_active)
        result = await session.execute(query)
        return list(result.scalars().all())

    async def check_name_exists(
        self,
        session: AsyncSession,
        tenant_key: str,
        name: str,
    ) -> bool:
        """
        Check if a template name already exists for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            name: Template name to check

        Returns:
            True if name exists
        """
        stmt = select(func.count(AgentTemplate.id)).where(
            and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.name == name)
        )
        result = await session.execute(stmt)
        return result.scalar() > 0

    async def get_defaults_by_role(
        self,
        session: AsyncSession,
        tenant_key: str,
        role: str,
    ) -> list[AgentTemplate]:
        """
        Get all default templates for a specific role.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            role: Role to filter by

        Returns:
            List of default AgentTemplate ORM instances
        """
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.role == role,
                AgentTemplate.is_default,
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_active_user_managed(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Count active user-managed templates for a tenant (excludes system roles).

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            Count of active user-managed templates
        """
        stmt = select(func.count(AgentTemplate.id)).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active,
                AgentTemplate.role.not_in(SYSTEM_MANAGED_ROLES),
            )
        )
        result = await session.execute(stmt)
        return result.scalar()

    async def get_template_role(
        self,
        session: AsyncSession,
        template_id: str,
    ) -> str | None:
        """
        Get only the role field for a template.

        Args:
            session: Active database session
            template_id: Template UUID

        Returns:
            Role string or None
        """
        stmt = select(AgentTemplate.role).where(AgentTemplate.id == template_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_distinct_roles(
        self,
        session: AsyncSession,
        tenant_key: str,
        exclude_template_id: str,
    ) -> set[str]:
        """
        Get distinct active roles excluding a specific template and system roles.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            exclude_template_id: Template to exclude

        Returns:
            Set of active role names
        """
        system_roles = list(SYSTEM_MANAGED_ROLES)
        stmt = (
            select(AgentTemplate.role)
            .where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active,
                AgentTemplate.id != exclude_template_id,
            )
            .where(AgentTemplate.role.notin_(system_roles))
            .distinct()
        )
        result = await session.execute(stmt)
        return {row[0] for row in result.all()}

    async def get_template_history(
        self,
        session: AsyncSession,
        template_id: str,
        tenant_key: str,
    ) -> list[TemplateArchive]:
        """
        Get template version history ordered by archived_at descending.

        Args:
            session: Active database session
            template_id: Template UUID
            tenant_key: Tenant key for isolation

        Returns:
            List of TemplateArchive ORM instances
        """
        stmt = (
            select(TemplateArchive)
            .where(
                TemplateArchive.template_id == template_id,
                TemplateArchive.tenant_key == tenant_key,
            )
            .order_by(TemplateArchive.archived_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_archive_by_id(
        self,
        session: AsyncSession,
        archive_id: str,
        template_id: str,
        tenant_key: str,
    ) -> TemplateArchive | None:
        """
        Get a specific archive entry with tenant isolation.

        Args:
            session: Active database session
            archive_id: Archive entry UUID
            template_id: Template UUID
            tenant_key: Tenant key for isolation

        Returns:
            TemplateArchive ORM instance or None
        """
        stmt = select(TemplateArchive).where(
            TemplateArchive.id == archive_id,
            TemplateArchive.template_id == template_id,
            TemplateArchive.tenant_key == tenant_key,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_template_exists_any_tenant(
        self,
        session: AsyncSession,
        template_id: str,
    ) -> bool:
        """
        Check if a template exists across any tenant.

        Args:
            session: Active database session
            template_id: Template UUID

        Returns:
            True if template exists
        """
        stmt = select(AgentTemplate).where(AgentTemplate.id == template_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None
