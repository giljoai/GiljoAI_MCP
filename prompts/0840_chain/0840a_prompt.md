# Terminal Session: 0840a - Dead Column Cleanup

## Mission
Execute Handover 0840a (Part 1/6 of JSONB Normalization Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0840a_dead_column_cleanup.md`

## Chain Log
**READ AND UPDATE**: `F:\GiljoAI_MCP\prompts\0840_chain\chain_log.json`
- Check `orchestrator_instructions` field — if non-null, follow those instructions
- This is the FIRST session — create the chain log workflow as described in the handover

## Reference Documents
- `F:\GiljoAI_MCP\handovers\HANDOVER_INSTRUCTIONS.md` — Coding principles and protocols
- `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt` — Quick reference
- `F:\GiljoAI_MCP\handovers\Reference_docs\AGENT_FLOW_SUMMARY.md` — Agent workflow

## Branch
You are on branch `feature/0840-jsonb-normalization`. Verify with `git branch --show-current`.

## CRITICAL: Use Subagents
**YOU MUST use the Agent tool to spawn subagents for this work.**

Recommended subagents:
- `database-expert` — For Alembic migration creation
- `tdd-implementor` — For test verification after column removal

## Execute
1. Read the handover document completely
2. Read the chain log and mark your session as `in_progress`
3. Use subagents to complete all phases
4. Update chain log with results
5. Commit work
6. Spawn next terminal (command is in the handover document)

## Success Criteria
- [ ] 7 dead meta_data columns removed from models
- [ ] Alembic migration created with idempotency guards
- [ ] 6 ghost config keys removed
- [ ] All code references cleaned up
- [ ] All tests pass
- [ ] `ruff check src/ api/` clean
- [ ] Chain log updated
- [ ] Next terminal spawned

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command** (from the handover document Step 6).
