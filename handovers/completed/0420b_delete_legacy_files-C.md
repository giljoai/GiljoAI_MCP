# Handover 0420b: Delete Legacy Files (Legacy Agent Coordination Removal - Part 2 of 4)

**Date:** 2026-01-17
**From Agent:** Orchestrator (0420 Series Planning)
**To Agent:** Backend Integration Tester
**Priority:** HIGH
**Estimated Complexity:** 30 minutes
**Status:** COMPLETE (See Closeout Notes section)
**Branch:** `legacy-agent-coordination-removal`
**Series:** 0420 Legacy Agent Coordination Removal (Part 2 of 4)

---

## Task Summary

Delete legacy agent coordination files and remove nested functions from `agent_coordination.py`. This is Part 2 of the Legacy Agent Coordination Removal series, following 0420a (Cascade Impact Analysis). **CRITICAL: Tests WILL fail after this handover - this is expected and will be fixed in 0420c.**

**What this handover does**: Surgical deletion of 4 legacy files + removal of ~740 lines of nested functions from `agent_coordination.py`.

**What this handover does NOT do**: Fix tests or resolve import errors (those are for 0420c).

---

## Context and Background

### Problem Statement

The codebase has TWO implementations of AgentJobManager:
1. **Legacy (SYNC)**: `src/giljo_mcp/agent_job_manager.py` - 500+ lines, no WebSocket events
2. **Modern (ASYNC)**: `src/giljo_mcp/services/agent_job_manager.py` - 693 lines, full service layer

The legacy path is orphaned dead code that must be removed.

### Critical Discovery from 0420a

**TWO AgentJobManager Classes Exist:**

| File | Type | Lines | Action |
|------|------|-------|--------|
| `src/giljo_mcp/agent_job_manager.py` | Sync, Legacy | 500+ | **DELETE** |
| `src/giljo_mcp/services/agent_job_manager.py` | Async, Modern | 693 | **KEEP** |

**The root-package AgentJobManager is the legacy code to remove.**

### Cascade Impact Analysis (from 0420a)

```
CHANGE: Remove nested functions in register_agent_coordination_tools()
    |
    +-> IMPACT: Tests using register_agent_coordination_tools()
    |   +-- tests/test_agent_coordination_tools.py (PRIMARY - 800+ lines)
    |   +-- tests/integration/test_multi_tool_orchestration.py
    |   +-- 47+ other test files
    |
    +-> IMPACT: Legacy tool registration
    |   +-- src/giljo_mcp/tools/__init__.py imports register_agent_coordination_tools
    |
    +-> IMPACT: AgentJobManager (root) becomes orphaned
        +-- Only used by legacy nested functions
        +-- ACTION: Delete after removing nested functions
```

### User Decisions

| Question | Answer |
|----------|--------|
| Timeline | **Pre-release** - Can make breaking changes |
| Verify Usage | **No** - Already verified in 0420a |
| Expected Failures | **Yes** - Tests will fail, fixed in 0420c |

### Related Handovers

- **0420a**: Cascade Impact Analysis (PREREQUISITE - must be complete)
- **0420c**: Fix Tests & Resolve Import Errors (NEXT - will fix failures from this handover)
- **0420d**: Final Verification & Merge (LAST - cleanup and merge)

---

## Technical Details

### Files to DELETE (4 files)

| File | Lines | Reason | Cascade Impact |
|------|-------|--------|----------------|
| `src/giljo_mcp/agent_job_manager.py` | 500+ | Legacy sync manager | Breaks all legacy nested functions |
| `tests/test_agent_job_manager.py` | 80+ tests | Tests deleted class | No cascade - already testing dead code |
| `tests/test_agent_coordination_tools.py` | Full file | Tests deprecated functions | No cascade - already testing dead code |
| `test_handover_0045_installation.py` | Full file | Legacy installation test | No cascade - isolated test file |

### Files to HEAVILY MODIFY (1 file this phase)

| File | Changes | Lines Removed |
|------|---------|---------------|
| `src/giljo_mcp/tools/agent_coordination.py` | Remove lines 530-1270 (nested functions) | ~740 lines |

**Functions to REMOVE from agent_coordination.py:**
- `get_pending_jobs()` (nested function inside register_agent_coordination_tools)
- `acknowledge_job()` (nested function)
- `report_progress()` (nested function)
- `complete_job()` (nested function)
- `report_error()` (nested function)
- `send_message()` (nested function)

**Functions to KEEP in agent_coordination.py:**

| Function | Lines | Reason |
|----------|-------|--------|
| `spawn_agent()` | 76-195 | Used by tool_accessor.py |
| `get_agent_status()` | 197-324 | Module-level async function |
| `get_team_agents()` | 326-528 | Used by tool_accessor.py |
| `_get_db_manager()` | 34-39 | Helper function |
| `set_db_manager()` | 42-49 | Test injection helper |
| `init_for_testing()` | 52-72 | Test setup function |

### Import Impact

**Files that will have broken imports after this handover:**

| File | Broken Import | Resolution in 0420c |
|------|---------------|---------------------|
| `src/giljo_mcp/orchestrator.py` | `from giljo_mcp.agent_job_manager import AgentJobManager` | Migrate to OrchestrationService |
| `src/giljo_mcp/workflow_engine.py` | `from giljo_mcp.agent_job_manager import AgentJobManager` | Migrate to OrchestrationService |
| `src/giljo_mcp/tools/agent_job_status.py` | `from giljo_mcp.agent_job_manager import AgentJobManager` | Migrate to OrchestrationService |
| 47+ test files | Various imports | Update to service layer |

### Expected State After This Handover

**CRITICAL EXPECTATIONS:**

1. ✅ 4 files deleted successfully
2. ✅ ~740 lines removed from agent_coordination.py
3. ✅ Module-level functions remain in agent_coordination.py
4. ❌ Tests WILL be failing (this is expected)
5. ❌ Import errors WILL occur (this is expected)
6. ❌ Branch contains BREAKING CHANGES (do NOT merge to master)

---

## Implementation Plan

### Phase 1: Verify 0420a Completion (5 min)

**Goal**: Ensure prerequisite handover is complete

**Tasks**:
1. Check for 0420a closeout notes in git log
2. Verify branch `legacy-agent-coordination-removal` exists
3. Verify database backup was created
4. Review 0420a completion summary for any blockers

**Expected Outcome**: Confirmation that 0420a is complete and safe to proceed.

**Recommended Sub-Agent**: Backend Integration Tester

### Phase 2: Delete Legacy Files (15 min)

**Goal**: Remove 4 orphaned legacy files

**Tasks**:
1. **DELETE** `src/giljo_mcp/agent_job_manager.py`
   - Verify file exists before deletion
   - Document file path for rollback if needed

2. **DELETE** `tests/test_agent_job_manager.py`
   - Verify file exists before deletion
   - Document number of tests being removed

3. **DELETE** `tests/test_agent_coordination_tools.py`
   - Verify file exists before deletion
   - This file has 800+ lines - confirm deletion

4. **DELETE** `test_handover_0045_installation.py`
   - Verify file exists before deletion
   - Legacy installation test - safe to remove

5. Run preliminary test check:
   ```bash
   pytest tests/ --collect-only 2>&1 | tail -20
   ```
   - Document import errors (expected)
   - Count test failures (for comparison with 0420c)

**Expected Outcome**: 4 files deleted, import errors documented.

**Recommended Sub-Agent**: Backend Integration Tester

### Phase 3: Remove Nested Functions from agent_coordination.py (10 min)

**Goal**: Remove ~740 lines of nested functions while keeping module-level functions

**Tasks**:
1. Open `src/giljo_mcp/tools/agent_coordination.py`

2. **LOCATE** the `register_agent_coordination_tools()` function (starts around line 530)

3. **REMOVE** lines 530-1270 (~740 lines):
   - The entire `register_agent_coordination_tools()` function
   - All nested functions inside it:
     - `get_pending_jobs()`
     - `acknowledge_job()`
     - `report_progress()`
     - `complete_job()`
     - `report_error()`
     - `send_message()`

4. **VERIFY** these module-level functions remain (lines 34-528):
   - `_get_db_manager()` (lines 34-39)
   - `set_db_manager()` (lines 42-49)
   - `init_for_testing()` (lines 52-72)
   - `spawn_agent()` (lines 76-195)
   - `get_agent_status()` (lines 197-324)
   - `get_team_agents()` (lines 326-528)

5. **VERIFY** imports at top of file still make sense:
   - Remove any imports only used by deleted functions
   - Keep imports used by remaining module-level functions

6. Run linting check:
   ```bash
   ruff src/giljo_mcp/tools/agent_coordination.py
   ```
   - Fix any obvious linting errors (unused imports)

**Expected Outcome**: ~740 lines removed, module-level functions intact, linting passes.

**Recommended Sub-Agent**: Backend Integration Tester

### Phase 4: Update src/giljo_mcp/tools/__init__.py (5 min)

**Goal**: Remove import of deleted function from tools module

**Tasks**:
1. Open `src/giljo_mcp/tools/__init__.py`

2. **REMOVE** import of `register_agent_coordination_tools`:
   ```python
   # DELETE this line:
   from giljo_mcp.tools.agent_coordination import register_agent_coordination_tools
   ```

3. **UPDATE** `__all__` list:
   - Remove `register_agent_coordination_tools` from exports

4. Run linting check:
   ```bash
   ruff src/giljo_mcp/tools/__init__.py
   ```

**Expected Outcome**: Import removed, `__all__` updated, linting passes.

**Recommended Sub-Agent**: Backend Integration Tester

### Phase 5: Document Failures for 0420c (5 min)

**Goal**: Create comprehensive failure report for next handover

**Tasks**:
1. Run full test suite:
   ```bash
   pytest tests/ -v 2>&1 | tee test_failures_0420b.log
   ```

2. Count failures:
   ```bash
   grep -i "failed\|error" test_failures_0420b.log | wc -l
   ```

3. Extract import errors:
   ```bash
   grep -i "importerror\|modulenotfounderror" test_failures_0420b.log
   ```

4. Create summary document in handover closeout section:
   - Total test count
   - Number of failures
   - Number of import errors
   - List of affected test files (top 10)

**Expected Outcome**: Comprehensive failure report ready for 0420c.

**Recommended Sub-Agent**: Backend Integration Tester

---

## Testing Requirements

### Unit Tests

**NO NEW TESTS** - This handover only deletes code.

**Tests Deleted**:
- All tests in `tests/test_agent_job_manager.py` (80+ tests)
- All tests in `tests/test_agent_coordination_tools.py` (800+ lines)
- `test_handover_0045_installation.py` (legacy test)

### Integration Tests

**EXPECTED FAILURES** (to be fixed in 0420c):
- `tests/integration/test_multi_tool_orchestration.py` - Uses register_agent_coordination_tools
- 47+ other test files - Import errors and missing function calls

### Manual Testing

**NO MANUAL TESTING** - This handover creates breaking changes intentionally.

Manual testing will occur in 0420d after all fixes are complete.

### Coverage Check

**NOT REQUIRED** - Coverage will be checked in 0420d after fixes are complete.

---

## Dependencies and Blockers

### Dependencies

**CRITICAL PREREQUISITE:**
- ✅ **0420a Complete**: Cascade Impact Analysis must be finished
  - Verify closeout notes exist
  - Verify branch `legacy-agent-coordination-removal` exists
  - Verify database backup was created

### Known Blockers

**None** - 0420a has identified all cascade impacts.

### Expected Issues (NOT blockers)

| Issue | Severity | Resolution Timeline |
|-------|----------|---------------------|
| Import errors | EXPECTED | Fixed in 0420c |
| Test failures | EXPECTED | Fixed in 0420c |
| Linting errors | LOW | Fix immediately if found |

---

## Success Criteria

**Definition of Done for 0420b:**

- [x] 0420a closeout notes reviewed
- [ ] `src/giljo_mcp/agent_job_manager.py` deleted
- [ ] `tests/test_agent_job_manager.py` deleted
- [ ] `tests/test_agent_coordination_tools.py` deleted
- [ ] `test_handover_0045_installation.py` deleted
- [ ] Lines 530-1270 removed from `agent_coordination.py`
- [ ] Module-level functions remain in `agent_coordination.py` (spawn_agent, get_agent_status, get_team_agents, helpers)
- [ ] Import removed from `src/giljo_mcp/tools/__init__.py`
- [ ] Linting passes: `ruff src/giljo_mcp/tools/`
- [ ] Test failures documented in closeout section
- [ ] Import errors documented in closeout section
- [ ] Handover 0420c updated with failure report

**NOT Required:**
- ❌ Tests passing (will be failing)
- ❌ No import errors (will have errors)
- ❌ Coverage maintained (will be checked in 0420d)
- ❌ Manual testing (will occur in 0420d)

---

## Rollback Plan

### Pre-Work Safety Net

**Already Complete from 0420a:**
```bash
# Branch created in 0420a
git checkout legacy-agent-coordination-removal

# Database backup created in 0420a
# File: backups/pre_0420_legacy_removal.sql
```

### Rollback Procedures

**Option A: Code-only rollback (most likely)**

```bash
# Discard all changes on branch
git checkout master
git branch -D legacy-agent-coordination-removal

# Recreate branch from master if needed
git checkout -b legacy-agent-coordination-removal
```

**Option B: Partial rollback (specific files)**

```bash
# Restore specific deleted file
git checkout HEAD~1 -- src/giljo_mcp/agent_job_manager.py

# Restore specific modified file
git checkout HEAD~1 -- src/giljo_mcp/tools/agent_coordination.py
```

### Rollback Decision Tree

```
Issue Detected?
    |
    +-> Expected failures (import errors, test failures)
    |   +-- Continue to 0420c (this is normal)
    |
    +-> Unexpected deletion (wrong file deleted)
    |   +-- git checkout HEAD~1 -- <file_path>
    |       +-- Continue implementation
    |
    +-> Major error (can't proceed to 0420c)
        +-- git checkout master
            +-- git branch -D legacy-agent-coordination-removal
                +-- Review 0420a and restart series
```

---

## Additional Resources

### Cascade Impact Discovery Reporting

**If you discover undocumented dependencies during implementation:**

Create an **Integration Report** section in the closeout notes (max 300 words) documenting:
1. **What was discovered**: Specific files/imports/functions not in 0420a analysis
2. **Files affected**: Complete list with line numbers
3. **Recommended action**: Should 0420c fix it, or does 0420d need updates?
4. **Severity**: CRITICAL (blocks 0420c) / HIGH (complicates 0420c) / LOW (informational)

**Example Integration Report:**
```markdown
## Integration Report: Undocumented Cascade

**Discovery**: `src/giljo_mcp/utils/helper.py` imports AgentJobManager (not in 0420a analysis)

**Files Affected**:
- `src/giljo_mcp/utils/helper.py:15` - Import statement
- `src/giljo_mcp/utils/helper.py:87` - AgentJobManager usage

**Recommended Action**: Add to 0420c fix list - migrate to OrchestrationService

**Severity**: HIGH - Blocks 0420c Phase 4
```

### File Deletion Verification Checklist

Before deleting each file, verify:
- [ ] File exists at specified path
- [ ] File is tracked by git (appears in `git ls-files`)
- [ ] File is NOT imported by any files being kept (use `grep -r "from.*import" src/`)
- [ ] File deletion is explicitly listed in this handover

### Links

- **Parent Handover**: `handovers/0420_legacy_agent_coordination_removal.md`
- **Previous Handover**: `handovers/0420a_cascade_impact_analysis.md` (PREREQUISITE)
- **Next Handover**: `handovers/0420c_fix_tests_and_imports.md` (will fix failures from this handover)
- **Architecture**: `docs/SERVICES.md`
- **Service Layer**: `docs/ORCHESTRATOR.md`

---

## Execution Checklist

### Pre-Implementation

- [ ] Read `handovers/0420a_cascade_impact_analysis.md` closeout notes
- [ ] Verify branch `legacy-agent-coordination-removal` exists
- [ ] Verify database backup exists: `ls backups/ | grep pre_0420`
- [ ] Current branch is `legacy-agent-coordination-removal`: `git branch --show-current`

### Phase 1: Verify 0420a Completion (5 min)

- [ ] Check git log for 0420a completion: `git log --oneline | grep 0420a`
- [ ] Review 0420a closeout summary for blockers
- [ ] Verify branch status: `git status`

### Phase 2: Delete Legacy Files (15 min)

- [ ] Verify file exists: `ls src/giljo_mcp/agent_job_manager.py`
- [ ] DELETE `src/giljo_mcp/agent_job_manager.py`
- [ ] Verify file exists: `ls tests/test_agent_job_manager.py`
- [ ] DELETE `tests/test_agent_job_manager.py`
- [ ] Verify file exists: `ls tests/test_agent_coordination_tools.py`
- [ ] DELETE `tests/test_agent_coordination_tools.py`
- [ ] Verify file exists: `ls test_handover_0045_installation.py`
- [ ] DELETE `test_handover_0045_installation.py`
- [ ] Document deletions in git: `git status`
- [ ] Run test collection check: `pytest tests/ --collect-only 2>&1 | tail -20`

### Phase 3: Remove Nested Functions (10 min)

- [ ] Open `src/giljo_mcp/tools/agent_coordination.py`
- [ ] Locate `register_agent_coordination_tools()` function (line ~530)
- [ ] REMOVE lines 530-1270 (entire function and nested functions)
- [ ] VERIFY module-level functions remain (lines 34-528)
- [ ] Remove unused imports
- [ ] Run linting: `ruff src/giljo_mcp/tools/agent_coordination.py`
- [ ] Fix linting errors if any

### Phase 4: Update tools/__init__.py (5 min)

- [ ] Open `src/giljo_mcp/tools/__init__.py`
- [ ] REMOVE import of `register_agent_coordination_tools`
- [ ] UPDATE `__all__` list (remove `register_agent_coordination_tools`)
- [ ] Run linting: `ruff src/giljo_mcp/tools/__init__.py`

### Phase 5: Document Failures (5 min)

- [ ] Run full test suite: `pytest tests/ -v 2>&1 | tee test_failures_0420b.log`
- [ ] Count failures: `grep -i "failed\|error" test_failures_0420b.log | wc -l`
- [ ] Extract import errors: `grep -i "importerror" test_failures_0420b.log`
- [ ] Document top 10 affected test files
- [ ] Create failure report in closeout section below

### Completion

- [ ] Commit changes: `git add -A && git commit -m "feat(0420b): Delete legacy files and nested functions"`
- [ ] Update this handover with closeout notes (see template below)
- [ ] Notify next agent (0420c) with failure report
- [ ] DO NOT merge to master (breaking changes intentional)

---

## Closeout Notes

### Implementation Summary

**Date Completed**: 2026-01-17
**Implemented By**: Backend-Tester Subagent
**Time Taken**: ~15 minutes

### Files Deleted

- [x] `src/giljo_mcp/agent_job_manager.py` - 1,142 lines (legacy sync AgentJobManager)
- [x] `tests/test_agent_job_manager.py` - 1,266 lines (tests for deleted class)
- [x] `tests/test_agent_coordination_tools.py` - 849 lines (tests for deleted functions)
- [x] `test_handover_0045_installation.py` - 440 lines (legacy installation test)

**Total Files Deleted**: 4 files, 3,697 lines

### Files Modified

- [x] `src/giljo_mcp/tools/agent_coordination.py` - Removed lines 530-1271 (~747 lines)
  - Removed entire `register_agent_coordination_tools()` function
  - Removed unused imports (datetime, MessageQueue, AgentJobManager, and_)
  - File reduced from 1,271 → 524 lines
- [x] `src/giljo_mcp/tools/__init__.py` - NO CHANGES NEEDED (already clean, HTTP-only)

### Test Failure Report

**Total Tests**: 3,137 collected
**Errors**: 50 (import errors from deleted module)
**Skipped**: 14

**10 Files Requiring Import Fixes**:

**Core Source Files (3)**:
1. `src/giljo_mcp/orchestrator.py` - ImportError: `from .agent_job_manager import AgentJobManager`
2. `src/giljo_mcp/tools/agent_job_status.py` - ImportError: `from src.giljo_mcp.agent_job_manager import AgentJobManager`
3. `src/giljo_mcp/workflow_engine.py` - ImportError: `from .agent_job_manager import AgentJobManager`

**API Files (1)**:
4. `api/endpoints/agent_jobs/operations.py` - ImportError: `from src.giljo_mcp.agent_job_manager import force_fail_job, request_job_cancellation`

**Test Files (6)**:
5. `tests/integration/test_multi_tool_orchestration.py` - ImportError
6. `tests/services/test_agent_job_manager_mission_ack.py` - ImportError
7. `tests/test_agent_job_status_tool.py` - ImportError
8. `tests/test_agent_orchestrator_communication_tools.py` - ImportError
9. `tests/test_job_cancellation.py` - ImportError
10. `tests/websocket/test_mission_tracking_events.py` - ImportError

**Import Errors Summary**:
```
ModuleNotFoundError: No module named 'giljo_mcp.agent_job_manager'
```

### Cascade Issues Discovered

**Integration Report**:
- `api/endpoints/agent_jobs/operations.py` imports `force_fail_job` and `request_job_cancellation` from deleted module
- These functions need to be either migrated to modern service layer or removed if no longer needed
- Severity: HIGH - affects API endpoint functionality

### Files for 0420c

**Critical Fixes Required**:
1. `src/giljo_mcp/orchestrator.py` - Change import to `from .services.agent_job_manager import AgentJobManager`
2. `src/giljo_mcp/tools/agent_job_status.py` - Change import to services path
3. `src/giljo_mcp/workflow_engine.py` - Change import to services path
4. `api/endpoints/agent_jobs/operations.py` - Migrate or remove `force_fail_job`, `request_job_cancellation`

**Test File Fixes Required**:
1. 6 test files need import path updates to use modern service layer

### Linting Status

- [x] `ruff src/giljo_mcp/tools/agent_coordination.py` - PASS (after removing unused imports)
- [x] Issues found: None remaining

### Rollback Decision

- [x] No rollback needed - proceed to 0420c
- [ ] Partial rollback needed
- [ ] Full rollback needed

### Notes for 0420c

1. **Import Migration Pattern**: Change `from giljo_mcp.agent_job_manager` to `from giljo_mcp.services.agent_job_manager`
2. **API Operations**: `force_fail_job` and `request_job_cancellation` were in deleted module - need to either:
   - Find modern equivalents in OrchestrationService/AgentJobManager
   - Or remove from API if no longer needed
3. **Test Files**: Many tests may be testing deleted functionality - some may need to be deleted rather than fixed

---

**Status**: COMPLETE ✅
**Next Handover**: 0420c (Fix Tests & Resolve Import Errors)
