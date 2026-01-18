# Terminal Session: 0387e - Add Message Counter Columns

## Mission
Execute Handover 0387e (Part 1/5 JSONB Normalization).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0387e_add_message_counter_columns.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="database-expert", prompt="Execute Phase 3 of handover 0387e - create Alembic migration...")
Task(subagent_type="tdd-implementor", prompt="Execute Phase 1 RED - write failing tests per handover 0387e...")
```

Recommended subagents for this handover:
- `database-expert` - For schema changes and migration
- `tdd-implementor` - For TDD test-first approach

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Complete all phases (Safety Net, RED, GREEN, Migration, Repository)

## Success Criteria
- 3 counter columns on AgentExecution
- Migration applies cleanly
- 7 TDD tests pass
- Existing tests pass

## On Completion - Spawn Next Terminal
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0387f - Stop JSONB Writes\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0387f. Read F:\GiljoAI_MCP\prompts\0387_chain\0387f_prompt.md for instructions. Use Task subagents (tdd-implementor, backend-tester) to complete all phases. When done, spawn next terminal per the prompt file.\"' -Verb RunAs"
```
