"""add_staging_status

Handover 0108: Staging Cancellation & Project Status Management.

This migration adds staging workflow status tracking to projects table:
1. staging_status - VARCHAR(50) column for tracking staging workflow states
2. idx_projects_staging_status - Index for filtering by staging status
3. idx_projects_status_staging_status - Composite index for common query patterns

Staging status values: null, staging, staged, cancelled, launching, active

Revision ID: 20251106_0108
Revises: 20251106_agent_monitoring
Create Date: 2025-11-06 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "20251106_0108"
down_revision: Union[str, Sequence[str], None] = "20251106_agent_monitoring"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add staging workflow status tracking to projects table.

    Steps:
    1. Add staging_status VARCHAR(50) NULL column
    2. Create index on staging_status for filtering
    3. Create composite index on (status, staging_status) for common queries

    All operations are idempotent using information_schema checks.
    """

    print("\n[Handover 0108 Migration] Adding staging workflow status to projects...")

    # Get database connection for idempotency checks
    conn = op.get_bind()

    # STEP 1: Add staging_status column (IDEMPOTENT)
    # ================================================
    print("  - Checking if staging_status column exists...")

    # Check if column already exists
    result = conn.execute(
        text(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'projects'
            AND column_name = 'staging_status'
            """
        )
    )
    column_exists = result.fetchone() is not None

    if not column_exists:
        print("  - Adding staging_status column to projects table...")
        op.add_column(
            "projects",
            sa.Column(
                "staging_status",
                sa.String(50),
                nullable=True,
                comment="Staging workflow status: null, staging, staged, cancelled, launching, active (Handover 0108)"
            )
        )
        print("  ✓ staging_status column added successfully")
    else:
        print("  ⚠ staging_status column already exists, skipping...")

    # STEP 2: Create index on staging_status (IDEMPOTENT)
    # ====================================================
    print("  - Checking if idx_projects_staging_status index exists...")

    # Check if index already exists
    result = conn.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'projects'
            AND indexname = 'idx_projects_staging_status'
            """
        )
    )
    index_exists = result.fetchone() is not None

    if not index_exists:
        print("  - Creating index idx_projects_staging_status...")
        op.create_index(
            "idx_projects_staging_status",
            "projects",
            ["staging_status"],
            unique=False
        )
        print("  ✓ Index idx_projects_staging_status created successfully")
    else:
        print("  ⚠ Index idx_projects_staging_status already exists, skipping...")

    # STEP 3: Create composite index on (status, staging_status) (IDEMPOTENT)
    # ========================================================================
    print("  - Checking if idx_projects_status_staging_status index exists...")

    # Check if composite index already exists
    result = conn.execute(
        text(
            """
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'projects'
            AND indexname = 'idx_projects_status_staging_status'
            """
        )
    )
    composite_index_exists = result.fetchone() is not None

    if not composite_index_exists:
        print("  - Creating composite index idx_projects_status_staging_status...")
        op.create_index(
            "idx_projects_status_staging_status",
            "projects",
            ["status", "staging_status"],
            unique=False
        )
        print("  ✓ Composite index idx_projects_status_staging_status created successfully")
    else:
        print("  ⚠ Composite index idx_projects_status_staging_status already exists, skipping...")

    print("[Handover 0108 Migration] OK Staging workflow status tracking added successfully\n")


def downgrade() -> None:
    """
    Remove staging workflow status tracking from projects table.

    WARNING: This will drop the staging_status column and its indexes.
    All staging workflow status data in this column will be lost.

    Steps:
    1. Drop composite index idx_projects_status_staging_status
    2. Drop index idx_projects_staging_status
    3. Drop staging_status column
    """

    print("\n[Handover 0108 Migration Rollback] Removing staging workflow status from projects...")

    # STEP 1: Drop composite index
    # =============================
    print("  - Dropping composite index idx_projects_status_staging_status...")
    op.drop_index("idx_projects_status_staging_status", table_name="projects")
    print("  ✓ Composite index dropped")

    # STEP 2: Drop staging_status index
    # ==================================
    print("  - Dropping index idx_projects_staging_status...")
    op.drop_index("idx_projects_staging_status", table_name="projects")
    print("  ✓ Index dropped")

    # STEP 3: Drop staging_status column
    # ===================================
    print("  - Dropping staging_status column from projects table...")
    op.drop_column("projects", "staging_status")
    print("  ✓ staging_status column dropped")

    print("[Handover 0108 Migration Rollback] OK Staging workflow status tracking removed\n")
    print("WARNING: All staging workflow status data has been lost.\n")
