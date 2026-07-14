# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6130b regression: VisionDocument soft-delete (trash) -> recover round-trip.

``DELETE /vision-documents/{id}`` was a HARD delete that FK-cascaded its
MCPContextIndex RAG chunks. BE-6130b converts it to a soft-delete and recovers
the doc + its chunks as ONE unit. These service-layer tests prove:

* delete -> recover round-trips (the doc leaves/returns to the live reads);
* a soft-deleted doc is excluded from ``list_documents_by_product`` /
  ``get_document_by_id`` and surfaces only in ``list_deleted_documents``;
* the doc's chunks SURVIVE the soft-delete (cascade does not fire) but are
  excluded from RAG retrieval while the parent is trashed, and re-surface after
  restore — the doc + chunks recover together.

Real DB (rollback-isolated ``db_session``), no mocks — parallel-safe: each test
mints its own tenant key + product, no module-level mutable state.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models import MCPContextIndex, Product, VisionDocument
from giljo_mcp.repositories.context_repository import ContextRepository
from giljo_mcp.services.product_vision_service import ProductVisionService


pytestmark = pytest.mark.asyncio


def _tk(suffix: str) -> str:
    return f"tk_be6130b_vd_{suffix}"


async def _make_product(db_session, tenant: str) -> Product:
    product = Product(
        id=str(uuid4()),
        name=f"VD Product {uuid4().hex[:6]}",
        description="vision soft-delete tests",
        tenant_key=tenant,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()
    return product


async def _make_doc_with_chunk(db_session, tenant: str, product_id: str) -> tuple[str, int]:
    doc = VisionDocument(
        id=str(uuid4()),
        tenant_key=tenant,
        product_id=product_id,
        document_name=f"Vision {uuid4().hex[:6]}",
        document_type="vision",
        vision_document="alpha beta gamma vision body",
        storage_type="inline",
        content_hash="hash" + uuid4().hex[:8],
        is_active=True,
        display_order=0,
        version="1.0.0",
        chunked=True,
        chunk_count=1,
    )
    db_session.add(doc)
    await db_session.flush()
    chunk = MCPContextIndex(
        tenant_key=tenant,
        product_id=product_id,
        vision_document_id=doc.id,
        content="alpha beta gamma chunk body",
        keywords=["beta"],
        chunk_order=0,
    )
    db_session.add(chunk)
    await db_session.flush()
    return doc.id, chunk.id


async def test_delete_then_recover_round_trips(db_manager, db_session):
    tenant = _tk("roundtrip")
    svc = ProductVisionService(db_manager=db_manager, tenant_key=tenant, test_session=db_session)
    with tenant_session_context(db_session, tenant):
        product = await _make_product(db_session, tenant)
        doc_id, _chunk_id = await _make_doc_with_chunk(db_session, tenant, product.id)

        # Live reads see it.
        live = await svc.list_documents_by_product(db_session, product.id, active_only=False)
        assert doc_id in {d.id for d in live}
        assert await svc.get_document_by_id(db_session, doc_id) is not None

        # Soft-delete (trash).
        result = await svc.delete_document(db_session, doc_id)
        assert result["success"] is True
        assert result["chunks_deleted"] == 1  # chunk went dormant with the doc

        # Excluded from normal reads.
        live = await svc.list_documents_by_product(db_session, product.id, active_only=False)
        assert doc_id not in {d.id for d in live}
        assert await svc.get_document_by_id(db_session, doc_id) is None

        # Surfaces ONLY in the trash with a deleted_at stamp.
        trashed = await svc.list_deleted_documents(db_session, product_id=product.id)
        assert doc_id in {d.id for d in trashed}
        assert next(d for d in trashed if d.id == doc_id).deleted_at is not None

        # Restore brings it back.
        restored = await svc.restore_document(db_session, doc_id)
        assert restored.deleted_at is None
        live = await svc.list_documents_by_product(db_session, product.id, active_only=False)
        assert doc_id in {d.id for d in live}
        trashed = await svc.list_deleted_documents(db_session, product_id=product.id)
        assert doc_id not in {d.id for d in trashed}


async def test_chunks_survive_softdelete_and_excluded_from_rag(db_manager, db_session):
    """The doc's chunks are NOT physically deleted on soft-delete, but RAG
    retrieval skips them while the parent is trashed, then re-includes them on
    restore — proving the doc + chunks recover as one unit."""
    tenant = _tk("rag")
    svc = ProductVisionService(db_manager=db_manager, tenant_key=tenant, test_session=db_session)
    ctx_repo = ContextRepository(db_manager)
    with tenant_session_context(db_session, tenant):
        product = await _make_product(db_session, tenant)
        doc_id, chunk_id = await _make_doc_with_chunk(db_session, tenant, product.id)

        # RAG finds the chunk while the doc is live.
        hits = await ctx_repo.search_chunks(db_session, tenant, product.id, "beta", limit=10)
        assert chunk_id in {c.id for c in hits}

        # Soft-delete the parent doc.
        await svc.delete_document(db_session, doc_id)

        # The chunk row still PHYSICALLY exists (cascade did not fire)...
        surviving = (
            await db_session.execute(select(func.count(MCPContextIndex.id)).where(MCPContextIndex.id == chunk_id))
        ).scalar_one()
        assert surviving == 1
        # ...but RAG retrieval excludes it (parent trashed).
        hits = await ctx_repo.search_chunks(db_session, tenant, product.id, "beta", limit=10)
        assert chunk_id not in {c.id for c in hits}

        # Restore re-surfaces the chunk for retrieval.
        await svc.restore_document(db_session, doc_id)
        hits = await ctx_repo.search_chunks(db_session, tenant, product.id, "beta", limit=10)
        assert chunk_id in {c.id for c in hits}


async def test_recover_window_expired_is_rejected(db_manager, db_session):
    """BE-6130b decision A: a doc trashed more than 30 days ago is no longer
    recoverable — restore raises ValidationError and the row stays trashed."""
    tenant = _tk("expired")
    svc = ProductVisionService(db_manager=db_manager, tenant_key=tenant, test_session=db_session)
    with tenant_session_context(db_session, tenant):
        product = await _make_product(db_session, tenant)
        doc_id, _ = await _make_doc_with_chunk(db_session, tenant, product.id)
        await svc.delete_document(db_session, doc_id)

        # Backdate deleted_at beyond the 30-day window.
        await db_session.execute(
            update(VisionDocument)
            .where(VisionDocument.id == doc_id)
            .values(deleted_at=datetime.now(UTC) - timedelta(days=31))
        )
        await db_session.flush()

        with pytest.raises(ValidationError):
            await svc.restore_document(db_session, doc_id)

        # Still trashed.
        trashed = await svc.list_deleted_documents(db_session, product_id=product.id)
        assert doc_id in {d.id for d in trashed}


async def test_restore_is_tenant_isolated(db_manager, db_session):
    owner = _tk("owner")
    intruder = _tk("intruder")
    owner_svc = ProductVisionService(db_manager=db_manager, tenant_key=owner, test_session=db_session)
    intruder_svc = ProductVisionService(db_manager=db_manager, tenant_key=intruder, test_session=db_session)

    with tenant_session_context(db_session, owner):
        product = await _make_product(db_session, owner)
        doc_id, _ = await _make_doc_with_chunk(db_session, owner, product.id)
        await owner_svc.delete_document(db_session, doc_id)

    # The intruder tenant cannot restore the owner's trashed doc.
    with tenant_session_context(db_session, intruder), pytest.raises(ResourceNotFoundError):
        await intruder_svc.restore_document(db_session, doc_id)

    # The owner can.
    with tenant_session_context(db_session, owner):
        restored = await owner_svc.restore_document(db_session, doc_id)
        assert restored.id == doc_id
