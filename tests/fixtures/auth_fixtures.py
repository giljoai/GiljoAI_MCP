"""
Shared test fixtures for authentication and user management testing.

These fixtures provide reusable components for testing:
- User creation (admin, developer, viewer roles)
- API key generation
- JWT token creation
- Multi-tenant test data
- Authentication headers
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional
from uuid import uuid4

import pytest
import pytest_asyncio
from passlib.hash import bcrypt
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.models import APIKey, User
from src.giljo_mcp.models.organizations import Organization


class OrganizationFactory:
    """Factory for creating test organizations (0424j: User.org_id NOT NULL)."""

    # Cache to reuse orgs within a test session
    _org_cache: Dict[str, str] = {}

    @staticmethod
    async def get_or_create_org(
        session: AsyncSession,
        tenant_key: str,
    ) -> str:
        """Get or create organization for tenant, return org_id."""
        # Check cache first
        if tenant_key in OrganizationFactory._org_cache:
            return OrganizationFactory._org_cache[tenant_key]

        # Create new org
        org_id = str(uuid4())
        org = Organization(
            id=org_id,
            tenant_key=tenant_key,
            name=f"Test Org {tenant_key}",
            slug=f"test-org-{tenant_key.replace('_', '-')}",
            is_active=True,
        )
        session.add(org)
        await session.flush()  # Don't commit - let test transaction handle it

        OrganizationFactory._org_cache[tenant_key] = org_id
        return org_id

    @staticmethod
    def clear_cache():
        """Clear org cache between test sessions."""
        OrganizationFactory._org_cache.clear()


class UserFactory:
    """Factory for creating test users."""

    @staticmethod
    async def create_user(
        session: AsyncSession,
        username: str,
        password: str = "TestPassword123!",
        email: Optional[str] = None,
        role: str = "developer",
        tenant_key: str = "test_tenant",
        is_active: bool = True,
        **kwargs,
    ) -> User:
        """
        Create a test user.

        Args:
            session: Database session
            username: Username
            password: Plain text password (will be hashed)
            email: Email address
            role: User role (admin, developer, viewer)
            tenant_key: Tenant key for multi-tenant isolation
            is_active: Whether user is active
            **kwargs: Additional user fields (including org_id)

        Returns:
            Created user instance
        """
        # Get or create organization for this tenant (0424j: User.org_id NOT NULL)
        org_id = kwargs.pop("org_id", None)
        if not org_id:
            org_id = await OrganizationFactory.get_or_create_org(session, tenant_key)

        user = User(
            id=kwargs.get("id", str(uuid4())),
            username=username,
            email=email or f"{username}@example.com",
            password_hash=bcrypt.hash(password),
            role=role,
            tenant_key=tenant_key,
            org_id=org_id,  # 0424j: User.org_id NOT NULL
            is_active=is_active,
            created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
            full_name=kwargs.get("full_name"),
            last_login=kwargs.get("last_login"),
        )

        session.add(user)
        await session.commit()
        await session.refresh(user)

        return user

    @staticmethod
    async def create_admin(
        session: AsyncSession, username: str = "admin", tenant_key: str = "test_tenant", **kwargs
    ) -> User:
        """Create admin user."""
        return await UserFactory.create_user(session, username=username, role="admin", tenant_key=tenant_key, **kwargs)

    @staticmethod
    async def create_developer(
        session: AsyncSession, username: str = "developer", tenant_key: str = "test_tenant", **kwargs
    ) -> User:
        """Create developer user."""
        return await UserFactory.create_user(
            session, username=username, role="developer", tenant_key=tenant_key, **kwargs
        )

    @staticmethod
    async def create_viewer(
        session: AsyncSession, username: str = "viewer", tenant_key: str = "test_tenant", **kwargs
    ) -> User:
        """Create viewer user."""
        return await UserFactory.create_user(session, username=username, role="viewer", tenant_key=tenant_key, **kwargs)


class APIKeyFactory:
    """Factory for creating test API keys."""

    @staticmethod
    async def create_api_key(
        session: AsyncSession,
        user_id: str,
        tenant_key: str,
        name: str = "Test API Key",
        permissions: Optional[List[str]] = None,
        is_active: bool = True,
        **kwargs,
    ) -> tuple[APIKey, str]:
        """
        Create a test API key.

        Args:
            session: Database session
            user_id: Owner user ID
            tenant_key: Tenant key
            name: API key name/description
            permissions: List of permissions
            is_active: Whether key is active
            **kwargs: Additional key fields

        Returns:
            Tuple of (APIKey instance, plaintext_key)
        """
        plaintext_key = generate_api_key()
        key_hash = hash_api_key(plaintext_key)
        key_prefix = get_key_prefix(plaintext_key)

        api_key = APIKey(
            id=kwargs.get("id", str(uuid4())),
            user_id=user_id,
            tenant_key=tenant_key,
            name=name,
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=permissions or ["*"],
            is_active=is_active,
            created_at=kwargs.get("created_at", datetime.now(timezone.utc)),
            last_used=kwargs.get("last_used"),
            revoked_at=kwargs.get("revoked_at"),
        )

        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)

        return api_key, plaintext_key

    @staticmethod
    async def create_revoked_key(
        session: AsyncSession, user_id: str, tenant_key: str, name: str = "Revoked API Key", **kwargs
    ) -> tuple[APIKey, str]:
        """Create a revoked API key."""
        return await APIKeyFactory.create_api_key(
            session,
            user_id=user_id,
            tenant_key=tenant_key,
            name=name,
            is_active=False,
            revoked_at=datetime.now(timezone.utc),
            **kwargs,
        )


class JWTHelper:
    """Helper for creating JWT tokens and auth headers."""

    @staticmethod
    def create_token(user: User) -> str:
        """
        Create JWT token for user.

        Args:
            user: User instance

        Returns:
            JWT token string
        """
        return JWTManager.create_access_token(
            user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
        )

    @staticmethod
    def create_auth_headers(user: User) -> Dict[str, str]:
        """
        Create authentication headers for user.

        Args:
            user: User instance

        Returns:
            Dict with Cookie header containing JWT
        """
        token = JWTHelper.create_token(user)
        return {"Cookie": f"access_token={token}"}

    @staticmethod
    def create_api_key_headers(api_key: str) -> Dict[str, str]:
        """
        Create API key authentication headers.

        Args:
            api_key: Plaintext API key

        Returns:
            Dict with X-API-Key header
        """
        return {"X-API-Key": api_key}


# Pytest fixtures for common test scenarios


@pytest_asyncio.fixture
async def admin_user(db_session):
    """Create admin user for testing."""
    return await UserFactory.create_admin(db_session)


@pytest_asyncio.fixture
async def developer_user(db_session):
    """Create developer user for testing."""
    return await UserFactory.create_developer(db_session)


@pytest_asyncio.fixture
async def viewer_user(db_session):
    """Create viewer user for testing."""
    return await UserFactory.create_viewer(db_session)


@pytest_asyncio.fixture
async def inactive_user(db_session):
    """Create inactive user for testing."""
    return await UserFactory.create_user(db_session, username="inactive_user", is_active=False)


@pytest_asyncio.fixture
async def other_tenant_user(db_session):
    """Create user in different tenant for isolation testing."""
    return await UserFactory.create_developer(db_session, username="other_tenant_user", tenant_key="other_tenant")


@pytest_asyncio.fixture
async def admin_with_api_key(db_session, admin_user):
    """Create admin user with API key."""
    api_key, plaintext_key = await APIKeyFactory.create_api_key(
        db_session, user_id=admin_user.id, tenant_key=admin_user.tenant_key, name="Admin API Key"
    )
    return admin_user, api_key, plaintext_key


@pytest_asyncio.fixture
async def developer_with_api_key(db_session, developer_user):
    """Create developer user with API key."""
    api_key, plaintext_key = await APIKeyFactory.create_api_key(
        db_session, user_id=developer_user.id, tenant_key=developer_user.tenant_key, name="Developer API Key"
    )
    return developer_user, api_key, plaintext_key


@pytest.fixture
def auth_headers_admin(admin_user):
    """Get auth headers for admin user."""
    return JWTHelper.create_auth_headers(admin_user)


@pytest.fixture
def auth_headers_developer(developer_user):
    """Get auth headers for developer user."""
    return JWTHelper.create_auth_headers(developer_user)


@pytest.fixture
def auth_headers_viewer(viewer_user):
    """Get auth headers for viewer user."""
    return JWTHelper.create_auth_headers(viewer_user)


@pytest_asyncio.fixture
async def multi_tenant_users(db_session):
    """
    Create users across multiple tenants for isolation testing.

    Returns:
        Dict with tenant_key -> list of users mapping
    """
    tenants = {"tenant_1": [], "tenant_2": [], "tenant_3": []}

    for tenant_key in tenants:
        # Create admin
        admin = await UserFactory.create_admin(db_session, username=f"{tenant_key}_admin", tenant_key=tenant_key)
        tenants[tenant_key].append(admin)

        # Create developers
        for i in range(2):
            dev = await UserFactory.create_developer(
                db_session, username=f"{tenant_key}_dev_{i}", tenant_key=tenant_key
            )
            tenants[tenant_key].append(dev)

    return tenants


@pytest_asyncio.fixture
async def users_with_api_keys(db_session):
    """
    Create multiple users with API keys for comprehensive testing.

    Returns:
        List of tuples: (user, api_key_model, plaintext_key)
    """
    users_and_keys = []

    # Admin with multiple keys
    admin = await UserFactory.create_admin(db_session, username="admin_multi_key")
    for i in range(3):
        key, plaintext = await APIKeyFactory.create_api_key(
            db_session, user_id=admin.id, tenant_key=admin.tenant_key, name=f"Admin Key {i + 1}"
        )
        users_and_keys.append((admin, key, plaintext))

    # Developer with one key
    dev = await UserFactory.create_developer(db_session, username="dev_single_key")
    key, plaintext = await APIKeyFactory.create_api_key(
        db_session, user_id=dev.id, tenant_key=dev.tenant_key, name="Developer Key"
    )
    users_and_keys.append((dev, key, plaintext))

    # Developer with revoked key
    dev2 = await UserFactory.create_developer(db_session, username="dev_revoked_key")
    key, plaintext = await APIKeyFactory.create_revoked_key(
        db_session, user_id=dev2.id, tenant_key=dev2.tenant_key, name="Revoked Key"
    )
    users_and_keys.append((dev2, key, plaintext))

    return users_and_keys


@pytest_asyncio.fixture
async def setup_wizard_state(db_session):
    """
    Initialize wizard state for testing.

    Returns:
        Dict with wizard state for different scenarios
    """
    return {
        "localhost": {
            "mode": "localhost",
            "tools_attached": ["claude-code"],
            "serena_enabled": True,
            "admin_created": False,
            "api_key_generated": False,
        },
        "lan": {
            "mode": "lan",
            "tools_attached": ["claude-code"],
            "serena_enabled": False,
            "admin_created": True,
            "api_key_generated": True,
            "server_ip": "192.168.1.100",
            "hostname": "giljo.local",
        },
        "wan": {
            "mode": "wan",
            "tools_attached": ["claude-code", "serena"],
            "serena_enabled": True,
            "admin_created": True,
            "api_key_generated": True,
            "server_ip": "203.0.113.45",  # Example public IP
            "hostname": "giljo.example.com",
        },
    }


@pytest_asyncio.fixture
async def password_test_cases():
    """
    Test cases for password validation.

    Returns:
        Dict with password test scenarios
    """
    return {
        "valid": ["SecurePass123!", "MyP@ssw0rd2024", "Complex_Pass_123", "!@#$%^&*()_+Pass1"],
        "invalid": {
            "too_short": "Pass1!",  # < 8 chars
            "no_number": "PasswordOnly!",
            "no_special": "Password123",
            "spaces": "Pass Word 123!",
            "empty": "",
        },
    }


# Export all factories and helpers for easy import
__all__ = [
    "APIKeyFactory",
    "JWTHelper",
    "UserFactory",
    "admin_user",
    "admin_with_api_key",
    "auth_headers_admin",
    "auth_headers_developer",
    "auth_headers_viewer",
    "developer_user",
    "developer_with_api_key",
    "inactive_user",
    "multi_tenant_users",
    "other_tenant_user",
    "password_test_cases",
    "setup_wizard_state",
    "users_with_api_keys",
    "viewer_user",
]
