# Handover 0073: Database Migration Guide
## Static Agent Grid with Enhanced Messaging

**Created**: 2025-10-29
**Migration IDs**: 20251029_0073_01, 20251029_0073_02, 20251029_0073_03
**Status**: Ready for execution

---

## Overview

This guide documents the three production-grade database migrations for Project 0073: Static Agent Grid with Enhanced Messaging. These migrations enhance the GiljoAI MCP Server with:

1. **Expanded Agent Status States** - 7 granular workflow states instead of 5
2. **Progress Tracking** - Real-time progress monitoring (0-100%)
3. **Project Closeout Support** - Orchestrator-driven completion tracking
4. **Agent Tool Assignment** - Track which AI tool (Claude Code/Codex/Gemini) handles each job

---

## Migration Summary

### Migration 1: Expand Agent Status States (0073_01)
**File**: `20251029_0073_01_expand_agent_statuses.py`
**Revises**: `20251028_simplify_states`
**Table**: `mcp_agent_jobs`

**Changes**:
- Status constraint: 5 states → 7 states
  - OLD: `pending`, `active`, `completed`, `failed`, `blocked`
  - NEW: `waiting`, `preparing`, `working`, `review`, `complete`, `failed`, `blocked`
- Data migration:
  - `pending` → `waiting`
  - `active` → `working`
  - `completed` → `complete`
- New columns:
  - `progress` (INTEGER, 0-100%)
  - `block_reason` (TEXT, nullable)
  - `current_task` (TEXT, nullable)
  - `estimated_completion` (TIMESTAMP WITH TIME ZONE, nullable)

**Impact**:
- Estimated downtime: <5 seconds
- Zero data loss (all jobs migrated)
- Backward compatible API (status mapping handled in migration)

---

### Migration 2: Project Closeout Support (0073_02)
**File**: `20251029_0073_02_project_closeout_support.py`
**Revises**: `20251029_0073_01`
**Table**: `projects`

**Changes**:
- New columns:
  - `orchestrator_summary` (TEXT, nullable)
  - `closeout_prompt` (TEXT, nullable)
  - `closeout_executed_at` (TIMESTAMP WITH TIME ZONE, nullable)
  - `closeout_checklist` (JSONB, default `[]`)
- New index:
  - `idx_projects_closeout_executed` (partial index for closeout queries)

**Impact**:
- Estimated downtime: <1 second
- Zero data impact (all columns nullable/defaulted)
- Fully backward compatible

---

### Migration 3: Agent Tool Assignment (0073_03)
**File**: `20251029_0073_03_agent_tool_assignment.py`
**Revises**: `20251029_0073_02`
**Table**: `mcp_agent_jobs`

**Changes**:
- New columns:
  - `tool_type` (VARCHAR(20), default `'universal'`)
  - `agent_name` (VARCHAR(255), nullable)
- New constraint:
  - `ck_mcp_agent_job_tool_type` (validates tool_type values)
- New index:
  - `idx_mcp_agent_jobs_tenant_tool` (tenant_key, tool_type)
- Data population:
  - Auto-populates `agent_name` from `agent_type` (e.g., "backend" → "Backend Agent")

**Impact**:
- Estimated downtime: <2 seconds
- Zero data loss
- Agent names auto-generated for existing jobs

---

## Pre-Migration Checklist

### 1. Database Backup
```bash
# Create full database backup
pg_dump -U postgres -d giljo_mcp -F c -f giljo_mcp_backup_pre_0073_$(date +%Y%m%d_%H%M%S).dump

# Verify backup integrity
pg_restore --list giljo_mcp_backup_pre_0073_*.dump | head -20
```

### 2. Environment Verification
```bash
# Check PostgreSQL version (requires 11+ for instant column defaults)
psql -U postgres -c "SELECT version();"

# Check current Alembic revision
cd F:\GiljoAI_MCP
alembic current

# Expected output: 20251028_simplify_states (head)
```

### 3. Pre-Migration Data Analysis
```sql
-- Count existing agent jobs by status
SELECT status, COUNT(*) FROM mcp_agent_jobs GROUP BY status;

-- Count projects
SELECT COUNT(*) FROM projects;

-- Check for any critical data patterns
SELECT agent_type, COUNT(*) FROM mcp_agent_jobs GROUP BY agent_type ORDER BY COUNT(*) DESC LIMIT 10;
```

---

## Migration Execution

### Step 1: Stop Application (Optional for Safety)
```bash
# Stop GiljoAI MCP Server
# If using systemd:
sudo systemctl stop giljo-mcp

# Or if running via Python:
pkill -f "python.*startup.py"
```

### Step 2: Run Migrations
```bash
cd F:\GiljoAI_MCP

# Run all three migrations sequentially
alembic upgrade head

# You should see output like:
# INFO  [alembic.runtime.migration] Running upgrade 20251028_simplify_states -> 20251029_0073_01, Handover 0073 Migration 1: ...
# [Handover 0073-01] Expanding agent status states and adding progress tracking
# ...
# INFO  [alembic.runtime.migration] Running upgrade 20251029_0073_01 -> 20251029_0073_02, Handover 0073 Migration 2: ...
# [Handover 0073-02] Adding project closeout support
# ...
# INFO  [alembic.runtime.migration] Running upgrade 20251029_0073_02 -> 20251029_0073_03, Handover 0073 Migration 3: ...
# [Handover 0073-03] Adding agent tool assignment tracking
# ...
```

### Step 3: Verify Migration Success
```sql
-- Check new status values (should see new states)
SELECT status, COUNT(*) FROM mcp_agent_jobs GROUP BY status ORDER BY status;
-- Expected: waiting, preparing, working, review, complete, failed, blocked

-- Verify progress tracking columns exist
SELECT progress, block_reason, current_task, estimated_completion, tool_type, agent_name
FROM mcp_agent_jobs LIMIT 1;

-- Verify project closeout columns exist
SELECT orchestrator_summary, closeout_prompt, closeout_executed_at, closeout_checklist
FROM projects LIMIT 1;

-- Check indexes were created
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename IN ('mcp_agent_jobs', 'projects')
AND indexname LIKE '%0073%' OR indexname LIKE '%tenant_tool%' OR indexname LIKE '%closeout%';
```

### Step 4: Restart Application
```bash
# Restart GiljoAI MCP Server
cd F:\GiljoAI_MCP
python startup.py

# Or with systemd:
sudo systemctl start giljo-mcp
```

---

## Post-Migration Verification

### 1. Functional Testing
```bash
# Test API endpoints that use agent jobs
curl -X GET http://localhost:8000/api/agent-jobs \
  -H "Authorization: Bearer YOUR_TOKEN"

# Test project endpoints
curl -X GET http://localhost:8000/api/projects \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 2. Performance Testing
```sql
-- Test new indexes are being used
EXPLAIN ANALYZE
SELECT * FROM mcp_agent_jobs
WHERE tenant_key = 'test-tenant' AND tool_type = 'claude-code';
-- Should use idx_mcp_agent_jobs_tenant_tool

EXPLAIN ANALYZE
SELECT * FROM projects
WHERE closeout_executed_at IS NOT NULL;
-- Should use idx_projects_closeout_executed
```

### 3. Multi-Tenant Isolation Check
```sql
-- Verify tenant_key isolation
SELECT COUNT(DISTINCT tenant_key) FROM mcp_agent_jobs;

-- Verify no cross-tenant data leakage
SELECT tenant_key, COUNT(*) FROM mcp_agent_jobs GROUP BY tenant_key;
```

---

## Rollback Procedures

### Safe Rollback Window: <24 hours after migration

### Option 1: Alembic Downgrade (Recommended)
```bash
cd F:\GiljoAI_MCP

# Rollback all three migrations
alembic downgrade 20251028_simplify_states

# This will:
# 1. Drop tool assignment columns (0073_03)
# 2. Drop project closeout columns (0073_02)
# 3. Revert status states and drop progress columns (0073_01)
```

**Data Loss Warning**:
- All progress tracking data will be lost
- All closeout data will be lost
- All tool assignments will be lost
- Status granularity will be lost (preparing/review → pending/active)

### Option 2: Database Restore (Nuclear Option)
```bash
# Stop application
sudo systemctl stop giljo-mcp

# Restore from backup
pg_restore -U postgres -d giljo_mcp -c giljo_mcp_backup_pre_0073_*.dump

# Restart application
sudo systemctl start giljo-mcp
```

### Option 3: Selective Rollback (Advanced)
```bash
# Rollback only one migration
alembic downgrade 20251029_0073_02  # Stops after migration 2
# or
alembic downgrade 20251029_0073_01  # Stops after migration 1
```

---

## Troubleshooting

### Issue: Migration Fails with Constraint Violation
**Symptoms**: Error during status migration or constraint creation

**Solution**:
```sql
-- Check for unexpected status values
SELECT DISTINCT status FROM mcp_agent_jobs WHERE status NOT IN ('pending', 'active', 'completed', 'failed', 'blocked');

-- Manually fix invalid statuses
UPDATE mcp_agent_jobs SET status = 'waiting' WHERE status IS NULL;
UPDATE mcp_agent_jobs SET status = 'waiting' WHERE status NOT IN ('pending', 'active', 'completed', 'failed', 'blocked');

-- Retry migration
alembic upgrade head
```

### Issue: Index Creation Times Out
**Symptoms**: Migration hangs during index creation

**Solution**:
```sql
-- Create indexes concurrently (outside migration)
CREATE INDEX CONCURRENTLY idx_mcp_agent_jobs_tenant_tool ON mcp_agent_jobs (tenant_key, tool_type);
CREATE INDEX CONCURRENTLY idx_projects_closeout_executed ON projects (closeout_executed_at) WHERE closeout_executed_at IS NOT NULL;

-- Then manually mark migration as complete
alembic stamp head
```

### Issue: Column Already Exists
**Symptoms**: Error "column already exists"

**Solution**:
```bash
# Check current database state
psql -U postgres -d giljo_mcp -c "\d mcp_agent_jobs"
psql -U postgres -d giljo_mcp -c "\d projects"

# If columns exist but Alembic doesn't know about them:
alembic stamp head

# If partial migration state:
alembic downgrade base
alembic upgrade head
```

---

## Performance Considerations

### Expected Query Performance Improvements

1. **Tool-based filtering** (new index):
   ```sql
   -- Before: Full table scan
   -- After: Index scan on idx_mcp_agent_jobs_tenant_tool
   SELECT * FROM mcp_agent_jobs
   WHERE tenant_key = ? AND tool_type = 'claude-code';
   ```

2. **Closeout queries** (partial index):
   ```sql
   -- Before: Full table scan + filter
   -- After: Index-only scan on idx_projects_closeout_executed
   SELECT * FROM projects WHERE closeout_executed_at IS NOT NULL;
   ```

### Storage Impact
- **mcp_agent_jobs**: ~40 bytes per row (new columns)
- **projects**: ~20 bytes per row (new columns)
- **Indexes**: ~2-5% overhead

### Example Calculations
```
10,000 agent jobs × 40 bytes = 400 KB
1,000 projects × 20 bytes = 20 KB
Total: ~420 KB additional storage
```

---

## Maintenance Tasks

### Weekly Health Check
```sql
-- Check for stale progress tracking
SELECT COUNT(*) FROM mcp_agent_jobs
WHERE status = 'working' AND updated_at < NOW() - INTERVAL '24 hours';

-- Check closeout completion rate
SELECT
  COUNT(*) FILTER (WHERE closeout_executed_at IS NOT NULL) * 100.0 / COUNT(*) as closeout_rate
FROM projects
WHERE status = 'completed';
```

### Monthly Optimization
```sql
-- Vacuum and analyze tables
VACUUM ANALYZE mcp_agent_jobs;
VACUUM ANALYZE projects;

-- Reindex for performance
REINDEX TABLE mcp_agent_jobs;
REINDEX TABLE projects;
```

---

## Contact & Support

**Migration Owner**: Database Expert Agent
**Handover Reference**: 0073 - Static Agent Grid with Enhanced Messaging
**Documentation Date**: 2025-10-29

For issues or questions:
1. Review this guide's Troubleshooting section
2. Check migration logs in Alembic output
3. Examine database state with SQL queries provided
4. Restore from backup if critical failure occurs

**Success Metrics**:
- ✅ All 3 migrations complete without errors
- ✅ Zero downtime for application
- ✅ All existing data preserved and migrated
- ✅ New indexes created and functional
- ✅ Multi-tenant isolation maintained
- ✅ Backward compatibility preserved

---

## Appendix A: SQL Schema Changes

### MCPAgentJob Table (Post-Migration)
```sql
CREATE TABLE mcp_agent_jobs (
    id SERIAL PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL,
    project_id VARCHAR(36) REFERENCES projects(id),
    job_id VARCHAR(36) UNIQUE NOT NULL,
    agent_type VARCHAR(100) NOT NULL,
    mission TEXT NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'waiting',
    spawned_by VARCHAR(36),
    context_chunks JSON DEFAULT '[]'::json,
    messages JSONB DEFAULT '[]'::jsonb,
    acknowledged BOOLEAN DEFAULT false,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),

    -- Handover 0073: New columns
    progress INTEGER NOT NULL DEFAULT 0,
    block_reason TEXT,
    current_task TEXT,
    estimated_completion TIMESTAMP WITH TIME ZONE,
    tool_type VARCHAR(20) NOT NULL DEFAULT 'universal',
    agent_name VARCHAR(255),

    -- Constraints
    CONSTRAINT ck_mcp_agent_job_status CHECK (status IN ('waiting', 'preparing', 'working', 'review', 'complete', 'failed', 'blocked')),
    CONSTRAINT ck_mcp_agent_job_progress_range CHECK (progress >= 0 AND progress <= 100),
    CONSTRAINT ck_mcp_agent_job_tool_type CHECK (tool_type IN ('claude-code', 'codex', 'gemini', 'universal'))
);

-- Indexes
CREATE INDEX idx_mcp_agent_jobs_tenant_status ON mcp_agent_jobs (tenant_key, status);
CREATE INDEX idx_mcp_agent_jobs_tenant_type ON mcp_agent_jobs (tenant_key, agent_type);
CREATE INDEX idx_mcp_agent_jobs_tenant_tool ON mcp_agent_jobs (tenant_key, tool_type);
CREATE INDEX idx_mcp_agent_jobs_job_id ON mcp_agent_jobs (job_id);
CREATE INDEX idx_mcp_agent_jobs_project ON mcp_agent_jobs (project_id);
CREATE INDEX idx_mcp_agent_jobs_tenant_project ON mcp_agent_jobs (tenant_key, project_id);
```

### Project Table (Post-Migration)
```sql
-- Partial schema showing new columns
ALTER TABLE projects ADD COLUMN orchestrator_summary TEXT;
ALTER TABLE projects ADD COLUMN closeout_prompt TEXT;
ALTER TABLE projects ADD COLUMN closeout_executed_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE projects ADD COLUMN closeout_checklist JSONB NOT NULL DEFAULT '[]'::jsonb;

-- New index
CREATE INDEX idx_projects_closeout_executed ON projects (closeout_executed_at)
WHERE closeout_executed_at IS NOT NULL;
```

---

## Appendix B: Testing Queries

### Verify Data Migration (0073_01)
```sql
-- Should return 0 (all old statuses migrated)
SELECT COUNT(*) FROM mcp_agent_jobs
WHERE status IN ('pending', 'active', 'completed');

-- Should show new status distribution
SELECT status, COUNT(*) FROM mcp_agent_jobs GROUP BY status;
```

### Verify Closeout Support (0073_02)
```sql
-- Should return 0 (all projects have empty checklist)
SELECT COUNT(*) FROM projects WHERE closeout_checklist IS NULL;

-- Should return total project count
SELECT COUNT(*) FROM projects WHERE closeout_checklist = '[]'::jsonb;
```

### Verify Tool Assignment (0073_03)
```sql
-- Should return 0 (all jobs have valid tool_type)
SELECT COUNT(*) FROM mcp_agent_jobs
WHERE tool_type NOT IN ('claude-code', 'codex', 'gemini', 'universal');

-- Should show agent_name population
SELECT COUNT(*) FROM mcp_agent_jobs WHERE agent_name IS NOT NULL;
```

---

**End of Migration Guide**
