# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Add sequence_runs table — durable state machine for the Sequential Multi-Project Runner.

Revision ID: ce_0058_sequence_runs
Revises: ce_0057_comm_thread_soft_delete
Create Date: 2026-06-18

Persists a multi-project sequential run: ordered project_ids, resolved run order,
current_index (resume point after an orchestrator crash), uniform execution_mode,
run status, review_policy, and a per-project status map.

Idempotent (table-existence guard) because the CE installer reruns migrations on
every boot; reversible (downgrade drops the table). No backfill — new table only.

Edition Scope: CE.
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision = "ce_0058_sequence_runs"
down_revision = "ce_0057_comm_thread_soft_delete"
branch_labels = None
depends_on = None


def _table_exists(conn, table: str) -> bool:
    return bool(
        conn.execute(
            sa.text("SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = :t)"),
            {"t": table},
        ).scalar()
    )


def upgrade() -> None:
    conn = op.get_bind()
    if _table_exists(conn, "sequence_runs"):
        return

    op.create_table(
        "sequence_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("tenant_key", sa.String(36), nullable=False),
        # Ordered list of project_id strings the user selected.
        sa.Column("project_ids", JSONB, nullable=False),
        # Topologically/roadmap-resolved run order (list of project_id strings).
        sa.Column("resolved_order", JSONB, nullable=False),
        # Index of the project currently being processed (0-based). Persisted
        # so a crash of the main orchestrator A can resume at current_index.
        sa.Column("current_index", sa.Integer, nullable=False, server_default="0"),
        # Uniform execution mode for the whole sequence.
        # Values mirror _STAGE_MODE_MAP execution_mode outputs:
        # multi_terminal, claude_code_cli, codex_cli, gemini_cli, antigravity_cli
        sa.Column("execution_mode", sa.String(50), nullable=False),
        # Run lifecycle status.
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        # Review policy: per_card (default) or auto_close.
        sa.Column("review_policy", sa.String(30), nullable=False, server_default="per_card"),
        # Per-project status map: {project_id -> status string}.
        sa.Column("project_statuses", JSONB, nullable=False, server_default=sa.text("'{}'::jsonb")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_index("idx_sequence_runs_tenant", "sequence_runs", ["tenant_key"])


def downgrade() -> None:
    conn = op.get_bind()
    if not _table_exists(conn, "sequence_runs"):
        return
    op.drop_index("idx_sequence_runs_tenant", table_name="sequence_runs")
    op.drop_table("sequence_runs")
