"""0440a_project_taxonomy - Add project types and taxonomy fields

Revision ID: d0a4f5b6c789
Revises: c9d1e2f3a4b5
Create Date: 2026-02-21

Add project taxonomy system for structured project naming (e.g., BE-0001, FE-0002a).

Changes:
1. Create project_types table with abbreviation, label, color, sort_order
2. Add project_type_id FK, series_number, subseries columns to projects table
3. Add unique constraint uq_project_taxonomy on (tenant_key, project_type_id, series_number, subseries)

All operations are IDEMPOTENT - safe to run on databases in various states.

Handover: 0440a - Project Taxonomy Phase 1 (Database Schema + Models)
"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

logger = logging.getLogger("alembic.migration.0440a")

# revision identifiers, used by Alembic.
revision: str = 'd0a4f5b6c789'
down_revision: Union[str, Sequence[str], None] = 'c9d1e2f3a4b5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helper utilities for idempotent operations
# ---------------------------------------------------------------------------

def _table_exists(conn, table_name: str) -> bool:
    """Check if a table exists."""
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.tables "
        "WHERE table_name = :table AND table_schema = 'public'"
    ), {"table": table_name})
    return result.fetchone() is not None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    """Check if a column exists on a table."""
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :col"
    ), {"table": table_name, "col": column_name})
    return result.fetchone() is not None


def _constraint_exists(conn, constraint_name: str) -> bool:
    """Check if a constraint exists."""
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = :name"
    ), {"name": constraint_name})
    return result.fetchone() is not None


def _index_exists(conn, index_name: str) -> bool:
    """Check if an index exists."""
    result = conn.execute(text(
        "SELECT 1 FROM pg_indexes WHERE indexname = :name"
    ), {"name": index_name})
    return result.fetchone() is not None


def _fk_exists(conn, constraint_name: str, table_name: str) -> bool:
    """Check if a foreign key constraint exists."""
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.table_constraints "
        "WHERE constraint_name = :name AND table_name = :table "
        "AND constraint_type = 'FOREIGN KEY'"
    ), {"name": constraint_name, "table": table_name})
    return result.fetchone() is not None


# ---------------------------------------------------------------------------
# Upgrade
# ---------------------------------------------------------------------------

def upgrade() -> None:
    """Create project_types table and add taxonomy columns to projects."""

    conn = op.get_bind()

    # ------------------------------------------------------------------
    # 1. Create project_types table
    # ------------------------------------------------------------------
    logger.info("[0440a] Creating project_types table...")

    if not _table_exists(conn, "project_types"):
        op.create_table(
            "project_types",
            sa.Column("id", sa.String(length=36), primary_key=True),
            sa.Column("tenant_key", sa.String(length=36), nullable=False),
            sa.Column("abbreviation", sa.String(length=4), nullable=False),
            sa.Column("label", sa.String(length=50), nullable=False),
            sa.Column("color", sa.String(length=7), nullable=False,
                       server_default=sa.text("'#607D8B'")),
            sa.Column("sort_order", sa.Integer(), nullable=True,
                       server_default=sa.text("0")),
            sa.Column("created_at", sa.DateTime(timezone=True),
                       server_default=sa.text("now()"), nullable=True),
            sa.Column("updated_at", sa.DateTime(timezone=True),
                       server_default=sa.text("now()"), nullable=True),
            sa.UniqueConstraint("tenant_key", "abbreviation",
                                name="uq_project_type_abbr"),
        )
        op.create_index("idx_project_type_tenant", "project_types", ["tenant_key"])
        logger.info("  Created table project_types with uq_project_type_abbr and idx_project_type_tenant")
    else:
        logger.info("  Table project_types already exists - skipping create")

    # ------------------------------------------------------------------
    # 2. Add taxonomy columns to projects table
    # ------------------------------------------------------------------
    logger.info("[0440a] Adding taxonomy columns to projects table...")

    if not _column_exists(conn, "projects", "project_type_id"):
        op.add_column("projects", sa.Column(
            "project_type_id", sa.String(length=36), nullable=True,
        ))
        logger.info("  Added projects.project_type_id")
    else:
        logger.info("  Column projects.project_type_id already exists - skipping")

    if not _column_exists(conn, "projects", "series_number"):
        op.add_column("projects", sa.Column(
            "series_number", sa.Integer(), nullable=True,
        ))
        logger.info("  Added projects.series_number")
    else:
        logger.info("  Column projects.series_number already exists - skipping")

    if not _column_exists(conn, "projects", "subseries"):
        op.add_column("projects", sa.Column(
            "subseries", sa.String(length=1), nullable=True,
        ))
        logger.info("  Added projects.subseries")
    else:
        logger.info("  Column projects.subseries already exists - skipping")

    # ------------------------------------------------------------------
    # 3. Add FK constraint: projects.project_type_id -> project_types.id
    # ------------------------------------------------------------------
    logger.info("[0440a] Adding FK constraint for project_type_id...")

    fk_name = "fk_projects_project_type_id"
    if not _fk_exists(conn, fk_name, "projects"):
        op.create_foreign_key(
            fk_name,
            "projects",
            "project_types",
            ["project_type_id"],
            ["id"],
            ondelete="SET NULL",
        )
        logger.info("  Created FK %s -> project_types(id) ON DELETE SET NULL", fk_name)
    else:
        logger.info("  FK %s already exists - skipping", fk_name)

    # ------------------------------------------------------------------
    # 4. Add unique constraint for taxonomy uniqueness
    # ------------------------------------------------------------------
    logger.info("[0440a] Adding taxonomy unique constraint...")

    uq_name = "uq_project_taxonomy"
    if not _constraint_exists(conn, uq_name):
        # Use NULLS NOT DISTINCT so NULL subseries is treated as equal (PG15+)
        conn.execute(text(
            "ALTER TABLE projects ADD CONSTRAINT uq_project_taxonomy "
            "UNIQUE NULLS NOT DISTINCT (tenant_key, project_type_id, series_number, subseries)"
        ))
        logger.info("  Created unique constraint %s (NULLS NOT DISTINCT)", uq_name)
    else:
        logger.info("  Unique constraint %s already exists - skipping", uq_name)

    logger.info("Migration 0440a complete: project taxonomy schema applied.")


# ---------------------------------------------------------------------------
# Downgrade
# ---------------------------------------------------------------------------

def downgrade() -> None:
    """Remove project taxonomy columns and drop project_types table."""

    conn = op.get_bind()

    logger.info("Downgrading 0440a: removing project taxonomy schema...")

    # ------------------------------------------------------------------
    # 4-reverse: Drop taxonomy unique constraint
    # ------------------------------------------------------------------
    uq_name = "uq_project_taxonomy"
    if _constraint_exists(conn, uq_name):
        op.drop_constraint(uq_name, "projects", type_="unique")
        logger.info("  Dropped unique constraint %s", uq_name)

    # ------------------------------------------------------------------
    # 3-reverse: Drop FK constraint
    # ------------------------------------------------------------------
    fk_name = "fk_projects_project_type_id"
    if _fk_exists(conn, fk_name, "projects"):
        op.drop_constraint(fk_name, "projects", type_="foreignkey")
        logger.info("  Dropped FK %s", fk_name)

    # ------------------------------------------------------------------
    # 2-reverse: Drop taxonomy columns from projects
    # ------------------------------------------------------------------
    for col_name in ("subseries", "series_number", "project_type_id"):
        if _column_exists(conn, "projects", col_name):
            op.drop_column("projects", col_name)
            logger.info("  Dropped projects.%s", col_name)

    # ------------------------------------------------------------------
    # 1-reverse: Drop project_types table
    # ------------------------------------------------------------------
    if _index_exists(conn, "idx_project_type_tenant"):
        op.drop_index("idx_project_type_tenant", table_name="project_types")
        logger.info("  Dropped index idx_project_type_tenant")

    if _table_exists(conn, "project_types"):
        op.drop_table("project_types")
        logger.info("  Dropped table project_types")

    logger.info("Downgrade 0440a complete.")
