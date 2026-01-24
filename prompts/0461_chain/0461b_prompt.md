# Terminal Session: 0461b - Database Schema Cleanup

## Mission
Execute Handover 0461b (Part 2/5 of Handover Simplification Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0461b_database_schema_cleanup.md`

---

## CHAIN LOG - Read First!
**Log File**: `F:\GiljoAI_MCP\prompts\0461_chain\chain_log.json`

**IMPORTANT**: Read `sessions[0]` (0461a) to see:
- What the previous team actually completed
- Any deviations from the plan
- Notes they left for you
- Any blockers to be aware of

---

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="database-expert", prompt="Read the handover document at F:\GiljoAI_MCP\handovers\0461b_database_schema_cleanup.md and execute Task 1: Add deprecation comments to AgentExecution model columns (instance_number, decommissioned_at, succeeded_by, succession_reason, handover_summary)")
```

Recommended subagents for this handover:
- `database-expert` - For schema changes and deprecation markers
- `tdd-implementor` - For 360 Memory entry type support

## Prerequisite Check
Verify 0461a complete:
- Check chain_log.json: `sessions[0].status` should be "complete"
- Run: `grep -r "should_trigger_succession" src/` → Should return nothing

## Execute
1. Read the chain log to understand what 0461a actually did
2. Read the handover document completely
3. **Use Task tool subagents** to:
   - Task 1: Add deprecation comments to AgentExecution model
   - Task 2: Update AgentExecution class docstring
   - Task 3: Add `session_handover` entry type to write_360_memory.py
   - Task 4: Document session_handover schema in 360_MEMORY_MANAGEMENT.md
   - Task 5: Verify ProductMemoryRepository handles new entry type
4. Run verification: `pytest tests/ -k "360_memory" -v`

## Success Criteria
- [ ] 5 columns have deprecation comments
- [ ] AgentExecution docstring updated
- [ ] `session_handover` entry type works
- [ ] Documentation updated
- [ ] All tests pass

---

## BEFORE SPAWNING NEXT TERMINAL - Update Chain Log!

**Use the Edit tool to update `F:\GiljoAI_MCP\prompts\0461_chain\chain_log.json`**

Update the `sessions[1]` (0461b) entry with:
```json
{
  "status": "complete",
  "started_at": "<timestamp>",
  "completed_at": "<timestamp>",
  "tasks_completed": ["<list what you actually did>"],
  "deviations": ["<any changes from the plan, or empty array if none>"],
  "blockers_encountered": ["<any issues hit, or empty array if none>"],
  "notes_for_next": "<important info for 0461c team>",
  "summary": "<2-3 sentence summary of what was accomplished>"
}
```

---

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0461c - Backend Simplify\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0461c. Read F:\GiljoAI_MCP\prompts\0461_chain\0461c_prompt.md for full instructions. The handover document is at F:\GiljoAI_MCP\handovers\0461c_backend_simplification.md. Use Task subagents (tdd-implementor, backend-tester) to complete all phases.\"' -Verb RunAs"
```
