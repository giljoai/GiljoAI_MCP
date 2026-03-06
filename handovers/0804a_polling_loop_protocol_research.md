# Handover 0804a: Research — Polling Loop Protocol (RT-2)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P2
**Estimated Complexity:** 30 minutes
**Status:** Not Started
**Chain:** 0804a (Research) -> 0804b (Fix)

---

## MANDATORY: Read First
- `F:\GiljoAI_MCP\handovers\handover_instructions.md` — coding protocols

---

## Task Summary

RT-2: The orchestrator polling loop protocol is too prescriptive. An agent wasted ~21 tool calls monitoring independent background agents. The protocol should make monitoring situational, not mandatory every ~20 seconds.

Trace the full flow: find where polling instructions live, determine if they're overly rigid, propose targeted text change.

---

## Research Tasks

### Task 1: Find the Polling Instructions
1. Search `thin_prompt_generator.py` for polling/monitoring text — "polling", "monitor", "20s", "interval", "check", "loop"
2. Search `protocol_builder.py` for the same terms
3. Search `mission_planner.py` for monitoring instructions
4. Identify: which exact text tells orchestrators to poll and how often?

### Task 2: Understand the Current Protocol
1. Read the full monitoring section wherever you find it
2. Answer: is polling ALWAYS required? Or conditional?
3. Answer: what does the protocol say about polling interval?
4. Answer: does it differentiate between "agents are running" vs "all agents are complete"?

### Task 3: Analyze the Problem
1. How many MCP calls does a single poll cycle consume? (get_workflow_status + receive_messages = 2 calls?)
2. For 5 agents over 10 minutes: how many total polling calls?
3. Is the waste in frequency (too often) or in scope (polling when not needed)?

### Task 4: Propose Fix
1. Should polling be situational? ("Poll only when agents are actively working")
2. Should interval be adaptive? ("Start at 20s, back off to 60s after 5 minutes")
3. Should it be opt-out? ("Monitor by default, but skip if all agents are independent")
4. Is this a protocol text fix only, or does backend need changes?

---

## Chain Log Instructions

Update `F:\GiljoAI_MCP\prompts\0804_chain\chain_log.json` with findings.

## DO NOT
- Do NOT implement — research only
- Do NOT modify source code
- Do NOT create commits
