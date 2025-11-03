# MCP Slash Commands - Quick Reference

**Version**: 1.0.0 | **Last Updated**: 2025-10-20

---

## The 3-Command Workflow

```bash
1. /gil_import_personalagents        # Install agents to ~/.claude (recommended)
   or /gil_import_productagents      # Install to product's .claude
   or /mcp__gil__fetch_agents        # Legacy alias (older setups)
   → Restart Claude Code

2. /mcp__gil__activate_project ABC123 # Prepare mission

3. /mcp__gil__launch_project ABC123   # Begin orchestration
```

---

## Command Summary

| Command | Purpose | When to Use | Restart Required? |
|---------|---------|-------------|-------------------|
| `/mcp__gil__fetch_agents` | Install agent templates | First time, or after updates | ✅ Yes |
| `/mcp__gil__activate_project <alias>` | Create mission plan | Before launching project | ❌ No |
| `/mcp__gil__launch_project <alias>` | Begin orchestration | After activation | ❌ No |
| `/mcp__gil__update_agents` | Update templates | Periodically (monthly) | ✅ Yes |

---

## Command Details

### 1️⃣ Install Agents / Import Templates

```bash
/gil_import_personalagents      # Personal (~/.claude/agents)
/gil_import_productagents       # Product (<project>/.claude/agents)
# Legacy: /mcp__gil__fetch_agents
```

**Installs:** orchestrator, implementer, code-reviewer, tester, analyzer, documenter

**Location:**
- Windows: `%USERPROFILE%\.claude\agents\`
- Mac/Linux: `~/.claude/agents/`

**⚠️ Must restart Claude Code after installation**
**Note:** Auto-export from orchestrator has been removed (0074). Use import commands or Settings → Integrations.

---

### 2️⃣ Activate Project

```bash
/mcp__gil__activate_project <ALIAS>
```

**Example:** `/mcp__gil__activate_project A3F7K2`

**Returns:** Mission plan and next steps

**Find alias:** GiljoAI web dashboard → Projects page

---

### 3️⃣ Launch Project

```bash
/mcp__gil__launch_project <ALIAS>
```

**Example:** `/mcp__gil__launch_project A3F7K2`

**Starts:** Automatic orchestration workflow

**Agents spawned:** As needed per mission plan

---

### 4️⃣ Update Agents (Optional)

```bash
/mcp__gil__update_agents
```

**Updates:** All agent templates to latest versions

**⚠️ Must restart Claude Code after update**

---

## Quick Troubleshooting

| Problem | Solution |
|---------|----------|
| Command not recognized | Check MCP connection, restart Claude Code |
| Project not found | Verify alias in web dashboard |
| No agents available | Run `/mcp__gil__fetch_agents` + restart |
| Permission denied | Check authentication credentials |
| No associated product | Link project to product with vision doc |

---

## Finding Your Project Alias

1. Open GiljoAI web dashboard
2. Go to **Projects** page
3. Find your project card
4. Alias is displayed prominently (e.g., `A3F7K2`)

**Format:** 6 uppercase letters/numbers

---

## Before You Start

✅ GiljoAI server running
✅ MCP adapter running (`python -m giljo_mcp`)
✅ Claude Code MCP configured
✅ Project created in web dashboard
✅ Project linked to product with vision

---

## Agent Installation Paths

Agents are installed to:

**Windows:**
```
C:\Users\YourName\.claude\agents\
```

**Mac:**
```
/Users/yourname/.claude/agents/
```

**Linux:**
```
/home/yourname/.claude/agents/
```

---

## Common Workflow

### First Time Setup
```bash
1. /mcp__gil__fetch_agents
2. Restart Claude Code
3. Create project in web dashboard
4. Note project alias (e.g., A3F7K2)
5. /mcp__gil__activate_project A3F7K2
6. /mcp__gil__launch_project A3F7K2
```

### Subsequent Projects
```bash
1. Create project in web dashboard
2. Note alias
3. /mcp__gil__activate_project <alias>
4. /mcp__gil__launch_project <alias>
```

### Monthly Maintenance
```bash
1. /mcp__gil__update_agents
2. Restart Claude Code
```

---

## Web Dashboard URLs

**Default:** http://localhost:7272
**LAN:** http://192.168.1.100:7272 (your server IP)

**Pages:**
- Dashboard: `/`
- Projects: `/projects`
- Products: `/products`
- Settings: `/settings`
- API Docs: `/docs`

---

## Tips

💡 **Aliases are short** - Only 6 chars vs 36-char UUIDs
💡 **Case-insensitive** - `ABC123` = `abc123`
💡 **Always in dashboard** - Prominently displayed on project cards
💡 **One-time install** - Agents persist after installation
💡 **Restart matters** - Always restart after install/update
💡 **Vision required** - Projects must link to products with vision docs

---

## Advanced: API Alternative

REST API endpoints for programmatic access:

```bash
# Get project by alias
GET /api/projects/by-alias/{alias}

# List agent templates
GET /api/v1/agents/templates/

# Download template
GET /api/v1/agents/templates/{filename}
```

**Documentation:** http://localhost:7272/docs

---

## Getting Help

📖 **Full User Guide:** `docs/guides/MCP_SLASH_COMMANDS_USER_GUIDE.md`
📖 **Implementation Details:** `handovers/0037_0038_IMPLEMENTATION_COMPLETE.md`
📖 **API Docs:** http://localhost:7272/docs

---

**Print this page for quick reference at your desk!**
