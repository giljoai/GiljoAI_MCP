"""Replace taxonomy unique constraint with partial index excluding soft-deleted rows

Revision ID: 0845a_taxonomy
Revises: 0844a_conventions
Create Date: 2026-03-29

The uq_project_taxonomy constraint blocked re-use of taxonomy combinations
(type + series_number + subseries) after soft-deleting a project. Replace
with a partial unique index that only enforces uniqueness on active rows
(deleted_at IS NULL).
"""

import sqlalchemy as sa
from alembic import op


# revision identifiers
revision = "0845a_taxonomy"
down_revision = "0844a_conventions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Idempotency: check if the old constraint still exists
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = 'uq_project_taxonomy' AND table_name = 'projects'"
        )
    )
    if result.fetchone():
        op.drop_constraint("uq_project_taxonomy", "projects", type_="unique")

    # Idempotency: check if the partial index already exists
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes "
            "WHERE indexname = 'uq_project_taxonomy_active'"
        )
    )
    if not result.fetchone():
        op.execute(
            sa.text(
                "CREATE UNIQUE INDEX uq_project_taxonomy_active "
                "ON projects (tenant_key, project_type_id, series_number, subseries) "
                "WHERE deleted_at IS NULL"
            )
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop partial index
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM pg_indexes "
            "WHERE indexname = 'uq_project_taxonomy_active'"
        )
    )
    if result.fetchone():
        op.drop_index("uq_project_taxonomy_active", table_name="projects")

    # Restore original constraint (may fail if deleted duplicates exist)
    result = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE constraint_name = 'uq_project_taxonomy' AND table_name = 'projects'"
        )
    )
    if not result.fetchone():
        op.create_unique_constraint(
            "uq_project_taxonomy",
            "projects",
            ["tenant_key", "project_type_id", "series_number", "subseries"],
        )
