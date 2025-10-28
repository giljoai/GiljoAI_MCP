"""project_soft_delete

Handover 0070: Add soft delete support to projects with 10-day recovery window.

This migration adds soft delete functionality to enable user-friendly deletion
with recovery options:
1. Adds deleted_at TIMESTAMP column to projects table
2. Adds partial index for efficient deleted project queries
3. Enables recovery UI in Settings -> Database tab
4. Auto-purge after 10 days

Revision ID: 20251027_project_soft_delete
Revises: 20251027_single_proj
Create Date: 2025-10-27 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '20251027_project_soft_delete'
down_revision: Union[str, Sequence[str], None] = '20251027_single_proj'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add soft delete support to projects table.

    Steps:
    1. Add deleted_at column (nullable TIMESTAMP)
    2. Add partial index for efficient deleted project queries
    """

    print("\n[Handover 0070 Migration] Adding soft delete support to projects table...")

    # STEP 1: Add deleted_at column
    # =============================
    print("  - Adding deleted_at column to projects table")

    op.add_column('projects',
        sa.Column('deleted_at', sa.TIMESTAMP(timezone=True), nullable=True,
                 comment='Timestamp when project was soft deleted (NULL for active projects)')
    )

    # STEP 2: Add partial index for performance
    # ==========================================
    print("  - Adding partial index for deleted projects")

    # Partial index only on deleted projects (WHERE deleted_at IS NOT NULL)
    # This optimizes queries for deleted projects list and purge operations
    op.create_index(
        'idx_projects_deleted_at',
        'projects',
        ['deleted_at'],
        unique=False,
        postgresql_where=text('deleted_at IS NOT NULL')
    )

    print("[Handover 0070 Migration] Soft delete support added successfully\n")
    print("Projects can now be soft deleted with 10-day recovery window")
    print("Recovery UI available in: Settings -> Database -> Deleted Projects\n")


def downgrade() -> None:
    """
    Remove soft delete support from projects table.

    WARNING: This will permanently remove the deleted_at column.
    Any deleted projects will become visible again as if never deleted.
    """

    print("\n[Handover 0070 Migration Rollback] Removing soft delete support...")

    # Remove index first
    print("  - Dropping partial index")
    op.drop_index('idx_projects_deleted_at', table_name='projects')

    # Remove column
    print("  - Dropping deleted_at column")
    op.drop_column('projects', 'deleted_at')

    print("[Handover 0070 Migration Rollback] Soft delete support removed\n")
    print("WARNING: All previously deleted projects are now visible again.\n")
