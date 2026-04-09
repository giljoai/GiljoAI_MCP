# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test suite for UserService CRUD operations and role management.

Split from test_user_service.py during test reorganization.
Covers: list_users, get_user, create_user, update_user, delete_user, change_role.

Shared fixtures (test_tenant_key, user_service, test_user, admin_user) are
provided by tests/services/conftest.py.
"""

from uuid import uuid4

import bcrypt
import pytest

from src.giljo_mcp.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.auth import User

# ============================================================================
# TEST: list_users
# ============================================================================


@pytest.mark.asyncio
async def test_list_users_returns_users_for_tenant(user_service, db_session, test_user, test_tenant_key):
    """Test that list_users returns list of User ORM models for tenant"""
    users = await user_service.list_users()

    assert isinstance(users, list)
    assert len(users) >= 1  # At least test_user

    # Verify returns User ORM instances, not dicts
    for u in users:
        assert isinstance(u, User)

    # Verify test_user in list
    usernames = [u.username for u in users]
    assert test_user.username in usernames


@pytest.mark.asyncio
async def test_list_users_tenant_isolation(user_service, db_session, test_tenant_key):
    """Test that list_users only returns users from same tenant"""
    # Create user in different tenant
    other_tenant = f"other_tenant_{uuid4().hex[:8]}"
    other_user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw("OtherPassword123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        tenant_key=other_tenant,
        role="developer",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    # List users in test tenant
    users = await user_service.list_users()

    assert isinstance(users, list)
    # Verify returns User ORM instances
    for u in users:
        assert isinstance(u, User)
    usernames = [u.username for u in users]
    assert other_user.username not in usernames


@pytest.mark.asyncio
async def test_list_users_includes_inactive(user_service, db_session, test_tenant_key):
    """Test that list_users includes inactive users by default"""
    # Create inactive user
    inactive_user = User(
        id=str(uuid4()),
        username=f"inactive_{uuid4().hex[:6]}",
        email=f"inactive_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw("Password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        tenant_key=test_tenant_key,
        role="developer",
        is_active=False,
    )
    db_session.add(inactive_user)
    await db_session.commit()

    users = await user_service.list_users()

    assert isinstance(users, list)
    # Verify returns User ORM instances
    for u in users:
        assert isinstance(u, User)
    usernames = [u.username for u in users]
    assert inactive_user.username in usernames


# ============================================================================
# TEST: get_user
# ============================================================================


@pytest.mark.asyncio
async def test_get_user_returns_user_by_id(user_service, test_user):
    """Test that get_user returns User ORM model by ID"""
    user = await user_service.get_user(test_user.id)

    assert isinstance(user, User)
    assert user.id == test_user.id
    assert user.username == test_user.username
    assert user.email == test_user.email


@pytest.mark.asyncio
async def test_get_user_not_found(user_service):
    """Test that get_user raises ResourceNotFoundError for non-existent user"""
    fake_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await user_service.get_user(fake_id)

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_user_tenant_isolation(user_service, db_session):
    """Test that get_user respects tenant isolation"""
    # Create user in different tenant
    other_tenant = f"other_tenant_{uuid4().hex[:8]}"
    other_user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hashpw("Password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        tenant_key=other_tenant,
        role="developer",
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    # Try to retrieve user from different tenant
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await user_service.get_user(other_user.id)

    assert "not found" in str(exc_info.value).lower()


# ============================================================================
# TEST: create_user
# ============================================================================


@pytest.mark.asyncio
async def test_create_user_success(user_service, test_tenant_key):
    """Test successful user creation returns User ORM model"""
    username = f"newuser_{uuid4().hex[:6]}"
    email = f"new_{uuid4().hex[:6]}@example.com"

    user = await user_service.create_user(
        username=username, email=email, full_name="New User", password="NewPassword123", role="developer"
    )

    assert isinstance(user, User)
    assert user.username == username
    assert user.email == email
    assert user.role == "developer"
    assert user.is_active is True
    assert user.tenant_key == test_tenant_key


@pytest.mark.asyncio
async def test_create_user_duplicate_username(user_service, test_user):
    """Test that create_user prevents duplicate usernames"""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.create_user(
            username=test_user.username,  # Duplicate
            email="different@example.com",
            password="Password123",
            role="developer",
        )

    error_msg = str(exc_info.value).lower()
    assert "already exists" in error_msg
    assert "username" in error_msg


@pytest.mark.asyncio
async def test_create_user_duplicate_email(user_service, test_user):
    """Test that create_user prevents duplicate emails"""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.create_user(
            username=f"newuser_{uuid4().hex[:6]}",
            email=test_user.email,  # Duplicate
            password="Password123",
            role="developer",
        )

    error_msg = str(exc_info.value).lower()
    assert "already exists" in error_msg
    assert "email" in error_msg


@pytest.mark.asyncio
async def test_create_user_default_password(user_service):
    """Test that create_user sets default password 'GiljoMCP' and returns User ORM model"""
    username = f"newuser_{uuid4().hex[:6]}"

    user = await user_service.create_user(
        username=username,
        email=f"new_{uuid4().hex[:6]}@example.com",
        role="developer",
        # No password provided - should default to "GiljoMCP"
    )

    assert isinstance(user, User)
    assert user.must_change_password is True


# ============================================================================
# TEST: update_user
# ============================================================================


@pytest.mark.asyncio
async def test_update_user_success(user_service, test_user):
    """Test successful user update returns User ORM model"""
    new_email = f"updated_{uuid4().hex[:6]}@example.com"

    user = await user_service.update_user(user_id=test_user.id, email=new_email, full_name="Updated Name")

    assert isinstance(user, User)
    assert user.email == new_email
    assert user.full_name == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_not_found(user_service):
    """Test that update_user raises ResourceNotFoundError for non-existent user"""
    fake_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await user_service.update_user(user_id=fake_id, email="new@example.com")

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_update_user_duplicate_email(user_service, test_user, admin_user):
    """Test that update_user prevents duplicate emails"""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.update_user(
            user_id=test_user.id,
            email=admin_user.email,  # Duplicate
        )

    assert "already exists" in str(exc_info.value).lower()


# ============================================================================
# TEST: delete_user (soft delete)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_user_soft_delete(user_service, test_user, db_session):
    """Test that delete_user performs soft delete (is_active=False)"""
    result = await user_service.delete_user(test_user.id)

    # Verify method completes without error (void return)
    assert result is None

    # Verify user is deactivated, not deleted
    await db_session.refresh(test_user)
    assert test_user.is_active is False


@pytest.mark.asyncio
async def test_delete_user_not_found(user_service):
    """Test that delete_user raises ResourceNotFoundError for non-existent user"""
    fake_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await user_service.delete_user(fake_id)

    assert "not found" in str(exc_info.value).lower()


# ============================================================================
# TEST: change_role
# ============================================================================


@pytest.mark.asyncio
async def test_change_role_success(user_service, test_user, db_session):
    """Test successful role change returns User ORM model"""
    user = await user_service.change_role(user_id=test_user.id, new_role="viewer")

    assert isinstance(user, User)
    assert user.role == "viewer"

    await db_session.refresh(test_user)
    assert test_user.role == "viewer"


@pytest.mark.asyncio
async def test_change_role_invalid_role(user_service, test_user):
    """Test that change_role rejects invalid roles"""
    with pytest.raises(ValidationError) as exc_info:
        await user_service.change_role(
            user_id=test_user.id,
            new_role="superuser",  # Invalid
        )

    assert "invalid" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_change_role_admin_restriction(user_service, admin_user):
    """Test that last admin cannot be demoted"""
    with pytest.raises(AuthorizationError) as exc_info:
        await user_service.change_role(user_id=admin_user.id, new_role="developer")

    assert "admin" in str(exc_info.value).lower()
