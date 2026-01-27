# Terminal Session: 0480b - Services Auth & Product

## Mission
Execute Handover 0480b (Part 2/6 of REVISED Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0480b_services_auth_product_REVISED.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="tdd-implementor", prompt="Migrate auth_service.py from dict returns to raising exceptions...")
```

Recommended subagents for this handover:
- `tdd-implementor` - For migrating service methods
- `backend-integration-tester` - For testing exception paths

## Prerequisite Check
Verify 0480a complete: Global exception handler registered in api/app.py

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete all tasks
3. Run verification command from handover

## Success Criteria
- [ ] Zero dict returns in auth_service.py
- [ ] Zero dict returns in product_service.py
- [ ] Tests pass

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0480c - Services Core\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0480c. Read F:\GiljoAI_MCP\prompts\0480_chain\0480c_prompt.md for instructions.\"' -Verb RunAs"
```
