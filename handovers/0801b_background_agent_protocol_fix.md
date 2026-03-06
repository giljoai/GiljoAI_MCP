# Handover 0801b: Implement — run_in_background Protocol Fix (#44)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Implementation agent
**Priority:** P1
**Estimated Complexity:** 15 minutes
**Status:** Not Started
**Chain:** 0801a (Research COMPLETE) -> 0801b (Implementation)

---

## MANDATORY: Read Before Coding

1. Read coding protocols: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
2. Read 0801a findings: `F:\GiljoAI_MCP\prompts\0801_chain\chain_log.json`

---

## Task Summary

Single-line text fix in `thin_prompt_generator.py`. The `run_in_background` protocol text is overly restrictive — says "only when the user's project description explicitly requests background execution" but there are ZERO technical limitations. Background execution works perfectly.

---

## The Fix

### File: `src/giljo_mcp/thin_prompt_generator.py`
### Location: Line ~1413 (inside the CLI orchestrator spawning section)

**Find this text:**
```
**DEFAULT**: Run agents in foreground for observability. Use `run_in_background=true` only when the user's project description explicitly requests background execution or parallel monitoring.
```

**Replace with:**
```
**Spawning Mode**: Use foreground (default) when you need to observe agent output in real-time. Use `run_in_background=true` for independent parallel agents — poll status via `get_workflow_status()`. Background execution is fully supported and reliable.
```

That's it. One line of protocol text changed.

---

## Implementation Steps

1. Read `F:\GiljoAI_MCP\handovers\handover_instructions.md` — coding protocols
2. Read `src/giljo_mcp/thin_prompt_generator.py` — find the line (~1413)
3. Apply the text change
4. Run tests: `python -m pytest tests/ -x -q --timeout=30 --no-cov`
5. Update chain_log.json: `F:\GiljoAI_MCP\prompts\0801_chain\chain_log.json`
6. Commit: `fix(0801b): Update run_in_background protocol from restrictive to neutral guidance (#44)`

## DO NOT
- Do NOT change any backend logic
- Do NOT add new features
- Do NOT modify other files
- Do NOT create new files

## Reference Files
- Chain Log: `F:\GiljoAI_MCP\prompts\0801_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
