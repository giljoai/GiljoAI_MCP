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

import logging
from typing import Any, ClassVar

from pydantic import ValidationError as PydanticValidationError
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.settings import Settings
from giljo_mcp.repositories.settings_repository import SettingsRepository
from giljo_mcp.schemas.jsonb_validators import validate_settings_by_category


logger = logging.getLogger(__name__)


class SettingsService:
    """
    SettingsService - Manages tenant-scoped system settings.

    Supports categories: general, network, database, integrations, security, runtime.

    Args:
        session: AsyncSession - Database session
        tenant_key: str - Tenant identifier for multi-tenant isolation

    Methods:
        get_settings(category) - Get settings for category (returns {} if not found)
        get_setting_value(category, key, default) - Get single nested key from category
        update_settings(category, settings_data) - Upsert settings for category

    Raises:
        ValidationError if category is invalid or data fails schema validation
    """

    VALID_CATEGORIES: ClassVar[set[str]] = {
        "general",
        "network",
        "database",
        "integrations",
        "security",
        "runtime",
    }

    def __init__(self, session: AsyncSession, tenant_key: str):
        self.session = session
        self.tenant_key = tenant_key
        self._repo = SettingsRepository()

    async def get_settings(self, category: str) -> dict[str, Any]:
        """
        Get settings for category.

        Args:
            category: Settings category (general, network, database, integrations, security, runtime)

        Returns:
            dict[str, Any] - Settings data (empty dict if not found).
            Intentionally returns dict because settings are dynamic key-value
            pairs with user-configurable schemas that vary by category.

        Raises:
            ValidationError: if category is invalid
        """
        if category not in self.VALID_CATEGORIES:
            raise ValidationError(f"Invalid category: {category}. Must be one of {self.VALID_CATEGORIES}")

        settings = await self._repo.get_by_category(self.session, self.tenant_key, category)

        if not settings:
            return {}

        return settings.settings_data or {}

    async def get_setting_value(self, category: str, key: str, default: Any = None) -> Any:
        """
        Get a single top-level key from a settings category.

        Convenience method for callers that only need one value (e.g., tools
        checking git_integration.enabled).

        Args:
            category: Settings category
            key: Top-level key within the settings_data dict
            default: Default value if key or category not found

        Returns:
            The value for the key, or default if not found.
        """
        data = await self.get_settings(category)
        return data.get(key, default)

    async def update_settings(self, category: str, settings_data: dict[str, Any]) -> dict[str, Any]:
        """
        Update settings for category (upsert).

        Validates settings_data against category-specific JSONB schema
        before persisting. For categories with known schemas (integrations,
        security, runtime), strict validation is applied. For others
        (general, network, database), the generic SettingsData validator is used.

        Args:
            category: Settings category
            settings_data: dict[str, Any] - Settings to save

        Returns:
            dict[str, Any] - Validated and updated settings data.

        Raises:
            ValidationError: if category is invalid or data fails schema validation
        """
        if category not in self.VALID_CATEGORIES:
            raise ValidationError(f"Invalid category: {category}. Must be one of {self.VALID_CATEGORIES}")

        # JSONB validation at write boundary (post-0962 discipline)
        try:
            validated_data = validate_settings_by_category(category, settings_data)
        except PydanticValidationError as e:
            raise ValidationError(f"Settings validation failed for category '{category}': {e}") from e

        settings = await self._repo.get_by_category(self.session, self.tenant_key, category)

        if settings:
            settings.settings_data = validated_data
        else:
            settings = Settings(tenant_key=self.tenant_key, category=category, settings_data=validated_data)
            await self._repo.add(self.session, settings)

        await self._repo.commit(self.session)
        await self._repo.refresh(self.session, settings)

        return settings.settings_data
