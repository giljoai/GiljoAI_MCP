#!/usr/bin/env python3
"""
Integration tests for Project Product Validation (Handover 0050 Phase 4)
Tests project activation validation against parent product status
"""

import asyncio
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import select

from api.app import create_app
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, Project
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
    return "tk_test_project_validation"


@pytest.fixture
def headers(tenant_key):
    """Request headers with tenant key"""
    return {"X-Tenant-Key": tenant_key}


@pytest.fixture
async def test_data(app, tenant_key):
    """Create test products and projects"""
    db_manager = app.state.api_state.db_manager

    async with db_manager.get_session_async() as session:
        # Create active product
        active_product = Product(
            name="Active Product",
            description="Product for testing active project validation",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(active_product)
        await session.flush()

        # Create inactive product
        inactive_product = Product(
            name="Inactive Product",
            description="Product for testing inactive validation",
            tenant_key=tenant_key,
            is_active=False,
        )
        session.add(inactive_product)
        await session.flush()

        # Create project under active product
        active_project = Project(
            name="Active Product Project",
            mission="Test project under active product",
            tenant_key=tenant_key,
            product_id=active_product.id,
            status="inactive",
        )
        session.add(active_project)
        await session.flush()

        # Create project under inactive product
        inactive_project = Project(
            name="Inactive Product Project",
            mission="Test project under inactive product",
            tenant_key=tenant_key,
            product_id=inactive_product.id,
            status="inactive",
        )
        session.add(inactive_project)
        await session.flush()

        # Create project without product (orphan)
        orphan_project = Project(
            name="Orphan Project",
            mission="Test project without parent product",
            tenant_key=tenant_key,
            product_id=None,
            status="inactive",
        )
        session.add(orphan_project)
        await session.flush()

        await session.commit()

        yield {
            "active_product_id": active_product.id,
            "inactive_product_id": inactive_product.id,
            "active_project_id": active_project.id,
            "inactive_project_id": inactive_project.id,
            "orphan_project_id": orphan_project.id,
        }


class TestProjectProductValidation:
    """
    Test suite for Handover 0050 Phase 4: Project Product Validation
    Validates that projects can only be activated when parent product is active
    """

    @pytest.mark.asyncio
    async def test_activate_project_with_active_product_success(self, client, headers, test_data):
        """
        TEST: Project activation succeeds when parent product is active
        EXPECTED: 200 OK, project status becomes 'active'
        """
        project_id = test_data["active_project_id"]

        response = client.patch(f"/api/projects/{project_id}", json={"status": "active"}, headers=headers)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "active", f"Expected status 'active', got '{data['status']}'"

    @pytest.mark.asyncio
    async def test_activate_project_with_inactive_product_failure(self, client, headers, test_data):
        """
        TEST: Project activation fails when parent product is inactive
        EXPECTED: 400 Bad Request with clear error message
        """
        project_id = test_data["inactive_project_id"]

        response = client.patch(f"/api/projects/{project_id}", json={"status": "active"}, headers=headers)

        assert response.status_code == 400, f"Expected 400, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data
        assert "not active" in data["detail"].lower(), (
            f"Error message should mention inactive product: {data['detail']}"
        )
        assert "Inactive Product" in data["detail"], f"Error message should include product name: {data['detail']}"

    @pytest.mark.asyncio
    async def test_activate_orphan_project_success(self, client, headers, test_data):
        """
        TEST: Project without parent product can be activated (backward compatibility)
        EXPECTED: 200 OK, project status becomes 'active'
        """
        project_id = test_data["orphan_project_id"]

        response = client.patch(f"/api/projects/{project_id}", json={"status": "active"}, headers=headers)

        # Orphan projects should activate successfully (no parent to validate)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "active", f"Expected status 'active', got '{data['status']}'"

    @pytest.mark.asyncio
    async def test_update_project_name_with_inactive_product_success(self, client, headers, test_data):
        """
        TEST: Updating project name works regardless of parent product status
        EXPECTED: 200 OK, name updated (validation only applies to status='active')
        """
        project_id = test_data["inactive_project_id"]

        response = client.patch(f"/api/projects/{project_id}", json={"name": "Updated Project Name"}, headers=headers)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["name"] == "Updated Project Name"

    @pytest.mark.asyncio
    async def test_update_project_to_inactive_no_validation(self, client, headers, test_data, app):
        """
        TEST: Setting project status to 'inactive' or 'completed' does not trigger validation
        EXPECTED: 200 OK regardless of parent product status
        """
        project_id = test_data["inactive_project_id"]

        # Should succeed even though parent product is inactive
        response = client.patch(f"/api/projects/{project_id}", json={"status": "completed"}, headers=headers)

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()
        assert data["status"] == "completed"

    @pytest.mark.asyncio
    async def test_multi_tenant_isolation(self, client, headers, test_data, app):
        """
        TEST: Multi-tenant isolation - cannot activate project from different tenant
        EXPECTED: 404 Not Found (project not visible to other tenant)
        """
        project_id = test_data["active_project_id"]

        # Try to access with different tenant key
        different_tenant_headers = {"X-Tenant-Key": "tk_different_tenant"}

        response = client.patch(
            f"/api/projects/{project_id}", json={"status": "active"}, headers=different_tenant_headers
        )

        # Should fail because project belongs to different tenant
        assert response.status_code in [404, 403], f"Expected 404/403, got {response.status_code}"

    @pytest.mark.asyncio
    async def test_database_validation_enforcement(self, app, tenant_key, test_data):
        """
        TEST: Direct database operations also respect validation logic
        EXPECTED: Database-level constraints prevent invalid state
        """
        db_manager = app.state.api_state.db_manager

        async with db_manager.get_session_async() as session:
            # Fetch project under inactive product
            project_query = select(Project).where(Project.id == test_data["inactive_project_id"])
            result = await session.execute(project_query)
            project = result.scalar_one()

            # Fetch parent product
            product_query = select(Product).where(Product.id == project.product_id)
            product_result = await session.execute(product_query)
            parent_product = product_result.scalar_one()

            # Verify product is inactive
            assert parent_product.is_active is False

            # Verify project is inactive
            assert project.status == "inactive"

    @pytest.mark.asyncio
    async def test_error_message_clarity(self, client, headers, test_data):
        """
        TEST: Error messages are clear and actionable for users
        EXPECTED: Message includes product name and clear instructions
        """
        project_id = test_data["inactive_project_id"]

        response = client.patch(f"/api/projects/{project_id}", json={"status": "active"}, headers=headers)

        assert response.status_code == 400
        data = response.json()
        error_msg = data["detail"]

        # Verify error message components
        assert "Cannot activate project" in error_msg, "Should explain what failed"
        assert "Inactive Product" in error_msg, "Should include product name"
        assert "not active" in error_msg.lower(), "Should explain why it failed"
        assert "activate the product first" in error_msg.lower(), "Should provide solution"

    @pytest.mark.asyncio
    async def test_project_missing_product_id_reference(self, client, headers, app, tenant_key):
        """
        TEST: Project with non-existent product_id (corrupted data scenario)
        EXPECTED: 400 Bad Request with 'product not found' error
        """
        db_manager = app.state.api_state.db_manager

        async with db_manager.get_session_async() as session:
            # Create project with fake product_id
            corrupt_project = Project(
                name="Corrupt Project",
                mission="Project with non-existent product_id",
                tenant_key=tenant_key,
                product_id="00000000-0000-0000-0000-000000000000",  # Non-existent
                status="inactive",
            )
            session.add(corrupt_project)
            await session.flush()
            await session.commit()
            corrupt_project_id = corrupt_project.id

        # Try to activate
        response = client.patch(f"/api/projects/{corrupt_project_id}", json={"status": "active"}, headers=headers)

        assert response.status_code == 400, f"Expected 400, got {response.status_code}"
        data = response.json()
        assert "product not found" in data["detail"].lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
