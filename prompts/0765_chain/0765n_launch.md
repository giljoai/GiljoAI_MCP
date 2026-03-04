# Terminal Session: 0765n - Post-0765l Re-Audit (Third Audit)

## Mission
Execute Handover 0765n — independent re-audit after 0765l full remediation.
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules
2. `F:\GiljoAI_MCP\handovers\0765n_reaudit.md` — Your full task specification
3. `F:\GiljoAI_MCP\handovers\Code_quality_prompt.md` — Standard audit methodology
4. `F:\GiljoAI_MCP\handovers\0765k_reaudit.md` — Previous audit (8.5/10), see rubric + findings
5. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Verify 0765l completed

## CRITICAL: You Are the Quality Gate

- FRESH agent, zero prior context
- Do NOT trust claims — verify everything yourself
- Your job is to FIND PROBLEMS, not confirm success
- Check for regressions from 0765l fixes (broken imports, missing references)
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Fix verification (11 items) | `deep-researcher` | Verify each 0765l fix actually landed |
| Backend audit | `deep-researcher` | Audit src/giljo_mcp/ for dead code, patterns, organization |
| API audit | `deep-researcher` | Audit api/ for tenant isolation, dead code, security |
| Test audit | `deep-researcher` | Audit tests/ for dead fixtures, broken refs from deletions |
| Frontend audit | `deep-researcher` | Audit frontend/src/ for dead vars, color consistency, dead exports |

### Communication via Chain Log
1. **On start:** Verify 0765l = `complete`, set 0765n to `in_progress`
2. **On complete:** Set 0765n to `complete`, write summary with score and PASS/FAIL verdict

### Commit Strategy
- Single commit: `audit(0765n): Post-remediation re-audit — score X.X/10`

## When Done
1. Write report to `handovers/0765n_reaudit_report.md`
2. Update chain log (status=complete, summary with verdict)
3. Commit the report + chain log update
4. Report to user: PASS or FAIL with score
5. Do NOT spawn another terminal
