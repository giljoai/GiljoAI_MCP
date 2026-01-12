"""Rename agent_type to agent_display_name in agent_executions table

Revision ID: 20260111_agent_display_name
Revises: 20260105_job_id_fix
Create Date: 2026-01-11

This migration renames the agent_type column to agent_display_name
in the agent_executions table for existing databases.

Semantic clarity (from handover 0414):
- agent_name = Internal code identifier ("database-expert")
- agent_display_name = Human-friendly label ("Database Expert")
- agent_type was deprecated terminology, replaced by agent_display_name

This migration is idempotent - it safely handles both:
1. Existing databases with agent_type (renames to agent_display_name)
2. Fresh installs from updated baseline (agent_display_name already exists, skips rename)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260111_agent_display_name'
down_revision = '20260105_job_id_fix'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename agent_type to agent_display_name in agent_executions table."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if agent_executions table exists
    tables = inspector.get_table_names()
    if 'agent_executions' not in tables:
        # Table doesn't exist yet - fresh install from baseline
        print("agent_executions table not found, skipping migration")
        return

    # Get current columns in agent_executions table
    columns = [col['name'] for col in inspector.get_columns('agent_executions')]

    # Case 1: Column already renamed (fresh install or migration already run)
    if 'agent_display_name' in columns and 'agent_type' not in columns:
        print("Column already renamed to agent_display_name, skipping migration")
        return

    # Case 2: Old column name exists (existing database)
    if 'agent_type' in columns:
        print("Renaming agent_type to agent_display_name...")

        # No indexes specifically on agent_type column to drop
        # (verified via \d agent_executions - no dedicated agent_type indexes)

        # Rename the column
        op.alter_column('agent_executions', 'agent_type', new_column_name='agent_display_name')
        print("  - Renamed column: agent_type -> agent_display_name")

        print("Migration complete!")

    else:
        print("WARNING: Neither agent_display_name nor agent_type found in agent_executions table")
        print(f"Available columns: {columns}")


def downgrade() -> None:
    """Revert agent_display_name back to agent_type."""
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

    if 'agent_display_name' in columns:
        print("Reverting agent_display_name to agent_type...")

        # Rename column back
        op.alter_column('agent_executions', 'agent_display_name', new_column_name='agent_type')
        print("  - Renamed column: agent_display_name -> agent_type")

        print("Downgrade complete!")

    else:
        print("agent_display_name column not found, nothing to revert")
