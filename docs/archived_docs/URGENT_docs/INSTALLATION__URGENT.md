# GiljoAI MCP Installation Guide

## Overview

GiljoAI MCP is a **standalone orchestration server** that coordinates multiple AI coding agents. It runs separately from your development projects and can serve multiple projects simultaneously.

## Architecture

```
┌─────────────────────────────────────────┐
│         GiljoAI MCP Server              │
│   (Installed once, system-wide)         │
│                                         │
│  • Runs at localhost:7272 or network   │
│  • Has its own Python environment       │
│  • Registered globally with Claude     │
└────────────┬────────────────────────────┘
             │
             │ Connects to
             │
    ┌────────┴────────┬────────────┬────────────┐
    │                 │            │            │
┌───▼────┐     ┌─────▼───┐  ┌────▼────┐  ┌────▼────┐
│Project A│     │Project B│  │Project C│  │Project D│
│         │     │         │  │         │  │         │
│.mcp.json│     │.mcp.json│  │.mcp.json│  │.mcp.json│
└─────────┘     └─────────┘  └─────────┘  └─────────┘

Each project has a lightweight config pointing to the MCP server
```

## Installation Process

### Step 1: Install the MCP Server (One-time)

Choose a dedicated directory for the MCP server installation. This should NOT be inside any project folder.

**Recommended locations:**
- Windows: `C:\GiljoAI_MCP` or `%USERPROFILE%\GiljoAI_MCP`
- Mac/Linux: `~/giljo-mcp` or `/opt/giljo-mcp`

```bash
# 1. Download the installer to your chosen directory
cd C:\GiljoAI_MCP  # or your chosen location

# 2. Run the installer
python bootstrap.py

# Or use the installation scripts:
install.bat         # Windows
./quickstart.sh     # Mac/Linux
```

The installer will:
- Create a Python virtual environment
- Install all dependencies
- Configure PostgreSQL database
- Set up server ports and security

### Step 1.5: Connect Your AI Coding Agent (One-Time)

After installing the server, connect your AI tool to enable orchestration:

**Option A: Universal Wizard (Recommended)**

```bash
cd %INSTALL_DIR%  # Your installation directory
python register_ai_tools.py
```

The wizard will:
- Detect which AI CLIs are installed (Claude, Codex, Gemini, Grok)
- Allow you to select which tools to configure
- Automatically register with selected tools
- Verify the integration

**Option B: Individual Tool Registration**

Register with specific AI tools using dedicated scripts:

```bash
# Claude Code
register_claude.bat                    # Windows
./register_claude.sh                   # Mac/Linux

# Codex CLI (OpenAI)
python register_codex.py

# Gemini CLI (Google)
python register_gemini.py

# Grok CLI (xAI)
python register_grok.py                # Helper with instructions
```

**Detailed Instructions:**

For comprehensive integration guides including:
- Manual configuration steps
- Troubleshooting
- Configuration file locations
- Verification commands

See: [`docs/AI_TOOL_INTEGRATION.md`](docs/AI_TOOL_INTEGRATION.md)

**Supported AI Coding Agents:**
- ✅ Claude Code (full MCP support with CLI commands)
- ✅ Codex CLI (OpenAI - TOML configuration)
- ✅ Gemini CLI (Google - JSON configuration)
- ✅ Grok CLI (xAI - multiple implementations)

### Step 2: Configure Your Development Projects

For each project that needs orchestration:

```bash
# 1. Go to your project directory
cd C:\MyProjects\MyAwesomeApp

# 2. Run the connection script
# Option A: Copy and run the connector
python C:\GiljoAI_MCP\connect_project.py

# Option B: Use the batch file (Windows)
C:\GiljoAI_MCP\connect_project.bat
```

This creates a `.mcp.json` file in your project with:
- Connection details to the MCP server
- Authentication credentials (if needed)
- Project-specific settings

## Deployment Modes

### Localhost Mode (Default)
- **Use case**: Single developer on local machine
- **Installation**: `C:\GiljoAI_MCP` or `~/giljo-mcp`
- **Access**: `localhost:7272`
- **Database**: PostgreSQL (automatically configured)
- **Authentication**: None required

### Network Server Mode
- **Use case**: Team collaboration or remote access
- **Installation**: Dedicated server or VM
- **Access**: `http://server-ip:7272`
- **Database**: PostgreSQL recommended
- **Authentication**: API keys

## Quick Start Commands

### After Server Installation

```bash
# Start the MCP server
cd C:\GiljoAI_MCP
start_giljo.bat         # Windows
./start_giljo.sh        # Mac/Linux

# The server runs:
# - MCP protocol on stdio (for Claude)
# - REST API on port 7272
# - WebSocket on port 7272/ws
```

### In Your Project Directory

```bash
# Connect your project to the MCP server
python C:\GiljoAI_MCP\connect_project.py

# This creates .mcp.json with:
{
  "mcpServers": {
    "giljo-orchestrator": {
      "command": "C:\\GiljoAI_MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "giljo_mcp"],
      "description": "GiljoAI MCP Orchestrator"
    }
  }
}
```

## Verification

### 1. Verify Server Installation

```bash
# In the MCP server directory
python -m giljo_mcp --version

# Check if registered with Claude
claude mcp list
```

### 2. Verify Project Connection

```bash
# In your project directory
# The .mcp.json file should exist
dir .mcp.json       # Windows
ls -la .mcp.json    # Mac/Linux
```

### 3. Test with Claude

1. Open Claude in your project directory
2. Type: "List available MCP tools"
3. You should see GiljoAI orchestration tools

## Troubleshooting

### MCP Server Not Found
- Ensure server is installed in a dedicated directory
- Check GILJO_MCP_HOME environment variable
- Verify Python path in .mcp.json

### Connection Failed
- Ensure MCP server is running
- Check firewall settings for port 7272
- Verify API key if using network mode

### Claude Doesn't See MCP Tools
- Restart Claude after configuration
- Check global registration: `claude mcp list`
- Verify .mcp.json in your project directory

## Best Practices

1. **Server Location**: Install MCP server in a dedicated directory, NOT in project folders
2. **One Server, Many Projects**: A single MCP server can handle multiple projects
3. **Project Isolation**: Each project has its own .mcp.json configuration
4. **Version Control**: Add .env.giljo to .gitignore (contains credentials)
5. **Team Setup**: Use network mode with API keys for team collaboration

## Environment Variables

The system respects these environment variables:

```bash
# Server location (helps auto-detection)
GILJO_MCP_HOME=C:\GiljoAI_MCP

# For network mode
GILJO_MCP_URL=http://server:7272
GILJO_MCP_API_KEY=your-api-key
```

## Uninstallation

### Remove Server
```bash
# 1. Stop all services
# 2. Delete the installation directory
rmdir /s C:\GiljoAI_MCP     # Windows
rm -rf ~/giljo-mcp          # Mac/Linux

# 3. Unregister from Claude
claude mcp remove giljo-orchestrator
```

### Remove from Project
```bash
# Just delete the configuration file
del .mcp.json .env.giljo    # Windows
rm .mcp.json .env.giljo      # Mac/Linux
```

## Support

- GitHub Issues: https://github.com/giljo/GiljoAI_MCP/issues
- Documentation: https://docs.giljo.ai
- Discord: https://discord.gg/giljoai

---

**Remember**: GiljoAI MCP is infrastructure - install it once, use it everywhere!