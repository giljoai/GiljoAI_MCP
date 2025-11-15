"""0128d: Drop deprecated agent_id foreign key columns

Removes 6 deprecated agent_id FK columns from various tables.
These columns referenced the deleted agents table and are no longer used.

Related: Handover 0116 (removed agents table and FKs)
Date: 2025-11-11

Tables affected:
- agent_interactions (parent_agent_id)
- jobs (agent_id)
- git_commits (agent_id)
- optimization_metrics (agent_id)
- messages (from_agent_id)
- template_usage_stats (agent_id)

Revision ID: 46a46cb1310b
Revises: 0128e_vision_fields
Create Date: 2025-11-11 19:57:41.568012

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46a46cb1310b'
down_revision: Union[str, Sequence[str], None] = '0128e_vision_fields'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop deprecated agent_id columns from 6 tables"""

    # 1. agent_interactions table
    op.drop_index('idx_interaction_parent', table_name='agent_interactions', if_exists=True)
    op.drop_column('agent_interactions', 'parent_agent_id')

    # 2. jobs table
    op.drop_index('idx_job_agent', table_name='jobs', if_exists=True)
    op.drop_column('jobs', 'agent_id')

    # 3. git_commits table
    op.drop_column('git_commits', 'agent_id')

    # 4. optimization_metrics table
    op.drop_index('idx_optimization_metric_agent', table_name='optimization_metrics', if_exists=True)
    op.drop_column('optimization_metrics', 'agent_id')

    # 5. messages table
    op.drop_column('messages', 'from_agent_id')

    # 6. template_usage_stats table
    op.drop_column('template_usage_stats', 'agent_id')


def downgrade() -> None:
    """Rollback: Re-add deprecated columns (for safety only)"""

    # 1. agent_interactions table
    op.add_column('agent_interactions',
                  sa.Column('parent_agent_id', sa.String(36), nullable=True))
    op.create_index('idx_interaction_parent', 'agent_interactions', ['parent_agent_id'])

    # 2. jobs table
    op.add_column('jobs',
                  sa.Column('agent_id', sa.String(36), nullable=True))
    op.create_index('idx_job_agent', 'jobs', ['agent_id'])

    # 3. git_commits table
    op.add_column('git_commits',
                  sa.Column('agent_id', sa.String(36), nullable=True))

    # 4. optimization_metrics table
    op.add_column('optimization_metrics',
                  sa.Column('agent_id', sa.String(36), nullable=True))
    op.create_index('idx_optimization_metric_agent', 'optimization_metrics', ['agent_id'])

    # 5. messages table
    op.add_column('messages',
                  sa.Column('from_agent_id', sa.String(36), nullable=True))

    # 6. template_usage_stats table
    op.add_column('template_usage_stats',
                  sa.Column('agent_id', sa.String(36), nullable=True))
