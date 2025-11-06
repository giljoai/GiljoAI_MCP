"""
Integration tests for Product Activation feature (Handover 0049)

Tests the complete activation/deactivation flow:
1. Product list includes is_active field
2. Activate/Deactivate endpoints work correctly
3. Only one product can be active per tenant
4. UI updates properly after activation
"""

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.app import create_app
from src.giljo_mcp.database import DatabaseManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def app():
    """Create FastAPI app with test database"""
    app = create_app()

    # Initialize test database
    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False), is_async=True)
    await db_manager.create_tables_async()

    # Store in app state
    app.state.api_state.db_manager = db_manager

    yield app

    # Cleanup
    await db_manager.close_async()


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def tenant_key():
    """Test tenant key"""
    return "tk_test_activation"


@pytest.fixture
def headers(tenant_key):
    """Request headers with tenant key"""
    return {"X-Tenant-Key": tenant_key}


class TestProductActivation:
    """Test suite for Product Activation feature"""

    @pytest.mark.asyncio
    async def test_list_products_includes_is_active(self, client, headers):
        """Test that list_products endpoint includes is_active field"""
        # Create test product
        create_response = client.post(
            "/api/v1/products/", data={"name": "Product A", "description": "Test Product A"}, headers=headers
        )
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]

        # List products
        list_response = client.get("/api/v1/products/", headers=headers)
        assert list_response.status_code == 200
        products = list_response.json()

        # Verify products list includes is_active field
        assert len(products) > 0
        product = next((p for p in products if p["id"] == product_id), None)
        assert product is not None, "Created product not found in list"

        # CRITICAL: Verify is_active field is present (this was the bug)
        assert "is_active" in product, "is_active field missing from list_products response"
        assert product["is_active"] is False, "New product should not be active by default"

    @pytest.mark.asyncio
    async def test_activate_product(self, client, headers):
        """Test activating a product"""
        # Create product
        create_response = client.post(
            "/api/v1/products/", data={"name": "Product B", "description": "Test Product B"}, headers=headers
        )
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]

        # Activate product
        activate_response = client.post(f"/api/v1/products/{product_id}/activate", headers=headers)
        assert activate_response.status_code == 200
        data = activate_response.json()

        # Verify response includes is_active=True
        assert data["is_active"] is True, "Product should be active after activation"
        assert data["id"] == product_id

    @pytest.mark.asyncio
    async def test_deactivate_product(self, client, headers):
        """Test deactivating a product"""
        # Create and activate product
        create_response = client.post(
            "/api/v1/products/", data={"name": "Product C", "description": "Test Product C"}, headers=headers
        )
        product_id = create_response.json()["id"]

        # Activate first
        activate_response = client.post(f"/api/v1/products/{product_id}/activate", headers=headers)
        assert activate_response.status_code == 200
        assert activate_response.json()["is_active"] is True

        # Deactivate
        deactivate_response = client.post(f"/api/v1/products/{product_id}/deactivate", headers=headers)
        assert deactivate_response.status_code == 200
        data = deactivate_response.json()

        # Verify response includes is_active=False
        assert data["is_active"] is False, "Product should be inactive after deactivation"

    @pytest.mark.asyncio
    async def test_only_one_product_active_per_tenant(self, client, headers):
        """Test that activating one product deactivates others"""
        # Create three products
        products = []
        for i in range(1, 4):
            response = client.post(
                "/api/v1/products/",
                data={"name": f"Product D{i}", "description": f"Test Product D{i}"},
                headers=headers,
            )
            products.append(response.json()["id"])

        # Activate first product
        client.post(f"/api/v1/products/{products[0]}/activate", headers=headers)

        # Verify first is active
        list_response = client.get("/api/v1/products/", headers=headers)
        product_list = list_response.json()
        assert next(p for p in product_list if p["id"] == products[0])["is_active"] is True

        # Activate second product
        client.post(f"/api/v1/products/{products[1]}/activate", headers=headers)

        # Verify second is active, first is now inactive
        list_response = client.get("/api/v1/products/", headers=headers)
        product_list = list_response.json()
        assert next(p for p in product_list if p["id"] == products[0])["is_active"] is False
        assert next(p for p in product_list if p["id"] == products[1])["is_active"] is True
        assert next(p for p in product_list if p["id"] == products[2])["is_active"] is False

        # Activate third product
        client.post(f"/api/v1/products/{products[2]}/activate", headers=headers)

        # Verify third is active, others are inactive
        list_response = client.get("/api/v1/products/", headers=headers)
        product_list = list_response.json()
        assert next(p for p in product_list if p["id"] == products[0])["is_active"] is False
        assert next(p for p in product_list if p["id"] == products[1])["is_active"] is False
        assert next(p for p in product_list if p["id"] == products[2])["is_active"] is True

    @pytest.mark.asyncio
    async def test_get_product_includes_is_active(self, client, headers):
        """Test that get_product endpoint includes is_active field"""
        # Create product
        create_response = client.post(
            "/api/v1/products/", data={"name": "Product E", "description": "Test Product E"}, headers=headers
        )
        product_id = create_response.json()["id"]

        # Get product by ID
        get_response = client.get(f"/api/v1/products/{product_id}", headers=headers)
        assert get_response.status_code == 200
        data = get_response.json()

        # Verify is_active field is present and correct
        assert "is_active" in data
        assert data["is_active"] is False

        # Activate and verify
        client.post(f"/api/v1/products/{product_id}/activate", headers=headers)

        get_response = client.get(f"/api/v1/products/{product_id}", headers=headers)
        data = get_response.json()
        assert data["is_active"] is True

    @pytest.mark.asyncio
    async def test_create_product_includes_is_active(self, client, headers):
        """Test that create_product endpoint includes is_active field"""
        response = client.post(
            "/api/v1/products/", data={"name": "Product F", "description": "Test Product F"}, headers=headers
        )
        assert response.status_code == 200
        data = response.json()

        # Verify is_active field is present and False by default
        assert "is_active" in data
        assert data["is_active"] is False

    @pytest.mark.asyncio
    async def test_update_product_preserves_is_active(self, client, headers):
        """Test that updating product preserves is_active status"""
        # Create and activate product
        create_response = client.post(
            "/api/v1/products/", data={"name": "Product G", "description": "Test Product G"}, headers=headers
        )
        product_id = create_response.json()["id"]

        # Activate
        client.post(f"/api/v1/products/{product_id}/activate", headers=headers)

        # Update product
        update_response = client.put(
            f"/api/v1/products/{product_id}",
            data={"name": "Product G Updated", "description": "Updated description"},
            headers=headers,
        )
        assert update_response.status_code == 200
        data = update_response.json()

        # Verify is_active is still True after update
        assert data["is_active"] is True
        assert data["name"] == "Product G Updated"

    @pytest.mark.asyncio
    async def test_button_text_changes_based_on_is_active(self, client, headers):
        """
        Test scenario for UI button text toggle
        Frontend button text should be: {{ product.is_active ? 'Deactivate' : 'Activate' }}
        """
        # Create product
        create_response = client.post(
            "/api/v1/products/", data={"name": "Product H", "description": "Test Product H"}, headers=headers
        )
        product_id = create_response.json()["id"]

        # Get product - should show "Activate" button
        response = client.get(f"/api/v1/products/{product_id}", headers=headers)
        product = response.json()
        assert product["is_active"] is False
        # Frontend logic: if is_active is False, button shows "Activate"
        button_text = "Deactivate" if product["is_active"] else "Activate"
        assert button_text == "Activate"

        # Activate product
        client.post(f"/api/v1/products/{product_id}/activate", headers=headers)

        # Get product again - should show "Deactivate" button
        response = client.get(f"/api/v1/products/{product_id}", headers=headers)
        product = response.json()
        assert product["is_active"] is True
        # Frontend logic: if is_active is True, button shows "Deactivate"
        button_text = "Deactivate" if product["is_active"] else "Activate"
        assert button_text == "Deactivate"

        # Deactivate product
        client.post(f"/api/v1/products/{product_id}/deactivate", headers=headers)

        # Get product again - should show "Activate" button
        response = client.get(f"/api/v1/products/{product_id}", headers=headers)
        product = response.json()
        assert product["is_active"] is False
        button_text = "Deactivate" if product["is_active"] else "Activate"
        assert button_text == "Activate"


class TestProductActivationWithTenantIsolation:
    """Test that product activation respects tenant isolation"""

    @pytest.mark.asyncio
    async def test_activation_isolated_by_tenant(self, client):
        """Test that activation status is isolated per tenant"""
        tenant1 = "tk_test_tenant1"
        tenant2 = "tk_test_tenant2"

        headers1 = {"X-Tenant-Key": tenant1}
        headers2 = {"X-Tenant-Key": tenant2}

        # Create product in tenant1
        response1 = client.post(
            "/api/v1/products/",
            data={"name": "Tenant1 Product", "description": "Product for tenant1"},
            headers=headers1,
        )
        product1_id = response1.json()["id"]

        # Create product in tenant2
        response2 = client.post(
            "/api/v1/products/",
            data={"name": "Tenant2 Product", "description": "Product for tenant2"},
            headers=headers2,
        )
        product2_id = response2.json()["id"]

        # Activate product in tenant1
        client.post(f"/api/v1/products/{product1_id}/activate", headers=headers1)

        # Verify product1 is active in tenant1
        response = client.get(f"/api/v1/products/{product1_id}", headers=headers1)
        assert response.json()["is_active"] is True

        # Verify product2 is still inactive in tenant2
        response = client.get(f"/api/v1/products/{product2_id}", headers=headers2)
        assert response.json()["is_active"] is False

        # Activate product2 in tenant2
        client.post(f"/api/v1/products/{product2_id}/activate", headers=headers2)

        # Verify both are active in their respective tenants
        response = client.get(f"/api/v1/products/{product1_id}", headers=headers1)
        assert response.json()["is_active"] is True

        response = client.get(f"/api/v1/products/{product2_id}", headers=headers2)
        assert response.json()["is_active"] is True
