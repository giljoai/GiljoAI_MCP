# MCP Installer Script Manual Testing Checklist

## Overview

This document provides comprehensive manual testing procedures for the MCP installer script templates. These tests verify that the generated scripts correctly detect, configure, and integrate GiljoAI MCP server with development tools.

**Template Files:**
- Windows: `installer/templates/giljo-mcp-setup.bat.template`
- Unix/Linux/macOS: `installer/templates/giljo-mcp-setup.sh.template`

**Test Environment Requirements:**
- Access to Windows, macOS, and Linux systems
- At least one MCP-compatible tool installed (Claude Code, Cursor, or Windsurf)
- Python 3.8+ in system PATH
- jq installed (Unix systems only)

---

## Test Categories

### Category 1: Template Variable Substitution

#### Test 1.1: Verify All Placeholders Replaced
**Objective:** Ensure installer correctly replaces all template variables

**Steps:**
1. Generate script from template with test credentials:
   - `{server_url}` → `http://localhost:7272`
   - `{api_key}` → `test_api_key_12345`
   - `{username}` → `test_user`
   - `{organization}` → `Test Organization`
   - `{timestamp}` → Current timestamp
2. Search generated script for any remaining `{...}` placeholders
3. Verify all values are correctly substituted

**Expected Result:**
- No `{...}` placeholders remain in generated script
- All configuration values match provided credentials
- Script header shows correct user, organization, server, timestamp

**Pass Criteria:**
- [ ] No template placeholders remain
- [ ] All values correctly substituted
- [ ] Header information is accurate

---

### Category 2: Tool Detection

#### Test 2.1: Claude Code Detection (Windows)
**Platform:** Windows 10/11

**Steps:**
1. Ensure Claude Code is installed
2. Verify `%APPDATA%\.claude.json` exists
3. Run generated `giljo-mcp-setup.bat`
4. Observe detection output

**Expected Result:**
```
[FOUND] Claude Code: C:\Users\<username>\AppData\Roaming\.claude.json
  Configuring Claude Code...
  [OK]    Claude Code configured successfully
```

**Pass Criteria:**
- [ ] Script detects Claude Code
- [ ] Shows correct config file path
- [ ] Configuration succeeds

#### Test 2.2: Claude Code Detection (macOS/Linux)
**Platform:** macOS or Linux

**Steps:**
1. Ensure Claude Code is installed
2. Verify `~/.claude.json` exists
3. Run generated `giljo-mcp-setup.sh`
4. Observe detection output

**Expected Result:**
```
[FOUND] Claude Code: /home/<username>/.claude.json
  Configuring Claude Code...
  [OK]    Claude Code configured successfully
```

**Pass Criteria:**
- [ ] Script detects Claude Code
- [ ] Shows correct config file path
- [ ] Configuration succeeds

#### Test 2.3: Cursor Detection (Windows)
**Platform:** Windows 10/11

**Steps:**
1. Ensure Cursor is installed
2. Verify `%APPDATA%\Cursor\User\globalStorage` directory exists
3. Run generated `giljo-mcp-setup.bat`
4. Observe detection output

**Expected Result:**
```
[FOUND] Cursor: C:\Users\<username>\AppData\Roaming\Cursor\User\globalStorage\mcp.json
  Configuring Cursor...
  [OK]    Cursor configured successfully
```

**Pass Criteria:**
- [ ] Script detects Cursor
- [ ] Shows correct config file path
- [ ] Configuration succeeds

#### Test 2.4: Cursor Detection (macOS)
**Platform:** macOS

**Steps:**
1. Ensure Cursor is installed
2. Verify `~/Library/Application Support/Cursor/User/globalStorage` exists
3. Run generated `giljo-mcp-setup.sh`
4. Observe detection output

**Expected Result:**
```
[FOUND] Cursor: /Users/<username>/Library/Application Support/Cursor/User/globalStorage/mcp.json
  Configuring Cursor...
  [OK]    Cursor configured successfully
```

**Pass Criteria:**
- [ ] Script detects Cursor
- [ ] Uses correct macOS path
- [ ] Configuration succeeds

#### Test 2.5: Cursor Detection (Linux)
**Platform:** Ubuntu 22.04 or similar

**Steps:**
1. Ensure Cursor is installed
2. Verify `~/.config/Cursor/User/globalStorage` exists
3. Run generated `giljo-mcp-setup.sh`
4. Observe detection output

**Expected Result:**
```
[FOUND] Cursor: /home/<username>/.config/Cursor/User/globalStorage/mcp.json
  Configuring Cursor...
  [OK]    Cursor configured successfully
```

**Pass Criteria:**
- [ ] Script detects Cursor
- [ ] Uses correct Linux path
- [ ] Configuration succeeds

#### Test 2.6: Windsurf Detection (Windows)
**Platform:** Windows 10/11

**Steps:**
1. Ensure Windsurf is installed
2. Verify `%APPDATA%\Windsurf` directory exists
3. Run generated `giljo-mcp-setup.bat`
4. Observe detection output

**Expected Result:**
```
[FOUND] Windsurf: C:\Users\<username>\AppData\Roaming\Windsurf\config.json
  Configuring Windsurf...
  [OK]    Windsurf configured successfully
```

**Pass Criteria:**
- [ ] Script detects Windsurf
- [ ] Shows correct config file path
- [ ] Configuration succeeds

#### Test 2.7: Windsurf Detection (macOS/Linux)
**Platform:** macOS or Linux

**Steps:**
1. Ensure Windsurf is installed
2. Verify Windsurf config directory exists
3. Run generated `giljo-mcp-setup.sh`
4. Observe detection output

**Expected Result:**
```
[FOUND] Windsurf: /path/to/Windsurf/config.json
  Configuring Windsurf...
  [OK]    Windsurf configured successfully
```

**Pass Criteria:**
- [ ] Script detects Windsurf
- [ ] Shows correct config file path
- [ ] Configuration succeeds

#### Test 2.8: No Tools Detected
**Platform:** Any

**Steps:**
1. Run script on system with NO development tools installed
2. Observe output

**Expected Result:**
```
[SKIP]  Claude Code not detected
[SKIP]  Cursor not detected
[SKIP]  Windsurf not detected

[WARNING] No development tools were detected or configured.

Please ensure you have one of the following installed:
  - Claude Code (AI CLI by Anthropic)
  - Cursor (AI Code Editor)
  - Windsurf (Codeium AI IDE)
```

**Pass Criteria:**
- [ ] All tools show [SKIP] status
- [ ] Warning message displayed
- [ ] Installation instructions shown
- [ ] Script exits gracefully

---

### Category 3: Backup Creation

#### Test 3.1: Backup Created Before Modification (Windows)
**Platform:** Windows 10/11

**Steps:**
1. Ensure Claude Code config exists with existing content
2. Note current timestamp
3. Run generated `giljo-mcp-setup.bat`
4. Check for backup file in same directory

**Expected Result:**
- Backup file created: `.claude.json.backup.YYYYMMDD.HHMMSS`
- Backup contains original config content
- Timestamp matches execution time
- Output shows: `Creating backup: <path>`

**Pass Criteria:**
- [ ] Backup file exists
- [ ] Backup has correct naming format
- [ ] Backup contains original config
- [ ] Original config still accessible

#### Test 3.2: Backup Created Before Modification (Unix)
**Platform:** macOS or Linux

**Steps:**
1. Ensure Claude Code config exists with existing content
2. Note current timestamp
3. Run generated `giljo-mcp-setup.sh`
4. Check for backup file in same directory

**Expected Result:**
- Backup file created: `.claude.json.backup.YYYYMMDD_HHMMSS`
- Backup contains original config content
- Timestamp matches execution time
- Output shows: `[INFO]  Backup created: <path>`

**Pass Criteria:**
- [ ] Backup file exists
- [ ] Backup has correct naming format (underscore separator)
- [ ] Backup contains original config
- [ ] Original config still accessible

#### Test 3.3: Multiple Backups Don't Overwrite
**Platform:** Any

**Steps:**
1. Run installer script first time
2. Note backup filename
3. Modify config manually
4. Run installer script again
5. Verify both backups exist

**Expected Result:**
- Two distinct backup files exist
- Each has unique timestamp
- Neither backup was overwritten
- Both contain their respective original configs

**Pass Criteria:**
- [ ] Multiple backup files present
- [ ] Each has unique timestamp
- [ ] No backups were overwritten
- [ ] All backups accessible

---

### Category 4: JSON Configuration Merging

#### Test 4.1: Merge with Existing Config (Windows)
**Platform:** Windows 10/11

**Setup:**
Create existing `.claude.json` with content:
```json
{
  "existingSetting": "value",
  "mcpServers": {
    "other-server": {
      "command": "other-command"
    }
  }
}
```

**Steps:**
1. Run generated `giljo-mcp-setup.bat`
2. Open `.claude.json`
3. Verify content

**Expected Result:**
```json
{
  "existingSetting": "value",
  "mcpServers": {
    "other-server": {
      "command": "other-command"
    },
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_API_KEY": "test_api_key_12345"
      }
    }
  }
}
```

**Pass Criteria:**
- [ ] Original settings preserved
- [ ] Other MCP servers preserved
- [ ] giljo-mcp server added
- [ ] Valid JSON structure

#### Test 4.2: Merge with Existing Config (Unix)
**Platform:** macOS or Linux

**Setup:**
Create existing `~/.claude.json` with content:
```json
{
  "existingSetting": "value",
  "mcpServers": {
    "other-server": {
      "command": "other-command"
    }
  }
}
```

**Steps:**
1. Run generated `giljo-mcp-setup.sh`
2. Open `~/.claude.json`
3. Verify content

**Expected Result:**
```json
{
  "existingSetting": "value",
  "mcpServers": {
    "other-server": {
      "command": "other-command"
    },
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_API_KEY": "test_api_key_12345"
      }
    }
  }
}
```

**Pass Criteria:**
- [ ] Original settings preserved
- [ ] Other MCP servers preserved
- [ ] giljo-mcp server added using jq
- [ ] Valid JSON structure

#### Test 4.3: Create New Config (No Existing File)
**Platform:** Any

**Steps:**
1. Delete existing config file (or test with tool that has no config)
2. Run installer script
3. Verify config file created
4. Verify content

**Expected Result:**
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_API_KEY": "test_api_key_12345"
      }
    }
  }
}
```

**Pass Criteria:**
- [ ] Config file created
- [ ] Proper JSON structure
- [ ] giljo-mcp server configured
- [ ] File is valid and parseable

#### Test 4.4: Update Existing giljo-mcp Config
**Platform:** Any

**Setup:**
Create config with old giljo-mcp server:
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "old-command",
      "args": ["old-args"]
    }
  }
}
```

**Steps:**
1. Run installer script
2. Verify config updated
3. Check old config replaced

**Expected Result:**
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_API_KEY": "test_api_key_12345"
      }
    }
  }
}
```

**Pass Criteria:**
- [ ] Old giljo-mcp config replaced
- [ ] New config has correct structure
- [ ] Server URL and API key updated
- [ ] JSON remains valid

---

### Category 5: Error Handling

#### Test 5.1: Missing jq (Unix Only)
**Platform:** macOS or Linux

**Steps:**
1. Temporarily rename jq binary: `sudo mv /usr/bin/jq /usr/bin/jq.bak`
2. Run generated `giljo-mcp-setup.sh`
3. Observe error handling
4. Restore jq: `sudo mv /usr/bin/jq.bak /usr/bin/jq`

**Expected Result:**
```
[ERROR] jq is not installed. Please install jq to continue.

Installation instructions:
  macOS:  brew install jq
  Ubuntu: sudo apt-get install jq
  CentOS: sudo yum install jq
```

**Pass Criteria:**
- [ ] Script detects missing jq
- [ ] Shows clear error message
- [ ] Provides installation instructions
- [ ] Exits gracefully without modifying configs

#### Test 5.2: Missing Python
**Platform:** Any

**Steps:**
1. Temporarily remove Python from PATH
2. Run installer script (note: may be difficult to test fully)
3. Observe error handling

**Expected Result:**
- Clear error about missing Python
- Instructions to install Python 3.8+
- Script exits without proceeding

**Pass Criteria:**
- [ ] Missing Python detected
- [ ] Clear error message shown
- [ ] Script exits gracefully

#### Test 5.3: Permission Denied (Read-Only Config)
**Platform:** Any

**Steps:**
1. Make config file read-only
   - Windows: `attrib +R .claude.json`
   - Unix: `chmod 444 ~/.claude.json`
2. Run installer script
3. Observe error handling
4. Restore permissions

**Expected Result:**
- Error message indicating permission denied
- Backup preserved (if created before error)
- Original config unchanged
- Script continues with other tools

**Pass Criteria:**
- [ ] Permission error caught
- [ ] Error message displayed
- [ ] Original config unchanged
- [ ] Script doesn't crash

#### Test 5.4: Corrupted JSON Config
**Platform:** Any

**Setup:**
Create invalid JSON in config file:
```
{
  "mcpServers": {
    "other-server": "missing closing brace"

```

**Steps:**
1. Run installer script
2. Observe error handling
3. Check backup was created

**Expected Result:**
- Error message indicating invalid JSON
- Backup created before merge attempt
- Script shows error but continues with other tools
- User can restore from backup

**Pass Criteria:**
- [ ] Invalid JSON detected
- [ ] Backup created
- [ ] Error message shown
- [ ] Script continues gracefully

---

### Category 6: User Experience

#### Test 6.1: Clear Status Messages (Windows)
**Platform:** Windows 10/11

**Steps:**
1. Run `giljo-mcp-setup.bat` with all three tools installed
2. Observe output formatting and clarity

**Expected Output Format:**
```
============================================================
  GiljoAI MCP - Tool Integration Installer
============================================================

This script will detect your development tools and configure
them to use GiljoAI Agent Orchestration MCP Server.

Server: http://localhost:7272
User: test_user
Organization: Test Organization

<pause for user>

============================================================
  Scanning for Development Tools...
============================================================

[FOUND] Claude Code: C:\Users\...\AppData\Roaming\.claude.json
  Configuring Claude Code...
  [INFO]  Backup created: ...
  [OK]    Claude Code configured successfully

[FOUND] Cursor: C:\Users\...\AppData\Roaming\Cursor\...
  Configuring Cursor...
  [INFO]  Backup created: ...
  [OK]    Cursor configured successfully

[FOUND] Windsurf: C:\Users\...\AppData\Roaming\Windsurf\...
  Configuring Windsurf...
  [INFO]  Backup created: ...
  [OK]    Windsurf configured successfully

============================================================
  Configuration Complete!
============================================================

[OK] Claude Code configured successfully
[OK] Cursor configured successfully
[OK] Windsurf configured successfully

Successfully configured 3 tool(s).

Server: http://localhost:7272
User: test_user

============================================================
  IMPORTANT: Please restart your development tools
  for the changes to take effect.
============================================================

Press any key to continue...
```

**Pass Criteria:**
- [ ] Headers clearly formatted
- [ ] Status indicators visible ([FOUND], [OK], [ERROR], [SKIP])
- [ ] Indentation shows hierarchy
- [ ] Summary shows all configured tools
- [ ] Restart instructions prominent
- [ ] User pauses to read output

#### Test 6.2: Color Output (Unix)
**Platform:** macOS or Linux

**Steps:**
1. Run `giljo-mcp-setup.sh` in terminal
2. Verify color coding

**Expected Result:**
- [FOUND] - Blue color
- [OK] - Green color
- [ERROR] - Red color
- [SKIP] - Yellow color
- [INFO] - Blue color

**Pass Criteria:**
- [ ] Colors display correctly
- [ ] Status easy to distinguish
- [ ] Terminal properly supports color codes
- [ ] Colors enhance readability

#### Test 6.3: Cross-Platform Path Display
**Platform:** All

**Steps:**
1. Run installer on Windows, macOS, and Linux
2. Verify path separators correct for each platform

**Expected Result:**
- Windows: `C:\Users\...\AppData\Roaming\.claude.json`
- macOS: `/Users/.../Library/Application Support/...`
- Linux: `/home/.../.config/...`

**Pass Criteria:**
- [ ] Windows uses backslashes
- [ ] macOS uses forward slashes
- [ ] Linux uses forward slashes
- [ ] Paths are platform-appropriate

---

### Category 7: Integration Verification

#### Test 7.1: Verify MCP Server in Claude Code
**Platform:** Any

**Prerequisites:**
- Claude Code installed and configured by script

**Steps:**
1. Launch Claude Code CLI
2. List available MCP servers
3. Verify giljo-mcp appears

**Expected Result:**
```bash
$ claude mcp list
Available MCP servers:
  - giljo-mcp (configured)
```

**Pass Criteria:**
- [ ] giljo-mcp server listed
- [ ] Server shows as configured
- [ ] No error messages

#### Test 7.2: Test MCP Server Connection
**Platform:** Any

**Prerequisites:**
- GiljoAI API server running on configured URL
- Tool configured by installer script

**Steps:**
1. Start GiljoAI API server
2. Launch configured tool (Claude Code, Cursor, or Windsurf)
3. Attempt to use giljo-mcp tools
4. Verify connection successful

**Expected Result:**
- Tool connects to MCP server
- MCP tools are available
- No authentication errors
- Server URL and API key work correctly

**Pass Criteria:**
- [ ] MCP server connection established
- [ ] Tools respond correctly
- [ ] Authentication succeeds
- [ ] No connection errors

#### Test 7.3: Multiple Tool Configuration
**Platform:** Any

**Prerequisites:**
- Multiple tools installed (e.g., Claude Code + Cursor)

**Steps:**
1. Run installer script
2. Verify both tools configured
3. Test each tool independently
4. Verify no conflicts

**Expected Result:**
- Both tools show giljo-mcp configured
- Each tool can connect independently
- No configuration conflicts
- API key works for both

**Pass Criteria:**
- [ ] All tools configured successfully
- [ ] Each tool connects independently
- [ ] No configuration conflicts
- [ ] Shared credentials work

---

## Test Execution Summary

### Test Environment

**Windows Testing:**
- Windows Version: ___________
- PowerShell Version: ___________
- Tools Installed: ___________
- Test Date: ___________

**macOS Testing:**
- macOS Version: ___________
- Bash Version: ___________
- jq Version: ___________
- Tools Installed: ___________
- Test Date: ___________

**Linux Testing:**
- Distribution: ___________
- Kernel Version: ___________
- Bash Version: ___________
- jq Version: ___________
- Tools Installed: ___________
- Test Date: ___________

### Overall Results

| Test Category | Total Tests | Passed | Failed | Skipped | Notes |
|---------------|-------------|--------|--------|---------|-------|
| Template Variables | | | | | |
| Tool Detection | | | | | |
| Backup Creation | | | | | |
| JSON Merging | | | | | |
| Error Handling | | | | | |
| User Experience | | | | | |
| Integration | | | | | |

### Critical Issues Found

List any critical issues that prevent script from functioning:

1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

### Recommendations

List improvements or fixes needed:

1. ___________________________________________
2. ___________________________________________
3. ___________________________________________

---

## Notes for Testers

### General Guidelines

1. **Safety First**: Always test on non-production systems first
2. **Backup Configs**: Manually backup configs before testing error scenarios
3. **Clean State**: Start each test with a known configuration state
4. **Document Issues**: Capture screenshots of errors or unexpected behavior
5. **Cross-Platform**: Test on all supported platforms when possible

### Known Limitations

- jq must be pre-installed on Unix systems (installer checks for this)
- Python must be in system PATH
- Script requires write permissions to config directories
- Some tools may require restart to load new MCP server config

### Troubleshooting

**If script fails to detect tool:**
- Verify tool is installed correctly
- Check config directory exists
- Confirm using standard installation paths

**If JSON merge fails:**
- Check existing config is valid JSON
- Verify PowerShell execution policy (Windows)
- Ensure jq is installed and functional (Unix)

**If backup creation fails:**
- Check disk space available
- Verify write permissions
- Check file system supports long filenames

---

## Approval

**Tested By:** ___________________________________________

**Date:** ___________________________________________

**Approval Status:** [ ] Approved [ ] Approved with Notes [ ] Rejected

**Notes:** ___________________________________________
