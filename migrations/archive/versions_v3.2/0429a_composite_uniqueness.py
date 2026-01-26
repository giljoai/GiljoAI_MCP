"""0429a: Add composite uniqueness for agent_id + instance_number

Handover 0429: Allow same agent_id across multiple instances for succession.

Revision ID: 0429a_composite
Revises: 0427a_remove_git
Create Date: 2026-01-21 22:13:00

Changes:
1. Add new 'id' column as primary key (UUID)
2. Remove primary key from 'agent_id' (keep as indexed column)
3. Add unique constraint on (agent_id, instance_number)

CRITICAL: This is a breaking schema change. Backup database before running.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0429a_composite'
down_revision: Union[str, Sequence[str], None] = '0427a_remove_git'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade: Add composite uniqueness constraint."""
    # Step 1: Add new 'id' column with default UUID
    op.add_column(
        'agent_executions',
        sa.Column('id', sa.String(36), nullable=False, server_default=sa.text("gen_random_uuid()::text"))
    )

    # Step 2: Drop old primary key on agent_id
    op.drop_constraint('agent_executions_pkey', 'agent_executions', type_='primary')

    # Step 3: Add new primary key on 'id'
    op.create_primary_key('agent_executions_pkey', 'agent_executions', ['id'])

    # Step 4: Create index on agent_id (no longer primary key)
    op.create_index('idx_agent_executions_agent_id', 'agent_executions', ['agent_id'])

    # Step 5: Add unique constraint on (agent_id, instance_number)
    op.create_unique_constraint('uq_agent_instance', 'agent_executions', ['agent_id', 'instance_number'])


def downgrade() -> None:
    """Downgrade: Revert to agent_id as primary key."""
    # Remove unique constraint
    op.drop_constraint('uq_agent_instance', 'agent_executions', type_='unique')

    # Remove agent_id index
    op.drop_index('idx_agent_executions_agent_id', table_name='agent_executions')

    # Drop current primary key on id
    op.drop_constraint('agent_executions_pkey', 'agent_executions', type_='primary')

    # Restore primary key on agent_id
    op.create_primary_key('agent_executions_pkey', 'agent_executions', ['agent_id'])

    # Drop id column
    op.drop_column('agent_executions', 'id')
