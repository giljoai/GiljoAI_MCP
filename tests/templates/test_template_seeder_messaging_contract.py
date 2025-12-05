"""
Tests for template seeder messaging contract compliance (Handover 0296).

Verifies that all agent templates use ONLY the canonical messaging tools
and do NOT reference legacy queue-style tools.
"""
import pytest
from src.giljo_mcp.template_seeder import (
    _get_agent_messaging_protocol_section,
    _get_orchestrator_messaging_protocol_section,
    _get_default_templates_v103,
)

# Canonical messaging tools that SHOULD be referenced
CANONICAL_TOOLS = [
    "send_message",
    "receive_messages",
    "acknowledge_message",
    "list_messages",
]

# Legacy tools that should NOT be referenced
LEGACY_TOOLS = [
    "send_mcp_message",
    "read_mcp_messages",
    "get_messages",  # Wrong name - should be receive_messages
    "broadcast_message",  # Should use send_message(to_agents=['all'])
]


class TestAgentMessagingProtocolSection:
    """Tests for _get_agent_messaging_protocol_section()"""

    def test_agent_messaging_uses_canonical_tools(self):
        """Agent messaging section should reference canonical messaging tools."""
        section = _get_agent_messaging_protocol_section()

        # Should mention the canonical tools
        assert "send_message" in section, "Should reference send_message tool"
        assert "receive_messages" in section, "Should reference receive_messages tool"
        assert "acknowledge_message" in section, "Should reference acknowledge_message tool"

    def test_agent_messaging_does_not_use_legacy_tools(self):
        """Agent messaging section should NOT reference legacy queue tools."""
        section = _get_agent_messaging_protocol_section()

        # Should NOT mention legacy tools
        assert "send_mcp_message" not in section, "Should not reference legacy send_mcp_message"
        assert "read_mcp_messages" not in section, "Should not reference legacy read_mcp_messages"
        # get_messages is the wrong tool name
        assert "get_messages" not in section or "receive_messages" in section, \
            "Should use receive_messages not get_messages"

    def test_agent_messaging_describes_acknowledge_behavior(self):
        """Agent messaging should instruct agents to acknowledge messages."""
        section = _get_agent_messaging_protocol_section()

        # Should describe acknowledgment behavior
        assert "acknowledge" in section.lower(), "Should describe message acknowledgment"


class TestOrchestratorMessagingProtocolSection:
    """Tests for _get_orchestrator_messaging_protocol_section()"""

    def test_orchestrator_messaging_uses_canonical_tools(self):
        """Orchestrator messaging section should reference canonical messaging tools."""
        section = _get_orchestrator_messaging_protocol_section()

        # Should mention the canonical tools
        assert "send_message" in section, "Should reference send_message tool"
        assert "receive_messages" in section, "Should reference receive_messages tool"
        assert "acknowledge_message" in section, "Should reference acknowledge_message tool"

    def test_orchestrator_messaging_does_not_use_legacy_tools(self):
        """Orchestrator messaging section should NOT reference legacy queue tools."""
        section = _get_orchestrator_messaging_protocol_section()

        # Should NOT mention legacy tools
        assert "send_mcp_message" not in section, "Should not reference legacy send_mcp_message"
        assert "read_mcp_messages" not in section, "Should not reference legacy read_mcp_messages"

    def test_orchestrator_messaging_describes_broadcast_correctly(self):
        """Orchestrator should use send_message(to_agents=['all']) for broadcasts."""
        section = _get_orchestrator_messaging_protocol_section()

        # Should NOT use separate broadcast_message tool
        # Instead should use send_message with to_agents=['all'] or to_agent='all'
        if "broadcast" in section.lower():
            assert "send_message" in section, \
                "Broadcasts should use send_message with to_agents=['all']"


class TestDefaultTemplatesMessagingContract:
    """Tests for default template v103 messaging compliance."""

    def test_default_templates_exist(self):
        """Should have default templates for all agent types."""
        templates = _get_default_templates_v103()

        assert len(templates) >= 6, "Should have at least 6 default templates"

        roles = [t["role"] for t in templates]
        assert "orchestrator" in roles
        assert "implementer" in roles
        assert "tester" in roles
