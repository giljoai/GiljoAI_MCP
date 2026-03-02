# Terminal Session: 0765b - Quick Tier 3 Fixes

## Mission
Execute Handover 0765b (Part 2/7 of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules, code discipline
2. `F:\GiljoAI_MCP\handovers\0765b_quick_tier3_fixes.md` — Your full task specification
3. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Check 0765a completed, read its `notes_for_next`
4. `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt` — Quick reference
5. `F:\GiljoAI_MCP\handovers\Reference_docs\AGENT_FLOW_SUMMARY.md` — Agent flow patterns

## CRITICAL: Protocol Requirements

### Quality Standards
- Production-grade code ONLY — no shortcuts, no bandaids
- TDD: write tests FIRST when adding new behavior
- DELETE old code, don't comment out
- Pre-commit hooks must pass. NEVER use `--no-verify`
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents. Do NOT do all work directly.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| NPM health check (3H) | `tdd-implementor` | Fix startup.py + control_panel.py detection |
| CSS + computeds (3C) | `frontend-tester` | Remove orphan selectors, convert static computeds |
| Dead emits (3D) | `frontend-tester` | Remove 8 unhandled ProjectTabs emits |
| Sort unification (3E) | `tdd-implementor` | Create shared constant, update both stores |
| CORS restriction (3F) | `backend-tester` | Restrict methods/headers in app.py + devpanel |
| H-24 prefetch (gap) | `frontend-tester` | Remove speculative agentStore.fetchAgents() |

### Communication via Chain Log
1. **On start:** Read chain log, verify 0765a = `complete`, set 0765b to `in_progress`
2. **On complete:** Update with `tasks_completed`, `deviations`, `notes_for_next`, `summary`, set `complete`

### Commit Strategy
- One commit per task or batch. Prefix: `cleanup(0765b):`
- Run `pytest tests/ -x -q` and `npm run build` before final commit

## Prerequisite Check
- Verify 0765a status = `complete` in chain log
- Verify tests pass and frontend builds clean

## When Done
1. Update chain log (status=complete)
2. Report completion summary to the user
3. Spawn the next terminal:

```
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0765c - Design Token Migration\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0765c. READ FIRST: F:\GiljoAI_MCP\prompts\0765_chain\0765c_launch.md — Full mission, protocols, subagent plan, chain log. Use Task tool subagents. Spawn next terminal when done.\"' -Verb RunAs"
```
