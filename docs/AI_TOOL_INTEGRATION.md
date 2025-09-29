# AI Tool Integration Guide

## Overview

GiljoAI MCP is a standalone orchestration server that provides Model Context Protocol (MCP) integration for multiple AI coding agents. This guide explains how to connect your AI coding tool to the GiljoAI MCP server.

### What is MCP?

Model Context Protocol (MCP) is an open protocol that standardizes how applications provide context to Large Language Models. Think of it as "USB-C for AI applications" - a universal way to connect AI tools to data sources and capabilities.

### Prerequisites

Before integrating with AI tools, ensure:
1. ✅ GiljoAI MCP server is installed
2. ✅ You know your installation directory (where you ran the installer)
3. ✅ The server can start successfully (test with `start_giljo.bat` or `start_giljo.sh`)

## Supported AI Coding Agents

| Tool | MCP Support | Auto-Config | Manual Config | Notes |
|------|-------------|-------------|---------------|-------|
| **Claude Code** | ✅ Full | ✅ Yes | ✅ Yes | Native MCP with CLI commands |
| **Codex CLI** | ✅ Full | ✅ Yes | ✅ Yes | TOML configuration file |
| **Gemini CLI** | ✅ Full | ✅ Yes | ✅ Yes | JSON configuration file |
| **Grok CLI** | ✅ Partial | ⚠️ Varies | ✅ Yes | Multiple implementations |

---

## Quick Start

### Option A: Universal Wizard (Recommended)

Run the universal configuration wizard from your installation directory:

```bash
# Windows
cd %INSTALL_DIR%
python register_ai_tools.py

# Mac/Linux
cd $INSTALL_DIR
python register_ai_tools.py
```

The wizard will:
- Detect which AI CLIs are installed
- Show you configuration options
- Automatically configure selected tools
- Verify the integration worked

### Option B: Individual Tool Scripts

Configure specific tools using dedicated scripts:

```bash
# Claude Code
register_claude.bat                    # Windows
./register_claude.sh                   # Mac/Linux

# Codex CLI
python register_codex.py

# Gemini CLI
python register_gemini.py

# Grok CLI
python register_grok.py
```

---

## Claude Code Integration

### Check if Claude Code is Installed

```bash
claude --version
```

If installed, you'll see version information. If not, download from: https://claude.ai/download

### Automatic Registration

**Windows:**
```cmd
cd %INSTALL_DIR%
register_claude.bat
```

**Mac/Linux:**
```bash
cd $INSTALL_DIR
./register_claude.sh
```

### Manual Registration

If automatic registration fails, run this command manually:

```bash
claude mcp add giljo-mcp "%INSTALL_DIR%\venv\Scripts\python.exe -m giljo_mcp.mcp_adapter" --scope user
```

Replace `%INSTALL_DIR%` with your actual installation path, for example:
- Windows: `C:\MyServers\GiljoAI_MCP`
- Mac: `/Users/username/giljo-mcp`
- Linux: `/home/username/giljo-mcp`

### Verification

```bash
# List registered MCP servers
claude mcp list

# You should see "giljo-mcp" in the list

# Test connection (inside Claude Code)
/mcp
```

### Scope Options

Claude Code supports three registration scopes:

- `--scope user` (Global): Available across all projects ✅ **Recommended**
- `--scope project`: Shared via `.mcp.json` in project root
- `--scope local`: Only for current user in current project

### Troubleshooting

**Problem:** "claude: command not found"
- **Solution:** Install Claude Code from https://claude.ai/download

**Problem:** "Registration failed"
- **Solution:** Check that Python venv exists at `%INSTALL_DIR%\venv`
- **Solution:** Verify `giljo_mcp.mcp_adapter` module exists

**Problem:** Tools don't appear in Claude
- **Solution:** Restart Claude Code completely
- **Solution:** Ensure GiljoAI server is running (`start_giljo.bat`)

---

## Codex CLI Integration

### Check if Codex is Installed

```bash
codex --version
```

If not installed, see: https://github.com/openai/codex

### Automatic Configuration

```bash
cd %INSTALL_DIR%
python register_codex.py
```

The script will:
1. Locate your Codex config file (`~/.codex/config.toml`)
2. Add the `giljo-mcp` server configuration
3. Show you the changes made
4. Provide rollback option if needed

### Manual Configuration

Edit `~/.codex/config.toml` and add:

```toml
[mcp_servers.giljo-mcp]
command = "%INSTALL_DIR%/venv/bin/python"
args = ["-m", "giljo_mcp.mcp_adapter"]

[mcp_servers.giljo-mcp.env]
GILJO_MCP_HOME = "%INSTALL_DIR%"
```

**Replace `%INSTALL_DIR%` with your actual path:**

**Windows example:**
```toml
[mcp_servers.giljo-mcp]
command = "C:/MyServers/GiljoAI_MCP/venv/Scripts/python.exe"
args = ["-m", "giljo_mcp.mcp_adapter"]

[mcp_servers.giljo-mcp.env]
GILJO_MCP_HOME = "C:/MyServers/GiljoAI_MCP"
```

**Mac/Linux example:**
```toml
[mcp_servers.giljo-mcp]
command = "/home/username/giljo-mcp/venv/bin/python"
args = ["-m", "giljo_mcp.mcp_adapter"]

[mcp_servers.giljo-mcp.env]
GILJO_MCP_HOME = "/home/username/giljo-mcp"
```

### Verification

```bash
# Inside Codex, check MCP servers
/mcp status

# Test a GiljoAI tool
codex "List available MCP tools"
```

### Configuration File Location

- **Windows:** `%USERPROFILE%\.codex\config.toml`
- **Mac/Linux:** `~/.codex/config.toml`

### Troubleshooting

**Problem:** Config file doesn't exist
- **Solution:** Run `codex` once to create default config
- **Solution:** Create `~/.codex/config.toml` manually

**Problem:** Python path not found
- **Solution:** Verify venv exists: `%INSTALL_DIR%\venv\Scripts\python.exe` (Windows) or `$INSTALL_DIR/venv/bin/python` (Mac/Linux)

---

## Gemini CLI Integration

### Check if Gemini CLI is Installed

```bash
gemini --version
```

If not installed, see: https://github.com/google-gemini/gemini-cli

### Automatic Configuration

```bash
cd %INSTALL_DIR%
python register_gemini.py
```

The script will:
1. Locate your Gemini settings file (`~/.gemini/settings.json`)
2. Add the `giljo-mcp` server to the `mcpServers` section
3. Preserve existing MCP servers
4. Show the updated configuration

### Manual Configuration

Edit `~/.gemini/settings.json` and add to the `mcpServers` object:

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "%INSTALL_DIR%/venv/bin/python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_MCP_HOME": "%INSTALL_DIR%"
      }
    }
  }
}
```

**Replace `%INSTALL_DIR%` with your actual path:**

**Windows example:**
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "C:/MyServers/GiljoAI_MCP/venv/Scripts/python.exe",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_MCP_HOME": "C:/MyServers/GiljoAI_MCP"
      }
    }
  }
}
```

**Mac/Linux example:**
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "/home/username/giljo-mcp/venv/bin/python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_MCP_HOME": "/home/username/giljo-mcp"
      }
    }
  }
}
```

### Verification

```bash
# Inside Gemini CLI, check MCP servers
/mcp

# You should see giljo-mcp with "connected" status
```

### Configuration File Location

- **Windows:** `%USERPROFILE%\.gemini\settings.json`
- **Mac/Linux:** `~/.gemini/settings.json`

### Troubleshooting

**Problem:** Settings file doesn't exist
- **Solution:** Run `gemini` once to create default settings
- **Solution:** Create `~/.gemini/settings.json` with `{"mcpServers": {}}`

**Problem:** Invalid JSON after editing
- **Solution:** Use the `register_gemini.py` script (handles JSON safely)
- **Solution:** Validate JSON at https://jsonlint.com/

**Problem:** MCP shows "failed" status
- **Solution:** Check that GiljoAI server is running
- **Solution:** Verify Python path is correct
- **Solution:** Check logs: `gemini mcp logs giljo-mcp`

---

## Grok CLI Integration

### About Grok CLI Variants

There are several community implementations of Grok CLI with MCP support:

1. **superagent-ai/grok-cli** - Full MCP support
2. **@webdevtoday/grok-cli** - npm package with `/mcp add` commands
3. **coldcanuk/grok-cli** - High-performance with MCP integration
4. **Bob-lance/grok-mcp** - MCP server for xAI Grok API

### Check if Grok CLI is Installed

```bash
grok --version
```

Or for npm version:
```bash
npx @webdevtoday/grok-cli --version
```

### Using the Helper Script

```bash
cd %INSTALL_DIR%
python register_grok.py
```

The script will:
- Detect which Grok CLI variant you have
- Generate the correct registration command
- Provide copy-pasteable commands with your actual paths
- Show manual configuration steps

### Configuration Methods

#### Method 1: In-App Command (webdevtoday variant)

```bash
grok
# Then inside Grok CLI:
/mcp add giljo-mcp "%INSTALL_DIR%/venv/bin/python -m giljo_mcp.mcp_adapter"
```

#### Method 2: Configuration File

Location varies by implementation. Common locations:
- `~/.grok/config.json`
- `~/.grok-cli/settings.json`

Example configuration:
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "%INSTALL_DIR%/venv/bin/python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_MCP_HOME": "%INSTALL_DIR%"
      }
    }
  }
}
```

### Verification

```bash
# Inside Grok CLI
/mcp list
/mcp status
/mcp tools
```

### Troubleshooting

**Problem:** Multiple Grok implementations installed
- **Solution:** Use `which grok` (Mac/Linux) or `where grok` (Windows) to identify which one
- **Solution:** Configure each separately if you use multiple

**Problem:** Configuration location unknown
- **Solution:** Check Grok CLI documentation for your specific variant
- **Solution:** Run `register_grok.py` for auto-detection

---

## General Troubleshooting

### Server Connection Issues

**Problem:** AI tool can't connect to GiljoAI server

**Solutions:**
1. Ensure server is running:
   ```bash
   cd %INSTALL_DIR%
   start_giljo.bat     # Windows
   ./start_giljo.sh    # Mac/Linux
   ```

2. Check server status:
   ```bash
   curl http://localhost:8000/health
   ```

3. Check server logs:
   ```bash
   cd %INSTALL_DIR%
   cat logs/giljo_mcp.log
   ```

### Path Issues

**Problem:** "Python not found" or "Module not found"

**Solutions:**
1. Verify venv exists:
   ```bash
   # Windows
   dir %INSTALL_DIR%\venv\Scripts\python.exe

   # Mac/Linux
   ls $INSTALL_DIR/venv/bin/python
   ```

2. Use absolute paths (no `~` or `%USERPROFILE%`)

3. On Windows, use forward slashes `/` in JSON/TOML files

### Authentication Issues

**Problem:** "API key required" or "Unauthorized"

**Solutions:**
1. Check if server is in network mode (requires API key)
2. Add API key to AI tool configuration:
   ```json
   "env": {
     "GILJO_API_KEY": "your-api-key-here"
   }
   ```
3. Or switch to local mode (no authentication needed)

### Tools Not Appearing

**Problem:** MCP registered but tools don't show in AI agent

**Solutions:**
1. Restart the AI tool completely (close all windows)
2. Wait 30 seconds after server starts
3. Check MCP connection status (`/mcp` command)
4. Verify server logs for errors

---

## Advanced Configuration

### Multiple Profiles

You can create multiple GiljoAI MCP server instances for different purposes:

1. Development server: `~/giljo-mcp-dev`
2. Production server: `~/giljo-mcp-prod`
3. Testing server: `~/giljo-mcp-test`

Register each with a different name:
```bash
claude mcp add giljo-dev "<dev-path>/venv/Scripts/python.exe -m giljo_mcp.mcp_adapter" --scope user
claude mcp add giljo-prod "<prod-path>/venv/Scripts/python.exe -m giljo_mcp.mcp_adapter" --scope user
```

### Network Mode Setup

For team access or remote servers:

1. Configure server for network mode during installation
2. Note the server URL and API key
3. Update AI tool configuration with network endpoint:

```json
{
  "mcpServers": {
    "giljo-mcp-remote": {
      "type": "http",
      "url": "http://server-ip:8000",
      "headers": {
        "Authorization": "Bearer YOUR_API_KEY"
      }
    }
  }
}
```

### Environment Variables

All registration methods support environment variables:

- `GILJO_MCP_HOME` - Installation directory path
- `GILJO_API_KEY` - API key (if network mode)
- `GILJO_LOG_LEVEL` - Logging level (DEBUG, INFO, WARNING, ERROR)
- `GILJO_PORT` - Override default port

---

## Verification Checklist

After configuration, verify your setup:

- [ ] Server starts without errors: `start_giljo.bat`
- [ ] Health check responds: `curl http://localhost:8000/health`
- [ ] AI tool lists giljo-mcp: `claude mcp list` or `/mcp`
- [ ] MCP shows "connected" status: `/mcp` command in AI tool
- [ ] Can list GiljoAI tools: Ask AI tool "What MCP tools are available?"
- [ ] Tools actually work: Try using a GiljoAI orchestration tool

---

## Unregistration

To remove GiljoAI MCP from an AI tool:

### Claude Code
```bash
claude mcp remove giljo-mcp
```

### Codex CLI
Edit `~/.codex/config.toml` and delete the `[mcp_servers.giljo-mcp]` section

### Gemini CLI
Edit `~/.gemini/settings.json` and remove `"giljo-mcp"` from `mcpServers` object

### Grok CLI
```bash
# Inside Grok
/mcp remove giljo-mcp
```

Or edit configuration file and remove the giljo-mcp entry.

---

## FAQ

### Q: Do I need to register with every AI tool I use?
**A:** Yes, each AI tool needs its own registration. But you only do it once per tool.

### Q: Can I use multiple AI tools with the same GiljoAI server?
**A:** Yes! Register each tool, and they'll all connect to the same server instance.

### Q: What if I move the installation directory?
**A:** You'll need to re-register with updated paths. Or use the uninstaller and reinstall in the new location.

### Q: Do I need to restart my AI tool after registration?
**A:** Yes, always restart completely (close all windows) after MCP registration.

### Q: Can I register per-project instead of globally?
**A:** Yes, Claude Code supports `--scope project` and `--scope local`. Other tools typically use global config files.

### Q: What if my AI tool isn't listed here?
**A:** Check if it supports MCP at https://modelcontextprotocol.io/. If so, use similar config to Gemini/Codex examples.

### Q: Is the server always required to be running?
**A:** Yes, your AI tool connects to the running server. Start it with `start_giljo.bat` before using AI tools.

### Q: Can I use GiljoAI MCP over a network/remotely?
**A:** Yes, install in "Server Deployment" mode and provide the network URL and API key to your AI tools.

---

## Getting Help

If you encounter issues:

1. **Check server logs:** `%INSTALL_DIR%/logs/giljo_mcp.log`
2. **Test server manually:** `curl http://localhost:8000/health`
3. **Verify paths:** Ensure all paths are absolute and correct
4. **Consult AI tool docs:** Each AI tool may have specific MCP requirements
5. **GitHub Issues:** https://github.com/your-repo/issues

---

## Quick Reference

### File Locations

| Item | Windows | Mac/Linux |
|------|---------|-----------|
| Installation Dir | `C:\path\to\GiljoAI_MCP` | `/path/to/giljo-mcp` |
| Python (venv) | `%INSTALL_DIR%\venv\Scripts\python.exe` | `$INSTALL_DIR/venv/bin/python` |
| Claude Config | Auto-managed | Auto-managed |
| Codex Config | `%USERPROFILE%\.codex\config.toml` | `~/.codex/config.toml` |
| Gemini Config | `%USERPROFILE%\.gemini\settings.json` | `~/.gemini/settings.json` |
| Grok Config | Varies by implementation | Varies by implementation |

### Registration Commands Summary

```bash
# Universal wizard
python register_ai_tools.py

# Individual tools
register_claude.bat                     # Windows only
python register_codex.py                # All platforms
python register_gemini.py               # All platforms
python register_grok.py                 # All platforms (helper)
```

### Verification Commands

```bash
# Claude Code
claude mcp list

# Inside any AI tool
/mcp
/mcp status
/mcp tools

# Test server
curl http://localhost:8000/health
```

---

**Last Updated:** 2025-09-29
**GiljoAI MCP Version:** 2.0+
**Document Version:** 1.0