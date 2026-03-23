"""Integration tests for the multi-platform export pipeline.

Handover 0836c: Tests the full export pipeline including
slash command templates, agent template assembler, and
backward compatibility with existing Claude-only flows.
"""

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.tools.agent_template_assembler import AgentTemplateAssembler
from src.giljo_mcp.tools.slash_command_templates import (
    BOOTSTRAP_CLAUDE_CODE,
    BOOTSTRAP_CODEX_CLI,
    BOOTSTRAP_GEMINI_CLI,
    get_all_templates,
)


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
    """Test that get_all_templates returns correct files per platform."""

    def test_claude_returns_md_files(self):
        """Claude Code templates are .md files."""
        result = get_all_templates(platform="claude_code")
        for filename in result:
            assert filename.endswith(".md"), f"Expected .md, got {filename}"

    def test_gemini_returns_toml_files(self):
        """Gemini CLI templates are .toml files."""
        result = get_all_templates(platform="gemini_cli")
        for filename in result:
            assert filename.endswith(".toml"), f"Expected .toml, got {filename}"

    def test_codex_returns_skill_md_files(self):
        """Codex CLI templates are SKILL.md files in subdirectories."""
        result = get_all_templates(platform="codex_cli")
        for filename in result:
            assert filename.endswith("SKILL.md"), f"Expected SKILL.md, got {filename}"

    def test_default_returns_claude_format(self):
        """Default (no platform) returns Claude format for backward compatibility."""
        default = get_all_templates()
        explicit = get_all_templates(platform="claude_code")
        assert default == explicit

    def test_all_platforms_have_get_agents_and_add(self):
        """Each platform has both a get_agents and gil_add command."""
        for platform in ("claude_code", "gemini_cli", "codex_cli"):
            result = get_all_templates(platform=platform)
            filenames = list(result.keys())
            has_get_agents = any("get_agents" in f or "get-agents" in f for f in filenames)
            has_add = any("add" in f for f in filenames)
            assert has_get_agents, f"{platform} missing get_agents command"
            assert has_add, f"{platform} missing gil_add command"


class TestGilAddConsistency:
    """Test that /gil_add has the same modes across all platforms."""

    def test_all_platforms_have_three_modes(self):
        """Each platform's gil_add mentions task, project, and interactive modes."""
        for platform in ("claude_code", "gemini_cli", "codex_cli"):
            result = get_all_templates(platform=platform)
            # Find the add template
            add_content = None
            for filename, content in result.items():
                if "add" in filename:
                    add_content = content
                    break
            assert add_content is not None, f"{platform} missing gil_add"
            assert "Direct Task Mode" in add_content, f"{platform} missing task mode"
            assert "Direct Project Mode" in add_content, f"{platform} missing project mode"
            assert "Interactive Mode" in add_content, f"{platform} missing interactive mode"


class TestDeprecatedAlias:
    """Test the deprecated /gil_get_claude_agents alias."""

    def test_deprecated_alias_included_in_claude_templates(self):
        """Claude platform still includes the deprecated alias."""
        result = get_all_templates(platform="claude_code")
        assert "gil_get_claude_agents.md" in result

    def test_deprecated_alias_has_migration_notice(self):
        """Deprecated alias starts with migration notice."""
        result = get_all_templates(platform="claude_code")
        content = result["gil_get_claude_agents.md"]
        assert "renamed" in content.lower()

    def test_gemini_has_no_deprecated_alias(self):
        """Gemini does not include the deprecated Claude-specific alias."""
        result = get_all_templates(platform="gemini_cli")
        assert not any("claude_agents" in f for f in result)

    def test_codex_has_no_deprecated_alias(self):
        """Codex does not include the deprecated Claude-specific alias."""
        result = get_all_templates(platform="codex_cli")
        assert not any("claude_agents" in f for f in result)


class TestBootstrapPromptTemplates:
    """Test bootstrap prompt templates have correct placeholders."""

    def test_claude_has_both_url_placeholders(self):
        """Claude bootstrap has SLASH_COMMANDS_URL and AGENT_TEMPLATES_URL."""
        assert "{SLASH_COMMANDS_URL}" in BOOTSTRAP_CLAUDE_CODE
        assert "{AGENT_TEMPLATES_URL}" in BOOTSTRAP_CLAUDE_CODE

    def test_gemini_has_both_url_placeholders(self):
        """Gemini bootstrap has SLASH_COMMANDS_URL and AGENT_TEMPLATES_URL."""
        assert "{SLASH_COMMANDS_URL}" in BOOTSTRAP_GEMINI_CLI
        assert "{AGENT_TEMPLATES_URL}" in BOOTSTRAP_GEMINI_CLI

    def test_codex_has_skills_url_placeholder(self):
        """Codex bootstrap has SKILLS_URL placeholder (not agent templates)."""
        assert "{SKILLS_URL}" in BOOTSTRAP_CODEX_CLI

    def test_codex_references_interactive_install(self):
        """Codex bootstrap mentions running the skill for agent install."""
        assert "gil-get-agents" in BOOTSTRAP_CODEX_CLI

    def test_all_bootstraps_mention_restart(self):
        """All bootstrap prompts mention restarting the CLI tool."""
        assert "restart" in BOOTSTRAP_CLAUDE_CODE.lower()
        assert "restart" in BOOTSTRAP_GEMINI_CLI.lower()
        assert "restart" in BOOTSTRAP_CODEX_CLI.lower()

    def test_all_bootstraps_mention_expiry(self):
        """All bootstrap prompts mention link expiry."""
        assert "expire" in BOOTSTRAP_CLAUDE_CODE.lower()
        assert "expire" in BOOTSTRAP_GEMINI_CLI.lower()
        assert "expire" in BOOTSTRAP_CODEX_CLI.lower()


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
