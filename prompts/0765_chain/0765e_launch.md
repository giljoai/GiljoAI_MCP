# Terminal Session: 0765e - Test File Splitting

## Mission
Execute Handover 0765e (Part 5/7 of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards
2. `F:\GiljoAI_MCP\handovers\0765e_test_file_splitting.md` — Your full task specification
3. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Check 0765d completed

## CRITICAL: Protocol Requirements

### Quality Standards
- Maintain test names (preserves git blame and CI history)
- Target 200-400 lines per split file
- Shared fixtures go to conftest.py, private fixtures stay in file
- Test count MUST match pre-split baseline after every split
- Pre-commit hooks must pass

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents — one per file split.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Each file split | `tdd-implementor` | Read file, identify splits, create new files, verify tests pass |

Process largest files first: test_orchestration_service.py (1,161 lines), test_service_responses.py (1,143 lines), etc.

### Communication via Chain Log
1. **On start:** Verify 0765d = `complete`, set 0765e to `in_progress`
2. **On complete:** Include split count and total line reduction, set `complete`

### Commit Strategy
- One commit per 2-3 file splits. Prefix: `cleanup(0765e):`
- `pytest tests/ -x -q` must pass after every commit

## Prerequisite Check
- Verify 0765d status = `complete` in chain log
- Record baseline test count before starting any splits

## When Done
1. Update chain log (status=complete)
2. Report completion summary — split count, line reduction, test count verification
3. Spawn the next terminal:

```
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0765f - Security Hardening\" --tabColor \"#F44336\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0765f. READ FIRST: F:\GiljoAI_MCP\prompts\0765_chain\0765f_launch.md — Full mission, protocols, subagent plan, chain log. Use Task tool subagents. Spawn next terminal when done.\"' -Verb RunAs"
```
