# Handover 0807a: Research — set_agent_status Missing (CW-5)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P2
**Estimated Complexity:** 30 minutes
**Status:** Not Started
**Chain:** 0807a (Research) -> 0807b (Fix)

---

## MANDATORY: Read First
- `F:\GiljoAI_MCP\handovers\handover_instructions.md` — coding protocols

---

## Task Summary

CW-5: Only `report_error()` and `complete_job()` exist for agent status changes. There is no generic `set_agent_status()` tool. **Key question: is this a real gap (agents need status control they don't have), or is the controlled lifecycle intentional?**

The valid statuses are: waiting, working, blocked, complete, silent, decommissioned.

---

## Research Tasks

### Task 1: Map All Status Transitions
1. Read AgentExecution model — status field definition, CHECK constraint
2. Trace ALL places in the codebase where `execution.status =` is set
3. Build a complete transition map: from -> to -> triggered by what method
4. Note: 0803a research already mapped these — check `F:\GiljoAI_MCP\prompts\0803_chain\chain_log.json` for the findings

### Task 2: Identify the Gap (If Any)
1. Can an orchestrator unblock a blocked agent? (Is there a `report_progress()` that changes blocked->working?)
2. Can an agent resume from "silent" status?
3. Can an orchestrator set an agent back to "working" from "blocked"?
4. What status transitions are IMPOSSIBLE with the current API?

### Task 3: Analyze Design Intent
1. Is the controlled lifecycle (only specific methods change status) intentional for safety?
2. Would a generic `set_agent_status()` allow dangerous transitions? (e.g., complete->working?)
3. Does the 0491 handover (status simplification) explain why generic status setting was avoided?
4. Search handovers for any discussion about status control design

### Task 4: Propose Fix or Close
1. If by-design: document why the controlled lifecycle is correct
2. If real gap: which specific transition is missing? (e.g., "blocked->working" via orchestrator)
3. If partial gap: propose a targeted tool (e.g., `unblock_agent()`) rather than a generic setter

---

## Chain Log Instructions

Update `F:\GiljoAI_MCP\prompts\0807_chain\chain_log.json` with findings.

## DO NOT
- Do NOT implement — research only
- Do NOT modify source code
- Do NOT create commits
