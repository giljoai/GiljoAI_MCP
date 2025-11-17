"""add_product_memory_column_handover_0135

Revision ID: f4121f77a2d9
Revises: f504ea46e988
Create Date: 2025-11-16 20:33:44.579913

Handover 0135: 360 Memory Management - Database Schema
Adds product_memory JSONB column to products table with GIN index for efficient queries.

This column stores:
- GitHub integration settings (github)
- Project learnings and insights (learnings)
- Product context summaries (context)
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'f4121f77a2d9'
down_revision: Union[str, Sequence[str], None] = 'f504ea46e988'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add product_memory JSONB column with GIN index.

    Changes:
    1. Add product_memory column with default structure
    2. Create GIN index for efficient JSONB path queries
    3. Update existing products with default structure (idempotent)
    """
    # Add product_memory column with default structure
    op.add_column(
        'products',
        sa.Column(
            'product_memory',
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{\"github\": {}, \"learnings\": [], \"context\": {}}'::jsonb"),
            comment='360 Memory: GitHub integration, learnings, context summaries (Handover 0135)'
        )
    )

    # Create GIN index for efficient JSONB path queries
    # GIN index enables fast queries like:
    # - WHERE product_memory->'github'->>'enabled' = 'true'
    # - WHERE product_memory ? 'learnings'
    # - WHERE product_memory @> '{"github": {"enabled": true}}'
    op.create_index(
        'idx_product_memory_gin',
        'products',
        ['product_memory'],
        unique=False,
        postgresql_using='gin'
    )

    # Update existing products to have default structure (idempotent safety)
    # This handles edge cases where server_default might not apply
    op.execute("""
        UPDATE products
        SET product_memory = '{"github": {}, "learnings": [], "context": {}}'::jsonb
        WHERE product_memory IS NULL OR product_memory = '{}'::jsonb
    """)


def downgrade() -> None:
    """
    Remove product_memory column and GIN index.

    WARNING: This will LOSE all product_memory data!
    Other product columns (name, description, config_data, etc.) will be preserved.
    """
    # Drop GIN index first (no dependencies)
    op.drop_index('idx_product_memory_gin', table_name='products')

    # Drop product_memory column (data will be lost)
    op.drop_column('products', 'product_memory')
