# Handover 0080: Quick Start Guide
## Database Schema Changes - Orchestrator Succession

**5-Minute Quick Reference** | **Date**: 2025-11-01

---

## What Changed?

Added 7 columns to `mcp_agent_jobs` table for orchestrator succession tracking:

| Column | Type | Default | Purpose |
|--------|------|---------|---------|
| `instance_number` | INTEGER | 1 | Orchestrator instance (1, 2, 3...) |
| `handover_to` | VARCHAR(36) | NULL | Successor job UUID |
| `handover_summary` | JSONB | NULL | Compressed state transfer |
| `handover_context_refs` | TEXT[] | NULL | Context chunk IDs |
| `succession_reason` | VARCHAR(100) | NULL | Why succession occurred |
| `context_used` | INTEGER | 0 | Tokens used |
| `context_budget` | INTEGER | 150000 | Token budget |

---

## For Fresh Installs

**Just run**: `python install.py`

✅ New columns created automatically
✅ Zero manual steps required

---

## For Existing Installations (Upgrades)

**Just run**: `python install.py`

✅ Migration runs automatically
✅ Detects existing installation
✅ Adds columns safely
✅ Idempotent (safe to re-run)

**Expected Output**:
```
[INFO] Creating database tables...
[INFO] Applying Handover 0080 migration (orchestrator succession)...
[OK] Handover 0080 migration completed successfully
[INFO]   Added 7 columns for orchestrator succession
[INFO]   Created 2 indexes for succession queries
[INFO]   Added 3 check constraints for data integrity
```

**OR** (if already migrated):
```
[INFO] Handover 0080 migration already applied (skipping)
```

---

## Verify Migration

**Quick Check** (psql):

```bash
psql -U giljo_user -d giljo_mcp
```

```sql
-- Check if migration applied
SELECT column_name FROM information_schema.columns
WHERE table_name = 'mcp_agent_jobs'
AND column_name = 'instance_number';
```

**Expected**: 1 row returned (migration successful)

---

## Test Queries

### View Orchestrator Succession

```sql
SELECT
    job_id,
    instance_number,
    status,
    context_used,
    handover_to
FROM mcp_agent_jobs
WHERE agent_type = 'orchestrator'
ORDER BY instance_number;
```

### Check Default Values

```sql
SELECT instance_number, context_used, context_budget
FROM mcp_agent_jobs
LIMIT 5;
```

**Expected**: All show `instance_number=1`, `context_used=0`, `context_budget=150000`

---

## Rollback (Emergency Only)

**If something went wrong**:

```sql
-- Drop new columns
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS instance_number CASCADE;
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS handover_to CASCADE;
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS handover_summary CASCADE;
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS handover_context_refs CASCADE;
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS succession_reason CASCADE;
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS context_used CASCADE;
ALTER TABLE mcp_agent_jobs DROP COLUMN IF EXISTS context_budget CASCADE;
```

**Then re-run**: `python install.py`

---

## Files Changed

- ✅ `src/giljo_mcp/models.py` (lines 1935-2046)
- ✅ `install.py` (lines 746-748, 1447-1589)

## Files Created

- ✅ `handovers/0080_migration_verification.sql` (12 verification queries)
- ✅ `handovers/0080_DATABASE_IMPLEMENTATION_SUMMARY.md` (full docs)
- ✅ `handovers/0080_QUICK_START.md` (this file)

---

## Support

**Full Documentation**: See `0080_DATABASE_IMPLEMENTATION_SUMMARY.md`
**Verification Queries**: See `0080_migration_verification.sql`
**Handover Design**: See `0080_orchestrator_succession_architecture.md`

---

## Success Checklist

- [ ] Run `python install.py` (or restart API server)
- [ ] Check logs for "Handover 0080 migration completed successfully"
- [ ] Run verification query (check if `instance_number` column exists)
- [ ] Test existing queries (verify backward compatibility)
- [ ] Monitor performance (EXPLAIN ANALYZE on succession queries)

---

**Status**: Ready for production ✅
**Risk Level**: Low (backward compatible, idempotent)
**Estimated Time**: <30 seconds migration time
