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

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.auth import User


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

    def __init__(self, db_manager: DatabaseManager, tenant_key: str, websocket_manager=None):
        """
        Initialize UserService with database and tenant isolation.

        Args:
            db_manager: Database manager for async database operations
            tenant_key: Tenant key for multi-tenant isolation
            websocket_manager: Optional WebSocket manager for event emission (Handover 0139a)
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._websocket_manager = websocket_manager
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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to list users: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to get user: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to create user: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to update user: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to delete user: {e}")
            return {"success": False, "error": str(e)}

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
            # Validate role
            valid_roles = ["admin", "developer", "viewer"]
            if new_role not in valid_roles:
                return {
                    "success": False,
                    "error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"
                }

            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to change role: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to change password: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to reset password: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
                stmt = select(User).where(User.username == username)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                return {
                    "success": True,
                    "exists": user is not None
                }

        except Exception as e:
            self._logger.exception(f"Failed to check username: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
                stmt = select(User).where(User.email == email)
                result = await session.execute(stmt)
                user = result.scalar_one_or_none()

                return {
                    "success": True,
                    "exists": user is not None
                }

        except Exception as e:
            self._logger.exception(f"Failed to check email: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to verify password: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to get field priority config: {e}")
            return {"success": False, "error": str(e)}

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

            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to update field priority config: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to reset field priority config: {e}")
            return {"success": False, "error": str(e)}

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
            async with self.db_manager.get_session_async() as session:
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
                    "vision_chunking": "moderate",
                    "memory_last_n_projects": 3,
                    "git_commits": 25,
                    "agent_template_detail": "standard",
                    "tech_stack_sections": "all",
                    "architecture_depth": "overview"
                }

                return {
                    "success": True,
                    "config": depth_config
                }

        except Exception as e:
            self._logger.exception(f"Failed to get depth config: {e}")
            return {"success": False, "error": str(e)}

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
            ...     {"vision_chunking": "heavy", "git_commits": 50}
            ... )
        """
        try:
            # Validate config values
            valid_vision = ["none", "light", "moderate", "heavy"]
            valid_memory = [1, 3, 5, 10]
            valid_git = [10, 25, 50, 100]

            if "vision_chunking" in config and config["vision_chunking"] not in valid_vision:
                return {
                    "success": False,
                    "error": f"Invalid vision_chunking. Must be one of: {', '.join(valid_vision)}"
                }

            async with self.db_manager.get_session_async() as session:
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

        except Exception as e:
            self._logger.exception(f"Failed to update depth config: {e}")
            return {"success": False, "error": str(e)}

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
