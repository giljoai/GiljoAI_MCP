# Terminal Session: 0840b - Message Table Normalization

## Mission
Execute Handover 0840b (Part 2/6 of JSONB Normalization Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0840b_message_normalization.md`

## Chain Log
**READ AND UPDATE**: `F:\GiljoAI_MCP\prompts\0840_chain\chain_log.json`
- Check `orchestrator_instructions` field — if non-null, follow those instructions
- Verify 0840a is `complete` before proceeding
- Read 0840a `notes_for_next`
- If 0840a is not complete or is blocked, STOP and report

## Reference Documents
- `F:\GiljoAI_MCP\handovers\HANDOVER_INSTRUCTIONS.md`
- `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt`

## Branch
You are on branch `feature/0840-jsonb-normalization`. Pull latest: `git pull origin feature/0840-jsonb-normalization` (if remote exists) or just verify branch.

## CRITICAL: Use Subagents
- `database-expert` — Migration, junction tables, backfill
- `tdd-implementor` — Service layer rewrite, test rewrite

## STOP CONDITIONS
If ANY of these occur, STOP and document in chain log:
- Undocumented code paths writing to Message.meta_data
- Test failures from undocumented JSONB dependencies
- Frontend requiring major restructuring

## Execute
1. Read handover completely
2. Check chain log, mark in_progress
3. Use subagents for phases
4. Update chain log
5. Commit, spawn next terminal

## On Completion
**Use Bash tool to EXECUTE the spawn command from the handover document Step 6.**
