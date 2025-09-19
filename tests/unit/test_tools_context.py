"""
Comprehensive tests for context.py tools
Target: 2.55% → 95%+ coverage

Tests all context tool functions:
- register_context_tools
- get_vision
- get_vision_index
- discover_context
- get_context_index
- get_context_section
- get_product_settings
- session_info
- recalibrate_mission
- get_large_document
- get_discovery_paths
- help
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.models import (
    Agent,
    Configuration,
    ContextIndex,
    LargeDocumentIndex,
    Message,
    Project,
    Vision,
)
from src.giljo_mcp.models import Session as DBSession
from src.giljo_mcp.tools.context import register_context_tools
from tests.utils.tools_helpers import (
    AssertionHelpers,
    MockMCPToolRegistrar,
    ToolsTestHelper,
)


class TestContextTools:
    """Test class for context tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup['db_manager']
        self.tenant_manager = tools_test_setup['tenant_manager']
        self.mock_server = tools_test_setup['mcp_server']
        self.discovery_manager = tools_test_setup['discovery_manager']
        self.path_resolver = tools_test_setup['path_resolver']

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Context Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_register_context_tools(self):
        """Test that all context tools are registered properly"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_context_tools(mock_server, self.db_manager, self.tenant_manager)

        # Verify all expected tools are registered
        expected_tools = [
            "get_vision",
            "get_vision_index",
            "discover_context",
            "get_context_index",
            "get_context_section",
            "get_product_settings",
            "session_info",
            "recalibrate_mission",
            "get_large_document",
            "get_discovery_paths",
            "help"
        ]

        registered_tools = registrar.get_all_tools()
        for tool in expected_tools:
            AssertionHelpers.assert_tool_registered(registrar, tool)

        assert len(registered_tools) >= len(expected_tools)

    # get_vision tests
    @pytest.mark.asyncio
    async def test_get_vision_no_active_project(self):
        """Test get_vision with no active project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Clear current tenant
        self.tenant_manager.clear_current_tenant()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        result = await get_vision()

        AssertionHelpers.assert_error_response(result, "No active project")

    @pytest.mark.asyncio
    async def test_get_vision_project_not_found(self):
        """Test get_vision with invalid tenant key"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Set invalid tenant key
        self.tenant_manager.set_current_tenant("tk_invalidtenantkey1234567890123456")

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        result = await get_vision()

        AssertionHelpers.assert_error_response(result, "Project not found")

    @pytest.mark.asyncio
    async def test_get_vision_from_database(self):
        """Test get_vision retrieving from database"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create vision documents in database
        async with self.db_manager.get_session_async() as session:
            vision = await ToolsTestHelper.create_test_vision(
                session,
                self.project.id,
                self.project.tenant_key,
                "test_vision.md",
                "# Test Vision\nThis is test content"
            )

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        result = await get_vision(part=1)

        AssertionHelpers.assert_success_response(result, ["part", "total_parts", "content", "tokens"])
        assert result["part"] == 1
        assert result["total_parts"] == 1
        assert "Test Vision" in result["content"]
        assert result["indexed"] is True

    @pytest.mark.asyncio
    async def test_get_vision_force_reindex(self):
        """Test get_vision with force_reindex=True"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create existing vision documents
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_vision(
                session,
                self.project.id,
                self.project.tenant_key
            )

        # Mock path resolver to return test files
        test_vision_dir = Path("tests/temp/docs/Vision")
        test_vision_dir.mkdir(parents=True, exist_ok=True)
        (test_vision_dir / "test.md").write_text("# Reindexed Content")

        self.path_resolver.resolve_path.return_value = test_vision_dir

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        result = await get_vision(part=1, force_reindex=True)

        AssertionHelpers.assert_success_response(result, ["content", "indexed"])
        assert "Reindexed Content" in result["content"]

    @pytest.mark.asyncio
    async def test_get_vision_no_files_found(self):
        """Test get_vision when no vision files exist"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock path resolver to return non-existent directory
        self.path_resolver.resolve_path.return_value = Path("nonexistent/path")

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        result = await get_vision()

        AssertionHelpers.assert_error_response(result, "No vision documents found")

    @pytest.mark.asyncio
    async def test_get_vision_invalid_part_number(self):
        """Test get_vision with invalid part number"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create one vision document
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_vision(
                session,
                self.project.id,
                self.project.tenant_key
            )

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        result = await get_vision(part=99)

        AssertionHelpers.assert_error_response(result, "Part 99 not found")

    # get_vision_index tests
    @pytest.mark.asyncio
    async def test_get_vision_index_from_database(self):
        """Test get_vision_index from database"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create context index in database
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_context_index(
                session,
                self.project.id,
                self.project.tenant_key,
                "test.md"
            )

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision_index = registrar.get_registered_tool("get_vision_index")

        result = await get_vision_index()

        AssertionHelpers.assert_success_response(result, ["index"])
        assert result["index"]["from_database"] is True
        assert result["index"]["total_files"] == 1

    @pytest.mark.asyncio
    async def test_get_vision_index_from_filesystem(self):
        """Test get_vision_index from filesystem when no database index"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock path resolver to return test files
        test_vision_dir = Path("tests/temp/docs/Vision")
        test_vision_dir.mkdir(parents=True, exist_ok=True)
        (test_vision_dir / "overview.md").write_text("# Overview\nTest content")
        (test_vision_dir / "architecture.md").write_text("# Architecture\nTest architecture")

        self.path_resolver.resolve_path.return_value = test_vision_dir

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision_index = registrar.get_registered_tool("get_vision_index")

        result = await get_vision_index()

        AssertionHelpers.assert_success_response(result, ["index"])
        assert result["index"]["from_filesystem"] is True
        assert result["index"]["total_files"] == 2

    @pytest.mark.asyncio
    async def test_get_vision_index_no_directory(self):
        """Test get_vision_index when vision directory doesn't exist"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock path resolver to return non-existent directory
        self.path_resolver.resolve_path.return_value = Path("nonexistent/path")

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision_index = registrar.get_registered_tool("get_vision_index")

        result = await get_vision_index()

        AssertionHelpers.assert_error_response(result, "No vision directory found")

    # discover_context tests
    @pytest.mark.asyncio
    async def test_discover_context_success(self):
        """Test discover_context with valid parameters"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        discover_context = registrar.get_registered_tool("discover_context")

        result = await discover_context(agent_role="orchestrator", force_refresh=False)

        AssertionHelpers.assert_success_response(result, ["context", "project"])
        self.discovery_manager.discover_context.assert_called_once_with(
            agent_role="orchestrator",
            project_id=self.project.id,
            force_refresh=False
        )

    @pytest.mark.asyncio
    async def test_discover_context_no_project(self):
        """Test discover_context with no active project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        self.tenant_manager.clear_current_tenant()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        discover_context = registrar.get_registered_tool("discover_context")

        result = await discover_context()

        AssertionHelpers.assert_error_response(result, "No active project")

    # get_context_index tests
    @pytest.mark.asyncio
    async def test_get_context_index_success(self):
        """Test get_context_index with valid project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_context_index = registrar.get_registered_tool("get_context_index")

        result = await get_context_index()

        AssertionHelpers.assert_success_response(result, ["sources", "discovery_enabled"])
        assert result["discovery_enabled"] is True
        self.discovery_manager.get_discovery_paths.assert_called_once()

    # get_context_section tests
    @pytest.mark.asyncio
    async def test_get_context_section_single_file(self):
        """Test get_context_section for a single file document"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock path resolver to return test file
        test_file = Path("tests/temp/CLAUDE.md")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        test_file.write_text("# Claude Instructions\n\n## Setup\nTest setup instructions")

        with patch('pathlib.Path', return_value=test_file):
            register_context_tools(mock_server, self.db_manager, self.tenant_manager)
            get_context_section = registrar.get_registered_tool("get_context_section")

            result = await get_context_section(document_name="claude")

        AssertionHelpers.assert_success_response(result, ["document", "content"])
        assert "Claude Instructions" in result["content"]

    @pytest.mark.asyncio
    async def test_get_context_section_with_section(self):
        """Test get_context_section with specific section"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test file with sections
        test_file = Path("tests/temp/CLAUDE.md")
        test_file.parent.mkdir(parents=True, exist_ok=True)
        content = """# Claude Instructions

## Setup
Setup instructions here

## Usage
Usage instructions here

## Testing
Testing instructions here
"""
        test_file.write_text(content)

        with patch('pathlib.Path', return_value=test_file):
            register_context_tools(mock_server, self.db_manager, self.tenant_manager)
            get_context_section = registrar.get_registered_tool("get_context_section")

            result = await get_context_section(document_name="claude", section_name="Usage")

        AssertionHelpers.assert_success_response(result, ["document", "section", "content"])
        assert "Usage instructions" in result["content"]

    @pytest.mark.asyncio
    async def test_get_context_section_unknown_document(self):
        """Test get_context_section with unknown document"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_context_section = registrar.get_registered_tool("get_context_section")

        result = await get_context_section(document_name="unknown")

        AssertionHelpers.assert_error_response(result, "Unknown document")

    # get_product_settings tests
    @pytest.mark.asyncio
    async def test_get_product_settings_success(self):
        """Test get_product_settings with configurations"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test configuration
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_configuration(
                session,
                self.project.id,
                self.project.tenant_key,
                "test_setting",
                "test_value"
            )

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_product_settings = registrar.get_registered_tool("get_product_settings")

        result = await get_product_settings()

        AssertionHelpers.assert_success_response(result, ["settings"])
        assert "project" in result["settings"]
        assert "configurations" in result["settings"]
        assert "test_setting" in result["settings"]["configurations"]

    @pytest.mark.asyncio
    async def test_get_product_settings_no_project(self):
        """Test get_product_settings with no active project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        self.tenant_manager.clear_current_tenant()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_product_settings = registrar.get_registered_tool("get_product_settings")

        result = await get_product_settings()

        AssertionHelpers.assert_error_response(result, "No active project")

    # session_info tests
    @pytest.mark.asyncio
    async def test_session_info_success(self):
        """Test session_info with active project and agents"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test agents and messages
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_agent(session, self.project.id, "agent1")
            await ToolsTestHelper.create_test_agent(session, self.project.id, "agent2")
            await ToolsTestHelper.create_test_message(session, self.project.id)

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        session_info = registrar.get_registered_tool("session_info")

        result = await session_info()

        AssertionHelpers.assert_success_response(result, ["session"])
        assert result["session"]["active_project"] == self.project.name
        assert result["session"]["agents"]["total"] == 2
        assert result["session"]["messages"]["total"] == 1

    @pytest.mark.asyncio
    async def test_session_info_no_project(self):
        """Test session_info with no active project"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        self.tenant_manager.clear_current_tenant()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        session_info = registrar.get_registered_tool("session_info")

        result = await session_info()

        AssertionHelpers.assert_success_response(result, ["session"])
        assert result["session"]["active_project"] is None

    # recalibrate_mission tests
    @pytest.mark.asyncio
    async def test_recalibrate_mission_success(self):
        """Test recalibrate_mission with valid parameters"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch('src.giljo_mcp.tools.context.broadcast') as mock_broadcast:
            mock_broadcast.return_value = {
                "success": True,
                "broadcast_to": ["agent1", "agent2"]
            }

            register_context_tools(mock_server, self.db_manager, self.tenant_manager)
            recalibrate_mission = registrar.get_registered_tool("recalibrate_mission")

            result = await recalibrate_mission(
                project_id=self.project.id,
                changes_summary="Updated mission with new requirements"
            )

        AssertionHelpers.assert_success_response(result, ["project_id", "agents_notified", "summary"])
        assert result["project_id"] == self.project.id

    # get_large_document tests
    @pytest.mark.asyncio
    async def test_get_large_document_success(self):
        """Test get_large_document with valid document"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test document
        test_doc = Path("tests/temp/large_doc.md")
        test_doc.parent.mkdir(parents=True, exist_ok=True)
        test_doc.write_text("# Large Document\n\nThis is a large document for testing.")

        with patch('pathlib.Path', return_value=test_doc):
            register_context_tools(mock_server, self.db_manager, self.tenant_manager)
            get_large_document = registrar.get_registered_tool("get_large_document")

            result = await get_large_document(document_path="large_doc.md")

        AssertionHelpers.assert_success_response(result, ["part", "total_parts", "content"])
        assert "Large Document" in result["content"]

    @pytest.mark.asyncio
    async def test_get_large_document_not_found(self):
        """Test get_large_document with non-existent document"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch('pathlib.Path') as mock_path:
            mock_path.return_value.exists.return_value = False

            register_context_tools(mock_server, self.db_manager, self.tenant_manager)
            get_large_document = registrar.get_registered_tool("get_large_document")

            result = await get_large_document(document_path="nonexistent.md")

        AssertionHelpers.assert_error_response(result, "Document not found")

    # get_discovery_paths tests
    @pytest.mark.asyncio
    async def test_get_discovery_paths_success(self):
        """Test get_discovery_paths returns all resolved paths"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_discovery_paths = registrar.get_registered_tool("get_discovery_paths")

        result = await get_discovery_paths()

        AssertionHelpers.assert_success_response(result, ["paths", "resolution_order"])
        assert "paths" in result
        assert "resolution_order" in result
        self.path_resolver.get_all_paths.assert_called_once()

    # help tests
    @pytest.mark.asyncio
    async def test_help_returns_documentation(self):
        """Test help returns complete tool documentation"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        help_tool = registrar.get_registered_tool("help")

        result = await help_tool()

        AssertionHelpers.assert_success_response(result, ["tool_count", "categories"])
        assert result["tool_count"] == 20
        assert "project" in result["categories"]
        assert "agent" in result["categories"]
        assert "message" in result["categories"]
        assert "context" in result["categories"]

    # Error handling tests
    @pytest.mark.asyncio
    async def test_context_tools_database_error_handling(self):
        """Test that context tools handle database errors gracefully"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Mock database to raise exception
        with patch.object(self.db_manager, 'get_session') as mock_get_session:
            mock_get_session.side_effect = Exception("Database connection failed")

            register_context_tools(mock_server, self.db_manager, self.tenant_manager)
            get_vision = registrar.get_registered_tool("get_vision")

            result = await get_vision()

        AssertionHelpers.assert_error_response(result, "Database connection failed")

    # Edge cases and boundary conditions
    @pytest.mark.asyncio
    async def test_get_vision_max_tokens_parameter(self):
        """Test get_vision with different max_tokens values"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create test vision files
        test_vision_dir = Path("tests/temp/docs/Vision")
        test_vision_dir.mkdir(parents=True, exist_ok=True)
        (test_vision_dir / "test.md").write_text("# Test\n" + "Content " * 1000)

        self.path_resolver.resolve_path.return_value = test_vision_dir

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        # Test with different token limits
        result_default = await get_vision()
        result_small = await get_vision(max_tokens=100)
        result_large = await get_vision(max_tokens=24000)

        # All should succeed but may have different chunking
        AssertionHelpers.assert_success_response(result_default)
        AssertionHelpers.assert_success_response(result_small)
        AssertionHelpers.assert_success_response(result_large)

    @pytest.mark.asyncio
    async def test_concurrent_vision_access(self):
        """Test concurrent access to vision tools"""
        import asyncio

        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create vision document
        async with self.db_manager.get_session_async() as session:
            await ToolsTestHelper.create_test_vision(
                session,
                self.project.id,
                self.project.tenant_key
            )

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        # Run multiple concurrent requests
        tasks = [get_vision() for _ in range(5)]
        results = await asyncio.gather(*tasks)

        # All should succeed
        for result in results:
            AssertionHelpers.assert_success_response(result)

    @pytest.mark.asyncio
    async def test_vision_with_empty_files(self):
        """Test vision tools with empty files"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Create empty vision directory
        test_vision_dir = Path("tests/temp/docs/Vision")
        test_vision_dir.mkdir(parents=True, exist_ok=True)

        self.path_resolver.resolve_path.return_value = test_vision_dir

        register_context_tools(mock_server, self.db_manager, self.tenant_manager)
        get_vision = registrar.get_registered_tool("get_vision")

        result = await get_vision()

        AssertionHelpers.assert_error_response(result, "No readable vision documents found")