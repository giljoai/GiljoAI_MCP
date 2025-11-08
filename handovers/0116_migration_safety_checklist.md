# Migration 0116b Safety Checklist

**Migration:** Drop agents table (Final cleanup)
**File:** `migrations/versions/20251107_0116b_drop_agents_table.py`
**Status:** READY TO RUN (pending file migrations)

---

## Pre-Migration Checklist

### ☐ 1. Prerequisites Verification

- [ ] **FK Removal Complete**: Migration `0116_remove_fk` has been run
- [ ] **decommissioned_at Added**: Migration `0113b_decom_at` has been run
- [ ] **7-State System**: Migration `0113_simplify_to_7_states` has been run
- [ ] **File Migrations**: ALL code changes complete (no files reference Agent model)

**Verify:**
```bash
# Check migration history
cd F:/GiljoAI_MCP
alembic current

# Should show: 0116_remove_fk (or later)
```

---

### ☐ 2. Database Backup

- [ ] **Full backup created** before running migration
- [ ] **Backup tested** (can restore if needed)
- [ ] **Backup location** documented

**Commands:**
```bash
# Create backup (PostgreSQL)
pg_dump -U postgres -d giljo_mcp > backups/giljo_mcp_before_0116b_$(date +%Y%m%d_%H%M%S).sql

# Verify backup file size
ls -lh backups/giljo_mcp_before_0116b_*.sql
```

---

### ☐ 3. Run Pre-Migration Verification

- [ ] **Pre-migration SQL executed** successfully
- [ ] **All checks passed** (see output below)

**Command:**
```bash
psql -U postgres -d giljo_mcp -f scripts/0116b_pre_migration_verification.sql
```

**Expected Output:**
```
CHECK 1: ✓ PASS - All FK constraints removed (0 remaining)
CHECK 2: ✓ PASS - agents table exists
CHECK 3: ✓ INFO - X agents will be backed up
CHECK 4: ✓ PASS - MCPAgentJob has all required fields
FINAL SUMMARY: ✓✓✓ ALL CHECKS PASSED
```

---

### ☐ 4. Code Review

- [ ] **No imports** of `Agent` model in codebase
- [ ] **No references** to `agents` table in SQL queries
- [ ] **All tools** use MCPAgentJob instead of Agent

**Verify:**
```bash
# Search for Agent model usage
cd F:/GiljoAI_MCP
grep -r "from giljo_mcp.models import.*Agent" src/
grep -r "FROM agents" src/
grep -r "\.agents\." src/

# Expected: No results (or only comments)
```

---

### ☐ 5. Test Suite Status

- [ ] **All tests passing** before migration
- [ ] **No Agent-dependent tests** remaining

**Command:**
```bash
pytest tests/ -v
```

---

## Migration Execution

### ☐ 6. Run Migration

- [ ] **Migration executed** successfully
- [ ] **No errors** in output
- [ ] **Summary displayed** correctly

**Command:**
```bash
cd F:/GiljoAI_MCP
alembic upgrade 0116b_drop_agents
```

**Expected Output:**
```
HANDOVER 0116: Final Agent Table Drop
========================================
STEP 1: Running safety checks...
  ✓ FK constraints removed: 0 (expected 0)
  ✓ agents table exists
  ✓ MCPAgentJob has required fields: 5/5

STEP 2: Creating agents_backup_final table...
  ✓ Created backup with X records
  ✓ Added retention metadata (30-day retention)

STEP 3: Migrating legacy Agent data...
  ✓ Migrated X agent records to MCPAgentJob.job_metadata

STEP 4: Dropping agents table...
  ✓ agents table dropped

STEP 5: Final verification...
  ✓ agents table no longer exists
  ✓ Backup table exists
  ✓ Backup record count verified: X
  ✓ MCPAgentJob records with legacy data: X

MIGRATION COMPLETE
```

---

## Post-Migration Validation

### ☐ 7. Run Post-Migration Validation

- [ ] **Post-migration SQL executed** successfully
- [ ] **All checks passed**

**Command:**
```bash
psql -U postgres -d giljo_mcp -f scripts/0116b_post_migration_validation.sql
```

**Expected Output:**
```
CHECK 1: ✓ PASS - agents table dropped successfully
CHECK 2: ✓ PASS - Backup table created
CHECK 3: ✓ PASS - Backup contains X records
CHECK 4: ✓ PASS - Backup has retention metadata
CHECK 5: ✓ PASS - X MCPAgentJob records have legacy data
CHECK 7: ✓ PASS - No orphaned references in any table (or expected warnings)
CHECK 8: ✓ PASS - All MCPAgentJob records have valid status, tenant_key, and job_id
CHECK 9: ✓ PASS - All agents with job_id migrated
FINAL SUMMARY: ✓✓✓✓ MIGRATION SUCCESSFUL - All checks passed
```

---

### ☐ 8. Manual Database Verification

- [ ] **agents table dropped**
- [ ] **agents_backup_final exists**
- [ ] **MCPAgentJob has legacy data**

**Commands:**
```sql
-- Verify agents table dropped
SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'agents';
-- Expected: 0

-- Verify backup exists
SELECT COUNT(*) FROM agents_backup_final;
-- Expected: > 0 (if agents existed)

-- Verify legacy data migrated
SELECT COUNT(*) FROM mcp_agent_jobs
WHERE job_metadata->'legacy_agent_data' IS NOT NULL;
-- Expected: Count of migrated agents

-- Sample legacy data
SELECT
    job_id,
    agent_name,
    job_metadata->'legacy_agent_data'->>'agent_id' AS legacy_id,
    job_metadata->'legacy_agent_data'->>'legacy_status' AS legacy_status
FROM mcp_agent_jobs
WHERE job_metadata->'legacy_agent_data' IS NOT NULL
LIMIT 5;
```

---

### ☐ 9. Application Testing

- [ ] **Server starts** without errors
- [ ] **Dashboard loads** correctly
- [ ] **Agent jobs display** correctly
- [ ] **No console errors** related to agents

**Commands:**
```bash
# Start server
cd F:/GiljoAI_MCP
python startup.py

# Check logs
tail -f logs/giljo_mcp.log

# Look for errors related to "agents" table
```

---

### ☐ 10. Test Suite Re-Run

- [ ] **All tests passing** after migration
- [ ] **No new failures** introduced

**Command:**
```bash
pytest tests/ -v --tb=short
```

---

## Post-Migration Cleanup

### ☐ 11. Code Cleanup (Next Steps)

- [ ] **Remove Agent model** from `src/giljo_mcp/models.py`
- [ ] **Remove legacy tools** (`get_agent_status`, `update_agent_status`)
- [ ] **Update imports** across codebase
- [ ] **Remove Agent tests** (if any)

**Files to Update:**
- `src/giljo_mcp/models.py` - Remove `Agent` class
- `src/giljo_mcp/tools/agent_coordination.py` - Remove legacy tools
- Any imports of `Agent` model

---

### ☐ 12. Documentation Updates

- [ ] **Update migration log** with actual metrics
- [ ] **Update handover doc** with completion status
- [ ] **Document backup retention** (30 days until 2025-12-07)

---

### ☐ 13. Backup Retention Plan

- [ ] **Calendar reminder** set for 2025-12-07 (30 days)
- [ ] **Backup drop command** documented

**After 30 days (2025-12-07):**
```sql
-- Drop backup table (only after 30 days and verification)
DROP TABLE agents_backup_final;
```

---

## Emergency Rollback Plan

### ⚠️ IF MIGRATION FAILS

**Do NOT attempt automatic downgrade** - migration is irreversible.

**Recovery Steps:**
1. **Stop application** immediately
2. **Restore from backup**:
   ```bash
   psql -U postgres -d giljo_mcp < backups/giljo_mcp_before_0116b_YYYYMMDD_HHMMSS.sql
   ```
3. **Verify restoration**:
   ```bash
   psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM agents;"
   ```
4. **Investigate failure** before re-attempting
5. **Contact development team** if needed

---

## Sign-Off

### Pre-Migration
- [ ] Database Administrator: _______________ Date: ___________
- [ ] Lead Developer: _______________ Date: ___________

### Post-Migration
- [ ] Database Administrator: _______________ Date: ___________
- [ ] Lead Developer: _______________ Date: ___________
- [ ] QA Engineer: _______________ Date: ___________

---

## Migration Metrics (Fill After Completion)

| Metric | Value |
|--------|-------|
| Records backed up | _______ |
| Records migrated | _______ |
| Orphaned agents | _______ |
| MCPAgentJob total | _______ |
| Migration duration | _______ |
| Backup file size | _______ |

---

## Notes

**CRITICAL WARNINGS:**
- DO NOT run until file migrations are 100% complete
- DO NOT attempt downgrade (irreversible)
- DO NOT drop backup table before 30 days
- TAKE FULL DATABASE BACKUP FIRST

**Architecture Decision:**
- Agent table uses WRONG 4-state model
- MCPAgentJob uses CORRECT 7-state model
- Legacy tools create data disconnect
- Modern tools provide dashboard visibility
- This migration enforces single source of truth

**Backup Retention:**
- Table: `agents_backup_final`
- Retention: 30 days (until 2025-12-07)
- Safe to drop after validation period

---

**Document Version:** 1.0
**Created:** 2025-11-07
**Last Updated:** 2025-11-07
**Migration ID:** 0116b_drop_agents
