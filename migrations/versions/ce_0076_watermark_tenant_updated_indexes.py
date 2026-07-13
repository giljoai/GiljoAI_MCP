# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""TSK-9076: (tenant_key, updated_at) indexes for the backup watermark sweep.

Revision ID: ce_0076_watermark_tenant_updated_indexes
Revises: ce_0075_projects_ever_launched_at
Create Date: 2026-07-08

The nightly backup-snapshot scheduler (``saas/backup/scheduler.py``, BE-9061)
computes a per-tenant change watermark to skip snapshotting unchanged tenants.
It runs ``MAX(updated_at) WHERE tenant_key = ?`` against every table that
carries BOTH ``tenant_key`` and ``updated_at``, discovered at runtime from
``information_schema`` (``_discover_watermark_sources``) and ``UNION ALL``-ed
into one query. The sweep is all-or-nothing: it is only as fast as its slowest
source table, so a single unindexed source turns the whole watermark into a
tenant-filtered heap scan + aggregate.

None of these source tables had a ``(tenant_key, updated_at)``-leading index.
The existing tenant indexes lead on ``tenant_key`` alone (or ``tenant_key`` +
some other column), which seeks the tenant's rows but still reads every one of
them to find the max. A composite ``(tenant_key, updated_at)`` lets Postgres
satisfy the equality filter AND the aggregate from the index alone — an index
scan to the tenant's last ``updated_at`` entry instead of a per-tenant heap
scan. Cheap today (these tables are low-hundreds of rows per tenant); at
thousands of rows/tenant each source would otherwise become a per-cycle scan.

Chosen over the "restructure" alternative (a denormalised per-tenant watermark
column maintained on every write): the index is the strictly smaller correct
fix — it touches no write path and no application code, only the physical access
path — and EXPLAIN confirms it converts the sweep's per-table plan from a
Seq Scan + Aggregate to an Index Only Scan. The restructure would have to
instrument ~20 write paths and is disproportionate to a read-side sweep.

Coverage: EVERY CE watermark source table that carries (tenant_key, updated_at)
— all 21. The sweep discovers its sources dynamically, so coverage is kept
uniform: each source gets exactly one composite. A couple of these tables are
single-row-per-tenant today (e.g. ``tenant_skills_ack``, whose PK is
``tenant_key``), where the composite adds no measurable gain over the existing
key; they are still indexed to keep the set uniform and to stay fast if any of
them grows. None of these composites is leftmost-covered by a droppable index,
so this does not reintroduce the ce_0069 dedup target. The two SaaS-only source
tables (``organization_plans``, ``tenant_trials``) are indexed in the sibling
``saas_028`` migration — they only exist, and are only swept, under
GILJO_MODE=saas.

Idempotent: every statement is ``CREATE INDEX IF NOT EXISTS`` (plain, NOT
CONCURRENTLY so it runs inside Alembic's transaction, matching ce_0045 / ce_0051
/ ce_0074). The CE installer reruns ``alembic upgrade head`` on every boot, so a
second run is a clean no-op. Reversible: downgrade drops each by name IF EXISTS.

Baseline: NOT mirrored into ``baseline_v37_unified.py`` — matching the nearest
precedent (ce_0051, the multi-index perf migration that also serves a SaaS-only
background sweep on CE tables). This incremental's IF-NOT-EXISTS guard creates
the indexes on fresh installs too (baseline -> incremental), so fresh and
existing DBs converge without a baseline edit.

Edition Scope: Both. Every table here is a CE-model table, so this migration
lives in ``migrations/versions/`` (never ``saas_versions/``). The backup sweep
that benefits is SaaS-only, but the tables and their indexes are CE — the same
CE-tables/SaaS-beneficiary shape as ce_0051.
"""

from alembic import op


revision = "ce_0076_watermark_tenant_updated_indexes"
down_revision = "ce_0075_projects_ever_launched_at"
branch_labels = None
depends_on = None


# Every CE watermark source table carrying (tenant_key, updated_at) — all 21,
# indexed uniformly (see docstring).
_TABLES = (
    "agent_templates",
    "agent_todo_items",
    "comm_threads",
    "configurations",
    "organizations",
    "product_agent_assignments",
    "product_architectures",
    "product_memory_entries",
    "product_tech_stacks",
    "product_test_configs",
    "products",
    "projects",
    "roadmap_items",
    "roadmaps",
    "sequence_runs",
    "settings",
    "setup_state",
    "taxonomy_types",
    "tenant_skills_ack",
    "user_field_priorities",
    "vision_documents",
)


def _index_name(table: str) -> str:
    return f"idx_{table}_tenant_updated"


def upgrade() -> None:
    for table in _TABLES:
        op.execute(f"CREATE INDEX IF NOT EXISTS {_index_name(table)} ON {table} (tenant_key, updated_at)")


def downgrade() -> None:
    for table in reversed(_TABLES):
        op.execute(f"DROP INDEX IF EXISTS {_index_name(table)}")
