"""
Slash command markdown templates for Claude Code/Codex/Gemini (Handover 0093)

This module provides markdown templates with YAML frontmatter for slash commands
that can be installed to ~/.claude/commands/ directory.
"""

GIL_IMPORT_PRODUCTAGENTS_MD = """---
name: gil_import_productagents
description: Import GiljoAI agent templates to current product folder
---

Import agent templates to your active product's .claude/agents folder by calling the gil_import_productagents MCP tool.

Requirements:
- Active product configured in GiljoAI dashboard
- Product must have project_path set

The tool will fetch active agent templates from GiljoAI server, create backup of existing agents (if any), and export templates to your product's .claude/agents directory with YAML frontmatter.
"""

GIL_IMPORT_PERSONALAGENTS_MD = """---
name: gil_import_personalagents
description: Import GiljoAI agent templates to personal agents folder
---

Import agent templates to your personal ~/.claude/agents folder (available across all projects) by calling the gil_import_personalagents MCP tool.

The tool will fetch active agent templates from GiljoAI server, create backup of existing agents (if any), and export templates to ~/.claude/agents with YAML frontmatter.
"""

GIL_HANDOVER_MD = """---
name: gil_handover
description: Trigger orchestrator succession (context handover)
---

Trigger orchestrator succession when context window reaches capacity by calling the gil_handover MCP tool.

Use when context window is approaching 90% capacity, at natural phase transitions in the project, or when manual succession is requested.

The tool will generate a handover summary, create a successor orchestrator job, return a launch prompt for the new instance, and update lineage tracking.

Optional arguments: reason can be "context_limit", "manual", or "phase_transition"
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
