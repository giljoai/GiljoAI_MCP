-- ============================================================================
-- Pre-Migration Verification for 0116b_drop_agents_table
-- ============================================================================
-- Purpose: Verify all prerequisites are met before dropping agents table
-- Required: All checks must pass (return expected values) before running migration
-- Usage: psql -U postgres -d giljo_mcp -f scripts/0116b_pre_migration_verification.sql
-- ============================================================================

\echo '============================================================================'
\echo 'HANDOVER 0116b: Pre-Migration Verification'
\echo '============================================================================'
\echo ''

-- ============================================================================
-- CHECK 1: FK Constraints Removed
-- ============================================================================
\echo 'CHECK 1: Verify FK constraints removed'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS fk_constraints_remaining,
    CASE
        WHEN COUNT(*) = 0 THEN '✓ PASS - All FK constraints removed'
        ELSE '✗ FAIL - FK constraints still exist (run 0116_remove_fk migration)'
    END AS status
FROM information_schema.table_constraints
WHERE constraint_type = 'FOREIGN KEY'
  AND constraint_name LIKE '%agent%'
  AND table_name IN ('messages', 'jobs', 'agent_interactions',
                     'template_usage_stats', 'git_commits',
                     'optimization_metrics');

\echo ''

-- ============================================================================
-- CHECK 2: Agents Table Exists
-- ============================================================================
\echo 'CHECK 2: Verify agents table exists'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS agents_table_exists,
    CASE
        WHEN COUNT(*) = 1 THEN '✓ PASS - agents table exists'
        ELSE '✗ FAIL - agents table already dropped or missing'
    END AS status
FROM information_schema.tables
WHERE table_name = 'agents';

\echo ''

-- ============================================================================
-- CHECK 3: Agent Record Counts
-- ============================================================================
\echo 'CHECK 3: Count Agent records (for backup verification)'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS total_agents,
    COUNT(CASE WHEN job_id IS NOT NULL THEN 1 END) AS agents_with_job_id,
    COUNT(CASE WHEN job_id IS NULL THEN 1 END) AS orphaned_agents,
    CASE
        WHEN COUNT(*) > 0 THEN '✓ INFO - ' || COUNT(*) || ' agents will be backed up'
        ELSE '✓ INFO - No agents to back up'
    END AS status
FROM agents;

\echo ''

-- ============================================================================
-- CHECK 4: MCPAgentJob Required Fields
-- ============================================================================
\echo 'CHECK 4: Verify MCPAgentJob has required fields'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS required_fields_count,
    CASE
        WHEN COUNT(*) = 5 THEN '✓ PASS - MCPAgentJob has all required fields'
        ELSE '✗ FAIL - MCPAgentJob missing fields (run 0113 migrations)'
    END AS status
FROM information_schema.columns
WHERE table_name = 'mcp_agent_jobs'
  AND column_name IN ('decommissioned_at', 'failure_reason',
                      'agent_name', 'agent_type', 'job_metadata');

\echo ''
\echo 'Required fields detail:'
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'mcp_agent_jobs'
  AND column_name IN ('decommissioned_at', 'failure_reason',
                      'agent_name', 'agent_type', 'job_metadata')
ORDER BY column_name;

\echo ''

-- ============================================================================
-- CHECK 5: MCPAgentJob Record Counts
-- ============================================================================
\echo 'CHECK 5: MCPAgentJob record statistics'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS total_jobs,
    COUNT(CASE WHEN status = 'complete' THEN 1 END) AS complete_jobs,
    COUNT(CASE WHEN status = 'failed' THEN 1 END) AS failed_jobs,
    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) AS cancelled_jobs,
    COUNT(CASE WHEN status = 'decommissioned' THEN 1 END) AS decommissioned_jobs,
    COUNT(CASE WHEN status IN ('waiting', 'working', 'blocked') THEN 1 END) AS active_jobs,
    '✓ INFO - MCPAgentJob status breakdown' AS status
FROM mcp_agent_jobs;

\echo ''

-- ============================================================================
-- CHECK 6: Data Alignment (Agents with matching MCPAgentJob)
-- ============================================================================
\echo 'CHECK 6: Verify Agent-to-MCPAgentJob alignment'
\echo '----------------------------------------'

WITH alignment AS (
    SELECT
        COUNT(*) FILTER (WHERE a.job_id IS NOT NULL AND j.job_id IS NOT NULL) AS matched_agents,
        COUNT(*) FILTER (WHERE a.job_id IS NOT NULL AND j.job_id IS NULL) AS orphaned_agents,
        COUNT(*) FILTER (WHERE a.job_id IS NULL) AS agents_without_job_id
    FROM agents a
    LEFT JOIN mcp_agent_jobs j ON j.job_id = a.job_id
)
SELECT
    matched_agents,
    orphaned_agents,
    agents_without_job_id,
    CASE
        WHEN orphaned_agents = 0 THEN '✓ PASS - All agents with job_id have matching MCPAgentJob'
        ELSE '⚠ WARNING - ' || orphaned_agents || ' agents have job_id but no matching MCPAgentJob'
    END AS status
FROM alignment;

\echo ''

-- ============================================================================
-- CHECK 7: Backup Table Status
-- ============================================================================
\echo 'CHECK 7: Check if backup table already exists'
\echo '----------------------------------------'

SELECT
    COUNT(*) AS backup_table_exists,
    CASE
        WHEN COUNT(*) = 0 THEN '✓ PASS - No existing backup (will be created fresh)'
        ELSE '⚠ WARNING - Backup already exists (will be overwritten)'
    END AS status
FROM information_schema.tables
WHERE table_name = 'agents_backup_final';

\echo ''

-- ============================================================================
-- CHECK 8: Agent-Job Relationship Detail
-- ============================================================================
\echo 'CHECK 8: Agent-Job relationship breakdown'
\echo '----------------------------------------'

SELECT
    a.status AS agent_status,
    j.status AS mcp_job_status,
    COUNT(*) AS count
FROM agents a
LEFT JOIN mcp_agent_jobs j ON j.job_id = a.job_id
GROUP BY a.status, j.status
ORDER BY a.status, j.status;

\echo ''

-- ============================================================================
-- FINAL SUMMARY
-- ============================================================================
\echo '============================================================================'
\echo 'FINAL SUMMARY'
\echo '============================================================================'

WITH checks AS (
    SELECT
        -- Check 1: FK constraints
        (SELECT COUNT(*) FROM information_schema.table_constraints
         WHERE constraint_type = 'FOREIGN KEY'
           AND constraint_name LIKE '%agent%'
           AND table_name IN ('messages', 'jobs', 'agent_interactions',
                              'template_usage_stats', 'git_commits',
                              'optimization_metrics')) = 0 AS fk_removed,

        -- Check 2: Agents table exists
        (SELECT COUNT(*) FROM information_schema.tables
         WHERE table_name = 'agents') = 1 AS agents_exists,

        -- Check 4: MCPAgentJob fields
        (SELECT COUNT(*) FROM information_schema.columns
         WHERE table_name = 'mcp_agent_jobs'
           AND column_name IN ('decommissioned_at', 'failure_reason',
                               'agent_name', 'agent_type', 'job_metadata')) = 5 AS fields_exist
)
SELECT
    CASE WHEN fk_removed THEN '✓' ELSE '✗' END AS fk_check,
    CASE WHEN agents_exists THEN '✓' ELSE '✗' END AS table_check,
    CASE WHEN fields_exist THEN '✓' ELSE '✗' END AS fields_check,
    CASE
        WHEN fk_removed AND agents_exists AND fields_exist THEN
            '✓✓✓ ALL CHECKS PASSED - Safe to run migration 0116b_drop_agents_table'
        ELSE
            '✗✗✗ CHECKS FAILED - DO NOT run migration until issues resolved'
    END AS final_status
FROM checks;

\echo ''
\echo 'To run migration:'
\echo '  cd F:/GiljoAI_MCP'
\echo '  alembic upgrade 0116b_drop_agents'
\echo ''
\echo '============================================================================'
