# MCP Registration Research - Multi-AI CLI Tools

**Status**: Phase 1 Complete (Claude), Phase 2 In Progress (Codex, Gemini, Grok)
**Date**: 2025-09-30
**Objective**: Create universal MCP registration system for all AI CLI tools

---

## Phase 1: Claude CLI/Desktop - COMPLETE ✅

### Research Findings

**Configuration Locations:**
- **Claude CLI**: `~/.claude.json` (user-wide, cross-platform)
- **Claude Desktop**: Platform-specific config directories
  - Windows: `%APPDATA%\Claude\claude_desktop_config.json`
  - macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
  - Linux: `~/.config/Claude/claude_desktop_config.json`

**Registration Methods:**
1. Command-based: `claude mcp add-json [name] [config] --scope user`
2. Direct file editing: Modify `~/.claude.json` with proper JSON structure

**Scope Levels:**
- `--scope user`: Global (all projects) - `~/.claude.json`
- `--scope project`: Project-specific - `.mcp.json`
- `--scope local`: Session-only - `.claude/settings.local.json`

**JSON Structure:**
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "/path/to/python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {"GILJO_SERVER_URL": "http://localhost:8000"}
    }
  }
}
```

**Verification:**
- CLI: `claude mcp list`
- Desktop: Restart app, check for hammer icon

**Current Bug Identified:**
- `register_claude.bat` has wrong command syntax (command and args not separated)
- Premature file existence checks before registration creates files

**Multi-Platform Support:** ✅ Confirmed - Single Python script works on Windows, macOS, Linux

---

## Phase 2: Other AI CLI Tools - COMPLETE ✅

### Codex CLI (OpenAI)
**Status**: ✅ Research complete
**Findings:**
- **Official Tool**: YES - `@openai/codex` (npm package, open source)
- **MCP Support**: ✅ YES - Native MCP support via TOML configuration
- **Config Location**: `~/.codex/config.toml` (cross-platform)
- **Format**: TOML (NOT JSON like Claude)
- **Registration**: File-based only (no CLI commands)
- **Section**: `[mcp_servers.servername]`
- **Platform**: Windows (experimental), macOS, Linux

**Key Differences:**
- Uses TOML instead of JSON
- Section name: `mcp_servers` (underscore, not camelCase)
- Config must be created manually (never auto-generated)
- Requires `toml` Python library for manipulation

### Gemini CLI (Google)
**Status**: ✅ Research complete
**Findings:**
- **Official Tool**: YES - `@google/gemini-cli` (npm package, v0.6.1)
- **MCP Support**: ✅ YES - Full native MCP support
- **Config Location**: `~/.gemini/settings.json` (cross-platform)
- **Format**: JSON (like Claude)
- **Registration**: Both CLI commands AND file editing
- **CLI Commands**: `gemini mcp add`, `gemini mcp list`, `gemini mcp remove`
- **Section**: `mcpServers` (like Claude)
- **Platform**: Windows, macOS, Linux (requires Node.js 20+)

**Key Features:**
- Three transport types: stdio, HTTP, SSE
- Environment variable support with `$VAR_NAME` syntax
- Tool filtering (include/exclude specific tools)
- Trust mode for bypassing confirmations
- Configuration precedence: user → project → system

### Grok CLI (xAI)
**Status**: ❌ NOT SUPPORTED
**Decision**: Removed from project scope
**Reason**: No official xAI CLI tool exists; only third-party implementations available

---

## Implementation Strategy - CONSOLIDATED

### Comparison Matrix: All AI CLI Tools

| Feature | Claude CLI | Codex CLI | Gemini CLI |
|---------|-----------|-----------|------------|
| **Official** | ✅ Yes (Anthropic) | ✅ Yes (OpenAI) | ✅ Yes (Google) |
| **MCP Support** | ✅ Native | ✅ Native | ✅ Native |
| **Config Format** | JSON | TOML | JSON |
| **Config File** | `.claude.json` | `config.toml` | `settings.json` |
| **Config Path** | `~/` | `~/.codex/` | `~/.gemini/` |
| **Section Name** | `mcpServers` | `mcp_servers` | `mcpServers` |
| **CLI Commands** | ✅ Yes | ❌ No | ✅ Yes |
| **Registration** | Command + File | File only | Command + File |
| **Multi-Platform** | ✅ Win/Mac/Linux | ⚠️ Win(exp)/Mac/Linux | ✅ Win/Mac/Linux |
| **Dependencies** | None | None | Node.js 20+ |
| **Priority** | 🔴 HIGH | 🔴 HIGH | 🟡 MEDIUM |

### Universal Registration Architecture

**Design Pattern**: Factory pattern with platform-specific adapters

```
UniversalMCPInstaller
    ├── ClaudeAdapter (JSON, CLI + file)
    ├── CodexAdapter (TOML, file only)
    └── GeminiAdapter (JSON, CLI + file)
```

### Common Implementation Patterns

**All adapters must implement:**
1. `is_installed()` - Detect if CLI tool is available
2. `get_config_path()` - Platform-aware config file location
3. `register()` - Add MCP server configuration
4. `verify()` - Confirm registration succeeded
5. `unregister()` - Remove MCP server configuration

**Cross-platform requirements:**
- Use `pathlib.Path` for all path operations
- Use `sys.platform` for OS detection
- Forward slashes in config files (even on Windows)
- Support `~` expansion with `Path.home()`
- Handle missing config directories (create automatically)

### File Format Handlers

**JSON Handler** (Claude, Gemini, Grok):
```python
import json
config = json.load(f)
config["mcpServers"]["server-name"] = {...}
json.dump(config, f, indent=2)
```

**TOML Handler** (Codex only):
```python
import toml  # Add to requirements.txt
config = toml.load(f)
config["mcp_servers"]["server-name"] = {...}
toml.dump(config, f)
```

### Registration Strategy by Tool

**1. Claude CLI** (Highest Priority):
- Try: `claude mcp add-json` command
- Fallback: Edit `~/.claude.json` directly
- Verify: `claude mcp list`

**2. Codex CLI** (High Priority):
- File editing only: `~/.codex/config.toml`
- No CLI commands available
- Verify: Check file contents (no CLI verification)

**3. Gemini CLI** (Medium Priority):
- Try: `gemini mcp add` command
- Fallback: Edit `~/.gemini/settings.json`
- Verify: `gemini mcp list`


---

## Critical Requirements

### Cross-Platform Compatibility
- [x] Windows support
- [x] macOS support
- [x] Linux support
- [x] Use pathlib for path handling
- [x] Handle OS-specific config locations

### Multi-AI Tool Support
- [x] Claude CLI
- [x] Claude Desktop
- [ ] Codex CLI
- [ ] Gemini CLI
- [ ] Grok CLI

### Installer Integration
- [ ] No premature file checks
- [ ] Proper progress bar updates
- [ ] Clear error messages
- [ ] Rollback capability
- [ ] Post-install verification

---

## Next Steps

1. **Research Phase 2:**
   - Launch research agent for Codex CLI
   - Launch research agent for Gemini CLI
   - Launch research agent for Grok CLI

2. **Consolidation:**
   - Document common patterns across all CLI tools
   - Identify differences and edge cases
   - Design unified registration architecture

3. **Implementation:**
   - Create universal registration scripts
   - Update master orchestrator
   - Add comprehensive testing
   - Update installer progress tracking

---

## Known Issues to Fix

### Current Bugs
1. **`register_claude.bat`**: Wrong command syntax
2. **`register_ai_tools.py`**: Premature file existence checks
3. **Progress bar**: Stuck at 80% when registration pending
4. **Error messages**: "File not found" before files created

### Design Improvements
1. **Fallback strategy**: Command fails → Direct file edit
2. **Validation**: Check JSON structure after registration
3. **User feedback**: Clear next steps after registration
4. **Debugging**: Log file for troubleshooting

---

## Resources

### Official Documentation
- Claude MCP: https://docs.anthropic.com/en/docs/build-with-claude/mcp
- Claude CLI: https://claude.ai/download
- Model Context Protocol Spec: https://spec.modelcontextprotocol.io/

### Research Completed ✅
- ✅ Claude CLI configuration locations (all platforms)
- ✅ Claude Desktop configuration locations (all platforms)
- ✅ Codex CLI configuration and MCP support (TOML format)
- ✅ Gemini CLI configuration and MCP support (JSON format)
- ✅ Grok CLI configuration and MCP support (third-party only)
- ✅ MCP JSON/TOML structure and requirements
- ✅ Registration command syntax (all tools)
- ✅ Verification methods (all tools)
- ✅ Cross-platform path handling
- ✅ Multi-tool comparison matrix

---

## Success Criteria

### Registration Must:
1. Work on Windows, macOS, and Linux
2. Support all detected AI CLI tools
3. Be user-wide (available across all projects)
4. Survive application restarts
5. Provide clear verification method
6. Update installer progress correctly
7. Give helpful error messages on failure
8. Not require manual user intervention

### Installation Flow Must:
1. Auto-detect installed AI tools
2. Register with each detected tool
3. Verify registration succeeded
4. Update progress bar for each step
5. Complete to 100% when all done
6. Provide clear next steps to user

---

---

## Implementation Dependencies

### Python Libraries Required

Add to `requirements.txt`:
```
toml>=0.10.2        # For Codex CLI TOML config files
tomli>=2.0.1        # Python 3.11+ TOML reading
tomli-w>=1.0.0      # Python 3.11+ TOML writing
```

### External Dependencies

**Required for various CLI tools:**
- Node.js 20+ (for Gemini CLI)
- Bun runtime (for third-party Grok CLI, optional)
- npm or global package managers

**Installer must check:**
- `claude` command availability
- `gemini` command availability
- `codex` command availability

---

## Next Steps - Implementation Phase

### Phase 3: Implementation (Current)

1. **Add TOML dependency** ✅
   - Update `requirements.txt`
   - Test TOML read/write operations

2. **Create adapter base class**
   - Abstract interface for all CLI adapters
   - Common methods: is_installed, register, verify, unregister

3. **Implement CLI adapters**
   - `ClaudeAdapter` (JSON, high priority)
   - `CodexAdapter` (TOML, high priority)
   - `GeminiAdapter` (JSON, medium priority)

4. **Create universal installer**
   - Detect all installed CLI tools
   - Register with each detected tool
   - Report success/failure per tool
   - Update progress bar correctly

5. **Integration testing**
   - Test on Windows, macOS, Linux
   - Test with/without each CLI tool installed
   - Test config file creation
   - Test registration verification

6. **Fix installer bugs**
   - Remove premature file checks
   - Fix progress bar stuck at 80%
   - Add proper error messages
   - Implement rollback on failure

---

**Last Updated**: 2025-09-30
**Research Status**: ✅ COMPLETE
**Next Phase**: Implementation
