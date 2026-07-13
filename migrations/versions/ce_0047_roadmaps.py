# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""FE-6022a: roadmaps + roadmap_items tables for the Roadmapping Pane.

Revision ID: ce_0047_roadmaps
Revises: ce_0046_list_tables_tenant_created_index
Create Date: 2026-06-12

Creates the thin 1:1 roadmap anchor and its junction table:

- ``roadmaps(id, tenant_key, product_id UNIQUE, last_generated_at, summary,
  created_at, updated_at)`` — one roadmap per product, auto-created on first write.
- ``roadmap_items(id, tenant_key, roadmap_id, item_type, project_id, task_id,
  priority, risk, complexity, created_at, updated_at)`` — junction rows tying a
  project OR task into the roadmap with ordering + AI risk/complexity.

The ``uq_roadmap_item`` UNIQUE uses ``NULLS NOT DISTINCT`` so the always-NULL
discriminator (one of project_id/task_id is NULL per row) cannot defeat
de-duplication / ON CONFLICT upserts. This mirrors the ORM model exactly so
fresh installs (migration chain) and the test schema (Base.metadata.create_all)
converge on the identical shape.

Idempotent: every CREATE TABLE is guarded by an information_schema existence
check. The CE installer reruns ``alembic upgrade head`` on every boot.

Edition Scope: CE — these are CE (tenant_key) tables; they live in
``migrations/versions/`` (NOT ``saas_versions/``). SaaS inherits them unchanged.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0047_roadmaps"
down_revision = "ce_0046_list_tables_tenant_created_index"
branch_labels = None
depends_on = None


ROADMAPS = "roadmaps"
ROADMAP_ITEMS = "roadmap_items"


def _has_table(conn, table: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.tables WHERE table_name = :table"),
        {"table": table},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_table(conn, ROADMAPS):
        op.create_table(
            ROADMAPS,
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_key", sa.String(length=36), nullable=False),
            sa.Column(
                "product_id",
                sa.String(length=36),
                sa.ForeignKey("products.id", ondelete="CASCADE"),
                nullable=False,
                unique=True,
            ),
            sa.Column("last_generated_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("summary", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
        )
        op.create_index("idx_roadmap_tenant", ROADMAPS, ["tenant_key"])

    if not _has_table(conn, ROADMAP_ITEMS):
        op.create_table(
            ROADMAP_ITEMS,
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_key", sa.String(length=36), nullable=False),
            sa.Column(
                "roadmap_id",
                sa.String(length=36),
                sa.ForeignKey("roadmaps.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("item_type", sa.String(length=20), nullable=False),
            sa.Column(
                "project_id",
                sa.String(length=36),
                sa.ForeignKey("projects.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column(
                "task_id",
                sa.String(length=36),
                sa.ForeignKey("tasks.id", ondelete="CASCADE"),
                nullable=True,
            ),
            sa.Column("priority", sa.Integer(), nullable=False, server_default=sa.text("0")),
            sa.Column("risk", sa.String(length=10), nullable=True),
            sa.Column("complexity", sa.String(length=10), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
            sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP")),
            # NULLS NOT DISTINCT mirrors the ORM model; required for upsert dedup.
            sa.UniqueConstraint(
                "roadmap_id",
                "item_type",
                "project_id",
                "task_id",
                name="uq_roadmap_item",
                postgresql_nulls_not_distinct=True,
            ),
        )
        op.create_index("idx_roadmap_item_tenant", ROADMAP_ITEMS, ["tenant_key"])
        op.create_index("idx_roadmap_item_roadmap", ROADMAP_ITEMS, ["roadmap_id"])


def downgrade() -> None:
    conn = op.get_bind()

    # Drop the junction first (FK to roadmaps).
    if _has_table(conn, ROADMAP_ITEMS):
        op.drop_table(ROADMAP_ITEMS)
    if _has_table(conn, ROADMAPS):
        op.drop_table(ROADMAPS)
