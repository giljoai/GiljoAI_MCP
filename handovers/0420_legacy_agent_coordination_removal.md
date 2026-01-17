# Handover 0420: Legacy Agent Coordination Removal (SERIES ROADMAP)

**Date:** 2026-01-17
**From Agent:** Orchestrator (Planning Session)
**To Agent:** See individual sub-handovers
**Priority:** HIGH
**Estimated Complexity:** 10-13 Hours (across 4 sub-handovers)
**Status:** SERIES ROADMAP - Execute sub-handovers in order
**Branch:** `legacy-agent-coordination-removal`

---

## Series Overview

This is the **MASTER ROADMAP** for the 0420 series. Execute sub-handovers in order:

| Handover | Scope | Hours | Prerequisite |
|----------|-------|-------|--------------|
| **[0420a](0420a_cancel_job_implementation.md)** | Safety net + cancel_job() TDD | 3h | None |
| **[0420b](0420b_delete_legacy_files.md)** | Delete files + remove functions | 2h | 0420a complete |
| **[0420c](0420c_update_core_and_tests.md)** | Update core + fix tests | 6h | 0420b complete |
| **[0420d](0420d_frontend_cleanup_merge.md)** | Frontend + cleanup + merge | 2h | 0420c complete |

**Execution Rule**: Each handover MUST read closeout notes from the previous handover before starting.

**Integration Reporting**: Each agent reports undiscovered cascade issues (max 300 words) for user review.

---

## Mission

Complete removal of legacy dual-path architecture in agent coordination tools. The codebase currently has two paths for MCP tool execution: the modern OrchestrationService path (used by MCP HTTP endpoint) and the legacy `register_agent_coordination_tools()` path (nested functions using synchronous AgentJobManager). This series eliminates the legacy path to achieve: **One codebase, no dead code.**

---

## Context and Background

### Problem Statement

The agent coordination layer evolved organically, resulting in duplicate implementations:

1. **Modern Path** (MCP HTTP): `mcp_http.py` → `ToolAccessor` → `OrchestrationService`
   - Async, WebSocket events, validation, TODO tracking

2. **Legacy Path** (FastMCP): `register_agent_coordination_tools()` → nested functions → `AgentJobManager` (root)
   - Sync, no WebSocket events, no validation

### Critical Discovery: TWO AgentJobManager Classes

| Location | Type | Action |
|----------|------|--------|
| `src/giljo_mcp/agent_job_manager.py` | Synchronous (500+ lines) | **DELETE** |
| `src/giljo_mcp/services/agent_job_manager.py` | Asynchronous (693 lines) | **KEEP** |

The root-package `AgentJobManager` is the legacy code to remove.

### User Decisions (from Planning Session)

| Question | Answer |
|----------|--------|
| Timeline | **Pre-release** - Can make breaking changes |
| Verify Usage | **Yes, verify first** - Add tracing before removal |
| cancel_job() | **Yes, add it** - Create OrchestrationService.cancel_job() |

### Related Handovers

- **0416**: Agent Status State Machine (BLOCKED vs FAILED) - recently completed
- **0417**: Multi-Terminal Template Injection - recently completed
- **0419**: Long-Polling Orchestrator Monitoring - ready for implementation

---

## Technical Details

### Impact Topology Map

```
                    +-------------------------------------------------------------+
                    |                     MCP CLIENTS                              |
                    |         (Claude Code, Codex CLI, Gemini CLI)                 |
                    +---------------------------+---------------------------------+
                                                |
                                                v
+-------------------------------------------------------------------------------------+
|                              API LAYER                                               |
|  +-----------------------------------------------------------------------------+   |
|  |  api/endpoints/mcp_http.py (MCP HTTP JSON-RPC)                              |   |
|  |  +-- tool_map routes to state.tool_accessor.{method}()                      |   |
|  |  +-- ALREADY uses OrchestrationService for:                                 |   |
|  |      get_pending_jobs, acknowledge_job, report_progress,                    |   |
|  |      complete_job, report_error                                             |   |
|  +-----------------------------------------------------------------------------+   |
+-------------------------------------------------------------------------------------+
                    |                                              |
                    | MODERN PATH (in use)                         | LEGACY PATH (dead code?)
                    v                                              v
+-------------------------------+          +---------------------------------------+
|  ToolAccessor                 |          |  register_agent_coordination_tools() |
|  (tool_accessor.py)           |          |  (agent_coordination.py)             |
|  +-- Delegates to services    |          |  +-- Nested functions using:         |
|      +-- OrchestrationService |          |      +-- AgentJobManager (SYNC)      |
|          +-- WebSocket events |          |          +-- NO WebSocket events     |
+-------------------------------+          +---------------------------------------+
                    |                                              |
                    v                                              v
+-------------------------------+          +---------------------------------------+
|  SERVICE LAYER                |          |  MANAGER LAYER (Legacy)               |
|  +-------------------------+  |          |  +-----------------------------------+|
|  | OrchestrationService    |  |          |  | AgentJobManager (root package)   ||
|  | (2,065 lines)           |  |          |  | (500+ lines, SYNCHRONOUS)        ||
|  | +-- WebSocket events    |  |          |  | +-- No WebSocket events          ||
|  | +-- Completion valid.   |  |          |  | +-- No validation                ||
|  | +-- Template injection  |  |          |  | +-- Direct DB access             ||
|  | +-- Protocol generation |  |          |  +-----------------------------------+|
|  | +-- TODO tracking       |  |          |                                       |
|  +-------------------------+  |          |  +-----------------------------------+|
|                               |          |  | AgentJobManager (services/)       ||
|                               |          |  | (ASYNC, different class!)         ||
|                               |          |  | +-- Used by get_team_agents only  ||
|                               |          |  +-----------------------------------+|
+-------------------------------+          +---------------------------------------+
```

### Files to DELETE (4 files)

| File | Lines | Reason |
|------|-------|--------|
| `src/giljo_mcp/agent_job_manager.py` | 500+ | Legacy sync manager |
| `tests/test_agent_job_manager.py` | 80+ tests | Tests deleted class |
| `tests/test_agent_coordination_tools.py` | Full file | Tests deprecated functions |
| `test_handover_0045_installation.py` | Full file | Legacy installation test |

### Files to HEAVILY MODIFY (3 files)

| File | Changes |
|------|---------|
| `src/giljo_mcp/tools/agent_coordination.py` | Remove lines 530-1270 (~740 lines) - nested functions |
| `src/giljo_mcp/orchestrator.py` | Remove import (line 26), migrate usage (line 115) |
| `src/giljo_mcp/workflow_engine.py` | Remove import (line 25), migrate usage (line 61) |

### Files to MODIFY (8 files)

| File | Changes |
|------|---------|
| `src/giljo_mcp/tools/agent_job_status.py` | Remove import (line 26), use OrchestrationService |
| `tests/test_orchestrator_routing.py` | Remove 3 deprecated test functions |
| `tests/test_agent_orchestrator_communication_tools.py` | Migrate to service layer |
| `tests/test_agent_job_status_tool.py` | Migrate to OrchestrationService |
| `tests/integration/test_multi_tool_orchestration.py` | Migrate to async service |
| `tests/websocket/test_mission_tracking_events.py` | Migrate to OrchestrationService |
| `tests/services/test_agent_job_manager_mission_ack.py` | Fix import path |
| `frontend/src/utils/statusConfig.js` | Add decommissioned status (~10 lines) |

### Files to KEEP (in agent_coordination.py)

| Function | Lines | Reason |
|----------|-------|--------|
| `spawn_agent()` | 76-195 | Used by tool_accessor.py |
| `get_agent_status()` | 197-324 | Module-level async |
| `get_team_agents()` | 326-528 | Used by tool_accessor.py |
| `_get_db_manager()` | 34-39 | Helper |
| `set_db_manager()` | 42-49 | Test injection |
| `init_for_testing()` | 52-72 | Test setup |

### Critical Gap to Fill Before Refactor

| Gap | Current State | Required | Priority |
|-----|---------------|----------|----------|
| `OrchestrationService.cancel_job()` | Does not exist | HIGH - tools need cancel ability | P0 |

### Cascade Impact Analysis

```
CHANGE: Remove nested functions in register_agent_coordination_tools()
    |
    +-> IMPACT: Tests using register_agent_coordination_tools()
    |   +-- tests/test_agent_coordination_tools.py (PRIMARY - 800+ lines)
    |   +-- tests/integration/test_multi_tool_orchestration.py
    |   +-- 47+ other test files
    |       +-- ACTION: Update tests to use OrchestrationService directly or MCP HTTP
    |
    +-> IMPACT: Legacy tool registration
    |   +-- src/giljo_mcp/tools/__init__.py imports register_agent_coordination_tools
    |   +-- ACTION: Remove import, update __all__
    |
    +-> IMPACT: AgentJobManager (root) becomes orphaned
    |   +-- Only used by legacy nested functions
    |   +-- ACTION: Deprecate or remove after migration
    |
    +-> NO IMPACT: MCP HTTP endpoint (already uses OrchestrationService)
        +-- Frontend (only uses WebSocket events)
```

### Function-Level Risk Assessment

**HIGH RISK (Break if changed incorrectly)**

| Function | Current Path | Change Impact | Cascade |
|----------|--------------|---------------|---------|
| `complete_job()` | AgentJobManager | Validation behavior changes | Tests expecting simple success will fail |
| `report_progress()` | AgentJobManager | TODO tracking added | Tests need todo_items parameter |
| `acknowledge_job()` | AgentJobManager | WebSocket events added | No breakage, additive |

**MEDIUM RISK (Requires careful migration)**

| Function | Current Path | Change Impact | Cascade |
|----------|--------------|---------------|---------|
| `report_error()` | AgentJobManager | Already sets blocked (0416) | Tests updated in 0416 |
| `get_pending_jobs()` | AgentJobManager | Schema differences | Minor test updates |
| `spawn_agent()` | Direct SQLAlchemy | NOT same as spawn_agent_job() | Keep separate or merge carefully |

**LOW RISK (Isolated or deprecated)**

| Function | Current Path | Change Impact | Cascade |
|----------|--------------|---------------|---------|
| `get_agent_status()` | Direct SQLAlchemy | Duplicate exists in agent_job_status.py | Remove duplicate |
| `get_team_agents()` | services/AgentJobManager | Already async | Minimal change |
| `send_message()` | AgentMessageQueue | Different from MessageService | Keep separate |

### Frontend Impact (LOW RISK)

**WebSocket Events - IMPROVEMENT!**

After refactor, frontend gets MORE events:

| Event | Legacy Path | OrchestrationService |
|-------|-------------|---------------------|
| `agent:created` | No | Yes |
| `job:mission_acknowledged` | No | Yes |
| `agent:status_changed` | No | Yes |
| `job:progress_update` | No | Yes |
| `job:status_changed` | No | Yes |

**UI Updates Needed (15 minutes)**

1. `StatusChip.vue` - Add `handed_over` to validator (1 line)
2. `statusConfig.js` - Add `decommissioned` status config (~10 lines)

**Cancel job already implemented** (Handover 0243d) - no new UI work!

---

## Implementation Plan

### Approach: Verified Full Removal (Option A + Verification)

Since this is pre-release, we do a clean removal with verification phase first.

### Phase 0: Safety Net (15 min)

**Goal**: Create branch and backup before any changes

**Tasks**:
1. Create branch: `git checkout -b legacy-agent-coordination-removal`
2. Push branch: `git push -u origin legacy-agent-coordination-removal`
3. Run database backup using DatabaseBackupUtility
4. Document current test count: `pytest tests/ --collect-only | tail -1`

**Recommended Sub-Agent**: Backend Integration Tester

### Phase 1: Add OrchestrationService.cancel_job() (2-3 hours, TDD)

**Goal**: Fill the gap before removing legacy code

**Tasks**:
1. Write tests first in `tests/unit/test_orchestration_service.py`:
   ```python
   @pytest.mark.asyncio
   async def test_cancel_job_success(mock_db_manager):
       """Cancel job should set status to cancelled and emit WebSocket event."""

   @pytest.mark.asyncio
   async def test_cancel_job_decommissions_all_executions(mock_db_manager):
       """Cancel should decommission all active executions for the job."""

   @pytest.mark.asyncio
   async def test_cancel_job_tenant_isolation(mock_db_manager):
       """Cancel should only affect jobs in the same tenant."""
   ```
2. Implement `OrchestrationService.cancel_job()`:
   - Set job status to "cancelled"
   - Decommission all AgentExecutions
   - Emit WebSocket event `agent:status_changed`
   - Return success with cancellation details
3. Add to ToolAccessor wrapper
4. Add to MCP HTTP tool_map

**Recommended Sub-Agent**: TDD Implementor

### Phase 2: Delete Legacy Files (30 min)

**Goal**: Remove orphaned legacy files

**Tasks**:
1. DELETE `src/giljo_mcp/agent_job_manager.py`
2. DELETE `tests/test_agent_job_manager.py`
3. DELETE `tests/test_agent_coordination_tools.py`
4. DELETE `test_handover_0045_installation.py`
5. Run tests - expect some failures

**Recommended Sub-Agent**: Backend Integration Tester

### Phase 3: Remove register_agent_coordination_tools (1 hour)

**Goal**: Remove nested functions from agent_coordination.py

**Tasks**:
1. REMOVE lines 530-1270 from `agent_coordination.py` (nested functions):
   - get_pending_jobs
   - acknowledge_job
   - report_progress
   - complete_job
   - report_error
   - send_message
2. KEEP module-level functions (spawn_agent, get_agent_status, get_team_agents)
3. VERIFY tool_accessor.py import still works
4. Run tests - note remaining failures

**Recommended Sub-Agent**: Backend Integration Tester

### Phase 4: Update Core Files (2-3 hours)

**Goal**: Migrate callers to OrchestrationService

**Tasks**:
1. MODIFY `orchestrator.py` - migrate to OrchestrationService
2. MODIFY `workflow_engine.py` - migrate to async service
3. MODIFY `agent_job_status.py` - use OrchestrationService
4. Run tests after each file

**Recommended Sub-Agent**: TDD Implementor

### Phase 5: Update Tests (3-4 hours)

**Goal**: Fix all broken tests after legacy removal

**Tasks**:
1. **High Priority** (Direct tool tests):
   - `tests/test_agent_coordination_tools.py` - Already deleted
   - Update mocks to match service layer patterns

2. **Medium Priority** (Integration tests):
   - `tests/integration/test_multi_tool_orchestration.py`
   - `tests/integration/test_mcp_orchestration_http_exposure.py`
   - Update to use MCP HTTP endpoint directly

3. **Low Priority** (Indirect tests):
   - `test_orchestrator_routing.py` - remove deprecated tests
   - `test_agent_orchestrator_communication_tools.py`
   - `test_agent_job_status_tool.py`
   - `test_mission_tracking_events.py`
   - `test_agent_job_manager_mission_ack.py` - fix import path

**Recommended Sub-Agent**: Backend Integration Tester

### Phase 6: Frontend Updates (15 min)

**Goal**: Add decommissioned status support

**Tasks**:
1. Update `StatusChip.vue` validator
2. Add `decommissioned` to `statusConfig.js`
3. Run frontend build: `cd frontend && npm run build`

**Recommended Sub-Agent**: Frontend Tester

### Phase 7: Cleanup & Verify (30 min)

**Goal**: Final verification and documentation

**Tasks**:
1. Run `ruff src/` - no linting errors
2. Run `pytest tests/ -v` - all pass
3. Run `pytest tests/ --cov=src/giljo_mcp --cov-report=term` - check coverage
4. Manual E2E test with dashboard
5. Update documentation (CLAUDE.md, docs/SERVICES.md if needed)

**Recommended Sub-Agent**: Documentation Manager

### Phase 8: Merge (15 min)

**Goal**: Merge to master

**Tasks**:
1. `git add -A && git commit -m "feat(0420): Remove legacy agent coordination path"`
2. `git checkout master && git merge legacy-agent-coordination-removal`
3. `git push origin master`
4. Delete branch: `git branch -d legacy-agent-coordination-removal`

---

## Testing Requirements

### Unit Tests

**New Tests Required (Phase 1)**:
- `test_cancel_job_success` - Cancel sets status and emits event
- `test_cancel_job_decommissions_all_executions` - All executions decommissioned
- `test_cancel_job_tenant_isolation` - Tenant isolation enforced

**Tests to Delete (Phase 2)**:
- All tests in `tests/test_agent_job_manager.py`
- All tests in `tests/test_agent_coordination_tools.py`

### Integration Tests

**Tests to Update**:
- `tests/integration/test_multi_tool_orchestration.py` - Use MCP HTTP
- `tests/integration/test_mcp_orchestration_http_exposure.py` - Verify unchanged

### Manual Testing

**Step-by-step procedure**:
1. Start server: `python startup.py`
2. Open dashboard in browser
3. Create a project and spawn orchestrator
4. Use Claude Code to call MCP tools (get_pending_jobs, acknowledge_job, etc.)
5. Verify WebSocket events appear in dashboard real-time
6. Test cancel_job via dashboard "Cancel" button
7. Verify job status changes to "cancelled"

### Coverage Check

```bash
python -m pytest tests/ --cov=src/giljo_mcp --cov-report=html
# Verify >80% coverage
```

---

## Dependencies and Blockers

### Dependencies

- **0416 Complete**: Agent Status State Machine (BLOCKED vs FAILED) - DONE
- **OrchestrationService exists**: Service layer already handles all MCP operations

### Known Blockers

**None** - All dependencies satisfied.

### Questions Resolved

| Question | Resolution |
|----------|------------|
| Is legacy path used? | Unknown - add tracing first (Phase 1 verification removed, doing full removal) |
| What about cancel_job()? | Must implement in OrchestrationService first (Phase 1) |
| Database changes? | None - no schema changes required |

---

## Success Criteria

- [ ] Zero imports of `src/giljo_mcp/agent_job_manager.py` remain
- [ ] Zero calls to `register_agent_coordination_tools()` nested functions remain
- [ ] All tests pass (may have fewer tests after removing legacy test files)
- [ ] Coverage maintained >80%
- [ ] MCP HTTP endpoint works (unchanged - already uses OrchestrationService)
- [ ] Dashboard works (WebSocket events now MORE reliable)
- [ ] `cancel_job()` available via MCP

---

## Rollback Plan

### Pre-Work Safety Net

```bash
# 1. Create branch (Phase 0)
git checkout -b legacy-agent-coordination-removal
git push -u origin legacy-agent-coordination-removal

# 2. Database backup
python -c "
from src.giljo_mcp.database_backup import DatabaseBackupUtility
backup = DatabaseBackupUtility()
backup.create_backup('pre_0420_legacy_removal')
"
```

### Rollback Procedures

**Option A: Code-only rollback (most likely)**
```bash
git checkout master
git branch -D legacy-agent-coordination-removal
```

**Option B: Full rollback with database restore**
```bash
pg_restore -U postgres -d giljo_mcp --clean backups/pre_0420_legacy_removal.sql
git checkout master
```

### Rollback Decision Tree

```
Issue Detected?
    |
    +-> Minor bug (1-2 files)
    |   +-- Fix forward on branch
    |
    +-> Major breakage (tests failing, can't fix quickly)
    |   +-- git checkout master (code rollback only)
    |       +-- Database unchanged (no schema changes)
    |
    +-> Data corruption (unlikely - no schema changes)
        +-- pg_restore from backup
            +-- git checkout master
```

---

## Additional Resources

### Risk Assessment Summary

| Area | Risk | Reason |
|------|------|--------|
| Database | LOW | No schema changes, backup utility exists |
| Frontend | LOW | Actually IMPROVES UX (more WebSocket events) |
| Backend | MEDIUM | 6 source files, 11 test files affected |
| Rollback | LOW | Git branch + database backup |

### Test Impact Summary

**49+ test files affected**, categorized:

| Category | Files | Impact Level |
|----------|-------|--------------|
| Direct tool tests | 5 | HIGH - Must rewrite |
| Integration tests | 12 | MEDIUM - Update mocks |
| Service tests | 8 | LOW - Already test OrchestrationService |
| E2E tests | 4 | MEDIUM - May need path updates |
| Other (indirect) | 20+ | LOW - Minimal changes |

### Estimated Hours

| Phase | Hours | Risk |
|-------|-------|------|
| Phase 0: Safety Net | 0.25 | Low |
| Phase 1: cancel_job() | 2-3 | Low |
| Phase 2: Delete Legacy | 0.5 | Low |
| Phase 3: Remove Functions | 1 | Medium |
| Phase 4: Update Core | 2-3 | Medium |
| Phase 5: Update Tests | 3-4 | Medium-High |
| Phase 6: Frontend | 0.25 | Low |
| Phase 7: Cleanup | 0.5 | Low |
| Phase 8: Merge | 0.25 | Low |
| **Total** | **10-13** | Medium |

### Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Tests break unexpectedly | Verification phase identifies all affected tests |
| Missing functionality | Phase 1 adds cancel_job() before removal |
| Orphaned code | Phase 3 includes orphan detection |
| Regression | Full test suite run after each phase |

### Links

- **Related Handovers**: 0416, 0417, 0419
- **Architecture**: `docs/SERVICES.md`
- **Orchestrator Docs**: `docs/ORCHESTRATOR.md`
- **Previous Work**: Handover 0120-0130 (Backend Refactoring Series)

---

## Execution Checklist

### Phase 0: Safety Net (15 min)
- [ ] Create branch: `git checkout -b legacy-agent-coordination-removal`
- [ ] Push branch: `git push -u origin legacy-agent-coordination-removal`
- [ ] Run database backup
- [ ] Document current test count: `pytest tests/ --collect-only | tail -1`

### Phase 1: Add OrchestrationService.cancel_job() (2-3 hours, TDD)
- [ ] Write tests in `tests/unit/test_orchestration_service.py`
- [ ] Implement `cancel_job()` method
- [ ] Add to ToolAccessor wrapper
- [ ] Add to MCP HTTP tool_map
- [ ] Verify tests pass

### Phase 2: Delete Legacy Files (30 min)
- [ ] DELETE `src/giljo_mcp/agent_job_manager.py`
- [ ] DELETE `tests/test_agent_job_manager.py`
- [ ] DELETE `tests/test_agent_coordination_tools.py`
- [ ] DELETE `test_handover_0045_installation.py`
- [ ] Run tests - expect some failures

### Phase 3: Remove register_agent_coordination_tools (1 hour)
- [ ] REMOVE lines 530-1270 from `agent_coordination.py`
- [ ] KEEP module-level functions (spawn_agent, get_agent_status, get_team_agents)
- [ ] VERIFY tool_accessor.py import still works
- [ ] Run tests - note remaining failures

### Phase 4: Update Core Files (2-3 hours)
- [ ] MODIFY `orchestrator.py` - migrate to OrchestrationService
- [ ] MODIFY `workflow_engine.py` - migrate to async service
- [ ] MODIFY `agent_job_status.py` - use OrchestrationService
- [ ] Run tests after each file

### Phase 5: Update Tests (3-4 hours)
- [ ] MODIFY `test_orchestrator_routing.py` - remove deprecated tests
- [ ] MODIFY `test_agent_orchestrator_communication_tools.py`
- [ ] MODIFY `test_agent_job_status_tool.py`
- [ ] MODIFY `test_multi_tool_orchestration.py`
- [ ] MODIFY `test_mission_tracking_events.py`
- [ ] MODIFY `test_agent_job_manager_mission_ack.py`
- [ ] Run full test suite

### Phase 6: Frontend Updates (15 min)
- [ ] Update `StatusChip.vue` validator
- [ ] Add `decommissioned` to `statusConfig.js`
- [ ] Run frontend build: `cd frontend && npm run build`

### Phase 7: Cleanup & Verify (30 min)
- [ ] Run `ruff src/` - no linting errors
- [ ] Run `pytest tests/ -v` - all pass
- [ ] Run `pytest tests/ --cov=src/giljo_mcp --cov-report=term` - check coverage
- [ ] Manual E2E test with dashboard
- [ ] Update documentation
- [ ] Create completion handover

### Phase 8: Merge (15 min)
- [ ] `git add -A && git commit -m "feat(0420): Remove legacy agent coordination path"`
- [ ] `git checkout master && git merge legacy-agent-coordination-removal`
- [ ] `git push origin master`
- [ ] Delete branch: `git branch -d legacy-agent-coordination-removal`
