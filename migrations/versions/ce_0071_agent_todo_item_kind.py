# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add the structural self-closeout marker to agent_todo_items (BE-9012b, D7).

Revision ID: ce_0071_agent_todo_item_kind
Revises: ce_0070_comm_participant_read_cursor
Create Date: 2026-07-03

The closeout-gate reframe ("Hub absorbs the bus", chain step b) stops re-matching
keyword regexes against every incomplete TODO at ``complete_job`` time and instead
reads a durable marker stamped once when the TODO is written (see
internal design notes §6 rows 4-6). This adds that column:

- ``todo_kind`` — one of ``self_closeout`` / ``closeout_intent`` / ``chain_drive``
  (``domain.todo_kinds``), or NULL for an ordinary work TODO. NULL is the common
  case and always blocks completion until the TODO is genuinely done.

Nullable, no backfill: every existing incomplete TODO carries NULL and the gate
tolerates it — a NULL-kind TODO falls back to the same classifier at read time, so
a legacy self-closeout TODO in flight at deploy still auto-clears (Data-facing DoD
answer (a): the reader tolerates the old shape; no data surgery). Incomplete-TODO
rows drain naturally as their jobs complete, so the NULL population is transient.

``agent_todo_items`` is a baseline table, so the same column is added to the
baseline create_table for parity — a fresh install gets it directly and converges
to the identical shape an upgraded deployment reaches through this migration.

Idempotent (existence-checked) because the CE installer reruns migrations on every
boot; reversible (downgrade drops the column).
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0071_agent_todo_item_kind"
down_revision = "ce_0070_comm_participant_read_cursor"
branch_labels = None
depends_on = None


def _column_exists(conn, column_name: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.columns"
                "  WHERE table_name = 'agent_todo_items'"
                "  AND column_name = :col"
                ")"
            ),
            {"col": column_name},
        ).scalar()
    )


def upgrade() -> None:
    # Idempotency guard: add the column only if absent (CE reruns on boot).
    conn = op.get_bind()
    if not _column_exists(conn, "todo_kind"):
        op.add_column("agent_todo_items", sa.Column("todo_kind", sa.String(32), nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "todo_kind"):
        op.drop_column("agent_todo_items", "todo_kind")
