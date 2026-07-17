# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

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
from datetime import UTC, datetime

from sqlalchemy import select
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
from giljo_mcp.services._session_helpers import tenant_context_session
from giljo_mcp.services.oauth_refresh_service import (
    revoke_all_for_user as revoke_all_refresh_tokens_for_user,
)
from giljo_mcp.utils.password_helper import async_hash_password, async_verify_password


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
        """Yield a tenant-scoped DB session, honoring an injected test session (shared helper, BE-8000d)."""
        return tenant_context_session(self.db_manager, self.tenant_key, self._session)

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

            if not await async_verify_password(old_password, user.password_hash):
                raise AuthenticationError(message="Current password is incorrect", context={"user_id": user_id})

        # Hash and update password (off the event loop via the shared helper)
        user.password_hash = await async_hash_password(new_password)
        user.must_change_password = False  # Clear flag after successful change

        # SEC-9217b: user-first FOR UPDATE lock (same order the OAuth /refresh grant
        # takes) so a concurrent refresh grant cannot interleave with this eviction
        # and mint a surviving access+refresh pair.
        await session.execute(
            select(User.id).where(User.id == str(user.id), User.tenant_key == self.tenant_key).with_for_update()
        )

        # SEC-9047: a credential change evicts every live session. Bumping the
        # revocation epoch invalidates all outstanding access tokens (the `rev`
        # claim check in principal.py), and revoking the user's OAuth refresh
        # tokens stops them minting fresh access tokens afterwards.
        user.token_revocation_epoch = (user.token_revocation_epoch or 0) + 1
        revoked_count = await revoke_all_refresh_tokens_for_user(
            session, user_id=str(user.id), tenant_key=self.tenant_key
        )

        await session.commit()

        self._logger.info(
            f"Password changed for user: {user.username} "
            f"(revocation epoch bumped to {user.token_revocation_epoch}, "
            f"{revoked_count} refresh token(s) revoked)"
        )

    async def set_initial_password(self, user_id: str, new_password: str) -> None:
        """
        Set an INITIAL password for a user who currently has none (BE-9032).

        This completes the recovery UX for a social-only user (``password_hash
        IS NULL``, e.g. Google/GitHub sign-in with no password ever set) who
        wants to add a password as a backup login method. It is deliberately
        NOT a variant of ``change_password``: there is no ``old_password``
        parameter at all, so this method can never be reached as an
        old-password bypass for an account that already has a password --
        that account MUST go through ``change_password`` (old-password
        required) or the email password-reset flow instead.

        Args:
            user_id: User UUID
            new_password: New password to set

        Raises:
            ResourceNotFoundError: User not found
            AuthorizationError: User already has a password set (this path is
                for INITIAL password-set only, never a bypass)
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._set_initial_password_impl(session, user_id, new_password)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to set initial password")
            raise BaseGiljoError(
                message=str(e), context={"operation": "set_initial_password", "user_id": user_id}
            ) from e

    async def _set_initial_password_impl(self, session: AsyncSession, user_id: str, new_password: str) -> None:
        """Implementation that uses provided session (void return)

        Raises:
            ResourceNotFoundError: User not found
            AuthorizationError: User already has a password set
        """
        user = await self._repo.get_user_by_id(session, user_id, self.tenant_key)

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # HARD GUARD (security): this path is for an INITIAL password only.
        # A user who already has a password_hash must use change_password
        # (old_password required) or the email reset flow -- never this one.
        if user.password_hash is not None:
            raise AuthorizationError(
                message="A password is already set for this account. Use change password instead.",
                context={"user_id": user_id},
            )

        user.password_hash = await async_hash_password(new_password)
        user.must_change_password = False
        # Clear the "set a password" nudge (BE-1004/1005) -- it no longer applies.
        user.password_nudge_dismissed_at = datetime.now(UTC)

        await session.commit()

        self._logger.info(f"Initial password set for user: {user.username}")

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

        return await async_verify_password(password, user.password_hash)

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
                return await self._repo.check_username_exists(session, username)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to check username")
            raise BaseGiljoError(
                message=str(e), context={"operation": "check_username_exists", "username": username}
            ) from e

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
                return await self._repo.check_email_exists(session, email)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to check email")
            raise BaseGiljoError(message=str(e), context={"operation": "check_email_exists", "email": email}) from e

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
        await session.commit()
        await session.refresh(user)

        self._logger.info(f"Changed role for user {user.username}: {old_role} -> {new_role}")

        return user

    async def force_logout(self, user_id: str) -> User:
        """Force-log-out a user by bumping their forced-logout epoch (SEC-6011).

        Incrementing ``token_revocation_epoch`` invalidates EVERY access token
        the user currently holds: each was minted with a ``rev`` claim below the
        new epoch, so validation (principal.py) rejects them on the next request.
        A fresh login mints a token at the new epoch and works normally.

        Args:
            user_id: User UUID to force-log-out.

        Returns:
            The updated User (with the bumped epoch).

        Raises:
            ResourceNotFoundError: User not found in this tenant.
            BaseGiljoError: Database operation failed.
        """
        try:
            async with self._get_session() as session:
                return await self._force_logout_impl(session, user_id)
        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to force logout")
            raise BaseGiljoError(message=str(e), context={"operation": "force_logout", "user_id": user_id}) from e

    async def _force_logout_impl(self, session: AsyncSession, user_id: str) -> User:
        """Implementation that uses the provided session."""
        user = await self._repo.get_user_by_id(session, user_id, self.tenant_key)
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # SEC-9217b: user-first FOR UPDATE lock (same order the OAuth /refresh grant
        # takes) so a concurrent refresh grant cannot interleave with this eviction
        # and mint a surviving access+refresh pair.
        await session.execute(
            select(User.id).where(User.id == str(user.id), User.tenant_key == self.tenant_key).with_for_update()
        )

        # SEC-9217a: bring force-logout to parity with change_password (SEC-9047).
        # Bumping the epoch only invalidates outstanding ACCESS tokens (the `rev`
        # claim gate in principal.py). A held OAuth refresh token is untouched and
        # would mint a fresh access token at the NEW epoch on its next /refresh,
        # sailing past the gate. Revoking the user's refresh families closes that seam.
        user.token_revocation_epoch = (user.token_revocation_epoch or 0) + 1
        revoked_count = await revoke_all_refresh_tokens_for_user(
            session, user_id=str(user.id), tenant_key=self.tenant_key
        )
        await session.commit()
        await session.refresh(user)

        self._logger.info(
            f"Force-logout: bumped revocation epoch for user {user.username} to "
            f"{user.token_revocation_epoch} ({revoked_count} refresh token(s) revoked)"
        )
        return user
