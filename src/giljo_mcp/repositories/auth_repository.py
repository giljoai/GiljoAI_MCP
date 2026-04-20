# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
AuthRepository - Data access layer for authentication-related entities.

BE-5022c: Extracted from auth_service.py to enforce the service->repository
boundary. All database reads and writes for User (auth context), APIKey,
SetupState, Organization (creation during registration), and OrgMembership
(creation during registration) are routed through this repository.

Tenant isolation is enforced at the query level where applicable.
Auth operations (login) intentionally omit tenant_key filters because
the user's tenant is unknown until after authentication succeeds.
"""

from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.auth import APIKey, User
from giljo_mcp.models.config import SetupState
from giljo_mcp.models.organizations import Organization, OrgMembership


logger = logging.getLogger(__name__)


class AuthRepository:
    """
    Repository for authentication-related database operations.

    Methods accept an AsyncSession parameter (session-in pattern) so the
    calling service controls transaction boundaries.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ========================================================================
    # User lookups (auth context -- no tenant_key filter for login)
    # ========================================================================

    async def get_user_by_username(self, session: AsyncSession, username: str) -> User | None:
        """
        Get user by username (cross-tenant, used for login).

        Args:
            session: Active database session
            username: Username to look up

        Returns:
            User ORM instance or None
        """
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_user_by_id(self, session: AsyncSession, user_id: str) -> User | None:
        """
        Get user by ID (cross-tenant, used for last-login updates).

        Args:
            session: Active database session
            user_id: User UUID

        Returns:
            User ORM instance or None
        """
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def update_last_login(self, session: AsyncSession, user: User, timestamp: datetime) -> None:
        """
        Set the last_login timestamp on a user and commit.

        Args:
            session: Active database session
            user: User ORM instance (must be attached to session)
            timestamp: Login timestamp (UTC)
        """
        user.last_login = timestamp
        await session.commit()

    async def get_total_user_count(self, session: AsyncSession) -> int:
        """
        Count all users across all tenants (used for first-admin guard).

        Args:
            session: Active database session

        Returns:
            Total user count
        """
        stmt = select(func.count(User.id))
        result = await session.execute(stmt)
        return result.scalar() or 0

    # ========================================================================
    # SetupState
    # ========================================================================

    async def get_setup_state(self, session: AsyncSession, tenant_key: str) -> SetupState | None:
        """
        Get setup state for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            SetupState ORM instance or None
        """
        stmt = select(SetupState).where(SetupState.tenant_key == tenant_key)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def create_setup_state(self, session: AsyncSession, setup_state: SetupState) -> None:
        """
        Add a new SetupState record to the session.

        Args:
            session: Active database session
            setup_state: Fully constructed SetupState ORM instance
        """
        session.add(setup_state)

    # ========================================================================
    # API Key operations
    # ========================================================================

    async def list_api_keys(
        self,
        session: AsyncSession,
        user_id: str,
        include_revoked: bool = False,
    ) -> list[APIKey]:
        """
        List API keys for a user, ordered by created_at descending.

        Args:
            session: Active database session
            user_id: User UUID
            include_revoked: Include revoked (inactive) keys

        Returns:
            List of APIKey ORM instances
        """
        if include_revoked:
            stmt = select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
        else:
            stmt = select(APIKey).where(APIKey.user_id == user_id, APIKey.is_active).order_by(APIKey.created_at.desc())
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def count_active_api_keys(self, session: AsyncSession, user_id: str) -> int:
        """
        Count active (non-expired) API keys for a user.

        Args:
            session: Active database session
            user_id: User UUID

        Returns:
            Count of active keys
        """
        result = await session.scalar(
            select(func.count())
            .select_from(APIKey)
            .where(
                APIKey.user_id == user_id,
                APIKey.is_active.is_(True),
                or_(APIKey.expires_at > func.now(), APIKey.expires_at.is_(None)),
            )
        )
        return result or 0

    async def create_api_key(self, session: AsyncSession, api_key: APIKey) -> APIKey:
        """
        Persist a new API key, commit, and refresh.

        Args:
            session: Active database session
            api_key: Fully constructed APIKey ORM instance

        Returns:
            Refreshed APIKey instance
        """
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return api_key

    async def get_api_key_by_id_and_user(self, session: AsyncSession, key_id: str, user_id: str) -> APIKey | None:
        """
        Get an API key by ID scoped to a user.

        Args:
            session: Active database session
            key_id: API key UUID
            user_id: User UUID (ownership check)

        Returns:
            APIKey ORM instance or None
        """
        stmt = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def revoke_api_key(
        self,
        session: AsyncSession,
        api_key: APIKey,
        revoked_at: datetime,
    ) -> None:
        """
        Mark an API key as revoked and commit.

        Args:
            session: Active database session
            api_key: APIKey ORM instance to revoke
            revoked_at: Revocation timestamp (UTC)
        """
        api_key.is_active = False
        api_key.revoked_at = revoked_at
        await session.commit()

    # ========================================================================
    # User registration (write helpers)
    # ========================================================================

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

    async def create_user(self, session: AsyncSession, user: User) -> User:
        """
        Add a user to the session and flush (to obtain user.id).

        Does NOT commit -- the caller manages transaction boundaries
        (e.g., to also create memberships in the same transaction).

        Args:
            session: Active database session
            user: Fully constructed User ORM instance

        Returns:
            User instance with generated id
        """
        session.add(user)
        await session.flush()
        return user

    async def commit_and_refresh_user(self, session: AsyncSession, user: User) -> User:
        """
        Commit the current transaction and refresh the user.

        Args:
            session: Active database session
            user: User ORM instance

        Returns:
            Refreshed User instance
        """
        await session.commit()
        await session.refresh(user)
        return user

    # ========================================================================
    # Organization & Membership helpers (used during registration)
    # ========================================================================

    async def create_organization(self, session: AsyncSession, org: Organization) -> Organization:
        """
        Add an organization and flush (to obtain org.id).

        Args:
            session: Active database session
            org: Fully constructed Organization ORM instance

        Returns:
            Organization with generated id
        """
        session.add(org)
        await session.flush()
        return org

    async def create_org_membership(self, session: AsyncSession, membership: OrgMembership) -> None:
        """
        Add an organization membership to the session.

        Args:
            session: Active database session
            membership: Fully constructed OrgMembership ORM instance
        """
        session.add(membership)

    async def get_user_with_org(self, session: AsyncSession, user_id: str) -> User | None:
        """
        Get user with eagerly loaded organization relationship.

        Args:
            session: Active database session
            user_id: User UUID

        Returns:
            User ORM instance with organization loaded, or None
        """
        from sqlalchemy.orm import selectinload

        stmt = select(User).where(User.id == user_id).options(selectinload(User.organization))
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_org_membership(self, session: AsyncSession, org_id: str, user_id: str) -> OrgMembership | None:
        """
        Get a specific organization membership.

        Args:
            session: Active database session
            org_id: Organization UUID
            user_id: User UUID

        Returns:
            OrgMembership ORM instance or None
        """
        stmt = select(OrgMembership).where(OrgMembership.org_id == org_id).where(OrgMembership.user_id == user_id)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def commit(self, session: AsyncSession) -> None:
        """
        Commit the current transaction.

        Args:
            session: Active database session
        """
        await session.commit()
