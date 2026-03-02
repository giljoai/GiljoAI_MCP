# Terminal Session: 0765g - Tenant Key + Encapsulation

## Mission
Execute Handover 0765g (Part 7/8 of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules
2. `F:\GiljoAI_MCP\handovers\0765g_tenant_key_encapsulation.md` — Your full task specification
3. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Check 0765f completed, read ALL predecessor notes

## CRITICAL: Protocol Requirements

### Quality Standards
- Production-grade code ONLY — this touches auth flow, must be bulletproof
- TDD: write tests for tenant key resolution before changing auth
- Installation flow: changes to install.py MUST handle both fresh install and upgrade
- Pre-commit hooks must pass
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Task 1: Tenant key backend | `network-security-engineer` | Remove hardcoded key from 5 backend locations, implement config-based resolution |
| Task 1: Tenant key frontend | `frontend-tester` | Remove hardcoded key from 4 frontend locations, wire auth store |
| Task 1: Installer | `installation-flow-agent` | Update install.py to generate unique key, handle upgrade path |
| Task 2: Prompts encapsulation | `tdd-implementor` | Add generate_implementation_prompt() public method |
| Task 3: update_project refactor | `tdd-implementor` | Extract 2 helpers from update_project |

### Product Decisions
If the user is unavailable, use Option A defaults from the handover:
- Q1: Return 401 when no tenant key provided
- Q2: install.py generates unique key, stores in config.yaml
- Q3: Frontend gets tenant key from login response / auth state

### Communication via Chain Log
1. **On start:** Verify 0765f = `complete`, set 0765g to `in_progress`
2. **On complete:** Set 0765g `status` to `"complete"` in chain log

### Commit Strategy
- Separate commits for tenant key, prompts fix, and update_project refactor
- Prefix: `cleanup(0765g):`
- Final verification: run code quality audit (`handovers/Code_quality_prompt.md`)

## Prerequisite Check
- Verify 0765f status = `complete` in chain log
- Verify CSRF middleware is enabled (from 0765f)
- Verify all tests pass

## When Done
1. Update chain log (status=complete)
2. Report completion summary
3. Spawn the next terminal:

```
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0765h - Skipped Test Resolution\" --tabColor \"#607D8B\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0765h (FINAL). READ FIRST: F:\GiljoAI_MCP\prompts\0765_chain\0765h_launch.md — Full mission, protocols, subagent plan, chain log. Use Task tool subagents. This is the LAST session — mark chain complete when done.\"' -Verb RunAs"
```
