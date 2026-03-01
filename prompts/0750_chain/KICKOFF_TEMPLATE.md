# 0750 Cleanup Sprint — Default Kickoff Prompt

## Usage

Replace `{HANDOVER_PATH}` with the specific handover file path. Everything else stays the same.

## Kickoff Command

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0750x - Cleanup Sprint\" --tabColor \"#COLOR\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"You are executing a cleanup handover. READ the handover document FIRST, then execute every task in it. Handover: F:\GiljoAI_MCP\{HANDOVER_PATH}. Chain log: F:\GiljoAI_MCP\prompts\0750_chain\chain_log.json. Progress tracker: F:\GiljoAI_MCP\handovers\0700_series\0750_cleanup_progress.json. RULES: 1) Read the handover completely before starting. 2) Use Task tool subagents where the handover recommends them. 3) Update the chain log when done. 4) Do NOT spawn the next terminal — the orchestrator handles chaining. 5) Commit with the message format specified in the handover. 6) Work on branch 0750-cleanup-sprint. 7) No AI signatures in code or commits.\"' -Verb RunAs"
```

## Color Assignments

| Phase | Handover | Color | Hex |
|-------|----------|-------|-----|
| 1 | 0750a | Green | #4CAF50 |
| 2 | 0750b | Blue | #2196F3 |
| 3 | 0750c | Purple | #9C27B0 |
| 4 | 0750d | Orange | #FF9800 |
| 5 | 0750e | Teal | #009688 |
| 6 | 0750f | Amber | #FFC107 |
| 7 | 0750g | Red | #F44336 |
