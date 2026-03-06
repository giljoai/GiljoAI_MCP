# Handover 0805a: Research — Progress Percent 0% Issue (RT-3/#43)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P2
**Estimated Complexity:** 30 minutes
**Status:** Not Started
**Chain:** 0805a (Research) -> 0805b (Fix)

---

## MANDATORY: Read First
- `F:\GiljoAI_MCP\handovers\handover_instructions.md` — coding protocols

---

## Task Summary

RT-3 / Enhancement #43: `progress_percent` in MCP tool responses shows 0% until agents complete. The Feb report notes this is NOT a UI issue — the dashboard uses todo steps (3/5, 4/5), not percentages. The % is only in MCP tool responses. **Key question: does anyone actually consume this value, or is it dead data?**

---

## Research Tasks

### Task 1: Find progress_percent
1. Search for `progress_percent` or `progress` in `orchestration_service.py`
2. Read `report_progress()` — does it set a percentage?
3. Read `get_workflow_status()` — does it calculate or return a percentage?
4. Check `AgentExecution` model — is there a `progress` field?

### Task 2: Trace Who Consumes It
1. Search frontend for `progress_percent` or `progress` (in agent status context)
2. Check: does the dashboard show a percentage anywhere?
3. Check: does the orchestrator protocol reference progress_percent?
4. Check: does any MCP tool response include progress_percent?

### Task 3: Determine Impact
1. If nobody reads progress_percent: this is a non-issue, close it
2. If the dashboard reads it: it's a real bug, needs fixing
3. If only MCP responses include it: is it useful or just noise?

### Task 4: Propose Fix or Close
1. If non-issue: document why and recommend closing
2. If real bug: where should the calculation happen? (completed_todos / total_todos * 100?)
3. If partially useful: should it be calculated differently?

---

## Chain Log Instructions

Update `F:\GiljoAI_MCP\prompts\0805_chain\chain_log.json` with findings.

## DO NOT
- Do NOT implement — research only
- Do NOT modify source code
- Do NOT create commits
