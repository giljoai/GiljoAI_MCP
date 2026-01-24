# Terminal Session: 0450 - Move Core Logic to OrchestrationService

## Mission
Execute Handover 0450 (Part 1/4 of Orchestrator Consolidation Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0450_move_orchestrator_core_logic.md`

## Reference Documents
- **QUICK_LAUNCH.txt**: `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt`
- **CLAUDE.md**: `F:\GiljoAI_MCP\CLAUDE.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="tdd-implementor", prompt="Write failing tests for process_product_vision in OrchestrationService...")
Task(subagent_type="backend-tester", prompt="Verify multi-tenant isolation in new service methods...")
```

Recommended subagents for this handover:
- `tdd-implementor` - Write tests first, then implement
- `backend-tester` - Verify integration tests pass
- `database-expert` - If any schema questions arise

## Pre-Flight Check
Before starting, verify:
1. Database backup exists: `ls F:/GiljoAI_MCP/backups/db_backup_orchestrator_consolidation*.dump`
2. On correct branch: `git branch --show-current` should show `_orchestrator_tool_accessor_consolidation`
3. Tests currently pass: `pytest tests/services/test_orchestration_service.py -v --tb=short`

## Execute
1. Read the handover document completely
2. **Use Task tool subagents** to complete:
   - Phase 1: Write failing tests (RED)
   - Phase 2: Implement in OrchestrationService (GREEN)
   - Phase 3: Update callers
   - Phase 4: Verify all tests pass
3. Commit changes with descriptive message

## Success Criteria
- [ ] New tests created and passing
- [ ] `process_product_vision` works via OrchestrationService
- [ ] Duplicate project bug fixed
- [ ] Existing tests still pass
- [ ] Git commit made

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0451 - Tool Accessor Inline\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0451. Read F:\GiljoAI_MCP\prompts\0450_consolidation_chain\0451_prompt.md for full instructions. The handover document is at F:\GiljoAI_MCP\handovers\0451_move_tool_accessor_inline_code.md. Use Task subagents (tdd-implementor, backend-tester) to complete all phases.\"' -Verb RunAs"
```
