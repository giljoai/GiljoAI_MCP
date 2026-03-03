# Terminal Session: 0765j - Audit Remediation

## Mission
Execute Handover 0765j — fix all 10 findings from the 0765i quality audit.
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules
2. `F:\GiljoAI_MCP\handovers\0765j_audit_remediation.md` — Your full task specification (10 items)
3. `F:\GiljoAI_MCP\handovers\0765i_quality_audit.md` — Original audit report with exact line numbers
4. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Verify 0765i completed

## CRITICAL: Protocol Requirements

### Quality Standards
- Items 1-3 are SECURITY fixes — tenant isolation. Get these right.
- Item 4 is a real bug — SQLAlchemy `is None` vs `.is_(None)`. Verify the fix works.
- Items 5-6: VERIFY before deleting. Use grep/find_referencing_symbols. Pytest fixtures can be injected by name without imports — check parameter names in test functions.
- Pre-commit hooks must pass
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Bucket 1: Security fixes (items 1-4) | `network-security-engineer` | Fix 3 tenant gaps + NULL filter |
| Bucket 2a: Dead test fixtures (item 5) | `backend-tester` | Verify and delete 55 dead fixtures |
| Bucket 2b: Dead source code (items 6, 8, 10) | `deep-researcher` | Verify zero refs, then delete dead files/functions/metrics |
| Bucket 2c: Frontend cleanup (items 7, 9) | `frontend-tester` | Migrate colors, remove dead exports |

### Communication via Chain Log
1. **On start:** Verify 0765i = `complete`, set 0765j to `in_progress`
2. **On complete:** Set 0765j to `complete`, report summary

### Commit Strategy
- Commit 1: `security(0765j): Fix 3 tenant isolation gaps + broken NULL filter`
- Commit 2: `cleanup(0765j): Remove dead code, fixtures, exports, and stale cache`

## Prerequisite Check
- Verify 0765i status = `complete` in chain log
- Run `pytest tests/ -x -q` — baseline: 1453 passed, 0 skipped
- Verify branch is `0760-perfect-score`

## When Done
1. Update chain log (status=complete, summary)
2. Run full test suite + frontend build — report counts
3. Report to user: items fixed, ready for re-audit
4. Do NOT spawn another terminal — orchestrator handles next steps
