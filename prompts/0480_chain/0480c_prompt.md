# Terminal Session: 0480c - Services Core

## Mission
Execute Handover 0480c (Part 3/6 of REVISED Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0480c_services_core_REVISED.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Recommended subagents for this handover:
- `tdd-implementor` - For migrating service methods
- `backend-integration-tester` - For testing exception paths

## Prerequisite Check
Verify 0480a complete: Global exception handler registered in api/app.py

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete all tasks
3. Verify zero dict returns in all three services

## Success Criteria
- [ ] Zero dict returns in project_service.py
- [ ] Zero dict returns in orchestration_service.py
- [ ] Zero dict returns in template_service.py
- [ ] Tests pass

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0480d - Services Remaining\" --tabColor \"#FF9800\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0480d. Read F:\GiljoAI_MCP\prompts\0480_chain\0480d_prompt.md for instructions.\"' -Verb RunAs"
```
