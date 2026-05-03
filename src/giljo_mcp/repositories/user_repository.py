# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
UserRepository - Data access layer for User and UserFieldPriority entities.

BE-5022c: Extracted from user_service.py to enforce the service->repository
boundary. All database reads and writes for User (CRUD context) and
UserFieldPriority are routed through this repository.

Tenant isolation is enforced at the query level on every operation.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.auth import User, UserFieldPriority


logger = logging.getLogger(__name__)


class UserRepository:
    """
    Repository for user-domain database operations.

    Methods accept an AsyncSession parameter (session-in pattern) so the
    calling service controls transaction boundaries.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ========================================================================
    # User CRUD
    # ========================================================================

    async def list_users(
        self,
        session: AsyncSession,
        tenant_key: str,
        include_all_tenants: bool = False,
    ) -> list[User]:
        """
        List users, optionally across all tenants.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            include_all_tenants: If True, list all users (admin only)

        Returns:
            List of User ORM instances
        """
        if include_all_tenants:
            stmt = select(User).order_by(User.created_at)
        else:
            stmt = select(User).where(User.tenant_key == tenant_key).order_by(User.created_at)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_user_by_id(
        self,
        session: AsyncSession,
        user_id: str,
        tenant_key: str,
        include_all_tenants: bool = False,
    ) -> User | None:
        """
        Get user by ID with optional tenant scope.

        Args:
            session: Active database session
            user_id: User UUID
            tenant_key: Tenant key for isolation
            include_all_tenants: If True, skip tenant filter

        Returns:
            User ORM instance or None
        """
        if include_all_tenants:
            stmt = select(User).where(User.id == user_id)
        else:
            stmt = select(User).where(and_(User.id == user_id, User.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def check_username_exists(self, session: AsyncSession, username: str) -> bool:
        """
        Check if a username is already taken (global scope).

        Args:
            session: Active database session
            username: Username to check

        Returns:
            True if username exists
        """
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def check_email_exists(self, session: AsyncSession, email: str) -> bool:
        """
        Check if an email is already taken (global scope).

        Args:
            session: Active database session
            email: Email to check

        Returns:
            True if email exists
        """
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def add_user(self, session: AsyncSession, user: User) -> User:
        """
        Add a user to the session, commit, and refresh.

        Args:
            session: Active database session
            user: Fully constructed User ORM instance

        Returns:
            Refreshed User instance
        """
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user

    async def commit_and_refresh_user(self, session: AsyncSession, user: User) -> User:
        """
        Commit pending changes and refresh the user.

        Args:
            session: Active database session
            user: User ORM instance with pending changes

        Returns:
            Refreshed User instance
        """
        await session.commit()
        await session.refresh(user)
        return user

    async def commit(self, session: AsyncSession) -> None:
        """
        Commit the current transaction.

        Args:
            session: Active database session
        """
        await session.commit()

    async def soft_delete_user(self, session: AsyncSession, user: User) -> None:
        """
        Soft-delete a user (set is_active=False) and commit.

        Args:
            session: Active database session
            user: User ORM instance to deactivate
        """
        user.is_active = False
        await session.commit()

    # ========================================================================
    # UserFieldPriority operations
    # ========================================================================

    async def get_field_priorities(
        self,
        session: AsyncSession,
        user_id: str,
        tenant_key: str,
    ) -> list[UserFieldPriority]:
        """
        Get all field priority rows for a user.

        Args:
            session: Active database session
            user_id: User UUID
            tenant_key: Tenant key for isolation

        Returns:
            List of UserFieldPriority ORM instances
        """
        stmt = select(UserFieldPriority).where(
            and_(
                UserFieldPriority.user_id == user_id,
                UserFieldPriority.tenant_key == tenant_key,
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def add_field_priority(self, session: AsyncSession, priority: UserFieldPriority) -> None:
        """
        Add a field priority record to the session.

        Args:
            session: Active database session
            priority: Fully constructed UserFieldPriority ORM instance
        """
        session.add(priority)

    async def delete_field_priority(self, session: AsyncSession, priority: UserFieldPriority) -> None:
        """
        Delete a field priority record from the session.

        Args:
            session: Active database session
            priority: UserFieldPriority ORM instance to delete
        """
        await session.delete(priority)

    async def count_admins_excluding(
        self,
        session: AsyncSession,
        tenant_key: str,
        exclude_user_id: str,
    ) -> int:
        """
        Count active admins excluding a specific user.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            exclude_user_id: User to exclude from count

        Returns:
            Count of other active admins
        """
        from sqlalchemy import func

        stmt = select(func.count(User.id)).where(
            and_(User.tenant_key == tenant_key, User.role == "admin", User.is_active, User.id != exclude_user_id)
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def commit_and_refresh(self, session: AsyncSession, entity) -> None:
        """
        Commit and refresh any entity.

        Args:
            session: Active database session
            entity: ORM instance to refresh
        """
        await session.commit()
        await session.refresh(entity)

    async def bulk_disable_field_priority(
        self,
        session: AsyncSession,
        tenant_key: str,
        category: str,
    ) -> int:
        """
        Bulk-disable a field priority category for all tenant users.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            category: Category to disable (must be in TOGGLEABLE_CATEGORIES)

        Returns:
            Number of rows updated
        """
        stmt = (
            update(UserFieldPriority)
            .where(
                and_(
                    UserFieldPriority.tenant_key == tenant_key,
                    UserFieldPriority.category == category,
                    UserFieldPriority.enabled.is_(True),
                )
            )
            .values(enabled=False, updated_at=datetime.now(UTC))
        )
        result = await session.execute(stmt)
        await session.commit()
        return result.rowcount
