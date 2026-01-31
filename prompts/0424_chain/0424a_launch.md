# 0424a Launch - Database Schema

## Slim Launch Command

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0424a - Database Schema\" --tabColor \"#4CAF50\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0424a. READ: F:\GiljoAI_MCP\handovers\0424a_database_schema.md\"' -Verb RunAs"
```

## What This Does

1. Opens Windows Terminal with green tab
2. Launches Claude Code with skip-permissions
3. Claude reads the handover document which contains:
   - Full implementation plan
   - Chain log creation instructions (first in series)
   - TDD steps
   - Spawn command for next terminal
