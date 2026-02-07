"""
AuthService - Authentication and authorization service layer.

Handover 0322 Phase 2: Service Layer Compliance
Handover 0480b: Exception-based error handling (migrated from dict returns)
Implements production-grade authentication operations following TDD discipline.

Responsibilities:
- User authentication (login validation, JWT token generation)
- Last login timestamp management
- Setup state checking
- API key management (list, create, revoke)
- User registration (admin + first admin flows)

Design Principles:
- NO tenant_key in constructor (auth operates across tenants for login)
- Dependency Injection: Accepts DatabaseManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Raises typed exceptions (AuthenticationError, ValidationError, etc.)
- Testability: Can be unit tested independently
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from passlib.hash import bcrypt
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    AuthenticationError,
    AuthorizationError,
    BaseGiljoException,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.auth import APIKey, User
from src.giljo_mcp.models.config import SetupState
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class AuthService:
    """
    Service for managing authentication and authorization operations.

    This service handles all auth-related operations including:
    - User authentication (login with username/password)
    - JWT token generation for authenticated sessions
    - Last login timestamp updates
    - Setup state checking (first admin created, etc.)
    - API key management (list, create, revoke)
    - User registration (admin creates users, first admin creation)

    Thread Safety: Each instance is request-scoped. Do not share across requests.
    NO tenant_key: Auth operations span tenants (login can be any tenant).
    """

    def __init__(self, db_manager: DatabaseManager, websocket_manager=None, session: AsyncSession | None = None):
        """
        Initialize AuthService with database manager.

        Args:
            db_manager: Database manager for async database operations
            websocket_manager: Optional WebSocket manager for event emission
            session: Optional AsyncSession for test transaction isolation (Handover 0324)
        """
        self.db_manager = db_manager
        self._websocket_manager = websocket_manager
        self._session = session  # Store for test transaction isolation
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # Authentication Methods
    # ============================================================================

    async def authenticate_user(self, username: str, password: str) -> Dict[str, Any]:
        """
        Authenticate user and return user dict + JWT token.

        Args:
            username: Username to authenticate
            password: Plaintext password to verify

        Returns:
            Dict with user data and JWT token
            {
                "user": {...},  # User dict
                "token": "eyJ..."  # JWT access token
            }

        Raises:
            AuthenticationError: If credentials are invalid
            AuthorizationError: If user account is inactive
            BaseGiljoException: For other errors

        Example:
            >>> result = await service.authenticate_user("admin", "Password123!")
            >>> token = result["token"]
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._authenticate_user_impl(self._session, username, password)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._authenticate_user_impl(session, username, password)

        except (AuthenticationError, AuthorizationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception(f"Failed to authenticate user: {e}")
            raise BaseGiljoException(message=f"Authentication failed: {e!s}", context={"username": username}) from e

    async def _authenticate_user_impl(self, session: AsyncSession, username: str, password: str) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        # Find user by username
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        # Verify user exists and password matches
        if not user or not bcrypt.verify(password, user.password_hash):
            self._logger.warning(
                f"Authentication failed for username: {username}",
                extra={"username": username, "reason": "invalid_credentials"},
            )
            raise AuthenticationError(message="Invalid credentials", context={"username": username})

        # Check if user account is active
        if not user.is_active:
            self._logger.warning(
                f"Authentication failed for username: {username} (inactive account)",
                extra={"username": username, "user_id": user.id, "reason": "inactive_account"},
            )
            raise AuthorizationError(
                message="User account is inactive", context={"username": username, "user_id": user.id}
            )

        # Generate JWT token
        token = JWTManager.create_access_token(
            user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
        )

        self._logger.info(
            f"User authenticated successfully: {username}",
            extra={"username": username, "user_id": user.id, "role": user.role},
        )

        # Convert user to dict for response
        user_dict = {
            "id": str(user.id),
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "tenant_key": user.tenant_key,
            "is_active": user.is_active,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_login": user.last_login.isoformat() if user.last_login else None,
        }

        return {"user": user_dict, "token": token}

    async def update_last_login(self, user_id: str, timestamp: datetime) -> None:
        """
        Update user's last login timestamp.

        Args:
            user_id: User UUID
            timestamp: Login timestamp (UTC)

        Raises:
            ResourceNotFoundError: If user not found
            BaseGiljoException: For other errors

        Example:
            >>> await service.update_last_login(user_id, datetime.now(timezone.utc))
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                await self._update_last_login_impl(self._session, user_id, timestamp)
            else:
                # Otherwise create new session (production mode)
                async with self.db_manager.get_session_async() as session:
                    await self._update_last_login_impl(session, user_id, timestamp)

        except ResourceNotFoundError:
            raise
        except Exception as e:
            self._logger.exception(f"Failed to update last login: {e}")
            raise BaseGiljoException(message=f"Failed to update last login: {e!s}", context={"user_id": user_id}) from e

    async def _update_last_login_impl(self, session: AsyncSession, user_id: str, timestamp: datetime) -> None:
        """Implementation that uses provided session"""
        stmt = select(User).where(User.id == user_id)
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()

        if not user:
            raise ResourceNotFoundError(message="User not found", context={"user_id": user_id})

        user.last_login = timestamp
        await session.commit()

        self._logger.debug(
            f"Updated last login for user {user_id}", extra={"user_id": user_id, "timestamp": timestamp.isoformat()}
        )

    # ============================================================================
    # Setup State Methods
    # ============================================================================

    async def check_setup_state(self, tenant_key: str) -> Optional[Dict[str, Any]]:
        """
        Check setup state for tenant.

        Args:
            tenant_key: Tenant key

        Returns:
            Setup state data or None if not found
            {
                "first_admin_created": bool,
                "database_initialized": bool,
                ...
            }

        Raises:
            BaseGiljoException: For errors

        Example:
            >>> state = await service.check_setup_state("test_tenant")
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._check_setup_state_impl(self._session, tenant_key)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._check_setup_state_impl(session, tenant_key)

        except Exception as e:
            self._logger.exception(f"Failed to check setup state: {e}")
            raise BaseGiljoException(message=f"Failed to check setup state: {e!s}", context={"tenant_key": tenant_key}) from e

    async def _check_setup_state_impl(self, session: AsyncSession, tenant_key: str) -> Optional[Dict[str, Any]]:
        """Implementation that uses provided session"""
        stmt = select(SetupState).where(SetupState.tenant_key == tenant_key)
        result = await session.execute(stmt)
        setup_state = result.scalar_one_or_none()

        if not setup_state:
            return None

        return {
            "first_admin_created": setup_state.first_admin_created,
            "database_initialized": setup_state.database_initialized,
            "tenant_key": setup_state.tenant_key,
        }

    # ============================================================================
    # API Key Methods
    # ============================================================================

    async def list_api_keys(self, user_id: str, include_revoked: bool = False) -> List[Dict[str, Any]]:
        """
        List API keys for user.

        Args:
            user_id: User UUID
            include_revoked: Include revoked keys in results (default: False)

        Returns:
            List of API keys
            [
                {"id": "...", "name": "...", "is_active": True, ...},
                ...
            ]

        Raises:
            BaseGiljoException: For errors

        Example:
            >>> keys = await service.list_api_keys(user_id, include_revoked=True)
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._list_api_keys_impl(self._session, user_id, include_revoked)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._list_api_keys_impl(session, user_id, include_revoked)

        except Exception as e:
            self._logger.exception(f"Failed to list API keys: {e}")
            raise BaseGiljoException(message=f"Failed to list API keys: {e!s}", context={"user_id": user_id}) from e

    async def _list_api_keys_impl(
        self, session: AsyncSession, user_id: str, include_revoked: bool
    ) -> List[Dict[str, Any]]:
        """Implementation that uses provided session"""
        if include_revoked:
            stmt = select(APIKey).where(APIKey.user_id == user_id).order_by(APIKey.created_at.desc())
        else:
            stmt = (
                select(APIKey)
                .where(APIKey.user_id == user_id, APIKey.is_active == True)
                .order_by(APIKey.created_at.desc())
            )

        result = await session.execute(stmt)
        api_keys = result.scalars().all()

        keys_list = [
            {
                "id": str(key.id),
                "name": key.name,
                "key_prefix": key.key_prefix,
                "permissions": key.permissions or [],
                "is_active": key.is_active,
                "created_at": key.created_at.isoformat() if key.created_at else None,
                "last_used": key.last_used.isoformat() if key.last_used else None,
                "revoked_at": key.revoked_at.isoformat() if key.revoked_at else None,
            }
            for key in api_keys
        ]

        return keys_list

    async def create_api_key(self, user_id: str, tenant_key: str, name: str, permissions: List[str]) -> Dict[str, Any]:
        """
        Create new API key for user.

        Args:
            user_id: User UUID
            tenant_key: Tenant key
            name: API key name/description
            permissions: List of permissions (e.g., ["*"] for all)

        Returns:
            API key data (includes raw key ONCE)
            {
                "id": "...",
                "name": "...",
                "api_key": "gk_...",  # RAW KEY - only shown once!
                "key_prefix": "gk_abc...",
                "key_hash": "$2b$..."  # Hashed version for storage
            }

        Raises:
            BaseGiljoException: For errors

        Example:
            >>> result = await service.create_api_key(user_id, tenant_key, "My Key", ["*"])
            >>> print("Store this key:", result["api_key"])
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._create_api_key_impl(self._session, user_id, tenant_key, name, permissions)

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._create_api_key_impl(session, user_id, tenant_key, name, permissions)

        except Exception as e:
            self._logger.exception(f"Failed to create API key: {e}")
            raise BaseGiljoException(
                message=f"Failed to create API key: {e!s}", context={"user_id": user_id, "name": name}
            ) from e

    async def _create_api_key_impl(
        self, session: AsyncSession, user_id: str, tenant_key: str, name: str, permissions: List[str]
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        # Generate new API key
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        key_prefix = get_key_prefix(api_key, length=12)

        # Create API key record
        new_key = APIKey(
            id=str(uuid4()),
            user_id=user_id,
            tenant_key=tenant_key,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=permissions,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        session.add(new_key)
        await session.commit()
        await session.refresh(new_key)

        self._logger.info(
            f"API key created: {name} (user: {user_id})",
            extra={"user_id": user_id, "key_name": name, "key_prefix": key_prefix},
        )

        return {
            "id": str(new_key.id),
            "name": new_key.name,
            "api_key": api_key,  # RAW KEY - only shown once!
            "key_prefix": key_prefix,
            "key_hash": key_hash,
            "permissions": new_key.permissions,
        }

    async def revoke_api_key(self, key_id: str, user_id: str) -> None:
        """
        Revoke (deactivate) an API key.

        Args:
            key_id: API key UUID
            user_id: User UUID (for ownership verification)

        Raises:
            ResourceNotFoundError: If API key not found or access denied
            BaseGiljoException: For other errors

        Example:
            >>> await service.revoke_api_key(key_id, user_id)
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                await self._revoke_api_key_impl(self._session, key_id, user_id)
            else:
                # Otherwise create new session (production mode)
                async with self.db_manager.get_session_async() as session:
                    await self._revoke_api_key_impl(session, key_id, user_id)

        except ResourceNotFoundError:
            raise
        except Exception as e:
            self._logger.exception(f"Failed to revoke API key: {e}")
            raise BaseGiljoException(
                message=f"Failed to revoke API key: {e!s}", context={"key_id": key_id, "user_id": user_id}
            ) from e

    async def _revoke_api_key_impl(self, session: AsyncSession, key_id: str, user_id: str) -> None:
        """Implementation that uses provided session"""
        stmt = select(APIKey).where(APIKey.id == key_id, APIKey.user_id == user_id)
        result = await session.execute(stmt)
        api_key = result.scalar_one_or_none()

        if not api_key:
            raise ResourceNotFoundError(
                message="API key not found or access denied", context={"key_id": key_id, "user_id": user_id}
            )

        # Revoke key
        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        await session.commit()

        self._logger.info(
            f"API key revoked: {api_key.name} (user: {user_id})",
            extra={"user_id": user_id, "key_id": key_id, "key_name": api_key.name},
        )

    # ============================================================================
    # User Registration Methods
    # ============================================================================

    async def register_user(
        self,
        username: str,
        email: Optional[str],
        password: str,
        role: str,
        requesting_admin_id: str,
    ) -> Dict[str, Any]:
        """
        Register new user (admin-only operation).

        Args:
            username: Username for new user
            email: Email address (optional)
            password: Plaintext password (will be hashed)
            role: User role (admin, developer, viewer)
            requesting_admin_id: Admin user ID creating this user

        Returns:
            New user data
            {
                "id": "...",
                "username": "...",
                "email": "...",
                "role": "...",
                "tenant_key": "..."  # Auto-generated per-user tenant
            }

        Raises:
            ValidationError: If username/email already exists
            BaseGiljoException: For other errors

        Example:
            >>> user = await service.register_user(
            ...     "newuser", "new@example.com", "Password123!", "developer", admin_id
            ... )
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._register_user_impl(
                    self._session, username, email, password, role, requesting_admin_id
                )

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._register_user_impl(session, username, email, password, role, requesting_admin_id)

        except ValidationError:
            raise
        except Exception as e:
            self._logger.exception(f"Failed to register user: {e}")
            raise BaseGiljoException(message=f"Failed to register user: {e!s}", context={"username": username}) from e

    async def _register_user_impl(
        self,
        session: AsyncSession,
        username: str,
        email: Optional[str],
        password: str,
        role: str,
        requesting_admin_id: str,
        org_id: Optional[str] = None,
        org_role: str = "member",
    ) -> Dict[str, Any]:
        """Implementation that uses provided session"""
        # Check for duplicate username
        stmt = select(User).where(User.username == username)
        result = await session.execute(stmt)
        if result.scalar_one_or_none():
            raise ValidationError(
                message=f"Username '{username}' already exists", context={"username": username, "field": "username"}
            )

        # Check for duplicate email if provided
        if email:
            stmt = select(User).where(User.email == email)
            result = await session.execute(stmt)
            if result.scalar_one_or_none():
                raise ValidationError(
                    message=f"Email '{email}' already exists", context={"email": email, "field": "email"}
                )

        # Hash password
        password_hash = bcrypt.hash(password)

        # Generate per-user tenant key
        tenant_key = TenantManager.generate_tenant_key(username)

        # Create user with optional org_id (Handover 0424g)
        new_user = User(
            id=str(uuid4()),
            username=username,
            email=email,
            password_hash=password_hash,
            role=role,
            tenant_key=tenant_key,
            org_id=org_id,  # Set org_id if provided (Handover 0424g)
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        session.add(new_user)
        await session.flush()  # Get user.id for membership

        # Create organization membership if org_id provided (Handover 0424g)
        if org_id:
            from src.giljo_mcp.models.organizations import OrgMembership

            membership = OrgMembership(
                org_id=org_id, user_id=str(new_user.id), tenant_key=tenant_key, role=org_role, is_active=True
            )
            session.add(membership)
        else:
            # Create default organization for user without org_id (backward compatibility)
            created_org_id = await self._create_default_organization(
                session=session, tenant_key=tenant_key, org_name=f"{username}'s Workspace"
            )
            new_user.org_id = created_org_id
            # Create owner membership for their own org
            from src.giljo_mcp.models.organizations import OrgMembership

            membership = OrgMembership(
                org_id=created_org_id, user_id=str(new_user.id), tenant_key=tenant_key, role="owner", is_active=True
            )
            session.add(membership)

        await session.commit()
        await session.refresh(new_user)

        self._logger.info(
            f"User registered: {username} (role: {role}, org_role: {org_role}, by admin: {requesting_admin_id})",
            extra={"username": username, "role": role, "org_role": org_role, "admin_id": requesting_admin_id},
        )

        return {
            "id": str(new_user.id),
            "username": new_user.username,
            "email": new_user.email,
            "role": new_user.role,
            "tenant_key": new_user.tenant_key,
        }

    async def create_user_in_org(
        self, session: AsyncSession, admin_user_id: str, username: str, email: str, role: str, initial_password: str
    ) -> Dict[str, Any]:
        """
        Create user within admin's organization (Handover 0424g).

        Admin/owner creates new user in their organization. New user inherits
        admin's org_id and receives specified membership role.

        Args:
            session: Database session
            admin_user_id: Admin user ID (must have owner/admin role in org)
            username: Username for new user
            email: Email address
            role: Organization membership role (owner/admin/member/viewer)
            initial_password: Initial password for new user

        Returns:
            New user data with org_id set

        Raises:
            AuthorizationError: If admin doesn't have owner/admin role
            ValidationError: If username/email already exists

        Example:
            >>> user = await service.create_user_in_org(
            ...     session, admin_id, "newuser", "new@example.com", "member", "TempPass123!"
            ... )
        """
        from sqlalchemy.orm import selectinload

        from src.giljo_mcp.models.organizations import OrgMembership

        # Verify admin has owner/admin role in their organization
        admin_stmt = select(User).where(User.id == admin_user_id).options(selectinload(User.organization))
        admin_result = await session.execute(admin_stmt)
        admin = admin_result.scalar_one_or_none()

        if not admin or not admin.org_id:
            raise AuthorizationError(
                message="Admin user not found or not member of any organization",
                context={"admin_user_id": admin_user_id},
            )

        # Check admin's membership role (must be owner or admin)
        membership_stmt = (
            select(OrgMembership)
            .where(OrgMembership.org_id == admin.org_id)
            .where(OrgMembership.user_id == admin_user_id)
        )
        membership_result = await session.execute(membership_stmt)
        membership = membership_result.scalar_one_or_none()

        if not membership or membership.role not in ("owner", "admin"):
            raise AuthorizationError(
                message="Only organization owners and admins can create users",
                context={
                    "admin_user_id": admin_user_id,
                    "org_id": admin.org_id,
                    "current_role": membership.role if membership else None,
                },
            )

        # Create user in admin's organization
        return await self._register_user_impl(
            session=session,
            username=username,
            email=email,
            password=initial_password,
            role="developer",  # User.role (system role, not org role)
            requesting_admin_id=admin_user_id,
            org_id=admin.org_id,  # Inherit admin's org_id
            org_role=role,  # OrgMembership.role (owner/admin/member/viewer)
        )

    async def create_first_admin(
        self,
        username: str,
        email: Optional[str],
        password: str,
        full_name: Optional[str],
        org_name: Optional[str] = "My Organization",
    ) -> Dict[str, Any]:
        """
        Create first administrator account (fresh install only).

        Args:
            username: Admin username
            email: Admin email (optional)
            password: Admin password (must meet complexity requirements)
            full_name: Admin full name (optional)
            org_name: Organization name (default: "My Organization") - Handover 0424h

        Returns:
            User data and JWT token for immediate login
            {
                "id": "...",
                "username": "...",
                "email": "...",
                "role": "admin",
                "tenant_key": "...",
                "is_active": True,
                "token": "eyJ..."  # JWT for immediate login
            }

        Raises:
            ValidationError: If admin already exists or password too weak
            BaseGiljoException: For other errors

        Example:
            >>> admin = await service.create_first_admin(
            ...     "admin", "admin@example.com", "SecureAdmin123!@#", "Administrator",
            ...     org_name="Acme Corporation"
            ... )
        """
        try:
            # Use provided session if available (test mode)
            if self._session:
                return await self._create_first_admin_impl(
                    self._session, username, email, password, full_name, org_name
                )

            # Otherwise create new session (production mode)
            async with self.db_manager.get_session_async() as session:
                return await self._create_first_admin_impl(session, username, email, password, full_name, org_name)

        except ValidationError:
            raise
        except Exception as e:
            self._logger.exception(f"Failed to create first admin: {e}")
            raise BaseGiljoException(message=f"Failed to create first admin: {e!s}", context={"username": username}) from e

    async def _create_first_admin_impl(
        self,
        session: AsyncSession,
        username: str,
        email: Optional[str],
        password: str,
        full_name: Optional[str],
        org_name: Optional[str] = "My Organization",
    ) -> Dict[str, Any]:
        """Implementation that uses provided session (Handover 0424h: accepts org_name)"""
        # Check if users already exist (must be fresh install)
        user_count_stmt = select(func.count(User.id))
        result = await session.execute(user_count_stmt)
        total_users = result.scalar()

        if total_users > 0:
            raise ValidationError(
                message="Administrator account already exists", context={"reason": "users_exist", "count": total_users}
            )

        # Validate password strength (12+ chars, complexity)
        if len(password) < 12:
            raise ValidationError(
                message="Password must be at least 12 characters",
                context={"password_length": len(password), "required": 12},
            )

        has_upper = any(c.isupper() for c in password)
        has_lower = any(c.islower() for c in password)
        has_digit = any(c.isdigit() for c in password)
        has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)

        if not (has_upper and has_lower and has_digit and has_special):
            raise ValidationError(
                message="Password must contain uppercase, lowercase, digit, and special character",
                context={
                    "has_uppercase": has_upper,
                    "has_lowercase": has_lower,
                    "has_digit": has_digit,
                    "has_special": has_special,
                },
            )

        # Hash password
        password_hash = bcrypt.hash(password)

        # Generate secure tenant key
        tenant_key = TenantManager.generate_tenant_key(username)

        # Create organization FIRST (Handover 0424g: org-first pattern)
        # Handover 0424h: Use provided org_name instead of username-based default
        org_id = await self._create_default_organization(
            session=session, tenant_key=tenant_key, org_name=org_name or "My Organization"
        )

        # Create first admin user WITH org_id set
        admin_user = User(
            id=str(uuid4()),
            username=username,
            email=email,
            full_name=full_name or "Administrator",
            password_hash=password_hash,
            role="admin",  # Force admin role
            tenant_key=tenant_key,
            org_id=org_id,  # Direct FK to organization (Handover 0424g)
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )

        session.add(admin_user)
        await session.flush()  # Get user.id for membership

        # Create owner membership (Handover 0424g)
        from src.giljo_mcp.models.organizations import OrgMembership

        owner_membership = OrgMembership(
            org_id=org_id, user_id=str(admin_user.id), tenant_key=tenant_key, role="owner", is_active=True
        )
        session.add(owner_membership)
        await session.commit()
        await session.refresh(admin_user)

        # Mark first admin created in SetupState
        setup_state_stmt = select(SetupState).where(SetupState.tenant_key == tenant_key)
        setup_result = await session.execute(setup_state_stmt)
        setup_state = setup_result.scalar_one_or_none()

        if setup_state:
            setup_state.first_admin_created = True
            setup_state.first_admin_created_at = datetime.now(timezone.utc)
        else:
            setup_state = SetupState(
                id=str(uuid4()),
                tenant_key=tenant_key,
                database_initialized=True,
                database_initialized_at=datetime.now(timezone.utc),
                first_admin_created=True,
                first_admin_created_at=datetime.now(timezone.utc),
            )
            session.add(setup_state)

        await session.commit()

        # Generate JWT token for immediate login
        token = JWTManager.create_access_token(
            user_id=admin_user.id, username=admin_user.username, role=admin_user.role, tenant_key=admin_user.tenant_key
        )

        self._logger.info(
            f"First administrator account created: {username}", extra={"username": username, "tenant_key": tenant_key}
        )

        return {
            "id": str(admin_user.id),
            "username": admin_user.username,
            "email": admin_user.email,
            "full_name": admin_user.full_name,
            "role": admin_user.role,
            "tenant_key": admin_user.tenant_key,
            "is_active": admin_user.is_active,
            "token": token,  # JWT for immediate login
        }

    # ============================================================================
    # Organization Helper Methods (Handover 0424b)
    # ============================================================================

    async def _create_default_organization(
        self, session: AsyncSession, tenant_key: str, org_name: str = "My Workspace"
    ) -> str:
        """
        Create default organization (Handover 0424g: org-first pattern).

        This method creates an organization WITHOUT creating membership.
        Caller is responsible for creating user and membership.

        Args:
            session: Database session
            tenant_key: Tenant isolation key
            org_name: Custom organization name (default: "My Workspace")

        Returns:
            org.id as UUID string

        Note: This method adds org to session without committing.
        Parent methods (_register_user_impl, _create_first_admin_impl) handle commit.
        """
        import re
        from uuid import uuid4

        from src.giljo_mcp.models.organizations import Organization

        # Generate slug from org_name (sanitize and make URL-friendly)
        slug_base = re.sub(r"[^a-z0-9]+", "-", org_name.lower()).strip("-")
        slug = f"{slug_base}-{str(uuid4())[:8]}"  # Add UUID suffix for uniqueness

        # Create organization
        org = Organization(name=org_name, tenant_key=tenant_key, slug=slug, settings={})
        session.add(org)
        await session.flush()  # Get org.id

        # No commit here - parent method handles it
        self._logger.info(
            f"Organization created: {org_name}", extra={"tenant_key": tenant_key, "org_id": org.id, "slug": slug}
        )

        return str(org.id)
