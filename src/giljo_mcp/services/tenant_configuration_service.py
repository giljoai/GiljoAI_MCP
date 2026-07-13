# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
TenantConfigurationService - Service for DB-stored tenant configuration.

Sprint 003c: Extracted from api/endpoints/configuration.py to enforce
write discipline (no direct session.commit in endpoints).

This handles the Configuration model (DB rows), NOT config.yaml.
For YAML config, see ConfigService.
"""

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
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

    async def execute_health_check(self) -> bool:
        """Execute a database health check query.

        BE-5022b: Service wrapper for ConfigurationRepository.execute_health_check().

        Returns:
            True if the database is healthy
        """
        async with self._get_session() as session:
            return await self._repo.execute_health_check(session)
