-- Handover 0088 Migration Verification SQL
-- Verifies that the job_metadata column was added correctly to mcp_agent_jobs table

-- 1. Check if job_metadata column exists
SELECT 
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'mcp_agent_jobs'
AND column_name = 'job_metadata';

-- Expected output:
-- column_name   | data_type | is_nullable | column_default
-- job_metadata  | jsonb     | NO          | '{}'::jsonb


-- 2. Check if GIN index exists on job_metadata column
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'mcp_agent_jobs'
AND indexname = 'idx_mcp_agent_jobs_job_metadata';

-- Expected output:
-- indexname                       | indexdef
-- idx_mcp_agent_jobs_job_metadata | CREATE INDEX idx_mcp_agent_jobs_job_metadata ON public.mcp_agent_jobs USING gin (job_metadata)


-- 3. Verify job_metadata column default value
SELECT 
    job_id,
    agent_type,
    job_metadata
FROM mcp_agent_jobs
LIMIT 5;

-- Expected: job_metadata should be {} for rows that don't have metadata set


-- 4. Test JSONB query performance (should use GIN index)
EXPLAIN (ANALYZE, BUFFERS)
SELECT job_id, agent_type
FROM mcp_agent_jobs
WHERE job_metadata @> '{"tool": "claude-code"}'::jsonb;

-- Expected: Query plan should show "Bitmap Index Scan on idx_mcp_agent_jobs_job_metadata"


-- 5. Verify multi-tenant isolation (job_metadata doesn't leak across tenants)
SELECT 
    tenant_key,
    COUNT(*) as job_count,
    COUNT(CASE WHEN job_metadata != '{}' THEN 1 END) as jobs_with_metadata
FROM mcp_agent_jobs
GROUP BY tenant_key;

-- Expected: Each tenant should have isolated job_metadata


-- 6. Check data migration (thin client data moved from handover_summary to job_metadata)
SELECT 
    job_id,
    agent_type,
    handover_summary ? 'field_priorities' as has_old_field_priorities,
    job_metadata ? 'field_priorities' as has_new_field_priorities,
    handover_summary ? 'project_status' as has_succession_data
FROM mcp_agent_jobs
WHERE handover_summary IS NOT NULL
LIMIT 10;

-- Expected: Thin client data (field_priorities, user_id, tool) should be in job_metadata
-- Succession data (project_status, active_agents) should remain in handover_summary


-- 7. Verify NOT NULL constraint
INSERT INTO mcp_agent_jobs (
    tenant_key, project_id, job_id, agent_type, mission, job_metadata
) VALUES (
    'test-tenant', 'test-project', 'test-job', 'orchestrator', 'test mission', NULL
);
-- Expected: ERROR: null value in column "job_metadata" violates not-null constraint


-- 8. Test JSONB operations
-- Test setting and retrieving nested data
UPDATE mcp_agent_jobs
SET job_metadata = jsonb_set(
    job_metadata,
    '{field_priorities}',
    '{"vision": 10, "architecture": 8}'::jsonb
)
WHERE job_id = (SELECT job_id FROM mcp_agent_jobs LIMIT 1);

-- Verify
SELECT 
    job_id,
    job_metadata->'field_priorities'->'vision' as vision_priority
FROM mcp_agent_jobs
WHERE job_metadata @> '{"field_priorities": {}}'::jsonb
LIMIT 1;

-- Expected: vision_priority = 10


-- 9. Performance test: Query by metadata field
SELECT 
    COUNT(*) as claude_code_jobs
FROM mcp_agent_jobs
WHERE job_metadata->>'tool' = 'claude-code';

-- Should execute quickly with GIN index


-- 10. Rollback test (verify migration idempotency)
-- This should NOT cause errors if run multiple times
ALTER TABLE mcp_agent_jobs
ADD COLUMN IF NOT EXISTS job_metadata JSONB DEFAULT '{}'::jsonb NOT NULL;

CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_job_metadata
ON mcp_agent_jobs USING gin(job_metadata);

-- Expected: No errors, column already exists
