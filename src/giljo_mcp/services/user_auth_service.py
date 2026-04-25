# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
UserAuthService - Authentication and password management for users

Extracted from UserService as part of the 0950 pre-release quality pass.

Responsibilities:
- Password change with old-password verification
- Password reset to default
- Password verification (bcrypt)
- Username/email uniqueness checks
- Role change with admin-count guard
"""

import logging
from contextlib import asynccontextmanager

import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.models.auth import User
from giljo_mcp.repositories.user_repository import UserRepository


logger = logging.getLogger(__name__)


class UserAuthService:
    """
    Service for user authentication, password management, and role changes.

    Extracted from UserService to keep both classes under their line budgets.
    All DB queries are tenant-scoped via tenant_key.

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        websocket_manager=None,
        session: AsyncSession | None = None,
    ):
        """
        Initialize UserAuthService with database and tenant isolation.

        Args:
            db_manager: Database manager for async database operations
            tenant_key: Tenant key for multi-tenant isolation
            websocket_manager: Optional WebSocket manager (reserved for future use)
            session: Optional AsyncSession for test transaction isolation
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._websocket_manager = websocket_manager
        self._session = session
        self._repo = UserRepository()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.

        Returns:
            Context manager for database session
        """
        if self._session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._session

            return _test_session_wrapper()

        return self.db_manager.get_session_async()

    # ============================================================================
    # Password Management
    # ============================================================================

    async def change_password(
        self, user_id: str, old_password: str | None, new_password: str, is_admin: bool = False
    ) -> None:
        """
        Change user password with verification.

        Args:
            user_id: User UUID
            old_password: Current password (required for non-admin)
            new_password: New password
            is_admin: Whether request is from admin (bypasses old password check)

        Raises:
            ResourceNotFoundError: User not found
            ValidationError: Current password not provided
            AuthenticationError: Current password incorrect
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._change_password_impl(session, user_id, old_password, new_password, is_admin)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to change password")
            raise BaseGiljoError(message=str(e), context={"operation": "change_password", "user_id": user_id}) from e

    async def _change_password_impl(
        self, session: AsyncSession, user_id: str, old_password: str | None, new_password: str, is_admin: bool
    ) -> None:
        """Implementation that uses provided session (void return)

        Raises:
            ResourceNotFoundError: User not found
            ValidationError: Current password not provided
            AuthenticationError: Current password incorrect
        """
        user = await self._repo.get_user_by_id(session, user_id, self.tenant_key)

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # If not admin, verify old password
        if not is_admin:
            if not old_password:
                raise ValidationError(message="Current password is required", context={"user_id": user_id})

            if not bcrypt.checkpw(old_password.encode("utf-8"), user.password_hash.encode("utf-8")):
                raise AuthenticationError(message="Current password is incorrect", context={"user_id": user_id})

        # Hash and update password
        user.password_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user.must_change_password = False  # Clear flag after successful change

        await self._repo.commit(session)

        self._logger.info(f"Password changed for user: {user.username}")

    async def verify_password(self, user_id: str, password: str) -> bool:
        """
        Verify user password using bcrypt.

        Args:
            user_id: User UUID
            password: Password to verify

        Returns:
            True if password matches, False otherwise

        Raises:
            ResourceNotFoundError: User not found
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._verify_password_impl(session, user_id, password)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to verify password")
            raise BaseGiljoError(message=str(e), context={"operation": "verify_password", "user_id": user_id}) from e

    async def _verify_password_impl(self, session: AsyncSession, user_id: str, password: str) -> bool:
        """Implementation that uses provided session

        Returns:
            True if password matches, False otherwise

        Raises:
            ResourceNotFoundError: User not found
        """
        user = await self._repo.get_user_by_id(session, user_id, self.tenant_key)

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        return bcrypt.checkpw(password.encode("utf-8"), user.password_hash.encode("utf-8"))

    # ============================================================================
    # Validation Methods
    # ============================================================================

    async def check_username_exists(self, username: str) -> bool:
        """
        Check if username already exists.

        Args:
            username: Username to check

        Returns:
            True if username exists, False otherwise

        Raises:
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._check_username_exists_impl(session, username)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to check username")
            raise BaseGiljoError(
                message=str(e), context={"operation": "check_username_exists", "username": username}
            ) from e

    async def _check_username_exists_impl(self, session: AsyncSession, username: str) -> bool:
        """Implementation that uses provided session

        Returns:
            True if username exists, False otherwise
        """
        return await self._repo.check_username_exists(session, username)

    async def check_email_exists(self, email: str) -> bool:
        """
        Check if email already exists.

        Args:
            email: Email to check

        Returns:
            True if email exists, False otherwise

        Raises:
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._check_email_exists_impl(session, email)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to check email")
            raise BaseGiljoError(message=str(e), context={"operation": "check_email_exists", "email": email}) from e

    async def _check_email_exists_impl(self, session: AsyncSession, email: str) -> bool:
        """Implementation that uses provided session

        Returns:
            True if email exists, False otherwise
        """
        return await self._repo.check_email_exists(session, email)

    # ============================================================================
    # Role Management
    # ============================================================================

    async def change_role(self, user_id: str, new_role: str) -> User:
        """
        Change user role with admin restrictions.

        Args:
            user_id: User UUID
            new_role: New role (admin, developer, viewer)

        Returns:
            User ORM model instance with updated role

        Raises:
            ValidationError: Invalid role
            ResourceNotFoundError: User not found
            AuthorizationError: Cannot demote last admin
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._change_role_impl(session, user_id, new_role)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to change role")
            raise BaseGiljoError(
                message=str(e), context={"operation": "change_role", "user_id": user_id, "new_role": new_role}
            ) from e

    async def _change_role_impl(self, session: AsyncSession, user_id: str, new_role: str) -> User:
        """Implementation that uses provided session

        Returns:
            User ORM model instance with updated role

        Raises:
            ValidationError: Invalid role
            ResourceNotFoundError: User not found
            AuthorizationError: Cannot demote last admin
        """
        # Validate role
        valid_roles = ["admin", "developer", "viewer"]
        if new_role not in valid_roles:
            raise ValidationError(
                message=f"Invalid role. Must be one of: {', '.join(valid_roles)}",
                context={"new_role": new_role, "valid_roles": valid_roles},
            )

        user = await self._repo.get_user_by_id(session, user_id, self.tenant_key)

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Check if this is the last admin (prevent lockout)
        if user.role == "admin" and new_role != "admin":
            admin_count = await self._repo.count_admins_excluding(session, self.tenant_key, user_id)

            if admin_count == 0:
                raise AuthorizationError(
                    message="Cannot demote the last admin. At least one admin must remain.",
                    context={"user_id": user_id, "current_role": "admin", "new_role": new_role},
                )

        # Update role
        old_role = user.role
        user.role = new_role
        await self._repo.commit_and_refresh(session, user)

        self._logger.info(f"Changed role for user {user.username}: {old_role} -> {new_role}")

        return user
