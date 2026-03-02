# Terminal Session: 0765f - Security Hardening

## Mission
Execute Handover 0765f (Part 6/7 of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules
2. `F:\GiljoAI_MCP\handovers\0765f_security_hardening.md` — Your full task specification
3. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Check 0765e completed

## CRITICAL: Protocol Requirements

### Quality Standards
- Production-grade code ONLY — security changes require extra care
- TDD: write CSRF tests FIRST, then enable middleware
- Every API router MUST inject `Depends(get_current_active_user)` for auth
- Tenant isolation: every new DB query filters by `tenant_key`
- Pre-commit hooks must pass

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Task 1: CSRF enable | `network-security-engineer` | Fix httponly bug, enable middleware, wire Axios interceptor, fix 8 fetch() calls, configure exemptions |
| Task 1: CSRF tests | `backend-tester` | Write CSRF integration tests |
| Task 2: Tenant isolation | `database-expert` | Fix 2 remaining pattern violations |
| Task 3: TenantManager | `tdd-implementor` | Add register_test_tenant(), update test files |

### Communication via Chain Log
1. **On start:** Verify 0765e = `complete`, set 0765f to `in_progress`
2. **On complete:** Include CSRF test count, set `complete`

### Commit Strategy
- Separate commits for CSRF, tenant isolation, and test coupling. Prefix: `security(0765f):`
- Run full test suite including new CSRF tests before final commit

## Prerequisite Check
- Verify 0765e status = `complete` in chain log
- Verify WebSocket bridge endpoint already deleted by 0765a (check chain log)
- Verify all 61 tenant isolation regression tests pass

## When Done
1. Update chain log (status=complete)
2. Report completion summary
3. Spawn the final terminal:

```
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0765g - Tenant Key + Encapsulation\" --tabColor \"#795548\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0765g (FINAL). READ FIRST: F:\GiljoAI_MCP\prompts\0765_chain\0765g_launch.md — Full mission, protocols, subagent plan, chain log. Use Task tool subagents. This is the LAST session — mark chain complete when done.\"' -Verb RunAs"
```
