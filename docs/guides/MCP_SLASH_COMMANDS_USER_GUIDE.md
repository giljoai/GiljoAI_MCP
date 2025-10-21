# GiljoAI MCP Slash Commands - User Guide

**Version**: 1.0.0
**Last Updated**: 2025-10-20
**Audience**: Claude Code Users

---

## Overview

GiljoAI MCP Slash Commands automate agent workflow setup, reducing manual steps from **12+ to just 3 commands**. This guide shows you how to use these commands to quickly set up and launch AI-powered development projects.

### Benefits

- ✅ **3 commands** instead of 12+ manual steps
- ✅ **Zero copy/paste** operations
- ✅ **Zero terminal management** required
- ✅ **One-time agent installation**
- ✅ **Short project aliases** (6 characters vs 36-character UUIDs)

---

## Prerequisites

Before using slash commands, ensure you have:

1. **GiljoAI Server Running**
   - Server accessible at your configured URL (e.g., `http://192.168.1.100:7272`)
   - MCP adapter running (`python -m giljo_mcp`)

2. **Claude Code CLI Configured**
   - MCP connection to GiljoAI server configured
   - Authentication credentials set up

3. **Project Created**
   - At least one project created in the GiljoAI web dashboard
   - Project must have a product with vision document

---

## Command Reference

### 1. Install Agents (One-Time Setup)

**Command:**
```
/mcp__gil__fetch_agents
```

**Purpose:** Downloads and installs all GiljoAI agent templates to your local Claude Code directory.

**When to Use:**
- First time using GiljoAI slash commands
- After agent templates are updated on the server

**What It Does:**
1. Fetches list of available agent templates from server
2. Downloads each agent template as `.md` file
3. Saves to your local agents directory:
   - Windows: `%USERPROFILE%\.claude\agents\`
   - Mac/Linux: `~/.claude/agents/`
4. Notifies you to restart Claude Code

**Example Output:**
```
✅ Successfully installed 6 GiljoAI agents:
  • orchestrator.md
  • implementer.md
  • code-reviewer.md
  • tester.md
  • analyzer.md
  • documenter.md

📁 Location: C:\Users\YourName\.claude\agents\

⚠️ IMPORTANT: Restart Claude Code for agents to be loaded.

After restart, use: /mcp__gil__activate_project <project-alias>
```

**Important Notes:**
- ⚠️ **Restart required** - Agents won't be available until you restart Claude Code
- ⚠️ **One-time setup** - Only needs to be run once (unless updating agents)
- ⚠️ **Internet required** - Needs connection to GiljoAI server

---

### 2. Activate Project

**Command:**
```
/mcp__gil__activate_project <ALIAS>
```

**Purpose:** Prepares a project for orchestration by analyzing requirements and generating mission plan.

**Parameters:**
- `<ALIAS>` - Your project's 6-character alias (e.g., `A3F7K2`)

**When to Use:**
- Before launching a new project mission
- To re-activate a paused project

**What It Does:**
1. Fetches project details by alias
2. Validates product association
3. Analyzes project requirements
4. Generates mission plan
5. Prepares agent assignments
6. Returns next steps

**Example Usage:**
```
/mcp__gil__activate_project A3F7K2
```

**Example Output:**
```
# Project Mission Activation

**Project**: My E-Commerce Platform (Alias: A3F7K2)
**Status**: Ready for orchestration

## Mission Plan Generated

Your project has been analyzed and the following workflow has been prepared:

1. **Orchestrator Agent** - Coordinates all activities
2. **Implementer Agents** - Build features according to specifications
3. **Tester Agents** - Validate functionality and quality
4. **Reviewer Agents** - Ensure code quality and best practices

## Next Steps

To launch the orchestration workflow, use:
```
/mcp__gil__launch_project A3F7K2
```

This will:
- Spawn all required agents with their specific missions
- Begin coordinated development workflow
- Track progress in real-time
- Deliver completed solution

The mission plan has been staged and is ready for execution.
```

**Finding Your Project Alias:**
- Check the GiljoAI web dashboard - Projects page
- Alias is displayed prominently on project cards
- Format: 6 uppercase letters/numbers (e.g., `ABC123`, `X9Y2K5`)

**Troubleshooting:**
- **"Project not found"** - Check alias spelling (case-insensitive)
- **"No associated product"** - Create product with vision document first
- **"Not authorized"** - Check authentication credentials

---

### 3. Launch Project

**Command:**
```
/mcp__gil__launch_project <ALIAS>
```

**Purpose:** Launches the orchestration workflow, spawning agents and beginning coordinated development.

**Parameters:**
- `<ALIAS>` - Your project's 6-character alias

**When to Use:**
- After successfully activating a project
- To resume a project mission

**What It Does:**
1. Loads mission context and requirements
2. Verifies all required agents are available
3. Generates detailed orchestration instructions
4. Guides you through agent coordination workflow

**Example Usage:**
```
/mcp__gil__launch_project A3F7K2
```

**Example Output:**
```
# Launch Project: My E-Commerce Platform (A3F7K2)

## Mission
Build a multi-tenant e-commerce platform with product catalog,
shopping cart, checkout, and payment integration.

## Assigned Agents
- /orchestrator - Coordinates all development activities
- /implementer - Builds features per specifications
- /code-reviewer - Reviews code for quality and security
- /tester - Validates functionality and edge cases

## Your Role (Orchestrator)

You are the Orchestrator agent. Your responsibilities:

1. **Coordinate the mission** described above
2. **Invoke subagents** using SlashCommand tool:
   //implementer
   //code-reviewer
   //tester
3. **Monitor progress** via MCP:
   - Check messages: get_agent_messages()
   - Send updates: send_agent_message(to="agent_name", content="...")
4. **Ensure quality** by coordinating reviews and testing
5. **Report completion** when mission objectives met

## Workflow

1. Start with planning and architecture
2. Invoke implementer for coding tasks
3. Invoke code-reviewer after each implementation
4. Invoke tester to validate functionality
5. Iterate until all objectives complete

Begin orchestration now.
```

**What Happens Next:**
- Claude Code follows orchestration instructions automatically
- Agents are spawned as needed
- Progress tracked in real-time
- You can monitor via GiljoAI web dashboard

---

### 4. Update Agents (Optional)

**Command:**
```
/mcp__gil__update_agents
```

**Purpose:** Updates all agent templates to the latest versions from the server.

**When to Use:**
- When agent templates are updated on the server
- To get new features or bug fixes
- Periodically (e.g., monthly)

**What It Does:**
1. Re-downloads all agent templates
2. Overwrites existing `.md` files
3. Notifies you to restart Claude Code

**Example Output:**
```
# Update GiljoAI Agent Templates

This command re-downloads all agent templates to get the latest versions.

## Steps:

1. Re-downloading all templates from server...
2. Overwriting existing .md files in ~/.claude/agents/
3. ✅ Update complete

⚠️ IMPORTANT: Restart Claude Code for updated agents to be loaded.

After restart, updated agents will be available for use.
```

---

## Complete Workflow Example

Here's a complete walkthrough from start to finish:

### Step 1: First-Time Setup (One Time Only)

```bash
# In Claude Code CLI
/mcp__gil__fetch_agents
```

**Output:**
```
✅ Successfully installed 6 GiljoAI agents
📁 Location: ~/.claude/agents/
⚠️ Restart Claude Code now
```

**Action:** Restart Claude Code

---

### Step 2: Create Project in Web Dashboard

1. Open GiljoAI web dashboard: `http://localhost:7272` (or your server URL)
2. Navigate to **Products** → Create new product
3. Add vision document describing what you want to build
4. Navigate to **Projects** → Create new project
5. Link project to your product
6. Note the project **alias** (e.g., `A3F7K2`)

---

### Step 3: Activate Project

```bash
# In Claude Code CLI (after restart)
/mcp__gil__activate_project A3F7K2
```

**Output:**
```
✅ Project Activated: My E-Commerce Platform (A3F7K2)

📋 Mission Plan: [displays plan]

🤖 Selected Agents: orchestrator, implementer, code-reviewer, tester

Next: /mcp__gil__launch_project A3F7K2
```

---

### Step 4: Launch Orchestration

```bash
/mcp__gil__launch_project A3F7K2
```

**Output:**
```
# Launch Project: My E-Commerce Platform

## Mission
[Full mission details]

## Your Role (Orchestrator)
[Coordination instructions]

Begin orchestration now.
```

**What Happens:**
- Claude Code becomes the Orchestrator agent
- Follows instructions to coordinate other agents
- Spawns subagents as needed
- Completes the mission automatically

---

## Tips & Best Practices

### Project Aliases

- **Find alias**: Always visible in web dashboard project cards
- **Copy carefully**: Aliases are case-insensitive but must be exact
- **Short & memorable**: Only 6 characters - much easier than UUIDs

### Agent Installation

- **One-time only**: Only need to install agents once
- **Update periodically**: Run `/mcp__gil__update_agents` monthly
- **Restart required**: Always restart Claude Code after install/update

### Mission Planning

- **Good vision documents**: Better vision = better mission plans
- **Clear requirements**: Specific project descriptions work best
- **Product context**: Always link projects to products with vision docs

### Troubleshooting

- **Agent not found**: Did you restart after installation?
- **Project not found**: Check alias spelling in web dashboard
- **Permission denied**: Verify MCP authentication credentials
- **Server unreachable**: Check GiljoAI server is running

---

## Troubleshooting Guide

### Issue: "MCP command not recognized"

**Cause:** MCP connection not configured or server not running

**Solution:**
1. Verify GiljoAI server is running
2. Check MCP adapter: `python -m giljo_mcp`
3. Verify Claude Code MCP configuration
4. Restart Claude Code

---

### Issue: "Project 'ABC123' not found"

**Cause:** Invalid alias or project doesn't exist

**Solution:**
1. Check project exists in web dashboard
2. Verify alias spelling (check dashboard)
3. Ensure you have access (multi-tenant check)
4. Try re-creating project if needed

---

### Issue: "No agents available"

**Cause:** Agents not installed or Claude Code not restarted

**Solution:**
1. Run `/mcp__gil__fetch_agents`
2. **Restart Claude Code** (critical step)
3. Verify files exist: `~/.claude/agents/*.md`
4. Re-run fetch if files missing

---

### Issue: "Project has no associated product"

**Cause:** Project not linked to a product with vision

**Solution:**
1. Open project in web dashboard
2. Click "Edit" → Select product
3. Ensure product has vision document
4. Save and try command again

---

### Issue: "Permission denied" or "Authentication failed"

**Cause:** Invalid or missing authentication credentials

**Solution:**
1. Check `.env` file has correct API key
2. Verify MCP config has authentication
3. Generate new API key in web dashboard if needed
4. Restart MCP adapter after credential update

---

## Advanced Usage

### Custom Agent Workflows

While slash commands provide standard workflows, you can customize:

1. **Manual agent invocation**: Use `//agent-name` directly
2. **Custom missions**: Edit agent templates in `~/.claude/agents/`
3. **Hybrid approach**: Mix slash commands with manual coordination

### API Access

All slash command functionality is also available via REST API:

```bash
# Get project by alias
curl -H "Authorization: Bearer <token>" \
     http://localhost:7272/api/projects/by-alias/A3F7K2

# Download agent template
curl -H "Authorization: Bearer <token>" \
     http://localhost:7272/api/v1/agents/templates/orchestrator.md
```

See API documentation: `http://localhost:7272/docs`

### Multiple Projects

You can work with multiple projects simultaneously:

```bash
# Activate different projects
/mcp__gil__activate_project ABC123
/mcp__gil__activate_project XYZ789

# Launch specific project
/mcp__gil__launch_project ABC123
```

---

## Frequently Asked Questions

### Do I need to install agents every time?

**No.** Agent installation is one-time only. After installing and restarting Claude Code, agents remain available until you update them.

---

### Can I use these commands on any project?

**Yes**, as long as:
- Project exists in GiljoAI system
- Project is linked to a product with vision document
- You have access permissions (multi-tenant)

---

### What if I want to stop a running mission?

Use standard Claude Code controls:
- Stop current execution
- Clear context
- Start fresh with `/mcp__gil__launch_project` again

---

### Can I modify agent templates?

**Yes.** Templates are just markdown files in `~/.claude/agents/`. You can edit them, but:
- Changes will be overwritten if you run `/mcp__gil__update_agents`
- Better to create custom agents via web dashboard
- Standard templates are version-controlled

---

### How do I know which agents are available?

List files in your agents directory:

**Windows:**
```bash
dir %USERPROFILE%\.claude\agents
```

**Mac/Linux:**
```bash
ls ~/.claude/agents/
```

Or check web dashboard → Settings → Agent Templates

---

### What's the difference between activate and launch?

- **Activate** (`/mcp__gil__activate_project`): Prepares mission plan, analyzes requirements
- **Launch** (`/mcp__gil__launch_project`): Actually begins orchestration, spawns agents

Think of it as "plan" vs "execute".

---

## Getting Help

### Documentation

- **Full Implementation Guide**: `handovers/0037_0038_IMPLEMENTATION_COMPLETE.md`
- **API Documentation**: http://localhost:7272/docs
- **Project Guides**: `docs/guides/`

### Support Channels

- **Web Dashboard**: Check status, view logs
- **GitHub Issues**: Report bugs or request features
- **Documentation**: Always check docs first

### Common Resources

- GiljoAI Server: http://localhost:7272 (or your configured URL)
- API Docs (Swagger): http://localhost:7272/docs
- Agent Templates: `~/.claude/agents/` directory

---

## Version History

### Version 1.0.0 (2025-10-20)

- ✅ Initial release
- ✅ 4 slash commands implemented
- ✅ Project alias system
- ✅ Agent template automation
- ✅ Complete workflow automation

---

**Need More Help?**

Check the full implementation documentation in `handovers/0037_0038_IMPLEMENTATION_COMPLETE.md` for technical details, architecture, and advanced topics.
