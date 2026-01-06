# MCP Tool Integration Guide

**Last Updated:** 2025-01-05 (Harmonized)  
**Version:** 3.0  
**Audience:** Developers integrating AI development tools
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../../handovers/Simple_Vision.md)** - User journey with MCP integration setup
- **[MCP_OVER_HTTP_INTEGRATION.md](../MCP_OVER_HTTP_INTEGRATION.md)** - Technical MCP-over-HTTP details

**Supported AI Tools** (native MCP support):
- **Claude Code** - via `claude-code mcp add` command
- **Codex CLI** - via `codex mcp add` command
- **Gemini CLI** - via `gemini mcp add` command

**Agent Template Export** (Handover 0102):
- 15-minute token TTL for secure downloads
- See Simple_Vision.md for complete export workflow

---

## Overview

The GiljoAI MCP Integration system makes it easy to connect your AI-powered development tools (Claude Code, Cursor, Windsurf) to the GiljoAI Agent Orchestration platform. This integration enables your AI assistants to access powerful multi-agent orchestration capabilities directly from your IDE.

### What You'll Get

- **Agent Orchestration:** Spawn and manage specialized AI agents for complex tasks
- **Project Management:** Create and track multi-agent development projects
- **Task Coordination:** Break down complex work into coordinated agent tasks
- **Context Management:** Share context efficiently across multiple agents
- **Real-time Monitoring:** Track agent activity and progress via dashboard

### How It Works

The installer script:
1. Auto-detects installed MCP-compatible tools
2. Creates timestamped backups of existing configurations
3. Safely merges GiljoAI MCP server settings
4. Preserves all your existing tool configurations
5. Provides detailed feedback during installation

---

## Prerequisites

Before you begin, ensure you have:

- **Python 3.11+** installed and available in your PATH
- **One or more** of these AI development tools:
  - **Claude Code** - AI CLI by Anthropic
  - **Cursor** - AI Code Editor
  - **Windsurf** - Codeium AI IDE
- **GiljoAI MCP server** running (localhost or network)
- **Network access** to the GiljoAI server

### Checking Python Installation

```bash
# Windows
python --version

# macOS/Linux
python3 --version
```

You should see Python 3.11 or higher. If not, download from [python.org](https://python.org).

### Additional macOS/Linux Requirement

The Unix installer requires `jq` for JSON configuration handling:

```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq
```

---

## Quick Start

### Option 1: Localhost Developer (Auto-Login)

If you're running GiljoAI MCP locally on your development machine:

1. **Access the dashboard** at `http://localhost:7274`
2. **Navigate to Settings** → **MCP Integration**
3. **Download the installer script:**
   - **Windows:** Click "Download for Windows" → saves `giljo-mcp-setup.bat`
   - **macOS/Linux:** Click "Download for macOS/Linux" → saves `giljo-mcp-setup.sh`
4. **Run the script:**

   **Windows:**
   ```cmd
   # Double-click giljo-mcp-setup.bat
   # OR run from command prompt:
   .\giljo-mcp-setup.bat
   ```

   **macOS/Linux:**
   ```bash
   # Make executable
   chmod +x giljo-mcp-setup.sh
   
   # Run installer
   ./giljo-mcp-setup.sh
   ```

5. **Restart your development tools** (Claude Code, Cursor, or Windsurf)
6. **Verify installation** by checking for GiljoAI MCP tools in your IDE

### Option 2: Team Member (Via Share Link)

If your team administrator sent you a download link:

1. **Click the download link** in the email
   - Choose your operating system (Windows or Unix)
2. **Save the installer script** to your Downloads folder
3. **Run the script:**

   **Windows:**
   ```cmd
   cd Downloads
   .\giljo-mcp-setup.bat
   ```

   **macOS/Linux:**
   ```bash
   cd ~/Downloads
   chmod +x giljo-mcp-setup.sh
   ./giljo-mcp-setup.sh
   ```

4. **Follow the on-screen prompts**
5. **Restart your development tools**

---

## What the Script Does

### Detection Phase

The installer automatically scans for MCP-compatible tools:

```
============================================================
  Scanning for Development Tools...
============================================================

[FOUND] Claude Code: C:\Users\YourName\.claude.json
[FOUND] Cursor: C:\Users\YourName\AppData\Roaming\Cursor\User\globalStorage\mcp.json
[SKIP]  Windsurf not detected
```

### Backup Phase

Before making any changes, the script creates timestamped backups:

```
  Creating backup: .claude.json.backup.20251009_143022
  [INFO]  Backup created: .claude.json.backup.20251009_143022
```

Your original configurations are **never lost**. If anything goes wrong, backups can be restored manually.

### Configuration Phase

The script safely merges GiljoAI MCP server configuration into your tool's config file:

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Key Points:**
- Existing `mcpServers` configurations are preserved
- Only `giljo-mcp` entry is added/updated
- All other tool settings remain unchanged
- JSON structure is validated before writing

### Summary Phase

After configuration, you'll see a summary:

```
============================================================
  Configuration Complete!
============================================================

[OK] Claude Code configured successfully
[OK] Cursor configured successfully

Successfully configured 2 tool(s).

Server: http://localhost:7272
User: your.username

============================================================
  IMPORTANT: Please restart your development tools
  for the changes to take effect.
============================================================
```

---

## Supported Tools

### Claude Code

**Description:** Official AI CLI from Anthropic  
**Config Location:**  
- Windows: `%USERPROFILE%\.claude.json`
- macOS/Linux: `~/.claude.json`

**What Gets Modified:**
- `mcpServers.giljo-mcp` entry is added/updated
- Existing settings and MCP servers are preserved

**How to Verify:**
```bash
# After restart, check available tools
claude --help

# Look for GiljoAI MCP tools in the tools list
```

### Cursor

**Description:** AI-powered code editor built on VS Code  
**Config Location:**  
- Windows: `%APPDATA%\Cursor\User\globalStorage\mcp.json`
- macOS: `~/Library/Application Support/Cursor/User/globalStorage/mcp.json`
- Linux: `~/.config/Cursor/User/globalStorage/mcp.json`

**What Gets Modified:**
- `mcpServers.giljo-mcp` entry is added/updated
- Editor settings and extensions unchanged

**How to Verify:**
1. Open Cursor
2. Open command palette (Ctrl+Shift+P / Cmd+Shift+P)
3. Type "MCP" - you should see GiljoAI MCP tools listed

### Windsurf

**Description:** Codeium's AI IDE  
**Config Location:**  
- Windows: `%APPDATA%\Windsurf\config.json`
- macOS: `~/Library/Application Support/Windsurf/config.json`
- Linux: `~/.config/Windsurf/config.json`

**What Gets Modified:**
- `mcpServers.giljo-mcp` entry is added/updated
- IDE preferences and plugins unchanged

**How to Verify:**
1. Open Windsurf
2. Check MCP integrations in settings
3. GiljoAI MCP should appear in the list

---

## Manual Configuration

If the automatic script doesn't work for your setup, you can manually configure your tools:

### Step 1: Locate Your Tool's Config File

See "Supported Tools" section above for config file locations.

### Step 2: Edit the Config File

**Important:** Create a backup first!

```bash
# Windows
copy %USERPROFILE%\.claude.json %USERPROFILE%\.claude.json.backup

# macOS/Linux
cp ~/.claude.json ~/.claude.json.backup
```

### Step 3: Add GiljoAI MCP Configuration

Open the config file in a text editor and add/merge this configuration:

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": {
        "GILJO_SERVER_URL": "http://localhost:7272",
        "GILJO_API_KEY": "your_api_key_here"
      }
    }
  }
}
```

**Configuration Variables:**

- `GILJO_SERVER_URL`: Your GiljoAI server address
  - Localhost: `http://localhost:7272`
  - LAN: `http://192.168.1.100:7272` (use your server's IP)
  - WAN: `https://your-domain.com` (with HTTPS)

- `GILJO_API_KEY`: Your API key
  - Get from dashboard: Settings → API Keys
  - Localhost mode: Optional (auto-login)
  - LAN/WAN mode: Required for authentication

### Step 4: Validate JSON

Ensure your JSON is valid before saving:

```bash
# Using Python
python -m json.tool < .claude.json

# Using jq (macOS/Linux)
jq . ~/.claude.json
```

### Step 5: Restart Your Tool

Close and reopen your development tool for changes to take effect.

---

## Troubleshooting

### Script fails with "Permission Denied"

**Windows:**
```cmd
# Run as Administrator
# Right-click giljo-mcp-setup.bat → "Run as administrator"
```

**macOS/Linux:**
```bash
# Make script executable
chmod +x giljo-mcp-setup.sh

# Run with explicit shell
bash ./giljo-mcp-setup.sh
```

### Python not found

**Error:**
```
'python' is not recognized as an internal or external command
```

**Solution:**
1. Install Python 3.11+ from [python.org](https://python.org)
2. During installation, check "Add Python to PATH"
3. Restart your terminal/command prompt
4. Verify: `python --version`

**macOS/Linux Alternative:**
Edit the config file and change `"command": "python"` to `"command": "python3"`

### Tool not detected

**Error:**
```
[SKIP] Claude Code not detected
```

**Possible Causes:**
- Tool not installed
- Non-standard installation location
- Config file in unexpected directory

**Solution:**
1. Verify tool is installed: Open the application
2. Check config location manually (see "Supported Tools")
3. Use manual configuration if script can't find it

### Configuration not working after script

**Symptoms:**
- GiljoAI MCP tools don't appear in IDE
- "Connection refused" errors
- Authentication failures

**Debugging Steps:**

1. **Check config file was modified:**
   ```bash
   # Windows
   type %USERPROFILE%\.claude.json
   
   # macOS/Linux
   cat ~/.claude.json
   ```
   Look for `giljo-mcp` entry.

2. **Verify server is running:**
   ```bash
   curl http://localhost:7272/health
   # Should return: {"status": "ok"}
   ```

3. **Test Python module:**
   ```bash
   python -m giljo_mcp.mcp_adapter --version
   ```

4. **Check API key (for LAN/WAN):**
   - Verify key exists in dashboard: Settings → API Keys
   - Ensure key is active (not expired/revoked)
   - Copy exact key (no extra spaces)

5. **Review tool logs:**
   - Claude Code: Check `~/.claude/logs/`
   - Cursor: Check developer console
   - Windsurf: Check application logs

### jq not found (macOS/Linux)

**Error:**
```
jq: command not found
```

**Solution:**
```bash
# macOS
brew install jq

# Ubuntu/Debian
sudo apt-get install jq

# CentOS/RHEL
sudo yum install jq

# After installing, run script again
./giljo-mcp-setup.sh
```

### Backup file conflicts

**Error:**
```
Failed to create backup: File already exists
```

**Solution:**
Backups use timestamps, but if running script multiple times per second:
```bash
# Manually create unique backup
cp ~/.claude.json ~/.claude.json.backup.manual

# Then run installer
./giljo-mcp-setup.sh
```

### JSON syntax errors after manual edit

**Error:**
```
Failed to parse JSON configuration
```

**Solution:**
1. Restore from backup:
   ```bash
   cp ~/.claude.json.backup ~/.claude.json
   ```

2. Use JSON validator before saving:
   ```bash
   python -m json.tool < ~/.claude.json
   ```

3. Common mistakes:
   - Missing commas between objects
   - Trailing commas (not allowed in JSON)
   - Unmatched brackets/braces
   - Unescaped quotes in strings

---

## Frequently Asked Questions

### Will this overwrite my existing config?

**No.** The installer uses intelligent JSON merging:
- Existing settings are preserved
- Other MCP servers remain untouched
- Only `mcpServers.giljo-mcp` entry is added/updated
- Timestamped backups are created before any changes

### Can I use multiple MCP servers?

**Yes!** The configuration supports multiple MCP servers:

```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp.mcp_adapter"],
      "env": { /* ... */ }
    },
    "another-mcp-server": {
      "command": "node",
      "args": ["server.js"],
      "env": { /* ... */ }
    }
  }
}
```

Each MCP server operates independently.

### How do I update my API key?

**Method 1: Re-run Installer**
1. Download fresh installer from dashboard
2. Run the script again
3. New API key will be embedded automatically

**Method 2: Manual Edit**
1. Open your tool's config file
2. Find `mcpServers.giljo-mcp.env.GILJO_API_KEY`
3. Replace with new key
4. Save and restart tool

**Method 3: Environment Variable**
```bash
# Windows
set GILJO_API_KEY=new_key_here

# macOS/Linux
export GILJO_API_KEY=new_key_here
```

### Do I need an API key for localhost?

**No.** When GiljoAI is running in localhost mode:
- API key is optional
- Auto-login is enabled
- Authentication happens via localhost detection

**Yes, for network modes:**
- LAN mode: API key required
- WAN mode: API key + OAuth required

### What happens if the GiljoAI server is unreachable?

Your development tools will continue to work normally:
- GiljoAI MCP tools will show "disconnected" status
- Other MCP servers function independently
- Your IDE/editor features are unaffected
- Reconnection is automatic when server comes back online

### Can I remove the integration?

**Yes.** To remove GiljoAI MCP integration:

**Option 1: Restore from Backup**
```bash
# Find your backup file
ls -la ~/.claude.json.backup.*

# Restore desired backup
cp ~/.claude.json.backup.20251009_143022 ~/.claude.json

# Restart tool
```

**Option 2: Manual Removal**
1. Open config file
2. Remove `giljo-mcp` entry from `mcpServers`
3. Save file
4. Restart tool

**Option 3: Edit with jq (macOS/Linux)**
```bash
jq 'del(.mcpServers."giljo-mcp")' ~/.claude.json > ~/.claude.json.tmp
mv ~/.claude.json.tmp ~/.claude.json
```

### How do I verify the integration is working?

**Method 1: Check Tool UI**
- Open your IDE (Claude Code, Cursor, Windsurf)
- Look for GiljoAI MCP tools in available tools/commands
- Should see tools like "get_orchestrator_instructions", "spawn_agent_job", etc.

**Method 2: Test Connection**
Try using a simple GiljoAI MCP tool:
```
# In Claude Code CLI
@giljo-mcp health_check

# Should return server health status
```

**Method 3: Check Dashboard**
- Open GiljoAI dashboard at `http://localhost:7274`
- Navigate to Statistics → Connected Clients
- Your tool should appear in connected clients list

### What versions are supported?

**Python:**
- Minimum: Python 3.11
- Recommended: Python 3.11 or 3.12
- Not supported: Python 3.10 and below

**Tools:**
- Claude Code: Latest version
- Cursor: 0.30.0+
- Windsurf: 1.0.0+

**Operating Systems:**
- Windows: 10, 11 (x64)
- macOS: 11+ (Big Sur and later)
- Linux: Ubuntu 20.04+, Debian 11+, CentOS 8+

### How are credentials secured?

**Localhost Mode:**
- No API key required (auto-login)
- Server binds to 127.0.0.1 only
- Not accessible from network

**LAN Mode:**
- API keys transmitted over local network
- Consider using HTTPS with self-signed certs
- Keys stored in config files (user read-only permissions)

**WAN Mode:**
- HTTPS/TLS encryption mandatory
- API key + OAuth authentication
- Rate limiting and DDoS protection enabled

**Best Practices:**
- Never commit config files to version control
- Use `.gitignore` to exclude tool configs
- Rotate API keys periodically
- Revoke keys for departing team members

### Can I automate installation for my team?

**Yes!** See the [Admin MCP Setup Guide](ADMIN_MCP_SETUP.md) for:
- Bulk deployment strategies
- Automated configuration management
- CI/CD integration examples
- Programmatic API access

---

## Next Steps

### For Developers

- **Explore MCP Tools:** Check the [MCP Tools Manual](../manuals/MCP_TOOLS_MANUAL.md)
- **Create Your First Project:** Follow the Quick Start guide
- **Join the Dashboard:** Monitor agent activity at `http://localhost:7274`

### For Team Leads

- **Admin Setup:** Read [Admin MCP Setup Guide](ADMIN_MCP_SETUP.md)
- **Team Distribution:** Learn how to generate share links
- **API Integration:** See [MCP Installer API](../api/MCP_INSTALLER_API.md)

### For System Administrators

- **Deployment Modes:** Review [Technical Architecture](../TECHNICAL_ARCHITECTURE.md)
- **Network Configuration:** See [LAN Deployment Guide](../deployment/LAN_DEPLOYMENT.md)
- **Security Hardening:** Check [Security Checklist](../deployment/SECURITY_CHECKLIST.md)

---

## Support

### Getting Help

1. **Documentation:** Check [README_FIRST.md](../README_FIRST.md) for all docs
2. **Troubleshooting:** Review this guide's troubleshooting section
3. **API Reference:** See [MCP Installer API](../api/MCP_INSTALLER_API.md)
4. **GitHub Issues:** Report bugs and feature requests

### Common Resources

- **Project Home:** `docs/README_FIRST.md`
- **Technical Details:** `docs/TECHNICAL_ARCHITECTURE.md`
- **MCP Tools Reference:** `docs/manuals/MCP_TOOLS_MANUAL.md`
- **Installation Guide:** `docs/manuals/INSTALL.md`

---

**Last Updated:** 2025-10-09  
**Version:** 3.0.0  
**Maintainer:** Documentation Manager Agent
