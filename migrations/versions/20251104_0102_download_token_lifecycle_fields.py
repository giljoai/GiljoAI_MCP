"""Add staging lifecycle and metrics to download_tokens (Handover 0102)

Revision ID: 20251104_0102
Revises: 631adb011a79
Create Date: 2025-11-04

This migration augments the download_tokens table with production-grade
staging lifecycle tracking and download metrics to support the single-token
architecture (token-first flow).

Adds columns:
 - staging_status (pending|ready|failed)
 - staging_error (text)
 - download_count (int)
 - last_downloaded_at (timestamptz)

Also adds a CHECK constraint for staging_status and an index to optimize
cleanup queries by (staging_status, expires_at).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '20251104_0102'
down_revision: Union[str, Sequence[str], None] = '631adb011a79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Add new lifecycle and metrics columns
    op.add_column(
        'download_tokens',
        sa.Column('staging_status', sa.String(length=20), nullable=False, server_default='pending',
                  comment='Staging lifecycle status: pending|ready|failed')
    )
    op.add_column(
        'download_tokens',
        sa.Column('staging_error', sa.Text(), nullable=True, comment='Staging error details when status=failed')
    )
    op.add_column(
        'download_tokens',
        sa.Column('download_count', sa.Integer(), nullable=False, server_default='0',
                  comment='Number of successful downloads for this token')
    )
    op.add_column(
        'download_tokens',
        sa.Column('last_downloaded_at', sa.DateTime(timezone=True), nullable=True,
                  comment='Timestamp of most recent successful download')
    )

    # Apply CHECK constraint for staging_status values
    op.create_check_constraint(
        'ck_download_token_staging_status',
        'download_tokens',
        "staging_status IN ('pending', 'ready', 'failed')"
    )

    # Create compound index for cleanup queries
    op.create_index(
        'idx_download_tokens_status',
        'download_tokens',
        ['staging_status', 'expires_at'],
        unique=False
    )

    # Drop server_default after backfilling defaults
    op.alter_column('download_tokens', 'staging_status', server_default=None)
    op.alter_column('download_tokens', 'download_count', server_default=None)


def downgrade() -> None:
    """Downgrade schema."""
    # Drop index and constraint
    op.drop_index('idx_download_tokens_status', table_name='download_tokens')
    op.drop_constraint('ck_download_token_staging_status', 'download_tokens', type_='check')

    # Drop added columns
    op.drop_column('download_tokens', 'last_downloaded_at')
    op.drop_column('download_tokens', 'download_count')
    op.drop_column('download_tokens', 'staging_error')
    op.drop_column('download_tokens', 'staging_status')

