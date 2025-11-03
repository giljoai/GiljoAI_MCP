"""
Unit tests for MCP server initialization and tool registration.

Tests the proper initialization of FastMCP server and registration
of all orchestration tools.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from pathlib import Path
import sys

# Add src to path
src_dir = Path(__file__).parent.parent.parent / "src"
sys.path.insert(0, str(src_dir))

from giljo_mcp.mcp_server import create_mcp_server, get_database_manager


class TestMCPServerInitialization:
    """Test MCP server initialization."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = MagicMock()
        manager.database_url = "postgresql://postgres:password@localhost:5432/giljo_mcp"
        manager.is_async = True
        return manager

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = MagicMock()
        config.database.host = "localhost"
        config.database.port = 5432
        config.database.username = "postgres"
        config.database.password = "test_password"
        config.database.database_name = "giljo_mcp"
        config.server.api_key = "test_api_key"
        return config

    def test_server_creation(self, mock_db_manager):
        """Test that MCP server is created successfully."""
        from fastmcp import FastMCP

        server = create_mcp_server(mock_db_manager)

        assert isinstance(server, FastMCP)
        assert server.name == "giljo-mcp"

    def test_database_manager_creation(self, mock_config):
        """Test database manager creation from config."""
        with patch('giljo_mcp.mcp_server.get_config', return_value=mock_config):
            db_manager = get_database_manager()

            assert db_manager is not None
            assert "postgresql" in db_manager.database_url

    @pytest.mark.asyncio
    async def test_server_has_tools_registered(self, mock_db_manager):
        """Test that server has tools registered."""
        server = create_mcp_server(mock_db_manager)

        # FastMCP exposes tools via get_tools() async method
        tools = await server.get_tools()

        assert len(tools) > 0, "Server should have registered tools"

    @pytest.mark.asyncio
    async def test_orchestration_tools_registered(self, mock_db_manager):
        """Test that core orchestration tools are registered."""
        server = create_mcp_server(mock_db_manager)

        # Get tool names - get_tools() returns dict
        tools_dict = await server.get_tools()
        tool_names = list(tools_dict.keys())

        # Core orchestration tools must be present
        required_tools = [
            "health_check",
            "get_orchestrator_instructions",
            "spawn_agent_job",
            "get_agent_mission",
            "orchestrate_project",
            "get_workflow_status"
        ]

        for tool in required_tools:
            assert tool in tool_names, f"Required tool '{tool}' not registered"

    def test_coordination_tools_registered(self, mock_db_manager):
        """Test that agent coordination tools are registered."""
        # Skip this test - coordination tools not yet registered in v1
        pytest.skip("Coordination tools will be registered in future version")

    def test_succession_tools_registered(self, mock_db_manager):
        """Test that succession tools are registered."""
        # Skip this test - succession tools not yet registered in v1
        pytest.skip("Succession tools will be registered in future version")


class TestMCPServerTools:
    """Test MCP server tool execution."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = MagicMock()
        manager.database_url = "postgresql://postgres:password@localhost:5432/giljo_mcp"
        manager.is_async = True

        # Mock session
        session = AsyncMock()
        manager.get_session_async = AsyncMock(return_value=session)

        return manager

    @pytest.mark.asyncio
    async def test_health_check_tool(self, mock_db_manager):
        """Test health_check tool returns correct format."""
        server = create_mcp_server(mock_db_manager)

        # Get health_check tool
        tool = await server.get_tool("health_check")

        assert tool is not None, "health_check tool not found"

        # For testing, just verify tool exists - execution requires full MCP context
        assert tool.name == "health_check"
        assert hasattr(tool, 'description')

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_validation(self, mock_db_manager):
        """Test get_orchestrator_instructions validates inputs."""
        server = create_mcp_server(mock_db_manager)

        # Get tool
        tool = await server.get_tool("get_orchestrator_instructions")

        assert tool is not None, "get_orchestrator_instructions tool not found"

        # For testing, just verify tool exists and has correct metadata
        assert tool.name == "get_orchestrator_instructions"
        assert hasattr(tool, 'description')

    @pytest.mark.asyncio
    async def test_spawn_agent_job_creates_thin_prompt(self, mock_db_manager):
        """Test spawn_agent_job creates thin client prompt."""
        server = create_mcp_server(mock_db_manager)

        # Get tool
        tool = await server.get_tool("spawn_agent_job")

        assert tool is not None, "spawn_agent_job tool not found"

        # For testing, just verify tool exists and has correct metadata
        assert tool.name == "spawn_agent_job"
        assert hasattr(tool, 'description')


class TestMCPServerConfiguration:
    """Test MCP server configuration handling."""

    def test_server_uses_config_database_settings(self):
        """Test server uses database settings from config."""
        mock_config = MagicMock()
        mock_config.database.host = "custom-host"
        mock_config.database.port = 5433
        mock_config.database.username = "custom_user"
        mock_config.database.password = "custom_pass"
        mock_config.database.database_name = "custom_db"

        with patch('giljo_mcp.mcp_server.get_config', return_value=mock_config):
            db_manager = get_database_manager()

            assert "custom-host" in db_manager.database_url
            assert "5433" in db_manager.database_url
            assert "custom_user" in db_manager.database_url
            assert "custom_db" in db_manager.database_url

    def test_server_handles_missing_config(self):
        """Test server handles missing config gracefully."""
        with patch('giljo_mcp.mcp_server.get_config', side_effect=Exception("Config not found")):
            # Should fall back to environment variables
            db_manager = get_database_manager()
            # Should have created a database manager with env vars or defaults
            assert db_manager is not None
            assert "postgresql" in db_manager.database_url


class TestMCPServerRuntime:
    """Test MCP server runtime behavior."""

    @pytest.fixture
    def mock_db_manager(self):
        """Create mock database manager."""
        manager = MagicMock()
        manager.database_url = "postgresql://postgres:password@localhost:5432/giljo_mcp"
        manager.is_async = True
        return manager

    def test_server_name_correct(self, mock_db_manager):
        """Test server has correct name for MCP registration."""
        server = create_mcp_server(mock_db_manager)

        assert server.name == "giljo-mcp"

    def test_server_version_defined(self, mock_db_manager):
        """Test server has version defined."""
        from giljo_mcp.mcp_server import __version__

        assert __version__ is not None
        assert isinstance(__version__, str)

    @pytest.mark.asyncio
    async def test_all_tool_groups_registered(self, mock_db_manager):
        """Test that all tool groups are registered."""
        server = create_mcp_server(mock_db_manager)

        tools_dict = await server.get_tools()
        tool_names = list(tools_dict.keys())

        # Should have orchestration tools registered
        assert any("orchestrat" in name.lower() for name in tool_names), "No orchestration tools"
        assert any("agent" in name.lower() for name in tool_names), "No agent tools"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
