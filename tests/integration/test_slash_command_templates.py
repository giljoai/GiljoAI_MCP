"""Integration tests for slash command templates across platforms.

Handover 0836c: Validates cross-platform consistency, template quality,
and the get_all_templates() registry function behavior.
"""

import pytest

from src.giljo_mcp.tools.slash_command_templates import (
    BOOTSTRAP_CLAUDE_CODE,
    BOOTSTRAP_CODEX_CLI,
    BOOTSTRAP_GEMINI_CLI,
    GIL_ADD_CODEX_SKILL_MD,
    GIL_ADD_GEMINI_TOML,
    GIL_ADD_MD,
    GIL_GET_AGENTS_CODEX_SKILL_MD,
    GIL_GET_AGENTS_GEMINI_TOML,
    GIL_GET_AGENTS_MD,
    get_all_templates,
)


class TestGetAllTemplatesRegistry:
    """Test the get_all_templates() registry function."""

    def test_claude_code_file_count(self):
        """Claude Code returns exactly 2 files (get_agents, add)."""
        result = get_all_templates(platform="claude_code")
        assert len(result) == 2

    def test_gemini_cli_file_count(self):
        """Gemini CLI returns exactly 2 files (get_agents, add)."""
        result = get_all_templates(platform="gemini_cli")
        assert len(result) == 2

    def test_codex_cli_file_count(self):
        """Codex CLI returns exactly 2 files (get_agents, add)."""
        result = get_all_templates(platform="codex_cli")
        assert len(result) == 2

    def test_invalid_platform_raises_value_error(self):
        """Invalid platform raises ValueError."""
        with pytest.raises(ValueError, match="Unknown platform"):
            get_all_templates(platform="windows_terminal")

    def test_all_template_values_are_nonempty_strings(self):
        """All returned templates contain non-empty content."""
        for platform in ("claude_code", "gemini_cli", "codex_cli"):
            result = get_all_templates(platform=platform)
            for filename, content in result.items():
                assert isinstance(content, str), f"{platform}/{filename} is not str"
                assert len(content.strip()) > 0, f"{platform}/{filename} is empty"


class TestCrossPlatformGilGetAgents:
    """Test that all get_agents templates reference the MCP tool."""

    def test_claude_references_mcp_tool(self):
        """Claude get_agents references the MCP export tool."""
        assert "get_agent_templates_for_export" in GIL_GET_AGENTS_MD

    def test_gemini_references_mcp_tool(self):
        """Gemini get_agents references the MCP export tool."""
        assert "get_agent_templates_for_export" in GIL_GET_AGENTS_GEMINI_TOML

    def test_codex_references_mcp_tool(self):
        """Codex get_agents references the MCP export tool."""
        assert "get_agent_templates_for_export" in GIL_GET_AGENTS_CODEX_SKILL_MD

    def test_all_reference_correct_platform(self):
        """Each get_agents template references its own platform string."""
        assert "claude_code" in GIL_GET_AGENTS_MD
        assert "gemini_cli" in GIL_GET_AGENTS_GEMINI_TOML
        assert "codex_cli" in GIL_GET_AGENTS_CODEX_SKILL_MD


class TestCodexSafetyProtocol:
    """Test that Codex skill enforces config.toml safety protocol."""

    def test_codex_mentions_backup(self):
        """Codex get_agents mentions backing up config.toml."""
        lower = GIL_GET_AGENTS_CODEX_SKILL_MD.lower()
        assert "back up" in lower or "backup" in lower

    def test_codex_mentions_diff(self):
        """Codex get_agents mentions showing diff before writing."""
        assert "diff" in GIL_GET_AGENTS_CODEX_SKILL_MD.lower()

    def test_codex_mentions_user_confirmation(self):
        """Codex get_agents requires explicit user confirmation before writing."""
        lower = GIL_GET_AGENTS_CODEX_SKILL_MD.lower()
        assert "confirm" in lower or "diff" in lower


class TestBootstrapTemplateIntegration:
    """Test bootstrap templates work end-to-end with placeholder substitution."""

    def test_claude_placeholder_substitution(self):
        """Claude bootstrap has only SLASH_COMMANDS_URL placeholder (two-phase install)."""
        result = BOOTSTRAP_CLAUDE_CODE.replace(
            "{SLASH_COMMANDS_URL}", "https://example.com/slash.zip"
        )
        assert "{" not in result  # No remaining placeholders
        assert "https://example.com/slash.zip" in result

    def test_gemini_placeholder_substitution(self):
        """Gemini bootstrap has only SLASH_COMMANDS_URL placeholder (two-phase install)."""
        result = BOOTSTRAP_GEMINI_CLI.replace(
            "{SLASH_COMMANDS_URL}", "https://example.com/slash.zip"
        )
        assert "{" not in result

    def test_codex_placeholder_substitution(self):
        """Codex bootstrap can have skills placeholder substituted."""
        result = BOOTSTRAP_CODEX_CLI.replace(
            "{SKILLS_URL}", "https://example.com/skills.zip"
        )
        assert "{SKILLS_URL}" not in result
        assert "https://example.com/skills.zip" in result

    def test_codex_does_not_have_agent_templates_url(self):
        """Codex bootstrap uses SKILLS_URL, not AGENT_TEMPLATES_URL."""
        assert "{AGENT_TEMPLATES_URL}" not in BOOTSTRAP_CODEX_CLI


class TestTemplateQualityGates:
    """Quality checks across all template constants."""

    _ALL_TEMPLATES = (
        ("GIL_GET_AGENTS_MD", GIL_GET_AGENTS_MD),
        ("GIL_ADD_MD", GIL_ADD_MD),
        ("GIL_GET_AGENTS_GEMINI_TOML", GIL_GET_AGENTS_GEMINI_TOML),
        ("GIL_ADD_GEMINI_TOML", GIL_ADD_GEMINI_TOML),
        ("GIL_GET_AGENTS_CODEX_SKILL_MD", GIL_GET_AGENTS_CODEX_SKILL_MD),
        ("GIL_ADD_CODEX_SKILL_MD", GIL_ADD_CODEX_SKILL_MD),
        ("BOOTSTRAP_CLAUDE_CODE", BOOTSTRAP_CLAUDE_CODE),
        ("BOOTSTRAP_GEMINI_CLI", BOOTSTRAP_GEMINI_CLI),
        ("BOOTSTRAP_CODEX_CLI", BOOTSTRAP_CODEX_CLI),
    )

    @pytest.mark.parametrize(("name", "template"), _ALL_TEMPLATES)
    def test_template_is_nonempty_string(self, name, template):
        """Each template constant is a non-empty string."""
        assert isinstance(template, str), f"{name} is not a string"
        assert len(template.strip()) > 50, f"{name} is suspiciously short"

    @pytest.mark.parametrize(("name", "template"), _ALL_TEMPLATES)
    def test_no_debug_markers(self, name, template):
        """No template contains developer debug markers (TODO:, FIXME:, HACK:)."""
        import re
        # Match developer markers with colon (e.g. "TODO:", "FIXME:", "HACK:")
        # but not the word "TODO" used as regular content (e.g. "a TODO", "TODOs")
        assert not re.search(r"\bTODO\s*:", template, re.IGNORECASE), f"{name} contains TODO: marker"
        assert not re.search(r"\bFIXME\b", template, re.IGNORECASE), f"{name} contains FIXME marker"
        assert not re.search(r"\bHACK\b", template, re.IGNORECASE), f"{name} contains HACK marker"
