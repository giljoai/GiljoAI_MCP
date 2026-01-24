# Terminal Session: 0452 - Delete orchestrator.py

## Mission
Execute Handover 0452 (Part 3/4 of Orchestrator Consolidation Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0452_delete_orchestrator_py.md`

## Reference Documents
- **QUICK_LAUNCH.txt**: `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt`
- **CLAUDE.md**: `F:\GiljoAI_MCP\CLAUDE.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="tdd-implementor", prompt="Delete orchestrator.py and fix all cascading imports...")
Task(subagent_type="backend-tester", prompt="Verify no orphaned references remain in codebase...")
```

Recommended subagents for this handover:
- `tdd-implementor` - Fix cascading test failures
- `backend-tester` - Verify cleanup is complete
- `deep-researcher` - Find any hidden references

## Prerequisite Check
Verify previous handovers (0450, 0451) complete:
```bash
pytest tests/services/test_orchestration_service_consolidation.py -v --tb=short
pytest tests/services/test_orchestration_service_instructions.py -v --tb=short
# All tests must pass
```

## Execute
1. Read the handover document completely
2. **Use Task tool subagents** to complete:
   - Phase 1: Pre-deletion verification (all service tests pass)
   - Phase 2: Delete orchestrator.py
   - Phase 3: Fix cascading imports
   - Phase 4: Delete orphaned test files
   - Phase 5: Update remaining tests
   - Phase 6: Final verification (grep for orphans)
3. Commit changes with descriptive message

## Success Criteria
- [ ] `orchestrator.py` deleted (1,675 lines removed)
- [ ] No orphaned imports (`grep -r "ProjectOrchestrator" src/ api/` returns nothing)
- [ ] All remaining tests pass
- [ ] MCP tools work end-to-end
- [ ] Git commit made

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0453 - TDD Test Rewrite\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0453. Read F:\GiljoAI_MCP\prompts\0450_consolidation_chain\0453_prompt.md for full instructions. The handover document is at F:\GiljoAI_MCP\handovers\0453_tdd_test_rewrite.md. Use Task subagents (tdd-implementor, backend-tester) to complete all phases.\"' -Verb RunAs"
```
