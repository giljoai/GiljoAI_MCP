# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Integration tests for the multi-platform export pipeline.

Handover 0836c: Tests the full export pipeline including slash command
templates, agent template assembler, and backward compatibility.

INF-6049a: the per-platform slash fleet (gil_add / gil_get / gil_chain /
gil_get_reference / gil_get_agents) collapsed to ONE thin ``/giljo`` command
whose body calls ``get_giljo_guide`` (bare -- BE-9012d F1: this body renders to
Codex/Gemini/Desktop too, where the Claude Code ``mcp__giljo_mcp__`` prefix is
wrong). These tests lock the new single-file-per-platform export surface (the
old per-command body tests were removed with the commands they guarded).
"""

from giljo_mcp.models import AgentTemplate
from giljo_mcp.tools.agent_template_assembler import AgentTemplateAssembler
from giljo_mcp.tools.slash_command_templates import (
    BOOTSTRAP_ANTIGRAVITY_CLI,
    BOOTSTRAP_CLAUDE_CODE,
    BOOTSTRAP_CODEX_CLI,
    BOOTSTRAP_GEMINI_CLI,
    BOOTSTRAP_GENERIC,
    SKILLS_VERSION,
    get_all_templates,
)


# The one file each platform ships, post-collapse.
_EXPECTED_FILE = {
    "claude_code": "giljo.md",
    "gemini_cli": "giljo.toml",
    "codex_cli": "giljo/SKILL.md",
    "antigravity_cli": "giljo/SKILL.md",
    "generic": "giljo_reference.md",
}


def _make_template(**overrides) -> AgentTemplate:
    """Create a test AgentTemplate with sensible defaults."""
    defaults = {
        "name": "implementer-frontend",
        "role": "implementer",
        "cli_tool": "claude",
        "description": "Implements frontend features",
        "system_instructions": "You are a frontend implementer.",
        "user_instructions": "Focus on component development.",
        "model": "sonnet",
        "background_color": "#3498DB",
        "behavioral_rules": ["Follow patterns"],
        "success_criteria": ["Tests pass"],
    }
    defaults.update(overrides)
    return AgentTemplate(**defaults)


class TestSlashCommandPlatformAwareness:
    """get_all_templates returns exactly ONE /giljo file per platform (INF-6049a)."""

    def test_every_platform_returns_exactly_one_file(self):
        for platform, expected_name in _EXPECTED_FILE.items():
            result = get_all_templates(platform=platform)
            assert list(result.keys()) == [expected_name], (
                f"{platform} must export exactly one file {expected_name!r}, got {list(result)}"
            )

    def test_the_one_file_calls_the_guide_tool(self):
        """The shipped body's whole job is to call get_giljo_guide and follow it.

        BE-9012d (F1): the tool name is bare (this body renders to Codex/Gemini/
        Desktop too, where the Claude Code mcp__giljo_mcp__ prefix is wrong).
        """
        for platform in _EXPECTED_FILE:
            (body,) = get_all_templates(platform=platform).values()
            assert "get_giljo_guide" in body, f"{platform} body must call get_giljo_guide"
            assert "mcp__giljo_mcp__get_giljo_guide" not in body, f"{platform} tool call must be bare, not prefixed"
            assert body.strip(), f"{platform} body is empty"

    def test_the_one_file_is_bundle_version_stamped(self):
        """Every exported file carries the current SKILLS_VERSION (drift-detection)."""
        for platform in _EXPECTED_FILE:
            (body,) = get_all_templates(platform=platform).values()
            assert SKILLS_VERSION in body, f"{platform} body missing bundle_version {SKILLS_VERSION}"

    def test_no_legacy_gil_commands_are_exported(self):
        """The collapsed gil_add / gil_get / gil_chain / gil_get_agents must be gone."""
        for platform in _EXPECTED_FILE:
            result = get_all_templates(platform=platform)
            for fname in result:
                for legacy in ("gil_add", "gil-add", "gil_get", "gil-get", "gil_chain", "gil-chain"):
                    assert legacy not in fname, f"{platform} still exports legacy file {fname}"

    def test_default_returns_claude_format(self):
        """Default (no platform) returns Claude format for backward compatibility."""
        assert get_all_templates() == get_all_templates(platform="claude_code")


class TestBootstrapPromptTemplates:
    """Bootstrap prompts keep their URL placeholders and advertise only /giljo."""

    def test_url_placeholders_preserved(self):
        assert "{SLASH_COMMANDS_URL}" in BOOTSTRAP_CLAUDE_CODE
        assert "{AGENT_TEMPLATES_URL}" not in BOOTSTRAP_CLAUDE_CODE
        assert "{SLASH_COMMANDS_URL}" in BOOTSTRAP_GEMINI_CLI
        assert "{SKILLS_URL}" in BOOTSTRAP_CODEX_CLI

    def test_bootstraps_advertise_only_the_giljo_command(self):
        for bootstrap in (BOOTSTRAP_CLAUDE_CODE, BOOTSTRAP_GEMINI_CLI, BOOTSTRAP_CODEX_CLI):
            assert "giljo" in bootstrap
            for legacy in ("gil_get_agents", "gil-get-agents", "gil_add", "gil-add", "/gil_get", "$gil-get"):
                assert legacy not in bootstrap, f"bootstrap still advertises deleted command {legacy}"

    def test_bootstraps_route_agent_install_through_giljo_setup(self):
        """Agent-template refresh now folds into giljo_setup (no separate command)."""
        for bootstrap in (BOOTSTRAP_CLAUDE_CODE, BOOTSTRAP_GEMINI_CLI, BOOTSTRAP_CODEX_CLI, BOOTSTRAP_ANTIGRAVITY_CLI):
            assert "giljo_setup" in bootstrap

    def test_generic_points_at_the_guide_tool(self):
        assert "get_giljo_guide" in BOOTSTRAP_GENERIC

    def test_all_bootstraps_mention_restart_and_expiry(self):
        for bootstrap in (BOOTSTRAP_CLAUDE_CODE, BOOTSTRAP_GEMINI_CLI, BOOTSTRAP_CODEX_CLI):
            assert "restart" in bootstrap.lower()
            assert "expire" in bootstrap.lower()


class TestAssemblerBackwardCompatibility:
    """Test assembler backward compatibility with existing flows."""

    def setup_method(self):
        self.assembler = AgentTemplateAssembler()
        self.templates = [
            _make_template(name="analyzer-code", role="analyzer"),
        ]

    def test_claude_code_default_produces_md_filenames(self):
        """Claude Code assembler produces .md filenames."""
        result = self.assembler.assemble(self.templates, "claude_code")
        for agent in result["agents"]:
            assert agent["filename"].endswith(".md")

    def test_gemini_produces_md_filenames(self):
        """Gemini assembler produces .md filenames."""
        result = self.assembler.assemble(self.templates, "gemini_cli")
        for agent in result["agents"]:
            assert agent["filename"].endswith(".md")

    def test_codex_has_no_filename_key(self):
        """Codex assembler uses agent_name, not filename."""
        result = self.assembler.assemble(self.templates, "codex_cli")
        for agent in result["agents"]:
            assert "filename" not in agent
            assert "agent_name" in agent

    def test_install_paths_per_platform(self):
        """Each platform has correct install paths."""
        claude = self.assembler.assemble(self.templates, "claude_code")
        assert ".claude/agents/" in claude["install_paths"]["project"]

        gemini = self.assembler.assemble(self.templates, "gemini_cli")
        assert ".gemini/agents/" in gemini["install_paths"]["project"]

        codex = self.assembler.assemble(self.templates, "codex_cli")
        assert ".codex/agents/" in codex["install_paths"]["agent_files"]
