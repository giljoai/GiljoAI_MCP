# Session Memory: Reset Script Claude MCP Server Removal Fix

**Date:** 2025-10-03
**Agent:** Claude Code
**Project:** GiljoAI MCP
**Task:** Fix reset.py script to properly remove giljo-mcp server from Claude Code configuration

---

## Problem

The `reset.py` script was not successfully removing the `giljo-mcp` MCP server from Claude Code's configuration. After running reset.py, the server would still appear in fresh Claude instances when running `claude mcp list`.

## Root Cause Analysis

Investigation revealed multiple issues:

1. **Wrong config file location**: Script was targeting `%APPDATA%/Claude/claude_desktop_config.json` (Claude Desktop app) instead of `~/.claude.json` (Claude Code CLI)

2. **Wrong server name**: The server was registered as `giljo-mcp` (with hyphen) not `giljo_mcp` (with underscore)

3. **Suboptimal approach**: Using manual file editing instead of the official Claude CLI command

## Solution Implemented

### Updated `reset.py` Script

Modified the `remove_giljo_from_claude_config()` function to:

1. **Use Claude CLI command** as primary method:
   ```bash
   claude mcp remove giljo-mcp
   ```

2. **Correct server name**: Changed from `giljo_mcp` to `giljo-mcp`

3. **Fallback mechanism**: Added `_remove_via_file()` helper function for manual config editing if CLI command fails

4. **Dual-name support**: Fallback checks for both `giljo-mcp` and `giljo_mcp` variants

### Key Code Changes

**Before:**
```python
# Wrong config path
claude_config_path = appdata / "Claude" / "claude_desktop_config.json"

# Wrong server name
if "giljo_mcp" in config["mcpServers"]:
    del config["mcpServers"]["giljo_mcp"]
```

**After:**
```python
# Use CLI command (preferred method)
subprocess.run(["claude", "mcp", "remove", "giljo-mcp"])

# Fallback to file editing with correct path
claude_config_path = Path.home() / ".claude.json"

# Check both name variants
for server_name in ["giljo-mcp", "giljo_mcp"]:
    if server_name in config["mcpServers"]:
        del config["mcpServers"][server_name]
```

## Verification

Tested the fix:
```bash
# Before fix
claude mcp list
# Output: giljo-mcp: ... ✗ Failed to connect
#         serena: ... ✓ Connected

# Run reset.py with fix
python reset.py

# After fix
claude mcp list
# Output: serena: ... ✓ Connected
# (giljo-mcp successfully removed)
```

Verified in config file:
```bash
cat ~/.claude.json | grep -A 10 "mcpServers"
# Shows only "serena", no "giljo-mcp"
```

## Important Learnings

1. **Claude Code vs Claude Desktop**: These are different products with different config files:
   - Claude Code CLI: `~/.claude.json`
   - Claude Desktop App: `%APPDATA%/Claude/claude_desktop_config.json`

2. **Server naming**: MCP servers registered via installer use hyphenated names (`giljo-mcp`), not underscored (`giljo_mcp`)

3. **CLI commands preferred**: Using official CLI commands (`claude mcp remove`) is more reliable than manual JSON editing

4. **UI caching**: Fresh Claude instances may cache the MCP server list - closing all instances and restarting resolves this

## Files Modified

- `C:\install_test\Giljo_MCP\reset.py` - Updated `remove_giljo_from_claude_config()` function and added `_remove_via_file()` helper

## Related Components

- `installer/claude_adapter.py` - How giljo-mcp gets registered during installation
- `~/.claude.json` - Claude Code CLI configuration file
- Claude CLI `mcp` commands - Official MCP server management

## Next Steps

This fix will be included in the next dev repo sync via `push_to_dev.py`.

---

**Status:** ✅ Complete
**Verified:** Yes - giljo-mcp successfully removed while preserving serena
