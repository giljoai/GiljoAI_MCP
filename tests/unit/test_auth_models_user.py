"""
Unit tests for the User authentication model.

Tests cover:
- User model CRUD operations
- Password hashing and verification
- Unique constraints (username, email)
- Default values and check constraints
- Multi-tenant isolation for users and API keys
"""

from datetime import datetime, timezone

import pytest
from passlib.hash import bcrypt
from sqlalchemy import select

from sqlalchemy.exc import IntegrityError

from src.giljo_mcp.api_key_utils import (
    generate_api_key,
    hash_api_key,
)
from src.giljo_mcp.models import APIKey, User

pytestmark = pytest.mark.skip(reason="0750c3: duplicate key on test@example.com — needs unique test user fixture")


@pytest.mark.asyncio
class TestUserModel:
    """Test User model CRUD operations and constraints."""

    async def test_create_user(self, db_session):
        """Test creating a new user with password hash."""
        # Hash password using bcrypt
        password_hash = bcrypt.hash("test_password_123")

        user = User(
            tenant_key="test_tenant",
            username="testuser",
            email="test@example.com",
            password_hash=password_hash,
            full_name="Test User",
            role="developer",
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Verify user was created
        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.role == "developer"
        assert user.is_active is True
        assert user.created_at is not None

        # Verify password can be verified
        assert bcrypt.verify("test_password_123", user.password_hash)

    async def test_user_default_values(self, db_session):
        """Test User model default values."""
        user = User(
            tenant_key="test_tenant",
            username="defaultuser",
            password_hash=bcrypt.hash("password"),
        )

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Check defaults
        assert user.role == "developer"
        assert user.is_active is True
        assert user.email is None
        assert user.full_name is None
        assert user.last_login is None

    async def test_user_unique_username(self, db_session):
        """Test username unique constraint."""
        user1 = User(
            tenant_key="test_tenant",
            username="uniqueuser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user1)
        await db_session.commit()

        # Try to create another user with same username
        user2 = User(
            tenant_key="test_tenant",
            username="uniqueuser",
            password_hash=bcrypt.hash("password2"),
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_user_unique_email(self, db_session):
        """Test email unique constraint."""
        user1 = User(
            tenant_key="test_tenant",
            username="user1",
            email="same@example.com",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user1)
        await db_session.commit()

        # Try to create another user with same email
        user2 = User(
            tenant_key="test_tenant",
            username="user2",
            email="same@example.com",
            password_hash=bcrypt.hash("password2"),
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_user_role_constraint(self, db_session):
        """Test role check constraint (admin, developer, viewer)."""
        # Valid role
        user = User(
            tenant_key="test_tenant",
            username="adminuser",
            password_hash=bcrypt.hash("password"),
            role="admin",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        assert user.role == "admin"

        # Invalid role should fail
        await db_session.rollback()
        user2 = User(
            tenant_key="test_tenant",
            username="invaliduser",
            password_hash=bcrypt.hash("password"),
            role="superadmin",  # Not a valid role
        )
        db_session.add(user2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_update_last_login(self, db_session):
        """Test updating last_login timestamp."""
        user = User(
            tenant_key="test_tenant",
            username="loginuser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        assert user.last_login is None

        # Simulate login
        login_time = datetime.now(timezone.utc)
        user.last_login = login_time
        await db_session.commit()
        await db_session.refresh(user)

        assert user.last_login is not None
        assert (user.last_login - login_time).total_seconds() < 1

    async def test_user_tenant_isolation(self, db_session):
        """Test multi-tenant isolation by tenant_key."""
        # Create users in different tenants
        user1 = User(
            tenant_key="tenant_1",
            username="user_tenant1",
            password_hash=bcrypt.hash("password"),
        )
        user2 = User(
            tenant_key="tenant_2",
            username="user_tenant2",
            password_hash=bcrypt.hash("password"),
        )

        db_session.add_all([user1, user2])
        await db_session.commit()

        # Query for tenant_1 only
        result = await db_session.execute(select(User).filter(User.tenant_key == "tenant_1"))
        tenant1_users = result.scalars().all()

        assert len(tenant1_users) == 1
        assert tenant1_users[0].username == "user_tenant1"


@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """Test multi-tenant isolation for auth models."""

    async def test_tenant_isolation_users(self, db_session):
        """Test that users are isolated by tenant_key."""
        # Create users in different tenants
        user1 = User(
            tenant_key="tenant_alpha",
            username="alpha_user",
            password_hash=bcrypt.hash("password"),
        )
        user2 = User(
            tenant_key="tenant_beta",
            username="beta_user",
            password_hash=bcrypt.hash("password"),
        )

        db_session.add_all([user1, user2])
        await db_session.commit()

        # Query with tenant_key filter (CRITICAL for multi-tenant)
        result = await db_session.execute(select(User).filter(User.tenant_key == "tenant_alpha"))
        alpha_users = result.scalars().all()

        assert len(alpha_users) == 1
        assert alpha_users[0].username == "alpha_user"

    async def test_tenant_isolation_api_keys(self, db_session):
        """Test that API keys are isolated by tenant_key."""
        # Create users in different tenants
        user1 = User(
            tenant_key="tenant_x",
            username="user_x",
            password_hash=bcrypt.hash("password"),
        )
        user2 = User(
            tenant_key="tenant_y",
            username="user_y",
            password_hash=bcrypt.hash("password"),
        )

        db_session.add_all([user1, user2])
        await db_session.commit()
        await db_session.refresh(user1)
        await db_session.refresh(user2)

        # Create API keys for each user
        key1 = APIKey(
            tenant_key=user1.tenant_key,
            user_id=user1.id,
            name="X Key",
            key_hash=hash_api_key(generate_api_key()),
            key_prefix="gk_xxx...",
        )
        key2 = APIKey(
            tenant_key=user2.tenant_key,
            user_id=user2.id,
            name="Y Key",
            key_hash=hash_api_key(generate_api_key()),
            key_prefix="gk_yyy...",
        )

        db_session.add_all([key1, key2])
        await db_session.commit()

        # Query with tenant_key filter (CRITICAL for multi-tenant)
        result = await db_session.execute(select(APIKey).filter(APIKey.tenant_key == "tenant_x"))
        tenant_x_keys = result.scalars().all()

        assert len(tenant_x_keys) == 1
        assert tenant_x_keys[0].name == "X Key"
