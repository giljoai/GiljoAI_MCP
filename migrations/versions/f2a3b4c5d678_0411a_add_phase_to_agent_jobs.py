"""0411a - Add phase column to agent_jobs table

Revision ID: f2a3b4c5d678
Revises: e1f2a3b4c567
Create Date: 2026-02-24

Add the phase column to agent_jobs for multi-terminal execution ordering.
Phase indicates when an agent should be spawned relative to others:
- NULL: no phase constraint (legacy behavior)
- 1: first phase (spawned first)
- Same value: agents run in parallel

All operations are IDEMPOTENT - safe on fresh installs where baseline
already includes this column.

Handover: 0411a - Add phase to AgentJob model
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "f2a3b4c5d678"
down_revision: Union[str, Sequence[str], None] = "e1f2a3b4c567"
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

    if not _column_exists(conn, "agent_jobs", "phase"):
        op.add_column(
            "agent_jobs",
            sa.Column(
                "phase",
                sa.Integer(),
                nullable=True,
                comment="Execution phase for multi-terminal ordering (1=first, same=parallel)",
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()

    if _column_exists(conn, "agent_jobs", "phase"):
        op.drop_column("agent_jobs", "phase")
