"""
Template rendering utilities for packaging/export (Claude Code, Gemini CLI, Codex CLI).

Implements 0102a/0103 rules for Claude Code agent templates:
- YAML frontmatter with: name, description, model, color (optional)
- Color field maps GiljoAI app colors to Claude Code named colors
- Omit tools to inherit all by default
- Body: system_instructions + optional Behavioral Rules / Success Criteria sections
- Packaging cap: max 8 distinct active roles with precedence
  1) is_default first
  2) updated_at descending
  3) name ascending

Handover 0836a: Added render_gemini_agent() and render_codex_agent() for multi-platform export.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

import yaml


if TYPE_CHECKING:
    from collections.abc import Iterable

    from .models import AgentTemplate


def _slugify_filename(name: str) -> str:
    """Return a safe slug filename (keeps existing slug if already valid)."""
    slug = name.strip().lower().replace(" ", "-")
    slug = re.sub(r"[^a-z0-9._-]", "-", slug)
    # collapse multiple dashes
    slug = re.sub(r"-+", "-", slug).strip("-")
    return slug or "agent"


def hex_to_claude_color(hex_code: str | None) -> str | None:
    """Convert hex color code to Claude Code named color.

    Maps GiljoAI app colors to Claude Code CLI color names.
    Returns None if no mapping exists (color field will be omitted).

    Supported Claude Code colors: green, blue, purple, orange, red, yellow, grey

    Args:
        hex_code: Hex color code (e.g., "#3498DB") or None

    Returns:
        Claude Code named color or None
    """
    if not hex_code:
        return None

    # Normalize hex code (uppercase, ensure # prefix)
    normalized = hex_code.strip().upper()
    if not normalized.startswith("#"):
        normalized = f"#{normalized}"

    # Map GiljoAI app colors to Claude Code named colors
    color_map = {
        # Orchestrator - tan/bronze -> orange
        "#D4A574": "orange",
        # Implementer/Frontend - blue
        "#3498DB": "blue",
        # Tester - yellow/gold
        "#FFC300": "yellow",
        # Analyzer - red
        "#E74C3C": "red",
        # Reviewer/Designer - purple
        "#9B59B6": "purple",
        # Documenter/Backend - green
        "#27AE60": "green",
        "#2ECC71": "green",
        # Default/fallback - grey
        "#90A4AE": "grey",
    }

    return color_map.get(normalized)


def render_claude_agent(template: AgentTemplate) -> str:
    """Render a single AgentTemplate to Claude Code-compatible Markdown.

    Handover 0813: Now includes user_instructions (role identity prose) in the body.
    Structure: frontmatter + system_instructions (slim bootstrap) + user_instructions
    (role prose) + behavioral_rules + success_criteria.

    Rules per 0102a:
    - Frontmatter includes name, description, model (omit tools to inherit all)
    - Description fallback: "Subagent for <role>"
    - Model default: 'sonnet' if blank; allow 'inherit' if explicitly set
    """
    description = template.description or (f"Subagent for {template.role}" if template.role else "Subagent")
    # Respect explicit 'inherit'; otherwise default to sonnet when blank
    model_value = (template.model or "sonnet").strip()

    frontmatter = {
        "name": template.name,
        "description": description,
        "model": model_value,
    }

    # Include color field if template has background_color (maps to Claude Code named colors)
    if hasattr(template, "background_color") and template.background_color:
        claude_color = hex_to_claude_color(template.background_color)
        if claude_color:
            frontmatter["color"] = claude_color

    # Include tools only when explicitly specified (inherit all otherwise)
    tools_field = (template.tools or "").strip() if hasattr(template, "tools") else ""
    if tools_field:
        # Normalize spacing (store as comma-separated string)
        tools_line = ", ".join([part.strip() for part in tools_field.split(",") if part.strip()])
        if tools_line:
            # Render as plain YAML string per 0102a
            frontmatter["tools"] = tools_line

    yaml_header = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip()

    parts: list[str] = []

    # Slim bootstrap (system_instructions -- now ~5-10 lines, Handover 0813)
    bootstrap = (template.system_instructions or "").strip()
    if bootstrap:
        parts.append(bootstrap)

    # Role identity prose (user_instructions -- Handover 0813: now included!)
    role_prose = (template.user_instructions or "").strip()
    if role_prose:
        parts.append(f"\n{role_prose}")

    # Behavioral Rules section
    rules = template.behavioral_rules or []
    if isinstance(rules, list) and rules:
        parts.append("\n## Behavioral Rules")
        parts.extend(f"- {r}" for r in rules)

    # Success Criteria section
    criteria = template.success_criteria or []
    if isinstance(criteria, list) and criteria:
        parts.append("\n## Success Criteria")
        parts.extend(f"- {c}" for c in criteria)

    body_text = "\n".join(parts).rstrip() + "\n"
    return f"---\n{yaml_header}\n---\n\n{body_text}"


def select_templates_for_packaging(templates: Iterable[AgentTemplate], max_count: int = 8) -> list[AgentTemplate]:
    """Select up to max_count templates using precedence rules.

    No role-based deduplication - users control which templates are enabled via UI toggle.
    The max_count cap (default 8) prevents context budget overflow.

    Precedence order:
      1) is_default templates first
      2) updated_at descending (most recent first)
      3) name ascending (stable fallback)
    """

    # Sort templates by precedence
    def sort_key(t: AgentTemplate):
        # For updated_at, None should be older than anything
        updated_ts = t.updated_at.isoformat() if getattr(t, "updated_at", None) else ""
        # We want updated_at desc, so invert by using reverse in sort later
        return (
            bool(getattr(t, "is_default", False)),  # True > False when reversed
            updated_ts,
            (t.name or ""),
        )

    sorted_list = sorted(templates, key=sort_key, reverse=True)

    # Return first max_count templates (no role deduplication)
    return sorted_list[:max_count]


def _build_body_parts(template: AgentTemplate) -> list[str]:
    """Build the shared body content parts used by all renderers.

    Returns list of text parts: system_instructions, user_instructions,
    behavioral_rules, success_criteria.
    """
    parts: list[str] = []

    bootstrap = (template.system_instructions or "").strip()
    if bootstrap:
        parts.append(bootstrap)

    role_prose = (template.user_instructions or "").strip()
    if role_prose:
        parts.append(f"\n{role_prose}")

    rules = template.behavioral_rules or []
    if isinstance(rules, list) and rules:
        parts.append("\n## Behavioral Rules")
        parts.extend(f"- {r}" for r in rules)

    criteria = template.success_criteria or []
    if isinstance(criteria, list) and criteria:
        parts.append("\n## Success Criteria")
        parts.extend(f"- {c}" for c in criteria)

    return parts


def render_generic_agent(template: AgentTemplate) -> str:
    """Render agent template to generic plaintext format.

    Used for Codex, Gemini, and other generic CLI tools.

    Args:
        template: AgentTemplate model instance

    Returns:
        Plaintext prompt without YAML frontmatter
    """
    parts = [
        f"# {template.name}",
        f"\nRole: {template.role}",
        f"\n{template.system_instructions or ''}",
    ]

    # Role identity prose (user_instructions -- Handover 0813)
    role_prose = (template.user_instructions or "").strip()
    if role_prose:
        parts.append(f"\n{role_prose}")

    # Add behavioral rules section if present
    rules = template.behavioral_rules or []
    if isinstance(rules, list) and rules:
        parts.append("\n## Behavioral Rules")
        parts.extend(f"- {r}" for r in rules)

    # Add success criteria section if present
    criteria = template.success_criteria or []
    if isinstance(criteria, list) and criteria:
        parts.append("\n## Success Criteria")
        parts.extend(f"- {c}" for c in criteria)

    return "\n".join(parts)


def render_gemini_agent(template: AgentTemplate) -> str:
    """Render a single AgentTemplate to Gemini CLI-compatible Markdown.

    Gemini CLI uses YAML frontmatter with different schema than Claude Code:
    - name, description, kind, model, max_turns, tools
    - kind must be 'local' (not 'agent') — matches built-in agent format
    - Tool names differ from Claude Code (run_shell_command not shell)
    - No color support (Gemini doesn't support agent colors)

    Handover 0836a: Multi-platform agent export.
    Handover 0836d: Fixed kind (local), tool names (run_shell_command), added
    file/search tools per Gemini CLI documentation.
    """
    description = template.description or (f"Subagent for {template.role}" if template.role else "Subagent")

    frontmatter: dict[str, object] = {
        "name": template.name,
        "description": description,
        "kind": "local",
        "model": "inherit",
        "max_turns": 50,
        "tools": [
            "run_shell_command",
            "read_file",
            "write_file",
            "glob",
            "grep_search",
            "list_directory",
            "read_many_files",
            "mcp_giljo-mcp_*",
        ],
    }

    yaml_header = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip()

    body_parts = _build_body_parts(template)
    body_text = "\n".join(body_parts).rstrip() + "\n"
    return f"---\n{yaml_header}\n---\n\n{body_text}"


def render_codex_agent(template: AgentTemplate) -> dict[str, object]:
    """Render a single AgentTemplate to Codex CLI structured data.

    Codex CLI agents are configured via TOML, not markdown files.
    Returns a dict that an LLM can use to write the config locally.

    Handover 0836a: Multi-platform agent export.
    """
    description = template.description or (f"Subagent for {template.role}" if template.role else "Subagent")

    body_parts = _build_body_parts(template)
    developer_instructions = "\n".join(body_parts).rstrip()

    return {
        "agent_name": template.name,
        "description": description,
        "role": template.role or "agent",
        "developer_instructions": developer_instructions,
        "suggested_model": "gpt-5.2-codex",
        "suggested_reasoning_effort": "medium",
    }


# TOML format reference string for Codex CLI agent configuration
CODEX_TOML_FORMAT_REFERENCE = """\
# Codex CLI agent configuration (add to ~/.codex/config.toml)
# Each agent is a [agents.<name>] section.
#
# [agents.implementer-frontend]
# model = "gpt-5.2-codex"
# reasoning_effort = "medium"
# instructions = \"\"\"
# <developer_instructions content here>
# \"\"\"
#
# Multiple agents can be defined in the same config.toml file.
# Existing sections not managed by GiljoAI should be preserved.
"""


def render_template(template: AgentTemplate) -> str:
    """Render template based on cli_tool field.

    Dispatcher function that routes to appropriate renderer:
    - 'claude' → render_claude_agent() (YAML format)
    - 'codex', 'gemini', 'generic' → render_generic_agent() (plaintext)
    - None or unknown → fallback to render_claude_agent()

    Args:
        template: AgentTemplate model instance

    Returns:
        Rendered content in appropriate format
    """
    cli_tool = (template.cli_tool or "").lower()

    if cli_tool == "claude":
        return render_claude_agent(template)
    if cli_tool in ("codex", "gemini", "generic"):
        return render_generic_agent(template)
    # Fallback to Claude format for backwards compatibility
    return render_claude_agent(template)


__all__ = [
    "CODEX_TOML_FORMAT_REFERENCE",
    "_slugify_filename",
    "hex_to_claude_color",
    "render_claude_agent",
    "render_codex_agent",
    "render_gemini_agent",
    "render_generic_agent",
    "render_template",
    "select_templates_for_packaging",
]
