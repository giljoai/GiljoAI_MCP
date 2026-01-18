# Multi-Terminal Chain Execution Strategy

**Created**: 2026-01-18
**Purpose**: Document the proven pattern for spawning chained Claude Code terminal sessions with pre-loaded prompts for sequential handover execution.

---

## Executive Summary

This document describes how to orchestrate multiple Claude Code terminal sessions that execute sequentially, each spawning the next upon completion. This pattern enables:
- Parallel-like execution across isolated contexts
- Visual tracking via colored terminal tabs
- Automatic chaining without manual intervention
- Subagent delegation within each session

---

## Core Syntax

### Terminal Spawn Command (PowerShell)

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"TITLE\" --tabColor \"#HEX\" -d \"WORKDIR\" cmd /k claude --dangerously-skip-permissions \"YOUR PROMPT\"' -Verb RunAs"
```

### Parameter Breakdown

| Parameter | Purpose | Example |
|-----------|---------|---------|
| `--title` | Tab/window title for identification | `"0387f - Stop JSONB Writes"` |
| `--tabColor` | Hex color for visual tracking | `"#2196F3"` (blue) |
| `-d` | Working directory | `"F:\GiljoAI_MCP"` |
| `cmd /k` | Keep terminal open after command | Required for interactive session |
| `claude` | Claude Code CLI | The AI agent |
| `--dangerously-skip-permissions` | Bypass all permission prompts | **CRITICAL** - enables autonomous execution |
| `"YOUR PROMPT"` | Initial prompt passed to Claude | The mission instructions |
| `-Verb RunAs` | Run as Administrator | Required for elevated permissions |

### Color Scheme (Visual Progress Tracking)

| Phase | Color | Hex | Meaning |
|-------|-------|-----|---------|
| Phase 1 | Green | `#4CAF50` | Foundation/Database |
| Phase 2 | Blue | `#2196F3` | Backend changes |
| Phase 3 | Purple | `#9C27B0` | Frontend changes |
| Phase 4 | Orange | `#FF9800` | Testing/Cleanup |
| Phase 5 | Red | `#F44336` | Final/Merge |

---

## Prompt File Structure

Each terminal session needs a prompt file that instructs the agent. Store in: `prompts/{project}_chain/`

### Template Structure

```markdown
# Terminal Session: {ID} - {Title}

## Mission
Execute Handover {ID} (Part X/Y of Series).

## Handover Document
**READ THIS FIRST**: `{path_to_handover.md}`

## CRITICAL: Use Task Tool Subagents
**YOU MUST use the Task tool to spawn subagents for this work. Do NOT do the work directly.**

Example:
```
Task(subagent_type="{agent_type}", prompt="{specific_task}...")
```

Recommended subagents for this handover:
- `{agent1}` - For {purpose}
- `{agent2}` - For {purpose}

## Prerequisite Check
Verify previous handover complete: {criteria}

## Execute
1. Read the handover document above completely
2. **Use Task tool subagents** to complete phases
3. {Specific execution steps}

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] etc.

## On Completion - EXECUTE This Command (Don't Just Print It!)
**Use Bash tool to RUN this command:**
```powershell
{spawn_command_for_next_terminal}
```
```

### Critical Instructions That Must Be Explicit

1. **READ THIS FIRST** - Point to the actual handover document
2. **CRITICAL: Use Task Tool Subagents** - With examples of exact syntax
3. **EXECUTE This Command (Don't Just Print It!)** - Agents tend to display commands instead of running them
4. **Use Bash tool to RUN** - Explicit tool instruction

---

## Lessons Learned

### Problem: Trust/Permission Prompts Block Execution
**Solution**: Use `--dangerously-skip-permissions` flag

### Problem: Agent Displays Spawn Command Instead of Running It
**Solution**: Add explicit instruction: "Use Bash tool to RUN this command" and "Don't Just Print It!"

### Problem: Agent Doesn't Know Handover Document Location
**Solution**: Include explicit path in both initial prompt AND prompt file with "READ THIS FIRST"

### Problem: Agent Does Work Directly Instead of Using Subagents
**Solution**: Add "CRITICAL" section with examples showing Task tool syntax

### Problem: Terminal Doesn't Have Admin Rights
**Solution**: Add `-Verb RunAs` to PowerShell command

---

## Implementation Checklist

### Setup Phase
- [ ] Create `prompts/{project}_chain/` directory
- [ ] Write prompt file for each handover in sequence
- [ ] Include explicit handover document paths
- [ ] Include subagent usage examples
- [ ] Include spawn commands for next terminal
- [ ] Use distinct colors for each phase

### Prompt File Requirements
- [ ] Mission statement
- [ ] Handover document path (READ THIS FIRST)
- [ ] CRITICAL subagent instruction with examples
- [ ] Prerequisite check (for non-first handovers)
- [ ] Success criteria
- [ ] Spawn command with "EXECUTE" instruction (or "CHAIN COMPLETE" for last)

### Spawn Command Requirements
- [ ] `--dangerously-skip-permissions` flag
- [ ] `-Verb RunAs` for admin
- [ ] Correct working directory
- [ ] Title and color for identification
- [ ] Initial prompt includes prompt file path

---

## Example: 0387 Phase 4 Chain

### Chain Overview
```
0387e (Green) → 0387f (Blue) → 0387g (Purple) → 0387h (Orange) → 0387i (Red)
   ↓               ↓               ↓               ↓               ↓
 Database       Backend         Frontend         Testing          Final
 Foundation     Changes         Changes          Cleanup          Merge
```

### Initial Spawn (From Orchestrator Session)
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0387e - Counter Columns\" --tabColor \"#4CAF50\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0387e. Read F:\GiljoAI_MCP\prompts\0387_chain\0387e_prompt.md for full instructions. The handover document is at F:\GiljoAI_MCP\handovers\0387e_add_message_counter_columns.md. Use Task subagents (database-expert, tdd-implementor) to complete all phases.\"' -Verb RunAs"
```

### Subagent Mapping by Handover Type

| Handover Type | Recommended Subagents |
|---------------|----------------------|
| Database/Schema | `database-expert`, `tdd-implementor` |
| Backend Code | `tdd-implementor`, `backend-tester` |
| Frontend Code | `frontend-tester`, `ux-designer` |
| Test Updates | `backend-tester`, `tdd-implementor` |
| Documentation | `documentation-manager`, `backend-tester` |

---

## Troubleshooting

### Terminal Opens But Claude Doesn't Start
- Check Windows Terminal is installed
- Verify `claude` is in PATH
- Check for syntax errors in ArgumentList

### Claude Starts But Prompt Not Loaded
- Ensure prompt is properly escaped in quotes
- Check for special characters that need escaping
- Verify prompt length isn't exceeding limits

### Agent Doesn't Spawn Next Terminal
- Check if agent printed command vs executed it
- Verify Bash tool is available
- Manually run the spawn command if needed

### Permission Denied Errors
- Ensure `-Verb RunAs` is included
- Accept UAC prompt when it appears
- Verify `--dangerously-skip-permissions` is present

---

## Results: 0387 Phase 4 Execution

**Total Execution**: 5 chained terminals
**Files Changed**: 75 files, 8,321 insertions, 919 deletions
**New Files**: 27 created
**Tests**: 3,743 collected, core tests passing
**Outcome**: Complete JSONB normalization with counter-based architecture

### Chain Completion Log
1. ✅ 0387e - Counter columns added, 7 TDD tests pass
2. ✅ 0387f - JSONB writes removed, counters used
3. ✅ 0387g - Frontend updated to use counters
4. ✅ 0387h - Tests updated, fixtures cleaned
5. ✅ 0387i - Column deprecated, docs updated, merged to master

---

## Future Improvements

1. **Auto-spawn detection**: Hook that triggers spawn when success criteria met
2. **Progress dashboard**: WebSocket-based monitoring of chain status
3. **Rollback chain**: Reverse execution if issues detected
4. **Parallel branches**: Non-dependent handovers in parallel terminals

---

**Document Version**: 1.0
**Last Updated**: 2026-01-18
**Author**: Claude Opus 4.5 (Orchestrator Session)
