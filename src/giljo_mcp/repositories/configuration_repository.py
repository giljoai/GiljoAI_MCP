# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Configuration repository for database configuration management.

Handover 1011: Migrates configuration queries from api/endpoints/configuration.py
and setup.py to follow the repository pattern with CRITICAL tenant isolation.
"""

from sqlalchemy import distinct, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import tenant_isolation_bypass
from giljo_mcp.models import Configuration
from giljo_mcp.models.auth import User


class ConfigurationRepository:
    """
    Repository for configuration and setup queries.

    Provides database configuration management with proper tenant isolation.
    All methods MUST include tenant_key parameter where applicable.
    """

    def __init__(self, db_manager):
        """
        Initialize configuration repository.

        Args:
            db_manager: Database manager instance
        """
        self.db = db_manager

    # ============================================================================
    # TENANT CONFIGURATION DOMAIN
    # ============================================================================

    async def list_tenant_keys(
        self,
        session: AsyncSession,
    ) -> list[str]:
        """
        List all distinct tenant keys that have custom configurations.

        Args:
            session: Async database session

        Returns:
            List of tenant keys with configurations
        """
        result = await session.execute(
            select(distinct(Configuration.tenant_key)).where(Configuration.tenant_key.isnot(None))
        )
        return [row[0] for row in result]

    # ============================================================================
    # SETUP / FIRST-RUN DOMAIN
    # ============================================================================

    async def check_admin_user_exists(
        self,
        session: AsyncSession,
    ) -> bool:
        """
        Check if at least one admin user exists (for first-run detection).

        Args:
            session: Async database session

        Returns:
            True if admin user exists, False otherwise
        """
        stmt = select(User).where(User.role == "admin").limit(1)
        with tenant_isolation_bypass(
            session,
            reason="setup guard checks for any admin user across tenants",
            models=(User,),
        ):
            result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    # ============================================================================
    # HEALTH CHECK DOMAIN
    # ============================================================================

    async def execute_health_check(
        self,
        session: AsyncSession,
    ) -> bool:
        """
        Execute simple database health check.

        Args:
            session: Async database session

        Returns:
            True if database is responsive, False otherwise
        """
        try:
            await session.execute(text("SELECT 1"))
            return True
        except (RuntimeError, OSError):
            return False
