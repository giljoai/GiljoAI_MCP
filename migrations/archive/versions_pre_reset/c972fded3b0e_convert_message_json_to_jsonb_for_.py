"""convert_message_json_to_jsonb_for_containment_operators

Revision ID: c972fded3b0e
Revises: 807c85a49438
Create Date: 2025-12-05 01:10:32.155017

CRITICAL BUG FIX:
PostgreSQL JSON type does NOT support the @> containment operator.
This migration converts JSON columns to JSONB for tables where containment
queries are used (receive_messages, list_messages, get_messages).

Affected columns:
- messages.to_agents (used with @> operator in message_service.py lines 481, 483, 595, 597)
- messages.acknowledged_by (array of agent names)
- messages.completed_by (array of agent names)
- messages.meta_data (dictionary of metadata)
- tasks.meta_data (used with .contains() in task.py line 703)

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'c972fded3b0e'
down_revision: Union[str, Sequence[str], None] = '807c85a49438'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Convert JSON columns to JSONB to support PostgreSQL containment operators.

    PostgreSQL can cast JSON to JSONB directly, so this is a safe operation.
    Existing data will be preserved and automatically converted.
    """
    # Convert messages table columns from JSON to JSONB
    op.alter_column('messages', 'to_agents',
                    existing_type=sa.JSON(),
                    type_=postgresql.JSONB(),
                    existing_nullable=True,
                    postgresql_using='to_agents::jsonb')

    op.alter_column('messages', 'acknowledged_by',
                    existing_type=sa.JSON(),
                    type_=postgresql.JSONB(),
                    existing_nullable=True,
                    postgresql_using='acknowledged_by::jsonb')

    op.alter_column('messages', 'completed_by',
                    existing_type=sa.JSON(),
                    type_=postgresql.JSONB(),
                    existing_nullable=True,
                    postgresql_using='completed_by::jsonb')

    op.alter_column('messages', 'meta_data',
                    existing_type=sa.JSON(),
                    type_=postgresql.JSONB(),
                    existing_nullable=True,
                    postgresql_using='meta_data::jsonb')

    # Convert tasks table meta_data column from JSON to JSONB
    op.alter_column('tasks', 'meta_data',
                    existing_type=sa.JSON(),
                    type_=postgresql.JSONB(),
                    existing_nullable=True,
                    postgresql_using='meta_data::jsonb')


def downgrade() -> None:
    """
    Rollback: Convert JSONB columns back to JSON.

    This is a safe operation as JSONB can be cast to JSON.
    Note: JSONB-specific indexes would need to be recreated after downgrade.
    """
    # Convert messages table columns from JSONB back to JSON
    op.alter_column('messages', 'to_agents',
                    existing_type=postgresql.JSONB(),
                    type_=sa.JSON(),
                    existing_nullable=True,
                    postgresql_using='to_agents::json')

    op.alter_column('messages', 'acknowledged_by',
                    existing_type=postgresql.JSONB(),
                    type_=sa.JSON(),
                    existing_nullable=True,
                    postgresql_using='acknowledged_by::json')

    op.alter_column('messages', 'completed_by',
                    existing_type=postgresql.JSONB(),
                    type_=sa.JSON(),
                    existing_nullable=True,
                    postgresql_using='completed_by::json')

    op.alter_column('messages', 'meta_data',
                    existing_type=postgresql.JSONB(),
                    type_=sa.JSON(),
                    existing_nullable=True,
                    postgresql_using='meta_data::json')

    # Convert tasks table meta_data column from JSONB back to JSON
    op.alter_column('tasks', 'meta_data',
                    existing_type=postgresql.JSONB(),
                    type_=sa.JSON(),
                    existing_nullable=True,
                    postgresql_using='meta_data::json')
