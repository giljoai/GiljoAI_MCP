# 0700b Continuation: Scope Clarification and Authorization

**Date**: 2026-02-04
**Status**: Continuation after blocker 0700b-001
**Authorization**: Human orchestrator via orchestrator-002

---

## Audit Trail Reference

**Decision Record**: `orchestrator-002` in `comms_log.json`
**Decision Date**: 2026-02-04
**Authorizing Party**: Human orchestrator
**Decision Type**: Scope clarification and mission authorization

---

## Acknowledging Your Blocker (0700b-001)

**You were absolutely correct.** Your analysis was thorough, accurate, and professional.

You correctly identified that all 9 deprecated columns are **STILL ACTIVELY USED** throughout the codebase:

| Column | Model | Usage Pattern |
|--------|-------|---------------|
| `instance_number` | AgentExecution | 100+ usages (constraints, indexes, succession logic, UI) |
| `decommissioned_at` | AgentExecution | 3 write locations |
| `succeeded_by` | AgentExecution | 2 write locations, 6+ read locations |
| `succession_reason` | AgentExecution | 1 write location |
| `handover_summary` | AgentExecution | 1 write location |
| `template_content` | AgentTemplate | 50+ usages (template system) |
| `is_used` | DownloadToken | 1 write location |
| `downloaded_at` | DownloadToken | 1 write location |
| `context_budget` | Project | 9+ read locations |

Your grep analysis, usage categorization, and risk assessment were exemplary. **This blocker was the right call.**

---

## The Misunderstanding

### What You Thought the Mission Was
"These columns are deprecated. I need to migrate their functionality to new locations, then remove the columns once migration is complete."

### What the Mission Actually Is
"These columns are deprecated. **Delete the columns AND all code that uses them.** This is a PURGE operation, not a MIGRATION operation."

### Why the Confusion Happened

The deprecation comments in the models (e.g., `# DEPRECATED in v4.0`) implied:
1. There would be a future v4.0 release
2. Backward compatibility would be maintained through v3.x
3. Migration work would happen between v3.x and v4.0

**The reality**:
1. There is no v4.0 - we ARE v1.0 (pre-release cleanup)
2. No backward compatibility needed - no external users exist
3. No migration needed - we delete the dead code paths

---

## Strategic Context: Why This Is a Purge, Not a Migration

### Project Status
- **Current Version**: v1.0 (pre-release)
- **External Users**: None
- **Production Deployments**: Zero
- **Backward Compatibility Requirement**: Zero

### Technical Context
- **Succession System**: Already removed in handover 0700d
- **Orchestrator Instances**: Deprecated - using job_id/agent_id instead
- **Thin Client Migration**: Complete - old prompt system obsolete
- **Template System**: Being replaced in 0700e

### What "Deprecated" Actually Means Here
"This code was part of a design we abandoned. It's dead weight. Delete it."

---

## Your New Mission: Authorized Destructive Purge

For **EACH of the 9 deprecated columns**, you are authorized to:

### 1. Delete the Column Definition
Remove from SQLAlchemy model in `src/giljo_mcp/models.py`

### 2. Delete All Read Operations
- Service methods that query this column
- API endpoints that return this column
- Frontend code that displays this column
- Pydantic schemas that include this field

### 3. Delete All Write Operations
- Service methods that write to this column
- API endpoints that accept this field
- Background jobs that populate this column

### 4. Delete Related Infrastructure
- Database indexes on this column
- UniqueConstraints involving this column
- Foreign key relationships (if any)
- Migration code that creates this column

### 5. Update Tests
- Remove tests that verify this column's behavior
- Update integration tests that assert on this field
- Fix any tests that break due to column removal

### 6. Update Baseline Migration
Remove column creation from `alembic/baseline/01_initial_schema.sql`

---

## Execution Order: Least to Most Risk

Based on your grep analysis, tackle columns in this order:

### Phase 1: Low-Hanging Fruit (1-2 writes, minimal reads)
**Estimated Impact**: <10 lines of code per column

1. **is_used** (DownloadToken)
   - 1 write location
   - Low risk - token download tracking

2. **downloaded_at** (DownloadToken)
   - 1 write location
   - Low risk - token download tracking

### Phase 2: Succession System Remnants (already dead system)
**Estimated Impact**: 10-30 lines of code per column

3. **succession_reason** (AgentExecution)
   - 1 write location
   - Medium risk - succession system removed in 0700d

4. **handover_summary** (AgentExecution)
   - 1 write location
   - Medium risk - succession system removed in 0700d

5. **decommissioned_at** (AgentExecution)
   - 3 write locations
   - Medium risk - succession system removed in 0700d

6. **succeeded_by** (AgentExecution)
   - 2 write locations, 6+ read locations
   - Medium-High risk - most active succession column

### Phase 3: Context Budget Migration (actual migration needed)
**Estimated Impact**: 20-40 lines of code

7. **context_budget** (Project)
   - 9+ read locations
   - **Special Case**: Check if `AgentExecution.context_budget` exists and is populated
   - If migration target exists: delete old column
   - If migration target missing: document for orchestrator

### Phase 4: Complex Removals (defer if too risky)
**Estimated Impact**: 100+ lines of code

8. **instance_number** (AgentExecution)
   - 100+ usages (constraints, indexes, succession ordering, UI)
   - **High Complexity**: May warrant dedicated handover
   - Attempt removal; if too complex, document findings and defer

9. **template_content** (AgentTemplate)
   - 50+ usages (entire template system)
   - **DEFER TO 0700e**: Template System Cleanup handover is specifically designed for this

---

## Special Cases: Detailed Guidance

### Special Case 1: template_content (DEFER)

**Do NOT touch this column.** It's heavily used by:
- Template retrieval system
- Agent spawning logic
- Template editor UI
- Template validation

**Handover 0700e** (Template System Cleanup) will handle this as part of the full template system refactor.

**Action**: Skip this column entirely. Document in completion report that it was deferred to 0700e.

---

### Special Case 2: instance_number (Complex, May Defer)

**Usage Patterns**:
1. **Succession Ordering**: `ORDER BY instance_number DESC` (DELETE - succession removed in 0700d)
2. **UniqueConstraint**: `UniqueConstraint('product_id', 'agent_id', 'instance_number')` (UPDATE)
3. **Database Index**: Index on instance_number (DELETE)
4. **Frontend Display**: "Orchestrator Instance #3" in UI (DELETE)

**Approach**:
1. Remove succession-related queries (grep for `instance_number.*ORDER BY`)
2. Update UniqueConstraint to exclude instance_number (if still needed)
3. Remove database index
4. Remove frontend display code

**If Too Complex**:
- Document what you found (usage patterns, dependencies, risks)
- Write findings to comms_log.json
- Request dedicated handover for instance_number removal

---

### Special Case 3: context_budget (Migration Needed)

**Current State**:
- Stored on `Project` model (deprecated)
- Read in 9+ locations

**Target State**:
- Should be on `AgentExecution` model (per-agent budget)

**Migration Steps**:
1. Check if `AgentExecution.context_budget` column exists:
   ```python
   from src.giljo_mcp.models import AgentExecution
   # Inspect the model or check migrations
   ```

2. **If target column exists and is populated**:
   - Delete `Project.context_budget` column
   - Update all 9+ read locations to use `AgentExecution.context_budget`
   - Update baseline migration

3. **If target column missing or unpopulated**:
   - Document findings in comms_log.json
   - Request orchestrator guidance
   - Do NOT delete the Project column yet

---

## Risk Acknowledgment and Authorization

You are **EXPLICITLY AUTHORIZED** to perform these **DESTRUCTIVE ACTIONS**:

✅ **Delete model columns** from `src/giljo_mcp/models.py`
✅ **Delete service methods** from `src/giljo_mcp/services/`
✅ **Delete API endpoints** from `api/endpoints/`
✅ **Delete Pydantic schemas** from `api/models/`
✅ **Delete frontend code** from `frontend/src/`
✅ **Delete tests** from `tests/`
✅ **Modify database constraints** (UniqueConstraint, indexes)
✅ **Update baseline migration** to exclude deleted columns

### Safety Net

If something breaks:
- We can `git revert` individual commits
- The baseline migration approach means fresh installs will work
- Existing test suite will catch breaking changes

**Fail fast, fix fast.** Don't hesitate to delete code.

---

## Verification Protocol: After Each Column Removal

Run these checks after removing each column:

### 1. Code Search (Should Return Zero Matches)
```bash
grep -r "column_name" src/ api/ frontend/src/ tests/
```

### 2. Model Import (Should Not Error)
```bash
python -c "from src.giljo_mcp.models import *; print('Models OK')"
```

### 3. Test Suite (Should Pass)
```bash
pytest tests/ -x --tb=short
```

### 4. API Startup (Should Not Crash)
```bash
python -c "from api.app import app; print('API OK')"
```

If any check fails, fix the issue before moving to the next column.

---

## Communication Protocol

After each significant milestone (e.g., completing a phase), write to `comms_log.json`:

```json
{
  "entry_id": "0700b-progress-001",
  "timestamp": "2026-02-04T...",
  "from": "worker-0700b",
  "to": "orchestrator-0700a",
  "entry_type": "progress_update",
  "content": {
    "phase": "phase_1",
    "columns_removed": ["is_used", "downloaded_at"],
    "lines_deleted": 47,
    "tests_updated": 3,
    "status": "phase_1_complete"
  }
}
```

### Final Completion Report

When all columns (except deferred ones) are removed, write:

```json
{
  "entry_id": "0700b-complete-001",
  "timestamp": "2026-02-04T...",
  "from": "worker-0700b",
  "to": "orchestrator-0700a",
  "entry_type": "completion_report",
  "content": {
    "columns_removed": ["is_used", "downloaded_at", "succession_reason", "handover_summary", "decommissioned_at", "succeeded_by", "context_budget"],
    "columns_deferred": ["template_content (to 0700e)", "instance_number (too complex - needs dedicated handover)"],
    "total_lines_deleted": 234,
    "tests_updated": 18,
    "tests_passing": true,
    "issues_encountered": [],
    "recommendations": "instance_number removal should be a dedicated handover due to 100+ usages"
  }
}
```

---

## Begin Continuation: Execution Checklist

- [ ] Read orchestrator-002 entry in comms_log.json to confirm authorization
- [ ] Review this continuation prompt in full
- [ ] Confirm understanding: This is a PURGE, not a MIGRATION
- [ ] Start with Phase 1 (is_used, downloaded_at)
- [ ] Verify after each column removal
- [ ] Write progress updates to comms_log.json
- [ ] Defer template_content to 0700e
- [ ] Defer instance_number if complexity exceeds 2 hours of work
- [ ] Write completion report when done

---

## Questions or Concerns?

If you encounter:
- **Unexpected dependencies** - Document in comms_log.json and request guidance
- **Circular dependencies** - Document and request orchestrator decision
- **Breaking production code** - This is expected; delete the broken code too
- **Uncertainty about deletion** - When in doubt, delete it (we can revert)

**You have full authorization to proceed.** The human orchestrator has reviewed your blocker analysis and confirmed this is the correct approach.

Good luck, and thank you for your thoroughness in identifying the blocker. That diligence is exactly what we need.

---

**End of Continuation Prompt**
