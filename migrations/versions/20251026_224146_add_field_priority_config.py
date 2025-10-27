"""add_field_priority_config

Add field_priority_config JSONB column to users table for user-customizable
field priority configuration. This enables users to override system defaults
for field importance in agent mission generation.

Revision ID: 20251026_224146
Revises: add_alias_to_projects
Create Date: 2025-10-26 22:41:46.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = '20251026_224146'
down_revision: Union[str, Sequence[str], None] = 'add_alias_to_projects'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add field_priority_config JSONB column to users table"""

    # Add field_priority_config column
    op.add_column(
        'users',
        sa.Column(
            'field_priority_config',
            JSONB,
            nullable=True,
            comment='User-customizable field priority for agent mission generation'
        )
    )

    # Create GIN index for efficient JSONB queries
    op.create_index(
        'idx_user_field_priority_config_gin',
        'users',
        ['field_priority_config'],
        postgresql_using='gin'
    )


def downgrade() -> None:
    """Remove field_priority_config column"""

    # Drop GIN index
    op.drop_index('idx_user_field_priority_config_gin', table_name='users')

    # Drop column
    op.drop_column('users', 'field_priority_config')
