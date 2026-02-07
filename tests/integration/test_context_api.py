"""
Integration tests for Context Management API endpoints.

Handover 0018: Comprehensive API integration testing for context management system.

Tests cover:
- Vision document chunking and indexing
- Context search functionality
- Agent context loading
- Context prioritization statistics
- Multi-tenant isolation
- Error handling
- Performance characteristics
"""

import asyncio
import sys
from pathlib import Path

import pytest
from httpx import AsyncClient


sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from api.app import create_app
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest.fixture(scope="module")
def event_loop():
    """Create event loop for async tests"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
async def db_manager():
    """Create test database manager"""
    db_url = PostgreSQLTestHelper.get_test_db_url(async_driver=True)
    manager = DatabaseManager(db_url, is_async=True)
    await manager.create_tables_async()
    yield manager
    await manager.close_async()


@pytest.fixture(scope="module")
async def app(db_manager):
    """Create FastAPI app with test database"""
    app = create_app()
    app.state.api_state.db_manager = db_manager
    app.state.db_manager = db_manager
    return app


@pytest.fixture
async def client(app):
    """Create async test client"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def tenant_key():
    """Test tenant key"""
    return "tk_test_context_api"


@pytest.fixture
def headers(tenant_key):
    """Request headers with tenant key"""
    return {"X-Tenant-Key": tenant_key}


@pytest.fixture
async def sample_product(db_manager, tenant_key):
    """Create a sample product with vision document"""
    vision_content = """# Product Vision

## Overview
This is a comprehensive product vision document for testing context management.

## Architecture
The system uses a microservices architecture with the following components:
- API Gateway
- Authentication Service
- Database Layer
- Cache Layer

## Technology Stack
- Backend: Python, FastAPI
- Database: PostgreSQL
- Cache: Redis
- Frontend: Vue.js

## Features
1. User Management
2. Product Catalog
3. Order Processing
4. Analytics Dashboard

## Security
All endpoints require authentication via JWT tokens.
Multi-tenant isolation is enforced at the database level.

## Performance Requirements
- API response time < 100ms
- Support 1000 concurrent users
- 99.9% uptime SLA
"""

    product = Product(
        id="test-product-001",
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for context API integration tests",
        vision_document=vision_content,
        vision_type="inline",
        chunked=False,
    )

    async with db_manager.get_session_async() as session:
        session.add(product)
        await session.commit()

    yield product

    async with db_manager.get_session_async() as session:
        await session.delete(product)

        stmt = "DELETE FROM mcp_context_index WHERE product_id = :product_id"
        await session.execute(stmt, {"product_id": product.id})
        await session.commit()


class TestContextAPIEndpoints:
    """Test suite for Context Management API endpoints"""

    @pytest.mark.asyncio
    async def test_chunk_vision_document_success(self, client, headers, sample_product):
        """Test successful vision document chunking"""
        response = await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["success"] is True
        assert data["product_id"] == sample_product.id
        assert data["chunks_created"] > 0
        assert data["total_tokens"] > 0
        assert data["original_size"] > 0
        assert "chunked and indexed successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_chunk_vision_document_already_chunked(self, client, headers, sample_product, db_manager):
        """Test chunking when document is already chunked"""
        async with db_manager.get_session_async() as session:
            sample_product.chunked = True
            session.add(sample_product)
            await session.commit()

        response = await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert "already chunked" in data["message"]
        assert data["chunks_created"] == 0

        async with db_manager.get_session_async() as session:
            sample_product.chunked = False
            session.add(sample_product)
            await session.commit()

    @pytest.mark.asyncio
    async def test_chunk_vision_document_force_rechunk(self, client, headers, sample_product, db_manager):
        """Test force rechunking"""
        async with db_manager.get_session_async() as session:
            sample_product.chunked = True
            session.add(sample_product)
            await session.commit()

        response = await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": True}, headers=headers
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["chunks_created"] > 0

    @pytest.mark.asyncio
    async def test_chunk_vision_document_product_not_found(self, client, headers):
        """Test chunking with non-existent product"""
        response = await client.post(
            "/api/v1/context/products/nonexistent-product/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        assert response.status_code == 404
        assert "Product not found" in response.text

    @pytest.mark.asyncio
    async def test_chunk_vision_document_no_vision(self, client, headers, db_manager, tenant_key):
        """Test chunking product without vision document"""
        product = Product(
            id="test-no-vision", tenant_key=tenant_key, name="No Vision Product", vision_type="none", chunked=False
        )

        async with db_manager.get_session_async() as session:
            session.add(product)
            await session.commit()

        try:
            response = await client.post(
                f"/api/v1/context/products/{product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
            )

            assert response.status_code == 404
            assert "No vision document available" in response.text

        finally:
            async with db_manager.get_session_async() as session:
                await session.delete(product)
                await session.commit()

    @pytest.mark.asyncio
    async def test_search_context_success(self, client, headers, sample_product):
        """Test context search functionality"""
        await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        response = await client.get(
            "/api/v1/context/search",
            params={"query": "architecture microservices", "product_id": sample_product.id, "limit": 5},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["query"] == "architecture microservices"
        assert len(data["chunks"]) > 0
        assert data["total_chunks"] > 0
        assert data["total_tokens"] > 0

        for chunk in data["chunks"]:
            assert "chunk_id" in chunk
            assert "content" in chunk
            assert "tokens" in chunk
            assert "chunk_number" in chunk

    @pytest.mark.asyncio
    async def test_search_context_no_results(self, client, headers, sample_product):
        """Test search with no matching results"""
        await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        response = await client.get(
            "/api/v1/context/search",
            params={"query": "quantum computing blockchain xyz", "product_id": sample_product.id, "limit": 5},
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["total_chunks"] == 0
        assert len(data["chunks"]) == 0

    @pytest.mark.asyncio
    async def test_load_context_for_agent_success(self, client, headers, sample_product):
        """Test loading context for specific agent"""
        await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        response = await client.post(
            "/api/v1/context/load-for-agent",
            json={
                "agent_display_name": "backend",
                "mission": "Implement authentication service",
                "product_id": sample_product.id,
                "max_tokens": 5000,
            },
            headers=headers,
        )

        assert response.status_code == 200
        data = response.json()

        assert data["agent_display_name"] == "backend"
        assert len(data["chunks"]) > 0
        assert data["total_chunks"] > 0
        assert data["total_tokens"] <= 5000
        assert data["average_relevance"] > 0

        for chunk in data["chunks"]:
            assert "chunk_id" in chunk
            assert "content" in chunk
            assert "tokens" in chunk
            assert chunk["relevance_score"] is not None

    @pytest.mark.asyncio
    async def test_load_context_for_agent_different_roles(self, client, headers, sample_product):
        """Test loading context for different agent types"""
        await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        agent_display_names = ["backend", "frontend", "database", "devops"]

        for agent_display_name in agent_display_names:
            response = await client.post(
                "/api/v1/context/load-for-agent",
                json={
                    "agent_display_name": agent_display_name,
                    "mission": f"Implement {agent_display_name} functionality",
                    "product_id": sample_product.id,
                    "max_tokens": 3000,
                },
                headers=headers,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["agent_display_name"] == agent_display_name
            assert data["total_tokens"] <= 3000

    @pytest.mark.asyncio
    async def test_get_token_stats_success(self, client, headers, sample_product):
        """Test getting context prioritization statistics"""
        await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        response = await client.get(f"/api/v1/context/products/{sample_product.id}/token-stats", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["product_id"] == sample_product.id
        assert data["original_tokens"] > 0
        assert data["condensed_tokens"] > 0
        assert data["reduction_percentage"] >= 0
        assert data["chunks_count"] > 0

    @pytest.mark.asyncio
    async def test_get_token_stats_no_chunks(self, client, headers, sample_product):
        """Test getting token stats when no chunks exist"""
        response = await client.get(f"/api/v1/context/products/{sample_product.id}/token-stats", headers=headers)

        assert response.status_code == 404
        assert "No chunks found" in response.text

    @pytest.mark.asyncio
    async def test_health_check_success(self, client, headers, sample_product):
        """Test context management system health check"""
        await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        response = await client.get("/api/v1/context/health", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["chunk_count"] > 0
        assert data["search_performance_ms"] is not None
        assert data["search_performance_ms"] >= 0
        assert "operational" in data["message"]

    @pytest.mark.asyncio
    async def test_health_check_no_chunks(self, client, headers):
        """Test health check with no chunks in database"""
        response = await client.get("/api/v1/context/health", headers=headers)

        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "healthy"
        assert data["chunk_count"] >= 0


class TestMultiTenantIsolation:
    """Test multi-tenant isolation for context management"""

    @pytest.mark.asyncio
    async def test_chunk_isolation(self, client, db_manager):
        """Test that chunks are isolated by tenant"""
        tenant1_key = "tk_tenant1_context"
        tenant2_key = "tk_tenant2_context"

        vision_content = "# Test Vision\n\nThis is a test vision document."

        product1 = Product(
            id="test-tenant1-product",
            tenant_key=tenant1_key,
            name="Tenant 1 Product",
            vision_document=vision_content,
            vision_type="inline",
            chunked=False,
        )

        product2 = Product(
            id="test-tenant2-product",
            tenant_key=tenant2_key,
            name="Tenant 2 Product",
            vision_document=vision_content,
            vision_type="inline",
            chunked=False,
        )

        async with db_manager.get_session_async() as session:
            session.add(product1)
            session.add(product2)
            await session.commit()

        try:
            await client.post(
                f"/api/v1/context/products/{product1.id}/chunk-vision",
                json={"force_rechunk": False},
                headers={"X-Tenant-Key": tenant1_key},
            )

            await client.post(
                f"/api/v1/context/products/{product2.id}/chunk-vision",
                json={"force_rechunk": False},
                headers={"X-Tenant-Key": tenant2_key},
            )

            response1 = await client.get(
                "/api/v1/context/search",
                params={"query": "test", "product_id": product1.id, "limit": 10},
                headers={"X-Tenant-Key": tenant1_key},
            )

            response2 = await client.get(
                "/api/v1/context/search",
                params={"query": "test", "product_id": product2.id, "limit": 10},
                headers={"X-Tenant-Key": tenant2_key},
            )

            assert response1.status_code == 200
            assert response2.status_code == 200

            data1 = response1.json()
            data2 = response2.json()

            assert len(data1["chunks"]) > 0
            assert len(data2["chunks"]) > 0

            tenant2_with_tenant1_key = await client.get(
                "/api/v1/context/search",
                params={"query": "test", "product_id": product2.id, "limit": 10},
                headers={"X-Tenant-Key": tenant1_key},
            )

            assert tenant2_with_tenant1_key.status_code == 200
            tenant2_data = tenant2_with_tenant1_key.json()
            assert tenant2_data["total_chunks"] == 0

        finally:
            async with db_manager.get_session_async() as session:
                await session.delete(product1)
                await session.delete(product2)

                from sqlalchemy import text

                await session.execute(
                    text("DELETE FROM mcp_context_index WHERE product_id IN (:p1, :p2)"),
                    {"p1": product1.id, "p2": product2.id},
                )
                await session.commit()


class TestErrorHandling:
    """Test error handling in context API"""

    @pytest.mark.asyncio
    async def test_invalid_product_id(self, client, headers):
        """Test with invalid product ID"""
        response = await client.post(
            "/api/v1/context/products/invalid-id/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_missing_tenant_key(self, client):
        """Test request without tenant key"""
        response = await client.get("/api/v1/context/health")

        assert response.status_code in [200, 401]

    @pytest.mark.asyncio
    async def test_invalid_search_query(self, client, headers):
        """Test search with empty query"""
        response = await client.get("/api/v1/context/search", params={"query": "", "limit": 10}, headers=headers)

        assert response.status_code in [200, 422]

    @pytest.mark.asyncio
    async def test_load_context_missing_fields(self, client, headers):
        """Test loading context with missing required fields"""
        response = await client.post(
            "/api/v1/context/load-for-agent", json={"agent_display_name": "backend"}, headers=headers
        )

        assert response.status_code == 422


class TestPerformance:
    """Test performance characteristics of context API"""

    @pytest.mark.asyncio
    async def test_large_document_chunking(self, client, headers, db_manager, tenant_key):
        """Test chunking large vision document"""
        large_vision = "\n\n".join(
            [
                f"# Section {i}\n\nThis is section {i} with detailed content about the system architecture."
                for i in range(100)
            ]
        )

        product = Product(
            id="test-large-doc",
            tenant_key=tenant_key,
            name="Large Document Product",
            vision_document=large_vision,
            vision_type="inline",
            chunked=False,
        )

        async with db_manager.get_session_async() as session:
            session.add(product)
            await session.commit()

        try:
            import time

            start_time = time.time()

            response = await client.post(
                f"/api/v1/context/products/{product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
            )

            elapsed_time = time.time() - start_time

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["chunks_created"] > 10

            assert elapsed_time < 10

        finally:
            async with db_manager.get_session_async() as session:
                await session.delete(product)

                from sqlalchemy import text

                await session.execute(
                    text("DELETE FROM mcp_context_index WHERE product_id = :product_id"), {"product_id": product.id}
                )
                await session.commit()

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, client, headers, sample_product):
        """Test concurrent search requests"""
        await client.post(
            f"/api/v1/context/products/{sample_product.id}/chunk-vision", json={"force_rechunk": False}, headers=headers
        )

        queries = ["architecture", "database", "security", "performance", "API"]

        tasks = [
            client.get(
                "/api/v1/context/search",
                params={"query": query, "product_id": sample_product.id, "limit": 5},
                headers=headers,
            )
            for query in queries
        ]

        responses = await asyncio.gather(*tasks)

        for response in responses:
            assert response.status_code == 200
            assert "chunks" in response.json()
