# Terminal Session: 0390c - Stop JSONB Writes

## Mission
Execute Handover 0390c (Part 3/4 360 Memory JSONB Normalization).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0390c_stop_jsonb_writes.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="tdd-implementor", prompt="Update write_360_memory.py to insert into table per handover 0390c Phase 2...")
Task(subagent_type="backend-tester", prompt="Run tests for table-based writes per handover 0390c Phase 5...")
```

Recommended subagents for this handover:
- `tdd-implementor` - For code modifications with TDD
- `backend-tester` - For integration testing

## Prerequisite Check
Verify 0390b complete (all reads from table):
```bash
grep -rn "sequential_history" src/giljo_mcp/tools/context_tools/
# Should show NO JSONB reads
pytest tests/ -v --tb=short
```

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Switch all 7 WRITE locations to insert into table

## Success Criteria
- [ ] Zero JSONB writes for 360 memory
- [ ] All entries created in table
- [ ] Sequence numbers atomic
- [ ] WebSocket events work
- [ ] TDD tests pass

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0390d - Deprecate JSONB\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0390d. Read F:\GiljoAI_MCP\prompts\0390_chain\0390d_prompt.md for instructions. This is the FINAL handover. Complete all steps and merge to master.\"' -Verb RunAs"
```
