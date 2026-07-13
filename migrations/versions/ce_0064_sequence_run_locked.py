# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add a non-null ``locked`` flag to sequence_runs (FE-6171).

Revision ID: ce_0064_sequence_run_locked
Revises: ce_0063_login_lockouts
Create Date: 2026-06-22

The Sequential Runner Phase 2 chain-election state machine needs a durable edit
lock on each run. ``locked=false`` is the Editing tier (membership / tickboxes
editable on all panes); pressing Stage flips it ``true`` (Staged tier — tickboxes
locked everywhere); Unstage flips it back. The lock lives on the run, not per
user, so it is tenant-scoped for free (a run belongs to a tenant; ADR-009).

Non-null with ``server_default='false'`` so existing rows (created before this
column) converge to the safe Editing state without a backfill — data-shape
self-heal via a default, not surgery. Idempotent (existence-checked) because the
CE installer reruns migrations on every boot; reversible (downgrade drops it).

``sequence_runs`` is a CE table (created in ce_0058), so this belongs in the CE
``versions/`` chain. It is NOT part of baseline_v37_unified (created post-baseline
in ce_0058), so there is no baseline block to mirror — a fresh install runs
baseline -> ... -> ce_0058 (creates the table) -> ce_0064 (adds this column) and
converges to the same shape as an upgraded deployment.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0064_sequence_run_locked"
down_revision = "ce_0063_login_lockouts"
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
    if not _column_exists(conn, "locked"):
        op.add_column(
            "sequence_runs",
            sa.Column("locked", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        )


def downgrade() -> None:
    op.drop_column("sequence_runs", "locked")
