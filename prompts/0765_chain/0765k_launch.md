# Terminal Session: 0765k - Post-Remediation Re-Audit

## Mission
Execute Handover 0765k — independent re-audit after 0765j remediation.
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules
2. `F:\GiljoAI_MCP\handovers\0765k_reaudit.md` — Your full task specification
3. `F:\GiljoAI_MCP\handovers\Code_quality_prompt.md` — Standard audit methodology
4. `F:\GiljoAI_MCP\handovers\0765i_quality_audit.md` — Previous audit (8.2/10), see rubric + findings
5. `F:\GiljoAI_MCP\handovers\0765j_audit_remediation.md` — Claims all 10 fixed
6. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Verify 0765j completed

## CRITICAL: You Are the Quality Gate

- FRESH agent, zero prior context
- Do NOT trust claims — verify everything yourself
- Your job is to FIND PROBLEMS, not confirm success
- Check for regressions from the fixes (broken imports, missing references)
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Fix verification (10 items) | `deep-researcher` | Verify each of the 10 fixes actually landed |
| Backend audit | `deep-researcher` | Audit src/giljo_mcp/ for dead code, patterns, organization |
| API audit | `deep-researcher` | Audit api/ for tenant isolation, dead code, fake data |
| Test audit | `deep-researcher` | Audit tests/ for dead fixtures, broken refs from deletions |
| Frontend audit | `deep-researcher` | Audit frontend/src/ for dead vars, color consistency, dead exports |

### Communication via Chain Log
1. **On start:** Verify 0765j = `complete`, set 0765k to `in_progress`
2. **On complete:** Set 0765k to `complete`, write summary with score

### Commit Strategy
- Single commit: `audit(0765k): Post-remediation re-audit — score X.X/10`

## When Done
1. Write report to handover file
2. Update chain log (status=complete, summary with verdict)
3. Commit
4. Report to user: PASS or FAIL with score
5. Do NOT spawn another terminal
