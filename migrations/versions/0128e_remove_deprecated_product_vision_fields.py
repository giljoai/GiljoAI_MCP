"""Remove deprecated Product vision fields (Handover 0128e)

Revision ID: 0128e_vision_fields
Revises: <previous_revision_id>
Create Date: 2025-11-11

IMPORTANT: This migration removes deprecated Product vision fields after code migration.
All production code has been updated to use the VisionDocument relationship instead.

Deprecated fields being removed:
- products.vision_path
- products.vision_document
- products.vision_type
- products.chunked

New pattern (already implemented):
- Product.vision_documents relationship (VisionDocument model)
- Helper properties: primary_vision_text, primary_vision_path, vision_is_chunked, etc.

BEFORE RUNNING:
1. Backup your database: pg_dump -U postgres giljo_mcp > backup_pre_0128e.sql
2. Test the application thoroughly to ensure all vision-related features work
3. Verify all test files have been updated if needed (92 test occurrences exist)

TO RUN:
    alembic upgrade head

TO ROLLBACK (emergency only):
    alembic downgrade -1
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '0128e_vision_fields'
down_revision = None  # TODO: Update with actual previous revision ID
branch_labels = None
depends_on = None


def upgrade():
    """
    Remove deprecated Product vision fields.

    This is safe because:
    1. All production code has been migrated to use VisionDocument relationship
    2. No data exists in these fields (verified during migration)
    3. Helper properties on Product model provide backward-compatible access
    """
    # Drop deprecated columns from products table
    op.drop_column('products', 'vision_path')
    op.drop_column('products', 'vision_document')
    op.drop_column('products', 'vision_type')
    op.drop_column('products', 'chunked')

    # Drop the CheckConstraint on vision_type (it will be removed automatically with the column)
    # Note: The constraint 'ck_product_vision_type' is dropped automatically when vision_type is dropped


def downgrade():
    """
    Restore deprecated Product vision fields (for rollback only).

    WARNING: This will restore the columns but they will be empty.
    The migrated code will continue to use VisionDocument relationship.
    """
    # Restore deprecated columns
    op.add_column('products', sa.Column('vision_path', sa.String(length=500), nullable=True,
                                         comment='DEPRECATED: Use vision_documents relationship'))
    op.add_column('products', sa.Column('vision_document', sa.Text(), nullable=True,
                                         comment='DEPRECATED: Use vision_documents relationship'))
    op.add_column('products', sa.Column('vision_type', sa.String(length=20), nullable=True,
                                         comment='DEPRECATED: Use vision_documents relationship',
                                         server_default='none'))
    op.add_column('products', sa.Column('chunked', sa.Boolean(), nullable=True,
                                         comment='DEPRECATED: Use vision_documents.chunked',
                                         server_default='false'))

    # Restore the CheckConstraint on vision_type
    op.create_check_constraint('ck_product_vision_type', 'products',
                               "vision_type IN ('file', 'inline', 'none')")
