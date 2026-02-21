"""0371 - Drop vestigial project_type column from agent_templates

Revision ID: e1f2a3b4c567
Revises: d0a4f5b6c789
Create Date: 2026-02-21

Drop the project_type column from agent_templates. This column was always
NULL and never populated or read by any code path.

Handover: 0371 Phase 4.6 - Dead Code Cleanup

All operations are IDEMPOTENT - safe on fresh installs where baseline
already omits this column.
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c567"
down_revision: Union[str, Sequence[str], None] = "d0a4f5b6c789"
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

    if _column_exists(conn, "agent_templates", "project_type"):
        op.drop_column("agent_templates", "project_type")


def downgrade() -> None:
    op.add_column(
        "agent_templates",
        sa.Column("project_type", sa.String(50), nullable=True),
    )
