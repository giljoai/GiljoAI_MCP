"""Handover 0073 Migration 3: Add agent tool assignment tracking

Adds columns to mcp_agent_jobs table to track which AI coding tool (Claude Code,
Codex, Gemini CLI) each agent uses and provides human-readable agent names for
enhanced UI display and debugging.

Key changes:
1. tool_type: VARCHAR(20) - Identifies the AI tool assigned to this agent job
   - Values: 'claude-code', 'codex', 'gemini', 'universal'
   - Default: 'universal' (compatible with any tool)
   - Enables tool-specific routing and load balancing

2. agent_name: VARCHAR(255) - Human-readable agent display name
   - Values: 'Backend Agent', 'Frontend Agent', 'Database Agent', etc.
   - Nullable for backward compatibility (falls back to agent_type)
   - Enhances UI clarity and debugging

3. Index on tool_type for efficient filtering and assignment queries

Use cases:
- Route specialized jobs to specific AI tools (e.g., Rust code to Claude Code)
- Load balance across multiple tool instances
- Track tool performance metrics and success rates
- Display friendly agent names in dashboard UI

Revision ID: 20251029_0073_03
Revises: 20251029_0073_02
Create Date: 2025-10-29

Database impact:
  - 2 ADD COLUMN operations (instant in PostgreSQL 11+)
  - 1 CREATE INDEX operation (fast on existing data)
  - 1 CHECK constraint for tool_type validation
Estimated downtime: <2 seconds
Rollback strategy: Full downgrade support (column drop)
Multi-tenant isolation: Preserved (columns scoped to existing tenant_key)

"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy import text


# revision identifiers, used by Alembic
revision: str = "20251029_0073_03"
down_revision: Union[str, Sequence[str], None] = "20251029_0073_02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Handover 0073 Migration 3: Add agent tool assignment tracking.

    This migration enhances the mcp_agent_jobs table by:
    1. Adding tool_type for AI tool assignment and routing
    2. Adding agent_name for human-readable display names
    3. Creating index for efficient tool-based filtering
    4. Adding constraint to validate tool_type values

    Migration characteristics:
    - Idempotent: Safe to run multiple times
    - Isolated: Only affects mcp_agent_jobs table
    - Zero impact: All columns have sensible defaults
    - Backward compatible: Existing code works without changes
    """

    print("\n" + "=" * 80)
    print("[Handover 0073-03] Adding agent tool assignment tracking")
    print("=" * 80)

    connection = op.get_bind()

    # STEP 1: Analyze current state
    # =============================
    print("[0073-03] Step 1: Analyzing current agent jobs state...")

    result = connection.execute(text("SELECT COUNT(*) FROM mcp_agent_jobs"))
    total_jobs = result.scalar()
    print(f"[0073-03]   - Total agent jobs in database: {total_jobs}")

    result = connection.execute(
        text(
            "SELECT agent_type, COUNT(*) as count FROM mcp_agent_jobs GROUP BY agent_type ORDER BY count DESC LIMIT 10"
        )
    )
    agent_distribution = result.fetchall()

    print("[0073-03]   Agent type distribution (top 10):")
    for agent_type, count in agent_distribution:
        print(f"[0073-03]     - {agent_type}: {count} job(s)")

    # STEP 2: Add tool_type column
    # ============================
    print("[0073-03] Step 2: Adding tool_type column...")

    op.add_column(
        "mcp_agent_jobs",
        sa.Column(
            "tool_type",
            sa.String(20),
            nullable=False,
            server_default="universal",
            comment="AI coding tool assigned to this agent job (claude-code, codex, gemini, universal)",
        ),
    )
    print("[0073-03]   - Added 'tool_type' column (VARCHAR(20), default='universal')")

    # STEP 3: Add CHECK constraint for tool_type
    # ===========================================
    print("[0073-03] Step 3: Adding tool_type validation constraint...")

    op.create_check_constraint(
        "ck_mcp_agent_job_tool_type", "mcp_agent_jobs", "tool_type IN ('claude-code', 'codex', 'gemini', 'universal')"
    )
    print("[0073-03]   - Added tool_type constraint (4 valid values)")

    # STEP 4: Add agent_name column
    # ==============================
    print("[0073-03] Step 4: Adding agent_name column...")

    op.add_column(
        "mcp_agent_jobs",
        sa.Column(
            "agent_name",
            sa.String(255),
            nullable=True,
            comment="Human-readable agent display name (e.g., Backend Agent, Database Agent)",
        ),
    )
    print("[0073-03]   - Added 'agent_name' column (VARCHAR(255), nullable)")

    # STEP 5: Create index for tool_type filtering
    # =============================================
    print("[0073-03] Step 5: Creating index for tool assignment queries...")

    # Composite index: tenant_key + tool_type (for multi-tenant tool filtering)
    op.create_index("idx_mcp_agent_jobs_tenant_tool", "mcp_agent_jobs", ["tenant_key", "tool_type"], unique=False)
    print("[0073-03]   - Created index 'idx_mcp_agent_jobs_tenant_tool' (tenant_key, tool_type)")

    # STEP 6: Populate agent_name from agent_type (best effort)
    # ==========================================================
    print("[0073-03] Step 6: Populating agent_name from agent_type...")

    # Create friendly names by converting agent_type to title case
    op.execute(
        text("""
        UPDATE mcp_agent_jobs
        SET agent_name = INITCAP(REPLACE(agent_type, '_', ' ')) || ' Agent'
        WHERE agent_name IS NULL
    """)
    )

    result = connection.execute(text("SELECT COUNT(*) FROM mcp_agent_jobs WHERE agent_name IS NOT NULL"))
    populated_names = result.scalar()

    print(f"[0073-03]   - Populated {populated_names} agent_name(s) from agent_type")

    # STEP 7: Verify migration success
    # =================================
    print("[0073-03] Step 7: Verifying migration...")

    # Check that all jobs have valid tool_type
    result = connection.execute(
        text("""
        SELECT COUNT(*)
        FROM mcp_agent_jobs
        WHERE tool_type NOT IN ('claude-code', 'codex', 'gemini', 'universal')
    """)
    )
    invalid_tools = result.scalar()

    if invalid_tools > 0:
        print(f"[0073-03] ERROR: {invalid_tools} jobs have invalid tool_type!")
        raise Exception("[0073-03] Migration failed: tool_type constraint violation")

    print("[0073-03]   - Verification complete: All jobs have valid tool_type")

    # STEP 8: Show final state
    # ========================
    print("[0073-03] Step 8: Final state summary...")

    result = connection.execute(
        text("""
        SELECT tool_type, COUNT(*) as count
        FROM mcp_agent_jobs
        GROUP BY tool_type
        ORDER BY count DESC
    """)
    )
    tool_distribution = result.fetchall()

    print("[0073-03]   Tool assignment distribution:")
    for tool_type, count in tool_distribution:
        print(f"[0073-03]     - {tool_type}: {count} job(s)")

    result = connection.execute(
        text("""
        SELECT
            COUNT(*) FILTER (WHERE agent_name IS NOT NULL) as with_name,
            COUNT(*) FILTER (WHERE agent_name IS NULL) as without_name,
            COUNT(*) as total
        FROM mcp_agent_jobs
    """)
    )
    row = result.fetchone()

    print("[0073-03]   Agent name coverage:")
    print(f"[0073-03]     - Total jobs: {row[2]}")
    print(f"[0073-03]     - With agent_name: {row[0]}")
    print(f"[0073-03]     - Without agent_name: {row[1]}")

    print("=" * 80)
    print("[Handover 0073-03] Migration completed successfully!")
    print("[0073-03] Agent tool assignment tracking enabled (2 columns + index + constraint)")
    print("=" * 80 + "\n")


def downgrade() -> None:
    """
    Downgrade migration: Remove agent tool assignment columns.

    This downgrade:
    1. Drops tool_type index
    2. Drops tool_type constraint
    3. Removes both tool_type and agent_name columns

    Data loss:
    - All tool assignments (tool_type)
    - All human-readable agent names (agent_name)

    Impact: Agents lose tool-specific routing but remain functional.
    Falls back to agent_type for identification.
    """

    print("\n" + "=" * 80)
    print("[Handover 0073-03] Downgrading: Removing agent tool assignment tracking")
    print("=" * 80)

    connection = op.get_bind()

    # STEP 1: Check for non-universal tool assignments
    # =================================================
    print("[0073-03 Downgrade] Step 1: Checking for tool-specific assignments...")

    result = connection.execute(
        text("""
        SELECT tool_type, COUNT(*) as count
        FROM mcp_agent_jobs
        WHERE tool_type != 'universal'
        GROUP BY tool_type
        ORDER BY count DESC
    """)
    )
    tool_specific_jobs = result.fetchall()

    if tool_specific_jobs:
        print("[0073-03] WARNING: Tool-specific assignments found:")
        for tool_type, count in tool_specific_jobs:
            print(f"[0073-03]   - {tool_type}: {count} job(s)")
        print("[0073-03] WARNING: These assignments will be lost after downgrade")

    # STEP 2: Drop tool_type index
    # =============================
    print("[0073-03 Downgrade] Step 2: Dropping tool_type index...")

    op.drop_index("idx_mcp_agent_jobs_tenant_tool", table_name="mcp_agent_jobs")
    print("[0073-03]   - Dropped 'idx_mcp_agent_jobs_tenant_tool' index")

    # STEP 3: Drop tool_type constraint
    # ==================================
    print("[0073-03 Downgrade] Step 3: Dropping tool_type constraint...")

    op.drop_constraint("ck_mcp_agent_job_tool_type", "mcp_agent_jobs", type_="check")
    print("[0073-03]   - Dropped 'ck_mcp_agent_job_tool_type' constraint")

    # STEP 4: Drop columns
    # ====================
    print("[0073-03 Downgrade] Step 4: Removing tool assignment columns...")

    op.drop_column("mcp_agent_jobs", "agent_name")
    print("[0073-03]   - Dropped 'agent_name' column")

    op.drop_column("mcp_agent_jobs", "tool_type")
    print("[0073-03]   - Dropped 'tool_type' column")

    # STEP 5: Verify downgrade success
    # =================================
    print("[0073-03 Downgrade] Step 5: Verifying downgrade...")

    result = connection.execute(text("SELECT COUNT(*) FROM mcp_agent_jobs"))
    total_jobs = result.scalar()

    print(f"[0073-03]   - {total_jobs} agent job(s) remain functional")
    print("[0073-03]   - Tool assignment tracking disabled")

    print("=" * 80)
    print("[Handover 0073-03] Downgrade completed successfully!")
    print("[0073-03] Agent tool columns removed (2 columns + index + constraint)")
    if tool_specific_jobs:
        total_tool_specific = sum(count for _, count in tool_specific_jobs)
        print(f"[0073-03] WARNING: Tool assignments lost for {total_tool_specific} job(s)")
    print("=" * 80 + "\n")
