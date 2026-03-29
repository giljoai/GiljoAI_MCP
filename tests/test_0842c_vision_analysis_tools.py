"""
Tests for vision analysis MCP tools: gil_get_vision_doc and gil_write_product.

Handover 0842c: TDD tests written FIRST before implementation.
Covers happy paths, tenant isolation, partial writes, and WebSocket emission.
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
    """Create test product for tenant A with extraction_custom_instructions."""
    product = Product(
        id=str(uuid.uuid4()),
        name="Test Product A",
        description="Product for vision analysis testing",
        tenant_key=tenant_a,
        is_active=True,
        product_memory={},
        extraction_custom_instructions="Focus on backend architecture.",
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture(scope="function")
async def product_a_no_instructions(db_session: AsyncSession, tenant_a: str) -> Product:
    """Create test product for tenant A without custom extraction instructions."""
    product = Product(
        id=str(uuid.uuid4()),
        name="Test Product No Instructions",
        description="Product without custom extraction instructions",
        tenant_key=tenant_a,
        is_active=False,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture(scope="function")
async def product_b(db_session: AsyncSession, tenant_b: str) -> Product:
    """Create test product for tenant B (cross-tenant isolation)."""
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
    """Create active vision document for product A."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        product_id=product_a.id,
        document_name="Product Vision",
        document_type="vision",
        vision_document="This is the main vision document content for testing.",
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
    """Create second active vision document for product A."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        product_id=product_a.id,
        document_name="Architecture Doc",
        document_type="architecture",
        vision_document="Architecture details for the product.",
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
    """Create vision document for tenant B product."""
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        product_id=product_b.id,
        document_name="Tenant B Vision",
        document_type="vision",
        vision_document="This is tenant B content.",
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


# ---------------------------------------------------------------------------
# Tests for gil_get_vision_doc
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_vision_doc_happy_path(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
):
    """Product with vision doc returns content, prompt, and metadata."""
    from src.giljo_mcp.tools.vision_analysis import gil_get_vision_doc

    result = await gil_get_vision_doc(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
    )

    assert result["product_id"] == product_a.id
    assert result["product_name"] == "Test Product A"
    assert result["total_chunks"] >= 1
    assert result["total_tokens"] > 0
    assert result["write_tool"] == "gil_write_product"
    assert "extraction_instructions" in result
    assert "{custom_instructions}" not in result["extraction_instructions"]
    # Metadata-only call should include usage hint, not content
    assert "usage" in result

    # Request chunk 1 to get actual content
    chunk_result = await gil_get_vision_doc(
        product_id=product_a.id,
        tenant_key=tenant_a,
        chunk=1,
        _test_session=db_session,
    )
    assert "vision document content" in chunk_result["content"]
    assert chunk_result["chunk"] == 1


@pytest.mark.asyncio
async def test_get_vision_doc_not_found(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
):
    """Nonexistent product raises ResourceNotFoundError."""
    from src.giljo_mcp.exceptions import ResourceNotFoundError
    from src.giljo_mcp.tools.vision_analysis import gil_get_vision_doc

    with pytest.raises(ResourceNotFoundError):
        await gil_get_vision_doc(
            product_id=str(uuid.uuid4()),
            tenant_key=tenant_a,
            _test_session=db_session,
        )


@pytest.mark.asyncio
async def test_get_vision_doc_tenant_isolation(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    tenant_b: str,
    product_b: Product,
    doc_b: VisionDocument,
):
    """Cannot read another tenant's product vision documents."""
    from src.giljo_mcp.exceptions import ResourceNotFoundError
    from src.giljo_mcp.tools.vision_analysis import gil_get_vision_doc

    with pytest.raises(ResourceNotFoundError):
        await gil_get_vision_doc(
            product_id=product_b.id,
            tenant_key=tenant_a,
            _test_session=db_session,
        )


@pytest.mark.asyncio
async def test_get_vision_doc_custom_instructions(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
):
    """Custom extraction instructions are injected into the prompt."""
    from src.giljo_mcp.tools.vision_analysis import gil_get_vision_doc

    result = await gil_get_vision_doc(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
    )

    assert "Focus on backend architecture." in result["extraction_instructions"]


@pytest.mark.asyncio
async def test_get_vision_doc_no_vision_docs(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a_no_instructions: Product,
):
    """Product without vision documents raises ResourceNotFoundError."""
    from src.giljo_mcp.exceptions import ResourceNotFoundError
    from src.giljo_mcp.tools.vision_analysis import gil_get_vision_doc

    with pytest.raises(ResourceNotFoundError, match="No vision documents found"):
        await gil_get_vision_doc(
            product_id=product_a_no_instructions.id,
            tenant_key=tenant_a,
            _test_session=db_session,
        )


# ---------------------------------------------------------------------------
# Tests for gil_write_product
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_product_core_fields(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
):
    """Writes product_name, description, and core_features to product."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    result = await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        product_name="Updated Product Name",
        product_description="A new description.",
        core_features="Feature A, Feature B",
    )

    assert result["success"] is True
    assert result["fields_written"] == 3
    assert "product_name" in result["fields"]
    assert "product_description" in result["fields"]
    assert "core_features" in result["fields"]

    # Verify values persisted
    await db_session.refresh(product_a)
    assert product_a.name == "Updated Product Name"
    assert product_a.description == "A new description."
    assert product_a.core_features == "Feature A, Feature B"


@pytest.mark.asyncio
async def test_write_product_tech_stack(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
):
    """Writes tech stack fields to product_tech_stacks table."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    result = await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        programming_languages="Python, TypeScript",
        databases="PostgreSQL, Redis",
        infrastructure="Docker, Kubernetes",
    )

    assert result["success"] is True
    assert "programming_languages" in result["fields"]
    assert "databases" in result["fields"]
    assert "infrastructure" in result["fields"]

    # Verify persisted via fresh query
    stmt = select(ProductTechStack).where(
        ProductTechStack.product_id == product_a.id,
        ProductTechStack.tenant_key == tenant_a,
    )
    row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert row is not None
    assert row.programming_languages == "Python, TypeScript"
    assert row.databases_storage == "PostgreSQL, Redis"
    assert row.infrastructure == "Docker, Kubernetes"


@pytest.mark.asyncio
async def test_write_product_architecture(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
):
    """Writes architecture fields to product_architectures table."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    result = await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        architecture_pattern="Microservices",
        api_style="REST + GraphQL",
        design_patterns="CQRS, Event Sourcing",
    )

    assert result["success"] is True
    assert "architecture_pattern" in result["fields"]

    stmt = select(ProductArchitecture).where(
        ProductArchitecture.product_id == product_a.id,
        ProductArchitecture.tenant_key == tenant_a,
    )
    row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert row is not None
    assert row.primary_pattern == "Microservices"
    assert row.api_style == "REST + GraphQL"
    assert row.design_patterns == "CQRS, Event Sourcing"


@pytest.mark.asyncio
async def test_write_product_test_config(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
):
    """Writes test config fields to product_test_configs table."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    result = await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        quality_standards="High reliability, zero downtime",
        testing_strategy="TDD",
        testing_frameworks="pytest, Jest",
        test_coverage_target=90,
    )

    assert result["success"] is True
    assert "quality_standards" in result["fields"]

    stmt = select(ProductTestConfig).where(
        ProductTestConfig.product_id == product_a.id,
        ProductTestConfig.tenant_key == tenant_a,
    )
    row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert row is not None
    assert row.quality_standards == "High reliability, zero downtime"
    assert row.test_strategy == "TDD"
    assert row.testing_frameworks == "pytest, Jest"
    assert row.coverage_target == 90


@pytest.mark.asyncio
async def test_write_product_summaries(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
    doc_a: VisionDocument,
):
    """Writes summary_33 and summary_66 to vision_document_summaries with source=ai."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    result = await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        summary_33="Executive summary of the product vision.",
        summary_66="Thorough technical summary preserving architecture decisions and feature specs.",
    )

    assert result["success"] is True
    assert "summary_33" in result["fields"]
    assert "summary_66" in result["fields"]

    # Verify summaries persisted
    stmt = select(VisionDocumentSummary).where(
        VisionDocumentSummary.product_id == product_a.id,
        VisionDocumentSummary.tenant_key == tenant_a,
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


@pytest.mark.asyncio
async def test_write_product_partial_fields(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
):
    """Only provided fields are written; missing fields remain untouched (merge-write)."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    # First write: set programming_languages and frontend_frameworks
    await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        programming_languages="Python",
        frontend_frameworks="Vue 3",
    )

    # Second write: only update programming_languages
    result = await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        programming_languages="Python, Rust",
    )

    assert result["fields_written"] == 1

    # Verify frontend_frameworks was NOT blanked
    stmt = select(ProductTechStack).where(
        ProductTechStack.product_id == product_a.id,
        ProductTechStack.tenant_key == tenant_a,
    )
    row = (await db_session.execute(stmt)).scalar_one_or_none()
    assert row is not None
    assert row.programming_languages == "Python, Rust"
    assert row.frontend_frameworks == "Vue 3"


@pytest.mark.asyncio
async def test_write_product_tenant_isolation(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    tenant_b: str,
    product_b: Product,
):
    """Cannot write to another tenant's product."""
    from src.giljo_mcp.exceptions import ResourceNotFoundError
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    with pytest.raises(ResourceNotFoundError):
        await gil_write_product(
            product_id=product_b.id,
            tenant_key=tenant_a,
            _test_session=db_session,
            product_name="Hacked Name",
        )


@pytest.mark.asyncio
async def test_write_product_websocket_event(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
):
    """WebSocket notification is emitted after successful write."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    mock_ws = AsyncMock()

    await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        websocket_manager=mock_ws,
        product_name="WS Test Product",
    )

    mock_ws.broadcast_event_to_tenant.assert_called_once()
    call_kwargs = mock_ws.broadcast_event_to_tenant.call_args[1]
    assert call_kwargs["tenant_key"] == tenant_a
    event = call_kwargs["event"]
    assert event["type"] == "vision:analysis_complete"
    assert event["data"]["product_id"] == product_a.id
    assert event["data"]["fields_written"] == 1


@pytest.mark.asyncio
async def test_write_product_target_platforms(
    db_session: AsyncSession,
    db_manager,
    tenant_a: str,
    product_a: Product,
):
    """target_platforms writes to the ARRAY column on the products table."""
    from src.giljo_mcp.tools.vision_analysis import gil_write_product

    result = await gil_write_product(
        product_id=product_a.id,
        tenant_key=tenant_a,
        _test_session=db_session,
        target_platforms=["windows", "linux"],
    )

    assert result["success"] is True
    assert "target_platforms" in result["fields"]

    await db_session.refresh(product_a)
    assert product_a.target_platforms == ["windows", "linux"]
