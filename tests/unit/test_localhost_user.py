"""
Unit tests for localhost user management.

Tests the creation and retrieval of the system localhost user
that enables zero-click authentication for 127.0.0.1/::1 clients.
"""

import pytest
from sqlalchemy import select

from src.giljo_mcp.auth.localhost_user import ensure_localhost_user, get_localhost_user
from src.giljo_mcp.models import User


@pytest.mark.asyncio
async def test_ensure_localhost_user_creates_if_missing(db_session):
    """Test localhost user creation when not exists."""
    # Arrange: Empty database (no localhost user)

    # Act: Call ensure_localhost_user
    user = await ensure_localhost_user(db_session)

    # Assert: User created with correct attributes
    assert user is not None
    assert user.username == "localhost"
    assert user.email == "localhost@local"
    assert user.is_system_user is True
    assert user.password_hash is None  # No password - auto-login only
    assert user.role == "admin"
    assert user.is_active is True

    # Verify user was persisted to database
    result = await db_session.execute(select(User).where(User.username == "localhost"))
    db_user = result.scalar_one_or_none()
    assert db_user is not None
    assert db_user.id == user.id


@pytest.mark.asyncio
async def test_ensure_localhost_user_idempotent(db_session):
    """Test calling ensure_localhost_user twice doesn't create duplicate."""
    # Arrange: Create localhost user first time
    user1 = await ensure_localhost_user(db_session)

    # Act: Call again
    user2 = await ensure_localhost_user(db_session)

    # Assert: Same user returned (not a duplicate)
    assert user1.id == user2.id
    assert user1.username == user2.username

    # Verify only one localhost user in database
    result = await db_session.execute(select(User).where(User.username == "localhost"))
    all_users = result.scalars().all()
    assert len(all_users) == 1


@pytest.mark.asyncio
async def test_get_localhost_user_returns_existing(db_session):
    """Test retrieving existing localhost user."""
    # Arrange: Create localhost user
    created_user = await ensure_localhost_user(db_session)

    # Act: Get user using get_localhost_user
    user = await get_localhost_user(db_session)

    # Assert: User found and matches created user
    assert user is not None
    assert user.id == created_user.id
    assert user.username == "localhost"
    assert user.is_system_user is True


@pytest.mark.asyncio
async def test_get_localhost_user_returns_none_if_missing(db_session):
    """Test returns None when localhost user doesn't exist."""
    # Arrange: Empty database (no localhost user created)

    # Act: Try to get localhost user
    user = await get_localhost_user(db_session)

    # Assert: None returned
    assert user is None


@pytest.mark.asyncio
async def test_localhost_user_tenant_key(db_session):
    """Test localhost user has default tenant key."""
    # Arrange & Act: Create localhost user
    user = await ensure_localhost_user(db_session)

    # Assert: Has default tenant key
    assert user.tenant_key == "default"


@pytest.mark.asyncio
async def test_localhost_user_no_api_keys_initially(db_session):
    """Test localhost user starts without API keys."""
    # Arrange & Act: Create localhost user
    user = await ensure_localhost_user(db_session)

    # Assert: No API keys associated (query directly to avoid lazy-load issues)
    from src.giljo_mcp.models import APIKey

    result = await db_session.execute(select(APIKey).where(APIKey.user_id == user.id))
    api_keys = result.scalars().all()
    assert len(api_keys) == 0


@pytest.mark.asyncio
async def test_localhost_user_cannot_login_with_password(db_session):
    """Test localhost user has no password (cannot login via password)."""
    # Arrange & Act: Create localhost user
    user = await ensure_localhost_user(db_session)

    # Assert: No password hash set
    assert user.password_hash is None

    # This user can ONLY be used via auto-login middleware
    # Password authentication should be impossible


@pytest.mark.asyncio
async def test_ensure_localhost_user_transaction_safety(db_session):
    """Test ensure_localhost_user handles transaction commit properly."""
    # Arrange & Act: Create localhost user
    user = await ensure_localhost_user(db_session)

    # Assert: User is persisted and can be queried in new transaction
    # Flush session to ensure data is written
    await db_session.flush()

    # Query again to verify persistence
    result = await db_session.execute(select(User).where(User.id == user.id))
    persisted_user = result.scalar_one_or_none()
    assert persisted_user is not None
    assert persisted_user.username == "localhost"
