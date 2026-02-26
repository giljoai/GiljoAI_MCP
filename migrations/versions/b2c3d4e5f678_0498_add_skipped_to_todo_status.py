"""0498 - Add 'skipped' to AgentTodoItem status CHECK constraint

Revision ID: b2c3d4e5f678
Revises: a1b2c3d4e567
Create Date: 2026-02-26

Handover 0498: Early Termination Protocol - Phase 1 (Schema)

Adds 'skipped' as a valid status for agent_todo_items, enabling
the early termination protocol to mark incomplete TODOs as skipped
(rather than completed) for audit trail clarity.

All operations are IDEMPOTENT - safe on fresh installs and upgrades.
"""
from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text

revision: str = "b2c3d4e5f678"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e567"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(conn, constraint_name: str) -> bool:
    """Check if a constraint exists in pg_constraint."""
    result = conn.execute(
        text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
        {"name": constraint_name},
    )
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    if _constraint_exists(conn, "ck_agent_todo_item_status"):
        op.drop_constraint("ck_agent_todo_item_status", "agent_todo_items", type_="check")

    op.create_check_constraint(
        "ck_agent_todo_item_status",
        "agent_todo_items",
        "status IN ('pending', 'in_progress', 'completed', 'skipped')",
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Migrate any 'skipped' items to 'completed' before tightening constraint
    conn.execute(
        text("UPDATE agent_todo_items SET status = 'completed' WHERE status = 'skipped'")
    )

    if _constraint_exists(conn, "ck_agent_todo_item_status"):
        op.drop_constraint("ck_agent_todo_item_status", "agent_todo_items", type_="check")

    op.create_check_constraint(
        "ck_agent_todo_item_status",
        "agent_todo_items",
        "status IN ('pending', 'in_progress', 'completed')",
    )
