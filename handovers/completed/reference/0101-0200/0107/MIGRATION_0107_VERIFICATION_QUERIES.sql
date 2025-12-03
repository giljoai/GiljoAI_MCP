-- ============================================================================
-- HANDOVER 0107: Agent Monitoring & Graceful Cancellation
-- Database Migration Verification Queries
-- ============================================================================
-- These queries were used to verify the migration was successfully applied
-- ============================================================================

-- ============================================================================
-- 1. VERIFY MIGRATION WAS RECORDED
-- ============================================================================

SELECT 'Check if migration 20251106_agent_monitoring is recorded:' as check_name;
SELECT version_num FROM alembic_version WHERE version_num = '20251106_agent_monitoring';
-- Expected: Returns one row with version_num = '20251106_agent_monitoring'


-- ============================================================================
-- 2. VERIFY NEW COLUMNS EXIST
-- ============================================================================

SELECT 'Verify new columns in mcp_agent_jobs table:' as check_name;
SELECT 
  column_name, 
  data_type, 
  is_nullable,
  ordinal_position
FROM information_schema.columns 
WHERE table_name = 'mcp_agent_jobs' 
AND column_name IN ('last_progress_at', 'last_message_check_at')
ORDER BY ordinal_position;
-- Expected: Two rows
--   - last_progress_at | timestamp with time zone | YES | 43
--   - last_message_check_at | timestamp with time zone | YES | 44


-- ============================================================================
-- 3. VERIFY STATUS CONSTRAINT INCLUDES 'CANCELLING'
-- ============================================================================

SELECT 'Verify cancelling status in constraint:' as check_name;
SELECT pg_get_constraintdef(oid) 
FROM pg_constraint 
WHERE conname = 'ck_mcp_agent_job_status' 
AND conrelid = 'mcp_agent_jobs'::regclass;
-- Expected: Includes 'cancelling' in the array of allowed status values


-- ============================================================================
-- 4. TABLE STRUCTURE VERIFICATION
-- ============================================================================

SELECT 'Count total columns in mcp_agent_jobs:' as check_name;
SELECT count(*) as total_columns FROM information_schema.columns 
WHERE table_name = 'mcp_agent_jobs';
-- Expected: 33 columns (including new last_progress_at and last_message_check_at)


SELECT 'Count check constraints on mcp_agent_jobs:' as check_name;
SELECT count(*) as check_constraints FROM information_schema.table_constraints 
WHERE table_name = 'mcp_agent_jobs' AND constraint_type = 'CHECK';
-- Expected: 19 check constraints


-- ============================================================================
-- 5. DATA INTEGRITY TEST: INSERT WITH NEW FIELDS
-- ============================================================================

-- Insert test job with new monitoring fields
INSERT INTO mcp_agent_jobs (
    tenant_key, job_id, agent_type, mission, status, 
    progress, tool_type, instance_number, context_used, 
    context_budget, job_metadata, health_status, health_failure_count,
    last_progress_at, last_message_check_at
) VALUES (
    'test_tenant', 'test_job_0107_verify', 'orchestrator',
    'Test mission for Handover 0107 migration',
    'waiting', 0, 'universal', 1, 0, 150000,
    '{"test": true}'::jsonb, 'healthy', 0,
    now(), now()
)
RETURNING id, job_id, status, last_progress_at, last_message_check_at;
-- Expected: Successfully returns row with both timestamp fields populated


-- ============================================================================
-- 6. DATA INTEGRITY TEST: UPDATE TIMESTAMP FIELDS
-- ============================================================================

UPDATE mcp_agent_jobs 
SET last_progress_at = now() - interval '5 minutes', 
    last_message_check_at = now() - interval '2 minutes'
WHERE job_id = 'test_job_0107_verify'
RETURNING job_id, last_progress_at, last_message_check_at;
-- Expected: Successfully updates both timestamp fields with new values


-- ============================================================================
-- 7. DATA INTEGRITY TEST: GRACEFUL CANCELLATION STATUS
-- ============================================================================

UPDATE mcp_agent_jobs 
SET status = 'cancelling'
WHERE job_id = 'test_job_0107_verify'
RETURNING job_id, status;
-- Expected: Successfully sets status to 'cancelling' without constraint error


-- ============================================================================
-- 8. DATA INTEGRITY TEST: COMPREHENSIVE QUERY
-- ============================================================================

SELECT 'Final verification - retrieve all new fields together:' as check_name;
SELECT job_id, status, last_progress_at, last_message_check_at 
FROM mcp_agent_jobs 
WHERE job_id = 'test_job_0107_verify';
-- Expected: One row with cancelling status and both timestamp fields


-- ============================================================================
-- 9. CLEANUP: REMOVE TEST DATA
-- ============================================================================

DELETE FROM mcp_agent_jobs WHERE job_id = 'test_job_0107_verify';
-- Expected: Deletes 1 row


-- ============================================================================
-- 10. MONITORING QUERIES - READY FOR PRODUCTION
-- ============================================================================

-- Monitor agent activity (find inactive agents)
SELECT 'Find agents without recent progress:' as monitoring_query;
SELECT job_id, agent_type, status, last_progress_at
FROM mcp_agent_jobs
WHERE tenant_key = 'your_tenant'
AND last_progress_at < now() - interval '5 minutes'
ORDER BY last_progress_at DESC;


-- Find agents that haven't checked messages recently
SELECT 'Find agents without recent message checks:' as monitoring_query;
SELECT job_id, agent_type, status, last_message_check_at
FROM mcp_agent_jobs
WHERE tenant_key = 'your_tenant'
AND last_message_check_at < now() - interval '10 seconds'
ORDER BY last_message_check_at DESC;


-- Check graceful cancellation queue
SELECT 'Check graceful cancellation queue:' as monitoring_query;
SELECT job_id, agent_type, status, created_at
FROM mcp_agent_jobs
WHERE tenant_key = 'your_tenant'
AND status = 'cancelling'
ORDER BY created_at DESC;


-- ============================================================================
-- 11. PERFORMANCE MONITORING
-- ============================================================================

-- Check table size impact
SELECT 'Table size and row count:' as performance_check;
SELECT 
  (SELECT count(*) FROM mcp_agent_jobs) as total_rows,
  pg_size_pretty(pg_total_relation_size('mcp_agent_jobs'::regclass)) as table_size;


-- ============================================================================
-- 12. POTENTIAL INDEX RECOMMENDATIONS (Optional)
-- ============================================================================

-- If you frequently query by agent progress timestamps:
-- CREATE INDEX idx_agent_progress 
-- ON mcp_agent_jobs(tenant_key, last_progress_at);

-- If you frequently query by message check timestamps:
-- CREATE INDEX idx_agent_messages 
-- ON mcp_agent_jobs(tenant_key, last_message_check_at);

-- If you frequently query agents in cancelling status:
-- CREATE INDEX idx_cancelling_status 
-- ON mcp_agent_jobs(tenant_key, status) 
-- WHERE status = 'cancelling';


-- ============================================================================
-- 13. ROLLBACK PROCEDURE (if needed)
-- ============================================================================

-- To rollback this migration, execute in order:

-- 1. Drop constraint with 'cancelling' state
-- ALTER TABLE mcp_agent_jobs 
--   DROP CONSTRAINT ck_mcp_agent_job_status;

-- 2. Recreate constraint without 'cancelling' state
-- ALTER TABLE mcp_agent_jobs 
--   ADD CONSTRAINT ck_mcp_agent_job_status 
--   CHECK (status IN ('waiting', 'preparing', 'active', 'working', 
--                     'review', 'complete', 'failed', 'blocked'));

-- 3. Drop last_message_check_at column
-- ALTER TABLE mcp_agent_jobs DROP COLUMN last_message_check_at;

-- 4. Drop last_progress_at column
-- ALTER TABLE mcp_agent_jobs DROP COLUMN last_progress_at;

-- 5. Remove migration record
-- DELETE FROM alembic_version 
-- WHERE version_num = '20251106_agent_monitoring';

-- OR use Alembic:
-- alembic downgrade 8cd632d27c5e

-- ============================================================================
-- END OF VERIFICATION QUERIES
-- ============================================================================
