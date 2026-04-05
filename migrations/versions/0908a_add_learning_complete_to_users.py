"""Add learning_complete column to users table

Revision ID: 0908a_learning
Revises: a47a279202a2
Create Date: 2026-04-04

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '0908a_learning'
down_revision: Union[str, Sequence[str], None] = 'a47a279202a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add learning_complete boolean column to users."""
    # Idempotency guard
    conn = op.get_bind()
    result = conn.execute(sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'users' AND column_name = 'learning_complete'"
    ))
    if result.scalar() is None:
        op.add_column('users', sa.Column(
            'learning_complete', sa.Boolean(), nullable=False, server_default='false'
        ))


def downgrade() -> None:
    """Remove learning_complete column from users."""
    op.drop_column('users', 'learning_complete')
