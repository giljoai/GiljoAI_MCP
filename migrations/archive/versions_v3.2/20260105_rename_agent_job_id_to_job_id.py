"""Rename agent_job_id to job_id in tasks table

Revision ID: 20260105_job_id_fix
Revises: caeddfdbb2a0
Create Date: 2026-01-05

This migration renames the incorrectly named agent_job_id column to job_id
in the tasks table for existing databases.

Semantic clarity:
- agent_id = Identity ("who are you")
- job_id = Work order ("what are we doing")

This migration is idempotent - it safely handles both:
1. Existing databases with agent_job_id (renames to job_id)
2. Fresh installs from updated baseline (job_id already exists, skips rename)
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = '20260105_job_id_fix'
down_revision = 'caeddfdbb2a0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Rename agent_job_id to job_id in tasks table."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if tasks table exists
    tables = inspector.get_table_names()
    if 'tasks' not in tables:
        # Table doesn't exist yet - fresh install from baseline
        return

    # Get current columns in tasks table
    columns = [col['name'] for col in inspector.get_columns('tasks')]

    # Case 1: Column already renamed (fresh install or migration already run)
    if 'job_id' in columns and 'agent_job_id' not in columns:
        print("Column already renamed to job_id, skipping migration")
        return

    # Case 2: Old column name exists (existing database)
    if 'agent_job_id' in columns:
        print("Renaming agent_job_id to job_id...")

        # Drop dependent indexes first
        try:
            op.drop_index('idx_task_agent_job', table_name='tasks')
            print("  - Dropped index: idx_task_agent_job")
        except Exception as e:
            print(f"  - Index idx_task_agent_job not found or already dropped: {e}")

        try:
            op.drop_index('idx_task_tenant_agent_job', table_name='tasks')
            print("  - Dropped index: idx_task_tenant_agent_job")
        except Exception as e:
            print(f"  - Index idx_task_tenant_agent_job not found or already dropped: {e}")

        # Drop foreign key constraint (name may vary)
        # We'll recreate it with the correct name after rename
        constraints = inspector.get_foreign_keys('tasks')
        fk_to_drop = None
        for fk in constraints:
            if fk['constrained_columns'] == ['agent_job_id']:
                fk_to_drop = fk['name']
                break

        if fk_to_drop:
            try:
                op.drop_constraint(fk_to_drop, 'tasks', type_='foreignkey')
                print(f"  - Dropped FK constraint: {fk_to_drop}")
            except Exception as e:
                print(f"  - Failed to drop FK constraint {fk_to_drop}: {e}")

        # Rename the column
        op.alter_column('tasks', 'agent_job_id', new_column_name='job_id')
        print("  - Renamed column: agent_job_id -> job_id")

        # Recreate foreign key with correct name
        op.create_foreign_key(
            'fk_task_job',
            'tasks',
            'mcp_agent_jobs',
            ['job_id'],
            ['job_id']
        )
        print("  - Created FK constraint: fk_task_job")

        # Recreate indexes with correct names
        op.create_index('idx_task_job', 'tasks', ['job_id'], unique=False)
        print("  - Created index: idx_task_job")

        op.create_index('idx_task_tenant_job', 'tasks', ['tenant_key', 'job_id'], unique=False)
        print("  - Created index: idx_task_tenant_job")

        print("Migration complete!")

    else:
        print("WARNING: Neither job_id nor agent_job_id found in tasks table")
        print(f"Available columns: {columns}")


def downgrade() -> None:
    """Revert job_id back to agent_job_id."""
    # Get database connection
    conn = op.get_bind()
    inspector = inspect(conn)

    # Check if tasks table exists
    tables = inspector.get_table_names()
    if 'tasks' not in tables:
        return

    # Get current columns
    columns = [col['name'] for col in inspector.get_columns('tasks')]

    if 'job_id' in columns:
        print("Reverting job_id to agent_job_id...")

        # Drop indexes
        try:
            op.drop_index('idx_task_job', table_name='tasks')
        except Exception:
            pass

        try:
            op.drop_index('idx_task_tenant_job', table_name='tasks')
        except Exception:
            pass

        # Drop FK
        try:
            op.drop_constraint('fk_task_job', 'tasks', type_='foreignkey')
        except Exception:
            pass

        # Rename column
        op.alter_column('tasks', 'job_id', new_column_name='agent_job_id')

        # Recreate old constraint and indexes
        op.create_foreign_key(
            None,  # Auto-generated name
            'tasks',
            'mcp_agent_jobs',
            ['agent_job_id'],
            ['job_id']
        )

        op.create_index('idx_task_agent_job', 'tasks', ['agent_job_id'], unique=False)
        op.create_index('idx_task_tenant_agent_job', 'tasks', ['tenant_key', 'agent_job_id'], unique=False)

        print("Downgrade complete!")
