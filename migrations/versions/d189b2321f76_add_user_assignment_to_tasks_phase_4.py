"""Add user assignment to tasks (Phase 4)

Revision ID: d189b2321f76
Revises: 8406a7a6dcc5
Create Date: 2025-10-09 00:15:29.487807

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd189b2321f76'
down_revision: Union[str, Sequence[str], None] = '8406a7a6dcc5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - Add user assignment fields to tasks for Phase 4."""
    # Add user assignment columns (nullable for backward compatibility)
    op.add_column('tasks', sa.Column('created_by_user_id', sa.String(length=36), nullable=True))
    op.add_column('tasks', sa.Column('assigned_to_user_id', sa.String(length=36), nullable=True))

    # Create indexes for performance
    op.create_index('idx_task_assigned_to_user', 'tasks', ['assigned_to_user_id'], unique=False)
    op.create_index('idx_task_created_by_user', 'tasks', ['created_by_user_id'], unique=False)
    op.create_index('idx_task_tenant_assigned_user', 'tasks', ['tenant_key', 'assigned_to_user_id'], unique=False)
    op.create_index('idx_task_tenant_created_user', 'tasks', ['tenant_key', 'created_by_user_id'], unique=False)

    # Create foreign key constraints
    op.create_foreign_key('fk_task_assigned_to_user', 'tasks', 'users', ['assigned_to_user_id'], ['id'])
    op.create_foreign_key('fk_task_created_by_user', 'tasks', 'users', ['created_by_user_id'], ['id'])


def downgrade() -> None:
    """Downgrade schema - Remove user assignment fields from tasks."""
    # Drop foreign key constraints
    op.drop_constraint('fk_task_created_by_user', 'tasks', type_='foreignkey')
    op.drop_constraint('fk_task_assigned_to_user', 'tasks', type_='foreignkey')

    # Drop indexes
    op.drop_index('idx_task_tenant_created_user', table_name='tasks')
    op.drop_index('idx_task_tenant_assigned_user', table_name='tasks')
    op.drop_index('idx_task_created_by_user', table_name='tasks')
    op.drop_index('idx_task_assigned_to_user', table_name='tasks')

    # Drop columns
    op.drop_column('tasks', 'assigned_to_user_id')
    op.drop_column('tasks', 'created_by_user_id')
