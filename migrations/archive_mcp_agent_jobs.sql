-- Handover 0367e: MCPAgentJob Archive Template
--
-- Purpose:
--   Provide a safe starting point for archiving the legacy mcp_agent_jobs table
--   now that production code uses AgentJob + AgentExecution exclusively.
--
-- IMPORTANT:
--   - This script is a TEMPLATE and is NOT meant to be applied as-is.
--   - Review and adapt for each environment.
--   - Run in a maintenance window and ensure full backups exist.

-- 1. Create archive table (if not already present)
--    Adjust tablespace, partitioning, and indexing as needed.
--
-- CREATE TABLE IF NOT EXISTS mcp_agent_jobs_archive AS
-- SELECT *
-- FROM mcp_agent_jobs;

-- 2. Optionally add indexes or constraints to the archive
--
-- CREATE INDEX IF NOT EXISTS idx_mcp_agent_jobs_archive_tenant
--     ON mcp_agent_jobs_archive (tenant_key);

-- 3. (Future) Drop or rename original table once tests and consumers no longer depend on it
--
-- ALTER TABLE mcp_agent_jobs RENAME TO mcp_agent_jobs_legacy;
--
-- 4. (Future) Drop foreign keys or references to mcp_agent_jobs_legacy
--    after all code and tests are migrated to AgentJob/AgentExecution.

