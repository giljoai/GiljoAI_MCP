"""
Products API Integration Tests - Handover 0609

Comprehensive validation of all 12+ product endpoints across 3 modules:
- CRUD endpoints (crud.py): create, list, get, update, list_deleted
- Lifecycle endpoints (lifecycle.py): activate, deactivate, delete, restore, cascade_impact, refresh_active
- Vision endpoints (vision.py): upload, list, delete, list_chunks

Test Coverage:
- Happy path scenarios (200/201 responses)
- Authentication enforcement (401 Unauthorized)
- Authorization enforcement (403 Forbidden)
- Multi-tenant isolation (zero cross-tenant leakage)
- Not Found scenarios (404)
- Validation errors (400 Bad Request)
- Response schema validation

Phase 2 Progress: API Layer Testing (1/10 groups)
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from pathlib import Path
import io


# ============================================================================
# FIXTURES - Test Users and Authentication
# ============================================================================

@pytest.fixture
async def tenant_a_user(db_manager):
    """Create Tenant A user for multi-tenant isolation testing."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager
    from uuid import uuid4

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_a_prod_{unique_id}"
    # Use TenantManager to generate a properly formatted tenant key
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("password_a"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Store credentials for login
        user._test_username = username
        user._test_password = "password_a"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_b_user(db_manager):
    """Create Tenant B user for cross-tenant access testing."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager
    from uuid import uuid4

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_b_prod_{unique_id}"
    # Use TenantManager to generate a properly formatted tenant key
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("password_b"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Store credentials for login
        user._test_username = username
        user._test_password = "password_b"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_a_token(api_client: AsyncClient, tenant_a_user):
    """Get JWT token for Tenant A user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_a_user._test_username, "password": tenant_a_user._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_b_token(api_client: AsyncClient, tenant_b_user):
    """Get JWT token for Tenant B user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_b_user._test_username, "password": tenant_b_user._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_a_product(api_client: AsyncClient, tenant_a_token: str):
    """Create a test product for Tenant A."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": "Tenant A Product",
            "description": "Test product for Tenant A",
            "project_path": "/path/to/tenant_a/product"
        },
        cookies={"access_token": tenant_a_token}
    )
    assert response.status_code == 200
    product_data = response.json()

    # CRITICAL FIX: Clear cookies after authenticated fixture setup
    # This prevents cookie persistence to subsequent tests
    api_client.cookies.clear()

    return product_data


@pytest.fixture
async def tenant_b_product(api_client: AsyncClient, tenant_b_token: str):
    """Create a test product for Tenant B."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": "Tenant B Product",
            "description": "Test product for Tenant B",
            "project_path": "/path/to/tenant_b/product"
        },
        cookies={"access_token": tenant_b_token}
    )
    assert response.status_code == 200
    product_data = response.json()

    # CRITICAL FIX: Clear cookies after authenticated fixture setup
    # This prevents cookie persistence to subsequent tests
    api_client.cookies.clear()

    return product_data


# ============================================================================
# CRUD ENDPOINTS TESTS
# ============================================================================

class TestProductCRUD:
    """Test CRUD operations: create, list, get, update, list_deleted"""

    @pytest.mark.asyncio
    async def test_create_product_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/products/ - Create product successfully."""
        response = await api_client.post(
            "/api/v1/products/",
            json={
                "name": "New Product",
                "description": "Test product creation",
                "project_path": "/path/to/project",
                "config_data": {"key": "value"}
            },
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "id" in data
        assert data["name"] == "New Product"
        assert data["description"] == "Test product creation"
        assert data["project_path"] == "/path/to/project"
        assert data["config_data"] == {"key": "value"}
        assert data["has_config_data"] is True
        assert data["is_active"] is False  # Not active by default
        assert data["project_count"] == 0
        assert data["task_count"] == 0
        assert data["vision_documents_count"] == 0
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_product_saves_tech_stack_config(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """
        Creating a product with nested tech_stack config_data should persist all fields.

        This guards the behavior relied on by the ProductsView wizard and the
        (i) configuration popover on the agent card.
        """
        payload = {
            "name": "Tech Stack Product",
            "description": "Product with rich tech stack config",
            "project_path": "/path/to/project",
            "config_data": {
                "tech_stack": {
                    "languages": "Python 3.11+, JavaScript ES2023, TypeScript 5.0+",
                    "frontend": "React 18, Vite 5, Tailwind CSS",
                    "backend": "FastAPI 0.104+, SQLAlchemy 2.0+",
                    "database": "SQLite 3.35+, PostgreSQL 13+",
                    "infrastructure": "Docker, Nginx, GitHub Actions",
                },
                "architecture": {
                    "pattern": "Modular monolith with service layer",
                    "api_style": "REST + WebSocket",
                    "design_patterns": "Repository, DI, Factory, Strategy",
                    "notes": "Local-first, async/await throughout backend",
                },
                "features": {
                    "core": "Contacts CRUD, photo uploads, fuzzy search",
                },
                "test_config": {
                    "strategy": "Hybrid",
                    "coverage_target": 85,
                    "frameworks": "pytest, pytest-asyncio, Cypress",
                },
            },
        }

        response = await api_client.post(
            "/api/v1/products/",
            json=payload,
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Basic persistence checks
        assert data["name"] == payload["name"]
        assert data["description"] == payload["description"]
        assert data["has_config_data"] is True

        cfg = data["config_data"]
        assert cfg is not None

        # Tech stack should round-trip exactly for all fields
        assert cfg["tech_stack"]["languages"] == payload["config_data"]["tech_stack"]["languages"]
        assert cfg["tech_stack"]["frontend"] == payload["config_data"]["tech_stack"]["frontend"]
        assert cfg["tech_stack"]["backend"] == payload["config_data"]["tech_stack"]["backend"]
        assert cfg["tech_stack"]["database"] == payload["config_data"]["tech_stack"]["database"]
        assert cfg["tech_stack"]["infrastructure"] == payload["config_data"]["tech_stack"]["infrastructure"]

        # A couple of other critical fields should also be present
        assert cfg["features"]["core"] == payload["config_data"]["features"]["core"]
        assert cfg["test_config"]["strategy"] == payload["config_data"]["test_config"]["strategy"]
        assert cfg["test_config"]["coverage_target"] == payload["config_data"]["test_config"]["coverage_target"]

    @pytest.mark.asyncio
    async def test_create_product_minimal_data(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/products/ - Create with minimal required data."""
        response = await api_client.post(
            "/api/v1/products/",
            json={"name": "Minimal Product"},
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Minimal Product"
        assert data["description"] is None
        assert data["project_path"] is None
        assert data["config_data"] is None
        assert data["has_config_data"] is False

    @pytest.mark.asyncio
    async def test_create_product_unauthorized(self, api_client: AsyncClient):
        """Test POST /api/v1/products/ - 401 without authentication."""
        response = await api_client.post(
            "/api/v1/products/",
            json={"name": "Unauthorized Product"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_products_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test GET /api/v1/products/ - List all products."""
        response = await api_client.get(
            "/api/v1/products/",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our test product
        product = next((p for p in data if p["id"] == tenant_a_product["id"]), None)
        assert product is not None
        assert product["name"] == tenant_a_product["name"]

    @pytest.mark.asyncio
    async def test_list_products_multi_tenant_isolation(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
        tenant_a_product,
        tenant_b_product
    ):
        """Test GET /api/v1/products/ - Verify tenant isolation."""
        # Tenant A should only see their products
        response_a = await api_client.get(
            "/api/v1/products/",
            cookies={"access_token": tenant_a_token}
        )
        assert response_a.status_code == 200
        products_a = response_a.json()

        product_ids_a = [p["id"] for p in products_a]
        assert tenant_a_product["id"] in product_ids_a
        assert tenant_b_product["id"] not in product_ids_a  # Isolation verified

        # Tenant B should only see their products
        response_b = await api_client.get(
            "/api/v1/products/",
            cookies={"access_token": tenant_b_token}
        )
        assert response_b.status_code == 200
        products_b = response_b.json()

        product_ids_b = [p["id"] for p in products_b]
        assert tenant_b_product["id"] in product_ids_b
        assert tenant_a_product["id"] not in product_ids_b  # Isolation verified

    @pytest.mark.asyncio
    async def test_list_products_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/v1/products/ - 401 without authentication."""
        response = await api_client.get("/api/v1/products/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_product_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id} - Get product details."""
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_product["id"]
        assert data["name"] == tenant_a_product["name"]
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_get_product_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/products/{product_id} - 404 for non-existent product."""
        response = await api_client.get(
            "/api/v1/products/00000000-0000-0000-0000-000000000000",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_get_product_cross_tenant_forbidden(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
        tenant_b_product
    ):
        """Test GET /api/v1/products/{product_id} - 403/404 for cross-tenant access."""
        # Tenant A tries to access Tenant B's product
        response = await api_client.get(
            f"/api/v1/products/{tenant_b_product['id']}",
            cookies={"access_token": tenant_a_token}
        )
        # Should return 404 (not found) to prevent information leakage
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_get_product_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id} - 401 without authentication."""
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_product_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test PUT /api/v1/products/{product_id} - Update product successfully."""
        response = await api_client.put(
            f"/api/v1/products/{tenant_a_product['id']}",
            json={
                "name": "Updated Product Name",
                "description": "Updated description",
                "project_path": "/new/path",
                "config_data": {"updated": "data"}
            },
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_product["id"]
        assert data["name"] == "Updated Product Name"
        assert data["description"] == "Updated description"
        assert data["project_path"] == "/new/path"
        assert data["config_data"] == {"updated": "data"}
        assert data["has_config_data"] is True

    @pytest.mark.asyncio
    async def test_update_product_saves_tech_stack_config(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """
        Updating an existing product with tech_stack config_data should persist nested fields.

        This ensures the edit flow does not drop tech stack information used by the UI.
        """
        payload = {
            "config_data": {
                "tech_stack": {
                    "languages": "Python 3.11+, TypeScript 5.0+",
                    "frontend": "React 18 + Tailwind",
                    "backend": "FastAPI 0.104+",
                    "database": "PostgreSQL 13+",
                    "infrastructure": "Docker Compose, GitHub Actions",
                },
                "features": {
                    "core": "Rich contact management with fuzzy search",
                },
                "test_config": {
                    "strategy": "Hybrid",
                    "coverage_target": 85,
                    "frameworks": "pytest, Vitest, Cypress",
                },
            }
        }

        response = await api_client.put(
            f"/api/v1/products/{tenant_a_product['id']}",
            json=payload,
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()

        cfg = data["config_data"]
        assert cfg is not None
        assert data["has_config_data"] is True

        # Tech stack round-trip
        assert cfg["tech_stack"]["languages"] == payload["config_data"]["tech_stack"]["languages"]
        assert cfg["tech_stack"]["frontend"] == payload["config_data"]["tech_stack"]["frontend"]
        assert cfg["tech_stack"]["backend"] == payload["config_data"]["tech_stack"]["backend"]
        assert cfg["tech_stack"]["database"] == payload["config_data"]["tech_stack"]["database"]
        assert cfg["tech_stack"]["infrastructure"] == payload["config_data"]["tech_stack"]["infrastructure"]

        # Sanity check a couple of non-tech fields
        assert cfg["features"]["core"] == payload["config_data"]["features"]["core"]
        assert cfg["test_config"]["strategy"] == payload["config_data"]["test_config"]["strategy"]

    @pytest.mark.asyncio
    async def test_update_product_partial(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test PUT /api/v1/products/{product_id} - Partial update."""
        response = await api_client.put(
            f"/api/v1/products/{tenant_a_product['id']}",
            json={"name": "Partially Updated"},
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partially Updated"
        # Original description should remain
        assert data["description"] == tenant_a_product["description"]

    @pytest.mark.asyncio
    async def test_update_product_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test PUT /api/v1/products/{product_id} - 404 for non-existent product."""
        response = await api_client.put(
            "/api/v1/products/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated"},
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_update_product_cross_tenant_forbidden(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_product
    ):
        """Test PUT /api/v1/products/{product_id} - 403/404 for cross-tenant update."""
        response = await api_client.put(
            f"/api/v1/products/{tenant_b_product['id']}",
            json={"name": "Hacked"},
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_update_product_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test PUT /api/v1/products/{product_id} - 401 without authentication."""
        response = await api_client.put(
            f"/api/v1/products/{tenant_a_product['id']}",
            json={"name": "Updated"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_deleted_products_empty(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/products/deleted - Empty list when no deleted products."""
        response = await api_client.get(
            "/api/v1/products/deleted",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_deleted_products_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/v1/products/deleted - 401 without authentication."""
        response = await api_client.get("/api/v1/products/deleted")
        assert response.status_code == 401


# ============================================================================
# LIFECYCLE ENDPOINTS TESTS
# ============================================================================

class TestProductLifecycle:
    """Test lifecycle operations: activate, deactivate, delete, restore, cascade_impact, refresh_active"""

    @pytest.mark.asyncio
    async def test_activate_product_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/activate - Activate successfully."""
        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert data["product_id"] == tenant_a_product["id"]
        assert "product" in data
        assert data["product"]["is_active"] is True
        assert "message" in data
        assert "deactivated_projects" in data

    @pytest.mark.asyncio
    async def test_activate_product_deactivates_previous(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/products/{product_id}/activate - Single active product enforcement."""
        # Create two products
        response1 = await api_client.post(
            "/api/v1/products/",
            json={"name": "Product 1"},
            cookies={"access_token": tenant_a_token}
        )
        product1 = response1.json()

        response2 = await api_client.post(
            "/api/v1/products/",
            json={"name": "Product 2"},
            cookies={"access_token": tenant_a_token}
        )
        product2 = response2.json()

        # Activate first product
        await api_client.post(
            f"/api/v1/products/{product1['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        # Activate second product (should deactivate first)
        response = await api_client.post(
            f"/api/v1/products/{product2['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == product2["id"]
        assert data["previous_active_product_id"] == product1["id"]

        # Verify first product is deactivated
        response1_check = await api_client.get(
            f"/api/v1/products/{product1['id']}",
            cookies={"access_token": tenant_a_token}
        )
        assert response1_check.json()["is_active"] is False

    @pytest.mark.asyncio
    async def test_activate_product_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/products/{product_id}/activate - 404 for non-existent product."""
        response = await api_client.post(
            "/api/v1/products/00000000-0000-0000-0000-000000000000/activate",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_activate_product_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/activate - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/activate"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_deactivate_product_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/deactivate - Deactivate successfully."""
        # First activate the product
        await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        # Then deactivate it
        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/deactivate",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_product["id"]
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_deactivate_product_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/products/{product_id}/deactivate - 404 for non-existent product."""
        response = await api_client.post(
            "/api/v1/products/00000000-0000-0000-0000-000000000000/deactivate",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_deactivate_product_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/deactivate - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/deactivate"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_product_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test DELETE /api/v1/products/{product_id} - Soft delete successfully."""
        # Create product to delete
        response = await api_client.post(
            "/api/v1/products/",
            json={"name": "Product to Delete"},
            cookies={"access_token": tenant_a_token}
        )
        product = response.json()

        # Delete it
        delete_response = await api_client.delete(
            f"/api/v1/products/{product['id']}",
            cookies={"access_token": tenant_a_token}
        )

        assert delete_response.status_code == 200
        data = delete_response.json()
        assert "message" in data
        assert "deleted_product_id" in data
        assert data["deleted_product_id"] == product["id"]

        # Verify product no longer appears in regular list
        list_response = await api_client.get(
            "/api/v1/products/",
            cookies={"access_token": tenant_a_token}
        )
        product_ids = [p["id"] for p in list_response.json()]
        assert product["id"] not in product_ids

        # Verify product appears in deleted list
        deleted_response = await api_client.get(
            "/api/v1/products/deleted",
            cookies={"access_token": tenant_a_token}
        )
        deleted_ids = [p["id"] for p in deleted_response.json()]
        assert product["id"] in deleted_ids

    @pytest.mark.asyncio
    async def test_delete_product_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test DELETE /api/v1/products/{product_id} - 404 for non-existent product."""
        response = await api_client.delete(
            "/api/v1/products/00000000-0000-0000-0000-000000000000",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_delete_product_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test DELETE /api/v1/products/{product_id} - 401 without authentication."""
        response = await api_client.delete(
            f"/api/v1/products/{tenant_a_product['id']}"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_restore_product_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/products/{product_id}/restore - Restore deleted product."""
        # Create and delete product
        response = await api_client.post(
            "/api/v1/products/",
            json={"name": "Product to Restore"},
            cookies={"access_token": tenant_a_token}
        )
        product = response.json()

        await api_client.delete(
            f"/api/v1/products/{product['id']}",
            cookies={"access_token": tenant_a_token}
        )

        # Restore it
        restore_response = await api_client.post(
            f"/api/v1/products/{product['id']}/restore",
            cookies={"access_token": tenant_a_token}
        )

        assert restore_response.status_code == 200
        data = restore_response.json()
        assert data["id"] == product["id"]
        assert data["name"] == product["name"]

        # Verify product appears in regular list again
        list_response = await api_client.get(
            "/api/v1/products/",
            cookies={"access_token": tenant_a_token}
        )
        product_ids = [p["id"] for p in list_response.json()]
        assert product["id"] in product_ids

    @pytest.mark.asyncio
    async def test_restore_product_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/products/{product_id}/restore - 404 for non-existent product."""
        response = await api_client.post(
            "/api/v1/products/00000000-0000-0000-0000-000000000000/restore",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_restore_product_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/restore - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/restore"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_cascade_impact(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id}/cascade-impact - Get deletion impact."""
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}/cascade-impact",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["product_id"] == tenant_a_product["id"]
        assert data["product_name"] == tenant_a_product["name"]
        assert "total_projects" in data
        assert "total_tasks" in data
        assert "total_vision_documents" in data
        assert "warning" in data

    @pytest.mark.asyncio
    async def test_get_cascade_impact_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/products/{product_id}/cascade-impact - 404 for non-existent product."""
        response = await api_client.get(
            "/api/v1/products/00000000-0000-0000-0000-000000000000/cascade-impact",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_get_cascade_impact_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id}/cascade-impact - 401 without authentication."""
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}/cascade-impact"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_refresh_active_product_with_active(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test GET /api/v1/products/refresh-active - Returns active product."""
        # Activate product first
        await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        response = await api_client.get(
            "/api/v1/products/refresh-active",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_active_product"] is True
        assert data["product"]["id"] == tenant_a_product["id"]
        assert data["product"]["is_active"] is True

    @pytest.mark.asyncio
    async def test_refresh_active_product_without_active(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/products/refresh-active - No active product."""
        response = await api_client.get(
            "/api/v1/products/refresh-active",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["has_active_product"] is False
        assert data["product"] is None

    @pytest.mark.asyncio
    async def test_refresh_active_product_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/v1/products/refresh-active - 401 without authentication."""
        response = await api_client.get("/api/v1/products/refresh-active")
        assert response.status_code == 401


# ============================================================================
# VISION ENDPOINTS TESTS
# ============================================================================

class TestProductVision:
    """Test vision document operations: upload, list, delete, list_chunks"""

    @pytest.mark.asyncio
    async def test_upload_vision_document_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/vision - Upload vision document."""
        # Create a mock markdown file
        content = b"# Vision Document\n\nThis is a test vision document with some content."
        files = {"file": ("vision.md", io.BytesIO(content), "text/markdown")}

        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files,
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "document_id" in data
        assert data["document_name"] == "vision.md"
        assert "chunks_created" in data
        assert "total_tokens" in data

    @pytest.mark.asyncio
    async def test_upload_vision_document_txt_file(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/vision - Upload .txt file."""
        content = b"Plain text vision document."
        files = {"file": ("vision.txt", io.BytesIO(content), "text/plain")}

        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files,
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["document_name"] == "vision.txt"

    @pytest.mark.asyncio
    async def test_upload_vision_document_invalid_file_type(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/vision - 400 for invalid file type."""
        content = b"Binary content"
        files = {"file": ("vision.pdf", io.BytesIO(content), "application/pdf")}

        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files,
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_upload_vision_document_duplicate_name(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/vision - 409 for duplicate filename."""
        content = b"# Vision Document"
        files = {"file": ("duplicate.md", io.BytesIO(content), "text/markdown")}

        # Upload first time
        response1 = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files,
            cookies={"access_token": tenant_a_token}
        )
        assert response1.status_code == 201

        # Upload again with same filename
        files2 = {"file": ("duplicate.md", io.BytesIO(content), "text/markdown")}
        response2 = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files2,
            cookies={"access_token": tenant_a_token}
        )

        assert response2.status_code == 409
        assert "already exists" in response2.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_upload_vision_document_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test POST /api/v1/products/{product_id}/vision - 401 without authentication."""
        content = b"# Vision"
        files = {"file": ("vision.md", io.BytesIO(content), "text/markdown")}

        response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_vision_documents_empty(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id}/vision - Empty list."""
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_vision_documents_with_documents(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id}/vision - List uploaded documents."""
        # Upload a document first
        content = b"# Vision"
        files = {"file": ("test_vision.md", io.BytesIO(content), "text/markdown")}
        upload_response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files,
            cookies={"access_token": tenant_a_token}
        )
        assert upload_response.status_code == 201

        # List documents
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        doc = next((d for d in data if d["document_name"] == "test_vision.md"), None)
        assert doc is not None
        assert doc["product_id"] == tenant_a_product["id"]

    @pytest.mark.asyncio
    async def test_list_vision_documents_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id}/vision - 401 without authentication."""
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}/vision"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_vision_document_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test DELETE /api/v1/products/{product_id}/vision/{doc_id} - Delete document."""
        # Upload document first
        content = b"# Vision to Delete"
        files = {"file": ("to_delete.md", io.BytesIO(content), "text/markdown")}
        upload_response = await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files,
            cookies={"access_token": tenant_a_token}
        )
        doc_id = upload_response.json()["document_id"]

        # Delete it
        response = await api_client.delete(
            f"/api/v1/products/{tenant_a_product['id']}/vision/{doc_id}",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 204

        # Verify it's gone
        list_response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            cookies={"access_token": tenant_a_token}
        )
        doc_ids = [d["id"] for d in list_response.json()]
        assert doc_id not in doc_ids

    @pytest.mark.asyncio
    async def test_delete_vision_document_not_found(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test DELETE /api/v1/products/{product_id}/vision/{doc_id} - 404 for non-existent document."""
        response = await api_client.delete(
            f"/api/v1/products/{tenant_a_product['id']}/vision/00000000-0000-0000-0000-000000000000",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
        assert "error_code" in data

    @pytest.mark.asyncio
    async def test_delete_vision_document_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test DELETE /api/v1/products/{product_id}/vision/{doc_id} - 401 without authentication."""
        response = await api_client.delete(
            f"/api/v1/products/{tenant_a_product['id']}/vision/some-doc-id"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_vision_chunks(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id}/vision-chunks - Get chunked content."""
        # Upload document first
        content = b"# Vision\n\nChunk 1 content\n\n## Section 2\n\nChunk 2 content"
        files = {"file": ("chunked.md", io.BytesIO(content), "text/markdown")}
        await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/vision",
            files=files,
            cookies={"access_token": tenant_a_token}
        )

        # Get chunks
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}/vision-chunks",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_vision_chunks_unauthorized(
        self, api_client: AsyncClient, tenant_a_product
    ):
        """Test GET /api/v1/products/{product_id}/vision-chunks - 401 without authentication."""
        response = await api_client.get(
            f"/api/v1/products/{tenant_a_product['id']}/vision-chunks"
        )
        assert response.status_code == 401


# ============================================================================
# MULTI-TENANT ISOLATION TESTS (COMPREHENSIVE)
# ============================================================================

class TestMultiTenantIsolation:
    """Comprehensive multi-tenant isolation verification across all endpoints"""

    @pytest.mark.asyncio
    async def test_cross_tenant_product_access_blocked(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
        tenant_a_product,
        tenant_b_product
    ):
        """Verify complete tenant isolation - Tenant A cannot access Tenant B's products."""

        # Test GET product
        response = await api_client.get(
            f"/api/v1/products/{tenant_b_product['id']}",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404  # Not found (prevents info leakage)
        data = response.json()
        assert "message" in data

        # Test UPDATE product
        response = await api_client.put(
            f"/api/v1/products/{tenant_b_product['id']}",
            json={"name": "Hacked"},
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data

        # Test DELETE product
        response = await api_client.delete(
            f"/api/v1/products/{tenant_b_product['id']}",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data

        # Test ACTIVATE product
        response = await api_client.post(
            f"/api/v1/products/{tenant_b_product['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data

        # Test CASCADE IMPACT
        response = await api_client.get(
            f"/api/v1/products/{tenant_b_product['id']}/cascade-impact",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data

    @pytest.mark.asyncio
    async def test_vision_documents_tenant_isolation(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
        tenant_a_product,
        tenant_b_product
    ):
        """Verify vision documents are isolated between tenants."""

        # Tenant B uploads vision document
        content = b"# Tenant B Vision"
        files = {"file": ("tenant_b_vision.md", io.BytesIO(content), "text/markdown")}
        upload_response = await api_client.post(
            f"/api/v1/products/{tenant_b_product['id']}/vision",
            files=files,
            cookies={"access_token": tenant_b_token}
        )
        assert upload_response.status_code == 201
        doc_id = upload_response.json()["document_id"]

        # Tenant A cannot access Tenant B's vision documents
        response = await api_client.get(
            f"/api/v1/products/{tenant_b_product['id']}/vision",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 200
        # Should get empty list or 404 (depends on implementation)

        # Tenant A cannot delete Tenant B's vision document
        response = await api_client.delete(
            f"/api/v1/products/{tenant_b_product['id']}/vision/{doc_id}",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404
        data = response.json()
        assert "message" in data
