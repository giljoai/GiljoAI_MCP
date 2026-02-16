"""0492: API Key Security Hardening - expires_at + IP logging

Revision ID: a7f3b2c4d890
Revises: b8d2f3a4e567
Create Date: 2026-02-12

Handover 0492: API Key Security Hardening

Changes:
1. Add expires_at column to api_keys table (nullable for backward compat)
2. Backfill existing keys with 90-day expiry from creation date
3. Create api_key_ip_log table for IP address tracking
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = 'a7f3b2c4d890'
down_revision = 'b8d2f3a4e567'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add expires_at to api_keys
    op.add_column('api_keys', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))

    # Backfill existing keys: expires_at = created_at + 90 days
    op.execute(
        "UPDATE api_keys SET expires_at = created_at + INTERVAL '90 days' WHERE expires_at IS NULL"
    )

    # Create api_key_ip_log table
    op.create_table('api_key_ip_log',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('api_key_id', sa.String(length=36), nullable=False),
        sa.Column('ip_address', sa.String(length=45), nullable=False),
        sa.Column('first_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('last_seen_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('request_count', sa.Integer(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['api_key_id'], ['api_keys.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('api_key_id', 'ip_address', name='uq_api_key_ip')
    )
    op.create_index('idx_api_key_ip_log_key_id', 'api_key_ip_log', ['api_key_id'], unique=False)
    op.create_index('idx_api_key_ip_log_last_seen', 'api_key_ip_log', ['last_seen_at'], unique=False)


def downgrade() -> None:
    op.drop_index('idx_api_key_ip_log_last_seen', table_name='api_key_ip_log')
    op.drop_index('idx_api_key_ip_log_key_id', table_name='api_key_ip_log')
    op.drop_table('api_key_ip_log')
    op.drop_column('api_keys', 'expires_at')
