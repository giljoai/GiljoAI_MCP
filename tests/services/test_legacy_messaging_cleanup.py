"""
Tests for legacy messaging cleanup verification (Handover 0298).

These tests document current behavior and ensure cleanup doesn't break anything.
"""
import pytest

# Tests that don't require pytestmark
class TestLegacyQueueNotExposed:
    """Verify legacy queue tools are not publicly exposed."""

    def test_mcp_tool_catalog_excludes_legacy_tools(self):
        """MCP tool catalog should not expose legacy queue tools."""
        from src.giljo_mcp.prompt_generation.mcp_tool_catalog import MCPToolCatalogGenerator

        gen = MCPToolCatalogGenerator()
        catalog = gen.generate_full_catalog()

        # Should NOT contain legacy tool names
        assert "send_mcp_message" not in catalog
        assert "read_mcp_messages" not in catalog
        assert "queue" not in catalog.lower() or "message queue" not in catalog.lower()

    def test_templates_exclude_legacy_tools(self):
        """Agent templates should not reference legacy queue tools."""
        from src.giljo_mcp.template_seeder import (
            _get_agent_messaging_protocol_section,
            _get_orchestrator_messaging_protocol_section,
        )

        agent_section = _get_agent_messaging_protocol_section()
        orch_section = _get_orchestrator_messaging_protocol_section()

        # Should NOT reference legacy tools
        assert "send_mcp_message" not in agent_section
        assert "read_mcp_messages" not in agent_section
        assert "send_mcp_message" not in orch_section
        assert "read_mcp_messages" not in orch_section


class TestMessageServiceExists:
    """Verify MessageService is the primary messaging implementation."""

    def test_message_service_imports(self):
        """MessageService should import successfully."""
        from src.giljo_mcp.services.message_service import MessageService
        assert MessageService is not None

    def test_message_service_has_send_method(self):
        """MessageService should have send_message method."""
        from src.giljo_mcp.services.message_service import MessageService
        assert hasattr(MessageService, 'send_message')
        assert callable(getattr(MessageService, 'send_message'))

    def test_message_service_has_list_method(self):
        """MessageService should have list_messages method."""
        from src.giljo_mcp.services.message_service import MessageService
        assert hasattr(MessageService, 'list_messages')
        assert callable(getattr(MessageService, 'list_messages'))


class TestInstallPyStillWorks:
    """Verify install.py continues to work after cleanup."""

    def test_template_seeder_imports_work(self):
        """Template seeder should import without errors."""
        from src.giljo_mcp.template_seeder import seed_tenant_templates
        assert seed_tenant_templates is not None

    def test_message_service_imports_work(self):
        """MessageService should import without errors."""
        from src.giljo_mcp.services.message_service import MessageService
        assert MessageService is not None

    def test_no_circular_imports(self):
        """Core modules should not have circular import issues."""
        # Import key modules to verify no circular dependencies
        from src.giljo_mcp.services.message_service import MessageService
        from src.giljo_mcp.services.project_service import ProjectService
        from src.giljo_mcp.services.orchestration_service import OrchestrationService

        assert MessageService is not None
        assert ProjectService is not None
        assert OrchestrationService is not None

    def test_mcp_tools_init_imports_work(self):
        """MCP tools __init__.py should import without errors."""
        # The tools module is now HTTP-only and doesn't export individual tools
        # It only exports placeholder registration functions
        from src.giljo_mcp.tools import (
            register_agent_tools,
            register_message_tools,
            register_orchestration_tools,
        )

        assert register_agent_tools is not None
        assert register_message_tools is not None
        assert register_orchestration_tools is not None


class TestNoLegacyQueueReferences:
    """Verify legacy queue references are removed from codebase."""

    def test_agent_communication_queue_not_in_tools_init(self):
        """tools/__init__.py should not export AgentCommunicationQueue."""
        import src.giljo_mcp.tools as tools_module

        # Should not have AgentCommunicationQueue
        assert not hasattr(tools_module, 'AgentCommunicationQueue')
        assert not hasattr(tools_module, 'agent_comm_queue')

    def test_legacy_queue_tools_not_in_mcp_catalog(self):
        """MCP tool catalog should only list modern messaging tools."""
        from src.giljo_mcp.prompt_generation.mcp_tool_catalog import MCPToolCatalogGenerator

        gen = MCPToolCatalogGenerator()
        catalog = gen.generate_full_catalog()

        # Should have modern tools
        assert 'send_message' in catalog
        assert 'receive_messages' in catalog or 'list_messages' in catalog

        # Should NOT have legacy tools
        assert 'send_mcp_message' not in catalog
        assert 'read_mcp_messages' not in catalog
        assert 'AgentCommunicationQueue' not in catalog


class TestDatabaseSchema:
    """Verify database schema supports modern messaging."""

    def test_message_model_exists(self):
        """Message model should exist with proper fields."""
        from src.giljo_mcp.models import Message
        assert Message is not None

        # Check for key fields
        assert hasattr(Message, 'id')
        assert hasattr(Message, 'project_id')
        assert hasattr(Message, 'tenant_key')
        assert hasattr(Message, 'content')
        assert hasattr(Message, 'to_agents')
    # 0371: Removed test_mcp_agent_job_has_messages_jsonb - MCPAgentJob model no longer exists
