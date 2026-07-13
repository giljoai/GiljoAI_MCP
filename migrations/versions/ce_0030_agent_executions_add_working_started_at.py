# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Re-add working_started_at column to agent_executions (BE-5107).

Revision ID: ce_0030_agent_executions_add_working_started_at
Revises: ce_0029_drop_working_started_at_column
Create Date: 2026-05-20

Minimal replacement for the abandoned BE-5105 design. The column is set
exactly once on the first transition INTO ``working`` (from any other
status) by a SQLAlchemy event listener on AgentExecution.status. The
``duration_seconds`` @property reads (now - working_started_at) while
the agent is working, and freezes at (completed_at - working_started_at)
once status reaches 'complete' or 'closed'.

NO BACKFILL. Existing rows stay NULL. Pre-existing executions get
re-anchored on their next working transition, or stay '---' in the UI
forever -- that is acceptable; this is a fresh start.

Idempotency: existence-checked ADD COLUMN.

Edition Scope: CE -- ``agent_executions`` is a CE table.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0030_agent_executions_add_working_started_at"
down_revision = "ce_0029_drop_working_started_at_column"
branch_labels = None
depends_on = None


TABLE = "agent_executions"
COLUMN = "working_started_at"


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
    if not _has_column(conn, TABLE, COLUMN):
        op.add_column(
            TABLE,
            sa.Column(
                COLUMN,
                sa.DateTime(timezone=True),
                nullable=True,
                comment=(
                    "Anchored on first transition INTO 'working'. Read by "
                    "AgentExecution.duration_seconds; freezes on complete/closed."
                ),
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    if _has_column(conn, TABLE, COLUMN):
        op.drop_column(TABLE, COLUMN)
