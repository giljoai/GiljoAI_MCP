# Terminal Session: 0765l - Full Remediation

## Mission
Execute Handover 0765l — fix all remaining findings from both independent audits.
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules
2. `F:\GiljoAI_MCP\handovers\0765l_full_remediation.md` — Your full task specification (6 buckets)
3. `F:\GiljoAI_MCP\handovers\0765k_reaudit.md` — Claude audit findings (scroll to bottom)
4. `F:\GiljoAI_MCP\handovers\0765k_external_audit.md` — External audit findings
5. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Verify 0765k completed

## CRITICAL: Protocol Requirements

### Quality Standards
- SECURITY fixes first — tenant isolation and secrets
- Function splits are BEHAVIORAL NO-OPS — same logic, smaller pieces. Run tests after EACH split.
- Dead code: VERIFY zero references before deleting. Pytest fixtures inject by parameter name.
- Pre-commit hooks must pass
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Bucket 1: Security (S1-S5) | `network-security-engineer` | Fix 5 security findings |
| Bucket 2+3: Bugs + Tenant | `backend-tester` | Fix 4 bugs/lint + MCP session tenant gap |
| Bucket 4: Dead code backend | `deep-researcher` | Verify + delete dead backend methods, test fixtures |
| Bucket 4: Dead code frontend | `frontend-tester` | Verify + delete dead CSS, SCSS, exports |
| Bucket 5: Function splits | `tdd-implementor` | Split create_app, send_message, handle_tools_list |
| Bucket 6: ESLint lock | `frontend-tester` | Add eslint max-warnings to pre-commit |

### Communication via Chain Log
1. **On start:** Verify 0765k = `complete`, set 0765l to `in_progress`
2. **On complete:** Set 0765l to `complete`, write summary

### Commit Strategy
4 commits:
1. `security(0765l): Fix 5 security findings from dual audit`
2. `fix(0765l): Fix bugs, lint, and tenant isolation gap`
3. `cleanup(0765l): Remove dead code across backend, tests, and frontend`
4. `refactor(0765l): Split 3 oversized functions + lock eslint budget`

## When Done
1. Update chain log (status=complete, summary)
2. Run full test suite + frontend build — report counts
3. Report to user: items fixed, ready for re-audit
4. Do NOT spawn another terminal
