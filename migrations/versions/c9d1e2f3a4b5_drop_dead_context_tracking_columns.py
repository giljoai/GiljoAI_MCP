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

All operations are IDEMPOTENT - safe on fresh installs where baseline already omits these.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = 'c9d1e2f3a4b5'
down_revision: Union[str, Sequence[str], None] = 'a7f3b2c4d890'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(conn, table_name: str, column_name: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :table AND column_name = :col"
    ), {"table": table_name, "col": column_name})
    return result.fetchone() is not None


def _constraint_exists(conn, constraint_name: str) -> bool:
    result = conn.execute(text(
        "SELECT 1 FROM pg_constraint WHERE conname = :name"
    ), {"name": constraint_name})
    return result.fetchone() is not None


def upgrade() -> None:
    conn = op.get_bind()

    # Drop CHECK constraint first (skip if baseline already omits it)
    if _constraint_exists(conn, 'ck_agent_execution_context_usage'):
        op.drop_constraint('ck_agent_execution_context_usage', 'agent_executions', type_='check')

    # Drop columns from agent_executions (skip if baseline already omits them)
    if _column_exists(conn, 'agent_executions', 'context_used'):
        op.drop_column('agent_executions', 'context_used')
    if _column_exists(conn, 'agent_executions', 'context_budget'):
        op.drop_column('agent_executions', 'context_budget')

    # Drop column from projects (skip if baseline already omits it)
    if _column_exists(conn, 'projects', 'context_used'):
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
