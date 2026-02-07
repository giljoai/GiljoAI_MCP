"""make_task_product_id_not_null_handover_0433

Revision ID: 2ab3b751cdba
Revises: baseline_v32
Create Date: 2026-02-07 11:42:22.278409

This migration enforces that all tasks must be bound to a product.

Changes:
1. Assign any tasks with product_id IS NULL to first product in tenant
2. Alter Task.product_id column to NOT NULL
3. Add CHECK constraint for UUID format validation

Security: Maintains tenant isolation during migration
Handover: 0433 - Task Product Binding and Tenant Isolation Fix

"""
from typing import Sequence, Union
import logging

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# Set up logging
logger = logging.getLogger("alembic.migration.0433")

# revision identifiers, used by Alembic.
revision: str = '2ab3b751cdba'
down_revision: Union[str, Sequence[str], None] = 'baseline_v32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Make Task.product_id NOT NULL."""

    # Get database connection
    conn = op.get_bind()

    # Step 1: Check for tasks with NULL product_id
    logger.info("Checking for tasks with NULL product_id...")

    result = conn.execute(text(
        "SELECT COUNT(*) FROM tasks WHERE product_id IS NULL"
    ))
    null_count = result.scalar()

    if null_count > 0:
        logger.warning(f"Found {null_count} tasks with NULL product_id - migrating...")

        # Get distinct tenants with NULL product_id tasks
        tenant_result = conn.execute(text(
            "SELECT DISTINCT tenant_key FROM tasks WHERE product_id IS NULL"
        ))
        tenants_with_null = [row[0] for row in tenant_result]

        logger.info(f"Processing {len(tenants_with_null)} tenants...")

        for tenant_key in tenants_with_null:
            # Get first active product for this tenant
            product_result = conn.execute(text(
                """
                SELECT id FROM products
                WHERE tenant_key = :tenant_key
                  AND is_active = true
                ORDER BY created_at ASC
                LIMIT 1
                """
            ), {"tenant_key": tenant_key})

            product_row = product_result.fetchone()

            if product_row:
                product_id = product_row[0]
                logger.info(f"Tenant {tenant_key}: Assigning NULL tasks to product {product_id}")

                # Update NULL product_id tasks for this tenant
                update_result = conn.execute(text(
                    """
                    UPDATE tasks
                    SET product_id = :product_id
                    WHERE tenant_key = :tenant_key
                      AND product_id IS NULL
                    """
                ), {"product_id": product_id, "tenant_key": tenant_key})

                logger.info(f"Tenant {tenant_key}: Updated {update_result.rowcount} tasks")
            else:
                # No products exist for this tenant - delete orphaned tasks
                logger.warning(
                    f"Tenant {tenant_key}: No products found - deleting orphaned tasks"
                )
                delete_result = conn.execute(text(
                    """
                    DELETE FROM tasks
                    WHERE tenant_key = :tenant_key
                      AND product_id IS NULL
                    """
                ), {"tenant_key": tenant_key})

                logger.warning(f"Tenant {tenant_key}: Deleted {delete_result.rowcount} orphaned tasks")
    else:
        logger.info("No tasks with NULL product_id found - proceeding with constraint")

    # Step 2: Verify no NULL values remain
    verification = conn.execute(text(
        "SELECT COUNT(*) FROM tasks WHERE product_id IS NULL"
    ))
    remaining_null = verification.scalar()

    if remaining_null > 0:
        raise ValueError(
            f"Migration failed: {remaining_null} tasks still have NULL product_id after migration"
        )

    logger.info("All tasks have valid product_id - applying NOT NULL constraint...")

    # Step 3: Alter column to NOT NULL
    op.alter_column(
        'tasks',
        'product_id',
        existing_type=sa.String(length=36),
        nullable=False,
        existing_nullable=True
    )

    # Step 4: Add CHECK constraint for UUID format validation
    # UUID v4 format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx
    op.create_check_constraint(
        'ck_task_product_id_uuid_format',
        'tasks',
        "product_id ~ '^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'"
    )

    logger.info("Migration complete: Task.product_id is now NOT NULL with UUID validation")

    # Step 5: Verify foreign key integrity
    fk_check = conn.execute(text(
        """
        SELECT COUNT(*) FROM tasks t
        LEFT JOIN products p ON t.product_id = p.id
        WHERE p.id IS NULL
        """
    ))
    orphaned_fk = fk_check.scalar()

    if orphaned_fk > 0:
        raise ValueError(
            f"Foreign key integrity violation: {orphaned_fk} tasks reference non-existent products"
        )

    logger.info("Foreign key integrity verified - all tasks reference valid products")


def downgrade() -> None:
    """Downgrade schema - Make Task.product_id nullable again."""

    logger.info("Downgrading: Removing NOT NULL constraint from Task.product_id...")

    # Remove CHECK constraint
    op.drop_constraint('ck_task_product_id_uuid_format', 'tasks', type_='check')

    # Alter column back to nullable
    op.alter_column(
        'tasks',
        'product_id',
        existing_type=sa.String(length=36),
        nullable=True,
        existing_nullable=False
    )

    logger.info("Downgrade complete: Task.product_id is now nullable")
