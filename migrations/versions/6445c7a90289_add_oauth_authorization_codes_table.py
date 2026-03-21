"""add_oauth_authorization_codes_table

Revision ID: 6445c7a90289
Revises: g7h8i9j0k123
Create Date: 2026-03-21 01:03:33.034913

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '6445c7a90289'
down_revision: Union[str, Sequence[str], None] = 'g7h8i9j0k123'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create oauth_authorization_codes table."""
    op.create_table('oauth_authorization_codes',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('code', sa.String(length=128), nullable=False),
        sa.Column('client_id', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.String(length=36), nullable=False),
        sa.Column('tenant_key', sa.String(length=64), nullable=False),
        sa.Column('redirect_uri', sa.String(length=2048), nullable=False),
        sa.Column('code_challenge', sa.String(length=128), nullable=False),
        sa.Column('code_challenge_method', sa.String(length=10), nullable=True),
        sa.Column('scope', sa.String(length=512), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('used', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_oauth_code_expires', 'oauth_authorization_codes', ['expires_at'], unique=False)
    op.create_index('idx_oauth_code_lookup', 'oauth_authorization_codes', ['code', 'tenant_key'], unique=False)
    op.create_index('idx_oauth_code_tenant', 'oauth_authorization_codes', ['tenant_key'], unique=False)
    op.create_index('idx_oauth_code_user', 'oauth_authorization_codes', ['user_id'], unique=False)
    op.create_index(op.f('ix_oauth_authorization_codes_code'), 'oauth_authorization_codes', ['code'], unique=True)
    op.create_index(op.f('ix_oauth_authorization_codes_tenant_key'), 'oauth_authorization_codes', ['tenant_key'], unique=False)


def downgrade() -> None:
    """Drop oauth_authorization_codes table."""
    op.drop_index(op.f('ix_oauth_authorization_codes_tenant_key'), table_name='oauth_authorization_codes')
    op.drop_index(op.f('ix_oauth_authorization_codes_code'), table_name='oauth_authorization_codes')
    op.drop_index('idx_oauth_code_user', table_name='oauth_authorization_codes')
    op.drop_index('idx_oauth_code_tenant', table_name='oauth_authorization_codes')
    op.drop_index('idx_oauth_code_lookup', table_name='oauth_authorization_codes')
    op.drop_index('idx_oauth_code_expires', table_name='oauth_authorization_codes')
    op.drop_table('oauth_authorization_codes')
