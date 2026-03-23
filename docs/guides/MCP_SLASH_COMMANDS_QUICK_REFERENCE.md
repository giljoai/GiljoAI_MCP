# MCP Slash Commands - Quick Reference

**Version**: 2.0.0 | **Last Updated**: 2026-01-03

---

## One-Time Setup (Install Slash Commands)

If you don’t already have the `/gil_*` commands in Claude Code:

1. Configure the GiljoAI MCP server connection in Claude Code
2. Call the MCP tool `mcp__giljo-mcp__setup_slash_commands` (no arguments)
3. Run the returned `bash_command`
4. Restart Claude Code

---

## Daily Workflow (4 Commands)

```text
1. /gil_get_agents            # Install/update agent templates (choose Project vs User)
   → Restart Claude Code

2. /gil_activate                     # Activate a project (requires project_id UUID)

3. /gil_launch                       # Launch execution (requires project_id UUID)

Optional:
4. /gil_handover                     # Trigger orchestrator succession (reason optional)
```

---

## Command Summary

| Command | Purpose | Restart Required? |
|---------|---------|-------------------|
| `/gil_get_agents` | Download + install agent templates | ✅ Yes |
| `/gil_activate` | Activate project for staging | ❌ No |
| `/gil_launch` | Launch staged project into execution | ❌ No |
| `/gil_handover` | Trigger orchestrator succession | ❌ No |

---

## Finding the Project ID

- Use the GiljoAI web dashboard → Projects
- Copy the project UUID (not a short alias)

