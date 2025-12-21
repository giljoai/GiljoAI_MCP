"""Add template_id to MCPAgentJob for Handover 0244a

Revision ID: 807c85a49438
Revises: 583c4b97e1ae
Create Date: 2025-11-24 08:19:47.300886

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '807c85a49438'
down_revision: Union[str, Sequence[str], None] = '583c4b97e1ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add template_id column to mcp_agent_jobs table
    op.add_column(
        'mcp_agent_jobs',
        sa.Column('template_id', sa.String(length=36), nullable=True, comment='Agent template ID this job was spawned from (Handover 0244a)')
    )

    # Add foreign key constraint to agent_templates
    op.create_foreign_key(
        'fk_mcp_agent_jobs_template_id',
        'mcp_agent_jobs',
        'agent_templates',
        ['template_id'],
        ['id']
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove foreign key constraint
    op.drop_constraint('fk_mcp_agent_jobs_template_id', 'mcp_agent_jobs', type_='foreignkey')

    # Remove template_id column
    op.drop_column('mcp_agent_jobs', 'template_id')
