# Terminal Session: 0390b - Switch Reads to Table

## Mission
Execute Handover 0390b (Part 2/4 360 Memory JSONB Normalization).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0390b_switch_reads_to_table.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="tdd-implementor", prompt="Update get_360_memory.py to use ProductMemoryRepository per handover 0390b Phase 2a...")
Task(subagent_type="backend-tester", prompt="Run integration tests for 360 memory reads per handover 0390b Phase 7...")
```

Recommended subagents for this handover:
- `tdd-implementor` - For code modifications with TDD
- `backend-tester` - For integration testing
- `frontend-tester` - For frontend updates

## Prerequisite Check
Verify 0390a complete:
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM product_memory_entries;"
pytest tests/repositories/test_product_memory_repository.py -v
```

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Switch all 12 READ locations to use repository

## Success Criteria
- [ ] All API endpoints return table data
- [ ] Query performance equal or better
- [ ] WebSocket events work
- [ ] Frontend displays correctly
- [ ] Project deletion marks table entries
- [ ] All tests pass

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0390c - Stop JSONB Writes\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0390c. Read F:\GiljoAI_MCP\prompts\0390_chain\0390c_prompt.md for instructions. CRITICAL: Use Task tool subagents. When done, RUN spawn command.\"' -Verb RunAs"
```
