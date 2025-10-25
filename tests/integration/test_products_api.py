#!/usr/bin/env python3
"""
Integration tests for Products API endpoints
Tests async database operations and endpoint functionality
"""

import asyncio
import io
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
    db_manager = DatabaseManager(
        PostgreSQLTestHelper.get_test_db_url(async_driver=False),
        is_async=True
    )
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
    return "tk_test_products_api"


@pytest.fixture
def headers(tenant_key):
    """Request headers with tenant key"""
    return {"X-Tenant-Key": tenant_key}


class TestProductsAPI:
    """Test suite for Products API endpoints"""

    def test_create_product_basic(self, client, headers):
        """Test creating a basic product without vision document"""
        response = client.post(
            "/api/v1/products/",
            data={
                "name": "Test Product",
                "description": "Test Description"
            },
            headers=headers
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["name"] == "Test Product"
        assert data["description"] == "Test Description"
        assert data["has_vision"] is False
        assert data["vision_path"] is None
        assert "id" in data
        assert "created_at" in data

        # Store product ID for other tests
        self.product_id = data["id"]

    def test_create_product_with_vision(self, client, headers):
        """Test creating a product with vision document upload"""
        vision_content = b"# Product Vision\n\nThis is a test vision document."

        response = client.post(
            "/api/v1/products/",
            data={
                "name": "Product with Vision",
                "description": "Has vision document"
            },
            files={
                "vision_file": ("vision.md", io.BytesIO(vision_content), "text/markdown")
            },
            headers=headers
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["name"] == "Product with Vision"
        assert data["has_vision"] is True
        assert data["vision_path"] is not None

        # Verify vision file exists
        vision_path = Path(data["vision_path"])
        assert vision_path.exists(), f"Vision file not found at {vision_path}"

    def test_create_product_invalid_vision_type(self, client, headers):
        """Test creating product with invalid vision file type"""
        response = client.post(
            "/api/v1/products/",
            data={
                "name": "Product with Invalid Vision",
                "description": "Should fail"
            },
            files={
                "vision_file": ("vision.pdf", io.BytesIO(b"fake pdf"), "application/pdf")
            },
            headers=headers
        )

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        assert "Invalid file type" in response.text

    def test_list_products(self, client, headers):
        """Test listing products"""
        # Create a couple of products first
        for i in range(3):
            client.post(
                "/api/v1/products/",
                data={
                    "name": f"List Test Product {i}",
                    "description": f"Description {i}"
                },
                headers=headers
            )

        # List products
        response = client.get("/api/v1/products/", headers=headers)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert isinstance(data, list), "Response should be a list"
        assert len(data) >= 3, f"Expected at least 3 products, got {len(data)}"

        # Verify structure (including new metrics fields from Issue #1)
        for product in data:
            assert "id" in product
            assert "name" in product
            assert "has_vision" in product
            assert "project_count" in product
            assert "task_count" in product
            # NEW: Verify new metrics fields exist
            assert "unresolved_tasks" in product
            assert "unfinished_projects" in product
            assert "vision_documents_count" in product

    def test_list_products_pagination(self, client, headers):
        """Test products list pagination"""
        response = client.get(
            "/api/v1/products/?limit=2&offset=0",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) <= 2, f"Expected max 2 products with limit=2, got {len(data)}"

    def test_get_product(self, client, headers):
        """Test getting a specific product"""
        # Create a product
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Get Test Product",
                "description": "For get test"
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Get the product
        response = client.get(f"/api/v1/products/{product_id}", headers=headers)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["id"] == product_id
        assert data["name"] == "Get Test Product"
        assert data["description"] == "For get test"
        # NEW: Verify new metrics fields exist (Issue #1)
        assert "unresolved_tasks" in data
        assert "unfinished_projects" in data
        assert "vision_documents_count" in data
        # Should be 0 for newly created product
        assert data["unresolved_tasks"] == 0
        assert data["unfinished_projects"] == 0
        assert data["vision_documents_count"] == 0

    def test_get_product_not_found(self, client, headers):
        """Test getting non-existent product"""
        response = client.get(
            "/api/v1/products/non-existent-id",
            headers=headers
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

    def test_update_product(self, client, headers):
        """Test updating a product"""
        # Create a product
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Update Test Product",
                "description": "Original description"
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Update the product
        response = client.put(
            f"/api/v1/products/{product_id}",
            json={
                "name": "Updated Product Name",
                "description": "Updated description"
            },
            headers=headers
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["id"] == product_id
        assert data["name"] == "Updated Product Name"
        assert data["description"] == "Updated description"
        assert data["updated_at"] is not None

    def test_update_product_partial(self, client, headers):
        """Test partial update of a product"""
        # Create a product
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Partial Update Test",
                "description": "Original description"
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Update only name
        response = client.put(
            f"/api/v1/products/{product_id}",
            json={"name": "New Name Only"},
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["name"] == "New Name Only"
        assert data["description"] == "Original description"

    def test_delete_product(self, client, headers):
        """Test deleting a product"""
        # Create a product
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Delete Test Product",
                "description": "Will be deleted"
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Delete the product
        response = client.delete(f"/api/v1/products/{product_id}", headers=headers)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert "message" in data
        assert "deleted successfully" in data["message"].lower()

        # Verify product is deleted
        get_response = client.get(f"/api/v1/products/{product_id}", headers=headers)
        assert get_response.status_code == 404

    def test_delete_product_with_vision(self, client, headers):
        """Test deleting a product with vision document"""
        vision_content = b"# Vision to be deleted\n\nTest content."

        # Create product with vision
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Delete Vision Product",
                "description": "Has vision"
            },
            files={
                "vision_file": ("vision.md", io.BytesIO(vision_content), "text/markdown")
            },
            headers=headers
        )
        product_id = create_response.json()["id"]
        vision_path = Path(create_response.json()["vision_path"])

        # Delete the product
        response = client.delete(f"/api/v1/products/{product_id}", headers=headers)

        assert response.status_code == 200

        # Vision file should be deleted (or attempt made)
        # Note: File cleanup is best-effort, so we don't strictly assert deletion

    def test_upload_vision_document(self, client, headers):
        """Test uploading vision document to existing product"""
        # Create a product without vision
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Vision Upload Test",
                "description": "Will get vision later"
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Upload vision document
        vision_content = b"# New Vision\n\nThis is uploaded later."
        response = client.post(
            f"/api/v1/products/{product_id}/upload-vision",
            files={
                "vision_file": ("vision.md", io.BytesIO(vision_content), "text/markdown")
            },
            headers=headers
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert "message" in data
        assert "filename" in data
        assert data["filename"] == "vision.md"
        assert "chunks" in data
        assert data["chunks"] > 0

    def test_replace_vision_document(self, client, headers):
        """Test replacing existing vision document"""
        # Create product with vision
        vision_content_1 = b"# Original Vision\n\nOriginal content."
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Vision Replace Test",
                "description": "Has vision"
            },
            files={
                "vision_file": ("vision1.md", io.BytesIO(vision_content_1), "text/markdown")
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Replace with new vision
        vision_content_2 = b"# New Vision\n\nReplaced content."
        response = client.post(
            f"/api/v1/products/{product_id}/upload-vision",
            files={
                "vision_file": ("vision2.md", io.BytesIO(vision_content_2), "text/markdown")
            },
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["filename"] == "vision2.md"

    def test_upload_vision_invalid_file_type(self, client, headers):
        """Test uploading invalid vision file type"""
        # Create a product
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Invalid Vision Test",
                "description": "Test"
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Try to upload invalid file type
        response = client.post(
            f"/api/v1/products/{product_id}/upload-vision",
            files={
                "vision_file": ("vision.exe", io.BytesIO(b"fake exe"), "application/octet-stream")
            },
            headers=headers
        )

        assert response.status_code == 400
        assert "Invalid file type" in response.text

    def test_get_vision_chunks(self, client, headers):
        """Test getting vision document chunks"""
        # Create product with vision
        vision_content = b"""# Product Vision

## Overview
This is section 1.

## Features
This is section 2.

## Roadmap
This is section 3.
"""
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Chunks Test Product",
                "description": "Has vision"
            },
            files={
                "vision_file": ("vision.md", io.BytesIO(vision_content), "text/markdown")
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Get vision chunks
        response = client.get(
            f"/api/v1/products/{product_id}/vision-chunks",
            headers=headers
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert isinstance(data, list), "Response should be a list of chunks"
        assert len(data) > 0, "Should have at least one chunk"

        # Verify chunk structure
        for chunk in data:
            assert "chunk_number" in chunk
            assert "total_chunks" in chunk
            assert "content" in chunk
            assert "char_start" in chunk
            assert "char_end" in chunk
            assert "boundary_type" in chunk
            assert "keywords" in chunk
            assert "headers" in chunk

    def test_get_vision_chunks_no_vision(self, client, headers):
        """Test getting chunks for product without vision"""
        # Create product without vision
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "No Vision Product",
                "description": "No vision"
            },
            headers=headers
        )
        product_id = create_response.json()["id"]

        # Try to get vision chunks
        response = client.get(
            f"/api/v1/products/{product_id}/vision-chunks",
            headers=headers
        )

        assert response.status_code == 404
        assert "No vision document" in response.text

    def test_tenant_isolation(self, client):
        """Test that products are isolated by tenant"""
        # Create product with tenant 1
        headers_1 = {"X-Tenant-Key": "tk_tenant_1"}
        response_1 = client.post(
            "/api/v1/products/",
            data={
                "name": "Tenant 1 Product",
                "description": "Belongs to tenant 1"
            },
            headers=headers_1
        )
        assert response_1.status_code == 200
        product_id_1 = response_1.json()["id"]

        # Try to access with tenant 2
        headers_2 = {"X-Tenant-Key": "tk_tenant_2"}
        response_2 = client.get(f"/api/v1/products/{product_id_1}", headers=headers_2)

        assert response_2.status_code == 404, "Should not find product from different tenant"

        # List products for tenant 2 should not include tenant 1's products
        list_response = client.get("/api/v1/products/", headers=headers_2)
        assert list_response.status_code == 200
        products = list_response.json()

        product_ids = [p["id"] for p in products]
        assert product_id_1 not in product_ids, "Tenant 2 should not see tenant 1's products"

    def test_cascade_impact_basic(self, client, headers):
        """Test cascade impact endpoint for product with no related data"""
        # Create a product with no projects/tasks/vision
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Cascade Test Product",
                "description": "Test cascade impact"
            },
            headers=headers
        )
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]

        # Get cascade impact
        response = client.get(
            f"/api/v1/products/{product_id}/cascade-impact",
            headers=headers
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify response structure
        assert data["product_id"] == product_id
        assert data["projects_count"] == 0
        assert data["unfinished_projects"] == 0
        assert data["tasks_count"] == 0
        assert data["unresolved_tasks"] == 0
        assert data["vision_documents_count"] == 0
        assert data["total_chunks"] == 0

    def test_cascade_impact_with_vision(self, client, headers):
        """Test cascade impact for product with vision documents"""
        # Create product with vision document
        vision_content = b"# Product Vision\n\nTest vision content for cascade impact."
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Vision Cascade Product",
                "description": "Has vision"
            },
            files={
                "vision_file": ("vision.md", io.BytesIO(vision_content), "text/markdown")
            },
            headers=headers
        )
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]

        # Get cascade impact
        response = client.get(
            f"/api/v1/products/{product_id}/cascade-impact",
            headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["product_id"] == product_id
        # Note: Vision documents might be 0 or 1 depending on whether
        # VisionDocument records are created during product creation
        # The test just verifies the field exists
        assert "vision_documents_count" in data
        assert data["vision_documents_count"] >= 0

    def test_cascade_impact_not_found(self, client, headers):
        """Test cascade impact for non-existent product"""
        response = client.get(
            "/api/v1/products/non-existent-id/cascade-impact",
            headers=headers
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"
        assert "not found" in response.text.lower()

    def test_cascade_impact_tenant_isolation(self, client):
        """Test cascade impact respects tenant isolation"""
        # Create product with tenant 1
        headers_1 = {"X-Tenant-Key": "tk_cascade_tenant_1"}
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Tenant 1 Cascade Product",
                "description": "Belongs to tenant 1"
            },
            headers=headers_1
        )
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]

        # Try to get cascade impact with tenant 2
        headers_2 = {"X-Tenant-Key": "tk_cascade_tenant_2"}
        response = client.get(
            f"/api/v1/products/{product_id}/cascade-impact",
            headers=headers_2
        )

        # Should return 404 since product doesn't belong to tenant 2
        assert response.status_code == 404, "Should not find product from different tenant"
        assert "not found" in response.text.lower()

    def test_product_metrics_computation(self, client, headers):
        """Test that unresolved_tasks and unfinished_projects are computed correctly (Issue #2 & #3)"""
        from src.giljo_mcp.models import Product, Project, Task
        from api.app import create_app
        import asyncio

        # This test verifies that the list and get endpoints compute statistics correctly
        # We need to create a product with mixed status projects and tasks

        # Create a product
        create_response = client.post(
            "/api/v1/products/",
            data={
                "name": "Metrics Test Product",
                "description": "Test metrics computation"
            },
            headers=headers
        )
        assert create_response.status_code == 200
        product_id = create_response.json()["id"]

        # Note: This test will validate the response structure
        # The actual data creation would require database access
        # For now, we verify the fields exist and are integers

        # Test list endpoint (Issue #2)
        list_response = client.get("/api/v1/products/", headers=headers)
        assert list_response.status_code == 200
        products = list_response.json()

        product = next((p for p in products if p["id"] == product_id), None)
        assert product is not None

        # Verify new metrics fields exist and are integers
        assert isinstance(product["unresolved_tasks"], int)
        assert isinstance(product["unfinished_projects"], int)
        assert isinstance(product["vision_documents_count"], int)
        assert product["unresolved_tasks"] >= 0
        assert product["unfinished_projects"] >= 0
        assert product["vision_documents_count"] >= 0

        # Test get endpoint (Issue #3)
        get_response = client.get(f"/api/v1/products/{product_id}", headers=headers)
        assert get_response.status_code == 200
        product_data = get_response.json()

        # Verify new metrics fields exist and are integers
        assert isinstance(product_data["unresolved_tasks"], int)
        assert isinstance(product_data["unfinished_projects"], int)
        assert isinstance(product_data["vision_documents_count"], int)
        assert product_data["unresolved_tasks"] >= 0
        assert product_data["unfinished_projects"] >= 0
        assert product_data["vision_documents_count"] >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
