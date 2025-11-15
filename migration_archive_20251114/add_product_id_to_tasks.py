"""Add product_id to tasks table for product isolation

Revision ID: add_product_id_to_tasks
Revises: add_template_management_tables
Create Date: 2025-09-15

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "add_product_id_to_tasks"
down_revision = "45abb2fcc00d"  # Skip problematic migrations
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add product_id column to tasks table and create index"""
    # Add product_id column to tasks table
    op.add_column("tasks", sa.Column("product_id", sa.String(36), nullable=True))

    # Create index for product_id
    op.create_index("idx_task_product", "tasks", ["product_id"])

    # Optional: Set a default product_id for existing tasks (if needed)
    # You can uncomment and modify this if you want to set a default value
    # op.execute("UPDATE tasks SET product_id = 'default-product-id' WHERE product_id IS NULL")


def downgrade() -> None:
    """Remove product_id column and index from tasks table"""
    # Drop the index first
    op.drop_index("idx_task_product", table_name="tasks")

    # Drop the column
    op.drop_column("tasks", "product_id")
