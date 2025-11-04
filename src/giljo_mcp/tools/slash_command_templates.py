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
    }
