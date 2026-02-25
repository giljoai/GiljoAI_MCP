"""0497b - Add result column to agent_executions table

Revision ID: a1b2c3d4e567
Revises: f2a3b4c5d678
Create Date: 2026-02-25

Add the result JSON column to agent_executions for persisting structured
completion results from agents (summary, artifacts, commits).

All operations are IDEMPOTENT - safe on fresh installs where baseline
already includes this column.

Handover: 0497b - Persist Agent Completion Results
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e567"
down_revision: Union[str, Sequence[str], None] = "f2a3b4c5d678"
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

    if not _column_exists(conn, "agent_executions", "result"):
        op.add_column(
            "agent_executions",
            sa.Column(
                "result",
                sa.JSON(),
                nullable=True,
                comment="Structured completion result from agent (summary, artifacts, commits)",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "agent_executions", "result"):
        op.drop_column("agent_executions", "result")
