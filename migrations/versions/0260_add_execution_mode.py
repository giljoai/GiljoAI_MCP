"""Add execution_mode column to projects table (Handover 0260)

Revision ID: 0260_execution_mode
Revises: (depends on latest migration)
Create Date: 2025-12-07

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers
revision = '0260_execution_mode'
down_revision = 'c972fded3b0e'  # Branch from same parent as d5a6385e1ff2
branch_labels = None
depends_on = None


def upgrade():
    """Add execution_mode column to projects table.

    Stores per-project execution mode preference:
    - 'multi_terminal': Manual multi-terminal workflow (default)
    - 'claude_code_cli': Single terminal with Claude Code Task tool
    """
    op.add_column(
        'projects',
        sa.Column(
            'execution_mode',
            sa.String(20),
            nullable=False,
            server_default='multi_terminal',
            comment="Execution mode: 'multi_terminal' (manual) or 'claude_code_cli' (single terminal with Task tool)"
        )
    )


def downgrade():
    """Remove execution_mode column from projects table."""
    op.drop_column('projects', 'execution_mode')
