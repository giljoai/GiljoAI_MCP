"""
Slash command markdown templates for Claude Code/Codex/Gemini (Handover 0093)

This module provides markdown templates with YAML frontmatter for slash commands
that can be installed to ~/.claude/commands/ directory.
"""

GIL_IMPORT_PRODUCTAGENTS_MD = """---
name: gil_import_productagents
description: Import GiljoAI agent templates to current product folder
---

# Import Product Agents

Imports active agent templates to your current product's `.claude/agents` folder.

**Requirements:**
- Active product configured in GiljoAI dashboard
- Product must have `project_path` set

**What it does:**
1. Fetches active agent templates from GiljoAI server
2. Creates backup of existing agents (if any)
3. Exports templates to `<project_path>/.claude/agents/`
4. Generates YAML frontmatter for each template

**Usage:**
```
/gil_import_productagents
```

**Output:**
- Backup created: `<project_path>/.claude/agents.backup.<timestamp>.zip`
- Templates written: `<project_path>/.claude/agents/*.md`

Call the MCP tool: `mcp__giljo-mcp__gil_import_productagents`
"""

GIL_IMPORT_PERSONALAGENTS_MD = """---
name: gil_import_personalagents
description: Import GiljoAI agent templates to personal agents folder
---

# Import Personal Agents

Imports active agent templates to your global personal agents folder.

**Target:** `~/.claude/agents/` (available across all projects)

**What it does:**
1. Fetches active agent templates from GiljoAI server
2. Creates backup of existing agents (if any)
3. Exports templates to `~/.claude/agents/`
4. Generates YAML frontmatter for each template

**Usage:**
```
/gil_import_personalagents
```

**Output:**
- Backup created: `~/.claude/agents.backup.<timestamp>.zip`
- Templates written: `~/.claude/agents/*.md`

Call the MCP tool: `mcp__giljo-mcp__gil_import_personalagents`
"""

GIL_HANDOVER_MD = """---
name: gil_handover
description: Trigger orchestrator succession (context handover)
---

# Orchestrator Handover

Triggers orchestrator succession when context window reaches capacity.

**Purpose:** Create successor orchestrator instance for context handover

**When to use:**
- Context window approaching 90% capacity
- Natural phase transition in project
- Manual succession requested

**What it does:**
1. Generates handover summary (<10K tokens)
2. Creates successor orchestrator job
3. Returns launch prompt for new instance
4. Updates lineage tracking (spawned_by chain)

**Usage:**
```
/gil_handover
```

**Arguments:**
- `reason` (optional): "context_limit" | "manual" | "phase_transition"

Call the MCP tool: `mcp__giljo-mcp__create_successor_orchestrator`
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
