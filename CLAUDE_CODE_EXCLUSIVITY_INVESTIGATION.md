# Claude Code Exclusivity Investigation Report

## Executive Summary

The GiljoAI MCP codebase currently has **extensive multi-tool support** for Claude Code, Codex CLI (OpenAI), and Gemini CLI (Google). The system is NOT exclusive to Claude Code - it has a fully implemented universal MCP registration system that actively detects and configures multiple AI coding tools during installation. References to Cursor and Windsurf exist primarily in documentation and comments, but Codex and Gemini have full implementation.

**Key Finding:** The system needs significant refactoring to make it Claude Code exclusive, as multi-tool support is deeply integrated into the installation flow and includes dedicated adapter classes for each tool.

## Current State Analysis

### Tools Currently Supported in Code
- **Claude Code:** ✅ Fully supported with native MCP integration
- **Codex CLI:** ✅ Fully supported with TOML configuration adapter
- **Gemini CLI:** ✅ Fully supported with JSON configuration adapter
- **Cursor:** ⚠️ Referenced in docs/comments only, no active integration
- **Windsurf:** ⚠️ Referenced in docs/comments only, no active integration
- **Codeium:** ⚠️ Referenced in docs/comments only, no active integration

## Detailed Findings

### Finding 1: Universal MCP Installer Module
- **Location:** `installer/universal_mcp_installer.py:17-29`
- **Class:** `UniversalMCPInstaller`
- **Description:** Core orchestration class that manages multi-tool registration
- **Current Implementation:**
```python
def __init__(self):
    """Initialize with adapters for each supported AI CLI tool."""
    self.adapters = {
        "claude": ClaudeAdapter(),
        "codex": CodexAdapter(),
        "gemini": GeminiAdapter(),
    }

    self.tool_names = {
        "claude": "Claude Code",
        "codex": "Codex CLI (OpenAI)",
        "gemini": "Gemini CLI (Google)",
    }
```
- **Recommendation:** Comment out Codex and Gemini adapters, keep only Claude

### Finding 2: Tool Detection in Bootstrap
- **Location:** `bootstrap.py:219-262`
- **Function:** `show_platform_integration()`
- **Description:** Shows instructions for multi-tool integration after installation
- **Line 238:**
```python
print(f"   Configure integration with Claude Code, Codex, or Gemini")
```
- **Recommendation:** Change to "Configure integration with Claude Code"

### Finding 3: GUI Installer MCP Integration
- **Location:** `setup_gui.py:24-27`
- **Description:** Imports UniversalMCPInstaller for automatic tool registration
```python
try:
    from installer.universal_mcp_installer import UniversalMCPInstaller
    MCP_SUPPORT_AVAILABLE = True
except ImportError:
    MCP_SUPPORT_AVAILABLE = False
```
- **Recommendation:** Keep import but ensure UniversalMCPInstaller only registers Claude

### Finding 4: Individual Tool Adapters
- **Files:**
  - `installer/claude_adapter.py` - Claude Code adapter (KEEP)
  - `installer/codex_adapter.py` - Codex CLI adapter (COMMENT OUT)
  - `installer/gemini_adapter.py` - Gemini CLI adapter (COMMENT OUT)
- **Recommendation:** Comment out entire Codex and Gemini adapter files with clear markers

### Finding 5: Registration Scripts
- **Files:**
  - `register_ai_tools.py` - Universal wizard supporting all tools
  - `register_claude.py` - Claude-specific registration (KEEP)
  - `register_codex.py` - Codex-specific registration (COMMENT OUT)
  - `register_gemini.py` - Gemini-specific registration (COMMENT OUT)
- **Recommendation:** Modify register_ai_tools.py to only support Claude

### Finding 6: Integration Script
- **Location:** `integrate_mcp.py:79-83`
- **Description:** Defines tool display names for UI
```python
tool_display_names = {
    'claude': 'Claude Code',
    'codex': 'Codex CLI (OpenAI)',
    'gemini': 'Gemini CLI (Google)'
}
```
- **Recommendation:** Remove codex and gemini entries

### Finding 7: Documentation References
Multiple documentation files reference multi-tool support:
- `docs/AI_TOOL_INTEGRATION.md` - Full multi-tool documentation
- `docs/MCP_REGISTRATION_RESEARCH.md` - Research on all tools
- `README.md:60` - References to "Other Tools (Cursor, Windsurf, Gemini, Codeium)"
- `TECHDEBT.md:23,27,45` - References to multi-tool challenges

## Files Requiring Modification

### 1. **installer/universal_mcp_installer.py**
- **Lines 19-23:** Comment out Codex and Gemini adapters
- **Lines 25-29:** Remove Codex and Gemini from tool_names dict
- **Action:** Add feature flag for future re-enablement

### 2. **bootstrap.py**
- **Line 238:** Change "Claude Code, Codex, or Gemini" to "Claude Code"
- **Action:** Update text to reflect Claude-only support

### 3. **setup_gui.py**
- **No changes needed** - Keep MCP support but it will only detect Claude

### 4. **integrate_mcp.py**
- **Lines 79-83:** Remove codex and gemini from tool_display_names
- **Action:** Keep only claude entry

### 5. **register_ai_tools.py**
- **Lines 310-315:** Remove references to Codex and Gemini installation URLs
- **Action:** Update to only show Claude Code installation

### 6. **Adapter Files (Comment Entirely)**
- `installer/codex_adapter.py` - Add header comment: "# DISABLED: Reserved for future multi-tool support"
- `installer/gemini_adapter.py` - Add header comment: "# DISABLED: Reserved for future multi-tool support"

### 7. **Registration Scripts (Comment Entirely)**
- `register_codex.py` - Add header comment: "# DISABLED: Reserved for future multi-tool support"
- `register_gemini.py` - Add header comment: "# DISABLED: Reserved for future multi-tool support"

## Recommended Implementation Strategy

### Phase 1: Core Changes
1. Modify `installer/universal_mcp_installer.py` to only initialize Claude adapter
2. Add feature flag `ENABLE_MULTI_TOOL_SUPPORT = False` at module level
3. Wrap Codex/Gemini code in conditional blocks checking this flag

### Phase 2: Script Updates
1. Comment out entire Codex and Gemini adapter/registration files
2. Add clear TECHDEBT markers referencing this investigation
3. Update register_ai_tools.py to only detect/register Claude

### Phase 3: Documentation Updates
1. Update README.md to clarify Claude Code exclusivity
2. Add note to TECHDEBT.md about commented multi-tool support
3. Update CLAUDE.md to reflect current state

### Phase 4: Testing
1. Verify installer only detects Claude Code
2. Confirm registration works with Claude Code only
3. Test that commented code doesn't affect functionality

## Code Examples

### Before (universal_mcp_installer.py):
```python
def __init__(self):
    """Initialize with adapters for each supported AI CLI tool."""
    self.adapters = {
        "claude": ClaudeAdapter(),
        "codex": CodexAdapter(),
        "gemini": GeminiAdapter(),
    }
```

### After (universal_mcp_installer.py):
```python
# Feature flag for future multi-tool support
ENABLE_MULTI_TOOL_SUPPORT = False  # Set to True to re-enable Codex/Gemini

def __init__(self):
    """Initialize with adapters for each supported AI CLI tool."""
    self.adapters = {
        "claude": ClaudeAdapter(),
    }

    if ENABLE_MULTI_TOOL_SUPPORT:
        # TECHDEBT: Multi-tool support disabled for Claude Code exclusivity
        # Uncomment below to re-enable support for other tools
        # self.adapters["codex"] = CodexAdapter()
        # self.adapters["gemini"] = GeminiAdapter()
        pass
```

## Technical Debt Notes

### For TECHDEBT.md:
```markdown
## Multi-Tool Support (Disabled)

**Date:** 2025-09-30
**Reason:** GiljoAI MCP is designed for Claude Code's native subagent capabilities

The codebase includes full support for Codex CLI and Gemini CLI, but this has been
disabled to maintain Claude Code exclusivity. The infrastructure remains in place
for future re-enablement.

**Disabled Components:**
- installer/codex_adapter.py
- installer/gemini_adapter.py
- register_codex.py
- register_gemini.py

**To Re-enable:**
1. Set ENABLE_MULTI_TOOL_SUPPORT = True in installer/universal_mcp_installer.py
2. Uncomment adapter initializations
3. Uncomment registration scripts
4. Update documentation

**Investigation Report:** See CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md
```

## Summary

The GiljoAI MCP system currently has deep, production-ready integration for multiple AI coding tools beyond Claude Code. The multi-tool support is not superficial - it includes:

1. **Full adapter implementations** for Codex and Gemini
2. **Automatic detection** during installation
3. **Configuration file management** (JSON/TOML)
4. **Registration wizards** for each tool
5. **Verification mechanisms** for successful integration

To make the system Claude Code exclusive, we need to systematically disable (not remove) the multi-tool components while preserving the ability to re-enable them in the future. This approach maintains the codebase's architectural integrity while ensuring users understand that GiljoAI MCP is optimized for Claude Code's unique subagent orchestration capabilities.

## Next Steps

1. **Immediate:** Comment out non-Claude tool support with clear markers
2. **Short-term:** Update all documentation to reflect Claude Code exclusivity
3. **Long-term:** Consider creating a separate branch for multi-tool experimentation
4. **Future:** When other tools develop subagent capabilities, re-enable support

---

**Investigation completed:** 2025-09-30
**Investigator:** Master Orchestrator
**Method:** Serena MCP symbolic code analysis