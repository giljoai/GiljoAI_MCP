# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6052e: rename roadmap_items.priority -> sort_order (vocabulary collision).

Revision ID: ce_0050_roadmap_sort_order
Revises: ce_0049_heal_tool_rename_user_instructions
Create Date: 2026-06-14

Roadmap ``priority`` is a 0-based sort-order index (the position within a single
roadmap); task ``priority`` is an enum (low/med/high/critical). Same field name,
two unrelated meanings — a real vocabulary collision for any agent reasoning
across both surfaces. This renames the roadmap column to ``sort_order`` so the
two stop colliding. The task ``priority`` enum is NOT touched.

A ``RENAME COLUMN`` is the lowest-risk DDL: it carries every existing row in
place (no row rewrite, no data copy), is atomic + instant, and is reversible.
The migration runs BEFORE the new application code serves (Railway
``preDeployCommand`` and CE boot both ``alembic upgrade heads`` first), so there
is never new code expecting ``sort_order`` against an un-renamed column — no
dual-read / tolerance window is needed.

Idempotent: the rename only fires when ``priority`` still exists and
``sort_order`` does not yet, so the CE installer's rerun-on-boot is a clean
no-op (and a partially-migrated DB converges). Existence-guarded both directions.

Edition Scope: CE — ``roadmap_items`` is a CE (tenant_key) table; this migration
lives in ``migrations/versions/`` (NOT ``saas_versions/``). SaaS inherits it
unchanged. ``roadmap_items`` is not in the unified baseline (it was added by
ce_0047), so no baseline edit is needed.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0050_roadmap_sort_order"
down_revision = "ce_0049_heal_tool_rename_user_instructions"
branch_labels = None
depends_on = None


ROADMAP_ITEMS = "roadmap_items"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()
    # Only rename when the old column is still present and the new one is absent
    # — makes the boot-time rerun a no-op and converges a partially-migrated DB.
    if _has_column(conn, ROADMAP_ITEMS, "priority") and not _has_column(conn, ROADMAP_ITEMS, "sort_order"):
        op.alter_column(ROADMAP_ITEMS, "priority", new_column_name="sort_order")


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, ROADMAP_ITEMS, "sort_order") and not _has_column(conn, ROADMAP_ITEMS, "priority"):
        op.alter_column(ROADMAP_ITEMS, "sort_order", new_column_name="priority")
