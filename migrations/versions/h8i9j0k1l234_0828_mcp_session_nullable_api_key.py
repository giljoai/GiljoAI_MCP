"""0828_mcp_session_nullable_api_key_id

Make mcp_sessions.api_key_id nullable to support OAuth JWT sessions
that authenticate without an API key.

Revision ID: h8i9j0k1l234
Revises: 6445c7a90289
Create Date: 2026-03-21 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'h8i9j0k1l234'
down_revision: Union[str, Sequence[str], None] = '6445c7a90289'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Make api_key_id nullable on mcp_sessions for OAuth JWT sessions."""
    op.alter_column(
        'mcp_sessions',
        'api_key_id',
        existing_type=sa.String(length=36),
        nullable=True,
    )


def downgrade() -> None:
    """Revert api_key_id to NOT NULL (requires removing JWT sessions first)."""
    op.execute("DELETE FROM mcp_sessions WHERE api_key_id IS NULL")
    op.alter_column(
        'mcp_sessions',
        'api_key_id',
        existing_type=sa.String(length=36),
        nullable=False,
    )
