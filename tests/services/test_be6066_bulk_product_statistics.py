# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE-6066 P1 regression tests — batched products-list statistics.

The products list used to call ``ProductMemoryService.get_product_statistics``
once PER product (1 redundant SELECT + 5 count queries each), making the stats
O(N) in product count. P1 replaces that with
``get_product_statistics_bulk(product_ids)`` which issues a FIXED number of
grouped (GROUP BY product FK) queries regardless of N.

These tests gate the two correctness properties:

1. **Byte-identical counts** — the batched path returns exactly the same
   project_count / unfinished_projects / task_count / unresolved_tasks /
   vision_documents_count / has_vision the old per-product path returned, for a
   fixture spanning multiple products and including soft-deleted (DELETED-status)
   projects. Proves the status / soft-delete filters survived the GROUP BY.
2. **O(1) scaling** — listing 1 product vs 3 products issues the SAME number of
   stats queries, proving the per-product loop is gone.

Parallel-safe: uses ``TransactionalTestContext`` (rollback at teardown), a unique
tenant_key per test, and no module-level mutable state.
"""

from uuid import uuid4

import pytest
from sqlalchemy import event

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.models import Product, Project, Task, VisionDocument
from giljo_mcp.services.product_memory_service import ProductMemoryService
from tests.helpers.test_db_helper import TransactionalTestContext


_STATS_FIELDS = (
    "project_count",
    "unfinished_projects",
    "task_count",
    "unresolved_tasks",
    "vision_documents_count",
    "has_vision",
)


def _add_product(session, tenant_key: str, name: str) -> Product:
    product = Product(id=str(uuid4()), tenant_key=tenant_key, name=name, is_active=False)
    session.add(product)
    return product


def _add_project(session, tenant_key: str, product_id: str, status: str, series_number: int) -> None:
    session.add(
        Project(
            id=str(uuid4()),
            name=f"Project {series_number}",
            description="desc",
            mission="mission",
            status=status,
            product_id=product_id,
            tenant_key=tenant_key,
            series_number=series_number,
        )
    )


def _add_task(session, tenant_key: str, product_id: str, status: str) -> None:
    session.add(
        Task(
            id=str(uuid4()),
            title="Task",
            description="desc",
            tenant_key=tenant_key,
            product_id=product_id,
            status=status,
            priority="medium",
        )
    )


def _add_vision(session, tenant_key: str, product_id: str, name: str = "Vision") -> None:
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
        )
    )


@pytest.mark.asyncio
class TestBulkProductStatistics:
    """BE-6066 P1: batched products-list statistics."""

    async def test_bulk_matches_per_product_path_with_soft_deletes(self, db_manager):
        """
        Batched stats must be byte-identical to the per-product path, including a
        product carrying a DELETED-status (soft-deleted) project that the
        non-deleted count must exclude.
        """
        tenant_key = str(uuid4())

        async with TransactionalTestContext(db_manager) as session:
            # P1: rich mix incl. a soft-deleted (DELETED-status) project.
            p1 = _add_product(session, tenant_key, "Product One")
            # P2: a little data, no vision.
            p2 = _add_product(session, tenant_key, "Product Two")
            # P3: completely empty (every count must be zero, has_vision False).
            p3 = _add_product(session, tenant_key, "Product Three")
            await session.flush()

            series = 1
            # P1 projects: 1 active, 2 inactive, 1 completed, 1 DELETED (soft-deleted).
            # Only one ACTIVE project is allowed per product
            # (idx_project_single_active_per_product).
            for status in (
                ProjectStatus.ACTIVE,
                ProjectStatus.INACTIVE,
                ProjectStatus.INACTIVE,
                ProjectStatus.COMPLETED,
                ProjectStatus.DELETED,
            ):
                _add_project(session, tenant_key, p1.id, status, series)
                series += 1
            # P1 tasks: 2 pending, 1 in_progress, 1 completed, 1 cancelled
            for status in ("pending", "pending", "in_progress", "completed", "cancelled"):
                _add_task(session, tenant_key, p1.id, status)
            # P1 vision: 2 docs (distinct names per uq_vision_doc_product_name)
            _add_vision(session, tenant_key, p1.id, "Vision A")
            _add_vision(session, tenant_key, p1.id, "Vision B")

            # P2 projects: 1 active; tasks: 1 pending; no vision
            _add_project(session, tenant_key, p2.id, ProjectStatus.ACTIVE, series)
            series += 1
            _add_task(session, tenant_key, p2.id, "pending")

            await session.flush()

            service = ProductMemoryService(db_manager, tenant_key, test_session=session)
            product_ids = [str(p1.id), str(p2.id), str(p3.id)]

            bulk = await service.get_product_statistics_bulk(product_ids)

            # Every requested product is present in the result.
            assert set(bulk.keys()) == set(product_ids)

            # Field-by-field equality against the legacy per-product path.
            for pid in product_ids:
                legacy = await service.get_product_statistics(pid)
                for field in _STATS_FIELDS:
                    assert bulk[pid][field] == getattr(legacy, field), (
                        f"mismatch for product {pid} field {field}: "
                        f"bulk={bulk[pid][field]} legacy={getattr(legacy, field)}"
                    )

            # Spot-check the known-correct values so a bug that changes BOTH paths
            # identically can't pass silently.
            assert bulk[str(p1.id)]["project_count"] == 4  # DELETED excluded
            assert bulk[str(p1.id)]["unfinished_projects"] == 3  # active+inactive+inactive
            assert bulk[str(p1.id)]["task_count"] == 5  # all tasks counted
            assert bulk[str(p1.id)]["unresolved_tasks"] == 3  # pending+pending+in_progress
            assert bulk[str(p1.id)]["vision_documents_count"] == 2
            assert bulk[str(p1.id)]["has_vision"] is True

            assert bulk[str(p3.id)] == {
                "project_count": 0,
                "unfinished_projects": 0,
                "task_count": 0,
                "unresolved_tasks": 0,
                "vision_documents_count": 0,
                "has_vision": False,
            }

    async def test_bulk_is_o1_in_product_count(self, db_manager):
        """
        Listing 1 product vs 3 products must issue the SAME number of SQL
        statements — proving the per-product loop is gone (O(1) in N).
        """
        tenant_key = str(uuid4())

        async with TransactionalTestContext(db_manager) as session:
            products = [_add_product(session, tenant_key, f"Product {i}") for i in range(3)]
            await session.flush()
            # Give each product some rows so counts are non-trivial.
            for i, product in enumerate(products):
                _add_project(session, tenant_key, product.id, ProjectStatus.ACTIVE, i + 1)
                _add_task(session, tenant_key, product.id, "pending")
                _add_vision(session, tenant_key, product.id)
            await session.flush()

            service = ProductMemoryService(db_manager, tenant_key, test_session=session)
            ids = [str(p.id) for p in products]

            # Count statements executed on the engine during each bulk call.
            sync_engine = db_manager.async_engine.sync_engine
            counter = {"n": 0}

            def _count(conn, cursor, statement, parameters, context, executemany):
                counter["n"] += 1

            event.listen(sync_engine, "before_cursor_execute", _count)
            try:
                counter["n"] = 0
                await service.get_product_statistics_bulk(ids[:1])
                one_product_stmts = counter["n"]

                counter["n"] = 0
                await service.get_product_statistics_bulk(ids)
                three_product_stmts = counter["n"]
            finally:
                event.remove(sync_engine, "before_cursor_execute", _count)

            assert one_product_stmts > 0
            assert one_product_stmts == three_product_stmts, (
                "stats query count scales with product count — the per-product "
                f"loop is not fully batched (1 product={one_product_stmts}, "
                f"3 products={three_product_stmts})"
            )
