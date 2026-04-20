# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
SettingsRepository - Data access layer for Settings entities.

BE-5022d: Extracted from settings_service.py to enforce the service->repository
boundary for discrete queries. SettingsService manages session lifecycle
(documented exception), but discrete queries are routed through this repository.

Tenant isolation is enforced at the query level on every operation.
"""

from __future__ import annotations

import logging

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.settings import Settings


logger = logging.getLogger(__name__)


class SettingsRepository:
    """
    Repository for settings-domain database operations.

    Methods accept an AsyncSession parameter (session-in pattern) so the
    calling service controls transaction boundaries.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def get_by_category(
        self,
        session: AsyncSession,
        tenant_key: str,
        category: str,
    ) -> Settings | None:
        """
        Get settings for a specific category with tenant isolation.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            category: Settings category

        Returns:
            Settings ORM instance or None
        """
        stmt = select(Settings).where(and_(Settings.tenant_key == tenant_key, Settings.category == category))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def add(self, session: AsyncSession, settings: Settings) -> None:
        """
        Add a settings entity to the session.

        Args:
            session: Active database session
            settings: Fully constructed Settings ORM instance
        """
        session.add(settings)

    async def commit(self, session: AsyncSession) -> None:
        """
        Commit the current transaction.

        Args:
            session: Active database session
        """
        await session.commit()

    async def refresh(self, session: AsyncSession, entity) -> None:
        """
        Refresh an entity from the database.

        Args:
            session: Active database session
            entity: ORM instance to refresh
        """
        await session.refresh(entity)
