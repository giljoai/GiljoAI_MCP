# Terminal Session: 0765i - Post-Sprint Quality Audit (FINAL)

## Mission
Execute Handover 0765i (Part 9/9 — FINAL session of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules
2. `F:\GiljoAI_MCP\handovers\0765i_quality_audit.md` — Your full task specification
3. `F:\GiljoAI_MCP\handovers\Code_quality_prompt.md` — Standard audit methodology
4. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Verify 0765h completed, read scope

## CRITICAL: You Are the Quality Gate

- You are a FRESH agent evaluating code quality independently
- Do NOT trust claims from prior agents — verify everything yourself
- Your job is to FIND PROBLEMS, not confirm success
- Be thorough but fair — flag real issues, not style preferences
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Backend audit | `deep-researcher` | Audit src/giljo_mcp/ for dead code, pattern violations, oversized functions |
| API audit | `deep-researcher` | Audit api/ for tenant isolation, dict returns, fake data, dead code |
| Test audit | `deep-researcher` | Audit tests/ for dead fixtures, stale imports, oversized files |
| Frontend audit | `deep-researcher` | Audit frontend/src/ for dead vars, dead config, stale references |

### Communication via Chain Log
1. **On start:** Verify 0765h = `complete`, set 0765i to `in_progress`
2. **On complete:** This is the FINAL session. Update chain log:
   - Set 0765i `status` to `"complete"`
   - Set `final_status` to `"complete"`
   - Write `chain_summary` summarizing the entire 0765 series + audit verdict

### Commit Strategy
- Single commit with audit report: `audit(0765i): Post-sprint quality audit — score X.X/10`

## Prerequisite Check
- Verify 0765h status = `complete` in chain log
- Run `pytest tests/ -x -q` — all pass, zero skips
- Run `ruff check src/ api/` — zero issues
- Run `npm run build` in frontend/ — clean

## When Done — CHAIN COMPLETE
1. Write audit report to the handover file
2. Update chain log with final status + chain summary
3. Commit audit report
4. Report verdict to user: PASS (>= 9.5/10) or FAIL with fix list
5. Do NOT spawn another terminal — the chain is complete
