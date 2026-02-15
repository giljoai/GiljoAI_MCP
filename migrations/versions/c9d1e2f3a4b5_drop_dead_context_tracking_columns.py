"""Remove dead context tracking columns

Revision ID: c9d1e2f3a4b5
Revises: a7f3b2c4d890
Create Date: 2026-02-13

Drop unused context_used/context_budget columns from agent_executions and
context_used from projects. These columns are no longer populated or read
by any code path since the on-demand context fetch architecture (v3.0).

Changes:
1. Drop CHECK constraint ck_agent_execution_context_usage from agent_executions
2. Drop context_used and context_budget columns from agent_executions
3. Drop context_used column from projects
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c9d1e2f3a4b5'
down_revision: Union[str, Sequence[str], None] = 'a7f3b2c4d890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop CHECK constraint first (must be before column drop)
    op.drop_constraint('ck_agent_execution_context_usage', 'agent_executions', type_='check')

    # Drop columns from agent_executions
    op.drop_column('agent_executions', 'context_used')
    op.drop_column('agent_executions', 'context_budget')

    # Drop column from projects
    op.drop_column('projects', 'context_used')


def downgrade() -> None:
    # Restore columns on projects
    op.add_column('projects', sa.Column('context_used', sa.Integer(), nullable=True))

    # Restore columns on agent_executions
    op.add_column('agent_executions', sa.Column(
        'context_budget', sa.Integer(), nullable=False, server_default='150000',
    ))
    op.add_column('agent_executions', sa.Column(
        'context_used', sa.Integer(), nullable=False, server_default='0',
    ))

    # Restore CHECK constraint
    op.create_check_constraint(
        'ck_agent_execution_context_usage',
        'agent_executions',
        'context_used >= 0 AND context_used <= context_budget',
    )
