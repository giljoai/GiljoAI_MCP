# Terminal Session: 0387h - Test Updates + Cleanup

## Mission
Execute Handover 0387h (Part 4/5 JSONB Normalization).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0387h_test_updates_cleanup.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="backend-tester", prompt="Delete obsolete JSONB tests per handover 0387h Section 2...")
Task(subagent_type="tdd-implementor", prompt="Rewrite integration tests to use counters per handover 0387h Section 3...")
```

Recommended subagents for this handover:
- `backend-tester` - For test updates and verification
- `tdd-implementor` - For rewriting tests with TDD approach

## Prerequisite Check
Verify 0387g complete: frontend uses counters.

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Delete 5 obsolete tests, rewrite 12 tests, update fixtures

## Success Criteria
- All obsolete tests deleted
- All fixtures updated (no `messages=[]`)
- 100% test pass rate
- Coverage >80%
- Zero `execution.messages` references

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0387i - Deprecate Column\" --tabColor \"#F44336\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0387i (FINAL). Read F:\GiljoAI_MCP\prompts\0387_chain\0387i_prompt.md for instructions. CRITICAL: Use Task tool subagents. This is FINAL - merge to master when done.\"' -Verb RunAs"
```
