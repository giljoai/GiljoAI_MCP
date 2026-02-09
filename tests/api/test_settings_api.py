"""
Settings API Integration Tests - Handover 0614

Comprehensive validation of all 7 settings endpoints:
- GET /settings/general - Get general settings
- PUT /settings/general - Update general settings (admin only)
- GET /settings/network - Get network settings
- PUT /settings/network - Update network settings (admin only)
- GET /settings/database - Get database settings (read-only)
- GET /settings/product-info - Get product info
- GET /settings/cookie-domain - Get cookie domain config

Test Coverage:
- Happy path scenarios (200 responses)
- Authentication enforcement (401 Unauthorized)
- Authorization enforcement (403 Forbidden for non-admin)
- Multi-tenant isolation (zero cross-tenant leakage)
- Validation errors (400 Bad Request)
- Response schema validation

Phase 2 Progress: API Layer Testing (6/10 groups)
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# FIXTURES - Test Users and Authentication
# ============================================================================


@pytest.fixture
async def admin_user(db_manager):
    """Create admin user for admin-only endpoint testing."""
    from uuid import uuid4

    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"admin_settings_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"admin_tenant_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create organization first (0424j: org_id is NOT NULL)
        org = Organization(
            name=f"Admin Settings Org {unique_id}",
            slug=f"admin-settings-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("admin_password"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # Required NOT NULL (0424j)
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "admin_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def developer_user(db_manager):
    """Create developer user for non-admin access testing."""
    from uuid import uuid4

    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"dev_settings_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"dev_tenant_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create organization first (0424j: org_id is NOT NULL)
        org = Organization(
            name=f"Dev Settings Org {unique_id}",
            slug=f"dev-settings-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("dev_password"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # Required NOT NULL (0424j)
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "dev_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_b_admin(db_manager):
    """Create Tenant B admin for multi-tenant isolation testing."""
    from uuid import uuid4

    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_b_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create organization first (0424j: org_id is NOT NULL)
        org = Organization(
            name=f"Tenant B Org {unique_id}",
            slug=f"tenant-b-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("admin_b_password"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # Required NOT NULL (0424j)
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "admin_b_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def admin_token(api_client: AsyncClient, admin_user):
    """Get JWT token for admin user."""
    response = await api_client.post(
        "/api/auth/login", json={"username": admin_user._test_username, "password": admin_user._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def developer_token(api_client: AsyncClient, developer_user):
    """Get JWT token for developer user."""
    response = await api_client.post(
        "/api/auth/login", json={"username": developer_user._test_username, "password": developer_user._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_b_admin_token(api_client: AsyncClient, tenant_b_admin):
    """Get JWT token for Tenant B admin."""
    response = await api_client.post(
        "/api/auth/login", json={"username": tenant_b_admin._test_username, "password": tenant_b_admin._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


# ============================================================================
# GENERAL SETTINGS TESTS
# ============================================================================


class TestGeneralSettings:
    """Test general settings endpoints (GET/PUT /settings/general)"""

    @pytest.mark.asyncio
    async def test_get_general_settings_happy_path(self, api_client: AsyncClient, admin_token: str):
        """Test GET /api/v1/settings/general - Get general settings successfully."""
        response = await api_client.get("/api/v1/settings/general", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "settings" in data
        assert isinstance(data["settings"], dict)

    @pytest.mark.asyncio
    async def test_get_general_settings_developer_access(self, api_client: AsyncClient, developer_token: str):
        """Test GET /api/settings/general - Developers can read settings."""
        response = await api_client.get("/api/v1/settings/general", cookies={"access_token": developer_token})

        assert response.status_code == 200
        data = response.json()
        assert "settings" in data

    @pytest.mark.asyncio
    async def test_get_general_settings_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/settings/general - 401 without authentication."""
        response = await api_client.get("/api/v1/settings/general")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_general_settings_happy_path(self, api_client: AsyncClient, admin_token: str):
        """Test PUT /api/settings/general - Update settings successfully (admin only)."""
        response = await api_client.put(
            "/api/v1/settings/general",
            json={"settings": {"theme": "dark", "language": "en", "notifications_enabled": True}},
            cookies={"access_token": admin_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "settings" in data
        assert "message" in data
        assert data["settings"]["theme"] == "dark"
        assert data["settings"]["language"] == "en"
        assert data["settings"]["notifications_enabled"] is True
        assert "Settings updated successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_update_general_settings_verify_persistence(self, api_client: AsyncClient, admin_token: str):
        """Test PUT /api/settings/general - Verify settings persist across requests."""
        # Update settings
        update_data = {"settings": {"test_key": "test_value", "numeric_value": 42}}
        update_response = await api_client.put(
            "/api/v1/settings/general", json=update_data, cookies={"access_token": admin_token}
        )
        assert update_response.status_code == 200

        # Retrieve settings and verify
        get_response = await api_client.get("/api/v1/settings/general", cookies={"access_token": admin_token})
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["settings"]["test_key"] == "test_value"
        assert data["settings"]["numeric_value"] == 42

    @pytest.mark.asyncio
    async def test_update_general_settings_forbidden_non_admin(self, api_client: AsyncClient, developer_token: str):
        """Test PUT /api/settings/general - 403 for non-admin users."""
        response = await api_client.put(
            "/api/v1/settings/general", json={"settings": {"theme": "dark"}}, cookies={"access_token": developer_token}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_general_settings_unauthorized(self, api_client: AsyncClient):
        """Test PUT /api/settings/general - 401 without authentication."""
        response = await api_client.put("/api/v1/settings/general", json={"settings": {"theme": "dark"}})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_general_settings_missing_settings_key(self, api_client: AsyncClient, admin_token: str):
        """Test PUT /api/settings/general - 422 when settings key missing."""
        response = await api_client.put(
            "/api/v1/settings/general",
            json={"theme": "dark"},  # Missing "settings" wrapper
            cookies={"access_token": admin_token},
        )
        assert response.status_code == 422  # Pydantic validation error


# ============================================================================
# NETWORK SETTINGS TESTS
# ============================================================================


class TestNetworkSettings:
    """Test network settings endpoints (GET/PUT /settings/network)"""

    @pytest.mark.asyncio
    async def test_get_network_settings_happy_path(self, api_client: AsyncClient, admin_token: str):
        """Test GET /api/settings/network - Get network settings successfully."""
        response = await api_client.get("/api/v1/settings/network", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert isinstance(data["settings"], dict)

    @pytest.mark.asyncio
    async def test_get_network_settings_developer_access(self, api_client: AsyncClient, developer_token: str):
        """Test GET /api/settings/network - Developers can read network settings."""
        response = await api_client.get("/api/v1/settings/network", cookies={"access_token": developer_token})

        assert response.status_code == 200
        data = response.json()
        assert "settings" in data

    @pytest.mark.asyncio
    async def test_get_network_settings_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/settings/network - 401 without authentication."""
        response = await api_client.get("/api/v1/settings/network")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_network_settings_happy_path(self, api_client: AsyncClient, admin_token: str):
        """Test PUT /api/settings/network - Update network settings (admin only)."""
        response = await api_client.put(
            "/api/v1/settings/network",
            json={
                "settings": {
                    "api_host": "0.0.0.0",
                    "api_port": 7272,
                    "cookie_domain": "localhost",
                    "cookie_secure": True,
                    "cookie_same_site": "lax",
                }
            },
            cookies={"access_token": admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert "message" in data
        assert data["settings"]["api_host"] == "0.0.0.0"
        assert data["settings"]["api_port"] == 7272
        assert "Network settings updated successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_update_network_settings_verify_persistence(self, api_client: AsyncClient, admin_token: str):
        """Test PUT /api/settings/network - Verify persistence."""
        # Update settings
        update_data = {"settings": {"custom_network_key": "custom_value", "port": 9999}}
        update_response = await api_client.put(
            "/api/v1/settings/network", json=update_data, cookies={"access_token": admin_token}
        )
        assert update_response.status_code == 200

        # Retrieve and verify
        get_response = await api_client.get("/api/v1/settings/network", cookies={"access_token": admin_token})
        assert get_response.status_code == 200
        data = get_response.json()
        assert data["settings"]["custom_network_key"] == "custom_value"
        assert data["settings"]["port"] == 9999

    @pytest.mark.asyncio
    async def test_update_network_settings_forbidden_non_admin(self, api_client: AsyncClient, developer_token: str):
        """Test PUT /api/settings/network - 403 for non-admin users."""
        response = await api_client.put(
            "/api/v1/settings/network", json={"settings": {"api_port": 8080}}, cookies={"access_token": developer_token}
        )
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_update_network_settings_unauthorized(self, api_client: AsyncClient):
        """Test PUT /api/settings/network - 401 without authentication."""
        response = await api_client.put("/api/v1/settings/network", json={"settings": {"api_port": 8080}})
        assert response.status_code == 401


# ============================================================================
# DATABASE SETTINGS TESTS
# ============================================================================


class TestDatabaseSettings:
    """Test database settings endpoint (GET /settings/database - read-only)"""

    @pytest.mark.asyncio
    async def test_get_database_settings_happy_path(self, api_client: AsyncClient, admin_token: str):
        """Test GET /api/settings/database - Get database settings (read-only)."""
        response = await api_client.get("/api/v1/settings/database", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()
        assert "settings" in data
        assert isinstance(data["settings"], dict)

    @pytest.mark.asyncio
    async def test_get_database_settings_developer_access(self, api_client: AsyncClient, developer_token: str):
        """Test GET /api/settings/database - Developers can read database settings."""
        response = await api_client.get("/api/v1/settings/database", cookies={"access_token": developer_token})

        assert response.status_code == 200
        data = response.json()
        assert "settings" in data

    @pytest.mark.asyncio
    async def test_get_database_settings_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/settings/database - 401 without authentication."""
        response = await api_client.get("/api/v1/settings/database")
        assert response.status_code == 401


# ============================================================================
# PRODUCT INFO TESTS
# ============================================================================


class TestProductInfo:
    """Test product info endpoint (GET /settings/product-info)"""

    @pytest.mark.asyncio
    async def test_get_product_info_happy_path(self, api_client: AsyncClient, admin_token: str):
        """Test GET /api/settings/product-info - Get static product information."""
        response = await api_client.get("/api/v1/settings/product-info", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "product" in data
        assert "version" in data
        assert "build" in data
        assert "python_version" in data
        assert "database" in data
        assert "features" in data

        # Validate expected values
        assert data["product"] == "GiljoAI MCP Server"
        assert data["version"] == "3.1.0"
        assert data["build"] == "production"
        assert data["python_version"] == "3.11+"
        assert data["database"] == "PostgreSQL 14+"
        assert isinstance(data["features"], list)
        assert len(data["features"]) > 0

    @pytest.mark.asyncio
    async def test_get_product_info_developer_access(self, api_client: AsyncClient, developer_token: str):
        """Test GET /api/settings/product-info - Accessible to all users."""
        response = await api_client.get("/api/v1/settings/product-info", cookies={"access_token": developer_token})

        assert response.status_code == 200
        data = response.json()
        assert data["product"] == "GiljoAI MCP Server"

    @pytest.mark.asyncio
    async def test_get_product_info_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/settings/product-info - 401 without authentication."""
        response = await api_client.get("/api/v1/settings/product-info")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_product_info_features_list(self, api_client: AsyncClient, admin_token: str):
        """Test GET /api/settings/product-info - Verify features list content."""
        response = await api_client.get("/api/v1/settings/product-info", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()
        features = data["features"]

        # Verify expected features are present
        assert "Multi-tenant orchestration" in features
        assert "context prioritization and orchestration" in features
        assert "Orchestrator succession" in features
        assert "Agent template management" in features


# ============================================================================
# COOKIE DOMAIN TESTS
# ============================================================================


class TestCookieDomain:
    """Test cookie domain endpoint (GET /settings/cookie-domain)"""

    @pytest.mark.asyncio
    async def test_get_cookie_domain_happy_path(self, api_client: AsyncClient, admin_token: str):
        """Test GET /api/settings/cookie-domain - Get cookie configuration."""
        response = await api_client.get("/api/v1/settings/cookie-domain", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "cookie_domain" in data
        assert "secure" in data
        assert "same_site" in data

        # Validate types
        assert isinstance(data["secure"], bool)
        assert isinstance(data["same_site"], str)

    @pytest.mark.asyncio
    async def test_get_cookie_domain_with_network_settings(self, api_client: AsyncClient, admin_token: str):
        """Test GET /api/settings/cookie-domain - Reads from network settings."""
        # First, set network settings with cookie config
        await api_client.put(
            "/api/v1/settings/network",
            json={"settings": {"cookie_domain": "example.com", "cookie_secure": True, "cookie_same_site": "strict"}},
            cookies={"access_token": admin_token},
        )

        # Retrieve cookie domain config
        response = await api_client.get("/api/v1/settings/cookie-domain", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()
        assert data["cookie_domain"] == "example.com"
        assert data["secure"] is True
        assert data["same_site"] == "strict"

    @pytest.mark.asyncio
    async def test_get_cookie_domain_defaults(self, api_client: AsyncClient, admin_token: str):
        """Test GET /api/settings/cookie-domain - Default values when not configured."""
        response = await api_client.get("/api/v1/settings/cookie-domain", cookies={"access_token": admin_token})

        assert response.status_code == 200
        data = response.json()

        # When not configured, should use defaults
        # secure defaults to True, same_site defaults to "lax"
        assert data["secure"] is True
        assert data["same_site"] == "lax"

    @pytest.mark.asyncio
    async def test_get_cookie_domain_developer_access(self, api_client: AsyncClient, developer_token: str):
        """Test GET /api/settings/cookie-domain - Accessible to all users."""
        response = await api_client.get("/api/v1/settings/cookie-domain", cookies={"access_token": developer_token})

        assert response.status_code == 200
        data = response.json()
        assert "cookie_domain" in data
        assert "secure" in data
        assert "same_site" in data

    @pytest.mark.asyncio
    async def test_get_cookie_domain_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/settings/cookie-domain - 401 without authentication."""
        response = await api_client.get("/api/v1/settings/cookie-domain")
        assert response.status_code == 401


# ============================================================================
# MULTI-TENANT ISOLATION TESTS
# ============================================================================


class TestMultiTenantIsolation:
    """Comprehensive multi-tenant isolation verification for settings"""

    @pytest.mark.asyncio
    async def test_general_settings_tenant_isolation(
        self, api_client: AsyncClient, admin_token: str, tenant_b_admin_token: str
    ):
        """Test general settings are isolated between tenants."""
        # Tenant A sets settings
        await api_client.put(
            "/api/v1/settings/general",
            json={"settings": {"tenant_a_key": "tenant_a_value"}},
            cookies={"access_token": admin_token},
        )

        # Tenant B sets different settings
        await api_client.put(
            "/api/v1/settings/general",
            json={"settings": {"tenant_b_key": "tenant_b_value"}},
            cookies={"access_token": tenant_b_admin_token},
        )

        # Tenant A retrieves - should only see their settings
        response_a = await api_client.get("/api/v1/settings/general", cookies={"access_token": admin_token})
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert "tenant_a_key" in data_a["settings"]
        assert "tenant_b_key" not in data_a["settings"]

        # Tenant B retrieves - should only see their settings
        response_b = await api_client.get("/api/v1/settings/general", cookies={"access_token": tenant_b_admin_token})
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert "tenant_b_key" in data_b["settings"]
        assert "tenant_a_key" not in data_b["settings"]

    @pytest.mark.asyncio
    async def test_network_settings_tenant_isolation(
        self, api_client: AsyncClient, admin_token: str, tenant_b_admin_token: str
    ):
        """Test network settings are isolated between tenants."""
        # Tenant A sets network settings
        await api_client.put(
            "/api/v1/settings/network",
            json={"settings": {"tenant_a_port": 7272}},
            cookies={"access_token": admin_token},
        )

        # Tenant B sets different network settings
        await api_client.put(
            "/api/v1/settings/network",
            json={"settings": {"tenant_b_port": 8080}},
            cookies={"access_token": tenant_b_admin_token},
        )

        # Tenant A retrieves - should only see their settings
        response_a = await api_client.get("/api/v1/settings/network", cookies={"access_token": admin_token})
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert "tenant_a_port" in data_a["settings"]
        assert "tenant_b_port" not in data_a["settings"]

        # Tenant B retrieves - should only see their settings
        response_b = await api_client.get("/api/v1/settings/network", cookies={"access_token": tenant_b_admin_token})
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert "tenant_b_port" in data_b["settings"]
        assert "tenant_a_port" not in data_b["settings"]

    @pytest.mark.asyncio
    async def test_database_settings_tenant_isolation(
        self, api_client: AsyncClient, admin_token: str, tenant_b_admin_token: str
    ):
        """Test database settings are isolated between tenants."""
        # Both tenants should only see their own database settings
        response_a = await api_client.get("/api/v1/settings/database", cookies={"access_token": admin_token})
        assert response_a.status_code == 200

        response_b = await api_client.get("/api/v1/settings/database", cookies={"access_token": tenant_b_admin_token})
        assert response_b.status_code == 200

        # Settings should be tenant-scoped (may be empty, but isolated)
        data_a = response_a.json()
        data_b = response_b.json()
        assert "settings" in data_a
        assert "settings" in data_b

    @pytest.mark.asyncio
    async def test_cookie_domain_tenant_isolation(
        self, api_client: AsyncClient, admin_token: str, tenant_b_admin_token: str
    ):
        """Test cookie domain settings are isolated between tenants."""
        # Tenant A sets cookie domain via network settings
        await api_client.put(
            "/api/v1/settings/network",
            json={
                "settings": {
                    "cookie_domain": "tenant-a.example.com",
                    "cookie_secure": True,
                    "cookie_same_site": "strict",
                }
            },
            cookies={"access_token": admin_token},
        )

        # Tenant B sets different cookie domain
        await api_client.put(
            "/api/v1/settings/network",
            json={
                "settings": {"cookie_domain": "tenant-b.example.com", "cookie_secure": False, "cookie_same_site": "lax"}
            },
            cookies={"access_token": tenant_b_admin_token},
        )

        # Tenant A retrieves cookie domain
        response_a = await api_client.get("/api/v1/settings/cookie-domain", cookies={"access_token": admin_token})
        assert response_a.status_code == 200
        data_a = response_a.json()
        assert data_a["cookie_domain"] == "tenant-a.example.com"
        assert data_a["secure"] is True
        assert data_a["same_site"] == "strict"

        # Tenant B retrieves cookie domain
        response_b = await api_client.get(
            "/api/v1/settings/cookie-domain", cookies={"access_token": tenant_b_admin_token}
        )
        assert response_b.status_code == 200
        data_b = response_b.json()
        assert data_b["cookie_domain"] == "tenant-b.example.com"
        assert data_b["secure"] is False
        assert data_b["same_site"] == "lax"
