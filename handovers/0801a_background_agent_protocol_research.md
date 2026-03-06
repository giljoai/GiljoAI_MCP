# Handover 0801a: Research — run_in_background Protocol Contradiction (#44)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P1
**Estimated Complexity:** 30 minutes
**Status:** Not Started
**Chain:** 0801a (Research) -> 0801b (Fix)

---

## Task Summary

Enhancement #44: The agent protocol tells agents "NEVER use run_in_background" but background agent execution actually works excellently in practice. Your job is to find where this prohibition lives, trace whether there's a real technical reason for it, and determine if it's just a stale instruction that needs updating.

**Key question:** Is `run_in_background` referring to Claude Code's `Task` tool parameter, or to some GiljoAI MCP feature? The context matters.

---

## Research Tasks

### Task 1: Find the Prohibition
1. Search the entire codebase for `run_in_background` — where is it referenced?
2. Search for `NEVER.*background` and `background.*NEVER` in prompt/protocol text
3. Read `protocol_builder.py` — search for background execution warnings
4. Read `thin_prompt_generator.py` — search for background execution warnings
5. Identify: which specific prompt text says "NEVER use run_in_background"?

### Task 2: Understand What It Refers To
1. Is this about Claude Code's `Task(run_in_background=true)` tool parameter?
2. Or is this about a GiljoAI MCP feature (like running agent jobs in background)?
3. Or is this about shell command `run_in_background` (the `&` operator)?
4. Read the surrounding context of the prohibition to understand intent

### Task 3: Trace the Technical Flow
1. If it's about Claude Code Task tool: what happens when an orchestrator spawns a subagent with `run_in_background=true`? Does the MCP connection work? Do tool calls succeed?
2. If it's about MCP: trace any background execution mechanism in the codebase
3. Check: are there any known issues with background execution? Search git history and handovers
4. Check: does the silence_detector or health_check have problems with background agents?

### Task 4: Determine the Fix
1. If it's a stale instruction: propose removing/updating the text
2. If there's a real limitation: document what it is
3. If it partially works: document what works and what doesn't
4. Check: should the protocol ENCOURAGE background execution for certain patterns? (e.g., parallel subagent spawning)

---

## Chain Log Instructions

Update `F:\GiljoAI_MCP\prompts\0801_chain\chain_log.json`:
- Set `0801a.status` to `"in_progress"` at start, `"complete"` when done
- Write findings with:
  - `prohibition_location`: exact file + line where the "NEVER" instruction is
  - `what_it_refers_to`: Claude Code Task tool / MCP feature / shell command
  - `is_stale`: true/false
  - `technical_limitation`: description if any real limitation exists
  - `proposed_fix`: what to change

## Success Criteria
- [ ] Found the exact prohibition text and location
- [ ] Determined what "run_in_background" refers to in this context
- [ ] Checked for real technical limitations
- [ ] Proposed fix or documented as valid restriction
- [ ] Findings written to chain_log.json

## DO NOT
- Do NOT implement any fixes — research only
- Do NOT modify any source code files
- Do NOT create commits

## Reference Files
- Chain Log: `F:\GiljoAI_MCP\prompts\0801_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
