# Terminal Session: 0387i - Deprecate JSONB Column (FINAL)

## Mission
Execute Handover 0387i (Part 5/5 JSONB Normalization) - **FINAL HANDOVER**.

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0387i_deprecate_jsonb_column.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="documentation-manager", prompt="Update CLAUDE.md and docs/SERVICES.md per handover 0387i Phase 5...")
Task(subagent_type="backend-tester", prompt="Run full regression test suite per handover 0387i Phase 3...")
```

Recommended subagents for this handover:
- `documentation-manager` - For updating documentation
- `backend-tester` - For final regression testing

## Prerequisite Check
Verify 0387h complete: all tests passing.

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Mark column deprecated, update docs, full regression, merge

## Success Criteria
- Column marked deprecated in code/DB
- All tests pass (100%)
- Coverage >80%
- Manual E2E complete
- Documentation updated
- Branch merged to master

## On Completion - CHAIN COMPLETE
This is the final handover. When done:
1. Commit all changes to master
2. Update parent handover 0387 status to COMPLETE
3. Report summary of the entire 0387 Phase 4 series

**NO NEXT TERMINAL** - You are the final link in the chain.
