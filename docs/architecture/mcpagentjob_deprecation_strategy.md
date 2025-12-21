# MCPAgentJob Table Deprecation Strategy

**Last Updated**: 2025-12-21
**Status**: Active - Production code migrated, table pending removal

## Overview

This document outlines the deprecation timeline and archival strategy for the `mcp_agent_jobs` table following the successful MCPAgentJob cleanup migration (Handover 0367 series).

## Deprecation Timeline

| Version | Date | Action | Rationale |
|---------|------|--------|-----------|
| **v3.2** | 2025-12-21 | Production code migrated | Remove active dependencies (Handover 0367a-d) |
| **v3.3** | Q1 2026 | Test code migrated | Remove test dependencies (Handover 0368 series) |
| **v3.4** | Q2 2026 | Table archived and removed | Safe removal after 2 release cycles |

## Current State (v3.2)

### Production Code
- **Status**: ✅ MIGRATED (0 MCPAgentJob references)
- **Verification**: `grep -r "MCPAgentJob" src/ api/ --include="*.py" | grep -v models | grep -v __pycache__ | wc -l` returns 0
- **New Architecture**: AgentJob (work order) + AgentExecution (executor instance)

### Test Code
- **Status**: ⏳ PENDING (1,291 references across 169 files)
- **Impact**: Test fixtures still use MCPAgentJob
- **Plan**: Handover 0368 series (estimated 22-30 hours)

### Database Table
- **Status**: 📦 HISTORICAL DATA ONLY
- **Content**: Records from pre-migration operations
- **No New Inserts**: All new operations use agent_jobs + agent_executions tables

## Archive Strategy

### Step 1: Create Archive Table (Before v3.4)
```sql
-- Create archive table with all historical data
CREATE TABLE mcp_agent_jobs_archive AS
SELECT * FROM mcp_agent_jobs;

-- Add archive metadata
ALTER TABLE mcp_agent_jobs_archive
ADD COLUMN archived_at TIMESTAMP DEFAULT NOW(),
ADD COLUMN archived_by VARCHAR(100) DEFAULT 'migration_0367';
```

### Step 2: Verify No Dependencies
```bash
# Should return 0 results
grep -r "mcp_agent_jobs" src/ api/ --include="*.py" | grep -v models | grep -v __pycache__ | wc -l

# Check no foreign keys reference mcp_agent_jobs
SELECT conname, confrelid::regclass
FROM pg_constraint
WHERE contype = 'f' AND confrelid = 'mcp_agent_jobs'::regclass;
```

### Step 3: Drop Table (v3.4+)
```sql
-- Final safety check - record count
SELECT COUNT(*) FROM mcp_agent_jobs;

-- Drop table (after 0368 test migration complete)
DROP TABLE mcp_agent_jobs;
```

## Rollback Strategy

If critical issues arise post-v3.4:

1. **Restore from Archive**
   ```sql
   CREATE TABLE mcp_agent_jobs AS SELECT * FROM mcp_agent_jobs_archive;
   ```

2. **Revert Code Changes**
   ```bash
   git revert <0367-commits>
   ```

3. **Restart Application**

## Model Definition Retention

The MCPAgentJob model class remains in `src/giljo_mcp/models/agents.py` with deprecation docstring until v3.4:
- Allows emergency rollback
- Supports test migration in 0368
- Preserves historical context

## Migration Reference Documents

- [0367_kickoff.md](../../handovers/0367_kickoff.md) - Master migration roadmap
- [0358_model_mapping_reference.md](../../handovers/Reference_docs/0358_model_mapping_reference.md) - Field mapping guide
- [0366a_schema_and_models-C.md](../../handovers/completed/0366a_schema_and_models-C.md) - Dual-model schema design

## Success Metrics

| Metric | v3.2 Target | v3.4 Target |
|--------|-------------|-------------|
| Production code refs | 0 ✅ | 0 |
| Test code refs | 1,291 | 0 |
| Table status | Historical | Archived |
| Model status | Deprecated | Removed |
