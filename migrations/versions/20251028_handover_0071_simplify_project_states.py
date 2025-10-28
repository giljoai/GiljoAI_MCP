"""Handover 0071: Simplify project state management

Convert paused projects to inactive, removing pause/resume complexity.

This migration is part of the project state simplification initiative that removes
the paused state from the project lifecycle. Projects that were in a paused state
are converted to inactive, simplifying the state machine and removing the associated
pause/resume logic from the codebase.

Key changes:
- Converts all projects with status='paused' to status='inactive'
- No schema changes (status column already exists)
- Maintains data integrity and audit trail
- Multi-tenant isolation preserved

Revision ID: 20251028_simplify_states
Revises: 20251028_completed_at
Create Date: 2025-10-28

Database impact: UPDATE statement only (no DDL changes)
Estimated downtime: Minimal (single UPDATE for entire projects table)
Rollback strategy: Database backup restore required

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic
revision: str = '20251028_simplify_states'
down_revision: Union[str, Sequence[str], None] = '20251028_completed_at'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Handover 0071: Convert paused projects to inactive.

    This migration simplifies project state management by:
    1. Converting all 'paused' projects to 'inactive'
    2. Removing pause/resume complexity from project lifecycle
    3. Maintaining data integrity (no data loss, only status field change)

    Database constraint 'idx_project_single_active_per_product' already exists
    and continues to enforce single active project per product.

    Migration characteristics:
    - Idempotent: Safe to run multiple times
    - Isolated: Only updates project status field
    - Auditable: Logs conversion count for audit trail
    - Verified: Checks no paused projects remain after conversion
    """

    print("\n" + "=" * 80)
    print("[Handover 0071] Simplifying project state management")
    print("=" * 80)

    connection = op.get_bind()

    # STEP 1: Count paused projects before conversion
    # ================================================
    print("[Handover 0071] Step 1: Analyzing current state...")

    result = connection.execute(text(
        "SELECT COUNT(*) as count FROM projects WHERE status = 'paused'"
    ))
    paused_count = result.scalar()

    print(f"[Handover 0071]   - Found {paused_count} paused project(s)")

    if paused_count > 0:
        # STEP 2: Convert paused to inactive
        # ==================================
        print(f"[Handover 0071] Step 2: Converting {paused_count} paused project(s) to inactive...")

        op.execute(text("""
            UPDATE projects
            SET status = 'inactive'
            WHERE status = 'paused'
        """))

        print(f"[Handover 0071]   - Successfully converted {paused_count} project(s)")
    else:
        print("[Handover 0071] Step 2: No paused projects to convert (skipping)")

    # STEP 3: Verify no paused projects remain
    # ========================================
    print("[Handover 0071] Step 3: Verifying conversion...")

    result = connection.execute(text(
        "SELECT COUNT(*) as count FROM projects WHERE status = 'paused'"
    ))
    remaining_paused = result.scalar()

    if remaining_paused > 0:
        print("[Handover 0071] ERROR: Migration verification failed!")
        print(f"[Handover 0071] ERROR: {remaining_paused} paused project(s) still exist")
        print("=" * 80)
        raise Exception(
            f"[Handover 0071] Migration failed: {remaining_paused} paused projects still exist. "
            "The state simplification could not be completed."
        )

    print("[Handover 0071]   - Verification complete: No paused projects remain")

    # STEP 4: Show final state
    # =======================
    print("[Handover 0071] Step 4: Final state summary...")

    result = connection.execute(text("""
        SELECT status, COUNT(*) as count
        FROM projects
        GROUP BY status
        ORDER BY status
    """))

    rows = result.fetchall()
    for row in rows:
        status, count = row
        print(f"[Handover 0071]   - Projects with status '{status}': {count}")

    print("=" * 80)
    print("[Handover 0071] Migration completed successfully!")
    print("[Handover 0071] Project state management simplified (paused -> inactive)")
    print("=" * 80 + "\n")


def downgrade() -> None:
    """
    Downgrade not supported for state simplification.

    This migration cannot be safely downgraded because:

    1. Information Loss: We cannot reliably revert inactive -> paused because we don't
       have a record of which inactive projects were originally paused vs. set to inactive
       after this migration runs.

    2. Timing Ambiguity: Projects may be set to inactive through normal application
       logic after this migration runs, making it impossible to distinguish between
       projects that should be restored to paused and those that should remain inactive.

    3. Code Removal: The pause/resume feature will be removed from the codebase as
       part of this handover, making downgrade semantically incorrect even if the
       data could be restored.

    Recovery Strategy:
    - If rollback is absolutely required, restore the database from backup
    - Do not use this migration downgrade function
    - Contact database administrator if recovery is needed

    The migration is designed to be forward-only and should not be reverted.
    """

    print("\n" + "=" * 80)
    print("[Handover 0071] WARNING: Downgrade not supported")
    print("=" * 80)
    print("[Handover 0071] ERROR: This migration cannot be safely downgraded")
    print("[Handover 0071]")
    print("[Handover 0071] Reason: Paused -> Inactive conversion is one-directional")
    print("[Handover 0071]         Cannot reliably revert due to information loss")
    print("[Handover 0071]")
    print("[Handover 0071] Recovery: Restore from database backup instead")
    print("=" * 80 + "\n")

    raise NotImplementedError(
        "[Handover 0071] Downgrade not supported for state simplification. "
        "Restore from database backup if rollback is required. "
        "See migration docstring for complete rationale."
    )
