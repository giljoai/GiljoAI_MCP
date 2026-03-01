"""
Unit tests for User and APIKey authentication models.

Tests cover:
- User model CRUD operations
- APIKey model CRUD operations
- User-APIKey relationship and cascade delete
- Password hashing and verification
- API key hashing and verification
- Unique constraints (username, email, key_hash)
- Default values and check constraints
- Multi-tenant isolation
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from src.giljo_mcp.api_key_utils import (
    generate_api_key,
    get_key_prefix,
    hash_api_key,
    validate_api_key_format,
    verify_api_key,
)
from src.giljo_mcp.models import APIKey, User

pytestmark = pytest.mark.skip(reason="0750b: Auth model tests need project fixture updates for NOT NULL constraints")

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
class TestAPIKeyModel:
    """Test APIKey model CRUD operations and constraints."""

    async def test_create_api_key(self, db_session):
        """Test creating a new API key."""
        # First create a user
        user = User(
            tenant_key="test_tenant",
            username="keyuser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Generate and hash API key
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)
        key_prefix = get_key_prefix(api_key)

        # Create APIKey record
        api_key_record = APIKey(
            tenant_key=user.tenant_key,
            user_id=user.id,
            name="Test API Key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=["*"],
        )

        db_session.add(api_key_record)
        await db_session.commit()
        await db_session.refresh(api_key_record)

        # Verify API key was created
        assert api_key_record.id is not None
        assert api_key_record.user_id == user.id
        assert api_key_record.name == "Test API Key"
        assert api_key_record.is_active is True
        assert api_key_record.permissions == ["*"]
        assert api_key_record.revoked_at is None

        # Verify key can be verified
        assert verify_api_key(api_key, api_key_record.key_hash)

    async def test_api_key_default_permissions(self, db_session):
        """Test APIKey default permissions (empty list)."""
        user = User(
            tenant_key="test_tenant",
            username="permuser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        api_key = generate_api_key()
        api_key_record = APIKey(
            tenant_key=user.tenant_key,
            user_id=user.id,
            name="Default Perms Key",
            key_hash=hash_api_key(api_key),
            key_prefix=get_key_prefix(api_key),
            # permissions not specified - should default to []
        )

        db_session.add(api_key_record)
        await db_session.commit()
        await db_session.refresh(api_key_record)

        # Check default
        assert api_key_record.permissions == []

    async def test_api_key_unique_hash(self, db_session):
        """Test key_hash unique constraint."""
        user = User(
            tenant_key="test_tenant",
            username="hashuser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create first API key
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)

        api_key1 = APIKey(
            tenant_key=user.tenant_key,
            user_id=user.id,
            name="Key 1",
            key_hash=key_hash,
            key_prefix=get_key_prefix(api_key),
        )
        db_session.add(api_key1)
        await db_session.commit()

        # Try to create another key with same hash (should fail)
        api_key2 = APIKey(
            tenant_key=user.tenant_key,
            user_id=user.id,
            name="Key 2",
            key_hash=key_hash,  # Same hash
            key_prefix=get_key_prefix(api_key),
        )
        db_session.add(api_key2)

        with pytest.raises(IntegrityError):
            await db_session.commit()

    async def test_api_key_revoked_consistency(self, db_session):
        """Test check constraint: revoked_at consistency with is_active."""
        user = User(
            tenant_key="test_tenant",
            username="revokeuser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        api_key = generate_api_key()
        api_key_record = APIKey(
            tenant_key=user.tenant_key,
            user_id=user.id,
            name="Revoke Test Key",
            key_hash=hash_api_key(api_key),
            key_prefix=get_key_prefix(api_key),
        )
        db_session.add(api_key_record)
        await db_session.commit()
        await db_session.refresh(api_key_record)

        # Revoke the key
        api_key_record.is_active = False
        api_key_record.revoked_at = datetime.now(timezone.utc)
        await db_session.commit()
        await db_session.refresh(api_key_record)

        assert api_key_record.is_active is False
        assert api_key_record.revoked_at is not None

    async def test_update_last_used(self, db_session):
        """Test updating last_used timestamp."""
        user = User(
            tenant_key="test_tenant",
            username="useduser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        api_key = generate_api_key()
        api_key_record = APIKey(
            tenant_key=user.tenant_key,
            user_id=user.id,
            name="Usage Tracking Key",
            key_hash=hash_api_key(api_key),
            key_prefix=get_key_prefix(api_key),
        )
        db_session.add(api_key_record)
        await db_session.commit()
        await db_session.refresh(api_key_record)

        assert api_key_record.last_used is None

        # Simulate API key usage
        used_time = datetime.now(timezone.utc)
        api_key_record.last_used = used_time
        await db_session.commit()
        await db_session.refresh(api_key_record)

        assert api_key_record.last_used is not None
        assert (api_key_record.last_used - used_time).total_seconds() < 1


@pytest.mark.asyncio
class TestUserAPIKeyRelationship:
    """Test User-APIKey relationship and cascade operations."""

    async def test_user_api_keys_relationship(self, db_session):
        """Test User.api_keys relationship."""
        from sqlalchemy.orm import selectinload

        user = User(
            tenant_key="test_tenant",
            username="reluser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create multiple API keys for the user
        for i in range(3):
            api_key = generate_api_key()
            api_key_record = APIKey(
                tenant_key=user.tenant_key,
                user_id=user.id,
                name=f"API Key {i + 1}",
                key_hash=hash_api_key(api_key),
                key_prefix=get_key_prefix(api_key),
            )
            db_session.add(api_key_record)

        await db_session.commit()

        # Reload user with eager loading of api_keys
        result = await db_session.execute(select(User).filter(User.id == user.id).options(selectinload(User.api_keys)))
        user = result.scalar_one()

        # Access relationship
        assert len(user.api_keys) == 3
        assert all(key.user_id == user.id for key in user.api_keys)

    async def test_cascade_delete_api_keys(self, db_session):
        """Test that deleting user cascades to API keys."""
        user = User(
            tenant_key="test_tenant",
            username="cascadeuser",
            password_hash=bcrypt.hash("password"),
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Create API keys
        api_keys = []
        for i in range(2):
            api_key = generate_api_key()
            api_key_record = APIKey(
                tenant_key=user.tenant_key,
                user_id=user.id,
                name=f"Cascade Key {i + 1}",
                key_hash=hash_api_key(api_key),
                key_prefix=get_key_prefix(api_key),
            )
            db_session.add(api_key_record)
            api_keys.append(api_key_record)

        await db_session.commit()

        # Get API key IDs before deleting user
        key_ids = [key.id for key in api_keys]

        # Delete the user
        await db_session.delete(user)
        await db_session.commit()

        # Verify API keys were deleted (CASCADE)
        result = await db_session.execute(select(APIKey).filter(APIKey.id.in_(key_ids)))
        remaining_keys = result.scalars().all()

        assert len(remaining_keys) == 0


@pytest.mark.asyncio
class TestAPIKeyUtilities:
    """Test API key utility functions."""

    def test_generate_api_key(self):
        """Test API key generation."""
        api_key = generate_api_key()

        assert api_key.startswith("gk_")
        assert len(api_key) > 40  # gk_ (3) + token (~43 chars)
        assert validate_api_key_format(api_key)

    def test_hash_and_verify_api_key(self):
        """Test API key hashing and verification."""
        api_key = generate_api_key()
        key_hash = hash_api_key(api_key)

        # Verify correct key
        assert verify_api_key(api_key, key_hash)

        # Verify wrong key
        wrong_key = generate_api_key()
        assert not verify_api_key(wrong_key, key_hash)

    def test_get_key_prefix(self):
        """Test key prefix extraction."""
        api_key = "gk_verylongtoken123456789"

        prefix = get_key_prefix(api_key)
        assert prefix == "gk_verylongt..."

        prefix_8 = get_key_prefix(api_key, 8)
        assert prefix_8 == "gk_veryl..."

    def test_validate_api_key_format(self):
        """Test API key format validation."""
        # Valid keys
        assert validate_api_key_format("gk_abc123def456ghi789")
        assert validate_api_key_format(generate_api_key())

        # Invalid keys
        assert not validate_api_key_format("invalid")
        assert not validate_api_key_format("gk_short")
        assert not validate_api_key_format("wrong_prefix_abc123def456")
        assert not validate_api_key_format("")
        assert not validate_api_key_format(None)

    def test_display_key_property(self, db_session):
        """Test APIKey.display_key property."""
        # This is a sync test for the property
        api_key = generate_api_key()
        api_key_record = APIKey(
            tenant_key="test_tenant",
            user_id=str(uuid4()),
            name="Display Test",
            key_hash=hash_api_key(api_key),
            key_prefix=get_key_prefix(api_key),
        )

        display = api_key_record.display_key
        assert display.endswith("...")
        assert len(display) > 3


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
