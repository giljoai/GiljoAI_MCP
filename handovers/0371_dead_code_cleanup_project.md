# Handover 0371: Dead Code Cleanup Project

**Date**: 2025-12-22
**Priority**: MEDIUM
**Status**: IN PROGRESS
**Estimated Effort**: 8-12 hours (can be parallelized)
**Related**: Handover 0370 (agent_id/job_id audit)

---

## Execution Status (Updated 2025-12-22)

| Phase | Status | Lines Removed | Notes |
|-------|--------|---------------|-------|
| **Phase 1** | ✅ COMPLETE | ~340 | All 3 items fixed |
| **Phase 2** | ✅ COMPLETE | ~6,600 | 12 test files deleted; 2.1 deferred to 0372 |
| **Phase 3** | ✅ COMPLETE | ~1,944 | 5 tool files + 1 test file deleted |
| **Phase 4** | 🔄 IN PROGRESS | ~561 | 4.1→0373, 4.2 deprecated, 4.3 fixed (bug!), 4.4 DONE, 4.5→0374, 4.6 pending |
| **Phase 5** | ⏳ PENDING | - | SQL files |
| **Phase 6** | ⏳ PENDING | - | Frontend (~5,500 lines) |
| **Phase 7** | ⏳ PENDING | - | Migration cleanup |

**Total Removed So Far**: ~9,400 lines

### Spawned Handovers
- **0372**: MessageService Unification (from Phase 2.1) - merge message_service_0366b.py
- **0373**: Template Adapter Migration (from Phase 4.1) - migrate template_adapter.py
- **0374**: Vision Summary Field Migration (from Phase 4.5) - remove deprecated summary_moderate/heavy fields

### Phase 4 Details
| Item | Status | Action |
|------|--------|--------|
| 4.1 Template Adapter | DEFERRED | → Handover 0373 |
| 4.2 TemplateManager Alias | ✅ DONE | Added DEPRECATED comment |
| 4.3 Duplicate User Endpoint | ✅ DONE | **BUG FIX** - frontend was calling non-existent endpoints! Fixed api.js, removed duplicate from auth.py |
| 4.4 GitHub Router | ✅ DONE | Deleted github.py (145 lines), removed router, cleaned frontend WS handler + tests (~464 lines total) |
| 4.5 Vision Document Fields | ✅ DONE | → Handover 0374 (migration created, code updated) |
| 4.6 Template Fields | ⏳ PENDING | Schema cleanup |

### Commits
- `4f31844b` - Phase 1-2: fix install.py, delete 13 test files
- `f313067c` - Phase 3: delete 5 orphan tool files + 1 test file
- `57da9794` - Phase 4.1-4.2: add 0373 handover, deprecate TemplateManager alias
- `93c8b4a6` - Phase 4.3: fix user management API bug
- `ac4bd88d` - Phase 4.4: remove deprecated GitHub router + frontend cleanup

---

## Executive Summary

Comprehensive 6-agent audit identified ~13,000 lines of dead code across all layers:
- Services: ~2,300 lines
- Tools: ~3,500 lines
- Bridge/Adapters: ~500 lines
- Refactor Leftovers: ~1,500 lines
- Frontend: ~5,500 lines

**Key Finding**: NO active bridge/proxy code translating old names to new names. System uses pure functions.

---

## Phase 1: Critical Fixes (Must Do First)

### 1.1 Backup File Deletion

**File**: `src/giljo_mcp/services/orchestration_service.py.backup`
**Action**: DELETE
**Risk**: NONE - file has no imports
**Command**: `rm src/giljo_mcp/services/orchestration_service.py.backup`

### 1.2 Install.py Table Check Fix

**File**: `install.py`
**Line**: 1858
**Issue**: Checks for deprecated `mcp_agent_jobs` table
**Fix**: Update `essential_tables` list to use `agent_jobs` and `agent_executions`

```python
# FROM:
essential_tables = ["users", "products", "projects", "mcp_agent_jobs", ...]

# TO:
essential_tables = ["users", "products", "projects", "agent_jobs", "agent_executions", ...]
```

### 1.3 Broken Test Files (Runtime Crashes)

**File 1**: `tests/services/test_project_service_launch.py`
**Line**: 229
**Issue**: Uses `MCPAgentJob` without importing it
**Fix**: Remove or update the query to use `AgentJob`

**File 2**: `tests/services/test_legacy_messaging_cleanup.py`
**Line**: 147
**Issue**: Asserts `MCPAgentJob is not None` but no import
**Fix**: Remove the assertion or delete the test if obsolete

---

## Phase 2: 0366 Series Leftovers (13 Files)

### 2.1 Duplicate Service File

**File**: `src/giljo_mcp/services/message_service_0366b.py`
**Lines**: 550
**Issue**: Parallel implementation created for Handover 0366b
**Dependencies**:
- `src/giljo_mcp/tools/agent_communication.py` (line 38) - UPDATE IMPORT
- `tests/tools/test_agent_communication_0366c.py` (line 35)
- `tests/tools/test_agent_communication_0360.py` (line 21)
- `tests/services/test_message_service_0366b.py` (line 24) - DELETE
- `tests/integration/test_mcp_tool_consistency_0356.py` (line 30)

**Action**:
1. Update `agent_communication.py` to import from `message_service.py`
2. Delete `message_service_0366b.py`
3. Delete or update dependent test files

### 2.2 Obsolete Test Files (12 Files)

All these files are TDD scaffolding from the 0366 series that can be deleted:

| File | Location | Lines |
|------|----------|-------|
| `test_orchestration_service_0366b.py` | `tests/services/` | ~200 |
| `test_message_service_0366b.py` | `tests/services/` | ~150 |
| `test_agent_job_manager_0366b.py` | `tests/services/` | ~150 |
| `test_agent_coordination_0366c.py` | `tests/tools/` | ~100 |
| `test_agent_communication_0366c.py` | `tests/tools/` | ~100 |
| `test_agent_status_0366c.py` | `tests/tools/` | ~100 |
| `test_agent_discovery_0366c.py` | `tests/tools/` | ~100 |
| `test_agent_job_status_0366c.py` | `tests/tools/` | ~100 |
| `test_succession_tools_0366c.py` | `tests/tools/` | ~100 |
| `test_orchestration_0366c.py` | `tests/tools/` | ~100 |
| `test_project_0366c.py` | `tests/tools/` | ~100 |
| `test_context_0366c.py` | `tests/tools/` | ~100 |

**Action**: Delete all 12 files
**Risk**: LOW - these are obsolete migration tests

---

## Phase 3: Orphan Tool Registrations (5 Files)

These files contain `register_*_tools()` functions that are NEVER called:

### 3.1 optimization.py

**File**: `src/giljo_mcp/tools/optimization.py`
**Lines**: ~400
**Function**: `register_optimization_tools()`
**Tools Defined**:
- `get_optimization_settings`
- `update_optimization_rules`
- `get_token_savings_report`
- `estimate_optimization_impact`
- `force_agent_handoff`
- `get_optimization_status`

**Decision Required**: DELETE entire file or integrate tools into MCP

### 3.2 agent_communication.py

**File**: `src/giljo_mcp/tools/agent_communication.py`
**Lines**: ~300
**Function**: `register_agent_communication_tools()`
**Tools Defined**:
- `check_orchestrator_messages`
- `report_status`

**Decision Required**: DELETE or integrate

### 3.3 claude_code_integration.py

**File**: `src/giljo_mcp/tools/claude_code_integration.py`
**Lines**: ~200
**Function**: `register_claude_code_tools()`
**Tools Defined**:
- `get_orchestrator_prompt`
- `get_agent_mapping`

**Decision Required**: DELETE or integrate

### 3.4 succession_tools.py

**File**: `src/giljo_mcp/tools/succession_tools.py`
**Lines**: ~150
**Function**: `register_succession_tools()`
**Tools Defined**:
- `trigger_succession`
- `check_succession_status`

**Note**: Succession is handled via `orchestration_service.py` - these may be duplicates
**Decision Required**: DELETE (likely duplicate)

### 3.5 task.py

**File**: `src/giljo_mcp/tools/task.py`
**Lines**: ~100
**Function**: `register_task_tools()`
**Tools Defined**:
- `create_task`
- `task`

**Note**: `create_task` IS exposed via ToolAccessor separately
**Decision Required**: DELETE registration function, keep exposed tool

---

## Phase 4: Bridge/Adapter Patterns (6 Items)

### 4.1 Template Adapter (DELETE)

**File**: `src/giljo_mcp/template_adapter.py`
**Lines**: 312
**Classes**: `TemplateAdapter`, `MissionTemplateGeneratorV2`
**Purpose**: Bridge old interface to new database-backed system
**Action**: DELETE - update callers to use `UnifiedTemplateManager` directly

**Callers to Update**:
- Search for `from.*template_adapter import`
- Search for `TemplateAdapter`
- Search for `MissionTemplateGeneratorV2`

### 4.2 Template Manager Alias (REMOVE)

**File**: `src/giljo_mcp/template_manager.py`
**Line**: 1051
**Code**: `TemplateManager = UnifiedTemplateManager`
**Action**: REMOVE alias, update callers to use `UnifiedTemplateManager`

### 4.3 Duplicate User Listing Endpoint (CONSOLIDATE)

**File**: `api/endpoints/auth.py`
**Lines**: 627-650
**Issue**: "duplicated from /api/users/ for backward compatibility"
**Action**: REMOVE duplicate, update any callers to use `/api/users/`

### 4.4 Deprecated GitHub Router (REMOVE)

**File**: `api/endpoints/products/__init__.py`
**Line**: 34
**Code**: `github.router` marked "DEPRECATED - kept for backward compatibility"
**Action**: REMOVE, ensure callers use `git_integration.router`

### 4.5 Deprecated Vision Document Fields (REMOVE)

**File**: `api/schemas/vision_document.py`
**Lines**: 97-101
**Fields**:
- `summary_moderate`
- `summary_heavy`
- `summary_moderate_tokens`
- `summary_heavy_tokens`

**Action**: REMOVE from schema (marked DEPRECATED)

### 4.6 Deprecated Template Fields (REMOVE)

**File**: `api/endpoints/templates/models.py`
**Lines**: 36-39, 70
**Fields**:
- `category` (deprecated)
- `project_type` (deprecated)
- `preferred_tool` (deprecated)
- `template_content` (deprecated=True, use `system_instructions`)

**Action**: REMOVE deprecated fields

---

## Phase 5: SQL Files in Project Root (5 Files)

### Files to DELETE

| File | Purpose | Action |
|------|---------|--------|
| `schema_old_chain.sql` | Old schema dump | DELETE |
| `fix_product_cascade.sql` | Applied fix script | DELETE |
| `diagnostic_cascade_test.sql` | One-time diagnostic | DELETE |
| `temp_add_columns.sql` | Temporary migration | DELETE |

### File to MOVE

| File | Purpose | Action |
|------|---------|--------|
| `backup_0128d_20251111.sql` | DB backup | MOVE to `backups/` folder |

---

## Phase 6: Frontend Dead Code (~5,500 lines)

### 6.1 Agent Flow Visualization System (DELETE ALL)

**Location**: `frontend/src/components/agent-flow/`
**Files**: 7 components
**Lines**: ~1,500
**Issue**: Never imported anywhere in the codebase

Files to delete:
- `AgentFlowVisualization.vue`
- `AgentNode.vue`
- `ConnectionLine.vue`
- `FlowCanvas.vue`
- `FlowControls.vue`
- `MiniMap.vue`
- `index.js`

Related store:
- `frontend/src/stores/agentFlow.js` (if exists)

### 6.2 SubAgent Timeline Components (DELETE)

**Location**: `frontend/src/components/`
**Files**: 3 components
**Issue**: Only used by unused agent-flow system

Files to delete:
- `SubAgentTimeline.vue`
- `TimelineEntry.vue`
- `TimelineConnector.vue`

### 6.3 Unused Stores (DELETE)

| File | Lines | Issue |
|------|-------|-------|
| `frontend/src/stores/projectJobs.js` | ~300 | Defined but never used |
| `frontend/src/stores/agentFlow.js` | ~250 | Only used by deleted components |

### 6.4 Unused Composables (DELETE)

| File | Lines | Issue |
|------|-------|-------|
| `frontend/src/composables/useAgentFlow.js` | ~100 | Only used by deleted components |
| `frontend/src/composables/useTimeline.js` | ~100 | Only used by deleted components |

### 6.5 Unused Views (EVALUATE)

| File | Lines | Issue |
|------|-------|-------|
| TBD | ~400 | Agent identified 2 unused views - need specific names |

### 6.6 Unused Utility Functions (EVALUATE)

**Location**: `frontend/src/utils/`
**Count**: 15+ functions
**Lines**: ~100
**Action**: Audit each function for callers before deletion

---

## Phase 7: Migration Cleanup

### 7.1 Archive Old Migrations

**Move to `migrations/archive/`**:
- `migrations/add_blocked_status_to_agent_jobs.py` (operates on deprecated table)
- `migrations/add_project_description_and_job_project_id.py` (operates on deprecated table)

### 7.2 Pre-commit Hook Enforcement

**File**: `scripts/check_deprecated_models.py`
**Line**: 101
**Current**: `return 0` (warning only)
**Recommended**: `return 1` (block commits with MCPAgentJob)

---

## Verification Checklist

After each phase, verify:

- [ ] `python -m pytest tests/ -x` passes
- [ ] `python -c "from src.giljo_mcp import *"` works
- [ ] `cd frontend && npm run build` succeeds
- [ ] Server starts without errors

---

## Risk Assessment

| Phase | Risk Level | Rollback |
|-------|------------|----------|
| Phase 1 | LOW | Git revert |
| Phase 2 | LOW | Git revert |
| Phase 3 | MEDIUM | Need to evaluate tool usage first |
| Phase 4 | MEDIUM | May have external callers |
| Phase 5 | NONE | Just file cleanup |
| Phase 6 | LOW | Frontend-only, easy to restore |
| Phase 7 | LOW | Migration archives are safe |

---

## Execution Strategy

**Recommended Approach**: Execute phases 1-2 first (safe deletes), then evaluate phases 3-4 (need decisions), then cleanup phases 5-7.

**Parallelization**: Phases can be assigned to separate agents:
- Agent 1: Phase 1 + Phase 2 (critical + 0366 leftovers)
- Agent 2: Phase 3 (tools evaluation)
- Agent 3: Phase 4 (bridge/adapter removal)
- Agent 4: Phase 5 + Phase 7 (file cleanup + migrations)
- Agent 5: Phase 6 (frontend cleanup)

---

## Success Criteria

1. All 13 0366-series test files deleted
2. `message_service_0366b.py` deleted
3. `orchestration_service.py.backup` deleted
4. `install.py` updated for new table names
5. No `MCPAgentJob` references in test files
6. All deprecated schema fields removed
7. Frontend builds without unused components
8. All tests pass

---

## Appendix: Files by Category

### A. Files to DELETE (Safe)

```
# Services
src/giljo_mcp/services/orchestration_service.py.backup
src/giljo_mcp/services/message_service_0366b.py

# Tests (0366 series)
tests/services/test_orchestration_service_0366b.py
tests/services/test_message_service_0366b.py
tests/services/test_agent_job_manager_0366b.py
tests/tools/test_agent_coordination_0366c.py
tests/tools/test_agent_communication_0366c.py
tests/tools/test_agent_status_0366c.py
tests/tools/test_agent_discovery_0366c.py
tests/tools/test_agent_job_status_0366c.py
tests/tools/test_succession_tools_0366c.py
tests/tools/test_orchestration_0366c.py
tests/tools/test_project_0366c.py
tests/tools/test_context_0366c.py

# SQL files
schema_old_chain.sql
fix_product_cascade.sql
diagnostic_cascade_test.sql
temp_add_columns.sql

# Adapter
src/giljo_mcp/template_adapter.py
```

### B. Files to EVALUATE (May Need)

```
# Tools - orphan registrations
src/giljo_mcp/tools/optimization.py
src/giljo_mcp/tools/agent_communication.py
src/giljo_mcp/tools/claude_code_integration.py
src/giljo_mcp/tools/succession_tools.py
src/giljo_mcp/tools/task.py

# Frontend - unused components
frontend/src/components/agent-flow/*
frontend/src/stores/projectJobs.js
```

### C. Files to UPDATE

```
# Fix broken tests
tests/services/test_project_service_launch.py (line 229)
tests/services/test_legacy_messaging_cleanup.py (line 147)

# Update table check
install.py (line 1858)

# Update imports
src/giljo_mcp/tools/agent_communication.py (line 38)

# Remove deprecated fields
api/schemas/vision_document.py (lines 97-101)
api/endpoints/templates/models.py (lines 36-39, 70)

# Remove aliases
src/giljo_mcp/template_manager.py (line 1051)

# Remove duplicate endpoints
api/endpoints/auth.py (lines 627-650)
api/endpoints/products/__init__.py (line 34)
```

---

*Document generated by 6-agent parallel audit on 2025-12-22*
