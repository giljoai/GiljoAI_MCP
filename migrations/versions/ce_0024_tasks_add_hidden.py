# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add hidden boolean column to tasks for UI declutter parity with projects.

Revision ID: ce_0024_tasks_add_hidden
Revises: ce_0023_tasks_shared_taxonomy_serial
Create Date: 2026-05-13

FE-5046 (Task UI Parity): ``projects`` carries a ``hidden`` flag (per-row UI
declutter) that the task model lacked. Mirroring the column on ``tasks`` lets
the FE expose the same hide/show affordance for tasks. The flag is NOT a
default visibility gate -- agents and the MCP ``list_tasks`` tool see hidden
and non-hidden rows alike; ``hidden`` only filters when an explicit
``hidden=true|false`` is passed.

Idempotent: column add is guarded by an information_schema lookup. Server
default ``false`` backfills existing rows on add.

Edition Scope: CE -- ``tasks`` is a CE table.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0024_tasks_add_hidden"
down_revision = "ce_0023_tasks_shared_taxonomy_serial"
branch_labels = None
depends_on = None


TASKS_TABLE = "tasks"
HIDDEN_COL = "hidden"


def _has_column(conn, table: str, column: str) -> bool:
    result = conn.execute(
        sa.text("SELECT 1 FROM information_schema.columns WHERE table_name = :table AND column_name = :column"),
        {"table": table, "column": column},
    )
    return result.first() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _has_column(conn, TASKS_TABLE, HIDDEN_COL):
        op.add_column(
            TASKS_TABLE,
            sa.Column(
                HIDDEN_COL,
                sa.Boolean(),
                nullable=False,
                server_default=sa.text("false"),
                comment="Whether task is hidden from default list view (UI declutter only)",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _has_column(conn, TASKS_TABLE, HIDDEN_COL):
        op.drop_column(TASKS_TABLE, HIDDEN_COL)
