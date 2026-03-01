# Monolith Split Plan

**Produced by:** 0750e Research Phase
**Date:** 2026-03-01
**Branch:** `0750-cleanup-sprint`
**Status:** PROPOSED — awaiting review before implementation

---

## 1. OrchestrationService Split

### Current State
- **File:** `src/giljo_mcp/services/orchestration_service.py`
- **Lines:** 3,427
- **Risk:** HIGH
- **Dependents:** 24 (7 production, 17 test)
- **Dependencies:** 13
- **TODOs:** 162

### File Structure

The file has two major regions:

| Region | Lines | Content |
|---|---|---|
| Imports | 1-76 | 76 lines of imports |
| Module-level functions | 77-981 | Protocol generation helpers (~886 lines) |
| OrchestrationService class | 984-3421 | The main class (~2,438 lines) |

### Method Inventory (by line count)

| Method | Lines | Start-End | Domain |
|---|---|---|---|
| `spawn_agent_job` | 444 | 1265-1708 | Spawn |
| `_build_orchestrator_protocol` (module) | 406 | 576-981 | Protocol |
| `get_orchestrator_instructions` | 303 | 3006-3308 | Mission/Instructions |
| `report_progress` | 269 | 2036-2304 | Job Lifecycle |
| `complete_job` | 268 | 2306-2573 | Job Lifecycle |
| `get_agent_mission` | 243 | 1710-1952 | Mission/Instructions |
| `_generate_agent_protocol` (module) | 207 | 209-415 | Protocol |
| `list_jobs` | 174 | 2733-2906 | Status/Query |
| `get_workflow_status` | 169 | 1091-1259 | Status/Query |
| `_generate_team_context_header` (module) | 130 | 77-206 | Protocol |
| `_get_user_config` (module) | 113 | 461-573 | Protocol |
| `report_error` | 104 | 2628-2731 | Job Lifecycle |
| `update_agent_mission` | 100 | 3310-3409 | Mission/Instructions |
| `_get_agent_template_internal` | 83 | 2918-3000 | Spawn |
| `get_pending_jobs` | 81 | 1954-2034 | Status/Query |
| `__init__` | 30 | 998-1027 | Infrastructure |
| `get_agent_result` | 31 | 2596-2626 | Job Lifecycle |
| `_normalize_field_priorities` (module) | 28 | 431-458 | Protocol |
| `_find_orchestrator_execution` | 20 | 2575-2594 | Job Lifecycle |
| `_get_session` | 18 | 1041-1058 | Infrastructure |
| `_can_warn_missing_todos` | 16 | 1060-1075 | Infrastructure |
| `health_check` | 11 | 3411-3421 | Status/Query |
| `_record_todo_warning` | 8 | 1077-1084 | Infrastructure |
| `mission_planner` (property) | 4 | 1036-1039 | Infrastructure |

### Proposed Split

#### Module A: `protocol_builder.py` (~886 lines)

Extract all module-level protocol generation functions. These are already decoupled from the class — they take explicit parameters, not `self`.

| Function | Lines | Currently At |
|---|---|---|
| `_generate_team_context_header` | 130 | 77-206 |
| `_generate_agent_protocol` | 207 | 209-415 |
| `DEFAULT_FIELD_PRIORITIES` | 1 | 427 |
| `DEFAULT_DEPTH_CONFIG` | 1 | 428 |
| `_normalize_field_priorities` | 28 | 431-458 |
| `_get_user_config` | 113 | 461-573 |
| `_build_orchestrator_protocol` | 406 | 576-981 |
| **Total** | **~886** | |

**Callers (internal):** `spawn_agent_job`, `get_agent_mission`, `get_orchestrator_instructions`
**External callers:** 3 test files directly import module-level functions.
**Risk:** LOW — these are pure functions, no shared state.
**Benefit:** Removes ~886 lines from the monolith with zero risk.

#### Module B: `job_lifecycle.py` (~692 lines)

Extract job completion, progress reporting, and error handling into a focused lifecycle manager.

| Method | Lines | Currently At |
|---|---|---|
| `report_progress` | 269 | 2036-2304 |
| `complete_job` | 268 | 2306-2573 |
| `report_error` | 104 | 2628-2731 |
| `_find_orchestrator_execution` | 20 | 2575-2594 |
| `get_agent_result` | 31 | 2596-2626 |
| **Total** | **~692** | |

**Production callers:**
- `api/endpoints/agent_jobs/lifecycle.py` → `complete_job`, `report_error`
- `api/endpoints/agent_jobs/progress.py` → `report_progress`
- `src/giljo_mcp/tools/tool_accessor.py` → `complete_job`, `report_progress`, `report_error`, `get_agent_result`

**Shared state needed:** `db_manager`, `tenant_manager`, `_test_session`, `_message_service`, `_websocket_manager`, `_logger`, `_todo_warning_timestamps`, `_get_session()`
**Risk:** MEDIUM — requires careful extraction of shared state.

#### Module C: Keep in `orchestration_service.py` (~860 lines remaining)

Keep spawn, mission, status, and infrastructure methods in the original file.

| Method | Lines | Domain |
|---|---|---|
| `__init__` | 30 | Infrastructure |
| `mission_planner` | 4 | Infrastructure |
| `_get_session` | 18 | Infrastructure |
| `_can_warn_missing_todos` | 16 | Infrastructure |
| `_record_todo_warning` | 8 | Infrastructure |
| `spawn_agent_job` | 444 | Spawn |
| `_get_agent_template_internal` | 83 | Spawn |
| `get_agent_mission` | 243 | Mission |
| `get_orchestrator_instructions` | 303 | Mission |
| `update_agent_mission` | 100 | Mission |
| `get_workflow_status` | 169 | Status |
| `get_pending_jobs` | 81 | Status |
| `list_jobs` | 174 | Status |
| `health_check` | 11 | Status |

**Rationale for keeping these together:** `spawn_agent_job`, the mission methods, and status methods all share heavy dependencies on the same DB models (AgentJob, AgentExecution, Project) and the same tenant isolation patterns. Splitting further would create multiple small files that all need the same imports and shared state, increasing complexity without proportional benefit.

### Shared Infrastructure

All methods use these shared resources:
- `self.db_manager` — DatabaseManager for session creation
- `self.tenant_manager` — TenantManager for tenant isolation
- `self._test_session` — Optional test session override
- `self._message_service` — MessageService for inter-agent messaging
- `self._websocket_manager` — WebSocketManager for real-time broadcasts
- `self._logger` — Logger
- `self._get_session()` — Session factory (uses test_session if available)

**Proposed pattern:** Composition with a shared context object.

```python
# orchestration_context.py (new, ~30 lines)
class OrchestrationContext:
    """Shared infrastructure for orchestration modules."""
    def __init__(self, db_manager, tenant_manager, ...):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._message_service = message_service
        self._websocket_manager = websocket_manager
        self._logger = logger

    def get_session(self):
        """Session factory."""
        ...
```

`OrchestrationService.__init__` creates the context and passes it to `JobLifecycleManager`. Both classes hold a reference to the same context.

### Migration Strategy

1. **Phase 1 (safe):** Extract `protocol_builder.py` — pure functions, no class state. Add re-exports from original file for backward compatibility.
2. **Phase 2:** Extract `job_lifecycle.py` with `OrchestrationContext`. Update API endpoint imports.
3. **Phase 3:** Remove re-exports from original file once all callers are updated.
4. **Backward compatibility:** During transition, the original `orchestration_service.py` re-exports moved symbols:
   ```python
   # Backward compatibility (remove after all callers updated)
   from .protocol_builder import _build_orchestrator_protocol, _generate_agent_protocol
   ```

### Post-Split File Sizes

| File | Lines | Change |
|---|---|---|
| `protocol_builder.py` (new) | ~886 | Extracted |
| `job_lifecycle.py` (new) | ~692 | Extracted |
| `orchestration_context.py` (new) | ~30 | New shared infra |
| `orchestration_service.py` | ~860 | From 3,427 |

---

## 2. tool_accessor.py Assessment

### Current State
- **File:** `src/giljo_mcp/tools/tool_accessor.py`
- **Lines:** 1,072
- **Risk:** MEDIUM
- **Dependents:** 10 (2 production, 8 test)
- **Dependencies:** 14

### Method Inventory by Domain

| Domain | Methods | Lines | % of File |
|---|---|---|---|
| **Project management** | create_project, list_projects, get_project, switch_project, complete_project, cancel_project, restore_project, update_project_mission, close_project_and_update_memory | ~156 | 15% |
| **Agent/Launch** | get_team_agents, gil_launch, write_360_memory, get_available_agents | ~169 | 16% |
| **Tasks** | log_task, create_task | ~104 | 10% |
| **Messaging** | send_message, get_messages, complete_message, broadcast, receive_messages, list_messages | ~88 | 8% |
| **Orchestration** | update_agent_mission, get_orchestrator_instructions, spawn_agent_job, get_agent_result, get_agent_mission, get_workflow_status, get_pending_jobs, report_progress, complete_job, report_error, health_check | ~80 | 7% |
| **Infrastructure** | __init__, get_session_async, generate_download_token | ~116 | 11% |
| **Product/Config** | get_product_settings, set_product_path, get_product_path | ~78 | 7% |
| **Templates** | list_templates, create_template, update_template, export_agents | ~54 | 5% |
| **Context/Vision** | get_context_index, get_vision, get_vision_index, fetch_context | ~53 | 5% |

### Recommendation: DO NOT SPLIT

**Rationale:**
1. **ToolAccessor is a facade/aggregator pattern** — it intentionally groups access to 7+ backend services into one unified interface. Most methods are 3-6 line pure delegation wrappers.
2. **Splitting would scatter the facade** across ~7 very small files (most <100 lines), each with only a handful of methods.
3. **Callers use methods from multiple domains** — `api/app.py` and `api/startup/core_services.py` use ToolAccessor as a single entry point. Splitting would require them to import from multiple files.
4. **No single-responsibility violation** — the responsibility IS being a facade. It's the adapter between MCP tools and backend services.
5. **At 1,072 lines, it's manageable** — especially since most methods are tiny.

---

## 3. Other Monolith Candidates

### Files >500 Lines Assessment

| File | Lines | Dependents | Monolith? | Recommendation |
|---|---|---|---|---|
| `project_service.py` | 2,821 | 20 | **Borderline** | Consider splitting closeout logic (~400 lines) into separate module in future. All methods relate to the same entity (projects), so this is a large-but-focused file. |
| `thin_prompt_generator.py` | 1,698 | 5 | No | Focused on prompt generation. Large due to template content, not complexity. |
| `product_service.py` | 1,679 | 13 | No | Focused single-entity service. Vision document upload (~193 lines) could extract but low priority. |
| `message_service.py` | 1,429 | 15 | No | Focused messaging service. `send_message` is oversized (439 lines) but that's a function extraction, not a file split. |
| `config_manager.py` | 1,233 | 16 | No | Configuration management, focused domain. |
| `user_service.py` | 1,165 | 3 | No | User management, low dependents. |
| `task_service.py` | 1,162 | 8 | No | Task management, focused domain. |
| `template_service.py` | 1,044 | 8 | No | Template CRUD, focused domain. |
| `template_manager.py` | 1,037 | 4 | No | Template loading/management. `_load_legacy_templates` is oversized (417 lines). |
| `service_responses.py` | 1,011 | 39 | No | Schema definitions (Pydantic models). High dependents but it's a schema registry, not a monolith. |
| `template_seeder.py` | 978 | 7 | No | Seeding logic, focused domain. |
| `auth_service.py` | 896 | 4 | No | Authentication, focused domain. |
| `statistics_repository.py` | 643 | 2 | No | Data access layer, focused. |
| `agent_job_manager.py` | 616 | 1 | No | Agent job management, focused. |
| `org_service.py` | 584 | 3 | No | Organization management, focused. |
| `write_360_memory.py` | 560 | 0 | No | Single tool, no dependents. |
| `slash_command_templates.py` | 542 | 1 | No | Template content, focused. |
| `project_closeout.py` | 535 | 2 | No | Closeout logic, focused. |
| `memory_instructions.py` | 528 | 0 | No | Prompt content, no dependents. |
| `agent_job_repository.py` | 524 | 2 | No | Data access layer, focused. |
| `agent_health_monitor.py` | 513 | 2 | No | Monitoring, focused domain. |

### Summary

Only **orchestration_service.py** is a genuine monolith requiring splitting. `project_service.py` is borderline but acceptable — all its methods operate on the same entity. All other large files are focused single-domain modules.

---

## 4. Oversized Functions (>250 Lines)

The original audit (H-16) identified 4 oversized functions. This research found **8 functions >250 lines**:

### In orchestration_service.py (5 functions)

| Function | Lines | Start-End | Proposed Extraction |
|---|---|---|---|
| `spawn_agent_job` | 444 | 1265-1708 | Extract: `_validate_spawn_request()` (~60 lines), `_create_agent_records()` (~100 lines), `_build_spawn_broadcast()` (~80 lines). Core orchestration logic stays. |
| `_build_orchestrator_protocol` | 406 | 576-981 | Extract: `_build_team_section()` (~100 lines), `_build_rules_section()` (~100 lines), `_build_instructions_section()` (~100 lines). Each section becomes its own helper. |
| `get_orchestrator_instructions` | 303 | 3006-3308 | Extract: `_build_context_frame()` (~80 lines), `_build_phase_instructions()` (~60 lines). |
| `report_progress` | 269 | 2036-2304 | Extract: `_validate_progress_data()` (~40 lines), `_broadcast_progress()` (~60 lines), `_check_todo_warnings()` (~50 lines). |
| `complete_job` | 268 | 2306-2573 | Extract: `_validate_completion()` (~40 lines), `_handle_successor_spawn()` (~60 lines), `_broadcast_completion()` (~50 lines). |

### In other files (3 functions)

| Function | File | Lines | Start-End | Proposed Extraction |
|---|---|---|---|---|
| `send_message` | `services/message_service.py` | 439 | 123-561 | Extract: `_validate_message()` (~50 lines), `_resolve_recipients()` (~80 lines), `_store_message()` (~60 lines), `_broadcast_message()` (~50 lines). Large due to message routing complexity + deadlock retry logic. |
| `_load_legacy_templates` | `template_manager.py` | 417 | 161-577 | Extract: `_parse_template_file()` (~80 lines), `_validate_template_schema()` (~60 lines), `_build_template_model()` (~80 lines). Large due to parsing multiple template formats. |
| `_build_claude_code_execution_prompt` | `thin_prompt_generator.py` | 272 | 1270-1541 | Extract: `_build_tool_instructions()` (~80 lines), `_build_execution_rules()` (~60 lines). Large due to prompt template assembly. |

### Priority Order for Extraction

1. **HIGH:** `spawn_agent_job` (444 lines) — most complex, most callers, hardest to debug
2. **HIGH:** `send_message` (439 lines) — critical messaging path
3. **MEDIUM:** `_build_orchestrator_protocol` (406 lines) — already module-level, easier to split
4. **MEDIUM:** `_load_legacy_templates` (417 lines) — template parsing, lower risk
5. **MEDIUM:** `get_orchestrator_instructions` (303 lines) — instruction builder
6. **LOW:** `_build_claude_code_execution_prompt` (272 lines) — prompt template, mainly string assembly
7. **LOW:** `report_progress` (269 lines) — lifecycle method
8. **LOW:** `complete_job` (268 lines) — lifecycle method

---

## 5. Estimated Effort

| Work Item | Sessions | Complexity | Notes |
|---|---|---|---|
| Extract `protocol_builder.py` | 1 | LOW | Pure functions, no shared state. Safe first step. |
| Extract `job_lifecycle.py` | 1-2 | MEDIUM | Shared state extraction, caller updates needed. |
| Extract oversized functions in orchestration_service.py | 1-2 | MEDIUM | 5 functions need internal decomposition. Can be done incrementally. |
| Extract `send_message` helpers | 0.5 | LOW | Internal to MessageService, no external API change. |
| Extract `_load_legacy_templates` helpers | 0.5 | LOW | Internal to TemplateManager. |
| Extract `_build_claude_code_execution_prompt` helpers | 0.5 | LOW | Internal to ThinPromptGenerator. |
| **Total** | **4-6 sessions** | | Recommended order: protocol_builder → oversized functions → job_lifecycle → other files |

---

## 6. Implementation Order

1. **Phase A:** Extract `protocol_builder.py` (lowest risk, biggest line reduction)
2. **Phase B:** Decompose oversized functions within `orchestration_service.py` (reduces individual method complexity)
3. **Phase C:** Extract `job_lifecycle.py` with shared context (requires Phase B's cleaner methods)
4. **Phase D:** Decompose oversized functions in other files (`send_message`, `_load_legacy_templates`, `_build_claude_code_execution_prompt`)

Phases A-C address the OrchestrationService monolith. Phase D is independent and can run in parallel with any phase.
