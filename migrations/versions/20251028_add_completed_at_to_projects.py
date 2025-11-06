"""add_completed_at_to_projects

Projects View v2.0: Enhanced status management with completion tracking.

This migration adds completion timestamp tracking to projects:
1. Adds completed_at TIMESTAMP column to projects table
2. Tracks when projects are marked as completed or cancelled
3. Enables enhanced status reporting and project lifecycle analytics

Revision ID: 20251028_completed_at
Revises: 20251027_project_soft_delete
Create Date: 2025-10-28 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "20251028_completed_at"
down_revision: Union[str, Sequence[str], None] = "20251027_project_soft_delete"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add completion timestamp tracking to projects table.

    Steps:
    1. Add completed_at column (nullable TIMESTAMP)

    Note: No index needed - column is only queried with tenant_key filtering,
    and existing tenant index provides sufficient performance.
    """

    print("\n[Projects View v2.0 Migration] Adding completion tracking to projects table...")

    # STEP 1: Add completed_at column
    # ================================
    print("  - Adding completed_at column to projects table")

    # Check if column already exists (idempotent migration)
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='projects' AND column_name='completed_at'"
        )
    )

    if result.fetchone():
        print("  - Column 'completed_at' already exists, skipping...")
    else:
        op.add_column(
            "projects",
            sa.Column(
                "completed_at",
                sa.TIMESTAMP(timezone=True),
                nullable=True,
                comment="Timestamp when project was marked as completed or cancelled",
            ),
        )
        print("  - Column 'completed_at' added successfully")

    print("[Projects View v2.0 Migration] Completion tracking added successfully\n")
    print("Projects can now track completion timestamps for status management\n")


def downgrade() -> None:
    """
    Remove completion timestamp tracking from projects table.

    WARNING: This will permanently remove the completed_at column.
    Historical completion timestamps will be lost.
    """

    print("\n[Projects View v2.0 Migration Rollback] Removing completion tracking...")

    # Check if column exists before dropping (idempotent migration)
    conn = op.get_bind()
    result = conn.execute(
        text(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name='projects' AND column_name='completed_at'"
        )
    )

    if result.fetchone():
        print("  - Dropping completed_at column")
        op.drop_column("projects", "completed_at")
        print("  - Column 'completed_at' dropped successfully")
    else:
        print("  - Column 'completed_at' does not exist, skipping...")

    print("[Projects View v2.0 Migration Rollback] Completion tracking removed\n")
    print("WARNING: Historical completion timestamps have been lost.\n")
