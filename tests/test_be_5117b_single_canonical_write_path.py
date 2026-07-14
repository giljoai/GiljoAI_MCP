# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for BE-5117b: single canonical vision-summary write path.

BE-5117 introduced the column-based write path:
- ``VisionDocument.summary_light`` / ``summary_medium`` (per-doc)
- ``Product.consolidated_vision_light`` / ``consolidated_vision_medium`` (aggregate)
- ``Product.vision_analysis_complete`` gates frontend staging unlock.

BE-5117b removes the LEGACY parallel write path:
- ``summary_33`` / ``summary_66`` parameters on ``update_product_fields``
- ``vision_document_summaries`` table + ``VisionDocumentSummary`` model
- ``VisionDocumentRepository.create_summary`` / ``get_summaries`` / ``get_best_summary``

After this project:
- The AI extraction prompt teaches ONLY ``vision_summaries[]`` + ``consolidated_vision{}``.
- Passing ``summary_33`` / ``summary_66`` produces a clean ``ValidationError`` (no silent no-op).
- The happy path through ``vision_summaries`` + ``consolidated_vision`` populates the
  per-doc columns AND flips ``vision_analysis_complete`` to True.
- The ``vision_document_summaries`` table is gone after migration ce_0035.
"""

import uuid

import pytest
import pytest_asyncio
from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models import Product, VisionDocument
from giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture(scope="function")
async def tenant_key() -> str:
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture(scope="function")
async def product(db_session: AsyncSession, tenant_key: str) -> Product:
    p = Product(
        id=str(uuid.uuid4()),
        name="BE-5117b Product",
        description="Regression product for single canonical write path.",
        tenant_key=tenant_key,
        is_active=True,
        product_memory={},
    )
    db_session.add(p)
    await db_session.flush()
    return p


@pytest_asyncio.fixture(scope="function")
async def vision_doc(db_session: AsyncSession, tenant_key: str, product: Product) -> VisionDocument:
    doc = VisionDocument(
        id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        product_id=product.id,
        document_name="vision.md",
        document_type="vision",
        vision_document="A platform for orchestrating AI coding agents.",
        storage_type="inline",
        content_hash="be5117b_hash",
        is_active=True,
        display_order=0,
        version="1.0.0",
        chunked=False,
        chunk_count=0,
    )
    db_session.add(doc)
    await db_session.flush()
    return doc


def test_prompt_single_path() -> None:
    """VISION_EXTRACTION_PROMPT teaches ONLY the column-write path."""
    from giljo_mcp.tools.vision_analysis import VISION_EXTRACTION_PROMPT

    assert "summary_33" not in VISION_EXTRACTION_PROMPT
    assert "summary_66" not in VISION_EXTRACTION_PROMPT
    assert "vision_summaries" in VISION_EXTRACTION_PROMPT
    assert "consolidated_vision" in VISION_EXTRACTION_PROMPT


@pytest.mark.asyncio
async def test_tool_rejects_legacy_fields(
    db_session: AsyncSession,
    db_manager,
    tenant_key: str,
    product: Product,
    vision_doc: VisionDocument,
) -> None:
    """Passing summary_33/summary_66 raises ValidationError (no silent no-op).

    Silent no-op would mask agent bugs: the agent thinks it wrote summaries
    but the staging gate never opens. A loud 422-style error surfaces the
    out-of-date prompt immediately.
    """
    from giljo_mcp.tools.vision_analysis import update_product_fields

    with pytest.raises(ValidationError):
        await update_product_fields(
            product_id=product.id,
            tenant_key=tenant_key,
            _test_session=db_session,
            summary_33="executive summary text",
            summary_66="thorough technical summary text",
        )


@pytest.mark.asyncio
async def test_happy_path_column_write(
    db_session: AsyncSession,
    db_manager,
    tenant_key: str,
    product: Product,
    vision_doc: VisionDocument,
) -> None:
    """vision_summaries + consolidated_vision populate columns and flip the gate."""
    from giljo_mcp.tools.vision_analysis import update_product_fields

    result = await update_product_fields(
        product_id=product.id,
        tenant_key=tenant_key,
        _test_session=db_session,
        vision_summaries=[
            {
                "doc_id": str(vision_doc.id),
                "light": "Light per-doc summary written via column path.",
                "medium": "Medium per-doc summary written via column path.",
            }
        ],
        consolidated_vision={
            "light": "Light product-aggregate summary across all docs.",
            "medium": "Medium product-aggregate summary across all docs.",
        },
    )

    assert result["success"] is True
    assert "vision_summaries" in result["fields"]
    assert "consolidated_vision" in result["fields"]

    await db_session.refresh(vision_doc)
    assert vision_doc.summary_light == "Light per-doc summary written via column path."
    assert vision_doc.summary_medium == "Medium per-doc summary written via column path."
    assert vision_doc.is_summarized is True

    refreshed = (await db_session.execute(select(Product).where(Product.id == product.id))).scalar_one()
    assert refreshed.consolidated_vision_light == "Light product-aggregate summary across all docs."
    assert refreshed.consolidated_vision_medium == "Medium product-aggregate summary across all docs."
    assert refreshed.vision_analysis_complete is True


@pytest.mark.asyncio
async def test_table_is_gone(db_session: AsyncSession) -> None:
    """vision_document_summaries table is dropped after migration ce_0035."""

    def _names(sync_conn) -> list[str]:
        return inspect(sync_conn).get_table_names()

    conn = await db_session.connection()
    names = await conn.run_sync(_names)

    assert "vision_document_summaries" not in names
