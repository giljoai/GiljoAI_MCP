# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""FE-6022d: roadmap_items.blocked + blocked_reason (dependency flag).

Revision ID: ce_0048_roadmap_item_blocked
Revises: ce_0047_roadmaps
Create Date: 2026-06-12

Adds an agent-flagged dependency-block to roadmap items:

- ``blocked``        BOOLEAN NOT NULL DEFAULT false — drives the red BLOCKED badge.
- ``blocked_reason`` TEXT     NULL                — the "blocked by the X gate" note
  the agent lifts out of the description; shown in the badge tooltip / 3rd card row.

Both are roadmap-planning state (set via ``update_roadmap_metadata`` alongside
risk/complexity), NOT the underlying project/task lifecycle status.

Idempotent: each ADD COLUMN is guarded by an information_schema column-existence
check (the CE installer reruns ``alembic upgrade head`` on every boot). The NOT
NULL + server_default false means existing rows backfill to ``blocked = false``
without a separate UPDATE.

Edition Scope: CE — ``roadmap_items`` is a CE (tenant_key) table; this migration
lives in ``migrations/versions/`` (NOT ``saas_versions/``). SaaS inherits it
unchanged. ``roadmap_items`` is not in the unified baseline (it was added by
ce_0047), so no baseline edit is needed.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0048_roadmap_item_blocked"
down_revision = "ce_0047_roadmaps"
branch_labels = None
depends_on = None


ROADMAP_ITEMS = "roadmap_items"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :column"
        ),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, ROADMAP_ITEMS, "blocked"):
        op.add_column(
            ROADMAP_ITEMS,
            sa.Column(
                "blocked",
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
            ),
        )

    if not _has_column(conn, ROADMAP_ITEMS, "blocked_reason"):
        op.add_column(
            ROADMAP_ITEMS,
            sa.Column("blocked_reason", sa.Text(), nullable=True),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_column(conn, ROADMAP_ITEMS, "blocked_reason"):
        op.drop_column(ROADMAP_ITEMS, "blocked_reason")

    if _has_column(conn, ROADMAP_ITEMS, "blocked"):
        op.drop_column(ROADMAP_ITEMS, "blocked")
