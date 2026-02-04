# Kickoff Prompt: Handover 0700b - Database Schema Purge

**Series**: 0700 Code Cleanup Series (4/12 complete: 0700a, 0700, 0701, [YOU ARE HERE])
**Status**: Ready to execute (dependencies satisfied: 0701 complete)
**Risk Level**: ⚠️ **HIGH** - Modifying critical database models with 32 dependents

---

## Mission Overview

Remove ALL deprecated database columns before v1.0 ships. This is pre-release cleanup with no backwards compatibility required - ship a clean schema without technical debt.

**Strategic Context**: No external users exist. We have the freedom to make breaking changes cleanly. This handover is part of the merged cleanup approach decided after deep-researcher audit (dead_code_audit.md).

**Reference**: `handovers/0700_series/0700b_database_schema_purge.md`

---

## ⚠️ CRITICAL: Dependency Awareness from 0701 Visualization

### HIGH-RISK FILES (Handle with Extreme Care)

From dependency analysis (0701 findings), these files have massive dependency trees:

1. **src/giljo_mcp/models/__init__.py** - 105 dependents
   - **CRITICAL HUB**: NEVER delete this file
   - Verify column removals don't break exports
   - Check that deprecated columns aren't re-exported

2. **src/giljo_mcp/models/agent_identity.py** - 32 dependents ⚠️
   - **PRIMARY TARGET**: Contains 5 deprecated AgentExecution columns
   - **RISK**: 32 files import from this module
   - **STRATEGY**: Verify each column isn't accessed by dependents before removal

### Files That Import agent_identity.py (32 dependents)

These files could potentially access the columns we're removing:

**Services Layer** (7 files):
- `src/giljo_mcp/services/agent_job_manager.py`
- `src/giljo_mcp/services/agent_service.py`
- `src/giljo_mcp/services/orchestration_service.py`
- `src/giljo_mcp/services/task_service.py`
- `src/giljo_mcp/services/context_service.py`
- `src/giljo_mcp/repositories/agent_job_repository.py`
- `src/giljo_mcp/repositories/message_repository.py`

**API Endpoints** (8 files):
- `api/endpoints/agent_management.py`
- `api/endpoints/agent_jobs/*.py` (6 modules)

**MCP Tools** (5 files):
- `src/giljo_mcp/tools/agent_coordination/*.py`

**Tests** (12 files):
- `tests/services/test_agent_job_manager.py`
- `tests/services/test_orchestration_service.py`
- Various integration tests

**See**: `handovers/0700_series/dependency_analysis.json` for complete list

---

## Scope: 4 Tables, 9 Deprecated Columns

### 1. agent_executions (5 deprecated columns) ⚠️ HIGH RISK

**File**: `src/giljo_mcp/models/agent_identity.py` (32 dependents)

| Column | Lines | Deprecation | Usage Check Required |
|--------|-------|-------------|---------------------|
| `instance_number` | 184-189 | Handover 0461b | Grep for access patterns |
| `decommissioned_at` | 200-204 | Handover 0461b | Check succession flows |
| `succeeded_by` | 212-216 | Handover 0461b | Verify handover logic |
| `succession_reason` | 282-286 | Handover 0461b | Check orchestration |
| `handover_summary` | 287-291 | Handover 0461b | Verify simple_handover |

**Critical Verification Steps**:
1. Grep each column name in `src/` and `api/` before removal
2. Check if any of the 32 dependent files access these columns
3. Verify `models/__init__.py` doesn't export these columns
4. Test that succession flows still work after removal

### 2. templates (1 deprecated column)

**File**: `src/giljo_mcp/models/templates.py`

| Column | Lines | Related Code |
|--------|-------|--------------|
| `template_content` | 73-77 | Template seeder at line 248 |

**Verification**: Check `src/giljo_mcp/template_seeder.py:248` for writes to this field

### 3. download_tokens (2 deprecated columns)

**File**: `src/giljo_mcp/models/config.py`

| Column | Lines |
|--------|-------|
| `is_used` | 620-622 |
| `downloaded_at` | 623-625 |

**Low Risk**: Simple utility columns, unlikely to have many dependents

### 4. projects (1 soft-deprecated column)

**File**: `src/giljo_mcp/models/projects.py`

| Column | Lines | Replacement |
|--------|-------|------------|
| `context_budget` | 69 | Migrated to `AgentExecution.context_budget` |

**Verification**: Search all code reading `Project.context_budget` and ensure it uses `AgentExecution.context_budget` instead

---

## Execution Plan (4 Phases)

### Phase 1: Pre-Removal Verification (30 min) 🔍

**Before removing ANY columns, verify they're not in use:**

```bash
# Check each AgentExecution column
grep -r "instance_number" src/ api/ --exclude-dir=migrations
grep -r "decommissioned_at" src/ api/ --exclude-dir=migrations
grep -r "succeeded_by" src/ api/ --exclude-dir=migrations
grep -r "succession_reason" src/ api/ --exclude-dir=migrations
grep -r "handover_summary" src/ api/ --exclude-dir=migrations

# Check template column
grep -r "template_content" src/ api/ --exclude-dir=migrations

# Check download_tokens columns
grep -r "is_used" src/ api/ | grep -i "download"
grep -r "downloaded_at" src/ api/ | grep -i "download"

# Check Project.context_budget migration status
grep -r "context_budget" src/ api/ | grep -v "AgentExecution"
```

**Expected**: Zero or minimal hits (only in model definitions + DEPRECATED comments)

**If you find usage**: DO NOT PROCEED. Write blocker to comms_log.json and report to orchestrator.

### Phase 2: Model Cleanup (45 min) 🔧

**Order matters**: Remove from least risky to most risky

1. **Start with download_tokens** (safest):
   - Remove lines 620-622 (`is_used`)
   - Remove lines 623-625 (`downloaded_at`)
   - Test: `pytest tests/ -k download_token -v`

2. **Then templates**:
   - Remove lines 73-77 (`template_content`)
   - Update template_seeder.py if it writes to this field
   - Test: `pytest tests/ -k template -v`

3. **Then projects**:
   - Remove line 69 (`context_budget`)
   - Update docstring at line 46 (remove soft-deprecation note)
   - Verify all code uses `AgentExecution.context_budget`
   - Test: `pytest tests/services/test_project_service.py -v`

4. **Finally agent_identity.py** (highest risk):
   - Remove lines 184-189 (`instance_number`)
   - Remove lines 200-204 (`decommissioned_at`)
   - Remove lines 212-216 (`succeeded_by`)
   - Remove lines 282-286 (`succession_reason`)
   - Remove lines 287-291 (`handover_summary`)
   - Update class docstring (lines 143-152) - remove all deprecation notices
   - Test: `pytest tests/services/test_agent_job_manager.py -v`
   - Test: `pytest tests/services/test_orchestration_service.py -v`

**Stop after each table**: Run tests, check for import errors, verify no runtime breaks

### Phase 3: Migration & Database (30 min) 🗄️

**Update baseline migration**:
1. Locate migration file (likely `migrations/baseline_migration.py`)
2. Remove column definitions for all 9 deprecated columns
3. Ensure migration generates clean schema matching updated models

**Test fresh install**:
```bash
# Drop and recreate database
python install.py --reset-db

# Verify schema matches models
python -c "from src.giljo_mcp.models import *; print('Models loaded successfully')"

# Inspect tables to verify columns removed
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d agent_executions"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d templates"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d download_tokens"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d projects"
```

**Expected**: Clean schema without deprecated columns, fresh install completes in ~1 second

### Phase 4: Code Search & Cleanup (15 min) 🧹

**Final verification - no references should remain**:
```bash
# Should return ZERO hits (except in git history / comments)
grep -r "instance_number\|decommissioned_at\|succeeded_by\|succession_reason\|handover_summary" src/ api/
grep -r "template_content" src/ api/ --exclude-dir=migrations
grep -r "is_used.*download\|downloaded_at" src/ api/
grep -r "Project.*context_budget" src/ api/
```

**If you find hits**: Remove or migrate the code accessing deprecated columns

---

## Verification Checklist

- [ ] Phase 1: All grep searches show zero/minimal usage
- [ ] Phase 2: All models updated, tests passing after each table
- [ ] Phase 3: Fresh install completes without errors
- [ ] Phase 3: Database schema inspection shows clean tables
- [ ] Phase 4: Final grep searches return zero hits
- [ ] All imports resolve (no undefined column references)
- [ ] Full test suite passes: `pytest tests/ -v` (100%)

---

## Risk Mitigation

**Rollback Plan**:
```bash
git revert HEAD
python install.py --reset-db
pytest tests/ -v
```

**If Tests Fail**:
1. Diagnose: Is it pre-existing or caused by your changes?
2. If pre-existing: Note it and continue
3. If caused by changes: Fix before proceeding
4. If unfixable: Write blocker to comms_log.json and STOP

**If Cascade Break Detected**:
1. Immediately STOP making changes
2. Run `git status` to see what's modified
3. Consider reverting to last good state
4. Write blocker to comms_log.json
5. Consult orchestrator

---

## Communication Requirements

**Read First** (Context Acquisition):
1. `handovers/0700_series/orchestrator_state.json` - Series status
2. `handovers/0700_series/comms_log.json` - Filter for `to_handovers: ["0700b"]`
3. `handovers/0700_series/dependency_analysis.json` - High-risk files
4. `handovers/0700_series/0700b_database_schema_purge.md` - Full spec

**Write to comms_log.json** (Downstream Communication):

For each significant finding or pattern, write an entry:

```json
{
  "id": "[UUID]",
  "timestamp": "[ISO timestamp]",
  "from_handover": "0700b",
  "to_handovers": ["0700c", "0700d"],
  "type": "dependency|info|warning|blocker",
  "subject": "[Short subject]",
  "message": "[Detailed message with context]",
  "files_affected": ["[Files you modified]"],
  "action_required": true|false,
  "context": {
    "columns_removed": ["list of columns"],
    "dependent_files_checked": 32
  }
}
```

**Notify These Handovers**:
- **0700c** (JSONB Field Cleanup) - They remove `AgentExecution.messages`, need to know about schema changes
- **0700d** (Legacy Succession Cleanup) - They remove succession.py, need to know about succession column removals
- **0700e** (Template System Cleanup) - They remove template_content references, need confirmation column is gone

---

## Recommended Subagents

**Primary**: `database-expert`
- Schema changes and migration updates
- Database verification queries
- Model integrity checks

**Secondary**: `tdd-implementor`
- Test verification after each phase
- Test updates if needed
- Regression detection

**Pattern**: Use database-expert for modifications, tdd-implementor for verification

---

## Documentation Updates (Post-Execution)

**Will be handled in Phase 6** per Worker Protocol

Files likely to need updates (check `doc_impacts.json`):
- `docs/SERVICES.md` - If any services documented these columns
- `docs/ORCHESTRATOR.md` - If succession columns mentioned
- `CLAUDE.md` - Remove references to deprecated columns
- API documentation - If endpoints documented these fields

---

## Commit Format

```bash
git add -A
git commit -m "cleanup(0700b): Purge 9 deprecated database columns

Removed 9 deprecated columns across 4 tables before v1.0 release.
No backwards compatibility required (pre-release cleanup).

Changes:
- AgentExecution: Removed 5 succession columns (instance_number, decommissioned_at, succeeded_by, succession_reason, handover_summary)
- AgentTemplate: Removed template_content column
- DownloadToken: Removed is_used, downloaded_at columns
- Project: Removed context_budget soft-deprecated column
- Updated baseline migration to match clean schema
- Verified zero code references to removed columns

Verification:
- Fresh install completes successfully
- All 32 dependent files checked for access patterns
- Full test suite passing (pytest tests/ -v)
- Database schema inspection confirms clean tables

Docs Updated:
- [List docs you updated]

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## Success Criteria

**You've completed 0700b when**:
1. ✅ All 9 deprecated columns removed from models
2. ✅ Baseline migration updated to match clean schema
3. ✅ Fresh install completes without errors (<1 second)
4. ✅ Full test suite passing (100%)
5. ✅ Zero grep hits for removed column names
6. ✅ Database schema verification shows clean tables
7. ✅ Comms log entry written for downstream handovers (0700c, 0700d, 0700e)
8. ✅ Documentation updated per doc_impacts.json
9. ✅ Orchestrator_state.json updated (status: complete)
10. ✅ Changes committed with proper message format

---

## Critical Reminders

⚠️ **HIGH-RISK FILE**: `src/giljo_mcp/models/agent_identity.py` has 32 dependents
- Grep BEFORE removing each column
- Check models/__init__.py doesn't export deprecated columns
- Run tests after EACH table modification
- Stop immediately if cascade breaks detected

⚠️ **NEVER DELETE**: `src/giljo_mcp/models/__init__.py` (105 dependents - critical hub)

⚠️ **STOP IF BLOCKED**: Write blocker to comms_log.json, report to orchestrator, do not hack around problems

---

**Ready to execute. Follow the Worker Protocol phases. Good hunting!** 🎯
