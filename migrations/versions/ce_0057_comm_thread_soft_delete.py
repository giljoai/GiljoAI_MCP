# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add comm_threads.deleted_at (soft delete for the Agent Message Hub) — FE/BE Hub delete.

Revision ID: ce_0057_comm_thread_soft_delete
Revises: ce_0056_server_runtime_metrics
Create Date: 2026-06-18

Adds a nullable ``deleted_at`` timestamp to ``comm_threads`` so threads can be
removed from the Message Hub without destroying their message history. NULL = a
live thread; non-NULL = soft-deleted (filtered out of every read). The CHT serial
counter keeps counting deleted rows, so a freed serial is never reused.

Idempotent (column-existence guard) because the CE installer reruns migrations on
every boot; reversible (downgrade drops the column). No backfill — existing rows
default to NULL (live), which is the correct pre-feature state.
"""

import sqlalchemy as sa
from alembic import op


revision = "ce_0057_comm_thread_soft_delete"
down_revision = "ce_0056_server_runtime_metrics"
branch_labels = None
depends_on = None


def _column_exists(conn, table: str, column: str) -> bool:
    return bool(
        conn.execute(
            sa.text(
                "SELECT EXISTS (SELECT FROM information_schema.columns WHERE table_name = :t AND column_name = :c)"
            ),
            {"t": table, "c": column},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()
    if _column_exists(conn, "comm_threads", "deleted_at"):
        return
    op.add_column(
        "comm_threads",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    conn = op.get_bind()
    if not _column_exists(conn, "comm_threads", "deleted_at"):
        return
    op.drop_column("comm_threads", "deleted_at")
