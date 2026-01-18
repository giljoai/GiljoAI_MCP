"""Mark messages column as deprecated (Handover 0387i)

Revision ID: 0387i_deprecate
Revises: 0387e_counters
Create Date: 2026-01-18

This migration adds a deprecation comment to the messages JSONB column,
marking it as deprecated and scheduled for removal in v4.0.

The column is NOT removed yet to:
1. Allow rollback if issues are discovered
2. Preserve historical message data
3. Enable re-enabling JSONB writes if needed

Part 5 of 5 in the JSONB Messages Normalization series (Phase 4 of 0387).
"""

from alembic import op
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '0387i_deprecate'
down_revision = '0387e_counters'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add deprecation comment to messages column."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if agent_executions table exists
    tables = inspector.get_table_names()
    if 'agent_executions' not in tables:
        print("agent_executions table not found, skipping migration")
        return

    # Check if messages column exists
    columns = [col['name'] for col in inspector.get_columns('agent_executions')]
    if 'messages' not in columns:
        print("messages column not found, skipping migration")
        return

    print("Adding deprecation comment to messages column...")

    # Add deprecation comment to column
    op.execute("""
        COMMENT ON COLUMN agent_executions.messages IS
        'DEPRECATED (0387i): Use counter columns (messages_sent_count, messages_waiting_count, messages_read_count) instead. Scheduled for removal in v4.0.'
    """)

    print("Migration complete - messages column marked as deprecated!")


def downgrade() -> None:
    """Remove deprecation comment from messages column."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if agent_executions table exists
    tables = inspector.get_table_names()
    if 'agent_executions' not in tables:
        print("agent_executions table not found, skipping downgrade")
        return

    # Check if messages column exists
    columns = [col['name'] for col in inspector.get_columns('agent_executions')]
    if 'messages' not in columns:
        print("messages column not found, skipping downgrade")
        return

    print("Removing deprecation comment from messages column...")

    # Restore original comment
    op.execute("""
        COMMENT ON COLUMN agent_executions.messages IS
        'Array of message objects for agent communication'
    """)

    print("Downgrade complete!")
