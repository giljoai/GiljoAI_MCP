# 0750e2: Monolith Split Execution — Protocol Builder Extraction

**Series:** 0750 (Code Quality Cleanup Sprint)
**Phase:** 5 of 7 (Session 2 — EXECUTION)
**Branch:** `0750-cleanup-sprint`
**Priority:** MEDIUM — architecture improvement

### Reference Documents
- **Split plan:** `handovers/MONOLITH_SPLIT_PLAN.md` (read this FIRST — it has the full analysis)
- **Roadmap:** `handovers/CLEANUP_ROADMAP_2026_02_28.md` (Phase 5 section)
- **Dependency graph:** `docs/cleanup/dependency_graph.json` (already refreshed by 0750e)
- **Previous phase notes:** Read `prompts/0750_chain/chain_log.json` session 0750e `notes_for_next`

### Tracking Files (update these when done)
- **Chain log:** `prompts/0750_chain/chain_log.json`
- **Progress tracker:** `handovers/0700_series/0750_cleanup_progress.json`

---

## Context

The 0750e research phase produced `MONOLITH_SPLIT_PLAN.md` with a detailed analysis. The plan recommends 4 phases of extraction. This session executes **Phase A** (protocol_builder extraction) and **Phase B** (oversized function decomposition) — the two safest, highest-impact changes.

**Phase A** extracts ~886 lines of pure module-level functions from `orchestration_service.py` into a new `protocol_builder.py`. These are stateless functions with zero shared class state — lowest possible risk.

**Phase B** decomposes the 5 oversized functions (>250 lines) inside `orchestration_service.py` by extracting helper methods. This reduces individual method complexity without changing the file structure.

---

## Scope

### Task 1: Extract `protocol_builder.py` (Phase A from split plan)

Create `src/giljo_mcp/services/protocol_builder.py` containing these module-level functions currently in `orchestration_service.py`:

| Function | Lines | Currently At |
|---|---|---|
| `_generate_team_context_header` | 130 | 77-206 |
| `_generate_agent_protocol` | 207 | 209-415 |
| `DEFAULT_FIELD_PRIORITIES` (constant) | 1 | 427 |
| `DEFAULT_DEPTH_CONFIG` (constant) | 1 | 428 |
| `_normalize_field_priorities` | 28 | 431-458 |
| `_get_user_config` | 113 | 461-573 |
| `_build_orchestrator_protocol` | 406 | 576-981 |

**Steps:**
- [ ] Read the full block (lines 77-981) from `orchestration_service.py`
- [ ] Create `src/giljo_mcp/services/protocol_builder.py` with these functions and their necessary imports
- [ ] Remove lines 77-981 from `orchestration_service.py`
- [ ] Add import in `orchestration_service.py`:
  ```python
  from giljo_mcp.services.protocol_builder import (
      _generate_team_context_header,
      _generate_agent_protocol,
      _normalize_field_priorities,
      _get_user_config,
      _build_orchestrator_protocol,
      DEFAULT_FIELD_PRIORITIES,
      DEFAULT_DEPTH_CONFIG,
  )
  ```
- [ ] Add backward-compatible re-exports at the end of `orchestration_service.py` (so external callers don't break):
  ```python
  # Backward compatibility — functions moved to protocol_builder.py
  # Remove these re-exports after all callers are updated
  ```
  Actually, the imports above already make them available. Check if any external file does `from orchestration_service import _build_orchestrator_protocol` — if so, the import line handles it.
- [ ] Find external callers: per the split plan, 3 test files directly import module-level functions. Update their imports.
- [ ] Run tests: `python -m pytest tests/ -x -q --timeout=60`

### Task 2: Decompose Oversized Functions (Phase B from split plan)

Within `orchestration_service.py`, extract helper methods from the 5 functions >250 lines. Do NOT move them to other files — just extract sub-methods within the same class or as module-level helpers.

**2a: `spawn_agent_job` (444 lines)**
- [ ] Extract `_validate_spawn_request()` (~60 lines) — input validation and precondition checks
- [ ] Extract `_create_agent_records()` (~100 lines) — DB record creation for AgentJob + AgentExecution
- [ ] Extract `_build_spawn_broadcast()` (~80 lines) — WebSocket broadcast assembly

**2b: `get_orchestrator_instructions` (303 lines)**
- [ ] Extract `_build_context_frame()` (~80 lines) — context assembly
- [ ] Extract `_build_phase_instructions()` (~60 lines) — phase-specific instruction building

**2c: `report_progress` (269 lines)**
- [ ] Extract `_validate_progress_data()` (~40 lines)
- [ ] Extract `_broadcast_progress()` (~60 lines)
- [ ] Extract `_check_todo_warnings()` (~50 lines)

**2d: `complete_job` (268 lines)**
- [ ] Extract `_validate_completion()` (~40 lines)
- [ ] Extract `_handle_successor_spawn()` (~60 lines)
- [ ] Extract `_broadcast_completion()` (~50 lines)

**NOTE:** `_build_orchestrator_protocol` (406 lines) is already being moved to `protocol_builder.py` in Task 1, so decompose it there instead:
- [ ] Extract `_build_team_section()` (~100 lines)
- [ ] Extract `_build_rules_section()` (~100 lines)
- [ ] Extract `_build_instructions_section()` (~100 lines)

After each function decomposition, run tests to verify no regressions.

### Task 3: Verify results

```bash
# Verify orchestration_service.py is significantly reduced
wc -l src/giljo_mcp/services/orchestration_service.py
# Target: ~2,500 lines (down from 3,427)

# Verify no function >250 lines remains in the file
# (Manual check using get_symbols_overview)

# Full test suite
python -m pytest tests/ -x -q --timeout=60
```

---

## What NOT To Do

- Do NOT extract `job_lifecycle.py` in this session — that requires shared state extraction (Phase C, future work)
- Do NOT split `tool_accessor.py` — the research concluded it's a facade pattern, splitting is counterproductive
- Do NOT modify files outside `src/giljo_mcp/services/` except for updating imports in test files
- Do NOT change any function signatures or return values — this is a structural refactor, not a behavioral change
- Do NOT remove the backward-compatible imports until all callers are verified

---

## Acceptance Criteria

- [ ] `src/giljo_mcp/services/protocol_builder.py` exists with ~886 lines of extracted functions
- [ ] `orchestration_service.py` reduced by ~886 lines (from 3,427 to ~2,541)
- [ ] No function >300 lines remains in `orchestration_service.py` (target: all <250)
- [ ] All imports updated — no broken references
- [ ] Test suite still GREEN: ~1416 passed, ~342 skipped, 0-2 failed (pre-existing)
- [ ] No behavioral changes — all functions produce identical outputs

---

## Completion Steps

### Step 1: Verify branch
```bash
git branch --show-current
# Must show: 0750-cleanup-sprint
```

### Step 2: Commit (split into logical commits)
```bash
# Commit 1: Protocol builder extraction
git add src/giljo_mcp/services/protocol_builder.py src/giljo_mcp/services/orchestration_service.py tests/
git commit -m "refactor(0750e2): Extract protocol_builder.py from orchestration_service — 886 lines moved"

# Commit 2: Oversized function decomposition
git add src/giljo_mcp/services/orchestration_service.py src/giljo_mcp/services/protocol_builder.py
git commit -m "refactor(0750e2): Decompose 5 oversized functions in orchestration_service"
```

### Step 3: Record commit hash
```bash
git rev-parse --short HEAD
```

### Step 4: Update chain log
Read `prompts/0750_chain/chain_log.json`, update session `0750e`:
- Update `"tasks_completed"` to include execution results
- Update `"notes_for_next"`: remaining split work (job_lifecycle extraction = Phase C, other file decompositions = Phase D), new file sizes
- Update `"summary"` to cover both research and execution

### Step 5: Update progress tracker
Read `handovers/0700_series/0750_cleanup_progress.json`, update `phases[4]`:
- Add new commit hashes to `"commits"` array
- Update `"notes"` with post-split file sizes

### Step 6: Done
Do NOT spawn the next terminal.
Print "0750e2 COMPLETE" as your final message with the new line counts.
