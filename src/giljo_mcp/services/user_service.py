# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
UserService - Dedicated service for user domain logic

Handover 0322 Phase 1: Extract user operations from direct database access
to follow established service layer pattern.
Handover 0950: Auth/password/role methods extracted to UserAuthService.

Responsibilities:
- CRUD operations for users (create, read, update, soft-delete)
- Field priority and depth configuration
- Execution mode management
- Facades for auth/password/role ops (delegated to UserAuthService)
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

import bcrypt
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.auth import TOGGLEABLE_CATEGORIES, User, UserFieldPriority
from src.giljo_mcp.services.user_auth_service import UserAuthService


logger = logging.getLogger(__name__)


class UserService:
    """
    Service for managing user lifecycle and operations.

    Handles CRUD, field-priority/depth config, and execution mode.
    Auth/password/role operations are delegated to UserAuthService via facades.

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self, db_manager: DatabaseManager, tenant_key: str, websocket_manager=None, session: AsyncSession | None = None
    ):
        """
        Initialize UserService with database and tenant isolation.

        Args:
            db_manager: Database manager for async database operations
            tenant_key: Tenant key for multi-tenant isolation
            websocket_manager: Optional WebSocket manager for event emission (Handover 0139a)
            session: Optional AsyncSession for test transaction isolation (Handover 0324)
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._websocket_manager = websocket_manager
        self._session = session  # Store for test transaction isolation
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._auth = UserAuthService(db_manager, tenant_key, websocket_manager, session)

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
    # CRUD Operations
    # ============================================================================

    async def list_users(self, include_all_tenants: bool = False) -> list[User]:
        """
        List all users (tenant-scoped by default).

        Args:
            include_all_tenants: If True, list users from all tenants (admin only)

        Returns:
            List of User ORM model instances

        Raises:
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._list_users_impl(session, include_all_tenants)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to list users")
            raise BaseGiljoError(
                message=str(e), context={"operation": "list_users", "tenant_key": self.tenant_key}
            ) from e

    async def _list_users_impl(self, session: AsyncSession, include_all_tenants: bool = False) -> list[User]:
        """Implementation that uses provided session"""
        if include_all_tenants:
            # Admin cross-tenant view - see all users
            stmt = select(User).order_by(User.created_at)
        else:
            # Regular tenant-isolated view
            stmt = select(User).where(User.tenant_key == self.tenant_key).order_by(User.created_at)
        result = await session.execute(stmt)
        users = list(result.scalars().all())

        log_msg = f"Found {len(users)} users" + (
            " (all tenants)" if include_all_tenants else f" for tenant {self.tenant_key}"
        )
        self._logger.debug(log_msg)

        return users

    async def get_user(self, user_id: str, include_all_tenants: bool = False) -> User:
        """
        Get a specific user by ID.

        Args:
            user_id: User UUID
            include_all_tenants: If True, allow fetching users from any tenant (admin only)

        Returns:
            User ORM model instance

        Raises:
            ResourceNotFoundError: User not found
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._get_user_impl(session, user_id, include_all_tenants)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to get user")
            raise BaseGiljoError(message=str(e), context={"operation": "get_user", "user_id": user_id}) from e

    async def _get_user_impl(self, session: AsyncSession, user_id: str, include_all_tenants: bool = False) -> User:
        """Implementation that uses provided session

        Returns:
            User ORM model instance

        Raises:
            ResourceNotFoundError: User not found
        """
        if include_all_tenants:
            # Admin cross-tenant fetch
            stmt = select(User).where(User.id == user_id)
        else:
            # Regular tenant-isolated fetch
            stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        self._logger.info("Fetched user", extra={"user_id": user_id})

        return user

    async def create_user(
        self,
        username: str,
        email: str | None = None,
        full_name: str | None = None,
        password: str | None = None,
        role: str = "developer",
        is_active: bool = True,
    ) -> User:
        """
        Create a new user.

        Args:
            username: Unique username (required)
            email: User email address
            full_name: User's full name
            password: User password (defaults to "GiljoMCP" if not provided)
            role: User role (admin, developer, viewer)
            is_active: Whether user account is active

        Returns:
            User ORM model instance

        Raises:
            ValidationError: Username or email already exists
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._create_user_impl(session, username, email, full_name, password, role, is_active)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to create user")
            raise BaseGiljoError(message=str(e), context={"operation": "create_user", "username": username}) from e

    async def _create_user_impl(
        self,
        session: AsyncSession,
        username: str,
        email: str | None,
        full_name: str | None,
        password: str | None,
        role: str,
        is_active: bool,
    ) -> User:
        """Implementation that uses provided session

        Returns:
            User ORM model instance

        Raises:
            ValidationError: Username or email already exists
        """
        # Check for duplicate username (global uniqueness)
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise ValidationError(message=f"Username '{username}' already exists", context={"username": username})

        # Check for duplicate email if provided
        if email:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                raise ValidationError(message=f"Email '{email}' already exists", context={"email": email})

        # Hash password (default to "GiljoMCP" per Handover 0023)
        password_hash = bcrypt.hashpw((password or "GiljoMCP").encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        # Create user
        user = User(
            id=str(uuid4()),
            username=username,
            email=email,
            full_name=full_name,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
            tenant_key=self.tenant_key,
            must_change_password=bool(not password),  # Force change if default password
            must_set_pin=True,  # Force PIN setup on first login
            recovery_pin_hash=None,  # No PIN set initially
            created_at=datetime.now(timezone.utc),
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        self._logger.info(f"Created user {user.id} for tenant {self.tenant_key}")

        return user

    async def update_user(self, user_id: str, include_all_tenants: bool = False, **updates) -> User:
        """
        Update a user.

        Args:
            user_id: User UUID
            include_all_tenants: If True, allow updating users from any tenant (admin only)
            **updates: Fields to update (email, full_name, is_active)

        Returns:
            User ORM model instance

        Raises:
            ResourceNotFoundError: User not found
            ValidationError: Email already exists
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._update_user_impl(session, user_id, updates, include_all_tenants)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to update user")
            raise BaseGiljoError(message=str(e), context={"operation": "update_user", "user_id": user_id}) from e

    async def _update_user_impl(
        self, session: AsyncSession, user_id: str, updates: dict, include_all_tenants: bool = False
    ) -> User:
        """Implementation that uses provided session

        Returns:
            User ORM model instance

        Raises:
            ResourceNotFoundError: User not found
            ValidationError: Email already exists
        """
        if include_all_tenants:
            # Admin cross-tenant update
            stmt = select(User).where(User.id == user_id)
        else:
            # Regular tenant-isolated update
            stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Check for duplicate username if changing username
        if "username" in updates and updates["username"] and updates["username"] != user.username:
            stmt = select(User).where(User.username == updates["username"])
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise ValidationError(
                    message=f"Username '{updates['username']}' already taken",
                    context={"username": updates["username"], "user_id": user_id},
                )

        # Check for duplicate email if changing email
        if "email" in updates and updates["email"] and updates["email"] != user.email:
            stmt = select(User).where(User.email == updates["email"])
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            if existing_user:
                raise ValidationError(
                    message=f"Email '{updates['email']}' already exists",
                    context={"email": updates["email"], "user_id": user_id},
                )

        # Apply updates (only allowed fields)
        allowed_fields = {"username", "email", "full_name", "is_active"}
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(user, field, value)

        # Handle password update separately (needs hashing)
        if updates.get("password"):
            user.password_hash = bcrypt.hashpw(updates["password"].encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
            self._logger.info(f"Password updated for user {user_id}")

        await session.commit()
        await session.refresh(user)

        self._logger.info(f"Updated user {user_id}")

        return user

    async def delete_user(self, user_id: str) -> None:
        """
        Soft delete a user (set is_active=False).

        Args:
            user_id: User UUID to delete

        Raises:
            ResourceNotFoundError: User not found
            BaseGiljoError: Database operation failed
        """
        try:
            async with self._get_session() as session:
                return await self._delete_user_impl(session, user_id)

        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise  # Re-raise without wrapping
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to delete user")
            raise BaseGiljoError(message=str(e), context={"operation": "delete_user", "user_id": user_id}) from e

    async def _delete_user_impl(self, session: AsyncSession, user_id: str) -> None:
        """Implementation that uses provided session (void return - soft delete)

        Raises:
            ResourceNotFoundError: User not found
        """
        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Soft delete
        user.is_active = False

        await session.commit()

        self._logger.info(f"Soft deleted user {user_id}")

    # ============================================================================
    # Role Management (facade — implementation in UserAuthService)
    # ============================================================================

    async def change_role(self, *a, **kw) -> User:
        """Facade: delegates to UserAuthService."""
        return await self._auth.change_role(*a, **kw)

    # ============================================================================
    # Password Management (facade — implementation in UserAuthService)
    # ============================================================================

    async def change_password(self, *a, **kw) -> None:
        """Facade: delegates to UserAuthService."""
        return await self._auth.change_password(*a, **kw)

    async def reset_password(self, *a, **kw) -> None:
        """Facade: delegates to UserAuthService."""
        return await self._auth.reset_password(*a, **kw)

    async def verify_password(self, *a, **kw) -> bool:
        """Facade: delegates to UserAuthService."""
        return await self._auth.verify_password(*a, **kw)

    # ============================================================================
    # Validation Methods (facade — implementation in UserAuthService)
    # ============================================================================

    async def check_username_exists(self, *a, **kw) -> bool:
        """Facade: delegates to UserAuthService."""
        return await self._auth.check_username_exists(*a, **kw)

    async def check_email_exists(self, *a, **kw) -> bool:
        """Facade: delegates to UserAuthService."""
        return await self._auth.check_email_exists(*a, **kw)

    # ============================================================================
    # Configuration Management
    # ============================================================================

    async def get_field_priority_config(self, user_id: str) -> dict[str, Any]:
        """Get user's field toggle configuration from user_field_priorities table.

        Returns backward-compatible dict with version + priorities keys.
        """
        try:
            async with self._get_session() as session:
                return await self._get_field_priority_config_impl(session, user_id)
        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to get field priority config")
            raise BaseGiljoError(
                message=str(e), context={"operation": "get_field_priority_config", "user_id": user_id}
            ) from e

    async def _get_field_priority_config_impl(self, session: AsyncSession, user_id: str) -> dict[str, Any]:
        """Query user_field_priorities table and build backward-compatible response."""
        from src.giljo_mcp.config.defaults import DEFAULT_CATEGORY_TOGGLES, DEFAULT_FIELD_PRIORITY

        # Verify user exists
        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Query user's toggle rows
        prio_stmt = select(UserFieldPriority).where(
            and_(UserFieldPriority.user_id == user_id, UserFieldPriority.tenant_key == self.tenant_key)
        )
        prio_result = await session.execute(prio_stmt)
        rows = prio_result.scalars().all()

        if not rows:
            return DEFAULT_FIELD_PRIORITY

        # Build priorities dict from rows, merging with defaults for missing categories
        toggles = dict(DEFAULT_CATEGORY_TOGGLES)
        for row in rows:
            toggles[row.category] = row.enabled

        # Build backward-compatible response (always-on categories included)
        priorities = {
            "product_core": {"toggle": True},
            "project_description": {"toggle": True},
        }
        for cat, enabled in toggles.items():
            priorities[cat] = {"toggle": enabled}

        return {"version": "4.0", "priorities": priorities}

    async def update_field_priority_config(self, user_id: str, config: dict[str, Any]) -> None:
        """Update user's field toggle config by upserting user_field_priorities rows."""
        try:
            async with self._get_session() as session:
                return await self._update_field_priority_config_impl(session, user_id, config)
        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to update field priority config")
            raise BaseGiljoError(
                message=str(e), context={"operation": "update_field_priority_config", "user_id": user_id}
            ) from e

    async def _update_field_priority_config_impl(
        self, session: AsyncSession, user_id: str, config: dict[str, Any]
    ) -> None:
        """Upsert toggleable categories into user_field_priorities table."""
        priorities = config.get("priorities", config)

        # Validate toggles
        for category, value in priorities.items():
            if isinstance(value, dict):
                if "toggle" not in value or not isinstance(value["toggle"], bool):
                    raise ValidationError(
                        message=f"Invalid toggle config for category '{category}'. Must have boolean 'toggle' key",
                        context={"category": category, "value": value},
                    )
            elif not isinstance(value, bool):
                raise ValidationError(
                    message=f"Invalid value for category '{category}'. Must be bool or dict with 'toggle'",
                    context={"category": category, "value": value},
                )

        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Get existing priority rows
        prio_stmt = select(UserFieldPriority).where(
            and_(UserFieldPriority.user_id == user_id, UserFieldPriority.tenant_key == self.tenant_key)
        )
        prio_result = await session.execute(prio_stmt)
        existing = {row.category: row for row in prio_result.scalars().all()}

        # Upsert toggleable categories
        now = datetime.now(timezone.utc)
        for category, value in priorities.items():
            if category not in TOGGLEABLE_CATEGORIES:
                continue  # Skip always-on categories

            enabled = value["toggle"] if isinstance(value, dict) else value

            if category in existing:
                existing[category].enabled = enabled
                existing[category].updated_at = now
            else:
                session.add(
                    UserFieldPriority(
                        id=str(uuid4()),
                        user_id=user_id,
                        tenant_key=self.tenant_key,
                        category=category,
                        enabled=enabled,
                        created_at=now,
                        updated_at=now,
                    )
                )

        await session.commit()
        self._logger.info(f"Updated field toggle config for user {user.username}")

        await self._emit_websocket_event(
            event_type="toggle_config_updated",
            data={"user_id": user_id, "toggles": priorities, "version": config.get("version", "4.0")},
        )

    async def reset_field_priority_config(self, user_id: str) -> None:
        """Reset field priority configuration by deleting all user_field_priorities rows."""
        try:
            async with self._get_session() as session:
                return await self._reset_field_priority_config_impl(session, user_id)
        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to reset field priority config")
            raise BaseGiljoError(
                message=str(e), context={"operation": "reset_field_priority_config", "user_id": user_id}
            ) from e

    async def _reset_field_priority_config_impl(self, session: AsyncSession, user_id: str) -> None:
        """Delete all user_field_priorities rows for user (reverts to defaults)."""
        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Delete all priority rows
        prio_stmt = select(UserFieldPriority).where(
            and_(UserFieldPriority.user_id == user_id, UserFieldPriority.tenant_key == self.tenant_key)
        )
        prio_result = await session.execute(prio_stmt)
        for row in prio_result.scalars().all():
            await session.delete(row)

        await session.commit()
        self._logger.info(f"Reset field priority config for user {user.username}")

    async def get_depth_config(self, user_id: str) -> dict[str, Any]:
        """Get user's depth configuration from columns on users table."""
        try:
            async with self._get_session() as session:
                return await self._get_depth_config_impl(session, user_id)
        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to get depth config")
            raise BaseGiljoError(message=str(e), context={"operation": "get_depth_config", "user_id": user_id}) from e

    async def _get_depth_config_impl(self, session: AsyncSession, user_id: str) -> dict[str, Any]:
        """Read depth columns from users table, return as dict."""
        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        return {
            "vision_documents": user.depth_vision_documents,
            "memory_last_n_projects": user.depth_memory_last_n,
            "git_commits": user.depth_git_commits,
            "agent_templates": user.depth_agent_templates,
            "tech_stack_sections": user.depth_tech_stack_sections,
            "architecture_depth": user.depth_architecture,
            "execution_mode": user.execution_mode,
        }

    async def update_depth_config(self, user_id: str, config: dict[str, Any]) -> None:
        """Update user's depth columns on users table."""
        try:
            async with self._get_session() as session:
                return await self._update_depth_config_impl(session, user_id, config)
        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            self._logger.exception("Failed to update depth config")
            raise BaseGiljoError(
                message=str(e), context={"operation": "update_depth_config", "user_id": user_id}
            ) from e

    async def _update_depth_config_impl(self, session: AsyncSession, user_id: str, config: dict[str, Any]) -> None:
        """Update depth columns on users table from config dict."""
        valid_vision = ["none", "optional", "light", "medium", "full"]
        if "vision_documents" in config and config["vision_documents"] not in valid_vision:
            raise ValidationError(
                message=f"Invalid vision_documents. Must be one of: {', '.join(valid_vision)}",
                context={"vision_documents": config["vision_documents"], "valid_values": valid_vision},
            )

        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        # Map config dict keys to column names
        column_map = {
            "vision_documents": "depth_vision_documents",
            "memory_last_n_projects": "depth_memory_last_n",
            "git_commits": "depth_git_commits",
            "agent_templates": "depth_agent_templates",
            "tech_stack_sections": "depth_tech_stack_sections",
            "architecture_depth": "depth_architecture",
            "execution_mode": "execution_mode",
        }

        for key, value in config.items():
            col_name = column_map.get(key)
            if col_name:
                setattr(user, col_name, value)

        await session.commit()
        await session.refresh(user)

        self._logger.info(f"Updated depth config for user {user.username}")

        depth_config = {
            "vision_documents": user.depth_vision_documents,
            "memory_last_n_projects": user.depth_memory_last_n,
            "git_commits": user.depth_git_commits,
            "agent_templates": user.depth_agent_templates,
            "tech_stack_sections": user.depth_tech_stack_sections,
            "architecture_depth": user.depth_architecture,
            "execution_mode": user.execution_mode,
        }
        await self._emit_websocket_event(
            event_type="depth_config_updated", data={"user_id": user_id, "depth_config": depth_config}
        )

    # ------------------------------------------------------------------
    # Execution mode (stored as column on users table)
    # ------------------------------------------------------------------

    async def get_execution_mode(self, user_id: str) -> str:
        """Get user's execution mode from column on users table."""
        try:
            async with self._get_session() as session:
                return await self._get_execution_mode_impl(session, user_id)
        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            logger.exception("Failed to get execution mode for user %s", user_id)
            raise BaseGiljoError(message=str(e), context={"operation": "get_execution_mode", "user_id": user_id}) from e

    async def _get_execution_mode_impl(self, session: AsyncSession, user_id: str) -> str:
        """Read execution_mode column from users table."""
        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})
        return user.execution_mode or "claude_code"

    async def update_execution_mode(self, user_id: str, execution_mode: str) -> None:
        """Update user's execution_mode column."""
        try:
            async with self._get_session() as session:
                return await self._update_execution_mode_impl(session, user_id, execution_mode)
        except (ResourceNotFoundError, ValidationError, AuthenticationError, AuthorizationError, BaseGiljoError):
            raise
        except (RuntimeError, ValueError) as e:
            logger.exception("Failed to update execution mode for user %s", user_id)
            raise BaseGiljoError(
                message=str(e), context={"operation": "update_execution_mode", "user_id": user_id}
            ) from e

    async def _update_execution_mode_impl(self, session: AsyncSession, user_id: str, execution_mode: str) -> None:
        """Set execution_mode column on users table."""
        valid_modes = {"claude_code", "multi_terminal"}
        if execution_mode not in valid_modes:
            raise ValidationError(
                message="Invalid execution_mode. Must be claude_code or multi_terminal",
                context={"execution_mode": execution_mode, "valid_modes": list(valid_modes)},
            )

        stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        user.execution_mode = execution_mode
        await session.commit()
        await session.refresh(user)

        await self._emit_websocket_event(
            event_type="execution_mode_updated",
            data={"user_id": user_id, "execution_mode": execution_mode},
        )

        self._logger.info(
            "Updated execution mode",
            extra={"user_id": user_id, "execution_mode": execution_mode},
        )

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _emit_websocket_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Emit WebSocket event to tenant clients (Handover 0139a).

        This helper method provides graceful degradation - events are emitted
        if WebSocket manager is available, but operations don't fail if it's not.

        Args:
            event_type: Event type (e.g., "toggle_config_updated")
            data: Event payload data

        Side Effects:
            - Broadcasts event to all tenant clients via WebSocket
            - Logs warning if WebSocket fails (doesn't crash operation)
        """
        if not self._websocket_manager:
            # No WebSocket manager - gracefully skip event emission
            self._logger.debug(f"No WebSocket manager available for event: {event_type}")
            return

        try:
            # Add timestamp to event data
            event_data_with_timestamp = {
                **data,
                "tenant_key": self.tenant_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Broadcast to tenant clients
            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=self.tenant_key, event_type=event_type, data=event_data_with_timestamp
            )

            self._logger.debug(f"WebSocket event emitted: {event_type} for tenant {self.tenant_key}")

        except (RuntimeError, ValueError) as e:
            # Log error but don't fail the operation
            self._logger.warning(f"Failed to emit WebSocket event {event_type}: {e}", exc_info=True)
