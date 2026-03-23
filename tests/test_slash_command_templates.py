"""
Tests for slash command templates module.

Validates template constants and the get_all_templates() function
across Claude Code, Gemini CLI, and Codex CLI platforms.
"""

import pytest

from src.giljo_mcp.tools.slash_command_templates import (
    GIL_GET_AGENTS_MD,
    GIL_GET_CLAUDE_AGENTS_MD,
    GIL_ADD_MD,
    GIL_GET_AGENTS_GEMINI_TOML,
    GIL_ADD_GEMINI_TOML,
    GIL_GET_AGENTS_CODEX_SKILL_MD,
    GIL_ADD_CODEX_SKILL_MD,
    BOOTSTRAP_CLAUDE_CODE,
    BOOTSTRAP_GEMINI_CLI,
    BOOTSTRAP_CODEX_CLI,
    get_all_templates,
)


class TestGetAllTemplates:
    """Tests for the get_all_templates() function."""

    def test_get_all_templates_default_returns_claude_code(self):
        """Calling with no args returns Claude Code templates."""
        result = get_all_templates()
        assert "gil_get_agents.md" in result
        assert "gil_get_claude_agents.md" in result
        assert "gil_add.md" in result

    def test_get_all_templates_claude_code_explicit(self):
        """Calling with platform='claude_code' returns same as default."""
        default_result = get_all_templates()
        explicit_result = get_all_templates(platform="claude_code")
        assert default_result == explicit_result

    def test_get_all_templates_gemini_cli(self):
        """Calling with platform='gemini_cli' returns TOML templates."""
        result = get_all_templates(platform="gemini_cli")
        assert "gil_get_agents.toml" in result
        assert "gil_add.toml" in result

    def test_get_all_templates_codex_cli(self):
        """Calling with platform='codex_cli' returns SKILL.md templates."""
        result = get_all_templates(platform="codex_cli")
        assert "gil-get-agents/SKILL.md" in result
        assert "gil-add/SKILL.md" in result

    def test_get_all_templates_invalid_platform(self):
        """Calling with unknown platform raises ValueError."""
        with pytest.raises(ValueError):
            get_all_templates(platform="unknown_platform")


class TestClaudeCodeTemplates:
    """Tests for Claude Code template constants."""

    def test_claude_get_agents_template_has_correct_frontmatter(self):
        """GIL_GET_AGENTS_MD contains expected YAML frontmatter fields."""
        assert "name: gil_get_agents" in GIL_GET_AGENTS_MD
        assert "allowed-tools:" in GIL_GET_AGENTS_MD

    def test_deprecated_claude_agents_has_migration_notice(self):
        """GIL_GET_CLAUDE_AGENTS_MD starts with deprecation notice."""
        stripped = GIL_GET_CLAUDE_AGENTS_MD.lstrip()
        assert stripped.startswith("NOTE: This command has been renamed")


class TestGeminiTemplates:
    """Tests for Gemini CLI template constants."""

    def test_gemini_get_agents_is_toml_format(self):
        """GIL_GET_AGENTS_GEMINI_TOML contains TOML key-value pairs."""
        assert "description =" in GIL_GET_AGENTS_GEMINI_TOML
        assert "prompt =" in GIL_GET_AGENTS_GEMINI_TOML

    def test_gemini_gil_add_has_same_modes_as_claude(self):
        """GIL_ADD_GEMINI_TOML mentions all three operation modes."""
        assert "Direct Task Mode" in GIL_ADD_GEMINI_TOML
        assert "Direct Project Mode" in GIL_ADD_GEMINI_TOML
        assert "Interactive Mode" in GIL_ADD_GEMINI_TOML


class TestCodexTemplates:
    """Tests for Codex CLI template constants."""

    def test_codex_get_agents_has_config_toml_safety(self):
        """GIL_GET_AGENTS_CODEX_SKILL_MD contains config.toml safety guidance."""
        assert "config.toml" in GIL_GET_AGENTS_CODEX_SKILL_MD
        assert "back up" in GIL_GET_AGENTS_CODEX_SKILL_MD
        assert "diff" in GIL_GET_AGENTS_CODEX_SKILL_MD

    def test_codex_gil_add_has_same_modes_as_claude(self):
        """GIL_ADD_CODEX_SKILL_MD mentions all three operation modes."""
        assert "Direct Task Mode" in GIL_ADD_CODEX_SKILL_MD
        assert "Direct Project Mode" in GIL_ADD_CODEX_SKILL_MD
        assert "Interactive Mode" in GIL_ADD_CODEX_SKILL_MD


class TestBootstrapTemplates:
    """Tests for bootstrap template constants."""

    def test_bootstrap_templates_have_placeholders(self):
        """Each bootstrap template contains placeholder markers."""
        assert "{" in BOOTSTRAP_CLAUDE_CODE
        assert "{" in BOOTSTRAP_GEMINI_CLI
        assert "{" in BOOTSTRAP_CODEX_CLI


class TestTemplateQuality:
    """General quality checks across all template constants."""

    def test_all_templates_are_non_empty_strings(self):
        """All template constants are non-empty strings."""
        templates = [
            GIL_GET_AGENTS_MD,
            GIL_GET_CLAUDE_AGENTS_MD,
            GIL_ADD_MD,
            GIL_GET_AGENTS_GEMINI_TOML,
            GIL_ADD_GEMINI_TOML,
            GIL_GET_AGENTS_CODEX_SKILL_MD,
            GIL_ADD_CODEX_SKILL_MD,
            BOOTSTRAP_CLAUDE_CODE,
            BOOTSTRAP_GEMINI_CLI,
            BOOTSTRAP_CODEX_CLI,
        ]
        for template in templates:
            assert isinstance(template, str), f"Expected str, got {type(template)}"
            assert len(template.strip()) > 0, "Template must not be empty or whitespace-only"
