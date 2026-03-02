# Terminal Session: 0765c - Design Token Migration

## Mission
Execute Handover 0765c (Part 3/7 of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules, code discipline
2. `F:\GiljoAI_MCP\handovers\0765c_design_token_migration.md` — Your full task specification
3. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Check 0765b completed, read its `notes_for_next`
4. `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt` — Quick reference

## CRITICAL: Protocol Requirements

### Quality Standards
- Production-grade code ONLY — no shortcuts
- DELETE old code, don't comment out
- Pre-commit hooks must pass. NEVER use `--no-verify`
- No AI signatures in code or commits
- Frontend: use Vuetify theme variables, no `!important` unless compensating for a verified framework bug

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Phase 1: Audit colors | `ux-designer` | Map all 108 hex colors, classify by semantic meaning |
| Phase 2: Extend tokens | `ux-designer` | Add missing custom tokens to theme.js + design-tokens.scss |
| Phase 3: Migrate files | `frontend-tester` | Replace hardcoded colors in Vue files (batch by component) |
| Phase 4: Verify | `frontend-tester` | Visual regression check, grep verification, build test |

### Communication via Chain Log
1. **On start:** Read chain log, verify 0765b = `complete`, set 0765c to `in_progress`
2. **On complete:** Update with results, set `complete`

### Commit Strategy
- Commit token infrastructure first, then migrations in batches. Prefix: `cleanup(0765c):`
- `npm run build` must pass after every commit

## Prerequisite Check
- Verify 0765b status = `complete` in chain log
- Verify frontend builds clean

## When Done
1. Update chain log (status=complete)
2. Report completion summary to the user
3. Spawn the next terminal:

```
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0765d - Exception Narrowing\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0765d. READ FIRST: F:\GiljoAI_MCP\prompts\0765_chain\0765d_launch.md — Full mission, protocols, subagent plan, chain log. Use Task tool subagents. Spawn next terminal when done.\"' -Verb RunAs"
```
