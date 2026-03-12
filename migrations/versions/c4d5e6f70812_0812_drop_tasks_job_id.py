"""0812_drop_tasks_job_id - Remove unused Task.job_id column

Revision ID: c4d5e6f70812
Revises: b2c3d4e5f678
Create Date: 2026-03-12

Removes the dead task.job_id column, FK constraint, and indexes.
This column was added in Handover 0072 for task-to-agent-job integration
that was never implemented. No code reads, writes, or queries this field.

Handover: 0812 - Remove Unused task.job_id Foreign Key

Changes:
1. Drop FK constraint fk_task_agent_job (tasks.job_id -> agent_jobs.job_id)
2. Drop index idx_task_tenant_job (tenant_key, job_id)
3. Drop index idx_task_job (job_id)
4. Drop column tasks.job_id

All operations are IDEMPOTENT - safe to run on databases in various states.
"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger("alembic.migration.0812")

# revision identifiers, used by Alembic.
revision: str = "c4d5e6f70812"
down_revision: Union[str, Sequence[str], None] = "b2c3d4e5f678"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helper utilities for idempotent operations
# ---------------------------------------------------------------------------


def _fk_exists(conn, constraint_name: str, table_name: str) -> bool:
    """Check if a foreign key constraint exists."""
    result = conn.execute(
        text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = :name AND table_name = :table "
            "AND constraint_type = 'FOREIGN KEY'"
        ),
        {"name": constraint_name, "table": table_name},
    )
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    """Check if an index exists."""
    result = conn.execute(
        text("SELECT 1 FROM pg_indexes WHERE indexname = :name"),
        {"name": index_name},
    )
    return result.fetchone() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists on a table."""
    result = conn.execute(
        text(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name = :table AND column_name = :col"
        ),
        {"table": table_name, "col": column_name},
    )
    return result.fetchone() is not None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    """Drop unused tasks.job_id column, FK constraint, and indexes."""

    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Drop FK constraint fk_task_agent_job
    # ------------------------------------------------------------------
    logger.info("[0812] Dropping FK constraint fk_task_agent_job...")

    if _fk_exists(conn, "fk_task_agent_job", "tasks"):
        op.drop_constraint("fk_task_agent_job", "tasks", type_="foreignkey")
        logger.info("  Dropped FK constraint fk_task_agent_job")
    else:
        logger.info("  FK constraint fk_task_agent_job does not exist - skipping")

    # ------------------------------------------------------------------
    # 2. Drop composite index idx_task_tenant_job
    # ------------------------------------------------------------------
    logger.info("[0812] Dropping index idx_task_tenant_job...")

    if _index_exists(conn, "idx_task_tenant_job"):
        op.drop_index("idx_task_tenant_job", table_name="tasks")
        logger.info("  Dropped index idx_task_tenant_job")
    else:
        logger.info("  Index idx_task_tenant_job does not exist - skipping")

    # ------------------------------------------------------------------
    # 3. Drop single-column index idx_task_job
    # ------------------------------------------------------------------
    logger.info("[0812] Dropping index idx_task_job...")

    if _index_exists(conn, "idx_task_job"):
        op.drop_index("idx_task_job", table_name="tasks")
        logger.info("  Dropped index idx_task_job")
    else:
        logger.info("  Index idx_task_job does not exist - skipping")

    # ------------------------------------------------------------------
    # 4. Drop column tasks.job_id
    # ------------------------------------------------------------------
    logger.info("[0812] Dropping column tasks.job_id...")

    if _column_exists(conn, "tasks", "job_id"):
        op.drop_column("tasks", "job_id")
        logger.info("  Dropped column tasks.job_id")
    else:
        logger.info("  Column tasks.job_id does not exist - skipping")

    logger.info("Migration 0812 complete: tasks.job_id removed.")


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------


def downgrade() -> None:
    """Restore tasks.job_id column, FK constraint, and indexes."""

    conn = op.get_bind()

    logger.info("Downgrading 0812: restoring tasks.job_id...")

    # ------------------------------------------------------------------
    # 1. Re-add column tasks.job_id
    # ------------------------------------------------------------------
    if not _column_exists(conn, "tasks", "job_id"):
        op.add_column(
            "tasks",
            sa.Column("job_id", sa.String(length=36), nullable=True),
        )
        logger.info("  Restored column tasks.job_id")

    # ------------------------------------------------------------------
    # 2. Re-create single-column index idx_task_job
    # ------------------------------------------------------------------
    if not _index_exists(conn, "idx_task_job"):
        op.create_index("idx_task_job", "tasks", ["job_id"])
        logger.info("  Restored index idx_task_job")

    # ------------------------------------------------------------------
    # 3. Re-create composite index idx_task_tenant_job
    # ------------------------------------------------------------------
    if not _index_exists(conn, "idx_task_tenant_job"):
        op.create_index("idx_task_tenant_job", "tasks", ["tenant_key", "job_id"])
        logger.info("  Restored index idx_task_tenant_job")

    # ------------------------------------------------------------------
    # 4. Re-create FK constraint fk_task_agent_job
    # ------------------------------------------------------------------
    if not _fk_exists(conn, "fk_task_agent_job", "tasks"):
        op.create_foreign_key(
            "fk_task_agent_job",
            "tasks",
            "agent_jobs",
            ["job_id"],
            ["job_id"],
        )
        logger.info("  Restored FK constraint fk_task_agent_job -> agent_jobs(job_id)")

    logger.info("Downgrade 0812 complete: tasks.job_id restored.")
