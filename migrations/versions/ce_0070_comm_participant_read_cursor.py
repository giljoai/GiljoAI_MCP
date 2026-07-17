# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add the server-persistent read cursor to comm_participants (BE-9012a, D6).

Revision ID: ce_0070_comm_participant_read_cursor
Revises: ce_0069_dedup_indexes_drift_reconcile
Create Date: 2026-07-03

The Agent Message Hub unification ("Hub absorbs the bus", chain step a) needs a
server-persistent per-(thread, participant) read cursor so that a unified Hub
read is O(N) drain-equivalent instead of an O(N^2) full-timeline re-read (see
internal design notes §1). This adds the two columns
``get_thread_history``'s new ``unread_only`` / ``mark_read`` params advance:

- ``last_read_at`` — the load-bearing filter. The unread read keys on
  ``Message.created_at > last_read_at``; keying on the timestamp (not the id) is
  reaper-safe — a reaped cursor message can never strand the reader.
- ``last_read_message_id`` — the exact boundary post, for reference/UI.

Nullable, no backfill: existing participant rows carry NULL and the read treats
NULL as "nothing read yet" (unread = the whole timeline). No FK on
``last_read_message_id`` — a deleted message leaves a harmless stale id, never a
broken constraint (tolerance, not surgery — Data-facing DoD answer (a)).

Idempotent (existence-checked per column) because the CE installer reruns
migrations on every boot; reversible (downgrade drops the columns).
``comm_participants`` is a CE table (created post-baseline in ce_0053), so this
belongs in the CE ``versions/`` chain and there is no baseline_v37 block to
mirror — a fresh install runs baseline -> ... -> ce_0053 (creates the table) ->
ce_0070 (adds these columns) and converges to the same shape as an upgraded
deployment.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0070_comm_participant_read_cursor"
down_revision = "ce_0069_dedup_indexes_drift_reconcile"
branch_labels = None
depends_on = None


_COLUMNS = (
    ("last_read_message_id", sa.String(36)),
    ("last_read_at", sa.DateTime(timezone=True)),
)


def _column_exists(conn, column_name: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                "SELECT EXISTS ("
                "  SELECT FROM information_schema.columns"
                "  WHERE table_name = 'comm_participants'"
                "  AND column_name = :col"
                ")"
            ),
            {"col": column_name},
        ).scalar()
    )


def upgrade() -> None:
    # Idempotency guard: add each column only if absent (CE reruns on boot).
    conn = op.get_bind()
    for name, coltype in _COLUMNS:
        if not _column_exists(conn, name):
            op.add_column("comm_participants", sa.Column(name, coltype, nullable=True))


def downgrade() -> None:
    conn = op.get_bind()
    for name, _coltype in reversed(_COLUMNS):
        if _column_exists(conn, name):
            op.drop_column("comm_participants", name)
