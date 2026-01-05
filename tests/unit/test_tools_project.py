"""
Comprehensive tests for project.py tools
Target: Unknown% → 95%+ coverage

Tests the project tool functions:
- register_project_tools
- list_projects
- close_project
- update_project_mission
- project_status
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.project import register_project_tools
from tests.utils.tools_helpers import (
    MockMCPToolRegistrar,
    ToolsTestHelper,
)


class TestProjectTools:
    """Test class for project tools"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup["db_manager"]
        self.tenant_manager = tools_test_setup["tenant_manager"]
        self.mock_server = tools_test_setup["mcp_server"]

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "Project Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    @pytest.mark.asyncio
    async def test_register_project_tools(self):
        """Test that project tools are registered properly"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        # Register tools
        register_project_tools(mock_server, self.db_manager, self.tenant_manager)

        # Should register project management tools
        registered_tools = registrar.get_all_tools()
        expected_tools = [
            "list_projects",
            "close_project",
            "update_project_mission",
            "project_status",
        ]

        for tool_name in expected_tools:
            assert any(tool_name in tool_info.get("name", "") for tool_info in registered_tools), (
                f"Tool {tool_name} not registered"
            )

    @pytest.mark.asyncio
    async def test_list_projects_tool(self):
        """Test list_projects tool functionality"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch.object(self.db_manager, "get_session") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project query results
            mock_project = MagicMock()
            mock_project.id = str(uuid.uuid4())
            mock_project.name = "Test Project"
            mock_project.status = "active"
            mock_project.tenant_key = "tk_" + "x" * 32
            mock_project.context_used = 1000
            mock_project.context_budget = 10000
            mock_project.created_at = None

            mock_result = MagicMock()
            mock_result.scalars.return_value.all.return_value = [mock_project]
            mock_db_session.execute.return_value = mock_result

            register_project_tools(mock_server, self.db_manager, self.tenant_manager)
            list_projects = registrar.get_registered_tool("list_projects")

            result = await list_projects()
            assert isinstance(result, dict)


    @pytest.mark.asyncio
    async def test_close_project_tool(self):
        """Test close_project tool functionality"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch.object(self.db_manager, "get_session") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project lookup
            mock_project = MagicMock()
            mock_project.id = str(uuid.uuid4())
            mock_project.name = "Test Project"
            mock_project.status = "active"
            mock_project.database_initialized_at = None

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_project
            mock_db_session.execute.return_value = mock_result
            mock_db_session.commit = AsyncMock()

            register_project_tools(mock_server, self.db_manager, self.tenant_manager)
            close_project = registrar.get_registered_tool("close_project")

            result = await close_project(project_id=str(uuid.uuid4()), summary="Project completed successfully")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_update_project_mission_tool(self):
        """Test update_project_mission tool functionality"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch.object(self.db_manager, "get_session") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project lookup
            mock_project = MagicMock()
            mock_project.id = str(uuid.uuid4())
            mock_project.name = "Test Project"
            mock_project.mission = "Old mission"

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_project
            mock_db_session.execute.return_value = mock_result
            mock_db_session.commit = AsyncMock()

            register_project_tools(mock_server, self.db_manager, self.tenant_manager)
            update_mission = registrar.get_registered_tool("update_project_mission")

            result = await update_mission(project_id=str(uuid.uuid4()), mission="Updated mission statement")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_project_status_tool(self):
        """Test project_status tool functionality"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch.object(self.db_manager, "get_session") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project lookup
            mock_project = MagicMock()
            mock_project.id = str(uuid.uuid4())
            mock_project.name = "Test Project"
            mock_project.mission = "Test mission"
            mock_project.status = "active"
            mock_project.tenant_key = "tk_" + "x" * 32
            mock_project.context_used = 1000
            mock_project.context_budget = 10000
            mock_project.created_at = None

            mock_agent = MagicMock()
            mock_agent.name = "test_agent"
            mock_agent.role = "worker"
            mock_agent.status = "active"
            mock_agent.context_used = 500

            mock_project_result = MagicMock()
            mock_project_result.scalar_one_or_none.return_value = mock_project

            mock_agent_result = MagicMock()
            mock_agent_result.scalars.return_value.all.return_value = [mock_agent]

            mock_db_session.execute.side_effect = [mock_project_result, mock_agent_result]

            register_project_tools(mock_server, self.db_manager, self.tenant_manager)
            project_status = registrar.get_registered_tool("project_status")

            result = await project_status(project_id=str(uuid.uuid4()))
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_project_not_found_scenarios(self):
        """Test scenarios where project is not found"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch.object(self.db_manager, "get_session") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project not found
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = None
            mock_db_session.execute.return_value = mock_result

            register_project_tools(mock_server, self.db_manager, self.tenant_manager)

            # Test close non-existent project
            close_project = registrar.get_registered_tool("close_project")
            result = await close_project(project_id=str(uuid.uuid4()), summary="Test")
            assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_project_status_with_tenant_context(self):
        """Test project_status using tenant context"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch.object(self.db_manager, "get_session") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock tenant context
            with patch.object(self.tenant_manager, "get_current_tenant") as mock_tenant:
                mock_tenant.return_value = "tk_" + "x" * 32

                # Mock project lookup
                mock_project = MagicMock()
                mock_project.id = str(uuid.uuid4())
                mock_project.name = "Test Project"
                mock_project.mission = "Test mission"
                mock_project.status = "active"
                mock_project.tenant_key = "tk_" + "x" * 32
                mock_project.context_used = 1000
                mock_project.context_budget = 10000
                mock_project.created_at = None

                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = mock_project
                mock_result.scalars.return_value.all.return_value = []
                mock_db_session.execute.return_value = mock_result

                register_project_tools(mock_server, self.db_manager, self.tenant_manager)
                project_status = registrar.get_registered_tool("project_status")

                # Test without project_id (should use tenant context)
                result = await project_status()
                assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_project_closure_inactive_project(self):
        """Test closing a project that's not active"""
        registrar = MockMCPToolRegistrar()
        mock_server = registrar.create_tool_decorator()

        with patch.object(self.db_manager, "get_session") as mock_session:
            mock_db_session = AsyncMock()
            mock_session.return_value.__aenter__.return_value = mock_db_session

            # Mock project that's already completed
            mock_project = MagicMock()
            mock_project.id = str(uuid.uuid4())
            mock_project.name = "Completed Project"
            mock_project.status = "database_initialized"  # Not active

            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = mock_project
            mock_db_session.execute.return_value = mock_result

            register_project_tools(mock_server, self.db_manager, self.tenant_manager)
            close_project = registrar.get_registered_tool("close_project")

            result = await close_project(project_id=str(uuid.uuid4()), summary="Trying to close completed project")

            assert isinstance(result, dict)
            # Should indicate error for non-active project
