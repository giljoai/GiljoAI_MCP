"""Add user_id to mcp_sessions for audit trail (Handover 0424 Phase 0)

Revision ID: 0424a_user_audit
Revises: aeef30e94762
Create Date: 2026-01-20

Security enhancement: Store user_id in MCP sessions for audit logging.
Enables forensic analysis of tenant_key override events.
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision = '0424a_user_audit'
down_revision = 'aeef30e94762'
branch_labels = None
depends_on = None


def upgrade():
    """Add user_id column with FK to users table."""
    # Add user_id column (nullable to support existing sessions)
    op.add_column(
        'mcp_sessions',
        sa.Column('user_id', sa.String(36), nullable=True)
    )

    # Add foreign key constraint
    op.create_foreign_key(
        'fk_mcp_sessions_user_id',
        'mcp_sessions',
        'users',
        ['user_id'],
        ['id'],
        ondelete='CASCADE'
    )

    # Add index for audit queries
    op.create_index(
        'idx_mcp_session_user',
        'mcp_sessions',
        ['user_id'],
        postgresql_where=sa.text('user_id IS NOT NULL')
    )

    # Backfill user_id from api_key relationship
    op.execute("""
        UPDATE mcp_sessions ms
        SET user_id = ak.user_id
        FROM api_keys ak
        WHERE ms.api_key_id = ak.id
          AND ms.user_id IS NULL
    """)


def downgrade():
    """Remove user_id column."""
    op.drop_index('idx_mcp_session_user', 'mcp_sessions')
    op.drop_constraint('fk_mcp_sessions_user_id', 'mcp_sessions', type_='foreignkey')
    op.drop_column('mcp_sessions', 'user_id')
