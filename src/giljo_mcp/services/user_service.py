"""
UserService - Dedicated service for user domain logic

Handover 0322 Phase 1: Extract user operations from direct database access
to follow established service layer pattern.

Responsibilities:
- CRUD operations for users
- User authentication and password management
- Role management with admin restrictions
- Field priority and depth configuration
- Username/email uniqueness validation

Design Principles:
- Single Responsibility: Only user domain logic
- Dependency Injection: Accepts DatabaseManager and tenant_key
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from uuid import uuid4

from passlib.hash import bcrypt
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.auth import User


logger = logging.getLogger(__name__)


class UserService:
    """
    Service for managing user lifecycle and operations.

    This service handles all user-related operations including:
    - Creating, reading, updating, deleting users (soft delete)
    - User authentication (password verification, reset)
    - Role management (change role, admin restrictions)
    - Configuration management (field priority, depth config)
    - Uniqueness validation (username, email)

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        websocket_manager=None,
        session: AsyncSession | None = None
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

    # ============================================================================
    # CRUD Operations
    # ============================================================================

    async def list_users(self) -> Dict[str, Any]:
        """
        List all users in tenant.

        Returns:
            Dict with success status and list of users (passwords excluded)

        Example:
            >>> result = await service.list_users()
            >>> for user in result["data"]:
            ...     print(user["username"])
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                sync_session = getattr(self._session, "sync_session", None)
                if (
                    getattr(self._session, "closed", False)
                    or not getattr(self._session, "is_active", True)
                    or (sync_session is not None and (getattr(sync_session, "closed", False) or not getattr(sync_session, "is_active", True)))
                    or getattr(self._session, "_is_ctx_manager_closed", False)
                ):
                    raise RuntimeError("Session is closed")
                return await self._list_users_impl(self._session)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._list_users_impl(session)

        except Exception as e:
            self._logger.exception(f"Failed to list users: {e}")
            return {"success": False, "error": str(e)}

    async def _list_users_impl(self, session: AsyncSession) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = (
            select(User)
            .where(User.tenant_key == self.tenant_key)
            .order_by(User.created_at)
        )
        result = await session.execute(stmt)
        users = result.scalars().all()

        user_list = []
        for user in users:
            user_list.append({
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_key": user.tenant_key,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            })

        self._logger.debug(f"Found {len(user_list)} users for tenant {self.tenant_key}")

        return {
            "success": True,
            "data": user_list
        }

    async def get_user(self, user_id: str) -> Dict[str, Any]:
        """
        Get a specific user by ID.

        Args:
            user_id: User UUID

        Returns:
            Dict with success status and user details (password excluded) or error

        Example:
            >>> result = await service.get_user("abc-123")
            >>> if result["success"]:
            ...     print(result["user"]["username"])
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._get_user_impl(self._session, user_id)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._get_user_impl(session, user_id)

        except Exception as e:
            self._logger.exception(f"Failed to get user: {e}")
            return {"success": False, "error": str(e)}

    async def _get_user_impl(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        self._logger.info("Fetched user", extra={"user_id": user_id})

        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_key": user.tenant_key,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat() if user.created_at else None,
                "last_login": user.last_login.isoformat() if user.last_login else None
            }
        }

    async def create_user(
        self,
        username: str,
        email: Optional[str] = None,
        full_name: Optional[str] = None,
        password: Optional[str] = None,
        role: str = "developer",
        is_active: bool = True
    ) -> Dict[str, Any]:
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
            Dict with success status and user details or error

        Example:
            >>> result = await service.create_user(
            ...     username="newuser",
            ...     email="new@example.com",
            ...     password="SecurePassword123"
            ... )
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._create_user_impl(
                    self._session, username, email, full_name, password, role, is_active
                )

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._create_user_impl(
                    session, username, email, full_name, password, role, is_active
                )

        except Exception as e:
            self._logger.exception(f"Failed to create user: {e}")
            return {"success": False, "error": str(e)}

    async def _create_user_impl(
        self,
        session: AsyncSession,
        username: str,
        email: Optional[str],
        full_name: Optional[str],
        password: Optional[str],
        role: str,
        is_active: bool
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        # Check for duplicate username (global uniqueness)
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            return {
                "success": False,
                "error": f"Username '{username}' already exists"
            }

        # Check for duplicate email if provided
        if email:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                return {
                    "success": False,
                    "error": f"Email '{email}' already exists"
                }

        # Hash password (default to "GiljoMCP" per Handover 0023)
        password_hash = bcrypt.hash(password or "GiljoMCP")

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
            must_change_password=True if not password else False,  # Force change if default password
            must_set_pin=True,  # Force PIN setup on first login
            recovery_pin_hash=None,  # No PIN set initially
            created_at=datetime.now(timezone.utc)
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        self._logger.info(f"Created user {user.id} for tenant {self.tenant_key}")

        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "tenant_key": user.tenant_key,
                "is_active": user.is_active,
                "must_change_password": user.must_change_password,
                "created_at": user.created_at.isoformat() if user.created_at else None
            }
        }

    async def update_user(
        self,
        user_id: str,
        **updates
    ) -> Dict[str, Any]:
        """
        Update a user.

        Args:
            user_id: User UUID
            **updates: Fields to update (email, full_name, is_active)

        Returns:
            Dict with success status and updated user or error

        Example:
            >>> result = await service.update_user(
            ...     "abc-123",
            ...     email="newemail@example.com",
            ...     full_name="Updated Name"
            ... )
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._update_user_impl(self._session, user_id, updates)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._update_user_impl(session, user_id, updates)

        except Exception as e:
            self._logger.exception(f"Failed to update user: {e}")
            return {"success": False, "error": str(e)}

    async def _update_user_impl(
        self, session: AsyncSession, user_id: str, updates: dict
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Check for duplicate email if changing email
        if "email" in updates and updates["email"] and updates["email"] != user.email:
            stmt = select(User).where(User.email == updates["email"])
            result = await session.execute(stmt)
            existing_user = result.scalar_one_or_none()
            if existing_user:
                return {
                    "success": False,
                    "error": f"Email '{updates['email']}' already exists"
                }

        # Apply updates (only allowed fields)
        allowed_fields = {"email", "full_name", "is_active"}
        for field, value in updates.items():
            if field in allowed_fields:
                setattr(user, field, value)

        await session.commit()
        await session.refresh(user)

        self._logger.info(f"Updated user {user_id}")

        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name,
                "role": user.role,
                "is_active": user.is_active
            }
        }

    async def delete_user(self, user_id: str) -> Dict[str, Any]:
        """
        Soft delete a user (set is_active=False).

        Args:
            user_id: User UUID to delete

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.delete_user("abc-123")
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._delete_user_impl(self._session, user_id)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._delete_user_impl(session, user_id)

        except Exception as e:
            self._logger.exception(f"Failed to delete user: {e}")
            return {"success": False, "error": str(e)}

    async def _delete_user_impl(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Soft delete
        user.is_active = False

        await session.commit()

        self._logger.info(f"Soft deleted user {user_id}")

        return {
            "success": True,
            "message": "User deactivated successfully",
            "user_id": str(user.id),
            "username": user.username
        }

    # ============================================================================
    # Role Management
    # ============================================================================

    async def change_role(self, user_id: str, new_role: str) -> Dict[str, Any]:
        """
        Change user role with admin restrictions.

        Args:
            user_id: User UUID
            new_role: New role (admin, developer, viewer)

        Returns:
            Dict with success status and updated role or error

        Example:
            >>> result = await service.change_role("abc-123", "viewer")
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._change_role_impl(self._session, user_id, new_role)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._change_role_impl(session, user_id, new_role)

        except Exception as e:
            self._logger.exception(f"Failed to change role: {e}")
            return {"success": False, "error": str(e)}

    async def _change_role_impl(
        self, session: AsyncSession, user_id: str, new_role: str
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        # Validate role
        valid_roles = ["admin", "developer", "viewer"]
        if new_role not in valid_roles:
            return {
                "success": False,
                "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
            }

        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Check if this is the last admin (prevent lockout)
        if user.role == "admin" and new_role != "admin":
            stmt = select(func.count(User.id)).where(
                and_(
                    User.tenant_key == self.tenant_key,
                    User.role == "admin",
                    User.is_active == True,
                    User.id != user_id
                )
            )
            admin_count_result = await session.execute(stmt)
            admin_count = admin_count_result.scalar() or 0

            if admin_count == 0:
                return {
                    "success": False,
                    "error": "Cannot demote the last admin. At least one admin must remain."
                }

        # Update role
        old_role = user.role
        user.role = new_role
        await session.commit()
        await session.refresh(user)

        self._logger.info(f"Changed role for user {user.username}: {old_role} -> {new_role}")

        return {
            "success": True,
            "user": {
                "id": str(user.id),
                "username": user.username,
                "role": user.role
            }
        }

    # ============================================================================
    # Password Management
    # ============================================================================

    async def change_password(
        self,
        user_id: str,
        old_password: Optional[str],
        new_password: str,
        is_admin: bool = False
    ) -> Dict[str, Any]:
        """
        Change user password with verification.

        Args:
            user_id: User UUID
            old_password: Current password (required for non-admin)
            new_password: New password
            is_admin: Whether request is from admin (bypasses old password check)

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.change_password(
            ...     "abc-123",
            ...     old_password="OldPass123",
            ...     new_password="NewPass456"
            ... )
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._change_password_impl(
                    self._session, user_id, old_password, new_password, is_admin
                )

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._change_password_impl(
                    session, user_id, old_password, new_password, is_admin
                )

        except Exception as e:
            self._logger.exception(f"Failed to change password: {e}")
            return {"success": False, "error": str(e)}

    async def _change_password_impl(
        self,
        session: AsyncSession,
        user_id: str,
        old_password: Optional[str],
        new_password: str,
        is_admin: bool
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # If not admin, verify old password
        if not is_admin:
            if not old_password:
                return {
                    "success": False,
                    "error": "Current password is required"
                }

            if not bcrypt.verify(old_password, user.password_hash):
                return {
                    "success": False,
                    "error": "Current password is incorrect"
                }

        # Hash and update password
        user.password_hash = bcrypt.hash(new_password)
        user.must_change_password = False  # Clear flag after successful change

        await session.commit()

        self._logger.info(f"Password changed for user: {user.username}")

        return {
            "success": True,
            "message": "Password updated successfully"
        }

    async def reset_password(self, user_id: str) -> Dict[str, Any]:
        """
        Reset user password to default 'GiljoMCP'.

        Args:
            user_id: User UUID

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.reset_password("abc-123")
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._reset_password_impl(self._session, user_id)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._reset_password_impl(session, user_id)

        except Exception as e:
            self._logger.exception(f"Failed to reset password: {e}")
            return {"success": False, "error": str(e)}

    async def _reset_password_impl(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Reset password to default 'GiljoMCP'
        user.password_hash = bcrypt.hash("GiljoMCP")

        # Set must_change_password flag
        user.must_change_password = True

        # Clear PIN lockout
        user.failed_pin_attempts = 0
        user.pin_lockout_until = None

        await session.commit()

        self._logger.info(f"Reset password for user: {user.username}")

        return {
            "success": True,
            "message": "Password reset successful"
        }

    # ============================================================================
    # Validation Methods
    # ============================================================================

    async def check_username_exists(self, username: str) -> Dict[str, Any]:
        """
        Check if username already exists.

        Args:
            username: Username to check

        Returns:
            Dict with success status and exists boolean

        Example:
            >>> result = await service.check_username_exists("testuser")
            >>> if result["exists"]:
            ...     print("Username taken")
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._check_username_exists_impl(self._session, username)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._check_username_exists_impl(session, username)

        except Exception as e:
            self._logger.exception(f"Failed to check username: {e}")
            return {"success": False, "error": str(e)}

    async def _check_username_exists_impl(self, session: AsyncSession, username: str) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        return {
            "success": True,
            "exists": user is not None
        }

    async def check_email_exists(self, email: str) -> Dict[str, Any]:
        """
        Check if email already exists.

        Args:
            email: Email to check

        Returns:
            Dict with success status and exists boolean

        Example:
            >>> result = await service.check_email_exists("test@example.com")
            >>> if result["exists"]:
            ...     print("Email taken")
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._check_email_exists_impl(self._session, email)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._check_email_exists_impl(session, email)

        except Exception as e:
            self._logger.exception(f"Failed to check email: {e}")
            return {"success": False, "error": str(e)}

    async def _check_email_exists_impl(self, session: AsyncSession, email: str) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(User.email == email)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        return {
            "success": True,
            "exists": user is not None
        }

    async def verify_password(self, user_id: str, password: str) -> Dict[str, Any]:
        """
        Verify user password using bcrypt.

        Args:
            user_id: User UUID
            password: Password to verify

        Returns:
            Dict with success status and verified boolean

        Example:
            >>> result = await service.verify_password("abc-123", "TestPass")
            >>> if result["verified"]:
            ...     print("Password correct")
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._verify_password_impl(self._session, user_id, password)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._verify_password_impl(session, user_id, password)

        except Exception as e:
            self._logger.exception(f"Failed to verify password: {e}")
            return {"success": False, "error": str(e)}

    async def _verify_password_impl(
        self, session: AsyncSession, user_id: str, password: str
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        verified = bcrypt.verify(password, user.password_hash)

        return {
            "success": True,
            "verified": verified
        }

    # ============================================================================
    # Configuration Management
    # ============================================================================

    async def get_field_priority_config(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's field priority configuration or defaults.

        Args:
            user_id: User UUID

        Returns:
            Dict with success status and config

        Example:
            >>> result = await service.get_field_priority_config("abc-123")
            >>> print(result["config"])
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._get_field_priority_config_impl(self._session, user_id)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._get_field_priority_config_impl(session, user_id)

        except Exception as e:
            self._logger.exception(f"Failed to get field priority config: {e}")
            return {"success": False, "error": str(e)}

    async def _get_field_priority_config_impl(
        self, session: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Return custom config if set, otherwise defaults
        if user.field_priority_config:
            return {
                "success": True,
                "config": user.field_priority_config
            }

        # Return system defaults (v2.0)
        from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

        return {
            "success": True,
            "config": DEFAULT_FIELD_PRIORITY
        }

    async def update_field_priority_config(
        self,
        user_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user's field priority configuration.

        Args:
            user_id: User UUID
            config: New field priority configuration

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.update_field_priority_config(
            ...     "abc-123",
            ...     {"version": "2.0", "priorities": {"product_core": 1}}
            ... )
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._update_field_priority_config_impl(self._session, user_id, config)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._update_field_priority_config_impl(session, user_id, config)

        except Exception as e:
            self._logger.exception(f"Failed to update field priority config: {e}")
            return {"success": False, "error": str(e)}

    async def _update_field_priority_config_impl(
        self, session: AsyncSession, user_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        # Validate config structure
        if "version" not in config or "priorities" not in config:
            return {
                "success": False,
                "error": "Invalid config structure. Must contain 'version' and 'priorities'"
            }

        # Validate priorities (1-4 range)
        for category, priority in config["priorities"].items():
            if not isinstance(priority, int) or priority < 1 or priority > 4:
                return {
                    "success": False,
                    "error": f"Invalid priority {priority} for category '{category}'. Must be 1-4"
                }

        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Update config
        user.field_priority_config = config
        await session.commit()

        self._logger.info(f"Updated field priority config for user {user.username}")

        # Emit WebSocket event if manager available
        await self._emit_websocket_event(
            event_type="priority_config_updated",
            data={
                "user_id": user_id,
                "priorities": config["priorities"],
                "version": config["version"]
            }
        )

        return {
            "success": True,
            "message": "Field priority config updated successfully"
        }

    async def reset_field_priority_config(self, user_id: str) -> Dict[str, Any]:
        """
        Reset field priority configuration to system defaults.

        Args:
            user_id: User UUID

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.reset_field_priority_config("abc-123")
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._reset_field_priority_config_impl(self._session, user_id)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._reset_field_priority_config_impl(session, user_id)

        except Exception as e:
            self._logger.exception(f"Failed to reset field priority config: {e}")
            return {"success": False, "error": str(e)}

    async def _reset_field_priority_config_impl(
        self, session: AsyncSession, user_id: str
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Clear custom config
        user.field_priority_config = None
        await session.commit()

        self._logger.info(f"Reset field priority config for user {user.username}")

        return {
            "success": True,
            "message": "Field priority config reset to defaults"
        }

    async def get_depth_config(self, user_id: str) -> Dict[str, Any]:
        """
        Get user's depth configuration or defaults.

        Args:
            user_id: User UUID

        Returns:
            Dict with success status and config

        Example:
            >>> result = await service.get_depth_config("abc-123")
            >>> print(result["config"])
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._get_depth_config_impl(self._session, user_id)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._get_depth_config_impl(session, user_id)

        except Exception as e:
            self._logger.exception(f"Failed to get depth config: {e}")
            return {"success": False, "error": str(e)}

    async def _get_depth_config_impl(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Return depth config (from user or defaults)
        depth_config = user.depth_config or {
            "vision_documents": "medium",
            "memory_last_n_projects": 3,
            "git_commits": 25,
            "agent_templates": "type_only",
            "tech_stack_sections": "all",
            "architecture_depth": "overview"
        }

        return {
            "success": True,
            "config": depth_config
        }

    async def update_depth_config(
        self,
        user_id: str,
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update user's depth configuration.

        Args:
            user_id: User UUID
            config: New depth configuration

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.update_depth_config(
            ...     "abc-123",
            ...     {"vision_documents": "heavy", "git_commits": 50}
            ... )
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._update_depth_config_impl(self._session, user_id, config)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._update_depth_config_impl(session, user_id, config)

        except Exception as e:
            self._logger.exception(f"Failed to update depth config: {e}")
            return {"success": False, "error": str(e)}

    async def _update_depth_config_impl(
        self, session: AsyncSession, user_id: str, config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        # Validate config values
        valid_vision = ["none", "optional", "light", "medium", "full"]
        valid_memory = [1, 3, 5, 10]
        valid_git = [5, 10, 25, 50, 100]
        valid_agent_templates = ["type_only", "full"]

        if "vision_documents" in config and config["vision_documents"] not in valid_vision:
            return {
                "success": False,
                "error": f"Invalid vision_documents. Must be one of: {', '.join(valid_vision)}"
            }

        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {
                "success": False,
                "error": "User not found"
            }

        # Update config
        user.depth_config = config
        await session.commit()

        self._logger.info(f"Updated depth config for user {user.username}")

        # Emit WebSocket event if manager available
        await self._emit_websocket_event(
            event_type="depth_config_updated",
            data={
                "user_id": user_id,
                "depth_config": config
            }
        )

        return {
            "success": True,
            "message": "Depth config updated successfully"
        }

    # ------------------------------------------------------------------
    # Execution mode (stored in depth_config.execution_mode)
    # ------------------------------------------------------------------

    async def get_execution_mode(self, user_id: str) -> Dict[str, Any]:
        """Get user's execution mode or default."""
        try:
            if self._session:
                return await self._get_execution_mode_impl(self._session, user_id)

            async with self.db_manager.get_session_async() as session:
                return await self._get_execution_mode_impl(session, user_id)
        except Exception as e:
            logger.error(f"Failed to get execution mode for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _get_execution_mode_impl(self, session: AsyncSession, user_id: str) -> Dict[str, Any]:
        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {"success": False, "error": "User not found"}

        depth_config = user.depth_config or {}
        mode = depth_config.get("execution_mode", "claude_code")

        return {"success": True, "execution_mode": mode}

    async def update_execution_mode(self, user_id: str, execution_mode: str) -> Dict[str, Any]:
        """Update user's execution mode with validation."""
        try:
            if self._session:
                return await self._update_execution_mode_impl(self._session, user_id, execution_mode)

            async with self.db_manager.get_session_async() as session:
                return await self._update_execution_mode_impl(session, user_id, execution_mode)
        except Exception as e:
            logger.error(f"Failed to update execution mode for user {user_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _update_execution_mode_impl(
        self, session: AsyncSession, user_id: str, execution_mode: str
    ) -> Dict[str, Any]:
        valid_modes = {"claude_code", "multi_terminal"}
        if execution_mode not in valid_modes:
            return {"success": False, "error": "Invalid execution_mode. Must be claude_code or multi_terminal"}

        stmt = select(User).where(
            and_(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            return {"success": False, "error": "User not found"}

        depth_config = user.depth_config or {
            "vision_documents": "medium",
            "memory_last_n_projects": 3,
            "git_commits": 25,
            "agent_templates": "type_only",
            "tech_stack_sections": "all",
            "architecture_depth": "overview",
        }
        depth_config = dict(depth_config)
        depth_config["execution_mode"] = execution_mode

        # Reuse depth config update path for consistency
        user.depth_config = depth_config
        await session.commit()
        await session.refresh(user)

        await self._emit_websocket_event(
            event_type="execution_mode_updated",
            data={
                "user_id": user_id,
                "execution_mode": execution_mode,
            },
        )

        self._logger.info(
            "Updated execution mode",
            extra={"user_id": user_id, "execution_mode": execution_mode},
        )

        return {"success": True, "execution_mode": execution_mode}

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _emit_websocket_event(
        self,
        event_type: str,
        data: Dict[str, Any]
    ) -> None:
        """
        Emit WebSocket event to tenant clients (Handover 0139a).

        This helper method provides graceful degradation - events are emitted
        if WebSocket manager is available, but operations don't fail if it's not.

        Args:
            event_type: Event type (e.g., "priority_config_updated")
            data: Event payload data

        Side Effects:
            - Broadcasts event to all tenant clients via WebSocket
            - Logs warning if WebSocket fails (doesn't crash operation)
        """
        if not self._websocket_manager:
            # No WebSocket manager - gracefully skip event emission
            self._logger.debug(
                f"No WebSocket manager available for event: {event_type}"
            )
            return

        try:
            # Add timestamp to event data
            event_data_with_timestamp = {
                **data,
                "tenant_key": self.tenant_key,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

            # Broadcast to tenant clients
            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=self.tenant_key,
                event_type=event_type,
                data=event_data_with_timestamp
            )

            self._logger.debug(
                f"WebSocket event emitted: {event_type} for tenant {self.tenant_key}"
            )

        except Exception as e:
            # Log error but don't fail the operation
            self._logger.warning(
                f"Failed to emit WebSocket event {event_type}: {e}",
                exc_info=True
            )
