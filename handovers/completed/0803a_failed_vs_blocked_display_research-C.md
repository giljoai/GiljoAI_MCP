# Handover 0803a: Research — Failed vs Blocked Agent Display (RT-6/#42)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P2
**Estimated Complexity:** 45 minutes
**Status:** Not Started
**Chain:** 0803a (Research) -> 0803b (Fix)

---

## Task Summary

RT-6 / Enhancement #42: Failed and blocked agents display identically on the dashboard — both show as "need input". Should visually distinguish terminal failure (agent crashed, can't recover) from recoverable blocked state (agent needs orchestrator input to continue).

Trace the FULL flow: agent status in database -> API response -> Vue dashboard rendering. Determine if "failed" is even a real status, or if only "blocked" exists.

---

## Research Tasks

### Task 1: Understand Agent Status Values
1. Read `AgentExecution` model (in `src/giljo_mcp/models/agent_identity.py`)
   - What status values are defined? Is there an enum or constraint?
   - Is "failed" a valid status? Or only "blocked"?
2. Read `report_error()` in `orchestration_service.py`
   - What status does it set? "blocked"? "failed"? "error"?
3. Search for all status transitions: `execution.status =` across the codebase
   - Build a complete map of all possible status values
4. Check: are "failed" and "blocked" actually different states, or the same state with different labels?

### Task 2: Trace the API Response
1. Read `get_workflow_status()` in `orchestration_service.py`
   - How does it report agent status?
   - Does it differentiate failed vs blocked?
2. Find the API endpoint that serves the dashboard (likely GET `/api/projects/{id}/workflow` or agents endpoint)
3. Check: does the API response include the raw status string, or does it map/transform it?

### Task 3: Trace the Frontend Display
1. Search Vue frontend for dashboard status display
   - Search for "need input", "blocked", "failed", "status" in frontend components
   - Look in `frontend/src/components/` or `frontend/src/views/`
2. Read the component that shows agent status badges/labels
   - How does it map status values to display text?
   - Is there a status-to-label mapping object?
   - Is "need input" a catch-all for anything that isn't "complete" or "working"?
3. Check: are there CSS classes or colors per status? Or one generic style for non-working agents?

### Task 4: Determine the Fix
1. If "failed" isn't a real status: is it needed? Should `report_error()` set status to "failed" instead of "blocked"?
2. If both statuses exist but frontend treats them the same: just a frontend label/color fix
3. If only "blocked" exists: should we introduce "failed" as a new status? What's the recovery path for each?
4. Consider: what does the ORCHESTRATOR need to know? "Blocked" = send a message to unblock. "Failed" = respawn or investigate.

---

## Chain Log Instructions

Update `F:\GiljoAI_MCP\prompts\0803_chain\chain_log.json`:
- Set `0803a.status` to `"in_progress"` at start, `"complete"` when done
- Write findings with:
  - `status_values`: complete list of all agent status values in the system
  - `failed_is_real_status`: true/false
  - `blocked_is_real_status`: true/false
  - `report_error_sets`: what status report_error() actually sets
  - `frontend_mapping`: how the dashboard maps status to labels
  - `root_cause`: why they display identically
  - `proposed_fix`: what to change (backend/frontend/both)

## Success Criteria
- [ ] Complete map of all agent status values
- [ ] Traced report_error() status transition
- [ ] Traced dashboard status display logic
- [ ] Determined if "failed" is a real status or not
- [ ] Identified root cause of identical display
- [ ] Proposed fix with file locations
- [ ] Findings written to chain_log.json

## DO NOT
- Do NOT implement any fixes — research only
- Do NOT modify any source code files
- Do NOT create commits

## Reference Files
- Chain Log: `F:\GiljoAI_MCP\prompts\0803_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
