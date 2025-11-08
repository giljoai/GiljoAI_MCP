# Migration 0116b Quick Reference

**One-page guide for running the final agent table drop migration**

---

## Overview

**What:** Drop legacy `agents` table (uses wrong 4-state model)
**Why:** MCPAgentJob uses correct 7-state model + provides dashboard visibility
**When:** After ALL file migrations complete (no code references Agent model)

---

## Quick Commands

### 1. Pre-Migration Check
```bash
# Verify prerequisites
psql -U postgres -d giljo_mcp -f scripts/0116b_pre_migration_verification.sql

# Expected: "✓✓✓ ALL CHECKS PASSED"
```

### 2. Take Backup
```bash
# Windows PowerShell
pg_dump -U postgres -d giljo_mcp > backups/giljo_mcp_before_0116b_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql

# Verify backup created
ls backups/
```

### 3. Run Migration
```bash
cd F:/GiljoAI_MCP
alembic upgrade 0116b_drop_agents

# Watch for "MIGRATION COMPLETE" message
```

### 4. Post-Migration Validation
```bash
# Verify success
psql -U postgres -d giljo_mcp -f scripts/0116b_post_migration_validation.sql

# Expected: "✓✓✓✓ MIGRATION SUCCESSFUL"
```

### 5. Test Application
```bash
# Start server
python startup.py

# Run tests
pytest tests/ -v
```

---

## Success Criteria

- ✅ agents table no longer exists
- ✅ agents_backup_final table created (X records)
- ✅ MCPAgentJob.job_metadata contains legacy data
- ✅ All tests passing
- ✅ Dashboard displays agent jobs correctly
- ✅ No errors in server logs

---

## Safety Features

1. **Full backup** before drop (agents_backup_final)
2. **30-day retention** (safe to drop after 2025-12-07)
3. **Legacy data migrated** to MCPAgentJob.job_metadata
4. **Irreversible** (prevents accidental downgrade)
5. **Pre/post validation** SQL scripts
6. **Record count verification** at each step

---

## What Gets Backed Up

**agents_backup_final table contains:**
- All Agent records (including orphaned)
- Full schema with all columns
- 30-day retention metadata
- Accessible for manual queries if needed

**MCPAgentJob.job_metadata['legacy_agent_data'] contains:**
```json
{
  "agent_id": "uuid",
  "legacy_status": "active|idle|completed|failed",
  "context_used": 12345,
  "last_active": "2025-11-07T12:00:00Z",
  "meta_data": {},
  "migrated_at": "2025-11-07T12:00:00Z"
}
```

---

## What Gets Deleted

**After migration completes:**
- ❌ agents table (dropped)
- ✅ agents_backup_final (retained for 30 days)

**After 30 days (2025-12-07):**
- ❌ agents_backup_final (can be dropped)

---

## Emergency Recovery

**IF migration fails:**
```bash
# 1. Stop application
# 2. Restore from backup
psql -U postgres -d giljo_mcp < backups/giljo_mcp_before_0116b_YYYYMMDD_HHMMSS.sql

# 3. Verify restoration
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM agents;"

# 4. Contact development team
```

---

## Prerequisites Checklist

- [ ] Migration `0116_remove_fk` completed
- [ ] Migration `0113b_decom_at` completed
- [ ] Migration `0113_simplify_to_7_states` completed
- [ ] ALL file migrations complete (no Agent model usage)
- [ ] Full database backup taken
- [ ] Pre-migration verification PASSED

---

## Next Steps After Migration

1. **Remove Agent model** from `src/giljo_mcp/models.py`
2. **Remove legacy tools**:
   - `src/giljo_mcp/tools/agent_coordination.py` (get_agent_status, update_agent_status)
3. **Update imports** across codebase
4. **Run test suite** (pytest tests/)
5. **Set reminder** for backup drop (2025-12-07)

---

## Troubleshooting

**"FK constraints still exist"**
→ Run migration `0116_remove_fk` first

**"MCPAgentJob missing fields"**
→ Run migrations `0113_simplify_to_7_states` and `0113b_decom_at` first

**"agents table still exists after drop"**
→ Check migration output for errors, verify no active connections

**"Backup record count mismatch"**
→ Re-run migration (backup will be overwritten), verify no concurrent writes

**"Tests failing after migration"**
→ Check for Agent model usage in test files, update to use MCPAgentJob

---

## Files Reference

| File | Purpose |
|------|---------|
| `migrations/versions/20251107_0116b_drop_agents_table.py` | Migration script |
| `scripts/0116b_pre_migration_verification.sql` | Pre-migration checks |
| `scripts/0116b_post_migration_validation.sql` | Post-migration validation |
| `handovers/0116_migration_log_phase7_final_drop.json` | Detailed metrics log |
| `handovers/0116_migration_safety_checklist.md` | Full safety checklist |

---

## Key Metrics to Record

After migration, update `0116_migration_log_phase7_final_drop.json`:

```json
{
  "records_backed_up": 123,
  "records_migrated": 98,
  "orphaned_agents": 25,
  "jobs_with_legacy_data": 98
}
```

---

## Architecture Validation

**Source:** Comprehensive_MCP_Analysis.md

| Model | States | Dashboard | Status |
|-------|--------|-----------|--------|
| Agent | 4 (idle, active, completed, failed) | No | ❌ WRONG |
| MCPAgentJob | 7 (waiting, working, blocked, complete, failed, cancelled, decommissioned) | Yes | ✅ CORRECT |

**Decision:** Drop Agent table, use MCPAgentJob as single source of truth.

---

**Document Version:** 1.0
**Created:** 2025-11-07
**Migration ID:** 0116b_drop_agents
