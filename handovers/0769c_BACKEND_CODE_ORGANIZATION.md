# 0769c: Backend Code Organization

**Series:** 0769 (Code Quality & Fragility Remediation Sprint)
**Phase:** 3 of 7
**Branch:** `feature/0769-quality-sprint`
**Priority:** HIGH — structural debt, change hotspots
**Estimated Time:** 4-5 hours

### Reference Documents
- **Audit report:** `handovers/0769_CODE_QUALITY_FRAGILITY_AUDIT.md` (sections H3, H4, F2, F7)
- **Project rules:** `CLAUDE.md`, `handovers/HANDOVER_INSTRUCTIONS.md`

### Tracking Files
- **Chain log:** `prompts/0769_chain/chain_log.json`

---

## Context

Three backend service classes have grown far beyond the 1000-line project limit: OrchestrationService (3,333 lines, 84 changes in 2 months), ProjectService (2,803 lines, 51 changes), and MessageService (1,680 lines). These are the top change hotspots and primary source of fragility. Multiple functions also exceed the 200-line limit.

This phase splits the god classes into focused modules and reduces oversized functions.

---

## Scope

### Task 1: Split OrchestrationService (3,333 lines -> ~4 modules)

**File:** `src/giljo_mcp/services/orchestration_service.py`

**Split plan:**

**New: `src/giljo_mcp/services/job_lifecycle_service.py`** (~600 lines)
Extract these methods:
- `spawn_agent_job` (line 368, 210 lines)
- `_validate_spawn_agent` (line 687, 124 lines)
- `_resolve_spawn_template` (line 812, 53 lines)
- `_build_predecessor_context` (line 579, 107 lines)
- `_broadcast_agent_created` (line 866, 52 lines)

**New: `src/giljo_mcp/services/mission_service.py`** (~800 lines)
Extract these methods:
- `get_agent_mission` (line 919, 348 lines)
- `get_orchestrator_instructions` (line 2881, 283 lines)
- `update_agent_mission` (line 3165, 151 lines)
- `_get_agent_template_internal` (line 2714, 83 lines)
- `_build_execution_mode_fields` (line 2802, 78 lines)

**New: `src/giljo_mcp/services/progress_service.py`** (~450 lines)
Extract these methods:
- `report_progress` (line 1350, 382 lines)
- `_fetch_and_broadcast_progress` (line 1733, 50 lines)

**Keep in OrchestrationService** (~1,400 lines — facade):
- `__init__`, `_get_session`, `mission_planner`
- `get_workflow_status`, `get_pending_jobs`, `list_jobs`
- `complete_job`, `_broadcast_completion`, `get_agent_result`
- `reactivate_job`, `dismiss_reactivation`, `report_error`
- `_find_orchestrator_execution`, `_can_warn_missing_todos`, `_record_todo_warning`, `health_check`

**Facade pattern:** OrchestrationService keeps a reference to each extracted service and delegates calls. Existing callers of `orchestration_service.spawn_agent_job()` continue to work — the facade method just calls `self._job_lifecycle.spawn_agent_job()`.

**CRITICAL:** Use `find_referencing_symbols` or grep for every method being moved. Update ALL callers. Test with `ruff check src/ api/` after each extraction.

### Task 2: Split ProjectService (2,803 lines -> ~4 modules)

**File:** `src/giljo_mcp/services/project_service.py`

**New: `src/giljo_mcp/services/project_lifecycle_service.py`** (~500 lines)
- `activate_project` (line 1090, 127 lines)
- `_ensure_orchestrator_fixture` (line 1218, 116 lines)
- `deactivate_project` (line 1335, 79 lines)
- `cancel_staging` (line 1415, 78 lines)
- `complete_project` (line 691, 69 lines)
- `_complete_project_transaction` (line 761, 79 lines)
- `cancel_project` (line 841, 58 lines)
- `continue_working` (line 993, 96 lines)

**New: `src/giljo_mcp/services/project_closeout_service.py`** (~300 lines)
- `close_out_project` (line 900, 92 lines)
- `get_closeout_data` (line 1615, 19 lines)
- `can_close_project` (line 1635, 23 lines)
- `generate_closeout_prompt` (line 1659, 23 lines)
- `_build_closeout_data` (line 1683, 35 lines)
- `_build_can_close_response` (line 1719, 36 lines)
- `_build_closeout_prompt` (line 1756, 62 lines)
- `_aggregate_agent_statuses` (line 1819, 33 lines)

**New: `src/giljo_mcp/services/project_deletion_service.py`** (~450 lines)
- `delete_project` (line 2487, 78 lines)
- `nuclear_delete_project` (line 2273, 166 lines)
- `_purge_project_records` (line 2440, 46 lines)
- `purge_all_deleted_projects` (line 2595, 50 lines)
- `purge_expired_deleted_projects` (line 2646, 81 lines)
- `restore_project` (line 2225, 43 lines)

**Keep in ProjectService** (~1,200 lines — CRUD + launch + summary):
- `__init__`, `_get_session`
- `create_project`, `get_project`, `get_active_project`, `list_projects`
- `update_project`, `update_project_mission`
- `get_project_summary`, `launch_project`
- `_get_project_for_tenant`, `_apply_project_updates`, `_build_project_data`
- `_broadcast_memory_update`, `_broadcast_mission_update`
- `get_project_type_by_label`

**Note:** Delete dead method `purge_deleted_project` (line 2566) — zero references.

### Task 3: Reduce Oversized Functions

Split the worst offenders. Do NOT split ALL 16 — focus on the top 5 exceeding 250 lines:

1. **`report_progress`** (382 lines) — Extract TODO processing into `_process_todo_items()`, broadcast logic into `_broadcast_progress_update()`
2. **`get_agent_mission`** (348 lines) — Extract template resolution into `_resolve_mission_template()`, context assembly into `_assemble_mission_context()`
3. **`receive_messages`** (311 lines) — Extract filtering logic, pagination logic
4. **`complete_job`** (299 lines) — Extract post-completion side effects into `_handle_completion_side_effects()`
5. **`_load_legacy_templates`** (417 lines in template_manager.py) — Extract per-template-type loaders

### Task 4: Introduce Parameter Dataclasses

Create `src/giljo_mcp/services/dto.py` (or add to existing models) with:

```python
@dataclass
class BroadcastContext:
    """Groups the 13 parameters of _broadcast_message_events"""
    tenant_key: str
    project_id: int
    sender_execution_id: int | None
    # ... etc

@dataclass
class SpawnRequest:
    """Groups the 10 parameters of spawn_agent_job"""
    project_id: int
    agent_template_id: int
    # ... etc
```

Update the worst offenders: `_broadcast_message_events` (13 params), `_broadcast_agent_created` (11 params), `spawn_agent_job` (10 params).

### Task 5: Housekeeping

- Delete 3 dead methods: `port_manager.py:check_all_ports_available`, `jwt_manager.py:decode_token_no_verify`, `project_service.py:purge_deleted_project`
- Fix 4 config bypass sites: replace inline `yaml.safe_load` with `_config_io.read_config()` in `thin_prompt_generator.py:73`, `discovery.py:133`, `config_service.py:80`, `port_manager.py:143`

---

## What NOT To Do

- Do NOT change any public API endpoint signatures
- Do NOT modify frontend code
- Do NOT modify test files (0769b handles that)
- Do NOT refactor MessageService into separate files — at 1,680 lines it's borderline; just split the oversized functions within it
- Do NOT rename any service class — keep backward-compatible facades

---

## Acceptance Criteria

- [ ] OrchestrationService <= 1,500 lines (down from 3,333)
- [ ] ProjectService <= 1,300 lines (down from 2,803)
- [ ] No function exceeds 200 lines (top 5 split)
- [ ] No class exceeds 1,500 lines
- [ ] 3 dead methods deleted
- [ ] 4 config bypass sites fixed
- [ ] Parameter dataclasses introduced for 10+ param methods
- [ ] `ruff check src/ api/` passes with 0 issues
- [ ] `npx vitest run` failure count does not increase from 0769b's final count
- [ ] All existing API endpoints still work (no broken imports)

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0769_chain/chain_log.json`
- Check `orchestrator_directives`
- Review 0769b's `notes_for_next` for any component API changes

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Work through Tasks 1-5. Run `ruff check src/ api/` after each major extraction.

### Step 4: Update Chain Log
In `notes_for_next`, include:
- New service file paths and class names
- Any method that was renamed or had its signature change
- Import paths that changed

### Step 5: STOP
Do NOT spawn the next terminal. Commit chain log update and exit.
