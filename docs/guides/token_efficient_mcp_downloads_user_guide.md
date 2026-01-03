# Token-Efficient MCP Downloads - User Guide

**Version:** 2.0  
**Last Updated:** 2026-01-03

---

## Overview

GiljoAI MCP provides HTTP download endpoints for slash commands and agent templates so the AI does not need to emit thousands of tokens of file content.

Downloads are:
- **Small in-token** (the AI returns a URL + a short install command)
- **Fast** (ZIP over HTTP)
- **Tenant-isolated** where applicable (agent templates via token staging)

---

## What You Can Download

1. **Slash commands ZIP** (public)
   - Endpoint: `GET /api/download/slash-commands.zip`
   - Contains:
     - `gil_get_claude_agents.md`
     - `gil_activate.md`
     - `gil_launch.md`
     - `gil_handover.md`
     - `install.sh`, `install.ps1`

2. **Agent templates ZIP** (optional-auth)
   - Endpoint: `GET /api/download/agent-templates.zip`
   - Returns tenant templates when authenticated; system defaults when unauthenticated (if present)
   - Contains up to 8 agent template `.md` files plus `install.sh` / `install.ps1`

---

## Method 1: Automated (Recommended)

### A) Install Slash Commands (One-Time)

1. Configure the GiljoAI MCP server in Claude Code
2. Call the MCP tool: `mcp__giljo-mcp__setup_slash_commands`
3. Run the returned `bash_command`
4. Restart Claude Code

### B) Install/Update Agent Templates (Claude Code)

Run:
```
/gil_get_claude_agents
```

This stages a one-time ZIP URL via `mcp__giljo-mcp__get_agent_download_url`, downloads it, and then asks where to install:
- **Project**: `.claude/agents/`
- **User**: `~/.claude/agents/`

Restart Claude Code after installation.

---

## Method 2: Manual Download (HTTP)

### Slash Commands

```bash
curl http://localhost:7272/api/download/slash-commands.zip -o slash-commands.zip
mkdir -p ~/.claude/commands
unzip -o slash-commands.zip -d ~/.claude/commands/
rm slash-commands.zip
```

### Agent Templates (Authenticated)

```bash
curl -H "X-API-Key: $GILJO_API_KEY" http://localhost:7272/api/download/agent-templates.zip -o agents.zip
mkdir -p ~/.claude/agents
unzip -o agents.zip -d ~/.claude/agents/
rm agents.zip
```

---

## Method 3: Install Scripts

Download a script that embeds the correct server URL:

- Slash commands:
  - `GET /api/download/install-script.sh?script_type=slash-commands`
  - `GET /api/download/install-script.ps1?script_type=slash-commands`
- Agent templates:
  - `GET /api/download/install-script.sh?script_type=agent-templates`
  - `GET /api/download/install-script.ps1?script_type=agent-templates`

---

## Troubleshooting

- **Commands not showing**: reinstall slash commands and restart Claude Code.
- **Agent templates not showing**: rerun `/gil_get_claude_agents` and restart Claude Code.
- **401 / not authenticated**: check `X-API-Key` and MCP connection config.

