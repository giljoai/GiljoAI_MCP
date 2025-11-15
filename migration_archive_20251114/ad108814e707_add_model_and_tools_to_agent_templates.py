"""add_model_and_tools_to_agent_templates

Revision ID: ad108814e707
Revises: 6adac1467121
Create Date: 2025-11-05

FIX: Missing model and tools columns in agent_templates table.
These columns are required by the SQLAlchemy model but were never migrated.
"""
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'ad108814e707'
down_revision: Union[str, Sequence[str], None] = '6adac1467121'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add model and tools columns to agent_templates."""
    # Add model column (nullable - no default, user can set it)
    op.add_column('agent_templates', sa.Column('model', sa.String(20), nullable=True))

    # Add tools column (nullable - null means inherit all tools)
    op.add_column('agent_templates', sa.Column('tools', sa.String(50), nullable=True))


def downgrade() -> None:
    """Remove model and tools columns from agent_templates."""
    op.drop_column('agent_templates', 'tools')
    op.drop_column('agent_templates', 'model')
