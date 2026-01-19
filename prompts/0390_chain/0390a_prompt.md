# Terminal Session: 0390a - Add Product Memory Entries Table

## Mission
Execute Handover 0390a (Part 1/4 360 Memory JSONB Normalization).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0390a_add_memory_entries_table.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="database-expert", prompt="Execute Phase 4 of handover 0390a - create Alembic migration with backfill...")
Task(subagent_type="tdd-implementor", prompt="Execute Phase 1 RED - write failing repository tests per handover 0390a...")
```

Recommended subagents for this handover:
- `database-expert` - For schema design, migration, backfill logic
- `tdd-implementor` - For TDD test-first approach, model, repository

## Phase 0 - SAFETY NET (Do First!)
```bash
git checkout -b 0390-360-memory-normalization
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/pg_dump.exe -U postgres giljo_mcp > backup_pre_0390.sql
pytest tests/ --tb=no -q | grep -E "passed|failed"
```

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Complete all phases (Safety Net, RED tests, Model, Repository, Migration, GREEN)

## Success Criteria
- [ ] Table `product_memory_entries` exists
- [ ] SQLAlchemy model works
- [ ] Repository CRUD works
- [ ] Backfill migrates all JSONB data
- [ ] All 10+ TDD tests pass
- [ ] Existing tests pass

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0390b - Switch Reads\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0390b. Read F:\GiljoAI_MCP\prompts\0390_chain\0390b_prompt.md for instructions. CRITICAL: Use Task tool subagents (tdd-implementor, backend-tester). When done, RUN spawn command.\"' -Verb RunAs"
```
