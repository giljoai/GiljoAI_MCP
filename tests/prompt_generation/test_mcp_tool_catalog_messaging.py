"""
Tests for MCP tool catalog messaging tools compliance (Handover 0296).

Verifies that the tool catalog exposes ONLY canonical messaging tools.
"""

import pytest

from src.giljo_mcp.prompt_generation.mcp_tool_catalog import MCPToolCatalogGenerator


class TestMCPToolCatalogMessaging:
    """Tests for MCPToolCatalogGenerator communication tools."""

    @pytest.fixture
    def catalog_generator(self):
        return MCPToolCatalogGenerator()

    def test_communication_category_has_canonical_tools(self, catalog_generator):
        """Communication category should include canonical messaging tools."""
        tools = catalog_generator.TOOLS.get("communication", {})

        # Must have these canonical tools
        assert "send_message" in tools, "Must have send_message tool"
        assert "receive_messages" in tools, "Must have receive_messages tool"
        assert "list_messages" in tools, "Must have list_messages tool"

    def test_communication_category_excludes_legacy_tools(self, catalog_generator):
        """Communication category should NOT include legacy tools."""
        tools = catalog_generator.TOOLS.get("communication", {})

        # Must NOT have these legacy tools
        assert "send_mcp_message" not in tools, "Must not have legacy send_mcp_message"
        assert "read_mcp_messages" not in tools, "Must not have legacy read_mcp_messages"
        assert "get_messages" not in tools, "Must not have get_messages (use receive_messages)"
        assert "broadcast_message" not in tools, "Must not have broadcast_message (use send_message)"

    def test_send_message_has_correct_params(self, catalog_generator):
        """send_message should have correct parameter signature."""
        tools = catalog_generator.TOOLS.get("communication", {})
        send_message = tools.get("send_message", {})

        params = send_message.get("params", [])
        param_str = " ".join(params)

        # Should have to_agents (list) not to_agent_id (single)
        assert "to_agents" in param_str or "to_agent" in param_str, "send_message should have to_agents parameter"
        assert "content" in param_str or "message_content" in param_str, "send_message should have content parameter"
        assert "project_id" in param_str, "send_message should have project_id parameter"

    def test_receive_messages_has_correct_params(self, catalog_generator):
        """receive_messages should have correct parameter signature."""
        tools = catalog_generator.TOOLS.get("communication", {})
        receive = tools.get("receive_messages", {})

        params = receive.get("params", [])
        param_str = " ".join(params)

        assert "agent_id" in param_str, "receive_messages should have agent_id parameter"

    def test_agent_tool_mappings_use_canonical_tools(self, catalog_generator):
        """Agent tool mappings should reference canonical communication tools."""
        mappings = catalog_generator.AGENT_TOOL_MAPPINGS

        for agent_display_name, tools in mappings.items():
            comm_tools = [t for t in tools if t.startswith("communication.")]

            for tool_ref in comm_tools:
                tool_name = tool_ref.split(".")[-1]
                # Should not reference legacy tools
                assert tool_name not in ["get_messages", "broadcast_message"], (
                    f"{agent_display_name} should not reference legacy {tool_name}"
                )

    def test_full_catalog_mentions_canonical_tools(self, catalog_generator):
        """Generated full catalog should mention canonical tools."""
        catalog = catalog_generator.generate_full_catalog()

        assert "send_message" in catalog
        assert "receive_messages" in catalog
        assert "list_messages" in catalog

    def test_full_catalog_excludes_legacy_tools(self, catalog_generator):
        """Generated full catalog should NOT mention legacy tools as primary options."""
        catalog = catalog_generator.generate_full_catalog()

        # These should not appear as tool headings
        assert "### broadcast_message" not in catalog, "broadcast_message should not be a separate tool"
        assert "### get_messages" not in catalog, "get_messages should not be a tool (use receive_messages)"
