# DevLog Entry: Fixed reset.py MCP Server Removal

**Date:** 2025-10-03
**Type:** Bug Fix
**Component:** Reset Script
**Priority:** Medium
**Status:** Complete

---

## Issue

The `reset.py` script failed to remove the `giljo-mcp` MCP server from Claude Code's configuration. Users would still see the server listed after running reset, requiring manual removal.

## Investigation

**Problem 1: Wrong Configuration File**
- Script targeted: `%APPDATA%/Claude/claude_desktop_config.json` (Claude Desktop app)
- Should target: `~/.claude.json` (Claude Code CLI)
- These are completely different applications with separate configs

**Problem 2: Incorrect Server Name**
- Script looked for: `giljo_mcp` (underscore)
- Actual name: `giljo-mcp` (hyphen)
- Installer uses hyphenated names for MCP servers

**Problem 3: Manual File Editing**
- Script edited JSON directly instead of using official CLI
- More error-prone and doesn't validate removal

## Solution

Rewrote `remove_giljo_from_claude_config()` function with:

1. **Primary Method**: Use Claude CLI command
   ```python
   subprocess.run(["claude", "mcp", "remove", "giljo-mcp"])
   ```

2. **Fallback Method**: Manual config editing via `_remove_via_file()` helper
   - Corrected path: `Path.home() / ".claude.json"`
   - Checks both name variants: `giljo-mcp` and `giljo_mcp`
   - Preserves other MCP servers (serena, etc.)

3. **Better Error Handling**
   - Graceful fallback if CLI command not found
   - Clear status messages for each step
   - Timeout protection (30s)

## Code Changes

**File Modified:** `reset.py`

**Function:** `remove_giljo_from_claude_config()`
- Changed from manual file editing to CLI command
- Corrected config file path from APPDATA to HOME
- Fixed server name from underscore to hyphen
- Added comprehensive error handling

**New Helper:** `_remove_via_file()`
- Fallback mechanism for manual removal
- Supports both naming conventions
- JSON-safe operations with error recovery

## Testing

**Test 1: CLI Command Method**
```bash
python reset.py
# Output: [OK] Removed giljo-mcp from Claude Code CLI
#         [OK] Preserved other MCP servers (e.g., serena)
```

**Test 2: Verification**
```bash
claude mcp list
# Before: giljo-mcp ✗ Failed + serena ✓ Connected
# After:  serena ✓ Connected (giljo-mcp removed)
```

**Test 3: Config File Check**
```bash
cat ~/.claude.json | grep "mcpServers"
# Confirmed: Only contains serena, no giljo-mcp
```

## Impact

- **Users:** Reset script now properly cleans up MCP configuration
- **Testing:** Simpler test environment resets without manual cleanup
- **Installer:** Prevents leftover configuration from old installs

## Related Files

- `reset.py` - Main script
- `installer/claude_adapter.py` - MCP registration logic
- `~/.claude.json` - Claude Code configuration

## Lessons Learned

1. Always verify config file locations for different Claude products
2. MCP server names use hyphens, not underscores
3. Prefer official CLI commands over manual config editing
4. Always include fallback mechanisms for robustness

## Technical Debt Addressed

- ✅ Corrected understanding of Claude Code vs Claude Desktop
- ✅ Proper MCP server name handling
- ✅ Modern CLI-based configuration management

## Future Considerations

- Consider adding `claude mcp list` output to verify removal
- Add validation step to confirm server no longer registered
- Document MCP naming conventions in installer architecture docs

---

**Complexity:** Low
**Time Spent:** ~30 minutes
**Files Changed:** 1
**Lines Changed:** ~70
**Tests Added:** Manual verification (3 test cases)
