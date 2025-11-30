# Handover 0261: Task MCP Surface Rationalization (Keep/Retool `create_task`, Remove Others)

**Date**: 2025-11-29  
**Status**: READY FOR IMPLEMENTATION  
**Priority**: Medium  
**Scope**: MCP task tool surface  
**Goal**: Remove MCP task tools except `create_task`; refactor `create_task` to accept a “punt findings to task” payload from CLI agent tools.

---

## Background
- Current MCP HTTP task tools (exposed via `api/endpoints/mcp_http.py -> ToolAccessor`):
  - `create_task`, `list_tasks`, `update_task`, `assign_task`, `complete_task`
- UI visualization at `http://10.1.0.164:7274/tasks` uses REST endpoints (`api/endpoints/tasks.py`), not these MCP tools.
- Token savings from removal are negligible; benefit is reduced surface area and forcing task CRUD through REST/UI, except for a “punt findings” path.

---

## Objective
1) **Retain and retool `create_task` (MCP)** to accept a conversational payload from CLI/agent tools (“punt findings to task”), auto-filling a task template from the agent’s last response.
2) **Remove all other task MCP tools** from the HTTP surface (`list_tasks`, `update_task`, `assign_task`, `complete_task`).
3) Ensure REST/UI task management remains intact and unaffected.

---

## Desired `create_task` behavior (MCP)
- Purpose: Let an agent/CLI quickly “punt” its current findings into a task without context switching.
- Input: A single structured payload (e.g., `summary`, `details`, optional `category/priority/product_id/project_id`).
- Behavior: 
  - Compose a task title/description from the payload (e.g., “Punted finding: <summary>”).
  - Store in DB via existing Task model, respecting tenant/product/project isolation.
  - Return the created task id and echo back normalized fields.
- Prompt guidance to agents (thin prompt snippet):  
  “Use `/mcp create_task` to capture your last findings; include `summary` and `details` from your previous response.”
- Keep backward compatibility with minimal parameter changes; prefer adding a single `payload`/`details` arg over breaking existing required args.

---

## Tasks for Implementation Agent
1) **Update MCP HTTP surface**
   - In `api/endpoints/mcp_http.py`, remove task entries from `tool_map` except `create_task`.
2) **Adjust ToolAccessor / task tool module**
   - If ToolAccessor exposes task methods, keep only `create_task`; remove/deprecate others or guard them from registration.
   - In `src/giljo_mcp/tools/task.py`, refactor `create_task` signature to accept a single findings payload (e.g., `summary`, `details`, `category`, `priority`, `product_id`, `project_id`) and map into Task fields. Preserve tenant isolation.
3) **Docs/UX**
   - Update handover MCPreport/README to reflect the reduced MCP task surface (1 tool).
   - Add a brief agent-facing note (thin prompt snippet) in the appropriate doc (if any) on how to “punt findings” using `create_task`.
4) **Tests (minimal)**
   - Adjust/remove tests for deleted task MCP tools.
   - Add/adjust a test for the new `create_task` payload path (unit-level).
   - Optional: smoke `create_task` via MCP HTTP if test harness available.

---

## Acceptance Criteria
- MCP HTTP `tools/list` shows only one task tool: `create_task`.
- `create_task` accepts a payload (summary/details), creates a task with tenant/product/project isolation, and returns task id + normalized fields.
- UI/REST task management (`/tasks` endpoints) remains unchanged.
- Tests updated to remove references to deleted task MCP tools; new/updated test covers the payload-based `create_task` path.
- Docs/MCPreport updated to note the reduced MCP task surface and the new “punt findings” usage.

---

## Notes
- Do not reintroduce legacy task-template MCP tools (already removed in 0255/0256).
- Keep the refactor minimal to avoid breaking existing thin prompts; prefer additive params over breaking changes. If a signature change is necessary, document it clearly.*** End Patch
