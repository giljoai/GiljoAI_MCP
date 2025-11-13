"""
Integration tests for settings endpoints.

Tests cover:
- GET /api/v1/settings/general (get general settings)
- PUT /api/v1/settings/general (update general settings)
- GET /api/v1/settings/network (get network settings)
- PUT /api/v1/settings/network (update network settings)
- GET /api/v1/settings/database (get database settings)
- GET /api/v1/settings/product-info (get product information)
- GET /api/v1/settings/cookie-domain (get cookie domain config)

Test scenarios:
- Happy path (successful CRUD operations)
- Admin authorization enforcement (PUT requires admin)
- Multi-tenant isolation
- Upsert behavior (create if not exists, update if exists)
- Read-only endpoints (product-info, cookie-domain)
- Empty settings handling

Handover 0506: Settings endpoints implementation.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# Fixtures

@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create admin user for testing."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User

    admin = User(
        username="test_admin_settings",
        password_hash=bcrypt.hash("admin_password"),
        email="admin_settings@test.com",
        role="admin",
        tenant_key="test_tenant_settings",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest.fixture
async def regular_user(db_session: AsyncSession):
    """Create regular (non-admin) user for testing."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User

    user = User(
        username="test_user_settings",
        password_hash=bcrypt.hash("user_password"),
        email="user_settings@test.com",
        role="developer",
        tenant_key="test_tenant_settings",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
async def admin_token(api_client: AsyncClient, admin_user):
    """Get JWT token for admin user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": "test_admin_settings", "password": "admin_password"}
    )
    assert response.status_code == 200

    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


@pytest.fixture
async def regular_token(api_client: AsyncClient, regular_user):
    """Get JWT token for regular user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": "test_user_settings", "password": "user_password"}
    )
    assert response.status_code == 200

    cookies = response.cookies
    access_token = cookies.get("access_token")
    assert access_token is not None

    return access_token


# Tests: General Settings

@pytest.mark.asyncio
async def test_get_general_settings_empty(api_client: AsyncClient, admin_token: str):
    """Test GET /api/v1/settings/general returns empty dict when not configured."""
    response = await api_client.get(
        "/api/v1/settings/general",
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "settings" in data
    assert data["settings"] == {}


@pytest.mark.asyncio
async def test_update_general_settings(api_client: AsyncClient, admin_token: str):
    """Test PUT /api/v1/settings/general creates new settings."""
    settings_data = {
        "theme": "dark",
        "locale": "en-US",
        "notifications": True
    }

    response = await api_client.put(
        "/api/v1/settings/general",
        json={"settings": settings_data},
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["settings"] == settings_data
    assert "message" in data


@pytest.mark.asyncio
async def test_get_general_settings_after_update(api_client: AsyncClient, admin_token: str):
    """Test GET /api/v1/settings/general returns saved settings."""
    # First create settings
    settings_data = {"theme": "light", "locale": "fr-FR"}
    await api_client.put(
        "/api/v1/settings/general",
        json={"settings": settings_data},
        cookies={"access_token": admin_token}
    )

    # Then retrieve them
    response = await api_client.get(
        "/api/v1/settings/general",
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["settings"] == settings_data


@pytest.mark.asyncio
async def test_update_general_settings_upsert(api_client: AsyncClient, admin_token: str):
    """Test PUT /api/v1/settings/general updates existing settings (upsert)."""
    # Create initial settings
    initial_settings = {"theme": "dark"}
    await api_client.put(
        "/api/v1/settings/general",
        json={"settings": initial_settings},
        cookies={"access_token": admin_token}
    )

    # Update settings
    updated_settings = {"theme": "light", "locale": "en-US"}
    response = await api_client.put(
        "/api/v1/settings/general",
        json={"settings": updated_settings},
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["settings"] == updated_settings


@pytest.mark.asyncio
async def test_update_general_settings_requires_admin(
    api_client: AsyncClient,
    regular_token: str
):
    """Test PUT /api/v1/settings/general requires admin role."""
    response = await api_client.put(
        "/api/v1/settings/general",
        json={"settings": {"theme": "dark"}},
        cookies={"access_token": regular_token}
    )

    assert response.status_code == 403


# Tests: Network Settings

@pytest.mark.asyncio
async def test_get_network_settings(api_client: AsyncClient, admin_token: str):
    """Test GET /api/v1/settings/network."""
    response = await api_client.get(
        "/api/v1/settings/network",
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "settings" in data


@pytest.mark.asyncio
async def test_update_network_settings(api_client: AsyncClient, admin_token: str):
    """Test PUT /api/v1/settings/network."""
    settings_data = {
        "cookie_domain": "example.com",
        "cookie_secure": True,
        "cookie_same_site": "strict"
    }

    response = await api_client.put(
        "/api/v1/settings/network",
        json={"settings": settings_data},
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["settings"] == settings_data


@pytest.mark.asyncio
async def test_update_network_settings_requires_admin(
    api_client: AsyncClient,
    regular_token: str
):
    """Test PUT /api/v1/settings/network requires admin role."""
    response = await api_client.put(
        "/api/v1/settings/network",
        json={"settings": {"cookie_domain": "test.com"}},
        cookies={"access_token": regular_token}
    )

    assert response.status_code == 403


# Tests: Database Settings

@pytest.mark.asyncio
async def test_get_database_settings(api_client: AsyncClient, admin_token: str):
    """Test GET /api/v1/settings/database (read-only)."""
    response = await api_client.get(
        "/api/v1/settings/database",
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "settings" in data


# Tests: Product Info

@pytest.mark.asyncio
async def test_get_product_info(api_client: AsyncClient, admin_token: str):
    """Test GET /api/v1/settings/product-info returns version data."""
    response = await api_client.get(
        "/api/v1/settings/product-info",
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "product" in data
    assert "version" in data
    assert "build" in data
    assert "python_version" in data
    assert "database" in data
    assert "features" in data
    assert isinstance(data["features"], list)


@pytest.mark.asyncio
async def test_get_product_info_accessible_to_regular_user(
    api_client: AsyncClient,
    regular_token: str
):
    """Test GET /api/v1/settings/product-info accessible to non-admin users."""
    response = await api_client.get(
        "/api/v1/settings/product-info",
        cookies={"access_token": regular_token}
    )

    assert response.status_code == 200


# Tests: Cookie Domain

@pytest.mark.asyncio
async def test_get_cookie_domain_defaults(api_client: AsyncClient, admin_token: str):
    """Test GET /api/v1/settings/cookie-domain returns defaults when network not configured."""
    response = await api_client.get(
        "/api/v1/settings/cookie-domain",
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert "cookie_domain" in data
    assert "secure" in data
    assert "same_site" in data
    assert data["secure"] is True  # Default secure
    assert data["same_site"] == "lax"  # Default same_site


@pytest.mark.asyncio
async def test_get_cookie_domain_from_network_settings(
    api_client: AsyncClient,
    admin_token: str
):
    """Test GET /api/v1/settings/cookie-domain reads from network settings."""
    # Set network settings with cookie config
    network_settings = {
        "cookie_domain": "test.example.com",
        "cookie_secure": False,
        "cookie_same_site": "none"
    }
    await api_client.put(
        "/api/v1/settings/network",
        json={"settings": network_settings},
        cookies={"access_token": admin_token}
    )

    # Get cookie domain config
    response = await api_client.get(
        "/api/v1/settings/cookie-domain",
        cookies={"access_token": admin_token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["cookie_domain"] == "test.example.com"
    assert data["secure"] is False
    assert data["same_site"] == "none"


# Tests: Authentication

@pytest.mark.asyncio
async def test_get_settings_requires_auth(api_client: AsyncClient):
    """Test all GET endpoints require authentication."""
    endpoints = [
        "/api/v1/settings/general",
        "/api/v1/settings/network",
        "/api/v1/settings/database",
        "/api/v1/settings/product-info",
        "/api/v1/settings/cookie-domain",
    ]

    for endpoint in endpoints:
        response = await api_client.get(endpoint)
        assert response.status_code == 401, f"{endpoint} should require auth"


# Tests: Multi-tenant Isolation

@pytest.mark.asyncio
async def test_multi_tenant_isolation(api_client: AsyncClient, db_session: AsyncSession):
    """Test settings are isolated per tenant."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User

    # Create users in different tenants
    tenant1_admin = User(
        username="tenant1_admin",
        password_hash=bcrypt.hash("password"),
        email="tenant1@test.com",
        role="admin",
        tenant_key="tenant1",
        is_active=True,
    )
    tenant2_admin = User(
        username="tenant2_admin",
        password_hash=bcrypt.hash("password"),
        email="tenant2@test.com",
        role="admin",
        tenant_key="tenant2",
        is_active=True,
    )
    db_session.add(tenant1_admin)
    db_session.add(tenant2_admin)
    await db_session.commit()

    # Login as tenant1 admin
    response1 = await api_client.post(
        "/api/auth/login",
        json={"username": "tenant1_admin", "password": "password"}
    )
    token1 = response1.cookies.get("access_token")

    # Login as tenant2 admin
    response2 = await api_client.post(
        "/api/auth/login",
        json={"username": "tenant2_admin", "password": "password"}
    )
    token2 = response2.cookies.get("access_token")

    # Set settings for tenant1
    await api_client.put(
        "/api/v1/settings/general",
        json={"settings": {"theme": "dark"}},
        cookies={"access_token": token1}
    )

    # Set settings for tenant2
    await api_client.put(
        "/api/v1/settings/general",
        json={"settings": {"theme": "light"}},
        cookies={"access_token": token2}
    )

    # Verify tenant1 sees only their settings
    response1 = await api_client.get(
        "/api/v1/settings/general",
        cookies={"access_token": token1}
    )
    assert response1.json()["settings"]["theme"] == "dark"

    # Verify tenant2 sees only their settings
    response2 = await api_client.get(
        "/api/v1/settings/general",
        cookies={"access_token": token2}
    )
    assert response2.json()["settings"]["theme"] == "light"
