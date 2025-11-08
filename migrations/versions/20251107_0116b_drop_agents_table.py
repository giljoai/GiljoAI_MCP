"""Drop agents table (Handover 0116 final cleanup)

Aligned with: Comprehensive_MCP_Analysis.md
Validates: Agent table uses wrong 4-state model (lines 1171-1181)
          MCPAgentJob uses correct 7-state model (lines 1183-1209)

Revision ID: 0116b_drop_agents
Revises: 0116_remove_fk
Create Date: 2025-11-07

PREREQUISITES (MUST BE TRUE):
- All file migrations complete (no code references agents table)
- All FK constraints removed (migration 0116_remove_fk)
- decommissioned_at field added (migration 0113b_decom_at)
- 7-state system implemented (migration 0113_simplify_7_states)

ARCHITECTURE DECISION:
Agent table: 4-state model (idle, active, completed, failed) ❌ WRONG
MCPAgentJob table: 7-state model (waiting, working, blocked, complete,
                                  failed, cancelled, decommissioned) ✅ CORRECT

Legacy MCP tools query agents table (creates data disconnect) ❌
Modern MCP tools query mcp_agent_jobs table (dashboard-visible) ✅

This migration eliminates the legacy Agent model and makes MCPAgentJob
the single source of truth for all agent state.
"""

from alembic import op
import sqlalchemy as sa
from datetime import datetime, timezone

# revision identifiers, used by Alembic.
revision = '0116b_drop_agents'
down_revision = '0116_remove_fk'
branch_labels = None
depends_on = None


def upgrade():
    """
    Drop agents table after migrating to unified MCPAgentJob model.

    This is the FINAL migration in Handover 0116 cleanup sequence.
    After this migration:
    - agents table no longer exists
    - MCPAgentJob is sole source of truth for agent state
    - Legacy data preserved in agents_backup_final table (30-day retention)
    - All historical agent data migrated to MCPAgentJob.job_metadata
    """

    # Bind to current connection for logging
    bind = op.get_bind()

    print("=" * 80)
    print("HANDOVER 0116: Final Agent Table Drop")
    print("=" * 80)

    # =========================================================================
    # STEP 1: Safety Verification
    # =========================================================================
    print("\nSTEP 1: Running safety checks...")

    # Check 1: Verify FK constraints removed
    result = bind.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.table_constraints
        WHERE constraint_type = 'FOREIGN KEY'
          AND constraint_name LIKE '%agent%'
          AND table_name IN ('messages', 'jobs', 'agent_interactions',
                             'template_usage_stats', 'git_commits',
                             'optimization_metrics')
    """))
    fk_count = result.scalar()

    if fk_count > 0:
        raise Exception(
            f"SAFETY CHECK FAILED: {fk_count} FK constraints still reference agents table. "
            f"Run migration 0116_remove_fk first."
        )

    print(f"  ✓ FK constraints removed: {fk_count} (expected 0)")

    # Check 2: Verify agents table exists
    result = bind.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'agents'
    """))
    table_exists = result.scalar()

    if table_exists == 0:
        print("  ⚠ agents table already dropped - skipping migration")
        return

    print(f"  ✓ agents table exists")

    # Check 3: Verify MCPAgentJob has required fields
    result = bind.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.columns
        WHERE table_name = 'mcp_agent_jobs'
          AND column_name IN ('decommissioned_at', 'failure_reason',
                              'agent_name', 'agent_type', 'job_metadata')
    """))
    required_fields = result.scalar()

    if required_fields < 5:
        raise Exception(
            f"SAFETY CHECK FAILED: MCPAgentJob missing required fields. "
            f"Found {required_fields}/5. Run migrations 0113_simplify_7_states and 0113b_decom_at first."
        )

    print(f"  ✓ MCPAgentJob has required fields: {required_fields}/5")

    # =========================================================================
    # STEP 2: Create Backup Table
    # =========================================================================
    print("\nSTEP 2: Creating agents_backup_final table...")

    # Check if backup already exists
    result = bind.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'agents_backup_final'
    """))
    backup_exists = result.scalar()

    if backup_exists > 0:
        print("  ⚠ Backup table already exists - dropping and recreating...")
        bind.execute(sa.text("DROP TABLE agents_backup_final"))

    # Create backup
    bind.execute(sa.text("""
        CREATE TABLE agents_backup_final AS
        SELECT * FROM agents
    """))

    # Count backed up records
    result = bind.execute(sa.text("SELECT COUNT(*) FROM agents_backup_final"))
    backup_count = result.scalar()
    print(f"  ✓ Created backup with {backup_count} records")

    # Add metadata comment
    bind.execute(sa.text("""
        COMMENT ON TABLE agents_backup_final IS
        'Backup of agents table before Handover 0116 drop. Created 2025-11-07. Safe to drop after 2025-12-07 (30 days).'
    """))
    print("  ✓ Added retention metadata (30-day retention)")

    # =========================================================================
    # STEP 3: Migrate Legacy Data to MCPAgentJob
    # =========================================================================
    print("\nSTEP 3: Migrating legacy Agent data to MCPAgentJob.job_metadata...")

    # Migrate agent data to job_metadata for agents with job_id
    result = bind.execute(sa.text("""
        UPDATE mcp_agent_jobs j
        SET job_metadata = jsonb_set(
            COALESCE(job_metadata, '{}'::jsonb),
            '{legacy_agent_data}',
            jsonb_build_object(
                'agent_id', a.id,
                'legacy_status', a.status,
                'context_used', a.context_used,
                'last_active', a.last_active::text,
                'meta_data', COALESCE(a.meta_data::jsonb, '{}'::jsonb),
                'migrated_at', NOW()::text
            )
        )
        FROM agents a
        WHERE j.job_id = a.job_id
          AND a.job_id IS NOT NULL
          AND j.job_metadata->>'legacy_agent_data' IS NULL
    """))
    migrated_count = result.rowcount
    print(f"  ✓ Migrated {migrated_count} agent records to MCPAgentJob.job_metadata")

    # Count orphaned agents (no job_id)
    result = bind.execute(sa.text("""
        SELECT COUNT(*) FROM agents WHERE job_id IS NULL
    """))
    orphaned_count = result.scalar()

    if orphaned_count > 0:
        print(f"  ⚠ Found {orphaned_count} orphaned agents (no job_id) - preserved in backup only")

    # =========================================================================
    # STEP 4: Drop Agents Table
    # =========================================================================
    print("\nSTEP 4: Dropping agents table...")

    op.drop_table('agents')
    print("  ✓ agents table dropped")

    # =========================================================================
    # STEP 5: Final Verification
    # =========================================================================
    print("\nSTEP 5: Final verification...")

    # Verify table dropped
    result = bind.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'agents'
    """))
    remaining = result.scalar()

    if remaining > 0:
        raise Exception("SAFETY CHECK FAILED: agents table still exists after drop")

    print("  ✓ agents table no longer exists")

    # Verify backup exists
    result = bind.execute(sa.text("""
        SELECT COUNT(*) FROM information_schema.tables
        WHERE table_name = 'agents_backup_final'
    """))
    backup_exists = result.scalar()

    if backup_exists == 0:
        raise Exception("SAFETY CHECK FAILED: agents_backup_final table missing")

    print("  ✓ Backup table exists")

    # Verify backup record count matches
    result = bind.execute(sa.text("SELECT COUNT(*) FROM agents_backup_final"))
    final_backup_count = result.scalar()

    if final_backup_count != backup_count:
        raise Exception(
            f"SAFETY CHECK FAILED: Backup record count mismatch "
            f"({final_backup_count} != {backup_count})"
        )

    print(f"  ✓ Backup record count verified: {final_backup_count}")

    # Count migrated data in MCPAgentJob
    result = bind.execute(sa.text("""
        SELECT COUNT(*) FROM mcp_agent_jobs
        WHERE job_metadata->'legacy_agent_data' IS NOT NULL
    """))
    jobs_with_legacy = result.scalar()
    print(f"  ✓ MCPAgentJob records with legacy data: {jobs_with_legacy}")

    # =========================================================================
    # Summary
    # =========================================================================
    print("\n" + "=" * 80)
    print("MIGRATION COMPLETE")
    print("=" * 80)
    print(f"  Records backed up:        {backup_count}")
    print(f"  Records migrated:         {migrated_count}")
    print(f"  Orphaned agents:          {orphaned_count}")
    print(f"  MCPAgentJob w/ legacy:    {jobs_with_legacy}")
    print()
    print("  ✓ agents table dropped successfully")
    print("  ✓ Backup preserved in agents_backup_final (30-day retention)")
    print("  ✓ Legacy data migrated to MCPAgentJob.job_metadata")
    print("  ✓ MCPAgentJob is now sole source of truth for agent state")
    print()
    print("NEXT STEPS:")
    print("  1. Remove Agent model from src/giljo_mcp/models.py")
    print("  2. Remove legacy agent tools from src/giljo_mcp/tools/")
    print("  3. Update imports across codebase")
    print("  4. Run test suite to verify no regressions")
    print("=" * 80 + "\n")


def downgrade():
    """
    CANNOT DOWNGRADE - Data migration is one-way.

    To restore agents table manually (NOT RECOMMENDED):
    1. CREATE TABLE agents AS SELECT * FROM agents_backup_final;
    2. Restore FK constraints (run 0116_remove_fk downgrade)
    3. Restore file code to use Agent model (git revert)
    4. Update MCPAgentJob records to point to restored agents

    WARNING: This will cause severe data inconsistencies!

    The agents table uses a DEPRECATED 4-state model that is incompatible
    with the modern 7-state MCPAgentJob model. Restoring it will break
    orchestrator coordination and dashboard visibility.

    RECOMMENDATION: Do not downgrade. If you must rollback, restore from
    database backup taken before running this migration.
    """
    raise RuntimeError(
        "CANNOT DOWNGRADE - agents table drop is irreversible.\n\n"
        "Downgrading this migration would cause severe data inconsistencies "
        "because the agents table uses a deprecated 4-state model that is "
        "incompatible with the modern 7-state MCPAgentJob model.\n\n"
        "If you absolutely must restore the agents table:\n"
        "1. Restore from full database backup taken before this migration\n"
        "2. Run: CREATE TABLE agents AS SELECT * FROM agents_backup_final;\n"
        "3. Run migration 0116_remove_fk downgrade (will fail due to NULL values)\n"
        "4. Manually restore code files (git revert)\n\n"
        "RECOMMENDATION: Do not attempt this. The agents table is deprecated.\n"
        "Contact development team if you encounter issues."
    )
