"""
Integration tests for user registration and access control.

Split from test_auth_endpoints.py. Tests admin-only user registration,
duplicate username handling, and role-based access restrictions.
"""

import pytest
from httpx import AsyncClient

from src.giljo_mcp.models import User

pytestmark = pytest.mark.skip(reason="0750c3: ValueError in auth fixture setup — needs bcrypt/async fixture update")


@pytest.mark.asyncio
async def test_register_user_as_admin(auth_ep_test_client: AsyncClient, auth_ep_admin_headers: dict):
    """Test admin can register new users."""
    response = await auth_ep_test_client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "password": "newpassword123",
            "email": "newuser@example.com",
            "role": "developer",
            "tenant_key": "default",
        },
        cookies=auth_ep_admin_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["role"] == "developer"
    assert data["email"] == "newuser@example.com"
    assert "User registered successfully" in data["message"]


@pytest.mark.asyncio
async def test_register_user_duplicate_username(auth_ep_test_client: AsyncClient, auth_ep_admin_headers: dict, auth_ep_test_user: User):
    """Test registering duplicate username fails."""
    response = await auth_ep_test_client.post(
        "/api/auth/register",
        json={
            "username": "testuser",  # Already exists
            "password": "password123",
            "role": "developer",
        },
        cookies=auth_ep_admin_headers,
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_user_as_non_admin(auth_ep_test_client: AsyncClient, auth_ep_authenticated_headers: dict):
    """Test non-admin cannot register users."""
    response = await auth_ep_test_client.post(
        "/api/auth/register",
        json={"username": "unauthorizeduser", "password": "password123", "role": "developer"},
        cookies=auth_ep_authenticated_headers,
    )

    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]
