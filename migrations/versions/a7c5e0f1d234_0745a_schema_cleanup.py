"""0745a_schema_cleanup - Security and data integrity fixes

Revision ID: a7c5e0f1d234
Revises: 2ab3b751cdba
Create Date: 2026-02-10

Post-audit schema cleanup addressing P0, P1, and P2 findings from Handover 0740.

Changes:
1. P0-1: Fix tasks.job_id FK to reference agent_jobs instead of mcp_agent_jobs
2. P0-1: Drop orphaned mcp_agent_jobs table (0 rows, replaced by agent_jobs)
3. P1-1: Drop 11 duplicate ix_* indexes (redundant with composite indexes)
4. P0-2: Fix products.product_memory server_default (remove sequential_history)
5. P1-2/P1-3/P1-5/P2-1: Drop 6 legacy columns from various tables

All operations are IDEMPOTENT - safe to run on databases in various states.

Handover: 0745a - Database Migration & P0 Fixes
"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# Set up logging
logger = logging.getLogger("alembic.migration.0745a")

# revision identifiers, used by Alembic.
revision: str = 'a7c5e0f1d234'
down_revision: Union[str, Sequence[str], None] = '2ab3b751cdba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helper utilities for idempotent operations
# ---------------------------------------------------------------------------

def _fk_exists(conn, constraint_name: str, table_name: str) -> bool:
    """Check if a foreign key constraint exists."""
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = :name AND table_name = :table "
        "AND constraint_type = 'FOREIGN KEY'"
    ), {"name": constraint_name, "table": table_name})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    """Check if an index exists."""
    result = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
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


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    """Apply all 0745a schema cleanup operations."""

    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. P0-1: Fix tasks.job_id FK (mcp_agent_jobs -> agent_jobs)
    # ------------------------------------------------------------------
    logger.info("[P0-1] Fixing tasks.job_id foreign key target...")

    if _fk_exists(conn, "fk_task_job", "tasks"):
        op.drop_constraint("fk_task_job", "tasks", type_="foreignkey")
        logger.info("  Dropped old FK constraint fk_task_job (pointed to mcp_agent_jobs)")
    else:
        logger.info("  FK constraint fk_task_job does not exist - skipping drop")

    if not _fk_exists(conn, "fk_task_agent_job", "tasks"):
        op.create_foreign_key(
            "fk_task_agent_job",
            "tasks",
            "agent_jobs",
            ["job_id"],
            ["job_id"],
        )
        logger.info("  Created new FK constraint fk_task_agent_job -> agent_jobs(job_id)")
    else:
        logger.info("  FK constraint fk_task_agent_job already exists - skipping create")

    # ------------------------------------------------------------------
    # 2. P0-1: Drop orphaned mcp_agent_jobs table
    # ------------------------------------------------------------------
    logger.info("[P0-1] Dropping orphaned mcp_agent_jobs table...")

    # Drop any indexes on the table first (idempotent via IF EXISTS)
    if _index_exists(conn, "ix_mcp_agent_jobs_project_id"):
        op.drop_index("ix_mcp_agent_jobs_project_id", table_name="mcp_agent_jobs")
        logger.info("  Dropped index ix_mcp_agent_jobs_project_id")

    if _table_exists(conn, "mcp_agent_jobs"):
        op.drop_table("mcp_agent_jobs")
        logger.info("  Dropped table mcp_agent_jobs")
    else:
        logger.info("  Table mcp_agent_jobs does not exist - skipping drop")

    # ------------------------------------------------------------------
    # 3. P1-1: Drop 11 duplicate ix_* indexes
    # ------------------------------------------------------------------
    duplicate_indexes = [
        "ix_api_keys_tenant_key",
        "ix_download_tokens_tenant_key",
        "ix_mcp_sessions_tenant_key",
        "ix_optimization_metrics_tenant_key",
        "ix_optimization_rules_tenant_key",
        "ix_products_tenant_key",
        "ix_settings_tenant_key",
        "ix_setup_state_database_initialized",
        "ix_users_tenant_key",
        "ix_vision_documents_tenant_key",
    ]

    logger.info("[P1-1] Dropping %d duplicate indexes...", len(duplicate_indexes))

    for idx_name in duplicate_indexes:
        if _index_exists(conn, idx_name):
            # Determine the table from the index metadata
            table_result = conn.execute(text(
                "SELECT tablename FROM pg_indexes WHERE indexname = :name"
            ), {"name": idx_name})
            row = table_result.fetchone()
            if row:
                table_name = row[0]
                op.drop_index(idx_name, table_name=table_name)
                logger.info("  Dropped index %s on %s", idx_name, table_name)
        else:
            logger.info("  Index %s does not exist - skipping", idx_name)

    # ------------------------------------------------------------------
    # 4. P0-2: Fix products.product_memory server_default
    #    Remove sequential_history from the default JSON
    # ------------------------------------------------------------------
    logger.info("[P0-2] Fixing products.product_memory server_default...")

    op.alter_column(
        "products",
        "product_memory",
        existing_type=sa.dialects.postgresql.JSONB(),
        server_default=sa.text("'{\"github\": {}, \"context\": {}}'::jsonb"),
        existing_nullable=True,
    )
    logger.info("  Updated product_memory default to {\"github\": {}, \"context\": {}}")

    # ------------------------------------------------------------------
    # 5. P1-2/P1-3/P1-5/P2-1: Drop 6 legacy columns
    # ------------------------------------------------------------------
    legacy_columns = [
        ("download_tokens", "is_used"),
        ("download_tokens", "downloaded_at"),
        ("agent_templates", "template_content"),
        ("template_archives", "template_content"),
        ("configurations", "user_id"),
        ("projects", "context_budget"),
    ]

    logger.info("[P1/P2] Dropping %d legacy columns...", len(legacy_columns))

    for table_name, col_name in legacy_columns:
        if _column_exists(conn, table_name, col_name):
            op.drop_column(table_name, col_name)
            logger.info("  Dropped %s.%s", table_name, col_name)
        else:
            logger.info("  Column %s.%s does not exist - skipping", table_name, col_name)

    logger.info("Migration 0745a complete: all schema cleanup operations applied.")


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    """Reverse all 0745a schema cleanup operations."""

    conn = op.get_bind()

    logger.info("Downgrading 0745a: reversing schema cleanup...")

    # ------------------------------------------------------------------
    # 5-reverse: Re-add 6 legacy columns
    # ------------------------------------------------------------------
    if not _column_exists(conn, "projects", "context_budget"):
        op.add_column("projects", sa.Column(
            "context_budget", sa.Integer(), nullable=True,
        ))
        logger.info("  Restored projects.context_budget")

    if not _column_exists(conn, "configurations", "user_id"):
        op.add_column("configurations", sa.Column(
            "user_id", sa.String(length=36), nullable=True,
        ))
        logger.info("  Restored configurations.user_id")

    if not _column_exists(conn, "template_archives", "template_content"):
        op.add_column("template_archives", sa.Column(
            "template_content", sa.Text(), nullable=True,
        ))
        logger.info("  Restored template_archives.template_content")

    if not _column_exists(conn, "agent_templates", "template_content"):
        op.add_column("agent_templates", sa.Column(
            "template_content", sa.Text(), nullable=True,
        ))
        logger.info("  Restored agent_templates.template_content")

    if not _column_exists(conn, "download_tokens", "downloaded_at"):
        op.add_column("download_tokens", sa.Column(
            "downloaded_at", sa.DateTime(timezone=True), nullable=True,
        ))
        logger.info("  Restored download_tokens.downloaded_at")

    if not _column_exists(conn, "download_tokens", "is_used"):
        op.add_column("download_tokens", sa.Column(
            "is_used", sa.Boolean(), nullable=True, server_default=sa.text("false"),
        ))
        logger.info("  Restored download_tokens.is_used")

    # ------------------------------------------------------------------
    # 4-reverse: Revert products.product_memory default
    # ------------------------------------------------------------------
    op.alter_column(
        "products",
        "product_memory",
        existing_type=sa.dialects.postgresql.JSONB(),
        server_default=sa.text(
            "'{\"github\": {}, \"context\": {}, \"sequential_history\": []}'::jsonb"
        ),
        existing_nullable=True,
    )
    logger.info("  Reverted product_memory default to include sequential_history")

    # ------------------------------------------------------------------
    # 3-reverse: Re-create duplicate indexes
    #   NOTE: We recreate them on the columns they originally indexed.
    #   These are single-column indexes that duplicated composite indexes.
    # ------------------------------------------------------------------
    index_definitions = [
        ("ix_api_keys_tenant_key", "api_keys", "tenant_key"),
        ("ix_download_tokens_tenant_key", "download_tokens", "tenant_key"),
        ("ix_mcp_sessions_tenant_key", "mcp_sessions", "tenant_key"),
        ("ix_optimization_metrics_tenant_key", "optimization_metrics", "tenant_key"),
        ("ix_optimization_rules_tenant_key", "optimization_rules", "tenant_key"),
        ("ix_products_tenant_key", "products", "tenant_key"),
        ("ix_settings_tenant_key", "settings", "tenant_key"),
        ("ix_setup_state_database_initialized", "setup_state", "database_initialized"),
        ("ix_users_tenant_key", "users", "tenant_key"),
        ("ix_vision_documents_tenant_key", "vision_documents", "tenant_key"),
    ]

    for idx_name, table_name, col_name in index_definitions:
        if not _index_exists(conn, idx_name):
            op.create_index(idx_name, table_name, [col_name])
            logger.info("  Restored index %s on %s(%s)", idx_name, table_name, col_name)

    # ------------------------------------------------------------------
    # 2-reverse: Re-create mcp_agent_jobs table
    #   Minimal skeleton matching the original model definition.
    # ------------------------------------------------------------------
    if not _table_exists(conn, "mcp_agent_jobs"):
        op.create_table(
            "mcp_agent_jobs",
            sa.Column("job_id", sa.String(length=36), primary_key=True),
            sa.Column("project_id", sa.String(length=36), nullable=True),
            sa.Column("tenant_key", sa.String(length=100), nullable=False),
            sa.Column("status", sa.String(length=50), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True),
                       server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                       server_default=sa.text("now()"), nullable=True),
        )
        op.create_index(
            "ix_mcp_agent_jobs_project_id", "mcp_agent_jobs", ["project_id"]
        )
        logger.info("  Restored table mcp_agent_jobs with ix_mcp_agent_jobs_project_id")

    # ------------------------------------------------------------------
    # 1-reverse: Revert tasks.job_id FK back to mcp_agent_jobs
    # ------------------------------------------------------------------
    if _fk_exists(conn, "fk_task_agent_job", "tasks"):
        op.drop_constraint("fk_task_agent_job", "tasks", type_="foreignkey")
        logger.info("  Dropped FK fk_task_agent_job")

    if not _fk_exists(conn, "fk_task_job", "tasks"):
        op.create_foreign_key(
            "fk_task_job",
            "tasks",
            "mcp_agent_jobs",
            ["job_id"],
            ["job_id"],
        )
        logger.info("  Restored FK fk_task_job -> mcp_agent_jobs(job_id)")

    logger.info("Downgrade 0745a complete.")
