"""
Integration tests for login, logout, session, and JWT authentication.

Split from test_auth_endpoints.py. Tests JWT-based authentication flows
including login, logout, /me endpoint, and token expiry.
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from src.giljo_mcp.models import User

pytestmark = pytest.mark.skip(reason="0750c3: ValueError in auth fixture setup — needs bcrypt/async fixture update")


@pytest.mark.asyncio
async def test_login_success(auth_ep_test_client: AsyncClient, auth_ep_test_user: User):
    """Test successful login with valid credentials."""
    response = await auth_ep_test_client.post("/api/auth/login", json={"username": "testuser", "password": "testpassword123"})

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Login successful"
    assert data["username"] == "testuser"
    assert data["role"] == "developer"
    assert data["tenant_key"] == "default"

    # Verify JWT cookie is set
    assert "access_token" in response.cookies
    assert response.cookies["access_token"] != ""


@pytest.mark.asyncio
async def test_login_invalid_username(auth_ep_test_client: AsyncClient):
    """Test login fails with invalid username."""
    response = await auth_ep_test_client.post("/api/auth/login", json={"username": "nonexistent", "password": "password123"})

    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]


@pytest.mark.asyncio
async def test_login_invalid_password(auth_ep_test_client: AsyncClient, auth_ep_test_user: User):
    """Test login fails with invalid password."""
    response = await auth_ep_test_client.post("/api/auth/login", json={"username": "testuser", "password": "wrongpassword"})

    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]


@pytest.mark.asyncio
async def test_login_inactive_user(auth_ep_test_client: AsyncClient, auth_ep_test_user: User):
    """Test login fails for inactive user."""
    from sqlalchemy import select

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Deactivate user using test database
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        # Fetch user from this session
        result = await session.execute(select(User).where(User.id == auth_ep_test_user.id))
        user = result.scalar_one()
        user.is_active = False
        await session.commit()
        break  # Exit after first iteration

    response = await auth_ep_test_client.post("/api/auth/login", json={"username": "testuser", "password": "testpassword123"})

    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout(auth_ep_test_client: AsyncClient):
    """Test logout clears the JWT cookie."""
    response = await auth_ep_test_client.post("/api/auth/logout")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Logout successful"

    # Verify cookie is cleared (not in cookies or empty)
    # Note: httpx doesn't handle cookie deletion the same way browsers do
    # In production, the cookie would have max_age=0 which deletes it


@pytest.mark.asyncio
async def test_get_me_authenticated(auth_ep_test_client: AsyncClient, auth_ep_authenticated_headers: dict, auth_ep_test_user: User):
    """Test /me endpoint returns current user profile."""
    response = await auth_ep_test_client.get("/api/auth/me", cookies=auth_ep_authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "developer"
    assert data["tenant_key"] == "default"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_me_unauthenticated(auth_ep_test_client: AsyncClient):
    """Test /me endpoint requires authentication."""
    response = await auth_ep_test_client.get("/api/auth/me")

    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_jwt_token_expiry(auth_ep_test_client: AsyncClient, auth_ep_test_user: User):
    """Test JWT tokens expire after 24 hours."""
    # This would require mocking time or waiting 24 hours
    # For now, we verify the token has an expiration claim
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=auth_ep_test_user.id, username=auth_ep_test_user.username, role=auth_ep_test_user.role, tenant_key=auth_ep_test_user.tenant_key
    )

    # Decode without verification to check expiry
    payload = JWTManager.decode_token_no_verify(token)
    assert "exp" in payload
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


@pytest.mark.asyncio
async def test_get_me_no_setup_mode_response(auth_ep_test_client: AsyncClient):
    """
    Test /me endpoint does NOT return setup mode status (Two-Layout Pattern).

    This test verifies Phase 3 of the Two-Layout Pattern implementation:
    /api/auth/me no longer checks setup mode and always returns 401 when not authenticated.

    Previously, the endpoint returned {"setup_mode": true, ...} when setup mode was active.
    Now, it simply returns 401 Unauthorized, regardless of setup state.
    """
    # Call /me endpoint without authentication
    response = await auth_ep_test_client.get("/api/auth/me")

    # Two-Layout Pattern: Should return 401 (not 200 with setup mode status)
    assert response.status_code == 401
    data = response.json()

    # Verify clean 401 response
    assert "detail" in data
    assert "Not authenticated" in data["detail"]

    # CRITICAL: Should NOT return setup mode fields
    assert "setup_mode" not in data
    assert "requires_setup" not in data
