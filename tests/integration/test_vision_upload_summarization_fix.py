"""
Integration tests for vision document summarization bug fix (Handover 0352).

Tests the fix for incorrect dictionary key access in ProductService.upload_vision_document()
where code was accessing summaries["moderate"] and summaries["heavy"] instead of
summaries["light"] and summaries["medium"] (matching vision_summarizer.py output).

Bug Location: src/giljo_mcp/services/product_service.py lines 1220-1225
Fix: Update key access to match VisionDocumentSummarizer.summarize_multi_level() output
"""

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, VisionDocument
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture
async def test_product(db_session: AsyncSession) -> Product:
    """Create test product for vision document testing"""
    tenant_key = TenantManager.generate_tenant_key()

    product = Product(
        tenant_key=tenant_key,
        name="Test Vision Summarization Product",
        description="Product for testing vision document summarization bug fix",
        is_active=True,
    )

    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)

    return product


@pytest_asyncio.fixture
async def product_service(db_session: AsyncSession, db_manager, test_product: Product) -> ProductService:
    """Create ProductService instance for testing"""
    service = ProductService(
        db_manager=db_manager,
        tenant_key=test_product.tenant_key,
        test_session=db_session,
    )
    return service


class TestVisionDocumentSummarizationFix:
    """Test correct dictionary key access for vision document summaries"""

    @pytest.mark.asyncio
    async def test_upload_vision_document_with_summarization_uses_correct_keys(
        self,
        product_service: ProductService,
        test_product: Product,
        db_session: AsyncSession,
    ):
        """
        Test that uploading a vision document (>100 tokens) generates summaries
        and stores them using the correct database field names.

        This test verifies the fix for Handover 0352 bug where ProductService was
        accessing summaries["moderate"] and summaries["heavy"] instead of
        summaries["light"] and summaries["medium"].

        Updated threshold: ALL documents >100 tokens are now summarized (was 5K).
        """
        # Create content > 100 tokens to trigger summarization
        # 1 token ≈ 4 chars, so 100 tokens ≈ 400 chars
        content = "This is test content. " * 30  # ~660 chars ≈ 165 tokens

        # Upload vision document (should trigger summarization)
        result = await product_service.upload_vision_document(
            product_id=test_product.id,
            content=content,
            filename="test_vision_with_summary.md",
            auto_chunk=False,  # Disable chunking to focus on summarization
        )

        # Verify upload succeeded
        assert result["success"] is True
        assert "document_id" in result
        doc_id = result["document_id"]

        # Verify document in database
        from sqlalchemy import select

        stmt = select(VisionDocument).where(VisionDocument.id == doc_id)
        db_result = await db_session.execute(stmt)
        doc = db_result.scalar_one()

        # Verify document exists and has correct properties
        assert doc is not None
        assert doc.document_name == "test_vision_with_summary.md"
        assert doc.product_id == test_product.id

        # CRITICAL: Verify summarization fields are populated correctly
        assert doc.is_summarized is True
        assert doc.original_token_count > 100

        # Verify CORRECT fields are populated (light, medium)
        assert doc.summary_light is not None
        assert doc.summary_medium is not None
        assert doc.summary_light_tokens is not None
        assert doc.summary_medium_tokens is not None

        # Verify summaries are not empty
        assert len(doc.summary_light) > 0
        assert len(doc.summary_medium) > 0

        # Verify token counts are reasonable
        assert doc.summary_light_tokens < doc.original_token_count
        assert doc.summary_medium_tokens < doc.original_token_count
        assert doc.summary_light_tokens < doc.summary_medium_tokens  # Light should be smaller

        # Verify backward compatibility field is set
        assert doc.summary_text is not None  # Should be set to medium summary for compat

    @pytest.mark.asyncio
    async def test_upload_tiny_document_under_100_tokens_skips_summarization(
        self,
        product_service: ProductService,
        test_product: Product,
        db_session: AsyncSession,
    ):
        """
        Test that tiny documents (<100 tokens) skip summarization.

        Updated threshold: Only documents >100 tokens are summarized.
        This test verifies tiny documents are NOT summarized.
        """
        # Create content < 100 tokens
        # 1 token ≈ 4 chars, so 100 tokens ≈ 400 chars
        content = "Tiny document. " * 5  # ~75 chars ≈ 19 tokens

        result = await product_service.upload_vision_document(
            product_id=test_product.id,
            content=content,
            filename="tiny_vision.md",
            auto_chunk=False,
        )

        assert result["success"] is True
        doc_id = result["document_id"]

        # Verify document in database
        from sqlalchemy import select

        stmt = select(VisionDocument).where(VisionDocument.id == doc_id)
        db_result = await db_session.execute(stmt)
        doc = db_result.scalar_one()

        # Verify summarization was NOT triggered (document too small)
        assert doc.is_summarized is False
        assert doc.summary_light is None
        assert doc.summary_medium is None
        assert doc.summary_light_tokens is None
        assert doc.summary_medium_tokens is None

    @pytest.mark.asyncio
    async def test_upload_document_above_100_tokens_is_summarized(
        self,
        product_service: ProductService,
        test_product: Product,
        db_session: AsyncSession,
    ):
        """
        Test that documents above 100 tokens ARE summarized.

        Updated threshold: ALL documents >100 tokens are now summarized (was 5K).
        This test verifies the new 100-token threshold works correctly.
        """
        # Create content > 100 tokens
        # 1 token ≈ 4 chars, so 100 tokens ≈ 400 chars
        content = "Document content for testing. " * 20  # ~600 chars ≈ 150 tokens

        result = await product_service.upload_vision_document(
            product_id=test_product.id,
            content=content,
            filename="medium_vision.md",
            auto_chunk=False,
        )

        assert result["success"] is True
        doc_id = result["document_id"]

        # Verify document in database
        from sqlalchemy import select

        stmt = select(VisionDocument).where(VisionDocument.id == doc_id)
        db_result = await db_session.execute(stmt)
        doc = db_result.scalar_one()

        # Verify summarization WAS triggered (new behavior)
        assert doc.is_summarized is True
        assert doc.summary_light is not None
        assert doc.summary_medium is not None
        assert doc.summary_light_tokens is not None
        assert doc.summary_medium_tokens is not None
        assert doc.original_token_count > 100

    @pytest.mark.asyncio
    async def test_summarization_failure_does_not_block_upload(
        self,
        product_service: ProductService,
        test_product: Product,
        db_session: AsyncSession,
        monkeypatch,
    ):
        """
        Test that if summarization fails, document upload still succeeds.

        This verifies the try-except block in upload_vision_document handles failures.
        """
        # Mock VisionDocumentSummarizer to raise exception
        def mock_summarize_multi_level(*args, **kwargs):
            raise RuntimeError("Summarization service unavailable")

        from src.giljo_mcp.services import vision_summarizer

        monkeypatch.setattr(
            vision_summarizer.VisionDocumentSummarizer,
            "summarize_multi_level",
            mock_summarize_multi_level,
        )

        # Create large content to trigger summarization attempt
        content = "This is test content. " * 1000  # ~5,500 tokens

        result = await product_service.upload_vision_document(
            product_id=test_product.id,
            content=content,
            filename="test_fail_summarization.md",
            auto_chunk=False,
        )

        # Upload should still succeed despite summarization failure
        assert result["success"] is True
        assert "document_id" in result
        doc_id = result["document_id"]

        # Verify document exists but is not summarized
        from sqlalchemy import select

        stmt = select(VisionDocument).where(VisionDocument.id == doc_id)
        db_result = await db_session.execute(stmt)
        doc = db_result.scalar_one()

        assert doc is not None
        assert doc.is_summarized is False  # Summarization failed
        assert doc.summary_light is None
        assert doc.summary_medium is None


class TestVisionSummarizerOutputStructure:
    """Test VisionDocumentSummarizer returns correct dictionary structure"""

    def test_summarize_multi_level_returns_light_and_medium_keys(self):
        """
        Test that VisionDocumentSummarizer.summarize_multi_level() returns
        dictionary with "light" and "medium" keys (NOT "moderate" and "heavy").

        This test documents the expected output structure from vision_summarizer.py.
        """
        from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

        summarizer = VisionDocumentSummarizer()

        # Create test content > 500 tokens (minimum for meaningful summary)
        test_content = "This is a test sentence. " * 100  # ~500 words

        result = summarizer.summarize_multi_level(test_content)

        # Verify result structure matches expected keys
        assert "light" in result
        assert "medium" in result
        assert "original_tokens" in result
        assert "processing_time_ms" in result

        # Verify DEPRECATED keys are NOT in result
        assert "moderate" not in result
        assert "heavy" not in result

        # Verify each level has required fields
        assert "summary" in result["light"]
        assert "tokens" in result["light"]
        assert "sentences" in result["light"]

        assert "summary" in result["medium"]
        assert "tokens" in result["medium"]
        assert "sentences" in result["medium"]
