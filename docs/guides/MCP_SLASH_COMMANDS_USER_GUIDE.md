# GiljoAI MCP Slash Commands - User Guide

**Version**: 2.0.0  
**Last Updated**: 2026-01-03  
**Audience**: Claude Code users

---

## Overview

GiljoAI provides a small set of `/gil_*` slash commands that install agent templates and control the project workflow (activate → launch), without requiring the AI to paste large template files into chat.

Current supported commands:
- `/gil_get_claude_agents`
- `/gil_activate`
- `/gil_launch`
- `/gil_handover`

---

## Prerequisites

1. **GiljoAI MCP server running** and reachable from your machine.
2. **Claude Code configured** with the GiljoAI MCP connection (HTTP JSON-RPC `/mcp`) and an API key.
3. **A project exists** in the GiljoAI dashboard (copy its `project_id` UUID).

---

## Step 0 (One-Time): Install the Slash Commands

If Claude Code does not show `/gil_*` commands yet:

1. In Claude Code, call the MCP tool: `mcp__giljo-mcp__setup_slash_commands`
2. Run the returned `bash_command` (use the Bash tool, not PowerShell)
3. Restart Claude Code

This installs command files into `~/.claude/commands/`.

---

## Step 1: Install/Update Agent Templates

Run:
```
/gil_get_claude_agents
```

This command:
- Calls `mcp__giljo-mcp__get_agent_download_url` to get a one-time ZIP URL
- Downloads the ZIP and asks where to install:
  - **Project**: `.claude/agents/` (only this repo)
  - **User**: `~/.claude/agents/` (all repos)

After installation, restart Claude Code so the agent templates are loaded.

---

## Step 2: Activate a Project

Run:
```
/gil_activate
```

Provide your `project_id` UUID when prompted.

This sets the project active and ensures an orchestrator job exists for staging.

---

## Step 3: Launch Execution

Run:
```
/gil_launch
```

Provide the same `project_id` UUID.

This transitions the project from staging to execution.

---

## Optional: Context Handover (Orchestrator Succession)

Run:
```
/gil_handover
```

Use this when the orchestrator context is getting large or when you want to start a fresh orchestrator session while preserving lineage and continuity.

---

## Troubleshooting

- **Command not found**: Re-run `mcp__giljo-mcp__setup_slash_commands` and restart Claude Code.
- **Agents not available**: Re-run `/gil_get_claude_agents` and restart Claude Code.
- **401 / not authenticated**: Verify your MCP connection and API key (`X-API-Key`).
- **Wrong install location**: Re-run `/gil_get_claude_agents` and pick the correct location.

