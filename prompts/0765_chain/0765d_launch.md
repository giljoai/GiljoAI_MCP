# Terminal Session: 0765d - Exception Narrowing

## Mission
Execute Handover 0765d (Part 4/7 of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules, code discipline
2. `F:\GiljoAI_MCP\handovers\0765d_exception_narrowing.md` — Your full task specification
3. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Check 0765c completed, read `notes_for_next`

## CRITICAL: Protocol Requirements

### Quality Standards
- Production-grade code ONLY
- Pre-commit hooks must pass. NEVER use `--no-verify`
- No AI signatures in code or commits
- Exception-based error handling (post-0480): services raise exceptions, tools raise exceptions

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Phase 1: Categorize | `deep-researcher` | Inventory all 121 except-Exception, classify A/B/C/D/E/F |
| Phase 2: Narrow safe | `tdd-implementor` | Narrow ~20 Category C instances to specific types |
| Phase 3: Annotate | `tdd-implementor` | Add inline comments to intentionally broad catches |

### Communication via Chain Log
1. **On start:** Read chain log, verify 0765c = `complete`, set 0765d to `in_progress`
2. **On complete:** Update with category breakdown and count, set `complete`

### Commit Strategy
- One commit per major file. Prefix: `cleanup(0765d):`
- Run per-file tests after each change, full suite before final commit

## Prerequisite Check
- Verify 0765c status = `complete` in chain log
- Verify all tests pass

## When Done
1. Update chain log (status=complete)
2. Report completion summary — include category breakdown
3. Spawn the next terminal:

```
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0765e - Test File Splitting\" --tabColor \"#E91E63\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0765e. READ FIRST: F:\GiljoAI_MCP\prompts\0765_chain\0765e_launch.md — Full mission, protocols, subagent plan, chain log. Use Task tool subagents. Spawn next terminal when done.\"' -Verb RunAs"
```
