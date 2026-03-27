"""
E2E integration tests for the vision document analysis feature.

Handover 0842e (session 5 of 5): Validates the complete flow from
vision document retrieval through AI analysis writing to context
manager reads, including AI-preference logic and partial field merging.
"""

import uuid
from decimal import Decimal
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, VisionDocument, VisionDocumentSummary
from src.giljo_mcp.models.products import (
    ProductArchitecture,
    ProductTechStack,
    ProductTestConfig,
)
from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository
from src.giljo_mcp.tenant import TenantManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture(scope="function")
async def vision_repo(db_manager) -> VisionDocumentRepository:
    """Create VisionDocumentRepository instance for testing."""
    return VisionDocumentRepository(db_manager)


@pytest_asyncio.fixture(scope="function")
async def tenant_key() -> str:
    """Generate a unique tenant key for each test."""
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture(scope="function")
async def product(db_session: AsyncSession, tenant_key: str) -> Product:
    """Create a test product with custom extraction instructions."""
    p = Product(
        id=str(uuid.uuid4()),
        name="E2E Test Product",
        description="Product for E2E vision analysis testing",
        tenant_key=tenant_key,
        is_active=True,
        product_memory={},
        extraction_custom_instructions="Focus on mobile architecture",
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture(scope="function")
async def vision_doc(
    db_session: AsyncSession, tenant_key: str, product: Product
) -> VisionDocument:
    """Create an active vision document for the product."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        document_name="Product Vision",
        document_type="vision",
        vision_document=(
            "This product is a mobile-first platform for real-time collaboration. "
            "It uses React Native for the frontend and FastAPI for the backend. "
            "The architecture follows event-driven microservices with PostgreSQL "
            "as the primary datastore. Testing strategy is TDD with pytest and Jest. "
            "Target coverage is 90 percent."
        ),
        storage_type="inline",
        content_hash="e2e_hash_001",
        is_active=True,
        display_order=0,
        version="1.0.0",
        chunked=False,
        chunk_count=0,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


# ---------------------------------------------------------------------------
# Test 1: Full AI Analysis Flow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_full_analysis_flow(
    db_session: AsyncSession,
    db_manager,
    tenant_key: str,
    product: Product,
    vision_doc: VisionDocument,
):
    """Full round-trip: get vision doc, write all 4 tables + summaries, verify persistence and WebSocket."""
    from src.giljo_mcp.tools.vision_analysis import gil_get_vision_doc, gil_write_product

    # Step 1: Retrieve vision document content + extraction prompt
    get_result = await gil_get_vision_doc(
        product_id=product.id,
        tenant_key=tenant_key,
        _test_session=db_session,
    )

    assert get_result["product_id"] == product.id
    assert get_result["product_name"] == "E2E Test Product"
    assert "mobile-first platform" in get_result["document_content"]
    assert get_result["document_tokens"] > 0
    assert get_result["write_tool"] == "gil_write_product"
    assert "extraction_instructions" in get_result
    assert "{document_content}" not in get_result["extraction_instructions"]

    # Step 2: Write fields spanning all 4 tables plus summaries
    mock_ws = AsyncMock()

    write_result = await gil_write_product(
        product_id=product.id,
        tenant_key=tenant_key,
        _test_session=db_session,
        websocket_manager=mock_ws,
        # products table
        product_description="A mobile-first real-time collaboration platform.",
        core_features="Real-time collaboration, mobile support",
        target_platforms=["windows", "linux", "macos"],
        # tech_stack table
        programming_languages="Python, TypeScript",
        frontend_frameworks="React Native",
        databases="PostgreSQL",
        # architecture table
        architecture_pattern="Event-driven microservices",
        api_style="REST",
        # test_config table
        testing_strategy="TDD",
        testing_frameworks="pytest, Jest",
        test_coverage_target=90,
        # summaries
        summary_33="Mobile-first collaboration platform using React Native and FastAPI.",
        summary_66=(
            "A mobile-first real-time collaboration platform built on React Native "
            "frontend with FastAPI backend. Event-driven microservices architecture "
            "using PostgreSQL. TDD with pytest and Jest targeting 90% coverage."
        ),
    )

    assert write_result["success"] is True
    assert write_result["fields_written"] == 13
    expected_fields = {
        "product_description", "core_features", "target_platforms",
        "programming_languages", "frontend_frameworks", "databases",
        "architecture_pattern", "api_style",
        "testing_strategy", "testing_frameworks", "test_coverage_target",
        "summary_33", "summary_66",
    }
    assert set(write_result["fields"]) == expected_fields

    # Step 3: Verify products table updated
    await db_session.refresh(product)
    assert product.description == "A mobile-first real-time collaboration platform."
    assert product.core_features == "Real-time collaboration, mobile support"
    assert product.target_platforms == ["windows", "linux", "macos"]

    # Step 4: Verify tech_stack table
    stmt = select(ProductTechStack).where(
        ProductTechStack.product_id == product.id,
        ProductTechStack.tenant_key == tenant_key,
    )
    ts = (await db_session.execute(stmt)).scalar_one_or_none()
    assert ts is not None
    assert ts.programming_languages == "Python, TypeScript"
    assert ts.frontend_frameworks == "React Native"
    assert ts.databases_storage == "PostgreSQL"

    # Step 5: Verify architecture table
    stmt = select(ProductArchitecture).where(
        ProductArchitecture.product_id == product.id,
        ProductArchitecture.tenant_key == tenant_key,
    )
    arch = (await db_session.execute(stmt)).scalar_one_or_none()
    assert arch is not None
    assert arch.primary_pattern == "Event-driven microservices"
    assert arch.api_style == "REST"

    # Step 6: Verify test_config table
    stmt = select(ProductTestConfig).where(
        ProductTestConfig.product_id == product.id,
        ProductTestConfig.tenant_key == tenant_key,
    )
    tc = (await db_session.execute(stmt)).scalar_one_or_none()
    assert tc is not None
    assert tc.test_strategy == "TDD"
    assert tc.testing_frameworks == "pytest, Jest"
    assert tc.coverage_target == 90

    # Step 7: Verify AI summaries in vision_document_summaries
    stmt = select(VisionDocumentSummary).where(
        VisionDocumentSummary.product_id == product.id,
        VisionDocumentSummary.tenant_key == tenant_key,
        VisionDocumentSummary.source == "ai",
    )
    rows = (await db_session.execute(stmt)).scalars().all()
    ratios = {row.ratio for row in rows}
    assert Decimal("0.33") in ratios
    assert Decimal("0.66") in ratios
    for row in rows:
        assert row.source == "ai"
        assert row.tokens_original > 0
        assert row.tokens_summary > 0

    # Step 8: Verify WebSocket event emitted
    mock_ws.broadcast_event_to_tenant.assert_called_once()
    call_kwargs = mock_ws.broadcast_event_to_tenant.call_args[1]
    assert call_kwargs["tenant_key"] == tenant_key
    event = call_kwargs["event"]
    assert event["type"] == "vision:analysis_complete"
    assert event["data"]["product_id"] == product.id
    assert event["data"]["fields_written"] == 13


# ---------------------------------------------------------------------------
# Test 2: Context Manager AI Preference
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_context_manager_prefers_ai(
    db_session: AsyncSession,
    db_manager,
    vision_repo: VisionDocumentRepository,
    tenant_key: str,
    product: Product,
    vision_doc: VisionDocument,
):
    """Context manager returns AI summary over Sumy when both exist."""
    from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    # Step 1: Write Sumy summaries via repository
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(vision_doc.id),
        product_id=str(product.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Sumy light: extractive summary of the vision document.",
        tokens_original=100,
        tokens_summary=33,
    )
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(vision_doc.id),
        product_id=str(product.id),
        source="sumy",
        ratio=Decimal("0.66"),
        summary="Sumy medium: longer extractive summary preserving more detail.",
        tokens_original=100,
        tokens_summary=66,
    )

    # Step 2: Write AI summaries via gil_write_product
    await gil_write_product(
        product_id=product.id,
        tenant_key=tenant_key,
        _test_session=db_session,
        summary_33="AI light: concise platform overview for developers.",
        summary_66="AI medium: detailed technical summary with architecture decisions.",
    )

    # Step 3: Verify light chunking returns AI summary, not Sumy
    light_result = await get_vision_document(
        product_id=str(product.id),
        tenant_key=tenant_key,
        chunking="light",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert light_result["depth"] == "light"
    assert "AI light: concise platform overview" in light_result["data"]["summary"]
    assert "Sumy light" not in light_result["data"]["summary"]

    # Step 4: Verify medium chunking returns AI summary, not Sumy
    medium_result = await get_vision_document(
        product_id=str(product.id),
        tenant_key=tenant_key,
        chunking="medium",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert medium_result["depth"] == "medium"
    assert "AI medium: detailed technical summary" in medium_result["data"]["summary"]
    assert "Sumy medium" not in medium_result["data"]["summary"]


# ---------------------------------------------------------------------------
# Test 3: Sumy-Only Fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_sumy_only_fallback(
    db_session: AsyncSession,
    db_manager,
    vision_repo: VisionDocumentRepository,
    tenant_key: str,
    product: Product,
    vision_doc: VisionDocument,
):
    """Context manager returns Sumy summary when no AI summary exists."""
    from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document

    # Write ONLY Sumy summaries (no AI summaries)
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(vision_doc.id),
        product_id=str(product.id),
        source="sumy",
        ratio=Decimal("0.33"),
        summary="Sumy-only light: extractive summary for light depth.",
        tokens_original=100,
        tokens_summary=33,
    )
    await vision_repo.create_summary(
        session=db_session,
        tenant_key=tenant_key,
        document_id=str(vision_doc.id),
        product_id=str(product.id),
        source="sumy",
        ratio=Decimal("0.66"),
        summary="Sumy-only medium: extractive summary for medium depth.",
        tokens_original=100,
        tokens_summary=66,
    )

    # Verify light returns Sumy
    light_result = await get_vision_document(
        product_id=str(product.id),
        tenant_key=tenant_key,
        chunking="light",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert light_result["depth"] == "light"
    assert "Sumy-only light: extractive summary" in light_result["data"]["summary"]

    # Verify medium returns Sumy
    medium_result = await get_vision_document(
        product_id=str(product.id),
        tenant_key=tenant_key,
        chunking="medium",
        db_manager=db_manager,
        _test_session=db_session,
    )

    assert medium_result["depth"] == "medium"
    assert "Sumy-only medium: extractive summary" in medium_result["data"]["summary"]


# ---------------------------------------------------------------------------
# Test 4: Partial Field Write (merge-write, no overwrite)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_partial_field_write_no_overwrite(
    db_session: AsyncSession,
    db_manager,
    tenant_key: str,
    product: Product,
    vision_doc: VisionDocument,
):
    """Partial writes only update provided fields; subsequent writes do not null earlier fields."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    # First write: 3 fields across products, tech_stack, and summaries
    result1 = await gil_write_product(
        product_id=product.id,
        tenant_key=tenant_key,
        _test_session=db_session,
        product_description="Initial description from first analysis pass.",
        programming_languages="Python, TypeScript",
        summary_33="Initial concise summary from first pass.",
    )

    assert result1["success"] is True
    assert result1["fields_written"] == 3
    assert set(result1["fields"]) == {"product_description", "programming_languages", "summary_33"}

    # Verify first-write persistence
    await db_session.refresh(product)
    assert product.description == "Initial description from first analysis pass."

    stmt = select(ProductTechStack).where(
        ProductTechStack.product_id == product.id,
        ProductTechStack.tenant_key == tenant_key,
    )
    ts = (await db_session.execute(stmt)).scalar_one_or_none()
    assert ts is not None
    assert ts.programming_languages == "Python, TypeScript"

    # Second write: 2 different fields (architecture + test_config)
    result2 = await gil_write_product(
        product_id=product.id,
        tenant_key=tenant_key,
        _test_session=db_session,
        architecture_pattern="Monolith",
        testing_strategy="BDD",
    )

    assert result2["success"] is True
    assert result2["fields_written"] == 2
    assert set(result2["fields"]) == {"architecture_pattern", "testing_strategy"}

    # Verify first-write fields were NOT overwritten or nulled
    await db_session.refresh(product)
    assert product.description == "Initial description from first analysis pass."

    stmt = select(ProductTechStack).where(
        ProductTechStack.product_id == product.id,
        ProductTechStack.tenant_key == tenant_key,
    )
    ts = (await db_session.execute(stmt)).scalar_one_or_none()
    assert ts is not None
    assert ts.programming_languages == "Python, TypeScript"

    # Verify second-write fields are present
    stmt = select(ProductArchitecture).where(
        ProductArchitecture.product_id == product.id,
        ProductArchitecture.tenant_key == tenant_key,
    )
    arch = (await db_session.execute(stmt)).scalar_one_or_none()
    assert arch is not None
    assert arch.primary_pattern == "Monolith"

    stmt = select(ProductTestConfig).where(
        ProductTestConfig.product_id == product.id,
        ProductTestConfig.tenant_key == tenant_key,
    )
    tc = (await db_session.execute(stmt)).scalar_one_or_none()
    assert tc is not None
    assert tc.test_strategy == "BDD"

    # Verify summary from first write still exists
    stmt = select(VisionDocumentSummary).where(
        VisionDocumentSummary.product_id == product.id,
        VisionDocumentSummary.tenant_key == tenant_key,
        VisionDocumentSummary.source == "ai",
        VisionDocumentSummary.ratio == Decimal("0.33"),
    )
    summary_row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert summary_row is not None
    assert summary_row.summary == "Initial concise summary from first pass."


# ---------------------------------------------------------------------------
# Test 5: Custom Instructions in Extraction Prompt
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_custom_instructions(
    db_session: AsyncSession,
    db_manager,
    tenant_key: str,
    product: Product,
    vision_doc: VisionDocument,
):
    """Custom instructions appear in extraction prompt; clearing them removes the section."""
    from src.giljo_mcp.tools.vision_analysis import gil_get_vision_doc

    # Step 1: Product has custom instructions ("Focus on mobile architecture")
    result_with = await gil_get_vision_doc(
        product_id=product.id,
        tenant_key=tenant_key,
        _test_session=db_session,
    )

    assert "Focus on mobile architecture" in result_with["extraction_instructions"]

    # Step 2: Clear custom instructions
    product.extraction_custom_instructions = None
    await db_session.flush()

    # Need to re-query to pick up cleared instructions
    result_without = await gil_get_vision_doc(
        product_id=product.id,
        tenant_key=tenant_key,
        _test_session=db_session,
    )

    assert "Focus on mobile architecture" not in result_without["extraction_instructions"]
    # The placeholder should be replaced with empty string, not left as a template variable
    assert "{custom_instructions}" not in result_without["extraction_instructions"]

    # Step 3: Verify document content is still present in both cases
    assert "mobile-first platform" in result_with["document_content"]
    assert "mobile-first platform" in result_without["document_content"]
