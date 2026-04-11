# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for slash command templates module.

Validates template constants and the get_all_templates() function
across Claude Code, Gemini CLI, and Codex CLI platforms.
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


class TestGetAllTemplates:
    """Tests for the get_all_templates() function."""

    def test_get_all_templates_default_returns_claude_code(self):
        """Calling with no args returns Claude Code templates."""
        result = get_all_templates()
        assert "gil_get_agents.md" in result
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
        with pytest.raises(ValueError, match="Unknown platform"):
            get_all_templates(platform="unknown_platform")


class TestClaudeCodeTemplates:
    """Tests for Claude Code template constants."""

    def test_claude_get_agents_template_has_correct_frontmatter(self):
        """GIL_GET_AGENTS_MD contains expected YAML frontmatter fields."""
        assert "name: gil_get_agents" in GIL_GET_AGENTS_MD
        assert "allowed-tools:" in GIL_GET_AGENTS_MD


class TestGeminiTemplates:
    """Tests for Gemini CLI template constants."""

    def test_gemini_get_agents_is_toml_format(self):
        """GIL_GET_AGENTS_GEMINI_TOML contains TOML key-value pairs."""
        assert "description =" in GIL_GET_AGENTS_GEMINI_TOML
        assert "prompt =" in GIL_GET_AGENTS_GEMINI_TOML

    def test_gemini_gil_add_has_same_modes_as_claude(self):
        """GIL_ADD_GEMINI_TOML mentions direct and interactive modes."""
        assert "--task" in GIL_ADD_GEMINI_TOML
        assert "--project" in GIL_ADD_GEMINI_TOML
        assert "Interactive" in GIL_ADD_GEMINI_TOML


class TestCodexTemplates:
    """Tests for Codex CLI template constants."""

    def test_codex_get_agents_has_config_toml_safety(self):
        """GIL_GET_AGENTS_CODEX_SKILL_MD contains config.toml safety guidance."""
        assert "config.toml" in GIL_GET_AGENTS_CODEX_SKILL_MD
        assert "backup" in GIL_GET_AGENTS_CODEX_SKILL_MD
        assert "diff" in GIL_GET_AGENTS_CODEX_SKILL_MD

    def test_codex_get_agents_requires_gil_prefix(self):
        """Codex skill must instruct agents to use gil- prefix (avoids built-in role shadowing)."""
        assert "gil-" in GIL_GET_AGENTS_CODEX_SKILL_MD
        assert "prefix" in GIL_GET_AGENTS_CODEX_SKILL_MD.lower()
        assert "shadow" in GIL_GET_AGENTS_CODEX_SKILL_MD.lower() or "built-in" in GIL_GET_AGENTS_CODEX_SKILL_MD.lower()

    def test_codex_get_agents_uses_relative_config_paths(self):
        """Codex skill must specify relative config_file paths (tilde paths fail in Codex CLI)."""
        assert "agents/gil-" in GIL_GET_AGENTS_CODEX_SKILL_MD
        assert "RELATIVE" in GIL_GET_AGENTS_CODEX_SKILL_MD

    def test_codex_get_agents_has_verification_step(self):
        """Codex skill includes a verification step to confirm custom templates are loaded."""
        assert "Verification" in GIL_GET_AGENTS_CODEX_SKILL_MD
        assert "mcp__giljo_mcp__health_check" in GIL_GET_AGENTS_CODEX_SKILL_MD

    def test_codex_gil_add_has_same_modes_as_claude(self):
        """GIL_ADD_CODEX_SKILL_MD mentions direct and interactive modes."""
        assert "--task" in GIL_ADD_CODEX_SKILL_MD
        assert "--project" in GIL_ADD_CODEX_SKILL_MD
        assert "Interactive" in GIL_ADD_CODEX_SKILL_MD


class TestProjectTypeParameter:
    """Tests for project_type parameter support in /gil_add templates (0837c)."""

    def test_claude_gil_add_has_type_flag(self):
        """Claude /gil_add template documents --type flag for projects."""
        assert "--type" in GIL_ADD_MD

    def test_claude_gil_add_has_project_type_mcp_param(self):
        """Claude /gil_add template references project_type MCP parameter."""
        assert "project_type" in GIL_ADD_MD

    def test_gemini_gil_add_has_type_flag(self):
        """Gemini /gil_add template documents --type flag for projects."""
        assert "--type" in GIL_ADD_GEMINI_TOML

    def test_gemini_gil_add_has_project_type_mcp_param(self):
        """Gemini /gil_add template references project_type MCP parameter."""
        assert "project_type" in GIL_ADD_GEMINI_TOML

    def test_codex_gil_add_has_type_flag(self):
        """Codex /gil_add template documents --type flag for projects."""
        assert "--type" in GIL_ADD_CODEX_SKILL_MD

    def test_codex_gil_add_has_project_type_mcp_param(self):
        """Codex /gil_add template references project_type MCP parameter."""
        assert "project_type" in GIL_ADD_CODEX_SKILL_MD

    def test_all_templates_mention_project_type_is_optional(self):
        """All templates note that project_type is optional."""
        for name, template in [
            ("Claude", GIL_ADD_MD),
            ("Gemini", GIL_ADD_GEMINI_TOML),
            ("Codex", GIL_ADD_CODEX_SKILL_MD),
        ]:
            assert "optional" in template.lower(), f"{name} template should mention project_type is optional"


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
