# Handover 0806a: Research — Todo Chicken-and-Egg on Closeout (RT-4)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P2
**Estimated Complexity:** 30 minutes
**Status:** Not Started
**Chain:** 0806a (Research) -> 0806b (Fix)

---

## MANDATORY: Read First
- `F:\GiljoAI_MCP\handovers\handover_instructions.md` — coding protocols

---

## Task Summary

RT-4: The final todo item "Close project with 360 memory" can't be marked complete before actually doing it, but COMPLETION_BLOCKED validation blocks `complete_job()` if any todo is incomplete. This creates a chicken-and-egg: you can't complete until todos are done, but the closeout todo can't be done until after completion.

Feb report says "documented workaround exists." **Key question: is this actually causing problems, or is the workaround sufficient?**

---

## Research Tasks

### Task 1: Understand the Conflict
1. Read `complete_job()` COMPLETION_BLOCKED logic (orchestration_service.py) — does it reject if ANY todo is incomplete?
2. Read the orchestrator protocol — does it tell orchestrators to create a "closeout" todo?
3. Check: is the closeout todo created by the system automatically, or by the orchestrator manually?

### Task 2: Find the Workaround
1. Search for any documentation about the chicken-and-egg workaround
2. Check: is the workaround "mark the closeout todo as completed BEFORE calling close_project"?
3. Check: is the workaround "call report_progress to mark it complete, then close_project, then complete_job"?
4. Check: does the orchestrator protocol already describe this sequence?

### Task 3: Analyze the Flow
1. What's the intended order? report_progress(mark closeout todo done) -> write_360_memory -> close_project -> complete_job?
2. Is this actually a problem or just a 2-step sequence that orchestrators handle naturally?
3. Does any agent actually GET blocked by this in practice?

### Task 4: Propose Fix or Close
1. If the workaround is already documented and works: close as minor friction with known workaround
2. If it's causing real problems: propose a fix (e.g., COMPLETION_BLOCKED exempts "closeout" type todos)
3. If the protocol needs updating: propose text change

---

## Chain Log Instructions

Update `F:\GiljoAI_MCP\prompts\0806_chain\chain_log.json` with findings.

## DO NOT
- Do NOT implement — research only
- Do NOT modify source code
- Do NOT create commits
