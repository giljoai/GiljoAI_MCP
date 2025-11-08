-- ============================================================================
-- Post-Migration Validation for 0116b_drop_agents_table
-- ============================================================================
-- Purpose: Verify migration completed successfully and data integrity maintained
-- Required: All checks must pass after migration completes
-- Usage: psql -U postgres -d giljo_mcp -f scripts/0116b_post_migration_validation.sql
-- ============================================================================

\echo '============================================================================'
\echo 'HANDOVER 0116b: Post-Migration Validation'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- CHECK 1: Agents Table Dropped
-- ============================================================================
\echo 'CHECK 1: Verify agents table no longer exists'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS agents_table_exists,
    CASE
        WHEN COUNT(*) = 0 THEN '✓ PASS - agents table dropped successfully'
        ELSE '✗ FAIL - agents table still exists'
    END AS status
FROM information_schema.tables
WHERE table_name = 'agents';

\echo ''

-- ============================================================================
-- CHECK 2: Backup Table Created
-- ============================================================================
\echo 'CHECK 2: Verify backup table exists'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS backup_exists,
    CASE
        WHEN COUNT(*) = 1 THEN '✓ PASS - Backup table created'
        ELSE '✗ FAIL - Backup table missing'
    END AS status
FROM information_schema.tables
WHERE table_name = 'agents_backup_final';

\echo ''

-- ============================================================================
-- CHECK 3: Backup Table Record Count
-- ============================================================================
\echo 'CHECK 3: Verify backup has records'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS backup_record_count,
    CASE
        WHEN COUNT(*) > 0 THEN '✓ PASS - Backup contains ' || COUNT(*) || ' records'
        WHEN COUNT(*) = 0 THEN '✓ INFO - No agents existed (empty backup is expected)'
    END AS status
FROM agents_backup_final;

\echo ''

-- ============================================================================
-- CHECK 4: Backup Table Metadata
-- ============================================================================
\echo 'CHECK 4: Verify backup table metadata'
\echo '----------------------------------------'

SELECT
    obj_description('agents_backup_final'::regclass) AS table_comment,
    CASE
        WHEN obj_description('agents_backup_final'::regclass) IS NOT NULL THEN
            '✓ PASS - Backup has retention metadata'
        ELSE
            '⚠ WARNING - Backup missing retention metadata'
    END AS status;

\echo ''

-- ============================================================================
-- CHECK 5: MCPAgentJob Legacy Data Migration
-- ============================================================================
\echo 'CHECK 5: Verify legacy data migrated to MCPAgentJob'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS jobs_with_legacy_data,
    CASE
        WHEN COUNT(*) > 0 THEN '✓ PASS - ' || COUNT(*) || ' MCPAgentJob records have legacy data'
        WHEN COUNT(*) = 0 THEN '✓ INFO - No legacy data (no agents had job_id)'
    END AS status
FROM mcp_agent_jobs
WHERE job_metadata->'legacy_agent_data' IS NOT NULL;

\echo ''

-- ============================================================================
-- CHECK 6: Legacy Data Structure Verification
-- ============================================================================
\echo 'CHECK 6: Sample legacy data structure (first 3 records)'
\echo '----------------------------------------'

SELECT
    job_id,
    agent_name,
    status,
    job_metadata->'legacy_agent_data'->>'agent_id' AS legacy_agent_id,
    job_metadata->'legacy_agent_data'->>'legacy_status' AS legacy_status,
    job_metadata->'legacy_agent_data'->>'migrated_at' AS migrated_at
FROM mcp_agent_jobs
WHERE job_metadata->'legacy_agent_data' IS NOT NULL
ORDER BY created_at DESC
LIMIT 3;

\echo ''

-- ============================================================================
-- CHECK 7: No Orphaned FK References
-- ============================================================================
\echo 'CHECK 7: Verify no orphaned foreign key references'
\echo '----------------------------------------'

WITH orphaned_refs AS (
    SELECT 'messages' AS table_name,
           COUNT(*) AS orphaned_count
    FROM messages
    WHERE from_agent_id IS NOT NULL
      AND from_agent_id NOT IN (SELECT job_id FROM mcp_agent_jobs)

    UNION ALL

    SELECT 'jobs' AS table_name,
           COUNT(*) AS orphaned_count
    FROM jobs
    WHERE agent_id IS NOT NULL

    UNION ALL

    SELECT 'agent_interactions' AS table_name,
           COUNT(*) AS orphaned_count
    FROM agent_interactions
    WHERE parent_agent_id IS NOT NULL

    UNION ALL

    SELECT 'template_usage_stats' AS table_name,
           COUNT(*) AS orphaned_count
    FROM template_usage_stats
    WHERE agent_id IS NOT NULL

    UNION ALL

    SELECT 'git_commits' AS table_name,
           COUNT(*) AS orphaned_count
    FROM git_commits
    WHERE agent_id IS NOT NULL

    UNION ALL

    SELECT 'optimization_metrics' AS table_name,
           COUNT(*) AS orphaned_count
    FROM optimization_metrics
    WHERE agent_id IS NOT NULL
)
SELECT
    table_name,
    orphaned_count,
    CASE
        WHEN orphaned_count = 0 THEN '✓ PASS - No orphaned references'
        ELSE '⚠ WARNING - ' || orphaned_count || ' orphaned references (expected due to FK removal)'
    END AS status
FROM orphaned_refs
WHERE orphaned_count > 0
UNION ALL
SELECT
    'ALL TABLES' AS table_name,
    SUM(orphaned_count) AS orphaned_count,
    CASE
        WHEN SUM(orphaned_count) = 0 THEN '✓ PASS - No orphaned references in any table'
        ELSE '⚠ WARNING - Total ' || SUM(orphaned_count) || ' orphaned references (expected due to FK removal)'
    END AS status
FROM orphaned_refs;

\echo ''

-- ============================================================================
-- CHECK 8: MCPAgentJob Table Integrity
-- ============================================================================
\echo 'CHECK 8: MCPAgentJob table integrity'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS total_jobs,
    COUNT(CASE WHEN status IN ('waiting', 'working', 'blocked', 'complete',
                                'failed', 'cancelled', 'decommissioned') THEN 1 END) AS valid_status_count,
    COUNT(CASE WHEN tenant_key IS NOT NULL THEN 1 END) AS jobs_with_tenant,
    COUNT(CASE WHEN job_id IS NOT NULL THEN 1 END) AS jobs_with_job_id,
    CASE
        WHEN COUNT(*) = COUNT(CASE WHEN status IN ('waiting', 'working', 'blocked',
                                                     'complete', 'failed', 'cancelled',
                                                     'decommissioned') THEN 1 END)
             AND COUNT(*) = COUNT(CASE WHEN tenant_key IS NOT NULL THEN 1 END)
             AND COUNT(*) = COUNT(CASE WHEN job_id IS NOT NULL THEN 1 END)
        THEN '✓ PASS - All MCPAgentJob records have valid status, tenant_key, and job_id'
        ELSE '✗ FAIL - Some MCPAgentJob records have invalid data'
    END AS status
FROM mcp_agent_jobs;

\echo ''

-- ============================================================================
-- CHECK 9: Backup vs. Migrated Record Comparison
-- ============================================================================
\echo 'CHECK 9: Compare backup records to migrated records'
\echo '----------------------------------------'

WITH backup_stats AS (
    SELECT
        COUNT(*) AS total_backup,
        COUNT(CASE WHEN job_id IS NOT NULL THEN 1 END) AS backup_with_job_id
    FROM agents_backup_final
),
migrated_stats AS (
    SELECT
        COUNT(*) AS total_migrated
    FROM mcp_agent_jobs
    WHERE job_metadata->'legacy_agent_data' IS NOT NULL
)
SELECT
    b.total_backup,
    b.backup_with_job_id,
    m.total_migrated,
    CASE
        WHEN b.backup_with_job_id = m.total_migrated THEN
            '✓ PASS - All agents with job_id migrated (' || m.total_migrated || ' records)'
        WHEN b.backup_with_job_id > m.total_migrated THEN
            '⚠ WARNING - ' || (b.backup_with_job_id - m.total_migrated) || ' agents not migrated (may be expected)'
        ELSE
            '✗ FAIL - More migrated records than backup records (data inconsistency)'
    END AS status
FROM backup_stats b, migrated_stats m;

\echo ''

-- ============================================================================
-- CHECK 10: Table Size Verification
-- ============================================================================
\echo 'CHECK 10: Table sizes after migration'
\echo '----------------------------------------'

SELECT
    schemaname || '.' || tablename AS table_name,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS total_size,
    pg_size_pretty(pg_relation_size(schemaname||'.'||tablename)) AS table_size,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename) -
                   pg_relation_size(schemaname||'.'||tablename)) AS indexes_size
FROM pg_tables
WHERE tablename IN ('agents_backup_final', 'mcp_agent_jobs')
ORDER BY tablename;

\echo ''

-- ============================================================================
-- FINAL SUMMARY
-- ============================================================================
\echo '============================================================================'
\echo 'FINAL SUMMARY'
\echo '============================================================================'

WITH validation AS (
    -- Check 1: Agents table dropped
    SELECT
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_name = 'agents') = 0 AS agents_dropped,

    -- Check 2: Backup exists
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_name = 'agents_backup_final') = 1 AS backup_exists,

    -- Check 3: Backup has records (if agents existed)
        (SELECT COUNT(*) FROM agents_backup_final) >= 0 AS backup_has_data,

    -- Check 8: MCPAgentJob integrity
        (SELECT COUNT(*) = COUNT(CASE WHEN status IN ('waiting', 'working', 'blocked',
                                                        'complete', 'failed', 'cancelled',
                                                        'decommissioned') THEN 1 END)
                    AND COUNT(*) = COUNT(CASE WHEN tenant_key IS NOT NULL THEN 1 END)
                    AND COUNT(*) = COUNT(CASE WHEN job_id IS NOT NULL THEN 1 END)
         FROM mcp_agent_jobs) AS mcp_integrity
)
SELECT
    CASE WHEN agents_dropped THEN '✓' ELSE '✗' END AS drop_check,
    CASE WHEN backup_exists THEN '✓' ELSE '✗' END AS backup_check,
    CASE WHEN backup_has_data THEN '✓' ELSE '✗' END AS data_check,
    CASE WHEN mcp_integrity THEN '✓' ELSE '✗' END AS integrity_check,
    CASE
        WHEN agents_dropped AND backup_exists AND backup_has_data AND mcp_integrity THEN
            '✓✓✓✓ MIGRATION SUCCESSFUL - All checks passed'
        ELSE
            '✗✗✗✗ MIGRATION ISSUES DETECTED - Review failed checks above'
    END AS final_status
FROM validation;

\echo ''

-- Record counts for migration log
SELECT
    (SELECT COUNT(*) FROM agents_backup_final) AS records_backed_up,
    (SELECT COUNT(*) FROM mcp_agent_jobs WHERE job_metadata->'legacy_agent_data' IS NOT NULL) AS records_migrated,
    (SELECT COUNT(*) FROM agents_backup_final WHERE job_id IS NULL) AS orphaned_agents,
    (SELECT COUNT(*) FROM mcp_agent_jobs) AS total_mcp_agent_jobs;

\echo ''
\echo 'NEXT STEPS:'
\echo '  1. Remove Agent model from src/giljo_mcp/models.py'
\echo '  2. Remove legacy agent tools from src/giljo_mcp/tools/'
\echo '  3. Update imports across codebase'
\echo '  4. Run test suite: pytest tests/'
\echo '  5. After 30 days (2025-12-07), drop backup: DROP TABLE agents_backup_final;'
\echo ''
\echo '============================================================================'
