-- Handover 0080: Orchestrator Succession Architecture
-- Migration Verification SQL Queries
-- Database: giljo_mcp (PostgreSQL 18)

-- ============================================================================
-- VERIFICATION 1: Check Column Existence
-- ============================================================================
-- Purpose: Verify all 7 new columns were added successfully
-- Expected: 7 rows returned (instance_number, handover_to, handover_summary,
--           handover_context_refs, succession_reason, context_used, context_budget)

SELECT
    column_name,
    data_type,
    is_nullable,
    column_default
FROM information_schema.columns
WHERE table_name = 'mcp_agent_jobs'
  AND column_name IN (
      'instance_number',
      'handover_to',
      'handover_summary',
      'handover_context_refs',
      'succession_reason',
      'context_used',
      'context_budget'
  )
ORDER BY column_name;

-- ============================================================================
-- VERIFICATION 2: Check Default Values
-- ============================================================================
-- Purpose: Verify existing records have correct defaults
-- Expected: All existing records show instance_number=1, context_used=0, context_budget=150000

SELECT
    job_id,
    agent_type,
    status,
    instance_number,
    context_used,
    context_budget,
    handover_to,
    succession_reason
FROM mcp_agent_jobs
ORDER BY created_at DESC
LIMIT 10;

-- ============================================================================
-- VERIFICATION 3: Check Indexes
-- ============================================================================
-- Purpose: Verify succession indexes were created
-- Expected: 2 rows (idx_agent_jobs_instance, idx_agent_jobs_handover)

SELECT
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'mcp_agent_jobs'
  AND indexname IN ('idx_agent_jobs_instance', 'idx_agent_jobs_handover');

-- ============================================================================
-- VERIFICATION 4: Check Constraints
-- ============================================================================
-- Purpose: Verify check constraints are in place
-- Expected: 3 rows (instance_positive, succession_reason, context_usage)

SELECT
    con.conname AS constraint_name,
    pg_get_constraintdef(con.oid) AS constraint_definition
FROM pg_constraint con
JOIN pg_class rel ON rel.oid = con.conrelid
WHERE rel.relname = 'mcp_agent_jobs'
  AND con.conname IN (
      'ck_mcp_agent_job_instance_positive',
      'ck_mcp_agent_job_succession_reason',
      'ck_mcp_agent_job_context_usage'
  );

-- ============================================================================
-- VERIFICATION 5: Test Multi-Tenant Isolation
-- ============================================================================
-- Purpose: Verify succession queries respect tenant boundaries
-- Expected: Each query returns only records for specified tenant

-- Count orchestrators by tenant (with instance numbers)
SELECT
    tenant_key,
    COUNT(*) as total_jobs,
    COUNT(DISTINCT instance_number) as unique_instances
FROM mcp_agent_jobs
WHERE agent_type = 'orchestrator'
GROUP BY tenant_key;

-- ============================================================================
-- VERIFICATION 6: Test Succession Query Performance
-- ============================================================================
-- Purpose: Verify composite index is being used for succession queries
-- Expected: Index scan (not sequential scan)

EXPLAIN ANALYZE
SELECT *
FROM mcp_agent_jobs
WHERE project_id = 'test-project-id'
  AND agent_type = 'orchestrator'
  AND instance_number = 1;

-- ============================================================================
-- VERIFICATION 7: Test Handover Lookup Performance
-- ============================================================================
-- Purpose: Verify handover_to index is being used
-- Expected: Index scan on idx_agent_jobs_handover

EXPLAIN ANALYZE
SELECT *
FROM mcp_agent_jobs
WHERE handover_to = 'test-job-id';

-- ============================================================================
-- VERIFICATION 8: Check Backward Compatibility
-- ============================================================================
-- Purpose: Verify existing queries still work
-- Expected: All queries return valid results

-- Original query pattern (should still work)
SELECT
    job_id,
    agent_type,
    status,
    created_at
FROM mcp_agent_jobs
WHERE tenant_key = 'test-tenant'
  AND status = 'waiting'
ORDER BY created_at DESC;

-- ============================================================================
-- VERIFICATION 9: Test JSONB Functionality
-- ============================================================================
-- Purpose: Verify handover_summary JSONB column works correctly
-- Expected: Query executes without errors

-- Insert test handover summary (DO NOT RUN IN PRODUCTION)
-- UPDATE mcp_agent_jobs
-- SET handover_summary = '{"project_status": "60% complete", "active_agents": []}'::jsonb
-- WHERE job_id = 'test-job-id';

-- Query JSONB field
SELECT
    job_id,
    handover_summary->>'project_status' as project_status,
    jsonb_array_length(handover_summary->'active_agents') as active_agent_count
FROM mcp_agent_jobs
WHERE handover_summary IS NOT NULL;

-- ============================================================================
-- VERIFICATION 10: Test TEXT[] Functionality
-- ============================================================================
-- Purpose: Verify handover_context_refs array column works correctly
-- Expected: Query executes without errors

-- Query array field
SELECT
    job_id,
    handover_context_refs,
    array_length(handover_context_refs, 1) as ref_count
FROM mcp_agent_jobs
WHERE handover_context_refs IS NOT NULL;

-- ============================================================================
-- VERIFICATION 11: Full Table Structure
-- ============================================================================
-- Purpose: Get complete table definition for documentation
-- Expected: Full column list with types and constraints

SELECT
    column_name,
    data_type,
    character_maximum_length,
    is_nullable,
    column_default,
    ordinal_position
FROM information_schema.columns
WHERE table_name = 'mcp_agent_jobs'
ORDER BY ordinal_position;

-- ============================================================================
-- VERIFICATION 12: Test Constraint Enforcement
-- ============================================================================
-- Purpose: Verify constraints reject invalid data
-- Expected: All INSERT attempts should FAIL with constraint violations

-- Test instance_number constraint (should fail: instance < 1)
-- INSERT INTO mcp_agent_jobs (tenant_key, job_id, agent_type, mission, instance_number)
-- VALUES ('test', 'invalid-1', 'orchestrator', 'test', 0);

-- Test succession_reason constraint (should fail: invalid reason)
-- INSERT INTO mcp_agent_jobs (tenant_key, job_id, agent_type, mission, succession_reason)
-- VALUES ('test', 'invalid-2', 'orchestrator', 'test', 'invalid_reason');

-- Test context_usage constraint (should fail: context_used > context_budget)
-- INSERT INTO mcp_agent_jobs (tenant_key, job_id, agent_type, mission, context_used, context_budget)
-- VALUES ('test', 'invalid-3', 'orchestrator', 'test', 200000, 150000);

-- ============================================================================
-- SUCCESS CRITERIA
-- ============================================================================
--
-- Migration is successful if:
-- ✓ Verification 1: Returns 7 rows (all columns exist)
-- ✓ Verification 2: All existing records have default values
-- ✓ Verification 3: Returns 2 rows (both indexes exist)
-- ✓ Verification 4: Returns 3 rows (all constraints exist)
-- ✓ Verification 5: Returns tenant-isolated results
-- ✓ Verification 6: Uses index scan (not seq scan)
-- ✓ Verification 7: Uses index scan on handover_to
-- ✓ Verification 8: Existing queries return valid results
-- ✓ Verification 9: JSONB queries work correctly
-- ✓ Verification 10: Array queries work correctly
-- ✓ Verification 11: Shows complete table structure
-- ✓ Verification 12: Constraint violations are rejected
--
-- ============================================================================
