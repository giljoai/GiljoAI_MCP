"""single_active_project_per_product

Handover 0050b: Enforce single active project per product architecture.

Revision ID: 20251027_single_proj
Revises: 20251027_single_active
Create Date: 2025-10-27 18:00:00.000000
"""

from collections.abc import Sequence
from typing import Union

from alembic import op
from sqlalchemy import text


revision: str = "20251027_single_proj"
down_revision: Union[str, None] = "20251027_single_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add single active project enforcement"""
    connection = op.get_bind()

    print("\n[Handover 0050b Migration] Starting single active project per product enforcement...\n")

    # Find conflicts
    conflicts_query = text("""
        SELECT product_id, COUNT(*) as active_count
        FROM projects
        WHERE status = 'active' AND product_id IS NOT NULL
        GROUP BY product_id
        HAVING COUNT(*) > 1
    """)

    conflicts = connection.execute(conflicts_query).fetchall()

    if conflicts:
        print(f"[Handover 0050b Migration] Found {len(conflicts)} products with multiple active projects")

        for product_id, active_count in conflicts:
            print(f"[Handover 0050b Migration] Product {product_id}: {active_count} active projects - resolving...")

            # Get active projects ordered by updated_at DESC
            projects_query = text("""
                SELECT id, name, updated_at
                FROM projects
                WHERE product_id = :product_id AND status = 'active'
                ORDER BY updated_at DESC NULLS LAST
            """)

            projects = connection.execute(projects_query, {"product_id": product_id}).fetchall()

            if projects:
                keep_project = projects[0]
                print(f"[Handover 0050b Migration]   Keeping: {keep_project.name} (most recent)")

                # Deactivate others
                for project in projects[1:]:
                    deactivate_query = text("""
                        UPDATE projects
                        SET status = 'paused'
                        WHERE id = :project_id
                    """)
                    connection.execute(deactivate_query, {"project_id": project.id})
                    print(f"[Handover 0050b Migration]   Paused: {project.name}")
    else:
        print("[Handover 0050b Migration] No conflicts found")

    print("\n[Handover 0050b Migration] Adding partial unique index...")

    # Create index
    op.create_index(
        "idx_project_single_active_per_product",
        "projects",
        ["product_id"],
        unique=True,
        postgresql_where=text("status = 'active'"),
    )

    print("[Handover 0050b Migration] Migration complete - single active project enforcement enabled\n")


def downgrade() -> None:
    """Remove constraint"""
    print("\n[Handover 0050b Migration] Removing constraint...")
    op.drop_index(
        "idx_project_single_active_per_product", table_name="projects", postgresql_where=text("status = 'active'")
    )
    print("[Handover 0050b Migration] Downgrade complete\n")
