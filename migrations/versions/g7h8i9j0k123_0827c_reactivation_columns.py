"""0827c - Add reactivation tracking columns to agent_executions

Revision ID: g7h8i9j0k123
Revises: d5e6f7a8b901
Create Date: 2026-03-19

Add accumulated_duration_seconds and reactivation_count columns to
agent_executions for tracking cumulative working time and reactivation
cycles when completed agents resume work.

All operations are IDEMPOTENT - safe on fresh installs where baseline
already includes these columns.

Handover: 0827c - reactivate_job + dismiss_reactivation tools
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "g7h8i9j0k123"
down_revision: Union[str, Sequence[str], None] = "d5e6f7a8b901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col"
        ),
        {"table": table_name, "col": column_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if not _column_exists(conn, "agent_executions", "accumulated_duration_seconds"):
        op.add_column(
            "agent_executions",
            sa.Column(
                "accumulated_duration_seconds",
                sa.Float(),
                nullable=False,
                server_default="0.0",
                comment="Total working time across reactivation cycles (seconds)",
            ),
        )

    if not _column_exists(conn, "agent_executions", "reactivation_count"):
        op.add_column(
            "agent_executions",
            sa.Column(
                "reactivation_count",
                sa.Integer(),
                nullable=False,
                server_default="0",
                comment="Number of times this agent has been reactivated after completion",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "agent_executions", "reactivation_count"):
        op.drop_column("agent_executions", "reactivation_count")

    if _column_exists(conn, "agent_executions", "accumulated_duration_seconds"):
        op.drop_column("agent_executions", "accumulated_duration_seconds")
