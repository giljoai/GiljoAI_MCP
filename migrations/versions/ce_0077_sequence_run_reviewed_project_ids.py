# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add ``reviewed_project_ids`` JSONB to sequence_runs (BE-9098).

Revision ID: ce_0077_sequence_run_reviewed_project_ids
Revises: ce_0076_watermark_tenant_updated_indexes
Create Date: 2026-07-08

Chain review-badge persistence. Before this column the per-member "Review"
acknowledgment lived ONLY in a client-side Pinia Map, so it evaporated on every
refresh/navigation and the Review badge returned. This column durably records
which member projects the user has acknowledged, so ``isReviewed`` survives a
reload. Append-only, tenant-scoped through the owning SequenceRunService; NEVER
touches ``project_statuses`` (review stays NON-GATING — purge_run and chain
advancement key on CHAIN_TERMINAL_PROJECT_STATUSES only).

Non-null with ``server_default='[]'`` so existing rows (created before this
column) converge to the safe empty-list state without a backfill — data-shape
self-heal via a default, not surgery. Idempotent (existence-checked) because the
CE installer reruns migrations on every boot; reversible (downgrade drops it).

``sequence_runs`` is a CE table (created in ce_0058) and is NOT part of
``baseline_v37_unified`` (it was added post-baseline), so there is no baseline
block to mirror — a fresh install runs baseline -> ... -> ce_0058 (creates the
table) -> ce_0077 (adds this column) and converges to the identical shape as an
upgraded deployment. Belongs in the CE ``versions/`` chain.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision = "ce_0077_sequence_run_reviewed_project_ids"
down_revision = "ce_0076_watermark_tenant_updated_indexes"
branch_labels = None
depends_on = None


def _column_exists(conn, column_name: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.columns"
                "  WHERE table_name = 'sequence_runs'"
                "  AND column_name = :col"
                ")"
            ),
            {"col": column_name},
        ).scalar()
    )


def upgrade() -> None:
    # Idempotency guard: add the column only if absent (CE reruns on boot).
    conn = op.get_bind()
    if not _column_exists(conn, "reviewed_project_ids"):
        op.add_column(
            "sequence_runs",
            sa.Column(
                "reviewed_project_ids",
                postgresql.JSONB(),
                nullable=False,
                server_default=sa.text("'[]'::jsonb"),
            ),
        )


def downgrade() -> None:
    op.drop_column("sequence_runs", "reviewed_project_ids")
