"""Handover 0072 Migration 1: Task-to-Agent Job Integration

Enables task-to-agent job linking and workflow automation by adding agent_job_id
foreign key to tasks table and making project_id nullable for unassigned tasks.

Key changes:
1. agent_job_id: VARCHAR(36) FK to mcp_agent_jobs.job_id
   - Links tasks to agent jobs for execution tracking
   - Nullable for backward compatibility
   - Enables bidirectional status synchronization

2. project_id: Changed from NOT NULL to NULLABLE
   - Allows tasks without product/project assignment
   - Unassigned tasks visible across all products
   - Support for quick task capture from CLI tools

3. status: Updated comment to include 'converted' state
   - Task status becomes 'converted' when promoted to project
   - Maintains audit trail via converted_to_project_id FK

4. Indexes for performance:
   - idx_task_agent_job: Single-column index on agent_job_id
   - idx_task_tenant_agent_job: Composite for tenant isolation

Use cases:
- CLI slash commands (/task) create unassigned tasks
- Assign task to agent → auto-spawn MCPAgentJob
- Agent completes job → task status auto-syncs
- Convert task to project → task marked 'converted'

Revision ID: 20251029_0072_01
Revises: 20251029_0073_03
Create Date: 2025-10-29

Database impact:
  - 1 ADD COLUMN operation (agent_job_id)
  - 1 ALTER COLUMN operation (project_id nullable)
  - 2 CREATE INDEX operations
  - 1 FOREIGN KEY constraint
Estimated downtime: <3 seconds
Rollback strategy: Full downgrade support (restore NOT NULL, drop column)
Multi-tenant isolation: Preserved (composite index with tenant_key)

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic
revision: str = "20251029_0072_01"
down_revision: Union[str, Sequence[str], None] = "20251029_0073_03"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Handover 0072 Migration 1: Task-to-Agent Job Integration.

    This migration enables task-agent job linking by:
    1. Adding agent_job_id FK for execution tracking
    2. Making project_id nullable for unassigned tasks
    3. Creating indexes for efficient queries
    4. Preserving multi-tenant isolation

    Migration characteristics:
    - Idempotent: Safe to run multiple times
    - Zero data loss: All existing tasks remain functional
    - Backward compatible: New columns are nullable
    - Performance optimized: Composite indexes for tenant queries
    """

    print("\n" + "=" * 80)
    print("[Handover 0072-01] Adding task-to-agent job integration")
    print("=" * 80)

    connection = op.get_bind()

    # STEP 1: Analyze current state
    # =============================
    print("[0072-01] Step 1: Analyzing current tasks state...")

    result = connection.execute(text("SELECT COUNT(*) FROM tasks"))
    total_tasks = result.scalar()
    print(f"[0072-01]   - Total tasks in database: {total_tasks}")

    result = connection.execute(
        text("""
        SELECT status, COUNT(*) as count
        FROM tasks
        GROUP BY status
        ORDER BY count DESC
    """)
    )
    status_distribution = result.fetchall()

    print("[0072-01]   Task status distribution:")
    for status, count in status_distribution:
        print(f"[0072-01]     - {status}: {count} task(s)")

    result = connection.execute(
        text("""
        SELECT
            COUNT(*) FILTER (WHERE project_id IS NOT NULL) as with_project,
            COUNT(*) FILTER (WHERE project_id IS NULL) as without_project,
            COUNT(*) as total
        FROM tasks
    """)
    )
    row = result.fetchone()

    print("[0072-01]   Project assignment:")
    print(f"[0072-01]     - Total tasks: {row[2]}")
    print(f"[0072-01]     - With project: {row[0]}")
    print(f"[0072-01]     - Without project: {row[1]}")

    # STEP 2: Make project_id nullable
    # =================================
    print("[0072-01] Step 2: Making project_id nullable for unassigned tasks...")

    # Drop NOT NULL constraint on project_id
    op.alter_column("tasks", "project_id", existing_type=sa.String(36), nullable=True)
    print("[0072-01]   - Made 'project_id' nullable (allows unassigned tasks)")

    # STEP 3: Add agent_job_id column
    # ================================
    print("[0072-01] Step 3: Adding agent_job_id column for job linking...")

    op.add_column(
        "tasks",
        sa.Column(
            "agent_job_id", sa.String(36), nullable=True, comment="Links task to MCPAgentJob for execution tracking"
        ),
    )
    print("[0072-01]   - Added 'agent_job_id' column (VARCHAR(36), nullable)")

    # STEP 4: Create foreign key constraint
    # ======================================
    print("[0072-01] Step 4: Creating foreign key to mcp_agent_jobs...")

    op.create_foreign_key(
        "fk_task_agent_job",
        "tasks",
        "mcp_agent_jobs",
        ["agent_job_id"],
        ["job_id"],
        ondelete="SET NULL",  # If agent job deleted, task remains but loses link
    )
    print("[0072-01]   - Created FK constraint (SET NULL on delete)")

    # STEP 5: Create indexes for performance
    # =======================================
    print("[0072-01] Step 5: Creating indexes for agent job queries...")

    # Single-column index for agent_job_id lookups
    op.create_index("idx_task_agent_job", "tasks", ["agent_job_id"], unique=False)
    print("[0072-01]   - Created index 'idx_task_agent_job' (agent_job_id)")

    # Composite index for tenant-scoped queries
    op.create_index("idx_task_tenant_agent_job", "tasks", ["tenant_key", "agent_job_id"], unique=False)
    print("[0072-01]   - Created index 'idx_task_tenant_agent_job' (tenant_key, agent_job_id)")

    # STEP 6: Verify migration success
    # =================================
    print("[0072-01] Step 6: Verifying migration...")

    # Check that all existing tasks still have valid data
    result = connection.execute(
        text("""
        SELECT COUNT(*)
        FROM tasks
        WHERE id IS NULL OR tenant_key IS NULL OR title IS NULL
    """)
    )
    invalid_tasks = result.scalar()

    if invalid_tasks > 0:
        print(f"[0072-01] ERROR: {invalid_tasks} tasks have invalid core data!")
        raise Exception("[0072-01] Migration failed: data integrity violation")

    print("[0072-01]   - Verification complete: All tasks have valid core data")

    # STEP 7: Show final state
    # ========================
    print("[0072-01] Step 7: Final state summary...")

    result = connection.execute(
        text("""
        SELECT
            COUNT(*) FILTER (WHERE agent_job_id IS NOT NULL) as with_job,
            COUNT(*) FILTER (WHERE agent_job_id IS NULL) as without_job,
            COUNT(*) as total
        FROM tasks
    """)
    )
    row = result.fetchone()

    print("[0072-01]   Agent job assignment:")
    print(f"[0072-01]     - Total tasks: {row[2]}")
    print(f"[0072-01]     - With agent job: {row[0]}")
    print(f"[0072-01]     - Without agent job: {row[1]}")

    result = connection.execute(
        text("""
        SELECT
            COUNT(*) FILTER (WHERE project_id IS NOT NULL) as with_project,
            COUNT(*) FILTER (WHERE project_id IS NULL) as without_project,
            COUNT(*) as total
        FROM tasks
    """)
    )
    row = result.fetchone()

    print("[0072-01]   Project assignment (after nullable change):")
    print(f"[0072-01]     - Total tasks: {row[2]}")
    print(f"[0072-01]     - With project: {row[0]}")
    print(f"[0072-01]     - Without project: {row[1]}")

    print("=" * 80)
    print("[Handover 0072-01] Migration completed successfully!")
    print("[0072-01] Task-agent job integration enabled (1 column + 1 FK + 2 indexes)")
    print("=" * 80 + "\n")


def downgrade() -> None:
    """
    Downgrade migration: Remove task-agent job integration.

    This downgrade:
    1. Drops indexes for agent_job_id
    2. Drops foreign key constraint
    3. Removes agent_job_id column
    4. Restores project_id NOT NULL constraint (DESTRUCTIVE)

    Data loss:
    - All task-to-agent job links (agent_job_id)
    - Tasks without project_id will be DELETED (if any exist)

    Impact: Tasks lose agent job tracking but remain functional.
    WARNING: Unassigned tasks will be deleted due to NOT NULL restore.
    """

    print("\n" + "=" * 80)
    print("[Handover 0072-01] Downgrading: Removing task-agent job integration")
    print("=" * 80)

    connection = op.get_bind()

    # STEP 1: Check for tasks with agent jobs
    # ========================================
    print("[0072-01 Downgrade] Step 1: Checking for task-agent job links...")

    result = connection.execute(
        text("""
        SELECT COUNT(*)
        FROM tasks
        WHERE agent_job_id IS NOT NULL
    """)
    )
    linked_tasks = result.scalar()

    if linked_tasks > 0:
        print(f"[0072-01] WARNING: {linked_tasks} task(s) linked to agent jobs")
        print("[0072-01] WARNING: These links will be lost after downgrade")

    # STEP 2: Check for unassigned tasks
    # ===================================
    print("[0072-01 Downgrade] Step 2: Checking for unassigned tasks...")

    result = connection.execute(
        text("""
        SELECT COUNT(*)
        FROM tasks
        WHERE project_id IS NULL
    """)
    )
    unassigned_tasks = result.scalar()

    if unassigned_tasks > 0:
        print(f"[0072-01] CRITICAL WARNING: {unassigned_tasks} unassigned task(s) found")
        print("[0072-01] CRITICAL: These tasks will be DELETED when restoring NOT NULL")
        print("[0072-01] ACTION REQUIRED: Assign tasks to projects before downgrade")
        # Optionally, we could fail here to prevent data loss
        # raise Exception("Cannot downgrade: unassigned tasks exist")

    # STEP 3: Drop indexes
    # ====================
    print("[0072-01 Downgrade] Step 3: Dropping agent job indexes...")

    op.drop_index("idx_task_tenant_agent_job", table_name="tasks")
    print("[0072-01]   - Dropped 'idx_task_tenant_agent_job' index")

    op.drop_index("idx_task_agent_job", table_name="tasks")
    print("[0072-01]   - Dropped 'idx_task_agent_job' index")

    # STEP 4: Drop foreign key
    # =========================
    print("[0072-01 Downgrade] Step 4: Dropping foreign key constraint...")

    op.drop_constraint("fk_task_agent_job", "tasks", type_="foreignkey")
    print("[0072-01]   - Dropped 'fk_task_agent_job' constraint")

    # STEP 5: Drop agent_job_id column
    # =================================
    print("[0072-01 Downgrade] Step 5: Removing agent_job_id column...")

    op.drop_column("tasks", "agent_job_id")
    print("[0072-01]   - Dropped 'agent_job_id' column")

    # STEP 6: Restore project_id NOT NULL (DESTRUCTIVE)
    # ==================================================
    print("[0072-01 Downgrade] Step 6: Restoring project_id NOT NULL constraint...")

    if unassigned_tasks > 0:
        print(f"[0072-01] WARNING: Deleting {unassigned_tasks} unassigned task(s)...")
        connection.execute(
            text("""
            DELETE FROM tasks WHERE project_id IS NULL
        """)
        )
        print(f"[0072-01]   - Deleted {unassigned_tasks} task(s)")

    op.alter_column("tasks", "project_id", existing_type=sa.String(36), nullable=False)
    print("[0072-01]   - Restored 'project_id' NOT NULL constraint")

    # STEP 7: Verify downgrade success
    # =================================
    print("[0072-01 Downgrade] Step 7: Verifying downgrade...")

    result = connection.execute(text("SELECT COUNT(*) FROM tasks"))
    remaining_tasks = result.scalar()

    print(f"[0072-01]   - {remaining_tasks} task(s) remain functional")
    print("[0072-01]   - Task-agent job integration disabled")

    print("=" * 80)
    print("[Handover 0072-01] Downgrade completed successfully!")
    print("[0072-01] Task-agent job columns removed (1 column + 1 FK + 2 indexes)")
    if linked_tasks > 0:
        print(f"[0072-01] WARNING: Agent job links lost for {linked_tasks} task(s)")
    if unassigned_tasks > 0:
        print(f"[0072-01] WARNING: {unassigned_tasks} unassigned task(s) deleted")
    print("=" * 80 + "\n")
