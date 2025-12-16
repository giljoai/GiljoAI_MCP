"""
Test suite for get_vision_document depth-based source selection (Handover 0352).

This test suite verifies that get_vision_document properly uses:
- summary_light for depth="light" (single response, no pagination)
- summary_medium for depth="medium" (single response, no pagination)
- MCPContextIndex chunks for depth="full" (paginated, ≤25K tokens per call)

Test-Driven Development (TDD) Approach:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass
3. REFACTOR: Optimize and clean up
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product
from src.giljo_mcp.models.context import MCPContextIndex
from src.giljo_mcp.models.products import VisionDocument
from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document


@pytest.mark.asyncio
class TestVisionDocumentDepthLightSummary:
    """Test depth='light' uses VisionDocument.summary_light field."""

    async def test_depth_light_returns_summary_light_field(self, db_manager: DatabaseManager):
        """
        GIVEN a product with vision document containing summary_light
        WHEN get_vision_document() is called with depth="light"
        THEN response contains summary_light content from database field
        AND no chunk pagination occurs
        """
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            # Create product
            product = Product(
                id=product_id, tenant_key=tenant_key, name="Test Product", description="Test product for light summary"
            )
            session.add(product)

            # Create vision document with summary_light
            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Full original content that is very long...",
                is_active=True,
                chunked=True,
                chunk_count=12,
                summary_light="Light summary content (~33% of original)",
                summary_light_tokens=5000,
                original_token_count=15000,
            )
            session.add(vision_doc)
            await session.commit()

        # Execute test
        result = await get_vision_document(
            product_id=product_id, tenant_key=tenant_key, chunking="light", db_manager=db_manager
        )

        # Assertions
        assert result["source"] == "vision_documents"
        assert result["depth"] == "light"
        assert result["data"]["summary"] == "Light summary content (~33% of original)"
        assert result["data"]["tokens"] == 5000
        assert result["data"]["compression"] == "33%"
        assert result["pagination"] is None, "Light summary should not be paginated"

    async def test_depth_light_no_summary_falls_back_gracefully(self, db_manager: DatabaseManager):
        """
        GIVEN a vision document WITHOUT summary_light field populated
        WHEN depth="light" is requested
        THEN return empty response with appropriate error message
        """
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            product = Product(id=product_id, tenant_key=tenant_key, name="Test Product")
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Full content",
                is_active=True,
                chunked=True,
                chunk_count=5,
                # No summary_light field populated
                summary_light=None,
                summary_light_tokens=None,
            )
            session.add(vision_doc)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id, tenant_key=tenant_key, chunking="light", db_manager=db_manager
        )

        assert result["source"] == "vision_documents"
        assert result["depth"] == "light"
        assert "error" in result["data"]
        assert result["data"]["error"] == "summary_not_available"


@pytest.mark.asyncio
class TestVisionDocumentDepthMediumSummary:
    """Test depth='medium' uses VisionDocument.summary_medium field."""

    async def test_depth_medium_returns_summary_medium_field(self, db_manager: DatabaseManager):
        """
        GIVEN a product with vision document containing summary_medium
        WHEN get_vision_document() is called with depth="medium"
        THEN response contains summary_medium content from database field
        AND no chunk pagination occurs
        """
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            product = Product(id=product_id, tenant_key=tenant_key, name="Test Product")
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Full original content that is very long...",
                is_active=True,
                chunked=True,
                chunk_count=12,
                summary_medium="Medium summary content (~66% of original)",
                summary_medium_tokens=10000,
                original_token_count=15000,
            )
            session.add(vision_doc)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id, tenant_key=tenant_key, chunking="medium", db_manager=db_manager
        )

        assert result["source"] == "vision_documents"
        assert result["depth"] == "medium"
        assert result["data"]["summary"] == "Medium summary content (~66% of original)"
        assert result["data"]["tokens"] == 10000
        assert result["data"]["compression"] == "66%"
        assert result["pagination"] is None, "Medium summary should not be paginated"

    async def test_depth_medium_no_summary_falls_back_gracefully(self, db_manager: DatabaseManager):
        """
        GIVEN a vision document WITHOUT summary_medium field populated
        WHEN depth="medium" is requested
        THEN return empty response with appropriate error message
        """
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            product = Product(id=product_id, tenant_key=tenant_key, name="Test Product")
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Full content",
                is_active=True,
                chunked=True,
                chunk_count=5,
                # No summary_medium field populated
                summary_medium=None,
                summary_medium_tokens=None,
            )
            session.add(vision_doc)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id, tenant_key=tenant_key, chunking="medium", db_manager=db_manager
        )

        assert result["source"] == "vision_documents"
        assert result["depth"] == "medium"
        assert "error" in result["data"]
        assert result["data"]["error"] == "summary_not_available"


@pytest.mark.asyncio
class TestVisionDocumentDepthFullChunks:
    """Test depth='full' uses MCPContextIndex chunks with pagination."""

    async def test_depth_full_uses_chunk_pagination(self, db_manager: DatabaseManager):
        """
        GIVEN a product with 12 vision document chunks in MCPContextIndex
        WHEN get_vision_document() is called with depth="full"
        THEN response uses chunk-based pagination (not summary fields)
        AND pagination metadata is included
        """
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())
        vision_doc_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            product = Product(id=product_id, tenant_key=tenant_key, name="Test Product")
            session.add(product)

            vision_doc = VisionDocument(
                id=vision_doc_id,
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Full content",
                is_active=True,
                chunked=True,
                chunk_count=12,
                # Has summaries but should NOT use them for depth="full"
                summary_light="Light summary",
                summary_medium="Medium summary",
            )
            session.add(vision_doc)

            # Create 12 chunks
            for i in range(12):
                chunk = MCPContextIndex(
                    tenant_key=tenant_key,
                    product_id=product_id,
                    vision_document_id=vision_doc_id,
                    content=f"Chunk {i+1} content with substantial text...",
                    chunk_order=i + 1,
                    token_count=2000,
                )
                session.add(chunk)

            await session.commit()

        result = await get_vision_document(
            product_id=product_id, tenant_key=tenant_key, chunking="full", offset=0, limit=3, db_manager=db_manager
        )

        # Verify chunk-based response (NOT summary)
        assert result["source"] == "vision_documents"
        assert result["depth"] == "full"
        assert isinstance(result["data"], list), "Full depth should return chunk array"
        assert len(result["data"]) <= 3, "Limit parameter should restrict chunks"

        # Verify pagination exists
        assert "pagination" in result
        assert result["pagination"] is not None
        assert result["pagination"]["total_chunks"] == 12
        assert result["pagination"]["offset"] == 0
        assert result["pagination"]["limit"] == 3
        assert result["pagination"]["has_more"] is True
        assert result["pagination"]["next_offset"] == 3

    async def test_depth_full_respects_25k_token_limit(self, db_manager: DatabaseManager):
        """
        GIVEN vision chunks that would exceed 25K tokens
        WHEN depth="full" is requested
        THEN total tokens returned should not exceed 25,000
        """
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())
        vision_doc_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            product = Product(id=product_id, tenant_key=tenant_key, name="Test Product")
            session.add(product)

            vision_doc = VisionDocument(
                id=vision_doc_id,
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Full content",
                is_active=True,
                chunked=True,
                chunk_count=20,
            )
            session.add(vision_doc)

            # Create chunks with 8K tokens each (would be 160K total if no limit)
            for i in range(20):
                chunk = MCPContextIndex(
                    tenant_key=tenant_key,
                    product_id=product_id,
                    vision_document_id=vision_doc_id,
                    content="x" * 32000,  # ~8K tokens (4 chars per token)
                    chunk_order=i + 1,
                    token_count=8000,
                )
                session.add(chunk)

            await session.commit()

        result = await get_vision_document(
            product_id=product_id, tenant_key=tenant_key, chunking="full", db_manager=db_manager
        )

        # Calculate total tokens returned
        total_tokens = sum(chunk["tokens"] for chunk in result["data"])

        assert total_tokens <= 25000, f"Exceeded 25K token limit: {total_tokens} tokens"
        assert result["pagination"]["has_more"] is True, "Should indicate more chunks available"


@pytest.mark.asyncio
class TestVisionDocumentDepthNone:
    """Test depth='none' returns empty response."""

    async def test_depth_none_returns_empty_response(self, db_manager: DatabaseManager):
        """
        GIVEN a product with vision documents
        WHEN depth="none" is requested
        THEN return empty response without querying database
        """
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        result = await get_vision_document(
            product_id=product_id, tenant_key=tenant_key, chunking="none", db_manager=db_manager
        )

        assert result["source"] == "vision_documents"
        assert result["depth"] == "none"
        assert result["data"] == []
        assert result["metadata"]["total_chunks"] == 0
        assert result["metadata"]["estimated_tokens"] == 0


@pytest.mark.asyncio
class TestVisionDocumentMultiTenantIsolation:
    """Test multi-tenant isolation for all depth levels."""

    async def test_depth_light_respects_tenant_isolation(self, db_manager: DatabaseManager):
        """
        GIVEN two products in different tenants with summary_light
        WHEN tenant A requests depth="light"
        THEN only tenant A's summary is returned
        """
        tenant_a = f"tenant_{uuid4().hex[:8]}"
        tenant_b = f"tenant_{uuid4().hex[:8]}"
        product_a_id = str(uuid4())
        product_b_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            # Tenant A product
            product_a = Product(id=product_a_id, tenant_key=tenant_a, name="Product A")
            vision_a = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_a,
                product_id=product_a_id,
                document_name="Vision A",
                document_type="vision",
                storage_type="inline",
                vision_document="Content A",
                is_active=True,
                chunked=True,
                chunk_count=5,
                summary_light="Summary A (Tenant A)",
                summary_light_tokens=1000,
            )

            # Tenant B product
            product_b = Product(id=product_b_id, tenant_key=tenant_b, name="Product B")
            vision_b = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_b,
                product_id=product_b_id,
                document_name="Vision B",
                document_type="vision",
                storage_type="inline",
                vision_document="Content B",
                is_active=True,
                chunked=True,
                chunk_count=5,
                summary_light="Summary B (Tenant B)",
                summary_light_tokens=1000,
            )

            session.add_all([product_a, vision_a, product_b, vision_b])
            await session.commit()

        # Request from Tenant A
        result = await get_vision_document(
            product_id=product_a_id, tenant_key=tenant_a, chunking="light", db_manager=db_manager
        )

        assert result["data"]["summary"] == "Summary A (Tenant A)"
        assert "Tenant B" not in result["data"]["summary"]

        # Request from Tenant B
        result_b = await get_vision_document(
            product_id=product_b_id, tenant_key=tenant_b, chunking="light", db_manager=db_manager
        )

        assert result_b["data"]["summary"] == "Summary B (Tenant B)"
        assert "Tenant A" not in result_b["data"]["summary"]
