# Handover 0766a: Research & Validate Mission/Progress Overwrite Risk

**Date:** 2026-03-04
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** Critical
**Estimated Complexity:** 1-2 hours
**Status:** Not Started
**Chain:** 0766a (Research) -> 0766b (Implementation)

---

## Task Summary

Two MCP tools silently destroy data when called by agents during multi-phase or continuation workflows. Your job is to **validate the problem**, **map all affected code paths**, and **propose production-grade fixes** — then write your findings to the chain log JSON so the implementation agent (0766b) can execute.

### The Two Bugs

**CW-1 (Critical) — Mission Overwrites:**
`update_project_mission()` and `update_agent_mission()` do pure SQL/ORM replacement of the `mission` field. When a continuation orchestrator calls these to set phase 2 instructions, all phase 1 context is silently destroyed. There is no append mode, no history, no warning.

**CW-3 (Medium) — Todo List Overwrites:**
`report_progress()` handles `todo_items` with a DELETE-all-then-INSERT strategy. Every call wipes all existing `AgentTodoItem` rows for that job and re-inserts only what was provided. If a continuation session sends only its new todos, all previous session's todos are gone.

---

## Context and Background

This project (GiljoAI MCP) is a multi-agent orchestration platform. The workflow is:
1. User creates a **Project** with requirements
2. An **Orchestrator** agent analyzes requirements, creates a **mission plan**, and saves it via `update_project_mission()`
3. The orchestrator spawns **specialist agents** who receive missions via `update_agent_mission()`
4. Agents report progress via `report_progress()` with `todo_items` arrays
5. When work completes, a **continuation/successor orchestrator** may be spawned to handle the next phase

The overwrite bugs bite in step 5: the successor orchestrator calls `update_project_mission()` with the new phase plan, destroying the original mission. Similarly, successor agents calling `report_progress()` wipe the predecessor's todo history.

### Why This Matters for Production

- Mission is displayed on the dashboard — users see it disappear/change without explanation
- 360 Memory system references missions for historical context
- Agents may need to reference prior phases during execution
- Todo items are the primary progress tracking mechanism in the dashboard

---

## Technical Details — Files to Investigate

### Primary Files (READ THESE BODIES)

| File | Symbol | Lines | What to Look For |
|------|--------|-------|------------------|
| `src/giljo_mcp/services/project_service.py` | `ProjectService.update_project_mission` | 549-626 | The `.values(mission=mission)` replacement |
| `src/giljo_mcp/services/orchestration_service.py` | `OrchestrationService.update_agent_mission` | 2575-2674 | The `job.mission = mission` replacement |
| `src/giljo_mcp/services/orchestration_service.py` | `OrchestrationService.report_progress` | 1278-1506 | The DELETE+INSERT todo strategy |
| `src/giljo_mcp/tools/tool_accessor.py` | `ToolAccessor.update_project_mission` | 177-181 | Pass-through to service |
| `src/giljo_mcp/tools/tool_accessor.py` | `ToolAccessor.update_agent_mission` | 184-186 | Pass-through to service |
| `src/giljo_mcp/tools/tool_accessor.py` | `ToolAccessor.report_progress` | 482-499 | Pass-through to service |
| `api/endpoints/mcp_http.py` | MCP tool schemas + tool_map | ~210-870 | Tool parameter definitions — check if `mode` param exists |

### Secondary Files (CHECK FOR CALLERS/REFERENCES)

| File | What to Look For |
|------|------------------|
| `src/giljo_mcp/thin_prompt_generator.py` | How agents are instructed to call `update_project_mission()` — protocol instructions |
| `src/giljo_mcp/services/protocol_builder.py` | How agents are instructed to call `update_project_mission()` — startup sequence |
| `api/endpoints/agent_jobs/progress.py` | The REST API endpoint for `report_progress` |
| `api/endpoints/agent_jobs/operations.py` | Check for any mission-update endpoints |
| `src/giljo_mcp/models/project.py` or wherever `Project` model lives | Check if `mission` field has any history mechanism |
| `src/giljo_mcp/models/agent_identity.py` | Check `AgentJob.mission` field definition |
| `src/giljo_mcp/models/` | Find `AgentTodoItem` model — check for soft-delete, archival fields |

### Model Discovery (FIND THESE)

Use Serena `find_symbol` to locate:
- `Project` model class — check all fields, especially anything related to mission history
- `AgentJob` model class — check mission field definition
- `AgentTodoItem` model class — check all fields, indexes, constraints
- `AgentExecution` model class — check if progress fields exist here too

---

## Research Tasks (Execute in Order)

### Task 1: Validate CW-1 — Mission Overwrite

1. Read `ProjectService.update_project_mission()` body
2. Confirm it does `.values(mission=mission)` (pure replacement)
3. Read `OrchestrationService.update_agent_mission()` body
4. Confirm it does `job.mission = mission` (pure replacement)
5. Check the `Project` model — is there ANY mission history, version, or previous_mission field?
6. Check the `AgentJob` model — same question
7. Search the codebase for any `mission_history` or `previous_mission` pattern

### Task 2: Validate CW-3 — Todo Overwrite

1. Read `OrchestrationService.report_progress()` body
2. Find the DELETE statement for `AgentTodoItem`
3. Confirm it deletes ALL items for the job, then re-inserts
4. Read the `AgentTodoItem` model — is there a `created_at`, `session_id`, or `execution_id` field?
5. Check if there's any mechanism to distinguish "which session created this todo"

### Task 3: Map All Callers

Find every place these functions are called:
1. `update_project_mission` — all callers across the codebase
2. `update_agent_mission` — all callers across the codebase
3. `report_progress` — all callers across the codebase (service + API + MCP + tests)
4. Document the call chain: MCP tool -> tool_accessor -> service -> database

### Task 4: Check MCP Schema & Agent Instructions

1. Read the MCP tool schema for `update_project_mission` in `mcp_http.py` (~line 326)
2. Read the MCP tool schema for `update_agent_mission` in `mcp_http.py` (~line 338)
3. Read the MCP tool schema for `report_progress` in `mcp_http.py` (~line 539)
4. Check if ANY of these already have a `mode` parameter
5. Read `thin_prompt_generator.py` — search for `update_project_mission` to see how agents are told to use it
6. Read `protocol_builder.py` — same search

### Task 5: Assess Backward Compatibility

1. What happens if we add `mode="replace"` (default) / `mode="append"` to `update_project_mission`?
2. Does this break any existing agents? (They don't pass `mode`, so default would be backward-compatible)
3. For todo items: what would `mode="merge"` look like? (Keep existing items, add/update new ones by content match?)
4. Is there a simpler approach for todos? (e.g., separate `add_todo_items()` tool instead of mode parameter?)

### Task 6: Propose Fixes

For each bug, propose at least 2 approaches with:
- **Approach name**
- **What changes** (which files, which functions)
- **New parameters** (if any)
- **Backward compatibility** (does default behavior stay the same?)
- **Database changes** (new columns? new tables?)
- **Estimated lines of code**
- **Recommended approach** and why

---

## Chain Log Instructions

### Step 1: Mark Session Started
Read `F:\GiljoAI_MCP\prompts\0766_chain\chain_log.json`
Update session `0766a`:
- `"status": "in_progress"`
- `"started_at": "<current ISO timestamp>"`

### Step 2: Execute Research Tasks (above)

### Step 3: Write Findings to Chain Log
Update session `0766a` in chain_log.json with:
- `"tasks_completed"`: List what you actually investigated
- `"findings"`: A detailed object with your research results
- `"proposed_fix_cw1"`: Your recommended fix for mission overwrites
- `"proposed_fix_cw3"`: Your recommended fix for todo overwrites
- `"files_investigated"`: List of files you read
- `"callers_found"`: List of all callers found for the 3 functions
- `"deviations"`: Any changes from the research plan
- `"blockers_encountered"`: Any issues found
- `"notes_for_next"`: Critical info the implementation agent needs
- `"summary"`: 3-5 sentence summary of findings
- `"status": "complete"`
- `"completed_at": "<current ISO timestamp>"`

### Findings Object Structure

Write your findings in this structure within the chain_log.json:

```json
{
  "cw1_mission_overwrite": {
    "confirmed": true/false,
    "current_behavior": "description of what happens",
    "affected_functions": ["list of function paths"],
    "model_has_history_field": true/false,
    "existing_callers": ["list"],
    "risk_scenarios": ["scenario 1", "scenario 2"],
    "proposed_fixes": [
      {
        "name": "Approach A",
        "description": "...",
        "files_to_change": ["..."],
        "new_params": {"param": "description"},
        "backward_compatible": true/false,
        "db_changes": "none/description",
        "estimated_loc": 0,
        "recommended": true/false,
        "rationale": "..."
      }
    ]
  },
  "cw3_todo_overwrite": {
    "confirmed": true/false,
    "current_behavior": "description",
    "delete_statement_location": "file:line",
    "model_fields": ["list of AgentTodoItem fields"],
    "has_session_tracking": true/false,
    "proposed_fixes": [
      {
        "name": "Approach A",
        "description": "...",
        "files_to_change": ["..."],
        "backward_compatible": true/false,
        "estimated_loc": 0,
        "recommended": true/false,
        "rationale": "..."
      }
    ]
  }
}
```

---

## Success Criteria

- [ ] Both CW-1 and CW-3 bugs are confirmed or refuted with code evidence
- [ ] ALL callers of the 3 affected functions are identified
- [ ] Model fields checked for existing history/versioning mechanisms
- [ ] At least 2 fix approaches proposed for each bug
- [ ] Each approach includes backward compatibility assessment
- [ ] Findings written to chain_log.json in the specified structure
- [ ] Chain log session status set to "complete"

---

## DO NOT

- Do NOT implement any fixes — this is research only
- Do NOT modify any source code files
- Do NOT create commits
- Do NOT spawn the next terminal — the orchestrator (user) will do that after reviewing your findings

---

## Tools Available

- **Serena MCP tools**: `find_symbol`, `get_symbols_overview`, `find_referencing_symbols`, `search_for_pattern` — use these for efficient codebase navigation
- **Read**: For reading full file contents when Serena overview isn't enough
- **Grep/Glob**: For broader pattern searches
- **Write**: Only for updating the chain_log.json

---

## Reference Files

- Chain Log: `F:\GiljoAI_MCP\prompts\0766_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
- Feb Handover Report (Section 6): `F:\GiljoAI_MCP\handovers\Handover_report_feb.md`
- Multi-Terminal Strategy: `F:\GiljoAI_MCP\handovers\Reference_docs\MULTI_TERMINAL_CHAIN_STRATEGY.md`
