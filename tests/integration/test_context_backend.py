"""
Backend integration tests for Context Management System.

Handover 0018: Test backend logic without API layer.

Tests cover:
- Full chunking workflow
- Search accuracy
- Agent context loading
- Token reduction metrics
- Concurrent operations
- Error recovery
- Multi-tenant isolation at database level
"""

import asyncio
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.context_management import (
    ContextManagementSystem,
    VisionDocumentChunker,
    ContextIndexer,
    DynamicContextLoader,
    ContextSummarizer
)
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product, MCPContextIndex
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


@pytest.fixture
def tenant_key():
    """Test tenant key"""
    return "tk_test_context_backend"


@pytest.fixture
def sample_vision_document():
    """Sample vision document for testing"""
    return """# E-Commerce Platform Vision

## Executive Summary
This document outlines the vision for a modern e-commerce platform that will revolutionize
online shopping through AI-powered recommendations and seamless user experience.

## System Architecture

### Frontend Components
- React-based SPA with TypeScript
- Redux for state management
- Material-UI component library
- Progressive Web App (PWA) capabilities

### Backend Services
- Python FastAPI microservices
- PostgreSQL for relational data
- Redis for caching and session management
- RabbitMQ for async task processing

### Infrastructure
- Kubernetes orchestration
- Docker containerization
- AWS cloud deployment
- CloudFront CDN for static assets

## Core Features

### User Management
- OAuth2 authentication
- Social login integration
- User profile management
- Preference tracking

### Product Catalog
- Multi-category support
- Advanced search with filters
- Product recommendations
- Inventory management

### Shopping Cart
- Session-based cart
- Wishlist functionality
- Price calculations
- Discount code support

### Order Processing
- Checkout workflow
- Payment gateway integration
- Order tracking
- Email notifications

### Admin Dashboard
- Sales analytics
- User management
- Product management
- Report generation

## Technical Requirements

### Performance
- Page load time < 2 seconds
- API response time < 100ms
- Support 10,000 concurrent users
- 99.99% uptime SLA

### Security
- HTTPS encryption
- JWT token authentication
- SQL injection prevention
- XSS protection
- CSRF protection
- PCI DSS compliance for payments

### Scalability
- Horizontal scaling capability
- Auto-scaling based on load
- Database sharding for growth
- CDN for global distribution

## Database Schema

### Users Table
- id (primary key)
- email (unique)
- password_hash
- name
- created_at
- updated_at

### Products Table
- id (primary key)
- name
- description
- price
- category_id
- stock_quantity
- images

### Orders Table
- id (primary key)
- user_id (foreign key)
- total_amount
- status
- created_at
- shipped_at

## API Endpoints

### Authentication
- POST /api/auth/register
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/profile

### Products
- GET /api/products
- GET /api/products/:id
- POST /api/products (admin)
- PUT /api/products/:id (admin)
- DELETE /api/products/:id (admin)

### Cart
- GET /api/cart
- POST /api/cart/add
- PUT /api/cart/update
- DELETE /api/cart/remove

### Orders
- POST /api/orders/create
- GET /api/orders/:id
- GET /api/orders/history

## Development Roadmap

### Phase 1 - MVP (3 months)
- Basic user authentication
- Product catalog
- Shopping cart
- Simple checkout

### Phase 2 - Enhancement (2 months)
- Admin dashboard
- Advanced search
- Order tracking
- Email notifications

### Phase 3 - Optimization (2 months)
- Performance tuning
- AI recommendations
- Mobile app
- Analytics

## Success Metrics
- User acquisition rate
- Conversion rate
- Average order value
- Customer satisfaction score
- System uptime percentage
"""


class TestVisionDocumentChunker:
    """Test vision document chunking functionality"""

    def test_chunk_document_basic(self, sample_vision_document):
        """Test basic document chunking"""
        chunker = VisionDocumentChunker(target_chunk_size=1000)
        chunks = chunker.chunk_document(sample_vision_document, product_id="test-product")

        assert len(chunks) > 0
        assert all("content" in chunk for chunk in chunks)
        assert all("tokens" in chunk for chunk in chunks)
        assert all("chunk_number" in chunk for chunk in chunks)
        assert all("metadata" in chunk for chunk in chunks)

        for chunk in chunks:
            assert chunk["tokens"] > 0
            assert chunk["tokens"] <= 1500

    def test_chunk_document_token_accuracy(self, sample_vision_document):
        """Test tiktoken-based token counting accuracy"""
        chunker = VisionDocumentChunker(target_chunk_size=500)
        chunks = chunker.chunk_document(sample_vision_document, product_id="test-product")

        for chunk in chunks:
            import tiktoken
            encoding = tiktoken.encoding_for_model("gpt-4")
            actual_tokens = len(encoding.encode(chunk["content"]))

            token_difference = abs(chunk["tokens"] - actual_tokens)
            assert token_difference <= 5

    def test_chunk_document_semantic_boundaries(self, sample_vision_document):
        """Test that chunks respect semantic boundaries"""
        chunker = VisionDocumentChunker(target_chunk_size=1000)
        chunks = chunker.chunk_document(sample_vision_document, product_id="test-product")

        for chunk in chunks:
            content = chunk["content"]
            assert not content.startswith(" ")
            assert not content.endswith(" ")

            assert "\n\n" in content or len(content) < 100

    def test_chunk_empty_document(self):
        """Test chunking empty document"""
        chunker = VisionDocumentChunker()
        chunks = chunker.chunk_document("", product_id="test-product")

        assert len(chunks) == 0

    def test_chunk_small_document(self):
        """Test chunking small document that fits in one chunk"""
        chunker = VisionDocumentChunker(target_chunk_size=5000)
        small_doc = "# Small Document\n\nThis is a very small document."
        chunks = chunker.chunk_document(small_doc, product_id="test-product")

        assert len(chunks) == 1
        assert chunks[0]["content"] == small_doc


class TestContextIndexer:
    """Test context indexer functionality"""

    @pytest.mark.asyncio
    async def test_store_chunks(self, db_manager, tenant_key, sample_vision_document):
        """Test storing chunks in database"""
        chunker = VisionDocumentChunker(target_chunk_size=1000)
        chunks = chunker.chunk_document(sample_vision_document, product_id="test-product")

        indexer = ContextIndexer(db_manager)
        chunk_ids = indexer.store_chunks(tenant_key, "test-product", chunks)

        assert len(chunk_ids) == len(chunks)
        assert all(chunk_id is not None for chunk_id in chunk_ids)

        async with db_manager.get_session_async() as session:
            from sqlalchemy import select
            stmt = select(MCPContextIndex).where(
                MCPContextIndex.tenant_key == tenant_key,
                MCPContextIndex.product_id == "test-product"
            )
            result = await session.execute(stmt)
            stored_chunks = result.scalars().all()

            assert len(stored_chunks) == len(chunks)

            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-product"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_search_chunks(self, db_manager, tenant_key, sample_vision_document):
        """Test searching chunks"""
        chunker = VisionDocumentChunker(target_chunk_size=1000)
        chunks = chunker.chunk_document(sample_vision_document, product_id="test-search")

        indexer = ContextIndexer(db_manager)
        indexer.store_chunks(tenant_key, "test-search", chunks)

        search_results = indexer.search_chunks(tenant_key, "authentication security", limit=5)

        assert len(search_results) > 0
        assert all("content" in chunk for chunk in search_results)
        assert all("relevance_score" in chunk for chunk in search_results)

        relevance_scores = [chunk["relevance_score"] for chunk in search_results]
        assert relevance_scores == sorted(relevance_scores, reverse=True)

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-search"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_get_chunks_by_product(self, db_manager, tenant_key, sample_vision_document):
        """Test retrieving all chunks for a product"""
        chunker = VisionDocumentChunker(target_chunk_size=1000)
        chunks = chunker.chunk_document(sample_vision_document, product_id="test-get-chunks")

        indexer = ContextIndexer(db_manager)
        indexer.store_chunks(tenant_key, "test-get-chunks", chunks)

        retrieved_chunks = indexer.get_chunks_by_product(tenant_key, "test-get-chunks")

        assert len(retrieved_chunks) == len(chunks)

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-get-chunks"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_delete_chunks_by_product(self, db_manager, tenant_key, sample_vision_document):
        """Test deleting all chunks for a product"""
        chunker = VisionDocumentChunker(target_chunk_size=1000)
        chunks = chunker.chunk_document(sample_vision_document, product_id="test-delete")

        indexer = ContextIndexer(db_manager)
        indexer.store_chunks(tenant_key, "test-delete", chunks)

        deleted_count = indexer.delete_chunks_by_product(tenant_key, "test-delete")

        assert deleted_count == len(chunks)

        remaining_chunks = indexer.get_chunks_by_product(tenant_key, "test-delete")
        assert len(remaining_chunks) == 0


class TestDynamicContextLoader:
    """Test dynamic context loading functionality"""

    @pytest.mark.asyncio
    async def test_load_relevant_chunks(self, db_manager, tenant_key, sample_vision_document):
        """Test loading relevant chunks for query"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)
        cms.process_vision_document(tenant_key, "test-loader", sample_vision_document)

        loader = DynamicContextLoader(db_manager)
        chunks = loader.load_relevant_chunks(
            tenant_key=tenant_key,
            product_id="test-loader",
            query="authentication security JWT",
            max_tokens=3000
        )

        assert len(chunks) > 0
        total_tokens = sum(chunk["tokens"] for chunk in chunks)
        assert total_tokens <= 3000

        assert all("relevance_score" in chunk for chunk in chunks)

        relevance_scores = [chunk["relevance_score"] for chunk in chunks]
        assert relevance_scores == sorted(relevance_scores, reverse=True)

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-loader"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_role_based_loading(self, db_manager, tenant_key, sample_vision_document):
        """Test role-based chunk selection"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)
        cms.process_vision_document(tenant_key, "test-role", sample_vision_document)

        loader = DynamicContextLoader(db_manager)

        backend_chunks = loader.load_relevant_chunks(
            tenant_key=tenant_key,
            product_id="test-role",
            query="API endpoints database",
            role="backend",
            max_tokens=5000
        )

        frontend_chunks = loader.load_relevant_chunks(
            tenant_key=tenant_key,
            product_id="test-role",
            query="React components UI",
            role="frontend",
            max_tokens=5000
        )

        assert len(backend_chunks) > 0
        assert len(frontend_chunks) > 0

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-role"}
            )
            await session.commit()


class TestContextSummarizer:
    """Test context summarizer functionality"""

    @pytest.mark.asyncio
    async def test_create_summary(self, db_manager, tenant_key):
        """Test creating condensed mission summary"""
        full_content = "# Full Vision\n\n" + "This is a detailed vision document. " * 100
        condensed_mission = "Build e-commerce platform with modern tech stack."

        summarizer = ContextSummarizer(db_manager)
        stats = summarizer.create_summary(
            tenant_key=tenant_key,
            product_id="test-summary",
            full_content=full_content,
            condensed_mission=condensed_mission
        )

        assert "original_tokens" in stats
        assert "condensed_tokens" in stats
        assert "reduction_percentage" in stats

        assert stats["original_tokens"] > stats["condensed_tokens"]
        assert stats["reduction_percentage"] > 0

    @pytest.mark.asyncio
    async def test_get_reduction_stats(self, db_manager, tenant_key):
        """Test retrieving token reduction statistics"""
        full_content = "# Full Vision\n\n" + "Detailed content. " * 50
        condensed_mission = "Build platform."

        summarizer = ContextSummarizer(db_manager)
        summarizer.create_summary(tenant_key, "test-stats", full_content, condensed_mission)

        stats = summarizer.get_reduction_stats(tenant_key, "test-stats")

        assert stats is not None
        assert "original_tokens" in stats
        assert "condensed_tokens" in stats
        assert "reduction_percentage" in stats


class TestContextManagementSystem:
    """Test complete context management system"""

    @pytest.mark.asyncio
    async def test_process_vision_document(self, db_manager, tenant_key, sample_vision_document):
        """Test complete vision document processing"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)

        result = cms.process_vision_document(
            tenant_key=tenant_key,
            product_id="test-cms",
            content=sample_vision_document
        )

        assert result["success"] is True
        assert result["chunks_created"] > 0
        assert result["total_tokens"] > 0

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-cms"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_load_context_for_agent(self, db_manager, tenant_key, sample_vision_document):
        """Test loading context for agent"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)
        cms.process_vision_document(tenant_key, "test-agent-context", sample_vision_document)

        result = cms.load_context_for_agent(
            tenant_key=tenant_key,
            product_id="test-agent-context",
            query="authentication API security",
            role="backend",
            max_tokens=4000
        )

        assert "chunks" in result
        assert "total_chunks" in result
        assert "total_tokens" in result
        assert "average_relevance" in result

        assert len(result["chunks"]) > 0
        assert result["total_tokens"] <= 4000
        assert result["average_relevance"] > 0

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-agent-context"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_get_all_chunks(self, db_manager, tenant_key, sample_vision_document):
        """Test retrieving all chunks"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)
        result = cms.process_vision_document(tenant_key, "test-all-chunks", sample_vision_document)

        chunks = cms.get_all_chunks(tenant_key, "test-all-chunks")

        assert len(chunks) == result["chunks_created"]

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-all-chunks"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_delete_product_context(self, db_manager, tenant_key, sample_vision_document):
        """Test deleting all context for a product"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)
        result = cms.process_vision_document(tenant_key, "test-delete-context", sample_vision_document)

        deleted_count = cms.delete_product_context(tenant_key, "test-delete-context")

        assert deleted_count == result["chunks_created"]

        chunks = cms.get_all_chunks(tenant_key, "test-delete-context")
        assert len(chunks) == 0


class TestMultiTenantIsolation:
    """Test multi-tenant isolation at database level"""

    @pytest.mark.asyncio
    async def test_chunk_storage_isolation(self, db_manager, sample_vision_document):
        """Test that chunks are isolated by tenant"""
        tenant1 = "tk_tenant1_backend"
        tenant2 = "tk_tenant2_backend"

        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)

        cms.process_vision_document(tenant1, "shared-product-id", sample_vision_document)
        cms.process_vision_document(tenant2, "shared-product-id", sample_vision_document)

        tenant1_chunks = cms.get_all_chunks(tenant1, "shared-product-id")
        tenant2_chunks = cms.get_all_chunks(tenant2, "shared-product-id")

        assert len(tenant1_chunks) > 0
        assert len(tenant2_chunks) > 0

        for chunk in tenant1_chunks:
            assert chunk.tenant_key == tenant1

        for chunk in tenant2_chunks:
            assert chunk.tenant_key == tenant2

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "shared-product-id"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_search_isolation(self, db_manager, sample_vision_document):
        """Test that search results are isolated by tenant"""
        tenant1 = "tk_search_tenant1"
        tenant2 = "tk_search_tenant2"

        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)

        cms.process_vision_document(tenant1, "search-product", sample_vision_document)
        cms.process_vision_document(tenant2, "search-product", "Different content for tenant 2")

        indexer = ContextIndexer(db_manager)

        tenant1_results = indexer.search_chunks(tenant1, "authentication", limit=10)
        tenant2_results = indexer.search_chunks(tenant2, "authentication", limit=10)

        assert all(chunk.get("tenant_key") == tenant1 or "tenant_key" not in chunk
                   for chunk in tenant1_results)

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "search-product"}
            )
            await session.commit()


class TestConcurrentOperations:
    """Test concurrent operations"""

    @pytest.mark.asyncio
    async def test_concurrent_chunking(self, db_manager, tenant_key, sample_vision_document):
        """Test concurrent chunking operations"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)

        product_ids = [f"concurrent-{i}" for i in range(5)]

        async def chunk_document(product_id):
            return cms.process_vision_document(tenant_key, product_id, sample_vision_document)

        tasks = [chunk_document(pid) for pid in product_ids]
        results = await asyncio.gather(*tasks)

        assert all(result["success"] for result in results)
        assert all(result["chunks_created"] > 0 for result in results)

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            for product_id in product_ids:
                await session.execute(
                    text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                    {"product_id": product_id}
                )
            await session.commit()

    @pytest.mark.asyncio
    async def test_concurrent_searches(self, db_manager, tenant_key, sample_vision_document):
        """Test concurrent search operations"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)
        cms.process_vision_document(tenant_key, "concurrent-search", sample_vision_document)

        queries = ["authentication", "database", "API", "security", "performance"]

        async def search_query(query):
            indexer = ContextIndexer(db_manager)
            return indexer.search_chunks(tenant_key, query, limit=5)

        tasks = [search_query(q) for q in queries]
        results = await asyncio.gather(*tasks)

        assert all(isinstance(result, list) for result in results)

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "concurrent-search"}
            )
            await session.commit()


class TestErrorRecovery:
    """Test error handling and recovery"""

    @pytest.mark.asyncio
    async def test_empty_content_handling(self, db_manager, tenant_key):
        """Test handling of empty content"""
        cms = ContextManagementSystem(db_manager)
        result = cms.process_vision_document(tenant_key, "empty-content", "")

        assert result["success"] is False
        assert result["chunks_created"] == 0

    @pytest.mark.asyncio
    async def test_invalid_tenant_key_isolation(self, db_manager, sample_vision_document):
        """Test that invalid tenant key doesn't access other tenant data"""
        cms = ContextManagementSystem(db_manager, target_chunk_size=1000)
        cms.process_vision_document("valid-tenant", "test-product", sample_vision_document)

        chunks = cms.get_all_chunks("invalid-tenant", "test-product")

        assert len(chunks) == 0

        async with db_manager.get_session_async() as session:
            from sqlalchemy import text
            await session.execute(
                text("DELETE FROM mcp_context_index WHERE product_id = :product_id"),
                {"product_id": "test-product"}
            )
            await session.commit()

    @pytest.mark.asyncio
    async def test_search_with_no_results(self, db_manager, tenant_key):
        """Test search when no matching results exist"""
        indexer = ContextIndexer(db_manager)
        results = indexer.search_chunks(tenant_key, "nonexistent query xyz", limit=10)

        assert len(results) == 0
