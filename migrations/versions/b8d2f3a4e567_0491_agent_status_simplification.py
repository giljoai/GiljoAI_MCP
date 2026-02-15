"""0491_agent_status_simplification - Remove failed/cancelled from AgentExecution

Revision ID: b8d2f3a4e567
Revises: a7c5e0f1d234
Create Date: 2026-02-12

Handover 0491: Agent Status Simplification (Phase 2 - Backend)

Changes:
1. Migrate 'failed' executions to 'blocked' (copy failure_reason to block_reason)
2. Migrate 'cancelled' executions to 'decommissioned'
3. Add 'silent' to CHECK constraint
4. Drop 'failed' and 'cancelled' from CHECK constraint
5. Drop failure_reason column from agent_executions

All operations are IDEMPOTENT - safe to run on databases in various states.
"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# Set up logging
logger = logging.getLogger("alembic.migration.0491")

# revision identifiers, used by Alembic.
revision: str = "b8d2f3a4e567"
down_revision: Union[str, None] = "a7c5e0f1d234"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(conn, constraint_name: str) -> bool:
    """Check if a constraint exists in pg_constraint."""
    result = conn.execute(text(
        "SELECT 1 FROM pg_constraint WHERE conname = :name"
    ), {"name": constraint_name})
    return result.fetchone() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists on a table."""
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :col"
    ), {"table": table_name, "col": column_name})
    return result.fetchone() is not None


def _table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table AND table_schema = 'public'"
    ), {"table": table_name})
    return result.fetchone() is not None


def upgrade() -> None:
    """Simplify agent execution statuses: remove failed/cancelled, add silent."""
    conn = op.get_bind()

    # Step 1: Migrate 'failed' executions to 'blocked'
    # Copy failure_reason to block_reason where it exists
    result = conn.execute(
        text("""
            UPDATE agent_executions
            SET status = 'blocked',
                block_reason = COALESCE(block_reason, failure_reason, 'Migrated from failed status')
            WHERE status = 'failed'
        """)
    )
    logger.info(f"Migrated {result.rowcount} 'failed' executions to 'blocked'")

    # Step 2: Migrate 'cancelled' executions to 'decommissioned'
    result = conn.execute(
        text("""
            UPDATE agent_executions
            SET status = 'decommissioned'
            WHERE status = 'cancelled'
        """)
    )
    logger.info(f"Migrated {result.rowcount} 'cancelled' executions to 'decommissioned'")

    # Step 3: Drop old CHECK constraint and create new one (idempotent)
    if _constraint_exists(conn, "ck_agent_execution_status"):
        op.drop_constraint("ck_agent_execution_status", "agent_executions", type_="check")
        logger.info("Dropped old ck_agent_execution_status constraint")

    # Create new constraint with simplified statuses
    op.create_check_constraint(
        "ck_agent_execution_status",
        "agent_executions",
        "status IN ('waiting', 'working', 'blocked', 'complete', 'silent', 'decommissioned')",
    )
    logger.info("Created new ck_agent_execution_status constraint")

    # Step 4: Drop failure_reason column (idempotent)
    if _column_exists(conn, "agent_executions", "failure_reason"):
        op.drop_column("agent_executions", "failure_reason")
        logger.info("Dropped failure_reason column from agent_executions")
    else:
        logger.info("failure_reason column already dropped")

    # Step 5: Update legacy mcp_agent_jobs CHECK if table still exists
    if _table_exists(conn, "mcp_agent_jobs") and _constraint_exists(conn, "ck_mcp_agent_job_status"):
        op.drop_constraint("ck_mcp_agent_job_status", "mcp_agent_jobs", type_="check")
        op.create_check_constraint(
            "ck_mcp_agent_job_status",
            "mcp_agent_jobs",
            "status IN ('waiting', 'working', 'blocked', 'complete', 'silent', 'decommissioned')",
        )
        logger.info("Updated mcp_agent_jobs CHECK constraint")
    else:
        logger.info("mcp_agent_jobs table not found or constraint already updated")


def downgrade() -> None:
    """Revert: restore failed/cancelled statuses and failure_reason column."""
    conn = op.get_bind()

    # Restore failure_reason column
    op.add_column(
        "agent_executions",
        sa.Column("failure_reason", sa.Text(), nullable=True,
                   comment="Reason for execution failure (full error description)"),
    )

    # Drop new constraint
    try:
        op.drop_constraint("ck_agent_execution_status", "agent_executions", type_="check")
    except Exception:
        pass

    # Restore old constraint
    op.create_check_constraint(
        "ck_agent_execution_status",
        "agent_executions",
        "status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned')",
    )

    # Migrate 'silent' back to 'blocked' (best effort)
    conn.execute(
        text("UPDATE agent_executions SET status = 'blocked' WHERE status = 'silent'")
    )

    logger.info("Downgrade complete: restored failed/cancelled statuses")
