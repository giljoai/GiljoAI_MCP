"""
Slash command markdown templates for Claude Code/Codex/Gemini (Handover 0093)

This module provides markdown templates with YAML frontmatter for slash commands
that can be installed to ~/.claude/commands/ directory.
"""

GIL_IMPORT_PRODUCTAGENTS_MD = """---
name: gil_import_productagents
description: Import GiljoAI agent templates to current product folder
allowed-tools: ["mcp__giljo-mcp__*"]
---

Use the mcp__giljo-mcp__gil_import_productagents tool to import agent templates to your active product's .claude/agents folder.

This will:
1. Download active agent templates from GiljoAI server
2. Create automatic backup of existing agents (if any)
3. Install templates to your product's .claude/agents directory with YAML frontmatter

Requirements:
- Active product configured in GiljoAI dashboard
- Product must have project_path set
- Connected to GiljoAI MCP server

This tool will generate a secure one-time download link. The AI assistant will automatically download and install the files to the appropriate location on your system.

Call the tool now to begin.
"""

GIL_IMPORT_PERSONALAGENTS_MD = """---
name: gil_import_personalagents
description: Import GiljoAI agent templates to personal agents folder
allowed-tools: ["mcp__giljo-mcp__*"]
---

Use the mcp__giljo-mcp__gil_import_personalagents tool to import agent templates to your personal ~/.claude/agents folder (available across all projects).

This will:
1. Download active agent templates from GiljoAI server
2. Create automatic backup of existing agents (if any)
3. Install templates to ~/.claude/agents with YAML frontmatter

Requirements:
- Connected to GiljoAI MCP server

This tool will generate a secure one-time download link. The AI assistant will automatically download and install the files to the appropriate location on your system.

Call the tool now to begin.
"""

GIL_HANDOVER_MD = """---
name: gil_handover
description: Trigger orchestrator succession (context handover)
allowed-tools: ["mcp__giljo-mcp__*"]
---

Use the mcp__giljo-mcp__gil_handover tool to trigger orchestrator succession when context window reaches capacity.

This will:
1. Generate handover summary from current orchestrator
2. Create successor orchestrator job
3. Return launch prompt for new instance
4. Update lineage tracking

Use when:
- Context window approaching 90% capacity
- Natural phase transitions in the project
- Manual succession requested

Optional arguments: reason can be "context_limit", "manual", or "phase_transition"

Call the tool now to begin.
"""

GIL_FETCH_MD = """---
name: gil_fetch
description: Fetch and install GiljoAI agent templates
allowed-tools: ["mcp__giljo-mcp__*"]
---

Use the mcp__giljo-mcp__gil_fetch tool to download the latest agent templates from your GiljoAI MCP server.

This will:
1. Generate a secure one-time download link
2. Download agent_templates.zip
3. Install into your ~/.claude/agents/ folder (or project .claude/agents)

Call the tool now to begin.
"""

GIL_UPDATE_AGENTS_MD = """---
name: gil_update_agents
description: Update GiljoAI agent templates to the latest version
allowed-tools: ["mcp__giljo-mcp__*"]
---

Use the mcp__giljo-mcp__gil_update_agents tool to refresh your installed agent templates to the latest versions.

This will:
1. Generate a secure one-time download link
2. Download agent_templates.zip
3. Replace existing templates with a backup

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
allowed-tools: ["mcp__giljo-mcp__gil_import_productagents", "mcp__giljo-mcp__gil_import_personalagents"]
---

Install GiljoAI agent templates to your Claude Code environment.

## STEP 1: Ask User

Ask the user: "Where should I install the agent templates?"

Options:
- **Project agents** (`.claude/agents/` in current directory) - Available only in this project
- **User agents** (`~/.claude/agents/`) - Available across all your projects

## STEP 2: Get Download URL

Based on user choice, call the appropriate MCP tool:

**For Project agents:**
```
Tool: mcp__giljo-mcp__gil_import_productagents
Parameters: {}
```

**For User agents:**
```
Tool: mcp__giljo-mcp__gil_import_personalagents
Parameters: {}
```

The tool returns a `download_url` (valid for 15 minutes, one-time use).

## STEP 3: Download and Extract

Use Bash to download and extract. The download URL includes authentication via token - no API key header needed.

**For Project agents (cross-platform):**
```bash
curl -o agents.zip "{download_url}" && mkdir -p .claude/agents && unzip -o agents.zip -d .claude/agents/ && rm agents.zip
```

**For User agents (cross-platform):**
```bash
curl -o agents.zip "{download_url}" && mkdir -p ~/.claude/agents && unzip -o agents.zip -d ~/.claude/agents/ && rm agents.zip
```

## STEP 4: Confirm and Restart Notice

Tell the user:
1. How many agent templates were installed
2. Where they were installed
3. **IMPORTANT: They must restart their Claude Code session** for the new agents to be available
4. After restart, they can use agents via `@agent-name` in Claude Code

Example completion message:
"Installed 6 agent templates to .claude/agents/. **Please restart Claude Code** (Ctrl+C and relaunch) for the agents to become available. After restart, you can use them with @orchestrator, @implementer, etc."

## IMPORTANT

- MCP tools are NATIVE tool calls - call them directly like Read, Write, or Bash
- Do NOT use curl or HTTP requests to call MCP tools
- The download URL already contains authentication (token-based) - no X-API-Key header needed
"""


def get_all_templates() -> dict[str, str]:
    """
    Return all slash command templates

    Returns:
        dict[str, str]: Mapping of filename to markdown content
    """
    return {
        "gil_import_productagents.md": GIL_IMPORT_PRODUCTAGENTS_MD,
        "gil_import_personalagents.md": GIL_IMPORT_PERSONALAGENTS_MD,
        "gil_handover.md": GIL_HANDOVER_MD,
        "gil_fetch.md": GIL_FETCH_MD,
        "gil_update_agents.md": GIL_UPDATE_AGENTS_MD,
        "gil_activate.md": GIL_ACTIVATE_MD,
        "gil_launch.md": GIL_LAUNCH_MD,
        "gil_get_claude_agents.md": GIL_GET_CLAUDE_AGENTS_MD,
    }
