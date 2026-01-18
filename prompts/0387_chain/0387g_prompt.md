# Terminal Session: 0387g - Frontend Use Counters

## Mission
Execute Handover 0387g (Part 3/5 JSONB Normalization).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0387g_frontend_use_counters.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="frontend-tester", prompt="Update agentJobsStore.js to use counter fields per handover 0387g Phase 3...")
Task(subagent_type="ux-designer", prompt="Update MessageAuditModal to fetch from API per handover 0387g Phase 4...")
```

Recommended subagents for this handover:
- `frontend-tester` - For Vue component updates and testing
- `ux-designer` - For UI component modifications

## Prerequisite Check
Verify 0387f complete: API returns counter fields.

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Create Messages API endpoint, update stores/components

## Success Criteria
- Counters display correctly in UI
- WebSocket updates work
- MessageAuditModal fetches from API
- No `agent.messages` array references
- Frontend tests pass

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0387h - Test Cleanup\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0387h. Read F:\GiljoAI_MCP\prompts\0387_chain\0387h_prompt.md for instructions. CRITICAL: Use Task tool subagents. When done, RUN spawn command.\"' -Verb RunAs"
```
