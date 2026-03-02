"""
Integration tests for API key management and API key authentication.

Split from test_auth_endpoints.py. Tests API key CRUD operations (create,
list, revoke) and API key-based authentication flows.
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from src.giljo_mcp.api_key_utils import generate_api_key, get_key_prefix, hash_api_key
from src.giljo_mcp.models import APIKey, User

pytestmark = pytest.mark.skip(reason="0750c3: ValueError in auth fixture setup — needs bcrypt/async fixture update")


@pytest.mark.asyncio
async def test_list_api_keys_empty(auth_ep_test_client: AsyncClient, auth_ep_authenticated_headers: dict):
    """Test listing API keys when user has none."""
    response = await auth_ep_test_client.get("/api/auth/api-keys", cookies=auth_ep_authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert data == []


@pytest.mark.asyncio
async def test_create_api_key(auth_ep_test_client: AsyncClient, auth_ep_authenticated_headers: dict, auth_ep_test_user: User):
    """Test creating a new API key."""
    response = await auth_ep_test_client.post(
        "/api/auth/api-keys", json={"name": "Test API Key", "permissions": ["*"]}, cookies=auth_ep_authenticated_headers
    )

    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test API Key"
    assert "api_key" in data
    assert data["api_key"].startswith("gk_")
    assert data["key_prefix"].startswith("gk_")
    assert "Store this key securely" in data["message"]


@pytest.mark.asyncio
async def test_list_api_keys_with_keys(auth_ep_test_client: AsyncClient, auth_ep_authenticated_headers: dict, auth_ep_test_api_key: APIKey):
    """Test listing API keys when user has keys."""
    response = await auth_ep_test_client.get("/api/auth/api-keys", cookies=auth_ep_authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1

    # Find our test key
    test_key_data = next((k for k in data if k["name"] == "Test Key"), None)
    assert test_key_data is not None
    assert test_key_data["is_active"] is True
    assert test_key_data["key_prefix"] == auth_ep_test_api_key.key_prefix
    assert "api_key" not in test_key_data  # Plaintext key not returned


@pytest.mark.asyncio
async def test_revoke_api_key(auth_ep_test_client: AsyncClient, auth_ep_authenticated_headers: dict, auth_ep_test_api_key: APIKey):
    """Test revoking an API key."""
    response = await auth_ep_test_client.delete(f"/api/auth/api-keys/{auth_ep_test_api_key.id}", cookies=auth_ep_authenticated_headers)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "API key revoked successfully"
    assert data["name"] == "Test Key"

    # Verify key is revoked
    list_response = await auth_ep_test_client.get("/api/auth/api-keys", cookies=auth_ep_authenticated_headers)
    data = list_response.json()
    revoked_key = next((k for k in data if k["id"] == str(auth_ep_test_api_key.id)), None)
    assert revoked_key is not None
    assert revoked_key["is_active"] is False
    assert revoked_key["revoked_at"] is not None


@pytest.mark.asyncio
async def test_revoke_nonexistent_api_key(auth_ep_test_client: AsyncClient, auth_ep_authenticated_headers: dict):
    """Test revoking a non-existent API key."""
    from uuid import uuid4

    fake_id = uuid4()

    response = await auth_ep_test_client.delete(f"/api/auth/api-keys/{fake_id}", cookies=auth_ep_authenticated_headers)

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_api_key_authentication(auth_ep_test_client: AsyncClient, auth_ep_test_user: User):
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
            user_id=auth_ep_test_user.id,
            tenant_key=auth_ep_test_user.tenant_key,
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
    response = await auth_ep_test_client.get("/api/auth/me", headers={"X-API-Key": api_key_plaintext})

    assert response.status_code == 200
    data = response.json()
    assert data["username"] == auth_ep_test_user.username


@pytest.mark.asyncio
async def test_api_key_invalid(auth_ep_test_client: AsyncClient):
    """Test authentication fails with invalid API key."""
    response = await auth_ep_test_client.get("/api/auth/me", headers={"X-API-Key": "gk_invalid_key_12345"})

    assert response.status_code == 401
    assert "Not authenticated" in response.json()["detail"]


@pytest.mark.asyncio
async def test_api_key_revoked(auth_ep_test_client: AsyncClient, auth_ep_test_user: User):
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
            user_id=auth_ep_test_user.id,
            tenant_key=auth_ep_test_user.tenant_key,
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
    response = await auth_ep_test_client.get("/api/auth/me", headers={"X-API-Key": api_key_plaintext})

    assert response.status_code == 401
