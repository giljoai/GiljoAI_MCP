"""
Unit tests for slash command templates and setup_slash_commands MCP tool.

These cover:
- Template YAML frontmatter validity (Claude Code slash commands)
- Supported template set for downloads (/api/download/slash-commands.zip)
- setup_slash_commands() token-first download workflow
"""

import pytest
import yaml

from src.giljo_mcp.tools.slash_command_templates import (
    GIL_ACTIVATE_MD,
    GIL_GET_CLAUDE_AGENTS_MD,
    GIL_HANDOVER_MD,
    GIL_LAUNCH_MD,
    get_all_templates,
)
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


@pytest.fixture
def tool_accessor(db_manager, tenant_manager):
    """Create tool accessor for testing with an active tenant."""
    # TenantManager requires tk_ + 32 alphanumeric chars
    tenant_manager.set_current_tenant("tk_" + ("A" * 32))
    return ToolAccessor(db_manager, tenant_manager)


class TestSlashCommandTemplates:
    """Validate shipped slash command templates."""

    def test_template_constants_exist(self):
        assert len(GIL_GET_CLAUDE_AGENTS_MD) > 0
        assert len(GIL_ACTIVATE_MD) > 0
        assert len(GIL_LAUNCH_MD) > 0
        assert len(GIL_HANDOVER_MD) > 0

    def test_get_all_templates_returns_supported_set(self):
        templates = get_all_templates()
        assert set(templates.keys()) == {
            "gil_get_claude_agents.md",
            "gil_activate.md",
            "gil_launch.md",
            "gil_handover.md",
        }

    def test_templates_have_valid_yaml_frontmatter(self):
        templates = get_all_templates()

        for filename, content in templates.items():
            assert content.startswith("---\n"), f"{filename} missing opening YAML delimiter"
            assert "\n---\n" in content, f"{filename} missing closing YAML delimiter"

            parts = content.split("---\n", 2)
            assert len(parts) >= 3, f"{filename} invalid YAML frontmatter structure"

            frontmatter = yaml.safe_load(parts[1])
            assert frontmatter is not None, f"{filename} YAML frontmatter is empty"
            assert "name" in frontmatter, f"{filename} missing 'name' in frontmatter"
            assert "description" in frontmatter, f"{filename} missing 'description' in frontmatter"

    def test_gil_get_claude_agents_references_download_tool(self):
        assert "mcp__giljo-mcp__get_agent_download_url" in GIL_GET_CLAUDE_AGENTS_MD

    def test_gil_handover_mentions_succession_tool(self):
        assert "create_successor_orchestrator" in GIL_HANDOVER_MD


class TestSetupSlashCommandsTool:
    """Validate setup_slash_commands() token-first download flow."""

    @pytest.mark.asyncio
    async def test_setup_slash_commands_requires_api_key(self, tool_accessor):
        result = await tool_accessor.setup_slash_commands(_api_key=None, _server_url="http://localhost:7272")
        assert result["success"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_setup_slash_commands_returns_download_url(self, tool_accessor):
        result = await tool_accessor.setup_slash_commands(_api_key="test-api-key", _server_url="http://localhost:7272")

        assert result["success"] is True
        assert "download_url" in result
        assert result["download_url"].startswith("http://localhost:7272/api/download/temp/")
        assert result["download_url"].endswith("/slash_commands.zip")
        assert "bash_command" in result
        assert "curl -o /tmp/slash_commands.zip" in result["bash_command"]
