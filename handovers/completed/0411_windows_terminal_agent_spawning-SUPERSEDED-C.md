# Handover 0411: Windows Terminal Agent Spawning

**Status**: SUPERSEDED
**Priority**: N/A
**Estimated Effort**: N/A
**Created**: 2026-01-08
**Validated**: 2026-01-08 (all commands tested successfully)
**Superseded**: 2026-02-24
**Superseded By**: 0411a (Recommended Execution Order) + 0411b (Dead Code Cleanup)
**Reason**: Auto-terminal spawning shelved in favor of advisory phase labels on AgentJob. The orchestrator recommends execution order during staging; the user remains the scheduler. Agent Lab (AgentTipsDialog.vue) retains the manual spawn command reference. See 0411a for full decision history.

---

## Executive Summary

Discovered and validated the ability for an orchestrator agent to **spawn multiple CLI agents in Windows Terminal tabs** with colored tabs, custom titles, and proper profile loading. This enables true multi-agent orchestration where one orchestrator can automatically launch an entire agent team.

### Key Discovery

```powershell
# Orchestrator opens first window (blue tab)
wt.exe -d "F:\GiljoAI_MCP" --title "Orchestrator" --tabColor "#2196F3" pwsh -NoExit -Command "claude --dangerously-skip-permissions 'Your prompt'"

# Additional agents join as tabs in same window
wt.exe -w 0 new-tab -d "F:\GiljoAI_MCP" --title "Implementer" --tabColor "#4CAF50" pwsh -NoExit -Command "claude --dangerously-skip-permissions 'Your prompt'"
```

### Impact

- Orchestrator can spawn entire agent teams automatically
- Visual organization with colored tabs per agent type
- User's PowerShell profile loads (colors, icons, environment)
- Works with multiple CLI tools (Claude, Codex, Gemini)

---

## Problem Statement

In Multi-Terminal Mode (toggle OFF), users had to manually:
1. Copy orchestrator prompt → paste in Terminal 1
2. Copy implementer prompt → paste in Terminal 2
3. Copy tester prompt → paste in Terminal 3
4. (Repeat for all agents)

This was tedious and error-prone for larger agent teams.

---

## Solution: Windows Terminal Spawning

### Critical Syntax Discoveries

#### 1. Claude Code CLI

```powershell
# WRONG - "-p" means "print and exit", not "pass prompt"
claude --dangerously-skip-permissions -p "prompt"  # Exits immediately!

# CORRECT - Prompt is positional argument AFTER options
claude --dangerously-skip-permissions "Your prompt here"
```

#### 2. Codex CLI (OpenAI)

```powershell
codex --dangerously-bypass-approvals-and-sandbox -C "F:\GiljoAI_MCP" "Your prompt here"
```

#### 3. Windows Terminal vs PowerShell Direct

```powershell
# WRONG - Opens raw PowerShell, no profile/customization
pwsh.exe -NoExit -Command "claude ..."

# CORRECT - Opens Windows Terminal with user profile
wt.exe -d "path" --title "Title" --tabColor "#HEX" pwsh -NoExit -Command "claude ..."
```

### Windows Terminal Command Structure

| Option | Description |
|--------|-------------|
| `-d <path>` | Starting directory |
| `--title "Title"` | Tab title |
| `--tabColor "#HEXCODE"` | Tab color |
| `-p "Profile Name"` | Use specific WT profile |
| `-w 0` | Target most recent window |
| `new-tab` | Open as new tab (not window) |

### Complete Spawning Pattern

```powershell
# First agent - opens NEW WINDOW
wt.exe -d "F:\GiljoAI_MCP" --title "Orchestrator" --tabColor "#2196F3" pwsh -NoExit -Command "claude --dangerously-skip-permissions 'Orchestrator prompt'"

# Subsequent agents - open as TABS in same window
wt.exe -w 0 new-tab -d "F:\GiljoAI_MCP" --title "Implementer" --tabColor "#4CAF50" pwsh -NoExit -Command "claude --dangerously-skip-permissions 'Implementer prompt'"

wt.exe -w 0 new-tab -d "F:\GiljoAI_MCP" --title "Tester" --tabColor "#FF9800" pwsh -NoExit -Command "claude --dangerously-skip-permissions 'Tester prompt'"

wt.exe -w 0 new-tab -d "F:\GiljoAI_MCP" --title "Codex Agent" --tabColor "#9C27B0" pwsh -NoExit -Command "codex --dangerously-bypass-approvals-and-sandbox -C 'F:\GiljoAI_MCP' 'Codex prompt'"
```

---

## Color Palette for Agent Types

| Agent Type | Hex Color | Visual |
|------------|-----------|--------|
| Orchestrator | `#2196F3` | Blue |
| Implementer | `#4CAF50` | Green |
| Tester | `#FF9800` | Orange |
| Documenter | `#9C27B0` | Purple |
| Analyzer | `#F44336` | Red |
| Reviewer | `#00BCD4` | Cyan |
| Codex (OpenAI) | `#10A37F` | OpenAI Green |
| Gemini (Google) | `#4285F4` | Google Blue |

---

## Integration with GiljoAI Architecture

### Updated Multi-Terminal Flow

```
┌─────────────────────────────────────────────────────────────┐
│  Windows Terminal                                            │
├──────────┬──────────┬──────────┬──────────┬────────────────┤
│ Orch     │ Impl     │ Test     │ Doc      │ Codex...       │
│ #2196F3  │ #4CAF50  │ #FF9800  │ #9C27B0  │ #10A37F        │
└──────────┴──────────┴──────────┴──────────┴────────────────┘
      │           │          │          │          │
      └───────────┴──────────┴──────────┴──────────┘
                             │
                     ┌───────▼───────┐
                     │  GiljoAI MCP  │
                     │    Server     │
                     │  Message Hub  │
                     └───────────────┘
```

### Orchestrator Spawning Workflow

1. User pastes orchestrator thin prompt in their terminal
2. Orchestrator fetches mission via `get_orchestrator_instructions()`
3. Orchestrator calls `spawn_agent_job()` for each agent (creates DB records)
4. **NEW**: Orchestrator uses Bash to run `wt.exe` commands for each agent
5. Windows Terminal tabs open with colored agents
6. Each agent calls `get_agent_mission(job_id, tenant_key)` to fetch its mission
7. All agents coordinate via MCP message hub

### Example Orchestrator Bash Commands

```python
# In orchestrator's execution phase, after spawn_agent_job() calls:

# Spawn Implementer (green tab)
subprocess.run([
    'cmd', '/c', 'start', '', 'wt.exe', '-w', '0', 'new-tab',
    '-d', workspace_path,
    '--title', f'Implementer - {agent_name}',
    '--tabColor', '#4CAF50',
    'pwsh', '-NoExit', '-Command',
    f"claude --dangerously-skip-permissions 'You are {agent_type}. Call get_agent_mission(\"{job_id}\", \"{tenant_key}\") to fetch your mission.'"
])
```

---

## Claude Code Bash Tool Usage

When spawning from Claude Code, use `run_in_background: true` to avoid blocking:

```python
# This blocks the orchestrator until command completes
Bash("cmd //c start wt.exe ...")  # BAD

# This returns immediately, orchestrator continues
Bash("cmd //c start wt.exe ...", run_in_background=True)  # GOOD
```

---

## Cross-Platform Considerations

| Platform | Terminal | Command |
|----------|----------|---------|
| Windows | Windows Terminal | `wt.exe -w 0 new-tab ...` |
| macOS | iTerm2 | `osascript -e 'tell application "iTerm2" to create tab...'` |
| macOS | Terminal.app | `osascript -e 'tell application "Terminal" to do script...'` |
| Linux | gnome-terminal | `gnome-terminal --tab --title="Agent" -- bash -c "claude ..."` |
| Linux | tmux | `tmux new-window -n "Agent" "claude ..."` |

**Note**: This handover focused on Windows. Linux/macOS implementations would follow similar patterns with platform-specific terminal commands.

---

## Testing Performed

| Test | Result |
|------|--------|
| Spawn Claude via raw pwsh.exe | Works but no profile |
| Spawn Claude via wt.exe | Works with profile |
| Spawn multiple tabs (-w 0 new-tab) | Works |
| Tab colors (--tabColor) | Works |
| Tab titles (--title) | Works |
| Spawn Codex in tab | Works |
| run_in_background: true | Works (non-blocking) |

---

## Validated Commands (Exact Syntax Tested)

The following commands were tested and validated during discovery on 2026-01-08:

### 1. Spawn Claude Orchestrator (Opens New Window - Blue Tab)

```powershell
# From Claude Code Bash tool:
cmd //c start "" wt.exe -d "F:\GiljoAI_MCP" --title "Agent 1 - Orchestrator" --tabColor "#2196F3" pwsh -NoExit -Command "claude --dangerously-skip-permissions 'Hello I am the Orchestrator agent with a blue tab'"
```

### 2. Spawn Claude Implementer (New Tab - Green)

```powershell
# From Claude Code Bash tool with run_in_background:
cmd //c start "" wt.exe -w 0 new-tab -d "F:\GiljoAI_MCP" --title "Agent 2 - Implementer" --tabColor "#4CAF50" pwsh -NoExit -Command "claude --dangerously-skip-permissions 'Hello I am the Implementer agent with a green tab'"
```

### 3. Spawn Claude Tester (New Tab - Orange)

```powershell
cmd //c start "" wt.exe -w 0 new-tab -d "F:\GiljoAI_MCP" --title "Agent 3 - Tester" --tabColor "#FF9800" pwsh -NoExit -Command "claude --dangerously-skip-permissions 'Hello I am the Tester agent with an orange tab'"
```

### 4. Spawn Codex Agent (New Tab - Purple)

```powershell
cmd //c start "" wt.exe -w 0 new-tab -d "F:\GiljoAI_MCP" --title "Codex Agent" --tabColor "#9C27B0" pwsh -NoExit -Command "codex --dangerously-bypass-approvals-and-sandbox -C 'F:\GiljoAI_MCP' 'Hello I am Codex agent with a purple tab'"
```

### 5. Non-Blocking Spawn from Claude Code

```python
# Use run_in_background=True to prevent orchestrator from blocking:
Bash(
    command='cmd //c start "" wt.exe -w 0 new-tab ...',
    run_in_background=True
)
# Returns immediately with task ID, orchestrator continues working
```

### Key Learnings from Testing

1. **`-p` flag is NOT for prompt** - It means "print and exit". Prompt is positional argument.
2. **Must use `wt.exe`** not `pwsh.exe` directly to get user profile/colors
3. **First spawn omits `-w 0 new-tab`** - Opens new window
4. **Subsequent spawns use `-w 0 new-tab`** - Joins existing window as tab
5. **`run_in_background=True`** essential for orchestrator to continue working

---

## Files Changed

None - this was a discovery/validation handover. Test scripts were created temporarily on desktop and deleted after validation.

---

## Implementation Tasks (TODO)

To fully integrate this capability into GiljoAI:

- [ ] **Update orchestrator template** - Add terminal spawning instructions to orchestrator mission in `src/giljo_mcp/templates/` or database
- [ ] **Add agent colors to database** - Store hex colors per agent type in `AgentTemplate` model
- [ ] **Update `start_to_finish_agent_FLOW.md`** - Document new auto-spawn capability in Step 7B
- [ ] **Add UI toggle** - "Auto-spawn Terminal Tabs" option in Implementation tab (optional)
- [ ] **Platform detection** - Add OS detection for cross-platform terminal commands (future)
- [ ] **Update thin prompt generator** - Include workspace path for `-d` flag

---

## Future Enhancements

1. **Add to orchestrator template**: Include terminal spawning instructions in orchestrator mission
2. **Platform detection**: Auto-detect OS and use appropriate terminal commands
3. **UI integration**: Add "Auto-spawn Terminals" toggle in Implementation tab
4. **Tab grouping**: Use Windows Terminal's tab grouping for related agents

---

## Related Handovers

- 0246a-c: Orchestrator Workflow & Token Optimization
- 0088: Thin Client Architecture
- Reference: `handovers/Reference_docs/Workflow architecture.pdf`
- Reference: `handovers/Reference_docs/start_to_finish_agent_FLOW.md`

---

## Conclusion

This discovery enables **true automated multi-agent orchestration** where a single orchestrator can spawn an entire team of agents in organized, color-coded Windows Terminal tabs. Combined with the MCP message hub, this creates a powerful visual multi-agent development environment.
