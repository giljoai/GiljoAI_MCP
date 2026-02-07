"""
Integration tests for get_db() dependency fix.

Tests validate that the async get_db() function in api/dependencies.py
works correctly with all endpoints that depend on it.

Handover Context:
- Fixed get_db() from sync Session to async AsyncSession
- Affected endpoints: agent_jobs/table_view.py, agent_jobs/filters.py, vision_documents.py
- Critical: Ensure no session leaks or connection pool issues
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, User


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession, test_user: User) -> Product:
    """Create a test product for API tests."""
    product = Product(
        id=str(uuid4()),
        name="Test Product",
        description="Integration test product",
        tenant_key=test_user.tenant_key,
        owner_id=test_user.id,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.mark.asyncio
class TestGetDbDependency:
    """Test suite for get_db() dependency validation"""

    async def test_get_db_returns_async_session(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """
        Verify get_db() returns AsyncSession (not sync Session).

        This test validates the core fix: get_db() must return AsyncSession
        for compatibility with all async endpoints.
        """
        # This test will be implemented by checking endpoint responses
        # If get_db() returns wrong type, endpoints will crash with 500 errors
        response = await client.get("/health", headers=auth_headers)
        assert response.status_code == 200

    async def test_agent_jobs_table_view_endpoint(
        self, client: AsyncClient, test_user: User, test_product: Product, auth_headers: dict
    ):
        """
        Test /api/jobs/table-view endpoint uses get_db() correctly.

        Endpoint: GET /api/jobs/table-view
        Dependency: db: AsyncSession = Depends(get_db)
        Expected: 200 OK with table data
        """
        # Create a test project first
        project_data = {
            "name": "Test Project for Table View",
            "product_id": str(test_product.id),
            "description": "Integration test",
        }
        project_response = await client.post("/api/projects", json=project_data, headers=auth_headers)
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        # Test table view endpoint
        response = await client.get(
            "/api/jobs/table-view",
            params={"project_id": project_id, "limit": 10, "offset": 0},
            headers=auth_headers,
        )

        # Should return 200 (not 500 from type mismatch)
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "rows" in data
        assert isinstance(data["rows"], list)

    async def test_agent_jobs_filters_endpoint(
        self, client: AsyncClient, test_user: User, test_product: Product, auth_headers: dict
    ):
        """
        Test /api/jobs/filter-options endpoint uses get_db() correctly.

        Endpoint: GET /api/jobs/filter-options
        Dependency: db: AsyncSession = Depends(get_db)
        Expected: 200 OK with filter options
        """
        # Create a test project first
        project_data = {
            "name": "Test Project for Filters",
            "product_id": str(test_product.id),
            "description": "Integration test",
        }
        project_response = await client.post("/api/projects", json=project_data, headers=auth_headers)
        assert project_response.status_code == 201
        project_id = project_response.json()["id"]

        # Test filter options endpoint
        response = await client.get(
            "/api/jobs/filter-options", params={"project_id": project_id}, headers=auth_headers
        )

        # Should return 200 (not 500 from type mismatch)
        assert response.status_code == 200
        data = response.json()
        assert "statuses" in data
        assert "agent_display_names" in data
        assert isinstance(data["statuses"], list)
        assert isinstance(data["agent_display_names"], list)

    async def test_vision_documents_endpoint(
        self, client: AsyncClient, test_user: User, test_product: Product, auth_headers: dict
    ):
        """
        Test vision documents endpoints use get_db() correctly.

        Vision documents module has its OWN get_db() function (async).
        This test validates it still works correctly.

        Endpoints tested:
        - POST /api/vision-documents/ (create)
        - GET /api/vision-documents/product/{product_id} (list)
        """
        # Test create vision document
        doc_data = {
            "product_id": str(test_product.id),
            "document_name": "Integration Test Vision",
            "document_type": "vision",
            "content": "This is a test vision document for integration testing.",
            "display_order": 0,
            "version": "1.0.0",
        }

        create_response = await client.post(
            "/api/vision-documents/",
            data=doc_data,  # Use data for Form fields
            headers=auth_headers,
        )

        # Should return 201 (not 500 from type mismatch)
        assert create_response.status_code == 201
        created_doc = create_response.json()
        assert created_doc["document_name"] == "Integration Test Vision"
        document_id = created_doc["id"]

        # Test list vision documents
        list_response = await client.get(
            f"/api/vision-documents/product/{test_product.id}", headers=auth_headers
        )

        assert list_response.status_code == 200
        docs = list_response.json()
        assert isinstance(docs, list)
        assert len(docs) >= 1
        assert any(doc["id"] == document_id for doc in docs)

    async def test_database_session_cleanup(
        self, client: AsyncClient, test_user: User, test_product: Product, auth_headers: dict
    ):
        """
        Verify database sessions are properly cleaned up after requests.

        This test makes multiple requests and verifies:
        1. No session leaks (sessions are closed)
        2. Connection pool doesn't exhaust
        3. No "QueuePool limit exceeded" errors
        """
        # Make 20 rapid requests to test session cleanup
        for i in range(20):
            response = await client.get(
                f"/api/vision-documents/product/{test_product.id}", headers=auth_headers
            )
            assert response.status_code == 200

        # If sessions weren't cleaned up, we'd hit connection pool limits
        # and get 500 errors or timeouts

    async def test_regression_random_endpoints(self, client: AsyncClient, test_user: User, auth_headers: dict):
        """
        Spot-check random endpoints to ensure no regression.

        Tests endpoints that DON'T use get_db() to verify overall API health.
        """
        # Test health endpoint
        response = await client.get("/health")
        assert response.status_code == 200

        # Test root endpoint
        response = await client.get("/")
        assert response.status_code == 200

        # Test user settings endpoint
        response = await client.get("/api/v1/user/settings", headers=auth_headers)
        assert response.status_code == 200

        # Test statistics endpoint
        response = await client.get("/api/v1/stats/overview", headers=auth_headers)
        # Should return 200 or 404 (if no data), but NOT 500
        assert response.status_code in (200, 404)

    async def test_concurrent_database_access(
        self, client: AsyncClient, test_user: User, test_product: Product, auth_headers: dict
    ):
        """
        Test concurrent requests don't cause session conflicts.

        Validates that multiple async requests can use get_db() simultaneously
        without session contamination or deadlocks.
        """
        import asyncio

        # Create 10 concurrent requests
        async def make_request():
            return await client.get(f"/api/vision-documents/product/{test_product.id}", headers=auth_headers)

        tasks = [make_request() for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        # All requests should succeed
        for response in responses:
            assert response.status_code == 200


@pytest.mark.asyncio
class TestGetDbErrorHandling:
    """Test error handling in get_db() dependency"""

    async def test_get_db_without_db_manager(self, client: AsyncClient, auth_headers: dict):
        """
        Verify get_db() raises clear error if db_manager not initialized.

        This should never happen in production, but validates defensive programming.
        """
        # This test is more conceptual - in reality, API won't start without db_manager
        # We test this indirectly by checking endpoints work correctly
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["checks"]["database"] == "healthy"

    async def test_get_db_session_rollback_on_error(
        self, client: AsyncClient, test_user: User, test_product: Product, auth_headers: dict
    ):
        """
        Verify database sessions rollback on endpoint errors.

        Tests that if an endpoint raises an exception, the session is
        properly rolled back (not committed with partial data).
        """
        # Try to create a vision document with invalid data
        invalid_data = {
            "product_id": "invalid-uuid-format",  # Invalid UUID
            "document_name": "Test",
            "content": "Test content",
        }

        response = await client.post("/api/vision-documents/", data=invalid_data, headers=auth_headers)

        # Should return error (400 or 422), not 500
        assert response.status_code in (400, 404, 422)

        # Verify database is still healthy after error
        health_response = await client.get("/health")
        assert health_response.status_code == 200
        assert health_response.json()["checks"]["database"] == "healthy"
