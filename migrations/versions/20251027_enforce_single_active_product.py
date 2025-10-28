"""enforce_single_active_product

Handover 0050: Enforce single active product per tenant architecture.

This migration implements defense-in-depth single active product enforcement:
1. Resolves any existing multi-active-product conflicts (keeps most recent)
2. Adds partial unique index to prevent multiple active products per tenant
3. Ensures database-level atomicity for product activation

Revision ID: 20251027_single_active
Revises: 20251026_224146
Create Date: 2025-10-27 16:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = '20251027_single_active'
down_revision: Union[str, Sequence[str], None] = '20251026_224146'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add single active product enforcement.

    Steps:
    1. Auto-repair: Resolve existing multi-active-product conflicts
    2. Add partial unique index for enforcement
    """

    # STEP 1: Identify and resolve conflicts
    # ======================================

    connection = op.get_bind()

    # Find tenants with multiple active products
    result = connection.execute(text("""
        SELECT tenant_key, COUNT(*) as active_count
        FROM products
        WHERE is_active = true
        GROUP BY tenant_key
        HAVING COUNT(*) > 1
    """))

    conflicts = result.fetchall()

    if conflicts:
        print(f"\n[Handover 0050 Migration] Found {len(conflicts)} tenants with multiple active products")
        print("Auto-repairing conflicts (keeping most recently updated product)...\n")

    # Resolve each conflict
    for tenant_key, active_count in conflicts:
        # Get all active products for this tenant, ordered by updated_at DESC
        products_result = connection.execute(text("""
            SELECT id, name, updated_at
            FROM products
            WHERE tenant_key = :tenant_key AND is_active = true
            ORDER BY updated_at DESC NULLS LAST, created_at DESC NULLS LAST
        """), {'tenant_key': tenant_key})

        products = products_result.fetchall()

        # Keep first (most recent), deactivate rest
        for i, (product_id, product_name, updated_at) in enumerate(products):
            if i == 0:
                print(f"  ✓ Tenant {tenant_key}: Keeping '{product_name}' active (updated: {updated_at})")
            else:
                print(f"  → Tenant {tenant_key}: Deactivating '{product_name}'")
                connection.execute(text("""
                    UPDATE products
                    SET is_active = false, updated_at = NOW()
                    WHERE id = :product_id
                """), {'product_id': product_id})
                connection.commit()

    if conflicts:
        print(f"\n[Handover 0050 Migration] Resolved {len(conflicts)} conflicts successfully\n")
    else:
        print("\n[Handover 0050 Migration] No conflicts found - all tenants have 0 or 1 active products\n")

    # STEP 2: Add partial unique index
    # =================================

    print("[Handover 0050 Migration] Adding partial unique index for single active product enforcement...")

    # Create partial unique index (PostgreSQL 9.0+)
    # Only indexes rows where is_active = true
    # Uniqueness enforced on (tenant_key) for active products
    op.create_index(
        'idx_product_single_active_per_tenant',
        'products',
        ['tenant_key'],
        unique=True,
        postgresql_where=text('is_active = true')
    )

    print("[Handover 0050 Migration] Migration complete - single active product enforcement enabled\n")


def downgrade() -> None:
    """
    Remove single active product enforcement.

    WARNING: This allows multiple active products per tenant again.
    Any data cleaned up during upgrade cannot be restored.
    """

    print("\n[Handover 0050 Migration Rollback] Removing single active product constraint...")

    # Drop partial unique index
    op.drop_index('idx_product_single_active_per_tenant', table_name='products')

    print("[Handover 0050 Migration Rollback] ✓ Constraint removed - multiple active products now allowed\n")
    print("WARNING: System will now allow multiple active products per tenant.")
    print("Consider running data cleanup if this was unintentional.\n")
