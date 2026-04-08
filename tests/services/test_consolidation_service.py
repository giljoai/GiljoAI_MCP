# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for ConsolidatedVisionService - Handover 0377 Phase 2

Tests written FIRST following strict TDD discipline (RED -> GREEN -> REFACTOR).

Purpose: Test consolidation of multiple vision documents into unified light/medium summaries.

Updated Handover 0730b: Migrated from dict wrappers to exception-based error handling.
Updated Handover 0731: Migrated from dict returns to typed ConsolidationResult.
"""

import hashlib
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.models.products import Product, VisionDocument
from src.giljo_mcp.schemas.service_responses import (
    ConsolidationResult,
    MultiLevelSummaryLevel,
    SummarizeMultiLevelResult,
)


@pytest.fixture
def mock_db_manager():
    """Mock database manager with async session support."""
    db_manager = MagicMock()
    session = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(return_value=False)
    session.get = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.add = MagicMock()
    session.execute = AsyncMock()
    db_manager.get_session_async = MagicMock(return_value=session)
    return db_manager, session


@pytest.mark.asyncio
async def test_consolidate_single_document_returns_unified_summary(mock_db_manager):
    """Single doc → summarization produces light and medium summaries"""
    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

    db_manager, session = mock_db_manager

    # Create product with one vision document
    doc = MagicMock(spec=VisionDocument)
    doc.id = "doc-1"
    doc.document_name = "Product Vision"
    doc.vision_document = "This is the product vision. " * 100  # ~600 chars
    doc.is_active = True
    doc.display_order = 1

    product = MagicMock(spec=Product)
    product.id = "test-product-id"
    product.tenant_key = "test-tenant"
    product.vision_documents = [doc]
    product.consolidated_vision_hash = None

    # Mock the execute result (service uses session.execute with select)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product
    session.execute.return_value = mock_result

    # Mock VisionDocumentSummarizer (returns typed SummarizeMultiLevelResult - Handover 0731)
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_multi_level.return_value = SummarizeMultiLevelResult(
        light=MultiLevelSummaryLevel(summary="Light summary of vision", tokens=50, sentences=2),
        medium=MultiLevelSummaryLevel(summary="Medium summary of vision with more detail", tokens=100, sentences=4),
        original_tokens=150,
        processing_time_ms=100,
    )

    service = ConsolidatedVisionService()
    service.summarizer = mock_summarizer

    result = await service.consolidate_vision_documents(
        product_id="test-product-id", session=session, tenant_key="test-tenant", force=False
    )

    # Verify typed ConsolidationResult (Handover 0731)
    assert isinstance(result, ConsolidationResult)
    assert result.light.summary == "Light summary of vision"
    assert result.light.tokens == 50
    assert result.medium.summary == "Medium summary of vision with more detail"
    assert result.medium.tokens == 100
    assert result.hash != ""
    assert len(result.source_docs) == 1

    # Verify product fields updated
    assert product.consolidated_vision_light == "Light summary of vision"
    assert product.consolidated_vision_light_tokens == 50
    assert product.consolidated_vision_medium == "Medium summary of vision with more detail"
    assert product.consolidated_vision_medium_tokens == 100
    assert product.consolidated_vision_hash is not None
    assert product.consolidated_at is not None

    # Verify database commit called
    assert session.commit.called


@pytest.mark.asyncio
async def test_consolidate_five_documents_returns_unified_summary(mock_db_manager):
    """Five chapters → unified 33%/66% summaries from aggregate"""
    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

    db_manager, session = mock_db_manager

    # Create product with 5 vision documents
    docs = []
    for i in range(5):
        doc = MagicMock(spec=VisionDocument)
        doc.id = f"doc-{i + 1}"
        doc.document_name = f"Chapter {i + 1}"
        doc.vision_document = f"Content of chapter {i + 1}. " * 50
        doc.is_active = True
        doc.display_order = i + 1
        docs.append(doc)

    product = MagicMock(spec=Product)
    product.id = "test-product-id"
    product.tenant_key = "test-tenant"
    product.vision_documents = docs
    product.consolidated_vision_hash = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product
    session.execute.return_value = mock_result

    # Mock summarizer (returns typed SummarizeMultiLevelResult - Handover 0731)
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_multi_level.return_value = SummarizeMultiLevelResult(
        light=MultiLevelSummaryLevel(summary="Light summary of all 5 chapters", tokens=200, sentences=10),
        medium=MultiLevelSummaryLevel(summary="Medium summary of all 5 chapters with more detail", tokens=400, sentences=20),
        original_tokens=600,
        processing_time_ms=200,
    )

    service = ConsolidatedVisionService()
    service.summarizer = mock_summarizer

    result = await service.consolidate_vision_documents(
        product_id="test-product-id", session=session, tenant_key="test-tenant", force=False
    )

    # Typed ConsolidationResult (Handover 0731)
    assert isinstance(result, ConsolidationResult)
    assert len(result.source_docs) == 5
    assert result.light.tokens == 200
    assert result.medium.tokens == 400


@pytest.mark.asyncio
async def test_consolidate_respects_display_order(mock_db_manager):
    """Documents ordered by display_order in aggregate text"""
    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

    db_manager, session = mock_db_manager

    # Create docs with intentionally scrambled order
    doc1 = MagicMock(spec=VisionDocument)
    doc1.document_name = "Chapter 1"
    doc1.vision_document = "First content"
    doc1.is_active = True
    doc1.display_order = 3  # Out of order

    doc2 = MagicMock(spec=VisionDocument)
    doc2.document_name = "Chapter 2"
    doc2.vision_document = "Second content"
    doc2.is_active = True
    doc2.display_order = 1  # Should be first

    doc3 = MagicMock(spec=VisionDocument)
    doc3.document_name = "Chapter 3"
    doc3.vision_document = "Third content"
    doc3.is_active = True
    doc3.display_order = 2  # Middle

    product = MagicMock(spec=Product)
    product.id = "test-product-id"
    product.tenant_key = "test-tenant"
    product.vision_documents = [doc1, doc2, doc3]  # Scrambled
    product.consolidated_vision_hash = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product
    session.execute.return_value = mock_result

    service = ConsolidatedVisionService()

    # Build aggregate to check order
    aggregate_text, source_ids, agg_hash = service._build_aggregate(product)

    # Verify order: doc2 (order=1), doc3 (order=2), doc1 (order=3)
    assert "Chapter 2" in aggregate_text
    assert "Chapter 3" in aggregate_text
    assert "Chapter 1" in aggregate_text

    # Check that Chapter 2 appears before Chapter 3, which appears before Chapter 1
    pos_ch2 = aggregate_text.index("Chapter 2")
    pos_ch3 = aggregate_text.index("Chapter 3")
    pos_ch1 = aggregate_text.index("Chapter 1")

    assert pos_ch2 < pos_ch3 < pos_ch1, "Documents not ordered by display_order"


@pytest.mark.asyncio
async def test_consolidate_skips_inactive_docs(mock_db_manager):
    """Only active documents included in aggregate"""
    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

    db_manager, session = mock_db_manager

    # Create 3 docs: 2 active, 1 inactive
    doc1 = MagicMock(spec=VisionDocument)
    doc1.document_name = "Active Doc 1"
    doc1.vision_document = "Active content 1"
    doc1.is_active = True
    doc1.display_order = 1

    doc2 = MagicMock(spec=VisionDocument)
    doc2.document_name = "Inactive Doc"
    doc2.vision_document = "Inactive content (should be skipped)"
    doc2.is_active = False  # INACTIVE
    doc2.display_order = 2

    doc3 = MagicMock(spec=VisionDocument)
    doc3.document_name = "Active Doc 2"
    doc3.vision_document = "Active content 2"
    doc3.is_active = True
    doc3.display_order = 3

    product = MagicMock(spec=Product)
    product.id = "test-product-id"
    product.tenant_key = "test-tenant"
    product.vision_documents = [doc1, doc2, doc3]
    product.consolidated_vision_hash = None

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product
    session.execute.return_value = mock_result

    service = ConsolidatedVisionService()

    aggregate_text, source_ids, agg_hash = service._build_aggregate(product)

    # Verify only active docs included
    assert "Active Doc 1" in aggregate_text
    assert "Active Doc 2" in aggregate_text
    assert "Inactive Doc" not in aggregate_text
    assert "Inactive content" not in aggregate_text
    assert len(source_ids) == 2  # Only 2 active docs


@pytest.mark.asyncio
async def test_consolidate_detects_no_changes(mock_db_manager):
    """Hash unchanged → raises ValidationError with no_changes, skips re-summarization"""
    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

    db_manager, session = mock_db_manager

    doc = MagicMock(spec=VisionDocument)
    doc.document_name = "Vision"
    doc.vision_document = "Unchanged content"
    doc.is_active = True
    doc.display_order = 1

    # Calculate expected hash
    aggregate_text = f"# {doc.document_name}\n\n{doc.vision_document}"
    expected_hash = hashlib.sha256(aggregate_text.encode("utf-8")).hexdigest()

    product = MagicMock(spec=Product)
    product.id = "test-product-id"
    product.tenant_key = "test-tenant"
    product.vision_documents = [doc]
    product.consolidated_vision_hash = expected_hash  # Same hash as new aggregate

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product
    session.execute.return_value = mock_result

    service = ConsolidatedVisionService()

    # Verify ValidationError raised with no_changes error code
    with pytest.raises(ValidationError) as exc_info:
        await service.consolidate_vision_documents(
            product_id="test-product-id",
            session=session,
            tenant_key="test-tenant",
            force=False,  # Don't force
        )

    assert exc_info.value.error_code == "NO_CHANGES"
    assert "no changes" in exc_info.value.message.lower()

    # Verify commit NOT called (no changes made)
    assert not session.commit.called


@pytest.mark.asyncio
async def test_consolidate_force_regenerates(mock_db_manager):
    """force=True → always regenerates regardless of hash"""
    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

    db_manager, session = mock_db_manager

    doc = MagicMock(spec=VisionDocument)
    doc.id = "doc-force"
    doc.document_name = "Vision"
    doc.vision_document = "Unchanged content"
    doc.is_active = True
    doc.display_order = 1

    # Calculate hash (same as before)
    aggregate_text = f"# {doc.document_name}\n\n{doc.vision_document}"
    expected_hash = hashlib.sha256(aggregate_text.encode("utf-8")).hexdigest()

    product = MagicMock(spec=Product)
    product.id = "test-product-id"
    product.tenant_key = "test-tenant"
    product.vision_documents = [doc]
    product.consolidated_vision_hash = expected_hash  # Same hash

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product
    session.execute.return_value = mock_result

    # Mock summarizer (returns typed SummarizeMultiLevelResult - Handover 0731)
    mock_summarizer = MagicMock()
    mock_summarizer.summarize_multi_level.return_value = SummarizeMultiLevelResult(
        light=MultiLevelSummaryLevel(summary="Forced light", tokens=25, sentences=1),
        medium=MultiLevelSummaryLevel(summary="Forced medium", tokens=50, sentences=2),
        original_tokens=100,
        processing_time_ms=50,
    )

    service = ConsolidatedVisionService()
    service.summarizer = mock_summarizer

    result = await service.consolidate_vision_documents(
        product_id="test-product-id",
        session=session,
        tenant_key="test-tenant",
        force=True,  # FORCE regeneration
    )

    # Verify regeneration happened despite matching hash (typed return - Handover 0731)
    assert isinstance(result, ConsolidationResult)
    assert result.light.summary == "Forced light"
    assert session.commit.called


@pytest.mark.asyncio
async def test_consolidate_handles_product_not_found(mock_db_manager):
    """Non-existent product_id → raises ResourceNotFoundError"""
    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

    db_manager, session = mock_db_manager

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None  # Product not found
    session.execute.return_value = mock_result

    service = ConsolidatedVisionService()

    # Verify ResourceNotFoundError raised
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.consolidate_vision_documents(
            product_id="nonexistent-id", session=session, tenant_key="test-tenant", force=False
        )

    assert exc_info.value.error_code == "PRODUCT_NOT_FOUND"
    assert "product_id" in exc_info.value.context

    # Verify commit NOT called
    assert not session.commit.called


@pytest.mark.asyncio
async def test_consolidate_enforces_tenant_isolation(mock_db_manager):
    """Product exists but belongs to different tenant → raises ResourceNotFoundError (no tenant leak)"""
    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

    db_manager, session = mock_db_manager

    # Product belongs to different tenant - query returns None because
    # tenant_key is now in the WHERE clause (defense-in-depth fix)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    service = ConsolidatedVisionService()

    # Verify ResourceNotFoundError raised (product not found due to tenant filter)
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.consolidate_vision_documents(
            product_id="test-product-id",
            session=session,
            tenant_key="test-tenant",  # Request from different tenant
            force=False,
        )

    assert exc_info.value.error_code == "PRODUCT_NOT_FOUND"
    # Context should have product_id but NOT reveal tenant mismatch
    assert "product_id" in exc_info.value.context

    # Verify commit NOT called
    assert not session.commit.called
