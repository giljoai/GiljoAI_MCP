# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add a nullable ``chain_mission`` text column to sequence_runs (BE-6185).

Revision ID: ce_0065_sequence_run_chain_mission
Revises: ce_0064_sequence_run_locked
Create Date: 2026-06-24

The dedicated-conductor chain (BE-6184) has a project-less conductor that owns no
project, so there is no head-project ``projects.mission`` to reuse for the
cross-project chain plan. ``projects.mission`` is also Text NOT NULL and never
locks, which is the wrong shape: the chain mission must be USER-EDITABLE before
Implement and LOCKED after. This adds the dedicated storage cell on the run.

Nullable, no backfill: existing rows carry NULL and the solo / pre-population
path renders ``chain_mission: None`` (data-shape self-heal, tolerance not
surgery). Idempotent (existence-checked) because the CE installer reruns
migrations on every boot; reversible (downgrade drops it).

``sequence_runs`` is a CE table (created post-baseline in ce_0058), so this
belongs in the CE ``versions/`` chain and there is NO baseline block to mirror:
a fresh install runs baseline -> ... -> ce_0058 (creates the table) -> ce_0065
(adds this column) and converges to the same shape as an upgraded deployment.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0065_sequence_run_chain_mission"
down_revision = "ce_0064_sequence_run_locked"
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
    if not _column_exists(conn, "chain_mission"):
        op.add_column("sequence_runs", sa.Column("chain_mission", sa.Text(), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "chain_mission"):
        op.drop_column("sequence_runs", "chain_mission")
