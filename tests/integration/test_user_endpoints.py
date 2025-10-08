"""
Integration tests for user management CRUD endpoints.

Tests all user CRUD operations, role-based access control, multi-tenant isolation,
password validation, and edge cases like self-demotion prevention.

Follows TDD principles: Tests written first to define expected behavior.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from passlib.hash import bcrypt
from httpx import AsyncClient
from uuid import uuid4

from src.giljo_mcp.models import User


@pytest.mark.asyncio
async def test_list_users_as_admin(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test admin can list all users in their tenant."""
    response = await test_client.get("/api/users/", cookies=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 2  # admin + test_user

    # Verify users are from same tenant
    for user_data in data:
        assert user_data["tenant_key"] == "default"
        assert "password_hash" not in user_data  # Security: password excluded


@pytest.mark.asyncio
async def test_list_users_as_non_admin(test_client: AsyncClient, authenticated_headers: dict):
    """Test non-admin cannot list users."""
    response = await test_client.get("/api/users/", cookies=authenticated_headers)

    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_as_admin(test_client: AsyncClient, admin_headers: dict):
    """Test admin can create new users."""
    response = await test_client.post(
        "/api/users/",
        json={
            "username": "newdevuser",
            "email": "newdev@example.com",
            "full_name": "New Developer",
            "password": "securepass123",
            "role": "developer",
            "is_active": True
        },
        cookies=admin_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newdevuser"
    assert data["email"] == "newdev@example.com"
    assert data["full_name"] == "New Developer"
    assert data["role"] == "developer"
    assert data["is_active"] is True
    assert "password_hash" not in data
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_user_as_non_admin(test_client: AsyncClient, authenticated_headers: dict):
    """Test non-admin cannot create users."""
    response = await test_client.post(
        "/api/users/",
        json={
            "username": "unauthorized",
            "password": "pass123",
            "role": "developer"
        },
        cookies=authenticated_headers
    )

    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_create_user_duplicate_username(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test creating user with duplicate username fails."""
    response = await test_client.post(
        "/api/users/",
        json={
            "username": "testuser",  # Already exists
            "password": "pass123",
            "email": "different@example.com",
            "role": "developer"
        },
        cookies=admin_headers
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_user_duplicate_email(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test creating user with duplicate email fails."""
    response = await test_client.post(
        "/api/users/",
        json={
            "username": "differentuser",
            "password": "pass123",
            "email": "test@example.com",  # Already exists
            "role": "developer"
        },
        cookies=admin_headers
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_create_user_invalid_role(test_client: AsyncClient, admin_headers: dict):
    """Test creating user with invalid role fails."""
    response = await test_client.post(
        "/api/users/",
        json={
            "username": "baduser",
            "password": "pass123",
            "email": "bad@example.com",
            "role": "superadmin"  # Invalid role
        },
        cookies=admin_headers
    )

    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_get_user_as_admin(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test admin can get any user details."""
    response = await test_client.get(f"/api/users/{test_user.id}", cookies=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(test_user.id)
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"
    assert data["role"] == "developer"
    assert "password_hash" not in data


@pytest.mark.asyncio
async def test_get_user_self(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """Test user can get their own details."""
    response = await test_client.get(f"/api/users/{test_user.id}", cookies=authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_get_user_other_as_non_admin(test_client: AsyncClient, authenticated_headers: dict, admin_user: User):
    """Test non-admin cannot get other users' details."""
    response = await test_client.get(f"/api/users/{admin_user.id}", cookies=authenticated_headers)

    assert response.status_code == 403
    assert "Cannot view other users" in response.json()["detail"]


@pytest.mark.asyncio
async def test_get_user_nonexistent(test_client: AsyncClient, admin_headers: dict):
    """Test getting non-existent user returns 404."""
    fake_id = uuid4()
    response = await test_client.get(f"/api/users/{fake_id}", cookies=admin_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_get_user_different_tenant(test_client: AsyncClient, admin_headers: dict):
    """Test admin cannot get users from different tenant."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Create user in different tenant
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        other_tenant_user = User(
            username="othertenant",
            password_hash=bcrypt.hash("pass123"),
            email="other@example.com",
            role="developer",
            tenant_key="other_tenant",
            is_active=True
        )
        session.add(other_tenant_user)
        await session.commit()
        await session.refresh(other_tenant_user)

        user_id = other_tenant_user.id
        break

    # Try to get user from different tenant
    response = await test_client.get(f"/api/users/{user_id}", cookies=admin_headers)

    assert response.status_code == 404  # Should not find user in different tenant


@pytest.mark.asyncio
async def test_update_user_as_admin(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test admin can update any user."""
    response = await test_client.put(
        f"/api/users/{test_user.id}",
        json={
            "email": "updated@example.com",
            "full_name": "Updated Name",
            "is_active": True
        },
        cookies=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "updated@example.com"
    assert data["full_name"] == "Updated Name"


@pytest.mark.asyncio
async def test_update_user_self(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """Test user can update their own profile."""
    response = await test_client.put(
        f"/api/users/{test_user.id}",
        json={
            "email": "selfupdate@example.com",
            "full_name": "Self Updated"
        },
        cookies=authenticated_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "selfupdate@example.com"
    assert data["full_name"] == "Self Updated"


@pytest.mark.asyncio
async def test_update_user_other_as_non_admin(test_client: AsyncClient, authenticated_headers: dict, admin_user: User):
    """Test non-admin cannot update other users."""
    response = await test_client.put(
        f"/api/users/{admin_user.id}",
        json={
            "email": "hacked@example.com"
        },
        cookies=authenticated_headers
    )

    assert response.status_code == 403
    assert "Cannot update other users" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_user_duplicate_email(test_client: AsyncClient, admin_headers: dict, test_user: User, admin_user: User):
    """Test updating user with duplicate email fails."""
    response = await test_client.put(
        f"/api/users/{test_user.id}",
        json={
            "email": "admin@example.com"  # admin's email
        },
        cookies=admin_headers
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_delete_user_as_admin(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test admin can soft-delete users."""
    response = await test_client.delete(f"/api/users/{test_user.id}", cookies=admin_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "User deactivated successfully"

    # Verify user is deactivated (soft delete)
    get_response = await test_client.get(f"/api/users/{test_user.id}", cookies=admin_headers)
    assert get_response.status_code == 200
    user_data = get_response.json()
    assert user_data["is_active"] is False


@pytest.mark.asyncio
async def test_delete_user_as_non_admin(test_client: AsyncClient, authenticated_headers: dict, admin_user: User):
    """Test non-admin cannot delete users."""
    response = await test_client.delete(f"/api/users/{admin_user.id}", cookies=authenticated_headers)

    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_user_nonexistent(test_client: AsyncClient, admin_headers: dict):
    """Test deleting non-existent user returns 404."""
    fake_id = uuid4()
    response = await test_client.delete(f"/api/users/{fake_id}", cookies=admin_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_user_role_as_admin(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test admin can change user roles."""
    response = await test_client.put(
        f"/api/users/{test_user.id}/role",
        json={
            "role": "admin"
        },
        cookies=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["role"] == "admin"
    assert data["message"] == "User role updated successfully"


@pytest.mark.asyncio
async def test_change_user_role_as_non_admin(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """Test non-admin cannot change user roles."""
    response = await test_client.put(
        f"/api/users/{test_user.id}/role",
        json={
            "role": "admin"
        },
        cookies=authenticated_headers
    )

    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_change_user_role_invalid(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test changing to invalid role fails."""
    response = await test_client.put(
        f"/api/users/{test_user.id}/role",
        json={
            "role": "superadmin"  # Invalid
        },
        cookies=admin_headers
    )

    assert response.status_code == 422  # Pydantic validation error


@pytest.mark.asyncio
async def test_admin_cannot_demote_self(test_client: AsyncClient, admin_headers: dict, admin_user: User):
    """Test admin cannot demote themselves (prevent lockout)."""
    response = await test_client.put(
        f"/api/users/{admin_user.id}/role",
        json={
            "role": "developer"
        },
        cookies=admin_headers
    )

    assert response.status_code == 400
    assert "cannot change your own role" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_change_password(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """Test user can change their own password."""
    response = await test_client.put(
        f"/api/users/{test_user.id}/password",
        json={
            "old_password": "testpassword123",
            "new_password": "newsecurepass456"
        },
        cookies=authenticated_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password updated successfully"

    # Verify new password works
    login_response = await test_client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "newsecurepass456"
        }
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_old(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """Test password change fails with wrong old password."""
    response = await test_client.put(
        f"/api/users/{test_user.id}/password",
        json={
            "old_password": "wrongoldpass",
            "new_password": "newsecurepass456"
        },
        cookies=authenticated_headers
    )

    assert response.status_code == 400
    assert "Current password is incorrect" in response.json()["detail"]


@pytest.mark.asyncio
async def test_change_password_other_user(test_client: AsyncClient, authenticated_headers: dict, admin_user: User):
    """Test user cannot change other users' passwords."""
    response = await test_client.put(
        f"/api/users/{admin_user.id}/password",
        json={
            "old_password": "adminpass123",
            "new_password": "hacked123"
        },
        cookies=authenticated_headers
    )

    assert response.status_code == 403
    assert "Cannot change other users' passwords" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_can_change_other_password(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test admin can change other users' passwords without old password."""
    response = await test_client.put(
        f"/api/users/{test_user.id}/password",
        json={
            "new_password": "admin_reset_pass123"
        },
        cookies=admin_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Password updated successfully"

    # Verify new password works
    login_response = await test_client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "admin_reset_pass123"
        }
    )
    assert login_response.status_code == 200


@pytest.mark.asyncio
async def test_multi_tenant_isolation_list(test_client: AsyncClient, admin_headers: dict):
    """Test users from different tenants are isolated."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Create users in different tenant
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        other_user = User(
            username="othertenant1",
            password_hash=bcrypt.hash("pass123"),
            email="other1@example.com",
            role="developer",
            tenant_key="other_tenant",
            is_active=True
        )
        session.add(other_user)
        await session.commit()
        break

    # List users - should only see users from 'default' tenant
    response = await test_client.get("/api/users/", cookies=admin_headers)
    assert response.status_code == 200
    data = response.json()

    # All returned users should be from default tenant
    for user in data:
        assert user["tenant_key"] == "default"

    # Should not see other_tenant users
    usernames = [u["username"] for u in data]
    assert "othertenant1" not in usernames


@pytest.mark.asyncio
async def test_require_authentication(test_client: AsyncClient):
    """Test all user endpoints require authentication (no localhost bypass)."""
    # List users
    response = await test_client.get("/api/users/")
    assert response.status_code == 401

    # Get user
    fake_id = uuid4()
    response = await test_client.get(f"/api/users/{fake_id}")
    assert response.status_code == 401

    # Create user
    response = await test_client.post("/api/users/", json={"username": "test"})
    assert response.status_code == 401

    # Update user
    response = await test_client.put(f"/api/users/{fake_id}", json={"email": "test@example.com"})
    assert response.status_code == 401

    # Delete user
    response = await test_client.delete(f"/api/users/{fake_id}")
    assert response.status_code == 401

    # Change role
    response = await test_client.put(f"/api/users/{fake_id}/role", json={"role": "admin"})
    assert response.status_code == 401


# Fixtures - same pattern as test_auth_endpoints.py

@pytest_asyncio.fixture
async def test_client():
    """Create async HTTP client for testing user endpoints with proper database dependency override."""
    from httpx import AsyncClient, ASGITransport
    from api.app import app
    from src.giljo_mcp.database import DatabaseManager
    from src.giljo_mcp.auth.dependencies import get_db_session
    from tests.helpers.test_db_helper import PostgreSQLTestHelper
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy import text

    # Ensure test database exists
    await PostgreSQLTestHelper.ensure_test_database_exists()

    # Create test database manager
    db_url = PostgreSQLTestHelper.get_test_db_url()
    test_db_manager = DatabaseManager(db_url, is_async=True)

    # Create tables
    await PostgreSQLTestHelper.create_test_tables(test_db_manager)

    # Clean all test data before each test
    async with test_db_manager.get_session_async() as session:
        await session.execute(text("TRUNCATE TABLE api_keys, users RESTART IDENTITY CASCADE"))
        await session.commit()

    # Override get_db_session dependency to use test database
    async def override_get_db_session():
        """Override database session to use test database"""
        async with test_db_manager.get_session_async() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    # IMPORTANT: Disable localhost bypass for tests
    # We need to patch the get_current_user to not treat test requests as localhost
    from functools import wraps
    from fastapi import Request, Cookie, Header, Depends
    from typing import Optional
    from sqlalchemy.ext.asyncio import AsyncSession

    import src.giljo_mcp.auth.dependencies

    original_code = src.giljo_mcp.auth.dependencies.get_current_user

    async def patched_get_current_user(
        request: Request,
        access_token: Optional[str] = Cookie(None),
        x_api_key: Optional[str] = Header(None),
        db: AsyncSession = Depends(override_get_db_session)  # Use our override directly
    ):
        # Mock the client to appear as non-localhost
        if request.client:
            # Create a mock client object with non-localhost IP
            class MockClient:
                def __init__(self, original_client):
                    self.host = "192.168.1.100"  # Non-localhost IP
                    self.port = original_client.port if original_client else 12345

            # Temporarily replace client
            original_client = request.client
            request._client = MockClient(original_client)
            try:
                return await original_code(request, access_token, x_api_key, db)
            finally:
                request._client = original_client
        else:
            return await original_code(request, access_token, x_api_key, db)

    app.dependency_overrides[src.giljo_mcp.auth.dependencies.get_current_user] = patched_get_current_user

    # Create async client with a non-localhost hostname to force authentication
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver:8000") as ac:
        yield ac

    # Cleanup: clear overrides and close test database
    app.dependency_overrides.clear()
    await test_db_manager.close_async()


@pytest_asyncio.fixture
async def test_user(test_client):
    """Create a test user for authentication."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Get the overridden database session
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        user = User(
            username="testuser",
            password_hash=bcrypt.hash("testpassword123"),
            email="test@example.com",
            role="developer",
            tenant_key="default",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def admin_user(test_client):
    """Create an admin user for testing admin endpoints."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Get the overridden database session
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        user = User(
            username="admin",
            password_hash=bcrypt.hash("adminpass123"),
            email="admin@example.com",
            role="admin",
            tenant_key="default",
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def authenticated_headers(test_client: AsyncClient, test_user: User):
    """Get authenticated JWT cookie for testing protected endpoints."""
    response = await test_client.post(
        "/api/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword123"
        }
    )
    assert response.status_code == 200
    return response.cookies


@pytest_asyncio.fixture
async def admin_headers(test_client: AsyncClient, admin_user: User):
    """Get admin JWT cookie for testing admin endpoints."""
    response = await test_client.post(
        "/api/auth/login",
        json={
            "username": "admin",
            "password": "adminpass123"
        }
    )
    assert response.status_code == 200
    return response.cookies
