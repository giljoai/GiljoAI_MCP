"""
AgentTemplateAssembler — multi-platform template export (Handover 0836a).

Takes platform-neutral AgentTemplate rows from the database and produces
correctly formatted output for Claude Code, Codex CLI, or Gemini CLI.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.template_renderer import (
    CODEX_TOML_FORMAT_REFERENCE,
    _slugify_filename,
    hex_to_claude_color,
    render_claude_agent,
    render_codex_agent,
    render_gemini_agent,
)


if TYPE_CHECKING:
    from src.giljo_mcp.models import AgentTemplate

logger = logging.getLogger(__name__)

VALID_PLATFORMS = frozenset({"claude_code", "codex_cli", "gemini_cli"})

# Install path metadata per platform
_INSTALL_PATHS: dict[str, dict[str, str]] = {
    "claude_code": {
        "project": ".claude/agents/",
        "user": "~/.claude/agents/",
    },
    "gemini_cli": {
        "project": ".gemini/agents/",
        "user": "~/.gemini/agents/",
    },
    "codex_cli": {
        "agent_files": "~/.codex/agents/",
        "config_file": "~/.codex/config.toml",
    },
}


class AgentTemplateAssembler:
    """Assembles agent templates into platform-specific export format."""

    def assemble(
        self,
        templates: list[AgentTemplate],
        platform: str,
    ) -> dict:
        """Assemble templates into export response for the given platform.

        Args:
            templates: Pre-selected list of AgentTemplate model instances
                       (already filtered and capped by select_templates_for_packaging).
            platform: Target platform — 'claude_code', 'codex_cli', or 'gemini_cli'.

        Returns:
            Dict matching the API contract defined in handover 0836.

        Raises:
            ValidationError: If platform is not one of the supported values.
        """
        if platform not in VALID_PLATFORMS:
            raise ValidationError(
                f"Invalid platform '{platform}'. Must be one of: {', '.join(sorted(VALID_PLATFORMS))}"
            )

        if platform == "claude_code":
            return self._assemble_claude(templates)
        if platform == "gemini_cli":
            return self._assemble_gemini(templates)
        return self._assemble_codex(templates)

    # ------------------------------------------------------------------
    # Claude Code — pre-assembled markdown files with YAML frontmatter
    # ------------------------------------------------------------------

    def _assemble_claude(self, templates: list[AgentTemplate]) -> dict:
        agents = []
        for t in templates:
            content = render_claude_agent(t)
            color = None
            if hasattr(t, "background_color") and t.background_color:
                color = hex_to_claude_color(t.background_color)

            agents.append(
                {
                    "filename": f"{_slugify_filename(t.name)}.md",
                    "content": content,
                    "role": t.role or "agent",
                    "color": color,
                }
            )

        return {
            "platform": "claude_code",
            "agents": agents,
            "install_paths": _INSTALL_PATHS["claude_code"],
            "template_count": len(agents),
            "format_version": "1.0",
        }

    # ------------------------------------------------------------------
    # Gemini CLI — pre-assembled markdown files (different frontmatter)
    # ------------------------------------------------------------------

    def _assemble_gemini(self, templates: list[AgentTemplate]) -> dict:
        agents = []
        for t in templates:
            content = render_gemini_agent(t)
            agents.append(
                {
                    "filename": f"{_slugify_filename(t.name)}.md",
                    "content": content,
                    "role": t.role or "agent",
                }
            )

        return {
            "platform": "gemini_cli",
            "agents": agents,
            "install_paths": _INSTALL_PATHS["gemini_cli"],
            "template_count": len(agents),
            "format_version": "1.0",
        }

    # ------------------------------------------------------------------
    # Codex CLI — structured data (LLM writes TOML config locally)
    # ------------------------------------------------------------------

    def _assemble_codex(self, templates: list[AgentTemplate]) -> dict:
        agents = []
        for t in templates:
            agent_data = render_codex_agent(t)
            agents.append(agent_data)

        return {
            "platform": "codex_cli",
            "agents": agents,
            "install_paths": _INSTALL_PATHS["codex_cli"],
            "toml_format_reference": CODEX_TOML_FORMAT_REFERENCE,
            "template_count": len(agents),
            "format_version": "1.0",
        }
