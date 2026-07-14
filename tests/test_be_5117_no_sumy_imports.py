# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-5117 regression: import discipline.

Asserts that importing any of the previously-Sumy-touching modules does NOT
drag ``sumy`` or ``nltk`` into ``sys.modules``. This is the failing-layer
guard: previous incidents (BE-5116, INF-5037) showed that broken
lazy-import patterns let heavy CPU libraries leak into the import graph
even when the code path was nominally removed. The only safe regression
is the import-graph assertion itself.
"""

from __future__ import annotations

import importlib
import sys
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giljo_mcp.database import tenant_session_context
from giljo_mcp.models import Product, VisionDocument
from giljo_mcp.tenant import TenantManager


_TARGET_MODULES = (
    "api.endpoints.vision_documents",
    "giljo_mcp.services.product_vision_service",
    "giljo_mcp.services.consolidation_service",
    "giljo_mcp.tools.vision_analysis",
    "giljo_mcp.repositories.vision_document_repository",
)


def test_no_sumy_or_nltk_after_importing_vision_modules() -> None:
    """Loading every vision-touching module must not import sumy or nltk."""
    # Force a fresh re-import so the assertion is meaningful even if a prior
    # test session imported one of these modules earlier.
    for mod in _TARGET_MODULES:
        sys.modules.pop(mod, None)

    for mod in _TARGET_MODULES:
        importlib.import_module(mod)

    leaked = sorted(name for name in sys.modules if name == "sumy" or name.startswith("sumy."))
    leaked += sorted(name for name in sys.modules if name == "nltk" or name.startswith("nltk."))
    assert not leaked, (
        f"BE-5117 regression: importing vision modules pulled in Sumy/NLTK: {leaked}. "
        "Sumy/NLTK should be entirely absent from the runtime import graph."
    )


def test_vision_summarizer_module_is_gone() -> None:
    """``giljo_mcp.services.vision_summarizer`` must no longer be importable."""
    sys.modules.pop("giljo_mcp.services.vision_summarizer", None)
    try:
        importlib.import_module("giljo_mcp.services.vision_summarizer")
    except ModuleNotFoundError:
        return
    raise AssertionError(
        "BE-5117 regression: giljo_mcp.services.vision_summarizer is still importable. "
        "It must be deleted along with the Sumy dependency."
    )


# ---------------------------------------------------------------------------
# Failing-layer regression tests (CLAUDE.md MANDATORY for bug-fix projects).
#
# - MCP tool: update_product_fields write path (per-doc + aggregate + completion).
# - Repository: tenant-scoped update_summaries.
# - Service: evaluate_vision_analysis_complete flips TRUE -> FALSE when a fresh
#   un-summarized doc is added.
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def be5117_tenant() -> str:
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def be5117_product(db_session: AsyncSession, be5117_tenant: str) -> Product:
    product = Product(
        id=str(uuid.uuid4()),
        name="BE-5117 Product",
        description="vision-analysis-complete test product",
        tenant_key=be5117_tenant,
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.flush()
    return product


@pytest_asyncio.fixture
async def be5117_doc(db_session: AsyncSession, be5117_tenant: str, be5117_product: Product) -> VisionDocument:
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=be5117_tenant,
        product_id=be5117_product.id,
        document_name="Vision",
        document_type="vision",
        vision_document="The product vision body text for BE-5117.",
        storage_type="inline",
        content_hash="be5117hash",
        is_active=True,
        display_order=0,
        version="1.0.0",
        chunked=False,
        chunk_count=0,
        is_summarized=False,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


@pytest.mark.asyncio
async def test_update_product_fields_writes_summaries_and_flips_complete(
    db_session: AsyncSession,
    db_manager,
    be5117_tenant: str,
    be5117_product: Product,
    be5117_doc: VisionDocument,
) -> None:
    """update_product_fields persists per-doc + aggregate summaries and flips the flag."""
    from giljo_mcp.tools.vision_analysis import update_product_fields

    result = await update_product_fields(
        product_id=be5117_product.id,
        tenant_key=be5117_tenant,
        _test_session=db_session,
        vision_summaries=[
            {
                "doc_id": str(be5117_doc.id),
                "light": "Light per-doc summary text.",
                "medium": "Medium per-doc summary text with more detail.",
            }
        ],
        consolidated_vision={
            "light": "Aggregate light summary across all docs.",
            "medium": "Aggregate medium summary across all docs.",
        },
    )
    assert result["success"] is True
    assert "vision_summaries" in result["fields"]
    assert "consolidated_vision" in result["fields"]

    # Refresh the PRODUCT before the DOC. The tool selectinload's
    # Product.vision_documents, so refreshing the product expires its loaded
    # child VisionDocument rows; doing it after refresh(be5117_doc) would
    # re-expire the doc's columns, and the sync attribute access below would
    # then trigger a forbidden async lazy-load (MissingGreenlet). Refreshing the
    # doc LAST keeps its columns populated for direct assertion. (Not a tenant
    # issue -- the tool's writes are correct.)
    await db_session.refresh(be5117_product)
    await db_session.refresh(be5117_doc)

    assert be5117_doc.summary_light == "Light per-doc summary text."
    assert be5117_doc.summary_medium == "Medium per-doc summary text with more detail."
    assert be5117_doc.is_summarized is True

    assert be5117_product.consolidated_vision_light == "Aggregate light summary across all docs."
    assert be5117_product.consolidated_vision_medium == "Aggregate medium summary across all docs."
    assert be5117_product.vision_analysis_complete is True


@pytest.mark.asyncio
async def test_vision_analysis_complete_flips_false_on_new_unsummarized_doc(
    db_session: AsyncSession,
    db_manager,
    be5117_tenant: str,
    be5117_product: Product,
    be5117_doc: VisionDocument,
) -> None:
    """Adding a fresh un-summarized vision document flips the flag back to FALSE."""
    from giljo_mcp.services.product_vision_service import ProductVisionService
    from giljo_mcp.tools.vision_analysis import update_product_fields

    # First reach vision_analysis_complete=True via the MCP tool.
    await update_product_fields(
        product_id=be5117_product.id,
        tenant_key=be5117_tenant,
        _test_session=db_session,
        vision_summaries=[
            {
                "doc_id": str(be5117_doc.id),
                "light": "Light summary.",
                "medium": "Medium summary.",
            }
        ],
        consolidated_vision={"light": "Agg light.", "medium": "Agg medium."},
    )
    await db_session.refresh(be5117_product)
    assert be5117_product.vision_analysis_complete is True

    # Now add a new active doc with NO summaries.
    fresh_doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=be5117_tenant,
        product_id=be5117_product.id,
        document_name="Fresh Vision",
        document_type="vision",
        vision_document="Newly uploaded, not yet summarized.",
        storage_type="inline",
        content_hash="freshhash",
        is_active=True,
        display_order=1,
        version="1.0.0",
        chunked=False,
        chunk_count=0,
        is_summarized=False,
    )
    db_session.add(fresh_doc)
    await db_session.flush()

    service = ProductVisionService(db_manager=db_manager, tenant_key=be5117_tenant, test_session=db_session)
    new_value = await service.evaluate_vision_analysis_complete(db_session, be5117_product.id)
    assert new_value is False
    await db_session.refresh(be5117_product)
    assert be5117_product.vision_analysis_complete is False


@pytest.mark.asyncio
async def test_evaluate_reads_fresh_data_despite_stale_identity_map(
    db_session: AsyncSession,
    db_manager,
    be5117_tenant: str,
    be5117_product: Product,
    be5117_doc: VisionDocument,
) -> None:
    """BE-6210 regression: the evaluator must not compute the flag from a stale
    identity-map snapshot.

    Reproduces a production bug: the per-doc summaries
    and the aggregate consolidated_vision are written through SEPARATE sessions
    from the one the evaluator runs on. The evaluator's Product/vision_documents
    were already loaded (un-summarized) into that session's identity map, so
    without populate_existing it recomputed FALSE against the cached snapshot and
    persisted a "Pending analysis" flag even though the data was complete.

    Simulated here by loading the product+docs into the identity map FIRST, then
    mutating the underlying rows via raw SQL (ORM objects stay stale, same as a
    foreign-session commit under READ COMMITTED), then evaluating.
    """
    from giljo_mcp.services.product_vision_service import ProductVisionService

    # 1. Load product + vision_documents into the session identity map while the
    #    doc has NO summaries and the product has NO consolidated vision. This is
    #    the stale snapshot the evaluator would otherwise reuse.
    loaded = (
        await db_session.execute(
            select(Product).where(Product.id == be5117_product.id).options(selectinload(Product.vision_documents))
        )
    ).scalar_one()
    assert loaded.vision_documents[0].summary_light is None
    assert loaded.consolidated_vision_light is None

    # 2. Populate the rows OUT-OF-BAND (raw SQL) so the ORM-mapped objects above
    #    keep their stale attributes — mirrors the cross-session commit.
    await db_session.execute(
        text(
            "UPDATE vision_documents SET summary_light = :l, summary_medium = :m, is_summarized = TRUE WHERE id = :id"
        ),
        {"l": "Fresh light.", "m": "Fresh medium.", "id": str(be5117_doc.id)},
    )
    await db_session.execute(
        text("UPDATE products SET consolidated_vision_light = :l, consolidated_vision_medium = :m WHERE id = :id"),
        {"l": "Agg light.", "m": "Agg medium.", "id": str(be5117_product.id)},
    )

    # 3. The evaluator must read fresh and return True (was False before the fix).
    service = ProductVisionService(db_manager=db_manager, tenant_key=be5117_tenant, test_session=db_session)
    new_value = await service.evaluate_vision_analysis_complete(db_session, be5117_product.id)
    assert new_value is True
    await db_session.refresh(be5117_product)
    assert be5117_product.vision_analysis_complete is True


@pytest.mark.asyncio
async def test_update_summaries_repository_enforces_tenant_scope(
    db_session: AsyncSession,
    db_manager,
    be5117_tenant: str,
    be5117_doc: VisionDocument,
) -> None:
    """``update_summaries`` returns None when the tenant key does not own the doc."""
    from giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository

    repo = VisionDocumentRepository(db_manager=db_manager)
    other_tenant = TenantManager.generate_tenant_key()
    # The be5117_doc fixture flushed a tenant-A row into the shared db_session,
    # leaving flush-derived tenant-A context on it. Scope the cross-tenant call
    # to `other_tenant` so the fail-closed guard authorizes the repo's explicit
    # tenant predicate (Slice-6 test-side pattern). The repo itself is correct:
    # get_by_id filters by tenant_key and returns None for a non-owning tenant.
    with tenant_session_context(db_session, other_tenant):
        result = await repo.update_summaries(
            session=db_session,
            tenant_key=other_tenant,
            document_id=str(be5117_doc.id),
            light="should not land",
            medium="should not land",
        )
    assert result is None

    await db_session.refresh(be5117_doc)
    assert be5117_doc.summary_light is None
    assert be5117_doc.summary_medium is None


@pytest.mark.asyncio
async def test_upload_flow_creates_unsummarized_doc(
    db_session: AsyncSession,
    db_manager,
    be5117_tenant: str,
    be5117_product: Product,
) -> None:
    """The post-BE-5117 upload path leaves new docs with is_summarized=False / NULL summaries."""
    from giljo_mcp.services.product_vision_service import ProductVisionService

    service = ProductVisionService(db_manager=db_manager, tenant_key=be5117_tenant, test_session=db_session)
    long_content = "Vision body. " * 200  # well above the old 100-token threshold
    upload = await service.upload_vision_document(
        product_id=be5117_product.id,
        content=long_content,
        filename="vision.md",
        auto_chunk=False,
    )

    # Look up the row that was just created.
    stmt = select(VisionDocument).where(VisionDocument.id == upload.document_id)
    row = (await db_session.execute(stmt)).scalar_one()
    assert row.is_summarized is False
    assert row.summary_light is None
    assert row.summary_medium is None
