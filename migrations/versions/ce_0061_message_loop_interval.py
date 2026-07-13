# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add nullable loop_interval_minutes column to messages (FE-6140 Request Auto Check-in).

Revision ID: ce_0061_message_loop_interval
Revises: ce_0060_softdelete_recover_template_be6137
Create Date: 2026-06-19

Persists the operator-chosen auto-check-in interval (minutes) ON the
``loop_directive`` message that arms a thread loop (FE-6140). Before this the
interval emitted by AutoCheckinControls died in the composer — only the
``loop_directive`` boolean reached the backend. The column lets the interval
round-trip FE -> backend -> persisted and be surfaced on the get_my_turn /
get_thread_history poll responses (the harness-neutral inject surfaces a running
agent re-reads). Latest live loop_directive message on a thread wins, giving the
"rolling cadence, resets each check-in" behaviour with a single source of truth.

Nullable, no backfill: non-directive messages and all legacy rows carry NULL and
tolerate the column's absence (data-shape self-heal). Idempotent
(existence-checked) because the CE installer reruns migrations on every boot;
reversible (downgrade drops the column). ``messages`` is a CE table, so this
belongs in the CE ``versions/`` chain.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0061_message_loop_interval"
down_revision = "ce_0060_softdelete_recover_template_be6137"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Idempotency guard: skip if the column already exists (CE reruns on boot).
    conn = op.get_bind()
    exists = conn.execute(
        sa.text(
            "SELECT EXISTS ("
            "  SELECT FROM information_schema.columns"
            "  WHERE table_name = 'messages'"
            "  AND column_name = 'loop_interval_minutes'"
            ")"
        )
    ).scalar()
    if exists:
        return

    op.add_column(
        "messages",
        sa.Column("loop_interval_minutes", sa.Integer(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("messages", "loop_interval_minutes")
