"""Add message counter columns to agent_executions (Handover 0387e)

Revision ID: 0387e_counters
Revises: 20260111_agent_display_name
Create Date: 2026-01-17

This migration adds three counter columns to the agent_executions table:
- messages_sent_count: Count of outbound messages sent by this agent
- messages_waiting_count: Count of inbound messages waiting to be read
- messages_read_count: Count of inbound messages that have been acknowledged/read

These counter columns replace JSONB array iteration for message counts,
establishing a single source of truth with O(1) read performance.

Part 1 of 5 in the JSONB Messages Normalization series (Phase 4 of 0387).
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '0387e_counters'
down_revision = '20260111_agent_display_name'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add message counter columns and backfill from Message table."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if agent_executions table exists
    tables = inspector.get_table_names()
    if 'agent_executions' not in tables:
        print("agent_executions table not found, skipping migration")
        return

    # Get current columns in agent_executions table
    columns = [col['name'] for col in inspector.get_columns('agent_executions')]

    # Check if columns already exist (migration already run)
    if all(col in columns for col in ['messages_sent_count', 'messages_waiting_count', 'messages_read_count']):
        print("Message counter columns already exist, skipping migration")
        return

    print("Adding message counter columns to agent_executions...")

    # Add counter columns with default values
    if 'messages_sent_count' not in columns:
        op.add_column(
            'agent_executions',
            sa.Column(
                'messages_sent_count',
                sa.Integer(),
                nullable=False,
                server_default='0',
                comment='Count of outbound messages sent by this agent (Handover 0387e)'
            )
        )
        print("  - Added column: messages_sent_count")

    if 'messages_waiting_count' not in columns:
        op.add_column(
            'agent_executions',
            sa.Column(
                'messages_waiting_count',
                sa.Integer(),
                nullable=False,
                server_default='0',
                comment='Count of inbound messages waiting to be read (Handover 0387e)'
            )
        )
        print("  - Added column: messages_waiting_count")

    if 'messages_read_count' not in columns:
        op.add_column(
            'agent_executions',
            sa.Column(
                'messages_read_count',
                sa.Integer(),
                nullable=False,
                server_default='0',
                comment='Count of inbound messages that have been acknowledged/read (Handover 0387e)'
            )
        )
        print("  - Added column: messages_read_count")

    # Check if messages table exists before backfilling
    if 'messages' not in tables:
        print("Messages table not found, skipping backfill (fresh install)")
        print("Migration complete!")
        return

    print("Backfilling message counts from messages table...")

    # Backfill messages_sent_count
    # from_agent is stored in meta_data->>'_from_agent'
    print("  - Backfilling messages_sent_count...")
    op.execute("""
        UPDATE agent_executions ae
        SET messages_sent_count = COALESCE((
            SELECT COUNT(*)
            FROM messages m
            WHERE m.meta_data->>'_from_agent' = ae.agent_id
            AND m.tenant_key = ae.tenant_key
        ), 0)
        WHERE ae.tenant_key IS NOT NULL
    """)

    # Backfill messages_waiting_count
    # to_agents is a JSONB array, use @> operator to check if agent_id is in the array
    print("  - Backfilling messages_waiting_count...")
    op.execute("""
        UPDATE agent_executions ae
        SET messages_waiting_count = COALESCE((
            SELECT COUNT(*)
            FROM messages m
            WHERE m.to_agents @> to_jsonb(ae.agent_id)
            AND m.status = 'pending'
            AND m.tenant_key = ae.tenant_key
        ), 0)
        WHERE ae.tenant_key IS NOT NULL
    """)

    # Backfill messages_read_count
    # acknowledged_by is a JSONB array
    print("  - Backfilling messages_read_count...")
    op.execute("""
        UPDATE agent_executions ae
        SET messages_read_count = COALESCE((
            SELECT COUNT(*)
            FROM messages m
            WHERE m.acknowledged_by @> to_jsonb(ae.agent_id)
            AND m.tenant_key = ae.tenant_key
        ), 0)
        WHERE ae.tenant_key IS NOT NULL
    """)

    print("Migration complete!")


def downgrade() -> None:
    """Remove message counter columns."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if agent_executions table exists
    tables = inspector.get_table_names()
    if 'agent_executions' not in tables:
        print("agent_executions table not found, skipping downgrade")
        return

    # Get current columns
    columns = [col['name'] for col in inspector.get_columns('agent_executions')]

    print("Removing message counter columns from agent_executions...")

    if 'messages_read_count' in columns:
        op.drop_column('agent_executions', 'messages_read_count')
        print("  - Dropped column: messages_read_count")

    if 'messages_waiting_count' in columns:
        op.drop_column('agent_executions', 'messages_waiting_count')
        print("  - Dropped column: messages_waiting_count")

    if 'messages_sent_count' in columns:
        op.drop_column('agent_executions', 'messages_sent_count')
        print("  - Dropped column: messages_sent_count")

    print("Downgrade complete!")
