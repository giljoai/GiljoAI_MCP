# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Base repository with automatic tenant filtering.

Handover 0017: Provides foundation for all repository classes with CRITICAL tenant isolation.
Every database operation MUST filter by tenant_key for security.
"""

from __future__ import annotations

from typing import Generic, TypeVar

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from src.giljo_mcp.database import DatabaseManager

T = TypeVar("T")


class BaseRepository(Generic[T]):
    """
    Base repository with automatic tenant filtering.

    CRITICAL: All database operations automatically filter by tenant_key.
    This prevents cross-tenant data access - a security vulnerability if missed.
    """

    def __init__(self, model_class: type[T], db_manager: DatabaseManager):
        """
        Initialize base repository.

        Args:
            model_class: SQLAlchemy model class
            db_manager: Database manager instance
        """
        self.model_class = model_class
        self.db = db_manager

    def create(self, session: Session, tenant_key: str, **data) -> T:
        """
        Create entity with tenant isolation.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            **data: Model field values

        Returns:
            Created entity instance
        """
        entity = self.model_class(tenant_key=tenant_key, **data)
        session.add(entity)
        session.flush()
        return entity

    async def get_by_id(self, session: AsyncSession, tenant_key: str, entity_id: str) -> T | None:
        """
        Get entity by ID with tenant filter.

        CRITICAL: Always filters by tenant_key to prevent cross-tenant access.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            entity_id: Entity ID to retrieve

        Returns:
            Entity instance or None if not found
        """
        result = await session.execute(
            select(self.model_class).where(self.model_class.tenant_key == tenant_key, self.model_class.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def list_all(self, session: AsyncSession, tenant_key: str) -> list[T]:
        """
        List all entities for tenant.

        CRITICAL: Only returns entities belonging to the tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            List of entities for the tenant
        """
        result = await session.execute(select(self.model_class).where(self.model_class.tenant_key == tenant_key))
        return list(result.scalars().all())

    def delete(self, session: Session, tenant_key: str, entity_id: str) -> bool:
        """
        Delete entity with tenant check.

        CRITICAL: Verifies entity belongs to tenant before deletion.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            entity_id: Entity ID to delete

        Returns:
            True if entity was deleted, False if not found
        """
        entity = self.get_by_id(session, tenant_key, entity_id)
        if entity:
            session.delete(entity)
            return True
        return False

    async def count(self, session: AsyncSession, tenant_key: str) -> int:
        """
        Count entities for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation

        Returns:
            Number of entities for the tenant
        """
        result = await session.execute(
            select(func.count()).select_from(self.model_class).where(self.model_class.tenant_key == tenant_key)
        )
        return result.scalar()

    async def exists(self, session: AsyncSession, tenant_key: str, entity_id: str) -> bool:
        """
        Check if entity exists for tenant.

        Args:
            session: Async database session
            tenant_key: Tenant key for isolation
            entity_id: Entity ID to check

        Returns:
            True if entity exists for tenant, False otherwise
        """
        result = await session.execute(
            select(self.model_class).where(self.model_class.tenant_key == tenant_key, self.model_class.id == entity_id)
        )
        return result.scalar_one_or_none() is not None
