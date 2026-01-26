"""Remove git_confirmed from projects (superseded by integration icons)

Revision ID: 0427a_remove_git
Revises: 0424a_user_audit
Create Date: 2026-01-20

Handover 0427: Replace per-project git_confirmed checkbox with system-level
integration status icons. The git_confirmed field was a user assertion only
(not verified) and is superseded by the GitHub integration toggle in settings.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0427a_remove_git'
down_revision = '0424a_user_audit'
branch_labels = None
depends_on = None


def upgrade():
    """Remove git_confirmed column from projects table."""
    op.drop_column('projects', 'git_confirmed')


def downgrade():
    """Restore git_confirmed column (for rollback only)."""
    op.add_column(
        'projects',
        sa.Column(
            'git_confirmed',
            sa.Boolean(),
            nullable=False,
            server_default=sa.text('false'),
            comment='User assertion that project directory is under version control (reminder only, not verified)'
        )
    )
