"""add_cli_tool_and_background_color_to_agent_templates

Revision ID: 6adac1467121
Revises: 20251104_0102
Create Date: 2025-11-04 23:44:06.621348

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6adac1467121'
down_revision: Union[str, Sequence[str], None] = '20251104_0102'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new columns
    op.add_column('agent_templates', sa.Column('cli_tool', sa.String(20), nullable=True))
    op.add_column('agent_templates', sa.Column('background_color', sa.String(7), nullable=True))

    # Set defaults for existing rows
    op.execute("UPDATE agent_templates SET cli_tool = 'claude' WHERE cli_tool IS NULL")

    # Backfill background_color based on role
    color_map = {
        'orchestrator': '#D4A574',
        'analyzer': '#E74C3C',
        'designer': '#9B59B6',
        'frontend': '#3498DB',
        'backend': '#2ECC71',
        'implementer': '#3498DB',
        'tester': '#FFC300',
        'reviewer': '#9B59B6',
        'documenter': '#27AE60',
    }
    for role, color in color_map.items():
        op.execute(f"UPDATE agent_templates SET background_color = '{color}' WHERE role = '{role}'")

    # Set default gray for unknown roles
    op.execute("UPDATE agent_templates SET background_color = '#90A4AE' WHERE background_color IS NULL")

    # Add constraint
    op.create_check_constraint(
        'check_cli_tool',
        'agent_templates',
        "cli_tool IN ('claude', 'codex', 'gemini', 'generic')"
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('check_cli_tool', 'agent_templates', type_='check')
    op.drop_column('agent_templates', 'background_color')
    op.drop_column('agent_templates', 'cli_tool')
