# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6067 — SQL-statement-level N+1 guard for the /mcp agent enrichment path.

Context (P8, 2026-06-11 perf trace): the agent ``/mcp`` transport issued a
per-project N+1 — ``count(agent_jobs)`` + ``SELECT product_memory_entries`` +
``SELECT agent_jobs`` once PER project across the listed set (a x11 block in the
trace). BE-6071 F6b collapsed that loop in
``ProjectService._build_mcp_project_list`` to ONE grouped-IN query per facet.

Why this guard exists ON TOP of BE-6071's own regression test:
``test_be6071_unbounded_reads::test_f6b_depth2_enrichment_query_count_is_project_count_independent``
counts batched *service-method* calls — a proxy. It would still PASS if a batched
method's internals silently regressed to per-row SQL (the N+1 reappearing one
layer down). This test closes that gap by counting the ACTUAL SQL cursor
executions that touch ``agent_jobs`` / ``product_memory_entries`` (the
established ``test_context_repository_search_n1`` ``before_cursor_execute``
pattern) and asserting the count is:

* **bounded** — a small constant (the 3 grouped facet queries at depth 2), and
* **project-count-INDEPENDENT** — identical for a small vs a large project set.

That independence is the defining property of an N+1-free path: at N=12 an
unfixed loop would emit ~36 such statements; the batched path emits 3 at any N.
Result-equivalence (each project's enriched counts) is asserted alongside.

Two-sided + parallel-safe: uses the transactional ``db_session`` fixture (no
commits, rolled back at teardown), no module-level mutable state, no ordering
deps.

Edition Scope: Both (the /mcp transport + agent_jobs/product_memory exist in CE
and SaaS).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

import pytest
from sqlalchemy import event

from giljo_mcp.models import AgentExecution, AgentJob, Product, Project
from giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from giljo_mcp.services.project_service import ProjectService


# Per-project seeded enrichment volume (kept small; the point is the project
# COUNT scaling, not per-project depth).
_JOBS_PER_PROJECT = 2
_ENTRIES_PER_PROJECT = 3

# Depth-2 enrichment hits exactly three tables once each (grouped-IN):
#   agent_summaries  -> agent_jobs
#   agent_details    -> agent_jobs JOIN agent_executions
#   memory_entries   -> product_memory_entries
_EXPECTED_ENRICHMENT_QUERIES = 3

_N_SMALL = 3
_N_LARGE = 12  # the trace's ~11-item block — an unfixed path would emit ~36 here


class _Item:
    """Minimal stand-in for ProjectListItem consumed by _build_mcp_project_list."""

    def __init__(self, project: Project):
        self.id = project.id
        self.name = project.name
        self.status = project.status
        self.project_type = None
        self.series_number = project.series_number
        self.taxonomy_alias = getattr(project, "taxonomy_alias", None)
        self.created_at = None
        self.completed_at = None
        self.description = project.description
        self.mission = project.mission


async def _seed_enriched_projects(db_session, tenant_key: str, count: int) -> list[_Item]:
    """Seed ``count`` projects (one product), each with jobs+executions+memory.

    Returns ``_Item`` stand-ins built from projects RE-FETCHED via a SELECT so
    every column is eagerly loaded — building straight off freshly-added ORM
    objects would lazy-load an expired column (IO) outside the async greenlet.
    """
    from giljo_mcp.repositories.project_repository import ProjectRepository

    product = Product(
        id=str(uuid.uuid4()),
        name=f"BE-6067 Product {uuid.uuid4().hex[:6]}",
        description="d",
        tenant_key=tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.flush()

    base = datetime(2026, 1, 1, tzinfo=UTC)
    seq = 0
    for n in range(count):
        project = Project(
            id=str(uuid.uuid4()),
            name=f"BE-6067 P{n}",
            description="d",
            mission="m",
            status="active" if n == 0 else "inactive",
            tenant_key=tenant_key,
            product_id=product.id,
            series_number=96670 + n,
        )
        db_session.add(project)
        await db_session.flush()
        for j in range(_JOBS_PER_PROJECT):
            jid = str(uuid.uuid4())
            db_session.add(
                AgentJob(job_id=jid, project_id=project.id, tenant_key=tenant_key, job_type="implementer", mission="m")
            )
            await db_session.flush()
            db_session.add(
                AgentExecution(
                    job_id=jid,
                    agent_id=str(uuid.uuid4()),
                    tenant_key=tenant_key,
                    status="working",
                    agent_name=f"impl-{n}-{j}",
                    agent_display_name="implementer",
                )
            )
        for _ in range(_ENTRIES_PER_PROJECT):
            seq += 1
            db_session.add(
                ProductMemoryEntry(
                    id=uuid.uuid4(),
                    tenant_key=tenant_key,
                    product_id=product.id,
                    project_id=project.id,
                    sequence=seq,
                    entry_type="closeout",
                    source="agent",
                    timestamp=base + timedelta(hours=seq),
                    summary=f"entry {n}",
                )
            )
    await db_session.commit()

    # Re-fetch fully-hydrated rows (the BE-6071 test pattern) before wrapping.
    repo = ProjectRepository()
    seeded = await repo.list_projects(db_session, tenant_key, status=["active", "inactive"], product_id=product.id)
    return [_Item(p) for p in seeded]


def _service(db_session, tenant_key: str) -> ProjectService:
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = tenant_key
    return ProjectService(db_manager=MagicMock(), tenant_manager=tenant_manager, test_session=db_session)


async def _count_enrichment_sql(db_session, db_manager, service: ProjectService, items, tenant_key: str) -> int:
    """Run _build_mcp_project_list(depth=2) and count SQL hitting the N+1 tables.

    Counts cursor executions whose statement references ``agent_jobs`` or
    ``product_memory_entries`` — the exact tables the P8 trace looped over.
    """
    sync_engine = db_manager.async_engine.sync_engine
    hits: list[str] = []

    def _count(conn, cursor, statement, parameters, context, executemany):
        lowered = statement.lower()
        if "agent_jobs" in lowered or "product_memory_entries" in lowered:
            hits.append(statement)

    event.listen(sync_engine, "before_cursor_execute", _count)
    try:
        built = await service._build_mcp_project_list(items, depth=2, tenant_key=tenant_key)
    finally:
        event.remove(sync_engine, "before_cursor_execute", _count)

    # Correctness: every project enriched from the grouped maps (two-sided check).
    assert len(built) == len(items)
    for row in built:
        assert row["agent_summary"]["agent_count"] == _JOBS_PER_PROJECT
        assert len(row["agent_details"]) == _JOBS_PER_PROJECT
        assert len(row["memory_entries"]) == _ENTRIES_PER_PROJECT

    return len(hits)


@pytest.mark.asyncio
async def test_be6067_enrichment_sql_is_bounded_and_project_count_independent(db_session, db_manager, test_tenant_key):
    """Depth-2 enrichment hits agent_jobs/product_memory a CONSTANT number of
    times regardless of project count — the SQL-level N+1 guard."""
    # One product, _N_LARGE projects; measure a small SLICE vs the full set so
    # both share a tenant (the single-active-product-per-tenant index forbids two).
    items = await _seed_enriched_projects(db_session, test_tenant_key, _N_LARGE)
    assert len(items) >= _N_LARGE, f"expected >= {_N_LARGE} seeded projects, got {len(items)}"
    small_items = items[:_N_SMALL]
    large_items = items

    small_sql = await _count_enrichment_sql(
        db_session, db_manager, _service(db_session, test_tenant_key), small_items, test_tenant_key
    )
    large_sql = await _count_enrichment_sql(
        db_session, db_manager, _service(db_session, test_tenant_key), large_items, test_tenant_key
    )

    # Bounded: exactly the three grouped facet queries, not one-per-project.
    assert small_sql == _EXPECTED_ENRICHMENT_QUERIES, (
        f"depth-2 enrichment over {_N_SMALL} projects issued {small_sql} statements "
        f"against agent_jobs/product_memory_entries (expected {_EXPECTED_ENRICHMENT_QUERIES} grouped-IN queries)"
    )
    # Project-count-INDEPENDENT: the large set emits the SAME count, not N-scaled.
    # An unfixed N+1 would emit ~{_N_LARGE * 3} here.
    assert large_sql == small_sql, (
        f"N+1 REGRESSION: enrichment SQL scaled with project count — {small_sql} for {_N_SMALL} projects "
        f"vs {large_sql} for {_N_LARGE}. The /mcp agent path must issue a project-count-independent "
        f"(grouped) query set, not one query per project."
    )
