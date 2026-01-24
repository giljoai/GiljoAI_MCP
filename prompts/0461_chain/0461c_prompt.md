# Terminal Session: 0461c - Backend Simplification

## Mission
Execute Handover 0461c (Part 3/5 of Handover Simplification Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0461c_backend_simplification.md`

---

## CHAIN LOG - Read First!
**Log File**: `F:\GiljoAI_MCP\prompts\0461_chain\chain_log.json`

**IMPORTANT**: Read `sessions[0]` and `sessions[1]` (0461a, 0461b) to see:
- What the previous teams actually completed
- Any deviations from the plan
- Notes they left for you
- Any blockers to be aware of

Pay special attention to 0461b's notes about the `session_handover` entry type - you'll need it!

---

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="tdd-implementor", prompt="Read the handover document at F:\GiljoAI_MCP\handovers\0461c_backend_simplification.md and execute Task 1: Create the new simple_handover.py endpoint at api/endpoints/agent_jobs/simple_handover.py that writes to 360 Memory, resets context, and returns continuation prompt")
```

Recommended subagents for this handover:
- `tdd-implementor` - For endpoint creation and service updates
- `backend-tester` - For integration testing

## Prerequisite Check
Verify 0461b complete:
- Check chain_log.json: `sessions[1].status` should be "complete"
- Run: `grep -r "session_handover" src/giljo_mcp/tools/write_360_memory.py` → Should find entry type

## Execute
1. Read the chain log to understand what previous sessions did
2. Read the handover document completely
3. **Use Task tool subagents** to:
   - Task 1: Create simple_handover.py endpoint (NEW FILE)
   - Task 2: Register endpoint in __init__.py and app.py
   - Task 3: Update ThinClientPromptGenerator._generate_continuation_prompt()
   - Task 4: Simplify OrchestrationService.trigger_succession()
   - Task 5: Update /gil_handover slash command
   - Task 6: Write unit tests for simple_handover
4. Run verification: `pytest tests/ -v`

## Success Criteria
- [ ] `/api/agent-jobs/{job_id}/simple-handover` endpoint works
- [ ] Writes `session_handover` to 360 Memory
- [ ] Resets `context_used` to 0
- [ ] Continuation prompt instructs reading 360 Memory
- [ ] No Agent ID Swap logic executed
- [ ] All tests pass

---

## BEFORE SPAWNING NEXT TERMINAL - Update Chain Log!

**Use the Edit tool to update `F:\GiljoAI_MCP\prompts\0461_chain\chain_log.json`**

Update the `sessions[2]` (0461c) entry with:
```json
{
  "status": "complete",
  "started_at": "<timestamp>",
  "completed_at": "<timestamp>",
  "tasks_completed": ["<list what you actually did>"],
  "deviations": ["<any changes from the plan, or empty array if none>"],
  "blockers_encountered": ["<any issues hit, or empty array if none>"],
  "notes_for_next": "<important info for 0461d frontend team - especially about new WebSocket event and API response format>",
  "summary": "<2-3 sentence summary of what was accomplished>"
}
```

---

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0461d - Frontend Simplify\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0461d. Read F:\GiljoAI_MCP\prompts\0461_chain\0461d_prompt.md for full instructions. The handover document is at F:\GiljoAI_MCP\handovers\0461d_frontend_simplification.md. Use Task subagents (frontend-tester, ux-designer) to complete all phases.\"' -Verb RunAs"
```
