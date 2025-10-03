# Master Orchestrator Prompt: Universal MCP Registration Integration

**Mission**: Integrate the universal MCP registration system into both GUI and CLI installation paths for GiljoAI MCP.

**Context**: A production-ready universal MCP registration system has been implemented and tested. It supports Claude CLI, Codex CLI (OpenAI), and Gemini CLI (Google) with automatic detection, multi-format support (JSON/TOML), and cross-platform compatibility. **The system is complete but NOT integrated into the installation flows.**

**Complexity**: High - Requires coordination of multiple agents (production-implementer, testing-validation-specialist, documentation-architect)

**Prerequisites**: Read the following files for full context:
1. `sessions/session_universal_mcp_registration_complete.md` - Complete session overview
2. `devlog/2025-09-30_universal_mcp_integration_complete.md` - Technical details
3. `docs/MCP_REGISTRATION_RESEARCH.md` - Research findings
4. `installer/universal_mcp_installer.py` - Implementation to integrate

---

## Mission Objectives

### Primary Objective
Integrate the `UniversalMCPInstaller` into both GUI (`setup_gui.py`) and CLI (`setup.py`) installation paths so that MCP registration happens automatically during installation.

### Success Criteria
1. ✅ MCP registration step added to GUI installer after dependency installation
2. ✅ MCP registration step added to CLI installer after dependency installation
3. ✅ Progress bar updates during MCP registration (GUI)
4. ✅ Console output shows MCP registration progress (CLI)
5. ✅ Installation does NOT fail if MCP registration fails (warn only)
6. ✅ Post-installation summary shows which MCP tools were configured
7. ✅ All tests pass (GUI and CLI installation flows)
8. ✅ Documentation updated (README, INSTALLATION.md)

---

## Current State Analysis

### ✅ What Exists (Production-Ready)
- `installer/mcp_adapter_base.py` - Abstract base adapter
- `installer/claude_adapter.py` - Claude CLI adapter (JSON)
- `installer/codex_adapter.py` - Codex CLI adapter (TOML)
- `installer/gemini_adapter.py` - Gemini CLI adapter (JSON)
- `installer/universal_mcp_installer.py` - Orchestrator class
- `register_ai_tools.py` - Standalone interactive wizard (working reference)
- Test scripts proving functionality
- Comprehensive documentation

### ❌ What's Missing (Integration Points)
- GUI installer (`setup_gui.py`) does NOT call MCP registration
- CLI installer (`setup.py`) does NOT call MCP registration
- No progress tracking for MCP registration step
- No UI elements for MCP status
- No error handling in installation context
- No post-install summary of MCP configuration
- User-facing docs not updated

---

## Integration Architecture

### Where to Integrate

**GUI Installer** (`setup_gui.py`):
- **Location**: After `install_dependencies()` step, before final completion
- **Current Flow**:
  1. Welcome
  2. Choose Mode (Localhost/Server)
  3. Database Configuration
  4. Dependency Installation ← **INSERT MCP REGISTRATION HERE**
  5. Installation Complete
- **New Step**: "Configuring AI Tool Integrations (MCP)"

**CLI Installer** (`setup.py`):
- **Location**: After dependency installation in `run_setup()` method
- **Current Flow**:
  1. System checks
  2. Database setup
  3. Dependency installation ← **INSERT MCP REGISTRATION HERE**
  4. Final configuration
  5. Summary
- **New Step**: Console output for MCP detection and registration

### API to Use

```python
from installer.universal_mcp_installer import UniversalMCPInstaller

# Initialize
installer = UniversalMCPInstaller()

# Detect installed CLI tools
tools = installer.detect_installed_tools()
# Returns: List['claude', 'codex', 'gemini'] or empty list

# Register with all detected tools
results = installer.register_all(
    server_name="giljo-mcp",
    command="python",
    args=["-m", "giljo_mcp"],
    env={
        "GILJO_SERVER_URL": "http://localhost:8000"  # or server URL
    }
)
# Returns: Dict[str, bool] e.g., {'claude': True, 'codex': False, ...}

# Verify registration
verified = installer.verify_all("giljo-mcp")
# Returns: Dict[str, bool]
```

---

## Task Breakdown for Agents

### Task 1: GUI Integration (production-implementer)

**File**: `setup_gui.py`

**Requirements**:
1. Import `UniversalMCPInstaller` at top of file
2. Create new method: `setup_mcp_integration()`
3. Add MCP registration step after dependency installation
4. Create UI elements:
   - Progress bar for MCP registration
   - Status text showing detection results
   - Success/warning indicators for each tool
5. Error handling:
   - Catch all exceptions from MCP registration
   - Log errors but DO NOT fail installation
   - Show warnings in UI if registration fails
6. Update main progress bar to include MCP step
7. Update completion screen to show MCP configuration status

**UI Design** (follow existing patterns):
```
Progress: [===============] 85%
Configuring AI Tool Integrations (MCP)...

Detected AI CLI Tools:
  [+] Claude Code - Configuring...
  [+] Codex CLI (OpenAI) - Configuring...
  [-] Gemini CLI - Not installed

MCP Registration:
  [OK] Claude Code - Successfully configured
  [OK] Codex CLI - Successfully configured
```

**Code Location**:
- Add method around line ~1800 (near other setup methods)
- Call from main setup flow after `install_dependencies()`
- Update progress calculations to include MCP step

**Error Handling Example**:
```python
try:
    installer = UniversalMCPInstaller()
    tools = installer.detect_installed_tools()

    if not tools:
        self.log_message("No AI CLI tools detected - skipping MCP registration")
        return

    self.log_message(f"Detected: {', '.join(tools)}")
    results = installer.register_all(...)

    for tool, success in results.items():
        if success:
            self.log_message(f"[OK] {tool} configured", "success")
        else:
            self.log_message(f"[WARN] {tool} configuration failed", "warning")
except Exception as e:
    self.log_message(f"MCP registration skipped: {e}", "warning")
    # Don't fail installation
```

---

### Task 2: CLI Integration (production-implementer)

**File**: `setup.py`

**Requirements**:
1. Import `UniversalMCPInstaller` at top of file
2. Create new method: `setup_mcp_integration()`
3. Add MCP registration step after dependency installation in `run_setup()`
4. Console output:
   - Detection results (which tools found)
   - Registration progress (per tool)
   - Success/failure status
5. Error handling:
   - Catch exceptions
   - Log to install log
   - Warn user but continue
6. Update installation summary to include MCP status

**Console Output Design** (follow existing patterns):
```
[INFO] Configuring AI Tool Integrations (MCP)...
[INFO] Scanning for installed AI CLI tools...
[INFO] Detected: Claude Code, Codex CLI (OpenAI)
[INFO]
[INFO] Registering GiljoAI MCP server...
[INFO]   Claude Code: Registering...
[SUCCESS] Claude Code: Successfully configured
[INFO]   Codex CLI: Registering...
[SUCCESS] Codex CLI: Successfully configured
[INFO]
[SUCCESS] MCP integration complete (2/2 tools configured)
```

**Code Location**:
- Add method around line ~400 (near other setup methods)
- Call from `run_setup()` after dependency installation
- Add to installation summary at end

**Error Handling Example**:
```python
def setup_mcp_integration(self, config):
    """Configure MCP integration with AI CLI tools"""
    try:
        self.log("Configuring AI Tool Integrations (MCP)...", "INFO")

        installer = UniversalMCPInstaller()
        tools = installer.detect_installed_tools()

        if not tools:
            self.log("No AI CLI tools detected - skipping MCP", "WARNING")
            return {"configured": 0, "total": 0}

        self.log(f"Detected: {', '.join(tools)}", "INFO")
        results = installer.register_all(...)

        success_count = sum(1 for v in results.values() if v)
        return {"configured": success_count, "total": len(results)}

    except Exception as e:
        self.log(f"MCP registration failed: {e}", "WARNING")
        return {"configured": 0, "total": 0}
```

---

### Task 3: Testing & Validation (testing-validation-specialist)

**Objective**: Validate integration works correctly in both installation paths

**Test Cases**:

1. **GUI Installation - No AI Tools Installed**
   - Expected: Detects none, shows "No AI tools detected", continues
   - Result: Installation completes successfully

2. **GUI Installation - Claude Only**
   - Expected: Detects Claude, registers successfully
   - Result: Shows "Claude Code configured", installation completes

3. **GUI Installation - All Tools Installed**
   - Expected: Detects all 3, registers all 3
   - Result: Shows all 3 configured, installation completes

4. **GUI Installation - Registration Fails**
   - Simulate: Corrupt config file permissions
   - Expected: Shows warning, installation continues
   - Result: Installation completes with warning

5. **CLI Installation - Same scenarios as GUI**

6. **End-to-End**
   - Fresh Windows install
   - Install Claude, Codex, Gemini first
   - Run GiljoAI installer (GUI and CLI separately)
   - Verify config files created correctly
   - Verify server name is "giljo-mcp"
   - Verify env vars include correct server URL

**Verification Steps**:
1. Check config files created:
   - `~/.claude.json` contains "giljo-mcp"
   - `~/.codex/config.toml` contains "giljo-mcp"
   - `~/.gemini/settings.json` contains "giljo-mcp"
2. Check server URL matches chosen mode:
   - Localhost mode: `http://localhost:8000`
   - Server mode: `http://<server-ip>:8000`
3. Check installation doesn't fail if MCP fails
4. Check progress bar reaches 100%
5. Check post-install summary shows MCP status

**Test Environment**:
- Use `giltest.bat` to create clean test installation
- Test both GUI and CLI modes
- Test with/without AI CLI tools installed
- Test on Windows (primary), Mac/Linux if available

---

### Task 4: Documentation Update (documentation-architect)

**Objective**: Update user-facing documentation to describe MCP integration

**Files to Update**:

1. **README.md**
   - Add "AI Tool Integration" section
   - Describe automatic MCP registration
   - List supported AI CLI tools

2. **INSTALLATION.md**
   - Add MCP registration step description
   - Add troubleshooting section for MCP issues
   - Add verification steps post-install

3. **docs/AI_TOOL_INTEGRATION.md** (if exists)
   - Update with new automatic registration
   - Remove old manual registration instructions
   - Add examples of config files

4. **CHANGELOG.md** (or similar)
   - Add entry for universal MCP registration feature

**Content Guidelines**:
- Professional tone, no emojis
- Clear step-by-step instructions
- Include screenshots (if applicable)
- Add troubleshooting section
- Explain what MCP is and why it's useful

**Example Content**:

```markdown
## AI Tool Integration (MCP)

GiljoAI MCP automatically registers itself with your installed AI coding assistants
during installation. This enables you to use GiljoAI's orchestration features
directly from your AI CLI tools.

### Supported AI CLI Tools

- **Claude Code** (Anthropic) - Automatically detected and configured
- **Codex CLI** (OpenAI) - Automatically detected and configured
- **Gemini CLI** (Google) - Automatically detected and configured

### How It Works

During installation, GiljoAI MCP:
1. Scans for installed AI CLI tools
2. Registers itself as an MCP server with each detected tool
3. Configures connection to your GiljoAI server

No manual configuration required!

### Verification

After installation, verify MCP registration:

**Claude Code**:
```bash
claude mcp list
# Should show "giljo-mcp" in the list
```

**Codex CLI**:
```bash
cat ~/.codex/config.toml
# Should contain [mcp_servers.giljo-mcp] section
```

**Gemini CLI**:
```bash
gemini mcp list
# Should show "giljo-mcp" in the list
```

### Troubleshooting

**MCP registration failed during installation**
- This is non-critical; installation continues
- You can register manually using: `python register_ai_tools.py`
- Check AI CLI tool is installed: `claude --version`, `codex --version`, `gemini --version`

**Config file not found**
- Ensure AI CLI tool is installed globally
- Check config file locations:
  - Claude: `~/.claude.json`
  - Codex: `~/.codex/config.toml`
  - Gemini: `~/.gemini/settings.json`
```

---

## Implementation Order

1. **Phase 1**: production-implementer - GUI Integration
   - Implement `setup_gui.py` changes
   - Test manually with GUI installer
   - Commit changes

2. **Phase 2**: production-implementer - CLI Integration
   - Implement `setup.py` changes
   - Test manually with CLI installer
   - Commit changes

3. **Phase 3**: testing-validation-specialist - Comprehensive Testing
   - Run all test cases (GUI and CLI)
   - Test edge cases and error conditions
   - Verify config files
   - Create test report

4. **Phase 4**: documentation-architect - Documentation
   - Update all user-facing docs
   - Create troubleshooting guide
   - Verify session/devlog entries exist (already done ✅)
   - Update project architecture docs if needed

5. **Phase 5**: Final validation and commit
   - Code review (lint, format, type hints)
   - Final end-to-end test
   - Git commit with detailed message
   - Update CHANGELOG

---

## Critical Requirements

### Must Have
1. ✅ Integration does NOT break existing installation flow
2. ✅ Installation DOES NOT fail if MCP registration fails
3. ✅ User sees clear status of MCP registration (which tools configured)
4. ✅ Progress bar includes MCP step and reaches 100%
5. ✅ Config files created with correct server URL (based on chosen mode)
6. ✅ Works on Windows (primary platform)

### Should Have
1. ✅ Works on macOS and Linux (cross-platform design validated)
2. ✅ Error messages are helpful and actionable
3. ✅ Post-install summary shows MCP configuration status
4. ✅ Documentation is clear and complete

### Nice to Have
1. ⏳ Retry logic if initial registration fails
2. ⏳ Detailed logging of MCP registration process
3. ⏳ Option to skip MCP registration (silent mode)

---

## Technical Constraints

1. **No Breaking Changes**: Existing installation flow must continue to work
2. **Error Tolerance**: MCP registration failure must not fail installation
3. **Cross-Platform**: Must work on Windows, macOS, Linux
4. **No New Dependencies**: Use existing `toml` dependency (already added)
5. **Follow Patterns**: Match existing code style in `setup_gui.py` and `setup.py`
6. **Professional Code**: No emojis, proper type hints, comprehensive docstrings

---

## Configuration Details

### Server URL Selection
- **Localhost Mode**: `http://localhost:8000`
- **Server Mode**: `http://<server-ip>:8000` (from user config)

**Implementation**:
```python
# In GUI: self.mode is 'localhost' or 'server'
if self.mode == 'localhost':
    server_url = "http://localhost:8000"
else:
    server_url = f"http://{self.db_host}:8000"  # or dedicated API config

# In CLI: Read from config
server_url = config.get('api_url', 'http://localhost:8000')
```

### MCP Server Name
**Fixed**: `"giljo-mcp"` (consistent across all installations)

### Environment Variables
```python
env = {
    "GILJO_SERVER_URL": server_url,
    # Optional: Add more as needed
    # "GILJO_MODE": self.mode,
    # "GILJO_TENANT_KEY": self.tenant_key,
}
```

---

## Error Handling Strategy

### Graceful Degradation
```python
try:
    # MCP registration
    installer = UniversalMCPInstaller()
    tools = installer.detect_installed_tools()

    if tools:
        results = installer.register_all(...)
        # Log results
    else:
        # Log "no tools detected"

except ImportError as e:
    # Missing toml library or other import issue
    self.log("MCP registration unavailable: missing dependency", "WARNING")

except PermissionError as e:
    # Can't write to config files
    self.log("MCP registration failed: permission denied", "WARNING")

except Exception as e:
    # Unknown error
    self.log(f"MCP registration failed: {e}", "WARNING")

# ALWAYS continue installation
```

### User Communication
- **Success**: "AI tool integration configured (X/Y tools)"
- **Partial**: "AI tool integration partially configured (X/Y tools)"
- **None Detected**: "No AI CLI tools detected - MCP registration skipped"
- **Failed**: "AI tool integration skipped (error occurred)"

---

## Success Metrics

### Code Quality
- [ ] Linting clean (ruff)
- [ ] Formatting applied (black)
- [ ] Type hints added
- [ ] Docstrings comprehensive
- [ ] No security issues

### Functionality
- [ ] GUI integration works
- [ ] CLI integration works
- [ ] Progress bar updates correctly
- [ ] Error handling works (installation continues)
- [ ] Config files created correctly
- [ ] Post-install summary includes MCP status

### Testing
- [ ] All test cases pass
- [ ] Edge cases handled
- [ ] Error conditions tested
- [ ] Cross-platform design validated

### Documentation
- [ ] User-facing docs updated
- [ ] Troubleshooting guide created
- [ ] Session/devlog entries complete (✅ already done)
- [ ] Code comments clear

---

## Reference Implementation

See `register_ai_tools.py` (lines 1-389) for working example of:
- Using `UniversalMCPInstaller`
- Detection logic
- Registration flow
- Verification
- Error handling
- User-friendly output

**Do NOT copy verbatim** - adapt for GUI/CLI context with progress tracking and non-interactive flow.

---

## Final Deliverables

1. **Code Changes**:
   - `setup_gui.py` - MCP integration added
   - `setup.py` - MCP integration added
   - All changes tested and working

2. **Testing**:
   - Test report showing all scenarios
   - Config files from test runs
   - Screenshots (if applicable)

3. **Documentation**:
   - README.md updated
   - INSTALLATION.md updated
   - Troubleshooting guide added
   - CHANGELOG updated

4. **Git Commit**:
   - Clear commit message
   - References issue/ticket (if applicable)
   - Includes all modified files

---

## Questions for User (If Needed)

1. Should MCP registration be optional/skippable in silent mode?
2. What should happen if user has multiple GiljoAI servers running?
3. Should we support project-specific MCP config (in addition to user-wide)?
4. Should we add MCP server health checks post-registration?

---

## Agent Coordination

**Master Orchestrator**: You coordinate these agents:

1. **production-implementer** (Tasks 1 & 2)
   - Implement GUI integration
   - Implement CLI integration
   - Follow existing code patterns
   - Maintain code quality

2. **testing-validation-specialist** (Task 3)
   - Comprehensive testing
   - Edge case validation
   - Config file verification
   - Create test report

3. **documentation-architect** (Task 4)
   - Update user docs
   - Create troubleshooting guide
   - Ensure consistency
   - Professional tone

**Communication**: Each agent should report completion status and any blockers. Master orchestrator ensures sequential execution where needed (testing after implementation).

---

## Timeline Estimate

- **Phase 1** (GUI Integration): 2-3 hours
- **Phase 2** (CLI Integration): 1-2 hours
- **Phase 3** (Testing): 2-3 hours
- **Phase 4** (Documentation): 1-2 hours
- **Phase 5** (Final validation): 1 hour

**Total**: 7-11 hours of agent work

---

**Master Orchestrator**: You have full autonomy to:
- Coordinate agent execution order
- Adjust plans based on findings
- Request additional context if needed
- Make implementation decisions within project constraints
- Report progress and blockers

**End State**: Universal MCP registration fully integrated into both GUI and CLI installation paths, comprehensively tested, and documented.

---

**BEGIN INTEGRATION MISSION**
