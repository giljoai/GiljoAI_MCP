"""
Settings Service for GiljoAI MCP system settings management.

SettingsService handles CRUD operations for tenant-scoped settings (general, network, database).
Handover 0506: Settings endpoints implementation.
"""

from typing import Any, Dict

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

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

    VALID_CATEGORIES = {"general", "network", "database"}

    def __init__(self, session: AsyncSession, tenant_key: str):
        self.session = session
        self.tenant_key = tenant_key

    async def get_settings(self, category: str) -> dict[str, Any]:
        """
        Get settings for category.

        Args:
            category: str - Settings category ('general', 'network', 'database')

        Returns:
            Dict[str, Any] - Settings data (empty dict if not found)

        Raises:
            ValueError if category invalid
        """
        if category not in self.VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {category}. Must be one of {self.VALID_CATEGORIES}")

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
            settings_data: Dict[str, Any] - Settings to save

        Returns:
            Dict[str, Any] - Updated settings data

        Raises:
            ValueError if category invalid
        """
        if category not in self.VALID_CATEGORIES:
            raise ValueError(f"Invalid category: {category}. Must be one of {self.VALID_CATEGORIES}")

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
