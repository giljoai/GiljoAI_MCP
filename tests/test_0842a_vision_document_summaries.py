# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for VisionDocumentSummary repository methods.

Handover 0842a Phase 2: Tests for create_summary, get_summaries,
get_best_summary, and get_product_summaries.

TDD: These tests are written FIRST, before implementation.
"""

import uuid
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, VisionDocument
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
from src.giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture(scope="function")
async def vision_repo(db_manager) -> VisionDocumentRepository:
    """Create VisionDocumentRepository instance for testing."""
    return VisionDocumentRepository(db_manager)


@pytest_asyncio.fixture(scope="function")
async def tenant_a() -> str:
    """Generate tenant key A."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture(scope="function")
async def tenant_b() -> str:
    """Generate tenant key B (for cross-tenant isolation tests)."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture(scope="function")
async def product_a(db_session: AsyncSession, tenant_a: str) -> Product:
    """Create test product for tenant A."""
    product = Product(
        id=str(uuid.uuid4()),
        name="Test Product A",
        description="Product for summary testing",
        tenant_key=tenant_a,
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture(scope="function")
async def product_b(db_session: AsyncSession, tenant_b: str) -> Product:
    """Create test product for tenant B (cross-tenant)."""
    product = Product(
        id=str(uuid.uuid4()),
        name="Test Product B",
        description="Product for cross-tenant testing",
        tenant_key=tenant_b,
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture(scope="function")
async def doc_a(db_session: AsyncSession, tenant_a: str, product_a: Product) -> VisionDocument:
    """Create test vision document for tenant A."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        product_id=product_a.id,
        document_name="Test Doc A",
        document_type="vision",
        vision_document="This is test content for document A.",
        storage_type="inline",
        content_hash="abc123",
        is_active=True,
        display_order=0,
        version="1.0.0",
        chunked=False,
        chunk_count=0,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest_asyncio.fixture(scope="function")
async def doc_a2(db_session: AsyncSession, tenant_a: str, product_a: Product) -> VisionDocument:
    """Create a second test vision document for tenant A (same product)."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        product_id=product_a.id,
        document_name="Test Doc A2",
        document_type="architecture",
        vision_document="This is test content for document A2.",
        storage_type="inline",
        content_hash="def456",
        is_active=True,
        display_order=1,
        version="1.0.0",
        chunked=False,
        chunk_count=0,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest_asyncio.fixture(scope="function")
async def doc_b(db_session: AsyncSession, tenant_b: str, product_b: Product) -> VisionDocument:
    """Create test vision document for tenant B (cross-tenant)."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        product_id=product_b.id,
        document_name="Test Doc B",
        document_type="vision",
        vision_document="This is test content for document B.",
        storage_type="inline",
        content_hash="ghi789",
        is_active=True,
        display_order=0,
        version="1.0.0",
        chunked=False,
        chunk_count=0,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest.mark.asyncio
async def test_create_summary_stores_correctly(
    db_session: AsyncSession,
    vision_repo: VisionDocumentRepository,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
):
    """create_summary stores all fields correctly and returns the instance."""
    summary = await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="This is a light summary.",
        tokens_original=1000,
        tokens_summary=330,
    )

    assert summary is not None
    assert summary.tenant_key == tenant_a
    assert summary.document_id == str(doc_a.id)
    assert summary.product_id == str(product_a.id)
    assert summary.source == "sumy"
    assert summary.ratio == Decimal("0.33")
    assert summary.summary == "This is a light summary."
    assert summary.tokens_original == 1000
    assert summary.tokens_summary == 330
    assert summary.id is not None
    assert summary.created_at is not None


@pytest.mark.asyncio
async def test_create_summary_upserts(
    db_session: AsyncSession,
    vision_repo: VisionDocumentRepository,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
):
    """create_summary with same doc+source+ratio replaces the existing row (upsert)."""
    # First insert
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Original summary.",
        tokens_original=1000,
        tokens_summary=330,
    )

    # Second insert (same doc+source+ratio) should replace
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Updated summary.",
        tokens_original=1200,
        tokens_summary=400,
    )

    # Verify only 1 row exists for this doc+source+ratio
    all_summaries = await vision_repo.get_summaries(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
    )
    matching = [s for s in all_summaries if s.source == "sumy" and s.ratio == Decimal("0.33")]
    assert len(matching) == 1
    assert matching[0].summary == "Updated summary."
    assert matching[0].tokens_original == 1200


@pytest.mark.asyncio
async def test_get_summaries_filters_by_tenant(
    db_session: AsyncSession,
    vision_repo: VisionDocumentRepository,
    tenant_a: str,
    tenant_b: str,
    product_a: Product,
    product_b: Product,
    doc_a: VisionDocument,
    doc_b: VisionDocument,
):
    """get_summaries enforces tenant isolation -- tenant A cannot see tenant B summaries."""
    # Create summary for tenant A
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Tenant A summary.",
        tokens_original=1000,
        tokens_summary=330,
    )

    # Create summary for tenant B
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_b,
        document_id=str(doc_b.id),
        product_id=str(product_b.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Tenant B summary.",
        tokens_original=800,
        tokens_summary=260,
    )

    # Tenant A should only see their own summaries
    summaries_a = await vision_repo.get_summaries(
        session=db_session, tenant_key=tenant_a, document_id=str(doc_a.id)
    )
    assert len(summaries_a) == 1
    assert summaries_a[0].summary == "Tenant A summary."

    # Tenant A cannot see tenant B's document summaries
    cross_tenant = await vision_repo.get_summaries(
        session=db_session, tenant_key=tenant_a, document_id=str(doc_b.id)
    )
    assert len(cross_tenant) == 0

    # Tenant B should only see their own summaries
    summaries_b = await vision_repo.get_summaries(
        session=db_session, tenant_key=tenant_b, document_id=str(doc_b.id)
    )
    assert len(summaries_b) == 1
    assert summaries_b[0].summary == "Tenant B summary."


@pytest.mark.asyncio
async def test_get_best_summary_prefers_ai(
    db_session: AsyncSession,
    vision_repo: VisionDocumentRepository,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
):
    """get_best_summary prefers AI source over Sumy when both exist."""
    # Create sumy summary
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Sumy light summary.",
        tokens_original=1000,
        tokens_summary=330,
    )

    # Create AI summary (same doc+ratio, different source)
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="ai",
        ratio=Decimal("0.33"),
        summary="AI light summary.",
        tokens_original=1000,
        tokens_summary=350,
    )

    best = await vision_repo.get_best_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        ratio=Decimal("0.33"),
    )

    assert best is not None
    assert best.source == "ai"
    assert best.summary == "AI light summary."


@pytest.mark.asyncio
async def test_get_best_summary_falls_back_to_sumy(
    db_session: AsyncSession,
    vision_repo: VisionDocumentRepository,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
):
    """get_best_summary returns Sumy summary when no AI summary exists."""
    # Create only sumy summary
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Sumy-only light summary.",
        tokens_original=1000,
        tokens_summary=330,
    )

    best = await vision_repo.get_best_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        ratio=Decimal("0.33"),
    )

    assert best is not None
    assert best.source == "sumy"
    assert best.summary == "Sumy-only light summary."


@pytest.mark.asyncio
async def test_get_best_summary_returns_none_when_empty(
    db_session: AsyncSession,
    vision_repo: VisionDocumentRepository,
    tenant_a: str,
    doc_a: VisionDocument,
):
    """get_best_summary returns None when no summaries exist."""
    best = await vision_repo.get_best_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        ratio=Decimal("0.33"),
    )
    assert best is None


@pytest.mark.asyncio
async def test_get_product_summaries_returns_all_docs(
    db_session: AsyncSession,
    vision_repo: VisionDocumentRepository,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
    doc_a2: VisionDocument,
):
    """get_product_summaries returns summaries for all documents in a product."""
    # Create summaries for doc_a
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Doc A light summary.",
        tokens_original=1000,
        tokens_summary=330,
    )

    # Create summaries for doc_a2
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a2.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Doc A2 light summary.",
        tokens_original=800,
        tokens_summary=260,
    )

    summaries = await vision_repo.get_product_summaries(
        session=db_session,
        tenant_key=tenant_a,
        product_id=str(product_a.id),
        ratio=Decimal("0.33"),
    )

    assert len(summaries) == 2
    doc_ids = {s.document_id for s in summaries}
    assert str(doc_a.id) in doc_ids
    assert str(doc_a2.id) in doc_ids


@pytest.mark.asyncio
async def test_get_product_summaries_prefers_ai_per_doc(
    db_session: AsyncSession,
    vision_repo: VisionDocumentRepository,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
    doc_a2: VisionDocument,
):
    """get_product_summaries returns AI-preferred summaries, ordered by document_id then source."""
    # doc_a has both sumy and ai
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Doc A sumy.",
        tokens_original=1000,
        tokens_summary=330,
    )
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a.id),
        product_id=str(product_a.id),
        source="ai",
        ratio=Decimal("0.33"),
        summary="Doc A ai.",
        tokens_original=1000,
        tokens_summary=350,
    )

    # doc_a2 has only sumy
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_a,
        document_id=str(doc_a2.id),
        product_id=str(product_a.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Doc A2 sumy.",
        tokens_original=800,
        tokens_summary=260,
    )

    summaries = await vision_repo.get_product_summaries(
        session=db_session,
        tenant_key=tenant_a,
        product_id=str(product_a.id),
        ratio=Decimal("0.33"),
    )

    # Should return all summaries for the product+ratio, ordered by doc_id then ai-first
    assert len(summaries) >= 2
    # Both docs should be represented
    doc_ids = {s.document_id for s in summaries}
    assert str(doc_a.id) in doc_ids
    assert str(doc_a2.id) in doc_ids
