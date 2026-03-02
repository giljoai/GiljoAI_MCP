# Terminal Session: 0765h - Skipped Test Resolution (FINAL)

## Mission
Execute Handover 0765h (Part 8/8 — FINAL session of the 0765 Perfect Score Sprint).
Branch: `0760-perfect-score`

## READ THESE FILES FIRST (in order)
1. `F:\GiljoAI_MCP\handovers\handover_instructions.md` — Quality standards, golden rules
2. `F:\GiljoAI_MCP\handovers\0765h_skipped_test_resolution.md` — Your full task specification
3. `F:\GiljoAI_MCP\prompts\0765_chain\chain_log.json` — Check 0765g completed, read ALL predecessor notes

## CRITICAL: Protocol Requirements

### Quality Standards
- This session is TEST-ONLY — no production code changes unless a real bug is discovered
- Every deleted test must have a documented reason (dead endpoint, obsolete pattern, duplicate)
- Every rewritten test must actually PASS — no skip markers allowed
- Pre-commit hooks must pass
- No AI signatures in code or commits

### Use Subagents to Preserve Context Budget
**Use the Task tool to spawn subagents.**

| Task | Subagent Type | What to Delegate |
|------|---------------|-----------------|
| Phase 1: Inventory | `deep-researcher` | Collect all skipped tests, categorize skip reasons, build triage table |
| Phase 2: Delete obsolete | `backend-tester` | Delete all tests verdicted DELETE, verify no collection errors |
| Phase 3: Fix quick wins | `backend-tester` | Fix imports, fixtures, small assertion mismatches |
| Phase 4a: Service rewrites | `tdd-implementor` | Rewrite dict-return service tests to exception/Pydantic patterns |
| Phase 4b: API rewrites | `tdd-implementor` | Rewrite dict-return API endpoint tests |
| Phase 5: Final verification | `backend-tester` | Full suite run, zero skips confirmation |

### Communication via Chain Log
1. **On start:** Verify 0765g = `complete`, set 0765h to `in_progress`
2. **On complete:** This is the FINAL session. Update chain log:
   - Set 0765h `status` to `"complete"`
   - Set `final_status` to `"complete"`
   - Write `chain_summary` summarizing the entire 0765 series outcome including test resolution

### Commit Strategy
- Batch commits by phase: deletions, fixes, rewrites (by domain area)
- Prefix: `tests(0765h):`
- Final commit message: `tests(0765h): Resolve all skipped tests — zero skips remaining`

## Prerequisite Check
- Verify 0765g status = `complete` in chain log
- Run `pytest tests/ -x -q` to establish baseline counts
- Verify baseline: ~1,410 passed, ~342 skipped, 0 failed

## When Done — CHAIN COMPLETE
1. Run full test suite — document final counts (passed, skipped=0, failed=0)
2. Run `npm run build` in frontend/ — verify clean
3. Update chain log:
   - Set 0765h `status` to `"complete"`
   - Set `final_status` to `"complete"`
   - Write `chain_summary` summarizing the entire 0765 series
4. Write completion summary to the handover file (max 400 words)
5. Commit all changes
6. Report to user: "Product is ready for manual testing"
7. Do NOT spawn another terminal — the chain is complete
