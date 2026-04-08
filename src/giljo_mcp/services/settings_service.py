# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Settings Service for GiljoAI MCP system settings management.

SettingsService handles CRUD operations for tenant-scoped settings (general, network, database).
Handover 0506: Settings endpoints implementation.
Updated Handover 0731: Reviewed for typed returns - dict[str, Any] retained because
settings are genuinely dynamic key-value pairs with user-configurable schemas that
vary by category and deployment. No fixed Pydantic model can represent the full range
of settings configurations.
"""

from typing import Any, ClassVar

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.models.settings import Settings


class SettingsService:
    """
    SettingsService - Manages tenant-scoped system settings (general, network, database).

    Args:
        session: AsyncSession - Database session
        tenant_key: str - Tenant identifier for multi-tenant isolation

    Methods:
        get_settings(category) - Get settings for category (returns {} if not found)
        update_settings(category, settings_data) - Upsert settings for category

    Raises:
        ValueError if category is invalid
    """

    VALID_CATEGORIES: ClassVar[set[str]] = {"general", "network", "database"}

    def __init__(self, session: AsyncSession, tenant_key: str):
        self.session = session
        self.tenant_key = tenant_key

    async def get_settings(self, category: str) -> dict[str, Any]:
        """
        Get settings for category.

        Args:
            category: str - Settings category ('general', 'network', 'database')

        Returns:
            dict[str, Any] - Settings data (empty dict if not found).
            Intentionally returns dict because settings are dynamic key-value
            pairs with user-configurable schemas that vary by category.

        Raises:
            ValidationError: if category is invalid
        """
        if category not in self.VALID_CATEGORIES:
            raise ValidationError(f"Invalid category: {category}. Must be one of {self.VALID_CATEGORIES}")

        stmt = select(Settings).where(and_(Settings.tenant_key == self.tenant_key, Settings.category == category))
        result = await self.session.execute(stmt)
        settings = result.scalar_one_or_none()

        if not settings:
            return {}

        return settings.settings_data or {}

    async def update_settings(self, category: str, settings_data: dict[str, Any]) -> dict[str, Any]:
        """
        Update settings for category (upsert).

        Args:
            category: str - Settings category ('general', 'network', 'database')
            settings_data: dict[str, Any] - Settings to save

        Returns:
            dict[str, Any] - Updated settings data.
            Intentionally returns dict because settings are dynamic key-value
            pairs with user-configurable schemas that vary by category.

        Raises:
            ValidationError: if category is invalid
        """
        if category not in self.VALID_CATEGORIES:
            raise ValidationError(f"Invalid category: {category}. Must be one of {self.VALID_CATEGORIES}")

        stmt = select(Settings).where(and_(Settings.tenant_key == self.tenant_key, Settings.category == category))
        result = await self.session.execute(stmt)
        settings = result.scalar_one_or_none()

        if settings:
            # Update existing
            settings.settings_data = settings_data
        else:
            # Create new
            settings = Settings(tenant_key=self.tenant_key, category=category, settings_data=settings_data)
            self.session.add(settings)

        await self.session.commit()
        await self.session.refresh(settings)

        return settings.settings_data
