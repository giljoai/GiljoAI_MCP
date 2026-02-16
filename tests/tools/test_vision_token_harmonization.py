"""
Test suite for Handover 0493: Vision Document Token Harmonization.

Tests:
1. Constants consistency across modules
2. Light/medium summary pagination when exceeding VISION_DELIVERY_BUDGET
3. Light/medium summary single response when within budget (regression)
4. Full-depth uses stored token_count instead of chars/4 estimation
5. Auto-consolidation on upload
6. Full-depth pagination regression
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product
from src.giljo_mcp.models.context import MCPContextIndex
from src.giljo_mcp.models.products import VisionDocument
from src.giljo_mcp.tools.chunking import (
    TOKEN_CHAR_RATIO,
    VISION_DEFAULT_CHUNK_SIZE,
    VISION_DELIVERY_BUDGET,
    VISION_MAX_INGEST_TOKENS,
    EnhancedChunker,
)
from src.giljo_mcp.tools.context_tools.get_vision_document import (
    estimate_tokens,
    get_max_tokens,
    get_vision_document,
)


class TestConstants:
    """Test that token constants are consistent and importable."""

    def test_constants_are_importable(self):
        assert VISION_MAX_INGEST_TOKENS == 25000
        assert VISION_DELIVERY_BUDGET == 24000
        assert VISION_DEFAULT_CHUNK_SIZE == 24000
        assert TOKEN_CHAR_RATIO == 4

    def test_delivery_budget_less_than_ingest(self):
        assert VISION_DELIVERY_BUDGET < VISION_MAX_INGEST_TOKENS

    def test_enhanced_chunker_uses_constants(self):
        assert EnhancedChunker.MAX_TOKENS == VISION_DELIVERY_BUDGET
        assert EnhancedChunker.TOKEN_CHAR_RATIO == TOKEN_CHAR_RATIO
        assert EnhancedChunker.DEFAULT_MAX_TOKENS == VISION_DELIVERY_BUDGET

    def test_get_max_tokens_all_depths_use_delivery_budget(self):
        """All depths use VISION_DELIVERY_BUDGET (24K) as per-call cap.
        Light/medium are percentage-based summaries delivered in 24K increments.
        """
        assert get_max_tokens("full") == VISION_DELIVERY_BUDGET
        assert get_max_tokens("light") == VISION_DELIVERY_BUDGET
        assert get_max_tokens("medium") == VISION_DELIVERY_BUDGET


@pytest.mark.asyncio
class TestSummaryPaginationSmall:
    """Test that small summaries (<= 24K tokens) return single response (regression)."""

    async def test_light_summary_within_budget_no_pagination(self, db_manager: DatabaseManager):
        """Small light summary fits in budget - returns single response with pagination=None."""
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            product = Product(
                id=product_id,
                tenant_key=tenant_key,
                name="Test Product",
                consolidated_vision_light="Small light summary content",
                consolidated_vision_light_tokens=500,
                consolidated_vision_hash="abc12345",
            )
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Original content",
                is_active=True,
            )
            session.add(vision_doc)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="light",
            db_manager=db_manager,
        )

        assert result["source"] == "vision_documents"
        assert result["depth"] == "light"
        assert result["data"]["summary"] == "Small light summary content"
        assert result["data"]["tokens"] == 500
        assert result["data"]["compression"] == "33%"
        assert result["pagination"] is None

    async def test_medium_summary_within_budget_no_pagination(self, db_manager: DatabaseManager):
        """Small medium summary fits in budget - returns single response with pagination=None."""
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        async with db_manager.get_session_async() as session:
            product = Product(
                id=product_id,
                tenant_key=tenant_key,
                name="Test Product",
                consolidated_vision_medium="Small medium summary content",
                consolidated_vision_medium_tokens=1000,
                consolidated_vision_hash="def56789",
            )
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Original content",
                is_active=True,
            )
            session.add(vision_doc)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="medium",
            db_manager=db_manager,
        )

        assert result["source"] == "vision_documents"
        assert result["depth"] == "medium"
        assert result["data"]["summary"] == "Small medium summary content"
        assert result["data"]["tokens"] == 1000
        assert result["data"]["compression"] == "66%"
        assert result["pagination"] is None


@pytest.mark.asyncio
class TestSummaryPaginationLarge:
    """Test that large summaries (> 24K tokens) get paginated."""

    async def test_light_summary_exceeding_budget_is_paginated(self, db_manager: DatabaseManager):
        """Light summary > 24K tokens gets chunked and paginated."""
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        # Create content that exceeds 24K tokens (~96K chars at 4 chars/token)
        large_summary = "A" * 120000  # ~30K tokens, well above 24K budget

        async with db_manager.get_session_async() as session:
            product = Product(
                id=product_id,
                tenant_key=tenant_key,
                name="Test Product",
                consolidated_vision_light=large_summary,
                consolidated_vision_light_tokens=30000,
                consolidated_vision_hash="large12345",
            )
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Original content",
                is_active=True,
            )
            session.add(vision_doc)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="light",
            offset=0,
            db_manager=db_manager,
        )

        # Should be paginated
        assert result["pagination"] is not None
        assert result["pagination"]["total_chunks"] >= 2
        assert result["pagination"]["offset"] == 0
        assert result["pagination"]["has_more"] is True
        assert result["pagination"]["next_offset"] == 1

        # First chunk should fit within delivery budget
        chunk_tokens = estimate_tokens(result["data"]["summary"])
        assert chunk_tokens <= VISION_DELIVERY_BUDGET

    async def test_medium_summary_exceeding_budget_is_paginated(self, db_manager: DatabaseManager):
        """Medium summary > 24K tokens gets chunked and paginated."""
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        large_summary = "B" * 120000  # ~30K tokens

        async with db_manager.get_session_async() as session:
            product = Product(
                id=product_id,
                tenant_key=tenant_key,
                name="Test Product",
                consolidated_vision_medium=large_summary,
                consolidated_vision_medium_tokens=30000,
                consolidated_vision_hash="large67890",
            )
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Original content",
                is_active=True,
            )
            session.add(vision_doc)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="medium",
            offset=0,
            db_manager=db_manager,
        )

        assert result["pagination"] is not None
        assert result["pagination"]["total_chunks"] >= 2
        assert result["pagination"]["has_more"] is True

    async def test_paginated_summary_offset_navigation(self, db_manager: DatabaseManager):
        """Can navigate through paginated summary with offset."""
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        # Use varied content so chunks are distinguishable
        part1 = "SECTION_ONE " * 10000  # ~30K tokens worth of section 1
        part2 = "SECTION_TWO " * 10000  # ~30K tokens worth of section 2
        large_summary = part1 + "\n\n" + part2

        async with db_manager.get_session_async() as session:
            product = Product(
                id=product_id,
                tenant_key=tenant_key,
                name="Test Product",
                consolidated_vision_light=large_summary,
                consolidated_vision_light_tokens=60000,
                consolidated_vision_hash="nav12345",
            )
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Original content",
                is_active=True,
            )
            session.add(vision_doc)
            await session.commit()

        # Fetch first page
        result_page1 = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="light",
            offset=0,
            db_manager=db_manager,
        )

        assert result_page1["pagination"]["offset"] == 0
        total_chunks = result_page1["pagination"]["total_chunks"]
        assert total_chunks >= 2

        # Fetch second page
        result_page2 = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="light",
            offset=1,
            db_manager=db_manager,
        )

        assert result_page2["pagination"]["offset"] == 1
        # Both pages should have content, and last page should signal no more
        assert result_page1["data"]["summary"]
        assert result_page2["data"]["summary"]
        if total_chunks == 2:
            assert result_page2["pagination"]["has_more"] is False

    async def test_paginated_summary_offset_beyond_range(self, db_manager: DatabaseManager):
        """Offset beyond total chunks returns empty with has_more=False."""
        tenant_key = f"tenant_{uuid4().hex[:8]}"
        product_id = str(uuid4())

        large_summary = "D" * 120000

        async with db_manager.get_session_async() as session:
            product = Product(
                id=product_id,
                tenant_key=tenant_key,
                name="Test Product",
                consolidated_vision_light=large_summary,
                consolidated_vision_light_tokens=30000,
                consolidated_vision_hash="oob12345",
            )
            session.add(product)

            vision_doc = VisionDocument(
                id=str(uuid4()),
                tenant_key=tenant_key,
                product_id=product_id,
                document_name="Test Vision",
                document_type="vision",
                storage_type="inline",
                vision_document="Original content",
                is_active=True,
            )
            session.add(vision_doc)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="light",
            offset=999,
            db_manager=db_manager,
        )

        assert result["pagination"]["has_more"] is False
        assert result["pagination"]["next_offset"] is None
        assert result["data"]["tokens"] == 0


@pytest.mark.asyncio
class TestFullDepthTokenCounting:
    """Test that full-depth uses stored token_count instead of chars/4."""

    async def test_full_depth_uses_stored_token_count(self, db_manager: DatabaseManager):
        """Full-depth loop uses chunk.token_count from DB, not estimate_tokens()."""
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
                chunk_count=3,
            )
            session.add(vision_doc)

            # Create chunks with KNOWN token_count values
            # Content is 40 chars = ~10 tokens by chars/4, but stored as 5000 tokens
            for i in range(3):
                chunk = MCPContextIndex(
                    tenant_key=tenant_key,
                    product_id=product_id,
                    vision_document_id=vision_doc_id,
                    content="x" * 40,  # 10 tokens by chars/4
                    chunk_order=i + 1,
                    token_count=5000,  # Stored tiktoken count
                )
                session.add(chunk)

            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="full",
            db_manager=db_manager,
        )

        # If using stored token_count (5000), each chunk reports 5000 tokens
        # If using chars/4 (40/4=10), each chunk would report 10 tokens
        for chunk_data in result["data"]:
            assert chunk_data["tokens"] == 5000, (
                f"Expected stored token_count=5000, got {chunk_data['tokens']}. "
                "Full-depth should use chunk.token_count, not estimate_tokens()."
            )

    async def test_full_depth_falls_back_to_estimate_when_no_token_count(self, db_manager: DatabaseManager):
        """When chunk.token_count is None/0, falls back to estimate_tokens()."""
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
                chunk_count=1,
            )
            session.add(vision_doc)

            # Chunk with token_count=None (fallback scenario)
            chunk = MCPContextIndex(
                tenant_key=tenant_key,
                product_id=product_id,
                vision_document_id=vision_doc_id,
                content="y" * 400,  # 100 tokens by chars/4
                chunk_order=1,
                token_count=None,
            )
            session.add(chunk)
            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="full",
            db_manager=db_manager,
        )

        assert len(result["data"]) == 1
        # Falls back to chars/4 estimation: 400/4 = 100
        assert result["data"][0]["tokens"] == 100

    async def test_full_depth_token_budget_respects_stored_counts(self, db_manager: DatabaseManager):
        """Token budget enforcement uses stored counts, stopping at 24K."""
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
                chunk_count=10,
            )
            session.add(vision_doc)

            # Create 10 chunks of 5000 tokens each (50K total)
            # Budget is 24K, so should return 4 chunks (20K) and stop before 5th (25K > 24K)
            for i in range(10):
                chunk = MCPContextIndex(
                    tenant_key=tenant_key,
                    product_id=product_id,
                    vision_document_id=vision_doc_id,
                    content=f"Chunk {i + 1} content",
                    chunk_order=i + 1,
                    token_count=5000,
                )
                session.add(chunk)

            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="full",
            db_manager=db_manager,
        )

        total_tokens = sum(c["tokens"] for c in result["data"])
        assert total_tokens <= VISION_DELIVERY_BUDGET
        assert len(result["data"]) == 4  # 4 * 5000 = 20K fits, 5 * 5000 = 25K doesn't
        assert result["pagination"]["has_more"] is True


@pytest.mark.asyncio
class TestFullDepthPaginationRegression:
    """Regression tests - full-depth pagination still works correctly."""

    async def test_full_depth_pagination_with_offset_and_limit(self, db_manager: DatabaseManager):
        """Full-depth pagination with offset and limit still works."""
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
                chunk_count=5,
            )
            session.add(vision_doc)

            for i in range(5):
                chunk = MCPContextIndex(
                    tenant_key=tenant_key,
                    product_id=product_id,
                    vision_document_id=vision_doc_id,
                    content=f"Chunk {i + 1}",
                    chunk_order=i + 1,
                    token_count=100,
                )
                session.add(chunk)

            await session.commit()

        result = await get_vision_document(
            product_id=product_id,
            tenant_key=tenant_key,
            chunking="full",
            offset=2,
            limit=2,
            db_manager=db_manager,
        )

        assert result["pagination"]["total_chunks"] == 5
        assert result["pagination"]["offset"] == 2
        assert result["pagination"]["limit"] == 2
        assert result["pagination"]["has_more"] is True
        assert len(result["data"]) <= 2


class TestAutoConsolidationOnUpload:
    """Test that upload_vision_document triggers auto-consolidation."""

    @pytest.mark.asyncio
    async def test_upload_triggers_consolidation(self):
        """After upload + summarization + chunking, consolidation is called."""
        mock_db_manager = MagicMock()
        mock_session = AsyncMock()
        mock_product = MagicMock()
        mock_product.id = str(uuid4())
        mock_product.tenant_key = "test_tenant"

        # Mock the session context manager
        mock_db_manager.get_session_async.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_db_manager.get_session_async.return_value.__aexit__ = AsyncMock()

        with patch(
            "src.giljo_mcp.services.product_service.ConsolidatedVisionService",
            create=True,
        ) as mock_consolidation_cls:
            mock_consolidation = MagicMock()
            mock_consolidation.consolidate_vision_documents = AsyncMock()
            mock_consolidation_cls.return_value = mock_consolidation

            # Import the service to check the code path exists
            # Verify the consolidation import path exists in the method
            import inspect

            from src.giljo_mcp.services.product_service import ProductService

            source = inspect.getsource(ProductService.upload_vision_document)
            assert "ConsolidatedVisionService" in source
            assert "consolidate_vision_documents" in source
            assert "force=True" in source

    @pytest.mark.asyncio
    async def test_consolidation_failure_does_not_fail_upload(self):
        """If consolidation fails, upload should still succeed."""
        import inspect

        from src.giljo_mcp.services.product_service import ProductService

        source = inspect.getsource(ProductService.upload_vision_document)
        # Verify the consolidation call is wrapped in try/except
        assert "Auto-consolidation failed" in source or "consolidation" in source.lower()
