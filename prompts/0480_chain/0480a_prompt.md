# Terminal Session: 0480a - Exception Framework Foundation

## Mission
Execute Handover 0480a (Part 1/6 of REVISED Series).

## Handover Document
**READ THIS FIRST**: `F:\GiljoAI_MCP\handovers\0480a_foundation_REVISED.md`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="system-architect", prompt="Modify BaseGiljoException in src/giljo_mcp/exceptions.py to add default_status_code and to_dict() method...")
```

Recommended subagents for this handover:
- `system-architect` - For modifying exception hierarchy
- `tdd-implementor` - For writing tests

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete all tasks
3. Verify success criteria in handover document

## Success Criteria
- [ ] BaseGiljoException has default_status_code and to_dict()
- [ ] All exception classes have HTTP status codes
- [ ] Global handler created and registered
- [ ] Tests pass

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0480b - Services Auth/Product\" --tabColor \"#2196F3\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0480b. Read F:\GiljoAI_MCP\prompts\0480_chain\0480b_prompt.md for instructions.\"' -Verb RunAs"
```
