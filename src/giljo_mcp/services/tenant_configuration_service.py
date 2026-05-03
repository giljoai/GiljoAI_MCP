# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
TenantConfigurationService - Service for DB-stored tenant configuration.

Sprint 003c: Extracted from api/endpoints/configuration.py to enforce
write discipline (no direct session.commit in endpoints).

This handles the Configuration model (DB rows), NOT config.yaml.
For YAML config, see ConfigService.
"""

import json
import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Configuration
from giljo_mcp.repositories.configuration_repository import ConfigurationRepository


logger = logging.getLogger(__name__)


class TenantConfigurationService:
    """
    Service for managing DB-stored tenant configurations.

    Wraps ConfigurationRepository with session management and commit control.
    All writes go through this service — endpoints never commit directly.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._session = session
        self._repo = ConfigurationRepository(db_manager)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._session

            return _test_session_wrapper()

        return self.db_manager.get_session_async()

    async def set_configurations(
        self,
        configurations: dict[str, Any],
    ) -> int:
        """
        Create or update multiple configuration entries for the tenant.

        Args:
            configurations: Dict of key-value pairs to set.

        Returns:
            Number of configurations updated/created.
        """
        async with self._get_session() as session:
            for key, value in configurations.items():
                config = await self._repo.get_configuration_by_key(session, self.tenant_key, key)

                if config:
                    config.value = json.dumps(value) if value is not None else None
                    config.updated_at = datetime.now(UTC)
                else:
                    config = Configuration(
                        tenant_key=self.tenant_key,
                        key=key,
                        value=(json.dumps(value) if value is not None else None),
                    )
                    await self._repo.add_configuration(session, config)

            await self._repo.commit(session)

            self._logger.info(
                "Updated %d configurations for tenant %s",
                len(configurations),
                self.tenant_key,
            )

        return len(configurations)

    async def delete_all_configurations(self) -> int:
        """
        Delete all configuration entries for the tenant.

        Returns:
            Number of configurations deleted.

        Raises:
            ResourceNotFoundError: No configurations found (caller decides HTTP code).
        """
        async with self._get_session() as session:
            deleted_count = await self._repo.delete_tenant_configurations(session, self.tenant_key)
            await self._repo.commit(session)

            self._logger.info(
                "Deleted %d configurations for tenant %s",
                deleted_count,
                self.tenant_key,
            )

        return deleted_count

    # ---- BE-5022b: Service wrappers for ConfigurationRepository methods ----

    async def get_tenant_configurations(self) -> list:
        """Fetch all configuration entries for the tenant.

        BE-5022b: Service wrapper for ConfigurationRepository.get_tenant_configurations().

        Returns:
            List of Configuration model instances for this tenant
        """
        async with self._get_session() as session:
            return await self._repo.get_tenant_configurations(session, self.tenant_key)

    async def execute_health_check(self) -> bool:
        """Execute a database health check query.

        BE-5022b: Service wrapper for ConfigurationRepository.execute_health_check().

        Returns:
            True if the database is healthy
        """
        async with self._get_session() as session:
            return await self._repo.execute_health_check(session)
