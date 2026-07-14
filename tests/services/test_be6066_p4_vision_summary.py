# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE-6066 P4 service-layer tests — batched vision-document aggregates.

The lean products LIST no longer ships the full ``vision_documents`` array.
``ProductCard.vue`` used to derive four values from it client-side; the backend
now pre-aggregates them in ONE grouped query via
``ProductMemoryService.get_vision_summary_bulk`` →
``ProductMemoryRepository.vision_summary_bulk``.

These tests gate that the aggregates mirror the card's EXACT computed semantics
for a fixture spanning chunked / unchunked / analyzed / not-analyzed docs:

- ``doc_count``     -> ``vision_documents.length``
- ``chunked_count`` -> count where ``chunked``
- ``chunk_total``   -> sum of ``chunk_count``
- ``embedded_count``-> count where ``summary_light`` AND ``summary_medium`` are
  both non-empty (the card's truthy ``getAnalyzedDocCount``; empty string is
  NOT analyzed)

Parallel-safe: ``TransactionalTestContext`` (rollback at teardown), a unique
tenant_key per test, no module-level mutable state.
"""

from uuid import uuid4

import pytest

from giljo_mcp.models import Product, VisionDocument
from giljo_mcp.services.product_memory_service import ProductMemoryService
from tests.helpers.test_db_helper import TransactionalTestContext


def _add_product(session, tenant_key: str, name: str) -> Product:
    product = Product(id=str(uuid4()), tenant_key=tenant_key, name=name, is_active=False)
    session.add(product)
    return product


def _add_vision(
    session,
    tenant_key: str,
    product_id: str,
    name: str,
    *,
    chunked: bool = False,
    chunk_count: int = 0,
    summary_light: str | None = None,
    summary_medium: str | None = None,
) -> None:
    # document_name must be unique per product (uq_vision_doc_product_name).
    session.add(
        VisionDocument(
            id=str(uuid4()),
            product_id=product_id,
            tenant_key=tenant_key,
            document_name=name,
            document_type="vision",
            vision_document="vision content",
            storage_type="inline",
            chunked=chunked,
            chunk_count=chunk_count,
            summary_light=summary_light,
            summary_medium=summary_medium,
        )
    )


@pytest.mark.asyncio
class TestVisionSummaryBulk:
    """BE-6066 P4: batched vision-document aggregates for the products LIST."""

    async def test_aggregates_mirror_card_semantics_mixed_fixture(self, db_manager):
        """
        doc_count / chunked_count / chunk_total / embedded_count must match the
        card's old client-side computeds for a mixed fixture, including the
        empty-string edge (an empty summary is NOT 'analyzed', mirroring the
        card's truthy ``summary_light && summary_medium``).
        """
        tenant_key = str(uuid4())

        async with TransactionalTestContext(db_manager) as session:
            p1 = _add_product(session, tenant_key, "Product One")
            # P2: completely empty — must be ABSENT from the result (callers zero-fill).
            p2 = _add_product(session, tenant_key, "Product Two")
            await session.flush()

            # P1: 4 docs spanning every combination.
            # doc1: chunked, 3 chunks, fully analyzed.
            _add_vision(
                session,
                tenant_key,
                p1.id,
                "Doc A",
                chunked=True,
                chunk_count=3,
                summary_light="light",
                summary_medium="medium",
            )
            # doc2: chunked, 2 chunks, NOT analyzed (no summaries).
            _add_vision(session, tenant_key, p1.id, "Doc B", chunked=True, chunk_count=2)
            # doc3: unchunked, analyzed.
            _add_vision(
                session,
                tenant_key,
                p1.id,
                "Doc C",
                summary_light="light",
                summary_medium="medium",
            )
            # doc4: unchunked, empty-string medium → NOT analyzed (truthy edge).
            _add_vision(
                session,
                tenant_key,
                p1.id,
                "Doc D",
                summary_light="light",
                summary_medium="",
            )
            await session.flush()

            service = ProductMemoryService(db_manager, tenant_key, test_session=session)
            summary = await service.get_vision_summary_bulk([str(p1.id), str(p2.id)])

            assert summary[str(p1.id)] == {
                "doc_count": 4,
                "chunked_count": 2,  # doc1 + doc2
                "chunk_total": 5,  # 3 + 2
                "embedded_count": 2,  # doc1 + doc3 (doc4's empty medium excluded)
            }
            # Product with no vision docs is absent (callers default missing keys).
            assert str(p2.id) not in summary

    async def test_empty_input_returns_empty_dict(self, db_manager):
        """No product_ids → no query, empty dict (mirrors the bulk-stats path)."""
        tenant_key = str(uuid4())
        async with TransactionalTestContext(db_manager) as session:
            service = ProductMemoryService(db_manager, tenant_key, test_session=session)
            assert await service.get_vision_summary_bulk([]) == {}

    async def test_doc_count_matches_count_vision_documents_bulk(self, db_manager):
        """
        The summary's ``doc_count`` must equal the P1 ``count_vision_documents_bulk``
        for the same fixture — the two paths share the count semantics.
        """
        tenant_key = str(uuid4())
        async with TransactionalTestContext(db_manager) as session:
            p1 = _add_product(session, tenant_key, "Product One")
            await session.flush()
            _add_vision(session, tenant_key, p1.id, "Doc A", chunked=True, chunk_count=1)
            _add_vision(session, tenant_key, p1.id, "Doc B")
            await session.flush()

            service = ProductMemoryService(db_manager, tenant_key, test_session=session)
            summary = await service.get_vision_summary_bulk([str(p1.id)])
            stats = await service.get_product_statistics_bulk([str(p1.id)])

            assert summary[str(p1.id)]["doc_count"] == stats[str(p1.id)]["vision_documents_count"] == 2
