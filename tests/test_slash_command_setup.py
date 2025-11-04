"""
Unit tests for slash command setup MCP tool (Handover 0093)
Tests the setup_slash_commands MCP tool that returns markdown files for local installation
"""
import pytest
import yaml
from typing import Any

from src.giljo_mcp.tools.tool_accessor import ToolAccessor
from src.giljo_mcp.tools.slash_command_templates import (
    GIL_IMPORT_PRODUCTAGENTS_MD,
    GIL_IMPORT_PERSONALAGENTS_MD,
    GIL_HANDOVER_MD,
    get_all_templates,
)


@pytest.fixture
def tool_accessor(db_manager, tenant_manager):
    """Create tool accessor for testing"""
    return ToolAccessor(db_manager, tenant_manager)


class TestSlashCommandTemplates:
    """Test slash command template constants"""

    def test_gil_import_productagents_template_exists(self):
        """Test that gil_import_productagents template is defined"""
        assert GIL_IMPORT_PRODUCTAGENTS_MD is not None
        assert len(GIL_IMPORT_PRODUCTAGENTS_MD) > 0

    def test_gil_import_personalagents_template_exists(self):
        """Test that gil_import_personalagents template is defined"""
        assert GIL_IMPORT_PERSONALAGENTS_MD is not None
        assert len(GIL_IMPORT_PERSONALAGENTS_MD) > 0

    def test_gil_handover_template_exists(self):
        """Test that gil_handover template is defined"""
        assert GIL_HANDOVER_MD is not None
        assert len(GIL_HANDOVER_MD) > 0

    def test_get_all_templates_returns_three_files(self):
        """Test that get_all_templates returns exactly 3 files"""
        templates = get_all_templates()
        assert len(templates) == 3
        assert "gil_import_productagents.md" in templates
        assert "gil_import_personalagents.md" in templates
        assert "gil_handover.md" in templates

    def test_templates_have_yaml_frontmatter(self):
        """Test that all templates have valid YAML frontmatter"""
        templates = get_all_templates()

        for filename, content in templates.items():
            # Check starts with YAML delimiter
            assert content.startswith("---\n"), f"{filename} missing opening YAML delimiter"

            # Check has closing delimiter
            assert "\n---\n" in content, f"{filename} missing closing YAML delimiter"

            # Extract frontmatter
            parts = content.split("---\n", 2)
            assert len(parts) >= 3, f"{filename} invalid YAML frontmatter structure"

            frontmatter_text = parts[1]

            # Parse YAML to verify validity
            frontmatter = yaml.safe_load(frontmatter_text)
            assert frontmatter is not None, f"{filename} YAML frontmatter is empty"
            assert "name" in frontmatter, f"{filename} missing 'name' in frontmatter"
            assert "description" in frontmatter, f"{filename} missing 'description' in frontmatter"

    def test_template_names_match_filenames(self):
        """Test that template name fields match expected command names"""
        templates = get_all_templates()

        # Expected mapping: filename -> command name
        expected_names = {
            "gil_import_productagents.md": "gil_import_productagents",
            "gil_import_personalagents.md": "gil_import_personalagents",
            "gil_handover.md": "gil_handover",
        }

        for filename, content in templates.items():
            # Extract frontmatter
            parts = content.split("---\n", 2)
            frontmatter = yaml.safe_load(parts[1])

            # Verify name matches
            assert frontmatter["name"] == expected_names[filename], \
                f"{filename} has incorrect name: {frontmatter['name']} (expected {expected_names[filename]})"

    def test_template_descriptions_not_empty(self):
        """Test that all templates have non-empty descriptions"""
        templates = get_all_templates()

        for filename, content in templates.items():
            parts = content.split("---\n", 2)
            frontmatter = yaml.safe_load(parts[1])

            description = frontmatter.get("description", "")
            assert len(description) > 0, f"{filename} has empty description"
            assert len(description) > 10, f"{filename} description too short: {description}"

    def test_templates_have_body_content(self):
        """Test that templates have markdown content after frontmatter"""
        templates = get_all_templates()

        for filename, content in templates.items():
            parts = content.split("---\n", 2)
            assert len(parts) == 3, f"{filename} missing body content"

            body = parts[2].strip()
            assert len(body) > 100, f"{filename} body content too short"
            assert "# " in body, f"{filename} missing markdown headers"

    def test_productagents_template_content(self):
        """Test specific content requirements for productagents template"""
        content = GIL_IMPORT_PRODUCTAGENTS_MD

        # Should mention product folder
        assert "product" in content.lower(), "Missing product reference"
        assert ".claude/agents" in content, "Missing .claude/agents path"

        # Should mention backup
        assert "backup" in content.lower(), "Missing backup information"

    def test_personalagents_template_content(self):
        """Test specific content requirements for personalagents template"""
        content = GIL_IMPORT_PERSONALAGENTS_MD

        # Should mention personal/global agents
        assert "personal" in content.lower(), "Missing personal reference"
        assert "~/.claude/agents" in content, "Missing ~/.claude/agents path"

        # Should mention backup
        assert "backup" in content.lower(), "Missing backup information"

    def test_handover_template_content(self):
        """Test specific content requirements for handover template"""
        content = GIL_HANDOVER_MD

        # Should mention succession/handover
        assert "succession" in content.lower() or "handover" in content.lower(), \
            "Missing succession/handover reference"

        # Should mention context
        assert "context" in content.lower(), "Missing context reference"

        # Should mention MCP tool call
        assert "create_successor_orchestrator" in content, \
            "Missing create_successor_orchestrator tool reference"


class TestSetupSlashCommandsTool:
    """Test the setup_slash_commands MCP tool"""

    @pytest.mark.asyncio
    async def test_setup_slash_commands_returns_success(self, tool_accessor):
        """Test that setup_slash_commands returns success response"""
        result = await tool_accessor.setup_slash_commands()

        assert result["success"] is True
        assert "message" in result

    @pytest.mark.asyncio
    async def test_setup_slash_commands_returns_three_files(self, tool_accessor):
        """Test that setup_slash_commands returns exactly 3 files"""
        result = await tool_accessor.setup_slash_commands()

        assert "files" in result
        assert len(result["files"]) == 3
        assert "gil_import_productagents.md" in result["files"]
        assert "gil_import_personalagents.md" in result["files"]
        assert "gil_handover.md" in result["files"]

    @pytest.mark.asyncio
    async def test_setup_slash_commands_file_contents(self, tool_accessor):
        """Test that returned files have valid markdown content"""
        result = await tool_accessor.setup_slash_commands()

        files = result["files"]

        for filename, content in files.items():
            assert isinstance(content, str), f"{filename} content is not a string"
            assert len(content) > 100, f"{filename} content too short"
            assert content.startswith("---\n"), f"{filename} missing YAML frontmatter"

    @pytest.mark.asyncio
    async def test_setup_slash_commands_returns_target_directory(self, tool_accessor):
        """Test that response includes target directory"""
        result = await tool_accessor.setup_slash_commands()

        assert "target_directory" in result
        assert result["target_directory"] == "~/.claude/commands/"

    @pytest.mark.asyncio
    async def test_setup_slash_commands_returns_instructions(self, tool_accessor):
        """Test that response includes installation instructions"""
        result = await tool_accessor.setup_slash_commands()

        assert "instructions" in result
        assert isinstance(result["instructions"], list)
        assert len(result["instructions"]) > 0

        # Check for key instruction steps
        instructions_text = " ".join(result["instructions"])
        assert "commands" in instructions_text.lower()
        assert "file" in instructions_text.lower()

    @pytest.mark.asyncio
    async def test_setup_slash_commands_restart_required(self, tool_accessor):
        """Test that response indicates restart is required"""
        result = await tool_accessor.setup_slash_commands()

        assert "restart_required" in result
        assert result["restart_required"] is True

    @pytest.mark.asyncio
    async def test_setup_slash_commands_message_format(self, tool_accessor):
        """Test that message has expected format"""
        result = await tool_accessor.setup_slash_commands()

        message = result["message"]
        assert "3" in message or "three" in message.lower(), "Message should mention 3 commands"
        assert "slash command" in message.lower(), "Message should mention slash commands"


@pytest.mark.skip(reason="MCP HTTP integration tests require full API stack - tested manually")
class TestMCPHttpExposure:
    """Test that setup_slash_commands is exposed via MCP HTTP endpoint"""

    @pytest.mark.asyncio
    async def test_setup_slash_commands_in_tools_list(self, async_client, auth_token):
        """Test that setup_slash_commands appears in MCP tools/list"""
        response = await async_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1
            },
            headers={"X-API-Key": auth_token}
        )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        assert "tools" in data["result"]

        tools = data["result"]["tools"]
        tool_names = [tool["name"] for tool in tools]

        assert "setup_slash_commands" in tool_names, "setup_slash_commands not in tools list"

    @pytest.mark.asyncio
    async def test_setup_slash_commands_tool_definition(self, async_client, auth_token):
        """Test that setup_slash_commands has correct tool definition"""
        response = await async_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/list",
                "params": {},
                "id": 1
            },
            headers={"X-API-Key": auth_token}
        )

        tools = response.json()["result"]["tools"]
        setup_tool = next((t for t in tools if t["name"] == "setup_slash_commands"), None)

        assert setup_tool is not None, "setup_slash_commands tool not found"
        assert "description" in setup_tool
        assert "inputSchema" in setup_tool

        # Verify description mentions key features
        description = setup_tool["description"]
        assert "slash command" in description.lower()
        assert ".claude/commands" in description or "claude/commands" in description

        # Verify no input parameters required
        schema = setup_tool["inputSchema"]
        assert schema["type"] == "object"
        assert "properties" in schema
        assert len(schema["properties"]) == 0, "setup_slash_commands should have no parameters"

    @pytest.mark.asyncio
    async def test_setup_slash_commands_tool_execution(self, async_client, auth_token):
        """Test that setup_slash_commands can be executed via MCP HTTP"""
        response = await async_client.post(
            "/mcp",
            json={
                "jsonrpc": "2.0",
                "method": "tools/call",
                "params": {
                    "name": "setup_slash_commands",
                    "arguments": {}
                },
                "id": 2
            },
            headers={"X-API-Key": auth_token}
        )

        assert response.status_code == 200
        data = response.json()

        assert "result" in data
        result = data["result"]

        # MCP response should have content array
        assert "content" in result
        assert isinstance(result["content"], list)
        assert len(result["content"]) > 0

        # Parse the text response
        content_text = result["content"][0]["text"]
        assert "success" in content_text.lower() or "files" in content_text.lower()


class TestEdgeCases:
    """Test edge cases and error handling"""

    @pytest.mark.asyncio
    async def test_setup_slash_commands_idempotent(self, tool_accessor):
        """Test that calling setup_slash_commands multiple times returns same result"""
        result1 = await tool_accessor.setup_slash_commands()
        result2 = await tool_accessor.setup_slash_commands()

        # Both calls should succeed
        assert result1["success"] is True
        assert result2["success"] is True

        # File contents should be identical
        assert result1["files"] == result2["files"]

    @pytest.mark.asyncio
    async def test_setup_slash_commands_no_tenant_required(self, tool_accessor):
        """Test that setup_slash_commands works without tenant context (static templates)"""
        # This tool returns static templates, no tenant isolation needed
        result = await tool_accessor.setup_slash_commands()

        assert result["success"] is True
        assert len(result["files"]) == 3

    def test_template_file_sizes_reasonable(self):
        """Test that template files are not excessively large"""
        templates = get_all_templates()

        for filename, content in templates.items():
            # Templates should be < 5KB (reasonable size for markdown docs)
            assert len(content) < 5000, f"{filename} is too large ({len(content)} bytes)"
            # But also not too small
            assert len(content) > 200, f"{filename} is too small ({len(content)} bytes)"
