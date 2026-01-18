# Terminal Session: 0387f - Stop JSONB Writes

## Mission
Execute Handover 0387f (Part 2/5 JSONB Normalization).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0387f_backend_stop_jsonb_writes.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="tdd-implementor", prompt="Remove JSONB write methods from MessageService per handover 0387f Phase 2...")
Task(subagent_type="backend-tester", prompt="Run integration tests for message flow per handover 0387f Phase 5...")
```

Recommended subagents for this handover:
- `tdd-implementor` - For code modifications with TDD
- `backend-tester` - For integration testing

## Prerequisite Check
Verify 0387e complete: counter columns exist in DB.

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. Remove JSONB write methods, update reads to use counters

## Success Criteria
- Zero JSONB writes in MessageService
- All reads use counters or Message table
- WebSocket events include counter values
- Tests pass (document failures for 0387h)

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0387g - Frontend Counters\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0387g. Read F:\GiljoAI_MCP\prompts\0387_chain\0387g_prompt.md for instructions. CRITICAL: Use Task tool subagents. When done, RUN spawn command.\"' -Verb RunAs"
```
