"""add_config_data_to_product

Add config_data JSONB column to products table for rich configuration storage.
This enables storing architecture, tech stack, features, and other metadata
in a queryable format.

Revision ID: 8406a7a6dcc5
Revises: 11b1e4318444
Create Date: 2025-10-08 01:12:26.989577

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '8406a7a6dcc5'
down_revision: Union[str, Sequence[str], None] = '11b1e4318444'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add config_data JSONB column to products table"""

    # Add config_data column
    op.add_column(
        'products',
        sa.Column('config_data', JSONB, nullable=True)
    )

    # Create GIN index for efficient JSONB queries
    op.create_index(
        'idx_product_config_data_gin',
        'products',
        ['config_data'],
        postgresql_using='gin'
    )

    # Initialize with empty object for existing products
    op.execute("""
        UPDATE products
        SET config_data = '{}'::jsonb
        WHERE config_data IS NULL
    """)


def downgrade() -> None:
    """Remove config_data column"""

    # Drop GIN index
    op.drop_index('idx_product_config_data_gin', table_name='products')

    # Drop column
    op.drop_column('products', 'config_data')
