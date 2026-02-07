"""
Configuration repository for database configuration management.

Handover 1011: Migrates configuration queries from api/endpoints/configuration.py
and setup.py to follow the repository pattern with CRITICAL tenant isolation.
"""

from typing import List, Optional

from sqlalchemy import delete, distinct, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Configuration
from ..models.auth import User


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
    ) -> List[str]:
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

    async def get_tenant_configurations(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> List[Configuration]:
        """
        Get all configurations for a specific tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            List of Configuration instances for the tenant
        """
        result = await session.execute(select(Configuration).where(Configuration.tenant_key == tenant_key))
        return list(result.scalars().all())

    async def get_configuration_by_key(
        self,
        session: AsyncSession,
        tenant_key: str,
        key: str,
    ) -> Optional[Configuration]:
        """
        Get a specific configuration by tenant and key.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            key: Configuration key

        Returns:
            Configuration instance or None if not found
        """
        result = await session.execute(
            select(Configuration).where(Configuration.tenant_key == tenant_key, Configuration.key == key)
        )
        return result.scalar_one_or_none()

    async def delete_tenant_configurations(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> int:
        """
        Delete all configurations for a tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Number of configurations deleted
        """
        result = await session.execute(delete(Configuration).where(Configuration.tenant_key == tenant_key))
        return result.rowcount

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
        result = await session.execute(select(User).where(User.role == "admin").limit(1))
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
        except Exception:
            return False
