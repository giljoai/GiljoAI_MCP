"""agent_monitoring

Handover 0107: Agent Monitoring & Graceful Cancellation.

This migration adds activity tracking fields to mcp_agent_jobs table:
1. last_progress_at - Timestamp of last progress update from agent
2. last_message_check_at - Timestamp of last message queue check by agent
3. Extends status enum to include 'cancelling' state for graceful cancellation

Revision ID: 20251106_agent_monitoring
Revises: 8cd632d27c5e
Create Date: 2025-11-06 00:00:00.000000

"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text


# revision identifiers, used by Alembic.
revision: str = "20251106_agent_monitoring"
down_revision: Union[str, Sequence[str], None] = "8cd632d27c5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add agent monitoring fields to mcp_agent_jobs table.

    Steps:
    1. Add last_progress_at timestamp column
    2. Add last_message_check_at timestamp column
    3. Drop existing status constraint
    4. Recreate status constraint with 'cancelling' state
    """

    print("\n[Handover 0107 Migration] Adding agent monitoring fields...")

    # STEP 1: Add last_progress_at column
    # ====================================
    print("  - Adding last_progress_at column...")
    op.add_column(
        "mcp_agent_jobs",
        sa.Column(
            "last_progress_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last progress update from agent (Handover 0107)"
        )
    )

    # STEP 2: Add last_message_check_at column
    # =========================================
    print("  - Adding last_message_check_at column...")
    op.add_column(
        "mcp_agent_jobs",
        sa.Column(
            "last_message_check_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp of last message queue check by agent (Handover 0107)"
        )
    )

    # STEP 3: Update status constraint to include 'cancelling'
    # =========================================================
    print("  - Updating status constraint to include 'cancelling' state...")

    # Drop existing constraint
    op.drop_constraint("ck_mcp_agent_job_status", "mcp_agent_jobs", type_="check")

    # Recreate with 'cancelling' state added
    op.create_check_constraint(
        "ck_mcp_agent_job_status",
        "mcp_agent_jobs",
        "status IN ('waiting', 'preparing', 'active', 'working', 'review', 'complete', 'failed', 'blocked', 'cancelling')"
    )

    print("[Handover 0107 Migration] OK Agent monitoring fields added successfully\n")


def downgrade() -> None:
    """
    Remove agent monitoring fields from mcp_agent_jobs table.

    WARNING: This will drop the last_progress_at and last_message_check_at columns.
    All tracking data in these columns will be lost.
    """

    print("\n[Handover 0107 Migration Rollback] Removing agent monitoring fields...")

    # STEP 1: Remove status constraint and restore original
    # ======================================================
    print("  - Restoring original status constraint...")

    # Drop constraint with 'cancelling'
    op.drop_constraint("ck_mcp_agent_job_status", "mcp_agent_jobs", type_="check")

    # Recreate without 'cancelling' state
    op.create_check_constraint(
        "ck_mcp_agent_job_status",
        "mcp_agent_jobs",
        "status IN ('waiting', 'preparing', 'active', 'working', 'review', 'complete', 'failed', 'blocked')"
    )

    # STEP 2: Drop last_message_check_at column
    # ==========================================
    print("  - Dropping last_message_check_at column...")
    op.drop_column("mcp_agent_jobs", "last_message_check_at")

    # STEP 3: Drop last_progress_at column
    # =====================================
    print("  - Dropping last_progress_at column...")
    op.drop_column("mcp_agent_jobs", "last_progress_at")

    print("[Handover 0107 Migration Rollback] OK Agent monitoring fields removed\n")
    print("WARNING: All agent activity tracking data has been lost.\n")
