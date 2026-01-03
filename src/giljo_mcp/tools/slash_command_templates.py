"""
Slash command markdown templates for Claude Code/Codex/Gemini (Handover 0093)

This module provides markdown templates with YAML frontmatter for slash commands
that can be installed to ~/.claude/commands/ directory.
"""

GIL_HANDOVER_MD = """---
name: gil_handover
description: Trigger orchestrator succession (context handover)
allowed-tools: ["mcp__giljo-mcp__*"]
---

Use the mcp__giljo-mcp__gil_handover tool to trigger orchestrator succession when context window reaches capacity.

This will:
1. Generate handover summary from current orchestrator
2. Create successor orchestrator job (via create_successor_orchestrator)
3. Return launch prompt for new instance
4. Update lineage tracking

Use when:
- Context window approaching 90% capacity
- Natural phase transitions in the project
- Manual succession requested

Optional arguments: reason can be "context_limit", "manual", or "phase_transition"

Call the tool now to begin.
"""

GIL_ACTIVATE_MD = """---
name: gil_activate
description: Activate a project to prepare orchestrator staging
allowed-tools: ["mcp__giljo-mcp__*"]
---

Provide the project ID when calling the tool to activate it:

Example:
"Call mcp__giljo-mcp__gil_activate with {\"project_id\": \"<PROJECT_ID>\"}"

Activation will:
1. Set project status to active
2. Ensure an orchestrator job exists (status=waiting)

Call the tool with project_id to begin.
"""

GIL_LAUNCH_MD = """---
name: gil_launch
description: Launch a staged project into execution
allowed-tools: ["mcp__giljo-mcp__*"]
---

Provide the project ID when calling the tool to launch execution:

Example:
"Call mcp__giljo-mcp__gil_launch with {\"project_id\": \"<PROJECT_ID>\"}"

Launch will:
1. Validate mission exists and agents are spawned
2. Update project staging status to launching

Call the tool with project_id to begin.
"""

GIL_GET_CLAUDE_AGENTS_MD = """---
name: gil_get_claude_agents
description: Download and install GiljoAI agent templates to Claude Code
allowed-tools: ["mcp__giljo-mcp__get_agent_download_url"]
---

Install GiljoAI agent templates to your Claude Code environment.

## STEP 1: Get Download URL

Call the MCP tool to stage templates and get download URL:

```
Tool: mcp__giljo-mcp__get_agent_download_url
Parameters: {}
```

Returns: `download_url` (valid 15 minutes, one-time use) and `template_count`

## STEP 2: Download Templates

Use the Bash tool (NOT PowerShell) to download. The URL contains auth token - no headers needed:

```bash
curl -o /tmp/agents.zip "{download_url}"
```

## STEP 3: Ask User Install Location

Ask: "Where should I install the {template_count} agent templates?"

Options:
- **Project agents** (`.claude/agents/`) - Available only in this project
- **User agents** (`~/.claude/agents/`) - Available across all your projects

## STEP 4: Extract to Chosen Location

Use Bash to extract based on user choice:

**For Project agents:**
```bash
mkdir -p .claude/agents && unzip -o /tmp/agents.zip -d .claude/agents/ && rm /tmp/agents.zip
```

**For User agents:**
```bash
mkdir -p ~/.claude/agents && unzip -o /tmp/agents.zip -d ~/.claude/agents/ && rm /tmp/agents.zip
```

## STEP 5: Confirm and Restart Notice

Tell the user:
1. How many templates were installed (from `template_count`)
2. Where they were installed
3. **They must restart Claude Code** (Ctrl+C and relaunch) for agents to become available
4. After restart, use agents via `@agent-name` in Claude Code

Example: "Installed 6 agent templates to ~/.claude/agents/. **Please restart Claude Code** for the agents to become available."

## IMPORTANT

- Use the Bash tool for curl/unzip commands (works on Windows via Git Bash, Linux, macOS)
- Unix paths (/tmp, ~/.claude/) work on ALL platforms
- Do NOT use PowerShell or Windows-style paths
"""


def get_all_templates() -> dict[str, str]:
    """
    Return all slash command templates

    Returns:
        dict[str, str]: Mapping of filename to markdown content
    """
    return {
        "gil_get_claude_agents.md": GIL_GET_CLAUDE_AGENTS_MD,
        "gil_activate.md": GIL_ACTIVATE_MD,
        "gil_launch.md": GIL_LAUNCH_MD,
        "gil_handover.md": GIL_HANDOVER_MD,
    }
