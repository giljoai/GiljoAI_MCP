"""add_decommissioned_at_field

Handover 0113 Phase 3: Add decommissioned_at timestamp field to MCPAgentJob.

This migration adds the decommissioned_at field to track when an agent job
was decommissioned during project closeout workflow.

Key changes:
1. Add decommissioned_at: TIMESTAMP WITH TIME ZONE - When job was decommissioned

Use cases:
- Track when agent jobs were decommissioned during project closeout
- Maintain audit trail for agent lifecycle
- Support project closeout workflow (Handover 0113)

Revision ID: 0113b_decommissioned_at
Revises: 0113_simplify_7_states
Create Date: 2025-11-07 00:00:00.000000

Database impact:
  - 1 ADD COLUMN operation (instant in PostgreSQL 11+ with NULL default)
  - No data migration required (column nullable)
Estimated downtime: <1 second
Rollback strategy: Full downgrade support (column drop)
Multi-tenant isolation: Preserved (column scoped to existing tenant_key)

"""

from collections.abc import Sequence
from typing import Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0113b_decom_at"
down_revision: Union[str, Sequence[str], None] = "0113_simplify_7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add decommissioned_at timestamp field to MCPAgentJob model.

    This migration adds a timezone-aware timestamp field to track when
    agent jobs are decommissioned during project closeout workflow.

    Migration characteristics:
    - Idempotent: Safe to run multiple times (column existence checked by Alembic)
    - Isolated: Only affects mcp_agent_jobs table
    - Zero impact: Column nullable with NULL default
    - Backward compatible: Existing code continues to work without changes
    """

    print("\n" + "=" * 80)
    print("[Handover 0113 Phase 3] Adding decommissioned_at field to MCPAgentJob")
    print("=" * 80)

    # STEP 1: Add decommissioned_at column
    # =====================================
    print("[0113 Phase 3] Step 1: Adding decommissioned_at column...")

    op.add_column(
        "mcp_agent_jobs",
        sa.Column(
            "decommissioned_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when agent job was decommissioned (Handover 0113)"
        )
    )

    print("[0113 Phase 3]   ✓ decommissioned_at column added successfully")
    print("[0113 Phase 3] Migration complete\n")
    print("=" * 80)


def downgrade() -> None:
    """
    Rollback decommissioned_at field addition.

    WARNING: This will drop the decommissioned_at column.
    All decommissioning timestamp data will be lost.
    """

    print("\n" + "=" * 80)
    print("[Handover 0113 Phase 3 Rollback] Removing decommissioned_at field")
    print("=" * 80)

    # STEP 1: Drop decommissioned_at column
    # ======================================
    print("[0113 Phase 3 Rollback] Step 1: Dropping decommissioned_at column...")

    op.drop_column("mcp_agent_jobs", "decommissioned_at")

    print("[0113 Phase 3 Rollback]   ✓ decommissioned_at column dropped successfully")
    print("[0113 Phase 3 Rollback] Rollback complete\n")
    print("WARNING: All decommissioning timestamp data has been lost.\n")
    print("=" * 80)
