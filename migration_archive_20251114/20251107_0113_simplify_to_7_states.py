"""simplify_to_7_states

Handover 0113 Phase 2: Simplify MCPAgentJob state system from 9 states to 7 states.

This migration:
1. Removes old states: preparing, active, review, cancelling
2. Adds new state: decommissioned
3. Migrates existing data to new state system
4. Adds failure_reason field for failed jobs

State Mapping:
- preparing → waiting
- active → working
- review → working
- cancelling → cancelled
- complete → complete (unchanged)
- failed → failed (unchanged)
- blocked → blocked (unchanged)
- waiting → waiting (unchanged)
- working → working (unchanged)
- NEW: decommissioned (terminal state for project closeout)
- NEW: cancelled (atomic cancellation, no intermediate state)

Final 7 States: waiting, working, blocked, complete, failed, cancelled, decommissioned

Revision ID: 0113_simplify_7_states
Revises: 9fdd0e67585f
Create Date: 2025-11-07 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "0113_simplify_7"
down_revision: Union[str, Sequence[str], None] = "9fdd0e67585f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Simplify MCPAgentJob state system from 9 states to 7 states.

    Steps:
    1. Add failure_reason column
    2. Migrate existing data to new states
    3. Drop old status constraint
    4. Create new 7-state constraint
    """

    print("\n[Handover 0113 Phase 2 Migration] Simplifying state system to 7 states...")

    # STEP 1: Add failure_reason column
    # ==================================
    print("  - Adding failure_reason column...")
    op.add_column(
        "mcp_agent_jobs",
        sa.Column(
            "failure_reason",
            sa.String(50),
            nullable=True,
            comment="Reason for failure: error, timeout, system_error"
        )
    )

    # STEP 2: Migrate existing data to new states
    # ============================================
    print("  - Migrating existing data to new state system...")

    connection = op.get_bind()

    # preparing → waiting
    result = connection.execute(
        text("UPDATE mcp_agent_jobs SET status = 'waiting' WHERE status = 'preparing'")
    )
    if result.rowcount > 0:
        print(f"    ✓ Migrated {result.rowcount} jobs from 'preparing' to 'waiting'")

    # active → working
    result = connection.execute(
        text("UPDATE mcp_agent_jobs SET status = 'working' WHERE status = 'active'")
    )
    if result.rowcount > 0:
        print(f"    ✓ Migrated {result.rowcount} jobs from 'active' to 'working'")

    # review → working
    result = connection.execute(
        text("UPDATE mcp_agent_jobs SET status = 'working' WHERE status = 'review'")
    )
    if result.rowcount > 0:
        print(f"    ✓ Migrated {result.rowcount} jobs from 'review' to 'working'")

    # cancelling → cancelled (atomic cancellation)
    result = connection.execute(
        text("UPDATE mcp_agent_jobs SET status = 'cancelled' WHERE status = 'cancelling'")
    )
    if result.rowcount > 0:
        print(f"    ✓ Migrated {result.rowcount} jobs from 'cancelling' to 'cancelled'")

    # STEP 3: Drop old status constraint
    # ===================================
    print("  - Dropping old 9-state constraint...")
    op.drop_constraint("ck_mcp_agent_job_status", "mcp_agent_jobs", type_="check")

    # STEP 4: Create new 7-state constraint
    # ======================================
    print("  - Creating new 7-state constraint...")
    op.create_check_constraint(
        "ck_mcp_agent_job_status",
        "mcp_agent_jobs",
        "status IN ('waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned')"
    )

    # STEP 5: Add failure_reason constraint
    # ======================================
    print("  - Adding failure_reason constraint...")
    op.create_check_constraint(
        "ck_mcp_agent_job_failure_reason",
        "mcp_agent_jobs",
        "failure_reason IS NULL OR failure_reason IN ('error', 'timeout', 'system_error')"
    )

    print("[Handover 0113 Phase 2 Migration] OK State system simplified to 7 states successfully\n")
    print("  Final states: waiting, working, blocked, complete, failed, cancelled, decommissioned")


def downgrade() -> None:
    """
    Rollback to 9-state system.

    WARNING: This will convert states back to the original 9-state system.
    Some state information may be lost during conversion:
    - cancelled → cancelling (intermediate state)
    - decommissioned → complete (closest match)
    - failure_reason data will be lost
    """

    print("\n[Handover 0113 Phase 2 Migration Rollback] Reverting to 9-state system...")

    # STEP 1: Migrate data back to old states
    # ========================================
    print("  - Migrating data back to 9-state system...")

    connection = op.get_bind()

    # cancelled → cancelling (intermediate state)
    result = connection.execute(
        text("UPDATE mcp_agent_jobs SET status = 'cancelling' WHERE status = 'cancelled'")
    )
    if result.rowcount > 0:
        print(f"    ✓ Reverted {result.rowcount} jobs from 'cancelled' to 'cancelling'")

    # decommissioned → complete (closest match)
    result = connection.execute(
        text("UPDATE mcp_agent_jobs SET status = 'complete' WHERE status = 'decommissioned'")
    )
    if result.rowcount > 0:
        print(f"    ✓ Reverted {result.rowcount} jobs from 'decommissioned' to 'complete'")
        print("      WARNING: Decommissioned jobs converted to complete - context may be lost")

    # STEP 2: Drop failure_reason constraint
    # =======================================
    print("  - Dropping failure_reason constraint...")
    op.drop_constraint("ck_mcp_agent_job_failure_reason", "mcp_agent_jobs", type_="check")

    # STEP 3: Drop new 7-state constraint
    # ====================================
    print("  - Dropping 7-state constraint...")
    op.drop_constraint("ck_mcp_agent_job_status", "mcp_agent_jobs", type_="check")

    # STEP 4: Restore old 9-state constraint
    # =======================================
    print("  - Restoring 9-state constraint...")
    op.create_check_constraint(
        "ck_mcp_agent_job_status",
        "mcp_agent_jobs",
        "status IN ('waiting', 'preparing', 'active', 'working', 'review', 'complete', 'failed', 'blocked', 'cancelling')"
    )

    # STEP 5: Drop failure_reason column
    # ===================================
    print("  - Dropping failure_reason column...")
    op.drop_column("mcp_agent_jobs", "failure_reason")

    print("[Handover 0113 Phase 2 Migration Rollback] OK Reverted to 9-state system\n")
    print("WARNING: failure_reason data has been lost.\n")
