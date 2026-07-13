# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add working_started_at column to agent_executions (BE-5105).

Revision ID: ce_0028_agent_executions_add_working_started_at
Revises: ce_0027_backfill_active_staging_orch_phase
Create Date: 2026-05-20

Splits the spawn timestamp (``started_at``, set by IMP-5036 for ORDER BY
correctness) from the working-clock anchor. The new column is set exactly
once on the first transition INTO ``working`` (from waiting / idle /
sleeping / blocked / awaiting_user / silent), and reset only on a
complete→working reactivation via begin_working(reset=True).

Backfill rule:
- Any non-waiting row gets ``working_started_at = started_at`` so existing
  running, blocked, idle, sleeping, awaiting_user, silent, and completed
  executions get a sensible anchor that yields the historical duration.
- Rows still in ``waiting`` keep ``working_started_at IS NULL`` so the
  JobsTab timer stops ticking for them (the actual BE-5105 bug fix).

Idempotency: existence-checked ADD COLUMN; backfill uses ``IS NULL`` guard.

Edition Scope: CE — ``agent_executions`` is a CE table.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0028_agent_executions_add_working_started_at"
down_revision = "ce_0027_backfill_active_staging_orch_phase"
branch_labels = None
depends_on = None


TABLE = "agent_executions"
COLUMN = "working_started_at"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, TABLE, COLUMN):
        op.add_column(
            TABLE,
            sa.Column(
                COLUMN,
                sa.DateTime(timezone=True),
                nullable=True,
                comment=(
                    "Set once on first waiting→working transition; reset only on "
                    "complete→working reactivation. Anchor for duration_seconds."
                ),
            ),
        )

    # Backfill: any non-waiting execution gets a working-clock anchor equal to
    # its spawn timestamp (the historical, pre-BE-5105 semantics of started_at).
    # Waiting rows stay NULL so the timer stops ticking — that IS the fix.
    op.execute(
        sa.text(
            "UPDATE agent_executions SET working_started_at = started_at "
            "WHERE working_started_at IS NULL AND status <> 'waiting' "
            "AND started_at IS NOT NULL"
        )
    )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_column(conn, TABLE, COLUMN):
        op.drop_column(TABLE, COLUMN)
