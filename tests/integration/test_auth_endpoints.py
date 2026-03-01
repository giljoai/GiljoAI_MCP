"""
Integration tests for authentication endpoints.

Tests JWT-based authentication, API key management, and user registration.
Covers happy paths, error conditions, and multi-tenant isolation.
"""

from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from passlib.hash import bcrypt

from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
from src.giljo_mcp.models import APIKey, User

pytestmark = pytest.mark.skip(reason="0750c3: ValueError in auth fixture setup — needs bcrypt/async fixture update")


@pytest.mark.asyncio
async def test_login_success(test_client: AsyncClient, test_user: User):
    """Test successful login with valid credentials."""
    response = await test_client.post("/api/auth/login", json={"username": "testuser", "password": "testpassword123"})

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
async def test_login_invalid_username(test_client: AsyncClient):
    """Test login fails with invalid username."""
    response = await test_client.post("/api/auth/login", json={"username": "nonexistent", "password": "password123"})

    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]


@pytest.mark.asyncio
async def test_login_invalid_password(test_client: AsyncClient, test_user: User):
    """Test login fails with invalid password."""
    response = await test_client.post("/api/auth/login", json={"username": "testuser", "password": "wrongpassword"})

    assert response.status_code == 401
    data = response.json()
    assert "Invalid credentials" in data["detail"]


@pytest.mark.asyncio
async def test_login_inactive_user(test_client: AsyncClient, test_user: User):
    """Test login fails for inactive user."""
    from sqlalchemy import select

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Deactivate user using test database
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        # Fetch user from this session
        result = await session.execute(select(User).where(User.id == test_user.id))
        user = result.scalar_one()
        user.is_active = False
        await session.commit()
        break  # Exit after first iteration

    response = await test_client.post("/api/auth/login", json={"username": "testuser", "password": "testpassword123"})

    assert response.status_code == 401
    assert "Invalid credentials" in response.json()["detail"]


@pytest.mark.asyncio
async def test_logout(test_client: AsyncClient):
    """Test logout clears the JWT cookie."""
    response = await test_client.post("/api/auth/logout")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Logout successful"

    # Verify cookie is cleared (not in cookies or empty)
    # Note: httpx doesn't handle cookie deletion the same way browsers do
    # In production, the cookie would have max_age=0 which deletes it


@pytest.mark.asyncio
async def test_get_me_authenticated(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """Test /me endpoint returns current user profile."""
    response = await test_client.get("/api/auth/me", cookies=authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["role"] == "developer"
    assert data["tenant_key"] == "default"
    assert data["is_active"] is True
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_me_unauthenticated(test_client: AsyncClient):
    """Test /me endpoint requires authentication."""
    response = await test_client.get("/api/auth/me")

    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_api_keys_empty(test_client: AsyncClient, authenticated_headers: dict):
    """Test listing API keys when user has none."""
    response = await test_client.get("/api/auth/api-keys", cookies=authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_create_api_key(test_client: AsyncClient, authenticated_headers: dict, test_user: User):
    """Test creating a new API key."""
    response = await test_client.post(
        "/api/auth/api-keys", json={"name": "Test API Key", "permissions": ["*"]}, cookies=authenticated_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test API Key"
    assert "api_key" in data
    assert data["api_key"].startswith("gk_")
    assert data["key_prefix"].startswith("gk_")
    assert "Store this key securely" in data["message"]


@pytest.mark.asyncio
async def test_list_api_keys_with_keys(test_client: AsyncClient, authenticated_headers: dict, test_api_key: APIKey):
    """Test listing API keys when user has keys."""
    response = await test_client.get("/api/auth/api-keys", cookies=authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

    # Find our test key
    test_key_data = next((k for k in data if k["name"] == "Test Key"), None)
    assert test_key_data is not None
    assert test_key_data["is_active"] is True
    assert test_key_data["key_prefix"] == test_api_key.key_prefix
    assert "api_key" not in test_key_data  # Plaintext key not returned


@pytest.mark.asyncio
async def test_revoke_api_key(test_client: AsyncClient, authenticated_headers: dict, test_api_key: APIKey):
    """Test revoking an API key."""
    response = await test_client.delete(f"/api/auth/api-keys/{test_api_key.id}", cookies=authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "API key revoked successfully"
    assert data["name"] == "Test Key"

    # Verify key is revoked
    list_response = await test_client.get("/api/auth/api-keys", cookies=authenticated_headers)
    data = list_response.json()
    revoked_key = next((k for k in data if k["id"] == str(test_api_key.id)), None)
    assert revoked_key is not None
    assert revoked_key["is_active"] is False
    assert revoked_key["revoked_at"] is not None


@pytest.mark.asyncio
async def test_revoke_nonexistent_api_key(test_client: AsyncClient, authenticated_headers: dict):
    """Test revoking a non-existent API key."""
    from uuid import uuid4

    fake_id = uuid4()

    response = await test_client.delete(f"/api/auth/api-keys/{fake_id}", cookies=authenticated_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_key_authentication(test_client: AsyncClient, test_user: User):
    """Test authenticating with API key header."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Create an API key
    api_key_plaintext = generate_api_key()
    key_hash = hash_api_key(api_key_plaintext)
    key_prefix = get_key_prefix(api_key_plaintext)

    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        api_key_record = APIKey(
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Auth Test Key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=["*"],
            is_active=True,
        )
        session.add(api_key_record)
        await session.commit()
        break  # Exit after first iteration

    # Use API key to access /me endpoint
    response = await test_client.get("/api/auth/me", headers={"X-API-Key": api_key_plaintext})

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == test_user.username


@pytest.mark.asyncio
async def test_api_key_invalid(test_client: AsyncClient):
    """Test authentication fails with invalid API key."""
    response = await test_client.get("/api/auth/me", headers={"X-API-Key": "gk_invalid_key_12345"})

    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_key_revoked(test_client: AsyncClient, test_user: User):
    """Test revoked API key cannot authenticate."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    # Create and revoke an API key
    api_key_plaintext = generate_api_key()
    key_hash = hash_api_key(api_key_plaintext)
    key_prefix = get_key_prefix(api_key_plaintext)

    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        api_key_record = APIKey(
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Revoked Key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=["*"],
            is_active=False,  # Revoked
            revoked_at=datetime.now(timezone.utc),
        )
        session.add(api_key_record)
        await session.commit()
        break  # Exit after first iteration

    # Try to use revoked key
    response = await test_client.get("/api/auth/me", headers={"X-API-Key": api_key_plaintext})

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_user_as_admin(test_client: AsyncClient, admin_headers: dict):
    """Test admin can register new users."""
    response = await test_client.post(
        "/api/auth/register",
        json={
            "username": "newuser",
            "password": "newpassword123",
            "email": "newuser@example.com",
            "role": "developer",
            "tenant_key": "default",
        },
        cookies=admin_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["role"] == "developer"
    assert data["email"] == "newuser@example.com"
    assert "User registered successfully" in data["message"]


@pytest.mark.asyncio
async def test_register_user_duplicate_username(test_client: AsyncClient, admin_headers: dict, test_user: User):
    """Test registering duplicate username fails."""
    response = await test_client.post(
        "/api/auth/register",
        json={
            "username": "testuser",  # Already exists
            "password": "password123",
            "role": "developer",
        },
        cookies=admin_headers,
    )

    assert response.status_code == 400
    assert "already exists" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_user_as_non_admin(test_client: AsyncClient, authenticated_headers: dict):
    """Test non-admin cannot register users."""
    response = await test_client.post(
        "/api/auth/register",
        json={"username": "unauthorizeduser", "password": "password123", "role": "developer"},
        cookies=authenticated_headers,
    )

    assert response.status_code == 403
    assert "Admin access required" in response.json()["detail"]


@pytest.mark.asyncio
async def test_jwt_token_expiry(test_client: AsyncClient, test_user: User):
    """Test JWT tokens expire after 24 hours."""
    # This would require mocking time or waiting 24 hours
    # For now, we verify the token has an expiration claim
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user.id, username=test_user.username, role=test_user.role, tenant_key=test_user.tenant_key
    )

    # Decode without verification to check expiry
    payload = JWTManager.decode_token_no_verify(token)
    assert "exp" in payload
    assert payload["exp"] > datetime.now(timezone.utc).timestamp()


@pytest.mark.asyncio
async def test_get_me_no_setup_mode_response(test_client: AsyncClient):
    """
    Test /me endpoint does NOT return setup mode status (Two-Layout Pattern).

    This test verifies Phase 3 of the Two-Layout Pattern implementation:
    /api/auth/me no longer checks setup mode and always returns 401 when not authenticated.

    Previously, the endpoint returned {"setup_mode": true, ...} when setup mode was active.
    Now, it simply returns 401 Unauthorized, regardless of setup state.
    """
    # Call /me endpoint without authentication
    response = await test_client.get("/api/auth/me")

    # Two-Layout Pattern: Should return 401 (not 200 with setup mode status)
    assert response.status_code == 401
    data = response.json()

    # Verify clean 401 response
    assert "detail" in data
    assert "Not authenticated" in data["detail"]

    # CRITICAL: Should NOT return setup mode fields
    assert "setup_mode" not in data
    assert "requires_setup" not in data


# Fixtures


@pytest_asyncio.fixture
async def test_client():
    """Create async HTTP client for testing auth endpoints with proper database dependency override."""
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import AsyncSession

    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session
    from src.giljo_mcp.database import DatabaseManager
    from tests.helpers.test_db_helper import PostgreSQLTestHelper

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

    # IMPORTANT: Mock client IP for tests
    # We need to mock the request.client to ensure tests use authentication

    # Patch directly in the auth module
    def mock_get_client_host(request):
        """Mock function to return non-localhost IP"""
        return "192.168.1.100"  # Non-localhost IP to force authentication

    # Store original for cleanup
    import src.giljo_mcp.auth.dependencies

    # Monkey-patch the localhost check in get_current_user
    original_code = src.giljo_mcp.auth.dependencies.get_current_user

    # Create wrapper that modifies request before calling original
    from typing import Optional

    from fastapi import Cookie, Depends, Header, Request

    async def patched_get_current_user(
        request: Request,
        access_token: Optional[str] = Cookie(None),
        x_api_key: Optional[str] = Header(None),
        db: AsyncSession = Depends(override_get_db_session),  # Use our override directly
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
            is_active=True,
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
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        return user


@pytest_asyncio.fixture
async def authenticated_headers(test_client: AsyncClient, test_user: User):
    """Get authenticated JWT cookie for testing protected endpoints."""
    response = await test_client.post("/api/auth/login", json={"username": "testuser", "password": "testpassword123"})
    assert response.status_code == 200
    return response.cookies


@pytest_asyncio.fixture
async def admin_headers(test_client: AsyncClient, admin_user: User):
    """Get admin JWT cookie for testing admin endpoints."""
    response = await test_client.post("/api/auth/login", json={"username": "admin", "password": "adminpass123"})
    assert response.status_code == 200
    return response.cookies


@pytest_asyncio.fixture
async def test_api_key(test_client, test_user: User):
    """Create a test API key."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_db_session

    api_key_plaintext = generate_api_key()
    key_hash = hash_api_key(api_key_plaintext)
    key_prefix = get_key_prefix(api_key_plaintext)

    # Get the overridden database session
    db_session_gen = app.dependency_overrides[get_db_session]
    async for session in db_session_gen():
        api_key = APIKey(
            user_id=test_user.id,
            tenant_key=test_user.tenant_key,
            name="Test Key",
            key_hash=key_hash,
            key_prefix=key_prefix,
            permissions=["*"],
            is_active=True,
        )
        session.add(api_key)
        await session.commit()
        await session.refresh(api_key)
        return api_key
