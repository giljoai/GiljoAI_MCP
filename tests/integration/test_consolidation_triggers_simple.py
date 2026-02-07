"""
Simple integration test for consolidated vision trigger functionality (Handover 0377 Phase 4).

Tests that the consolidation service can be called successfully without errors.
Full E2E endpoint testing deferred to Phase 5.
"""

import pytest

from src.giljo_mcp.models import Product, VisionDocument
from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService
from tests.fixtures.vision_document_fixtures import VisionDocumentTestData


@pytest.mark.asyncio
async def test_consolidation_service_with_vision_docs(db_session, tenant_manager):
    """
    Test that consolidation service can process vision documents without errors.

    This is a smoke test to verify the consolidation service works in async context.
    """
    # GIVEN: Product with vision documents
    tenant_key = tenant_manager.generate_tenant_key("test-consolidation")

    product = Product(
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for consolidation",
    )
    db_session.add(product)
    await db_session.flush()

    # Add vision documents
    for i in range(2):
        content = VisionDocumentTestData.generate_markdown_content(6000)
        doc = VisionDocument(
            tenant_key=tenant_key,
            product_id=product.id,
            document_name=f"Vision Doc {i + 1}",
            document_type="vision",
            storage_type="inline",
            vision_document=content,
            is_active=True,
            display_order=i,
        )
        db_session.add(doc)

    await db_session.flush()

    # WHEN: Run consolidation service
    consolidation_service = ConsolidatedVisionService()
    result = await consolidation_service.consolidate_vision_documents(
        product_id=product.id, session=db_session, tenant_key=tenant_key, force=True
    )

    # THEN: Consolidation succeeds
    assert result["success"] is True
    assert "light" in result
    assert "medium" in result
    # Token counts may be 0 if content is too simple for summarization
    # The important thing is the service runs without errors

    # THEN: Product fields updated (hash and timestamp always set)
    await db_session.refresh(product)
    assert product.consolidated_vision_hash is not None
    assert product.consolidated_at is not None
    # Light/medium summaries may be None or empty if content too simple
    # But at minimum the hash should be calculated


@pytest.mark.asyncio
async def test_consolidation_skip_no_changes(db_session, tenant_manager):
    """Test that consolidation skips when no changes detected."""
    # GIVEN: Product with vision doc and existing consolidation
    tenant_key = tenant_manager.generate_tenant_key("test-skip")

    product = Product(
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product",
    )
    db_session.add(product)
    await db_session.flush()

    content = VisionDocumentTestData.generate_markdown_content(6000)
    doc = VisionDocument(
        tenant_key=tenant_key,
        product_id=product.id,
        document_name="Vision Doc",
        document_type="vision",
        storage_type="inline",
        vision_document=content,
        is_active=True,
    )
    db_session.add(doc)
    await db_session.flush()

    # Run initial consolidation
    consolidation_service = ConsolidatedVisionService()
    first_result = await consolidation_service.consolidate_vision_documents(
        product_id=product.id, session=db_session, tenant_key=tenant_key, force=True
    )
    assert first_result["success"] is True

    # WHEN: Run consolidation again without changes
    second_result = await consolidation_service.consolidate_vision_documents(
        product_id=product.id,
        session=db_session,
        tenant_key=tenant_key,
        force=False,  # Don't force
    )

    # THEN: Second consolidation skipped
    assert second_result["success"] is False
    assert second_result["error"] == "no_changes"


@pytest.mark.asyncio
async def test_consolidation_multi_tenant_isolation(db_session, tenant_manager):
    """Test that consolidation respects multi-tenant isolation."""
    # GIVEN: Two products from different tenants
    tenant_a = tenant_manager.generate_tenant_key("tenant-a")
    tenant_b = tenant_manager.generate_tenant_key("tenant-b")

    product_a = Product(
        tenant_key=tenant_a,
        name="Product A",
        description="Tenant A product",
    )
    db_session.add(product_a)
    await db_session.flush()

    # WHEN: Try to consolidate with wrong tenant key
    consolidation_service = ConsolidatedVisionService()
    result = await consolidation_service.consolidate_vision_documents(
        product_id=product_a.id,
        session=db_session,
        tenant_key=tenant_b,  # Wrong tenant!
        force=False,
    )

    # THEN: Consolidation fails (tenant isolation)
    assert result["success"] is False
    assert result["error"] == "product_not_found"
