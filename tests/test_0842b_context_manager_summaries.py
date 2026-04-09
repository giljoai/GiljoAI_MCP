# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for Context Manager summary reads from vision_document_summaries table.

Handover 0842b: Validates that _get_summary_response() reads from the new
vision_document_summaries table (AI-preferred) with fallback to
Product.consolidated_vision_* columns.

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
from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document


@pytest_asyncio.fixture(scope="function")
async def vision_repo(db_manager) -> VisionDocumentRepository:
    """Create VisionDocumentRepository instance for testing."""
    return VisionDocumentRepository(db_manager)


@pytest_asyncio.fixture(scope="function")
async def tenant_key() -> str:
    """Generate a unique tenant key for each test."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture(scope="function")
async def product_with_consolidated(
    db_session: AsyncSession, tenant_key: str
) -> Product:
    """Create a product with consolidated vision columns populated (for fallback)."""
    product = Product(
        id=str(uuid.uuid4()),
        name="Product With Summaries",
        description="Product for 0842b context manager summary tests",
        tenant_key=tenant_key,
        is_active=True,
        product_memory={},
        consolidated_vision_light="Fallback light summary from consolidated column.",
        consolidated_vision_light_tokens=50,
        consolidated_vision_medium="Fallback medium summary from consolidated column.",
        consolidated_vision_medium_tokens=80,
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture(scope="function")
async def active_doc(
    db_session: AsyncSession, tenant_key: str, product_with_consolidated: Product
) -> VisionDocument:
    """Create a single active, chunked vision document."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product_with_consolidated.id,
        document_name="Requirements Spec",
        document_type="vision",
        vision_document="Full content of the requirements spec document.",
        storage_type="inline",
        content_hash="hash_active_doc",
        is_active=True,
        display_order=0,
        version="1.0.0",
        chunked=True,
        chunk_count=3,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest_asyncio.fixture(scope="function")
async def active_doc_2(
    db_session: AsyncSession, tenant_key: str, product_with_consolidated: Product
) -> VisionDocument:
    """Create a second active, chunked vision document for multi-doc tests."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product_with_consolidated.id,
        document_name="Architecture Overview",
        document_type="architecture",
        vision_document="Full content of the architecture overview document.",
        storage_type="inline",
        content_hash="hash_active_doc_2",
        is_active=True,
        display_order=1,
        version="1.0.0",
        chunked=True,
        chunk_count=2,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest.mark.asyncio
async def test_light_depth_returns_ai_summary_when_both_exist(
    db_session: AsyncSession,
    db_manager,
    vision_repo: VisionDocumentRepository,
    tenant_key: str,
    product_with_consolidated: Product,
    active_doc: VisionDocument,
):
    """When both sumy and ai summaries exist at ratio 0.33, AI summary is preferred."""
    # Create sumy summary
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(active_doc.id),
        product_id=str(product_with_consolidated.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Sumy light summary of requirements spec.",
        tokens_original=1000,
        tokens_summary=330,
    )

    # Create AI summary (should be preferred)
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(active_doc.id),
        product_id=str(product_with_consolidated.id),
        source="ai",
        ratio=Decimal("0.33"),
        summary="AI light summary of requirements spec.",
        tokens_original=1000,
        tokens_summary=350,
    )

    result = await get_vision_document(
        product_id=str(product_with_consolidated.id),
        tenant_key=tenant_key,
        chunking="light",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert result["depth"] == "light"
    assert "AI light summary of requirements spec." in result["data"]["summary"]
    assert "Sumy light summary" not in result["data"]["summary"]


@pytest.mark.asyncio
async def test_light_depth_returns_sumy_when_only_sumy_exists(
    db_session: AsyncSession,
    db_manager,
    vision_repo: VisionDocumentRepository,
    tenant_key: str,
    product_with_consolidated: Product,
    active_doc: VisionDocument,
):
    """When only sumy summary exists at ratio 0.33, it is returned."""
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(active_doc.id),
        product_id=str(product_with_consolidated.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Sumy-only light summary of requirements.",
        tokens_original=1000,
        tokens_summary=330,
    )

    result = await get_vision_document(
        product_id=str(product_with_consolidated.id),
        tenant_key=tenant_key,
        chunking="light",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert result["depth"] == "light"
    assert "Sumy-only light summary of requirements." in result["data"]["summary"]


@pytest.mark.asyncio
async def test_medium_depth_returns_ai_summary_when_both_exist(
    db_session: AsyncSession,
    db_manager,
    vision_repo: VisionDocumentRepository,
    tenant_key: str,
    product_with_consolidated: Product,
    active_doc: VisionDocument,
):
    """When both sumy and ai summaries exist at ratio 0.66, AI summary is preferred."""
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(active_doc.id),
        product_id=str(product_with_consolidated.id),
        source="sumy",
        ratio=Decimal("0.66"),
        summary="Sumy medium summary of requirements spec.",
        tokens_original=1000,
        tokens_summary=660,
    )

    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(active_doc.id),
        product_id=str(product_with_consolidated.id),
        source="ai",
        ratio=Decimal("0.66"),
        summary="AI medium summary of requirements spec.",
        tokens_original=1000,
        tokens_summary=680,
    )

    result = await get_vision_document(
        product_id=str(product_with_consolidated.id),
        tenant_key=tenant_key,
        chunking="medium",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert result["depth"] == "medium"
    assert "AI medium summary of requirements spec." in result["data"]["summary"]
    assert "Sumy medium summary" not in result["data"]["summary"]


@pytest.mark.asyncio
async def test_medium_depth_returns_sumy_when_only_sumy_exists(
    db_session: AsyncSession,
    db_manager,
    vision_repo: VisionDocumentRepository,
    tenant_key: str,
    product_with_consolidated: Product,
    active_doc: VisionDocument,
):
    """When only sumy summary exists at ratio 0.66, it is returned."""
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(active_doc.id),
        product_id=str(product_with_consolidated.id),
        source="sumy",
        ratio=Decimal("0.66"),
        summary="Sumy-only medium summary of requirements.",
        tokens_original=1000,
        tokens_summary=660,
    )

    result = await get_vision_document(
        product_id=str(product_with_consolidated.id),
        tenant_key=tenant_key,
        chunking="medium",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert result["depth"] == "medium"
    assert "Sumy-only medium summary of requirements." in result["data"]["summary"]


@pytest.mark.asyncio
async def test_multi_document_aggregation(
    db_session: AsyncSession,
    db_manager,
    vision_repo: VisionDocumentRepository,
    tenant_key: str,
    product_with_consolidated: Product,
    active_doc: VisionDocument,
    active_doc_2: VisionDocument,
):
    """Multiple documents produce headers with doc names and concatenated summaries."""
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(active_doc.id),
        product_id=str(product_with_consolidated.id),
        source="ai",
        ratio=Decimal("0.33"),
        summary="AI summary for requirements spec document.",
        tokens_original=1000,
        tokens_summary=350,
    )

    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(active_doc_2.id),
        product_id=str(product_with_consolidated.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Sumy summary for architecture overview document.",
        tokens_original=800,
        tokens_summary=260,
    )

    result = await get_vision_document(
        product_id=str(product_with_consolidated.id),
        tenant_key=tenant_key,
        chunking="light",
        db_manager=db_manager,
        _test_session=db_session,
    )

    summary_text = result["data"]["summary"]
    # Both document names should appear as headers
    assert "# Requirements Spec" in summary_text
    assert "# Architecture Overview" in summary_text
    # Both summaries should be present
    assert "AI summary for requirements spec document." in summary_text
    assert "Sumy summary for architecture overview document." in summary_text


@pytest.mark.asyncio
async def test_fallback_to_consolidated_when_no_summaries(
    db_session: AsyncSession,
    db_manager,
    tenant_key: str,
    product_with_consolidated: Product,
    active_doc: VisionDocument,
):
    """When no rows exist in vision_document_summaries, fall back to consolidated columns."""
    # No summaries created -- should fall back to product.consolidated_vision_light
    result = await get_vision_document(
        product_id=str(product_with_consolidated.id),
        tenant_key=tenant_key,
        chunking="light",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert result["depth"] == "light"
    assert result["data"]["summary"] == "Fallback light summary from consolidated column."
    assert result["data"]["tokens"] == 50
