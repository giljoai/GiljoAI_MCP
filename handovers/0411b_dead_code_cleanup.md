# Handover 0411b: Dead Code Cleanup (Orphaned Orchestration Pipeline)

**Status**: COMPLETE
**Priority**: LOW (housekeeping - no functional impact)
**Estimated Effort**: 1-2 hours
**Created**: 2026-02-24
**Parent**: 0411 (Windows Terminal Agent Spawning - superseded)
**Related**: 0020 (original vision), 0411a (phase labels), 0353 (team context headers)

---

## Executive Summary

The automated orchestration pipeline (WorkflowEngine, JobCoordinator, and four OrchestrationService methods) has been fully unreachable since the `orchestrate_project` MCP tool was removed on 2026-01-27 (commit `d67f0d23`). This handover catalogs approximately **1,640 lines of dead production code** across 4 files, plus **~2,550 lines of dead test code** across 4 test files, for a total removal of **~4,190 lines**. The MissionPlanner and AgentSelector files require partial cleanup because they contain methods used by both dead and active code paths.

**CRITICAL**: The MissionPlanner is still ACTIVELY used by `get_orchestrator_instructions()` (line 3313 of orchestration_service.py) for its `_build_fetch_instructions()` method. It must NOT be deleted entirely. Similarly, `AgentConfig` in orchestration_types.py is imported by MissionPlanner and AgentSelector.

---

## Archaeological Context

### Why This Code Exists

Handover 0020 (October 2025) built an ambitious automated orchestration vision:

1. **MissionPlanner** (commit `2a11064d`, 2025-10-19): Analyze product requirements, generate agent-specific missions with field priority framing and vision document chunking.
2. **AgentSelector** (same period): Query database templates and select agents based on requirement analysis.
3. **WorkflowEngine** (commit `23089573`, 2025-10-19): Execute multi-agent workflows in waterfall or parallel coordination patterns.
4. **JobCoordinator** (companion to WorkflowEngine): Spawn agent jobs, wait for completion, aggregate results.

The entry point was the `orchestrate_project` MCP tool, which called `process_product_vision()` on OrchestrationService.

### Why It Is Now Dead

The system was replaced by a manual orchestration model:
- The orchestrator agent reads `get_orchestrator_instructions()` for framing context
- The orchestrator calls `spawn_agent_job()` individually for each agent
- The user manages execution order via the Jobs tab UI (play buttons)

The automated pipeline was never removed - it was simply disconnected when its only entry point was deleted.

### Timeline

| Date | Commit | Event |
|------|--------|-------|
| 2025-10-19 | `2a11064d` | Handover 0020 Phase 1A: MissionPlanner, orchestration_types |
| 2025-10-19 | `23089573` | Handover 0020 Phase 1D: WorkflowEngine, JobCoordinator |
| 2025-12-19 | `f98b933d` | Handover 0353: `_generate_team_context_header()` (active system, NOT part of dead code) |
| **2026-01-27** | **`d67f0d23`** | **Handover 0470: `orchestrate_project` MCP tool REMOVED** |
| 2026-01-27 | (same) | Line 1099 comment: "orchestrate_project() method removed in favor of manual orchestration workflow" |

---

## Dead Code Inventory

### Tier 1: Entire Files to Delete

| File | Lines | Justification |
|------|-------|---------------|
| `src/giljo_mcp/workflow_engine.py` | 465 | Only imported at orchestration_service.py:74. Only called by `coordinate_agent_workflow()` which is unreachable. |
| `src/giljo_mcp/job_coordinator.py` | 503 | Only imported by workflow_engine.py:24. Only consumer is WorkflowEngine. |

**Total Tier 1**: ~968 lines of production code

### Tier 2: Partial File Cleanup (orchestration_types.py)

**File**: `src/giljo_mcp/orchestration_types.py` (238 lines total)

| Lines | Symbol | Action | Justification |
|-------|--------|--------|---------------|
| 20-55 | `Mission` dataclass | KEEP for now | Imported by mission_planner.py (active file). Evaluate separately after MissionPlanner audit. |
| 58-91 | `RequirementAnalysis` dataclass | KEEP for now | Imported by mission_planner.py. Only used by dead `analyze_requirements()` method, but removing requires MissionPlanner surgery. |
| 95-136 | `AgentConfig` dataclass | KEEP for now | Imported by mission_planner.py AND agent_selector.py. Note: separate `AgentConfig` also exists in config_manager.py:170 (different class, same name). |
| 140-178 | `WorkflowStage` dataclass | **DELETE** | Only imported by workflow_engine.py (being deleted). |
| 182-201 | `StageResult` dataclass | **DELETE** | Only imported by workflow_engine.py (being deleted). |
| 205-238 | `WorkflowResult` dataclass | **DELETE** | Only imported by workflow_engine.py (being deleted). |

**Lines to delete from orchestration_types.py**: ~99 lines (lines 140-238)
**Lines remaining after cleanup**: ~139 lines (Mission, RequirementAnalysis, AgentConfig)

### Tier 3: Orphaned Methods in OrchestrationService

**File**: `src/giljo_mcp/services/orchestration_service.py` (3,618 lines total)

| Lines | Method | Action | Justification |
|-------|--------|--------|---------------|
| 2929-2966 | `generate_mission_plan()` | **DELETE** | Only called by `process_product_vision()` (unreachable). |
| 2968-2990 | `select_agents_for_mission()` | **DELETE** | Only called by `process_product_vision()` (unreachable). |
| 2992-3022 | `coordinate_agent_workflow()` | **DELETE** | Only called by `process_product_vision()` (unreachable). Only consumer of WorkflowEngine. |
| 3024-3206 | `process_product_vision()` | **DELETE** | No caller. Was reached by `orchestrate_project` MCP tool (removed `d67f0d23`). |

**Lines to delete from orchestration_service.py**: ~278 lines (lines 2929-3206)

Also remove from the same file:
- **Line 35**: `from src.giljo_mcp.agent_selector import AgentSelector` (top-level import, no longer needed)
- **Line 39**: `from src.giljo_mcp.context_management.chunker import VisionDocumentChunker` (only used by `process_product_vision`)
- **Line 67**: `OrchestrationWorkflowResult,` from schema import block (only used by `process_product_vision`)
- **Line 74**: `from src.giljo_mcp.workflow_engine import WorkflowEngine` (only used by dead `workflow_engine` property)
- **Lines 1010-1012**: `self._agent_selector = None` and `self._workflow_engine = None` (in `__init__`)
- **Lines 1027-1049**: `agent_selector` and `workflow_engine` lazy properties + setters (~22 lines)

**Note**: Keep the `mission_planner` lazy property (lines 1015-1025) - it is used by `get_orchestrator_instructions()` at line 3313.

**Note**: Keep the MissionPlanner import at line 49 - it is used both by the lazy property AND the inline import at line 3229.

### Tier 4: Schema Cleanup

**File**: `src/giljo_mcp/schemas/service_responses.py`

| Lines | Symbol | Action | Justification |
|-------|--------|--------|---------------|
| 477-490 | `OrchestrationWorkflowResult` class | **DELETE** | Only used by `process_product_vision()` return type (being deleted). |

**File**: `src/giljo_mcp/schemas/__init__.py`

- **Line 29**: Remove `OrchestrationWorkflowResult` from import
- **Line 73**: Remove `"OrchestrationWorkflowResult"` from `__all__`

### Tier 5: Dead Test Files

| File | Lines | Action | Justification |
|------|-------|--------|---------------|
| `tests/unit/test_workflow_engine.py` | 866 | **DELETE** | Tests for WorkflowEngine (being deleted). |
| `tests/test_job_coordinator.py` | 680 | **DELETE** | Tests for JobCoordinator (being deleted). |
| `tests/unit/test_agent_selector.py` | 514 | **DELETE** | Tests for AgentSelector (being deleted). |

**File**: `tests/unit/test_orchestration_types.py` (682 lines total)

| Lines | Test Class | Action | Justification |
|-------|-----------|--------|---------------|
| 23-115 | `TestMission` | KEEP | Mission dataclass is kept. |
| 117-223 | `TestRequirementAnalysis` | KEEP | RequirementAnalysis dataclass is kept. |
| 225-328 | `TestAgentConfig` | KEEP | AgentConfig dataclass is kept. |
| 330-455 | `TestWorkflowStage` | **DELETE** | WorkflowStage dataclass being deleted. |
| 457-501 | `TestStageResult` | **DELETE** | StageResult dataclass being deleted. |
| 503-682 | `TestWorkflowResult` | **DELETE** | WorkflowResult dataclass being deleted. |

**Lines to delete from test_orchestration_types.py**: ~352 lines (lines 330-682)

**Total Tier 5**: ~2,412 lines of test code

---

## What NOT to Remove

These are ACTIVE systems that share namespace or proximity with the dead code:

| Symbol | File | Why It Is Active |
|--------|------|-----------------|
| `_generate_team_context_header()` | orchestration_service.py:84-212 | Called by `get_agent_mission()` (ACTIVE MCP tool). Handover 0353. |
| `dependency_rules` dict | Inside `_generate_team_context_header()` | Part of active team context headers. |
| `get_orchestrator_instructions()` | orchestration_service.py:3212 | ACTIVE MCP tool endpoint. |
| `MissionPlanner` class | mission_planner.py | Used by `get_orchestrator_instructions()` for `_build_fetch_instructions()`. |
| `mission_planner` property | orchestration_service.py:1015-1025 | Lazy init used by active `get_orchestrator_instructions()`. |
| `MissionPlanner` import (line 49) | orchestration_service.py | Used by lazy property (active). |
| `AgentConfig` dataclass | orchestration_types.py:95-136 | Imported by mission_planner.py and agent_selector.py. |
| `Mission` dataclass | orchestration_types.py:20-55 | Imported by mission_planner.py. |
| `RequirementAnalysis` dataclass | orchestration_types.py:58-91 | Imported by mission_planner.py. |
| `spawn_agent_job()` | orchestration_service.py | ACTIVE - used by orchestrator agents. |
| `get_workflow_status()` | orchestration_service.py:1101 | ACTIVE - referenced in thin_prompt_generator and exposed via tool_accessor. |
| All MissionPlanner test files | tests/unit/test_mission_planner*.py (6 files) | Test active MissionPlanner methods. Do NOT delete. |
| `VisionDocumentChunker` module | context_management/chunker.py | Used by product_service.py (active). Only the import in orchestration_service.py is dead. |

---

## Deferred Decisions (Out of Scope)

### MissionPlanner Audit

MissionPlanner (3,150 lines) is a large file with many methods. Some methods are only used through the dead `generate_mission_plan()` path (e.g., `analyze_requirements()`, `generate_mission()`, `generate_missions()`), while others are actively used (e.g., `_build_fetch_instructions()`, `_build_context_with_priorities()`). A targeted audit of which MissionPlanner methods are dead is recommended as a separate handover because:

1. The file is 3,150 lines with 40+ methods
2. Many methods are internal helpers called by both active and dead entry points
3. Incorrect removal could break `get_orchestrator_instructions()`
4. The MissionPlanner test suite (6 files, ~3,190 lines) needs careful triage

### AgentSelector Audit

AgentSelector (278 lines) is only imported by orchestration_service.py. After removing the dead orchestration_service.py methods, the only remaining reference would be the top-level import (which we are also removing). However, confirm no other files import it before deleting.

**Recommendation**: Delete `agent_selector.py` in this cleanup, but verify with the grep below first.

---

## Implementation Steps

### Step 1: Delete Entire Files (Tier 1)

```bash
git rm src/giljo_mcp/workflow_engine.py
git rm src/giljo_mcp/job_coordinator.py
git rm tests/unit/test_workflow_engine.py
git rm tests/test_job_coordinator.py
git rm tests/unit/test_agent_selector.py
```

### Step 2: Clean Up orchestration_types.py (Tier 2)

Delete lines 140-238 (WorkflowStage, StageResult, WorkflowResult dataclasses). Keep lines 1-136 (module docstring, Mission, RequirementAnalysis, AgentConfig).

Update the module docstring (lines 1-13) to remove references to WorkflowStage, StageResult, and WorkflowResult.

### Step 3: Clean Up orchestration_service.py (Tier 3)

1. Remove dead imports at the top of the file:
   - Line 35: `from src.giljo_mcp.agent_selector import AgentSelector`
   - Line 39: `from src.giljo_mcp.context_management.chunker import VisionDocumentChunker`
   - Line 67: `OrchestrationWorkflowResult,` from the schema import block
   - Line 74: `from src.giljo_mcp.workflow_engine import WorkflowEngine`

2. Remove dead `__init__` attributes:
   - Lines referencing `self._agent_selector` and `self._workflow_engine`

3. Remove dead lazy properties:
   - `agent_selector` property + setter (lines 1027-1037)
   - `workflow_engine` property + setter (lines 1039-1049)

4. Remove dead methods (lines 2929-3206):
   - `generate_mission_plan()`
   - `select_agents_for_mission()`
   - `coordinate_agent_workflow()`
   - `process_product_vision()`

### Step 4: Clean Up Schemas (Tier 4)

1. Delete `OrchestrationWorkflowResult` class from `src/giljo_mcp/schemas/service_responses.py` (lines 477-490)
2. Remove from `src/giljo_mcp/schemas/__init__.py`:
   - Line 29: import reference
   - Line 73: `__all__` entry

### Step 5: Clean Up test_orchestration_types.py (Tier 5)

Delete test classes for removed types (lines 330-682):
- `TestWorkflowStage`
- `TestStageResult`
- `TestWorkflowResult`

### Step 6: Conditional - Delete AgentSelector

Run verification first:
```bash
rg "AgentSelector|agent_selector" src/ --type py
```

If the only references are in:
- `agent_selector.py` (the file itself)
- `orchestration_service.py` (imports/properties being removed)
- `orchestration_types.py` (AgentConfig import - but AgentConfig stays)

Then delete:
```bash
git rm src/giljo_mcp/agent_selector.py
```

---

## Verification Steps

### Pre-Cleanup Verification

Run these searches to confirm no hidden callers exist:

```bash
# 1. Verify WorkflowEngine has no active callers
rg "WorkflowEngine" src/ --type py

# 2. Verify JobCoordinator has no active callers
rg "JobCoordinator|job_coordinator" src/ --type py

# 3. Verify process_product_vision has no active callers
rg "process_product_vision" src/ --type py

# 4. Verify coordinate_agent_workflow has no active callers
rg "coordinate_agent_workflow" src/ --type py

# 5. Verify AgentSelector has no active callers outside dead code
rg "AgentSelector|agent_selector" src/ --type py

# 6. Verify OrchestrationWorkflowResult has no active callers
rg "OrchestrationWorkflowResult" src/ --type py
```

### Post-Cleanup Verification

```bash
# 1. Run the full test suite
pytest tests/ -x -q

# 2. Verify no broken imports
python -c "from src.giljo_mcp.services.orchestration_service import OrchestrationService"
python -c "from src.giljo_mcp.orchestration_types import Mission, RequirementAnalysis, AgentConfig"
python -c "from src.giljo_mcp.mission_planner import MissionPlanner"

# 3. Verify active methods still work
pytest tests/unit/test_mission_planner.py -x -q
pytest tests/unit/test_orchestration_types.py -x -q

# 4. Verify no dangling references
rg "workflow_engine|WorkflowEngine" src/ --type py
rg "job_coordinator|JobCoordinator" src/ --type py
rg "WorkflowStage|StageResult|WorkflowResult" src/ --type py
rg "OrchestrationWorkflowResult" src/ --type py
```

---

## Risk Assessment

| Risk | Severity | Mitigation |
|------|----------|------------|
| Accidentally removing MissionPlanner | **HIGH** | MissionPlanner is ACTIVE via `get_orchestrator_instructions()`. Only delete methods confirmed dead. This handover explicitly defers MissionPlanner internal cleanup. |
| Breaking schema imports | LOW | `OrchestrationWorkflowResult` is only used by dead `process_product_vision()`. Remove from `__init__.py` exports simultaneously. |
| Missing a caller | LOW | Pre-cleanup grep verification confirms no hidden callers. The `orchestrate_project` tool was the only entry point and was definitively removed. |
| Test regressions | LOW | Only deleting tests for deleted code. Active test files (MissionPlanner, orchestration_types partial) are preserved. |
| VisionDocumentChunker import | NONE | The module is used elsewhere (product_service.py). Only the orchestration_service.py import line is dead. |

---

## Summary Table

| Category | Files | Lines Removed |
|----------|-------|---------------|
| Production code (entire files) | workflow_engine.py, job_coordinator.py | ~968 |
| Production code (partial cleanup) | orchestration_service.py | ~300 |
| Production code (partial cleanup) | orchestration_types.py | ~99 |
| Production code (schema cleanup) | service_responses.py, schemas/__init__.py | ~16 |
| Conditional: agent_selector.py | agent_selector.py | ~278 |
| Test code (entire files) | test_workflow_engine.py, test_job_coordinator.py, test_agent_selector.py | ~2,060 |
| Test code (partial cleanup) | test_orchestration_types.py | ~352 |
| **Total** | **~10 files touched** | **~4,073 lines** |

---

## Related Handovers

- **0020**: Original automated orchestration vision (October 2025) - created all this code
- **0353**: `_generate_team_context_header()` - ACTIVE dependency system, do NOT touch
- **0411**: Windows Terminal Agent Spawning - parent handover (superseded)
- **0411a**: Phase Labels - sibling handover, references WorkflowEngine as disconnected
- **0470**: Commit `d67f0d23` that removed `orchestrate_project` MCP tool, orphaning the pipeline

---

## Implementation Summary (2026-02-24)

### What Was Removed
- **8 entire files deleted**: workflow_engine.py, job_coordinator.py, agent_selector.py + 5 test files
- **4 files partially cleaned**: orchestration_service.py (~311 lines), orchestration_types.py (~100 lines), service_responses.py (~16 lines), test_orchestration_types.py (~350 lines)
- **2 additional dead test files found and deleted**: test_orchestration_service_consolidation.py (tested removed methods), test_stage_project_workflow.py (tested removed AgentSelector)
- **Total**: ~4,600 lines removed across 12 files (5,504 deletions in diff)

### Verification
- All grep searches for deleted symbols return zero hits in src/
- `ruff check src/ api/` passes clean (1 pre-existing issue in unrelated file)
- All critical imports verified: OrchestrationService, orchestration_types, MissionPlanner
- Pre-existing test failures (moderate vs medium assertions) confirmed NOT caused by this cleanup

### Active Code Preserved
- MissionPlanner (mission_planner.py) - used by get_orchestrator_instructions()
- mission_planner lazy property in OrchestrationService
- Mission, RequirementAnalysis, AgentConfig dataclasses
- _generate_team_context_header() and all active MCP tool endpoints
