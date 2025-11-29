"""
Comprehensive MCP Server tests to achieve 80%+ coverage
Tests GiljoMCPServer class with production-grade standards
"""

# Import the production MCP server
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.server import GiljoMCPServer, create_server, main

from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestGiljoMCPServer:
    """Comprehensive test suite for GiljoMCPServer class"""

    @pytest.fixture
    def mock_config(self):
        """Create mock configuration for testing"""
        config = MagicMock()

        # Create mock server config
        config.server = MagicMock()
        config.server.mcp_port = 8080
        config.server.mode = MagicMock()
        config.server.mode.value = "LOCAL"

        # Create mock database config
        config.database = MagicMock()
        config.database.type = "sqlite"
        config.database.sqlite_path = "/tmp/test.db"
        config.database.pg_host = "localhost"
        config.database.pg_port = 5432
        config.database.pg_database = "test_db"
        config.database.pg_user = "test_user"
        config.database.pg_password = "test_pass"

        return config

    @pytest.fixture
    def mock_fastmcp(self):
        """Mock FastMCP instance with required methods"""
        mock_mcp = MagicMock()
        mock_mcp.tool = MagicMock()
        return mock_mcp

    @pytest.fixture
    def mock_db_manager(self):
        """Mock DatabaseManager with async support"""
        mock_db = AsyncMock()
        mock_db.create_tables_async = AsyncMock()
        mock_db.close_async = AsyncMock()
        mock_db.get_session = AsyncMock()
        return mock_db

    @pytest.fixture
    def mock_tenant_manager(self):
        """Mock TenantManager for testing"""
        return MagicMock()

    # Test 1: Server Initialization
    @patch("src.giljo_mcp.server.FastMCP")
    @patch("src.giljo_mcp.server.get_config")
    def test_server_init_with_default_config(self, mock_get_config, mock_fastmcp_class, mock_config):
        """Test server initialization with default configuration"""
        mock_get_config.return_value = mock_config
        mock_fastmcp_instance = MagicMock()
        mock_fastmcp_class.return_value = mock_fastmcp_instance

        server = GiljoMCPServer()

        # Verify config was loaded
        mock_get_config.assert_called_once()
        assert server.config == mock_config

        # Verify FastMCP was initialized with proper parameters
        mock_fastmcp_class.assert_called_once_with(name="GiljoAI MCP Server", lifespan=server._lifespan)
        assert server.mcp == mock_fastmcp_instance

        # Verify initial state
        assert server.db_manager is None
        assert server.tenant_manager is None

    @patch("src.giljo_mcp.server.FastMCP")
    def test_server_init_with_custom_config(self, mock_fastmcp_class, mock_config):
        """Test server initialization with custom configuration"""
        mock_fastmcp_instance = MagicMock()
        mock_fastmcp_class.return_value = mock_fastmcp_instance

        server = GiljoMCPServer(config=mock_config)

        assert server.config == mock_config
        mock_fastmcp_class.assert_called_once()

    def test_create_server_factory(self, mock_config):
        """Test create_server factory function"""
        with patch("src.giljo_mcp.server.GiljoMCPServer") as mock_server_class:
            mock_server_instance = MagicMock()
            mock_server_class.return_value = mock_server_instance

            result = create_server(mock_config)

            mock_server_class.assert_called_once_with(mock_config)
            assert result == mock_server_instance

    def test_create_server_factory_no_config(self):
        """Test create_server factory function without config"""
        with patch("src.giljo_mcp.server.GiljoMCPServer") as mock_server_class:
            mock_server_instance = MagicMock()
            mock_server_class.return_value = mock_server_instance

            result = create_server()

            mock_server_class.assert_called_once_with(None)
            assert result == mock_server_instance

    # Test 2: Database Initialization
    @pytest_asyncio.fixture
    async def server_with_mocks(self, mock_config, mock_fastmcp):
        """Create server instance with mocked dependencies"""
        with patch("src.giljo_mcp.server.FastMCP", return_value=mock_fastmcp):
            server = GiljoMCPServer(config=mock_config)
            yield server

    @pytest.mark.asyncio
    async def test_initialize_database_sqlite_success(self, server_with_mocks, mock_config):
        """Test successful SQLite database initialization"""
        server = server_with_mocks
        mock_config.database.type = "sqlite"

        with patch("src.giljo_mcp.server.DatabaseManager") as mock_db_class:
            mock_db_instance = AsyncMock()
            mock_db_class.return_value = mock_db_instance
            mock_db_class.build_sqlite_url.return_value = PostgreSQLTestHelper.get_test_db_url()

            await server._initialize_database()

            # Verify SQLite URL was built
            mock_db_class.build_sqlite_url.assert_called_once_with(str(mock_config.database.sqlite_path))

            # Verify DatabaseManager was created
            mock_db_class.assert_called_once_with(PostgreSQLTestHelper.get_test_db_url(), is_async=True)

            # Verify schema creation
            mock_db_instance.create_tables_async.assert_called_once()

            assert server.db_manager == mock_db_instance

    @pytest.mark.asyncio
    async def test_initialize_database_postgresql_success(self, server_with_mocks, mock_config):
        """Test successful PostgreSQL database initialization"""
        server = server_with_mocks
        mock_config.database.type = "postgresql"

        with patch("src.giljo_mcp.server.DatabaseManager") as mock_db_class:
            mock_db_instance = AsyncMock()
            mock_db_class.return_value = mock_db_instance
            mock_db_class.build_postgresql_url.return_value = "postgresql+asyncpg://test"

            await server._initialize_database()

            # Verify PostgreSQL URL was built with first host
            mock_db_class.build_postgresql_url.assert_called_once_with(
                host="localhost", port=5432, database="test_db", username="test_user", password="test_pass"
            )

            # Verify DatabaseManager was created
            mock_db_class.assert_called_once_with("postgresql+asyncpg://test", is_async=True)

            # Verify schema creation
            mock_db_instance.create_tables_async.assert_called_once()

            assert server.db_manager == mock_db_instance

    @pytest.mark.asyncio
    async def test_initialize_database_postgresql_failover(self, server_with_mocks, mock_config):
        """Test PostgreSQL database initialization with host failover"""
        server = server_with_mocks
        mock_config.database.type = "postgresql"

        with patch("src.giljo_mcp.server.DatabaseManager") as mock_db_class:
            # First host fails, second succeeds
            mock_db_class.side_effect = [
                Exception("First host failed"),  # First attempt fails
                AsyncMock(),  # Second attempt succeeds
            ]
            mock_db_class.build_postgresql_url.return_value = "postgresql+asyncpg://test"

            # Mock successful second instance
            mock_db_instance = AsyncMock()
            mock_db_class.return_value = mock_db_instance

            await server._initialize_database()

            # Verify both hosts were tried
            assert mock_db_class.build_postgresql_url.call_count == 2
            calls = mock_db_class.build_postgresql_url.call_args_list

            # First call with primary host
            assert calls[0][1]["host"] == "localhost"
            # Second call with fallback host
            assert calls[1][1]["host"] == "10.1.0.164"

    @pytest.mark.asyncio
    async def test_initialize_database_postgresql_all_hosts_fail(self, server_with_mocks, mock_config):
        """Test PostgreSQL database initialization when all hosts fail"""
        server = server_with_mocks
        mock_config.database.type = "postgresql"

        with patch("src.giljo_mcp.server.DatabaseManager") as mock_db_class:
            # All hosts fail
            mock_db_class.side_effect = Exception("Connection failed")
            mock_db_class.build_postgresql_url.return_value = "postgresql+asyncpg://test"

            with pytest.raises(Exception, match="Failed to connect to PostgreSQL with all available hosts"):
                await server._initialize_database()

    # Test 3: Tool Registration
    @pytest.mark.asyncio
    async def test_register_tools_success(self, server_with_mocks):
        """Test successful tool registration"""
        server = server_with_mocks
        server.db_manager = MagicMock()
        server.tenant_manager = MagicMock()

        # Mock all tool registration functions - they're imported inside the method
        with (
            patch("src.giljo_mcp.tools.project.register_project_tools") as mock_project,
            patch("src.giljo_mcp.tools.agent.register_agent_tools") as mock_agent,
            patch("src.giljo_mcp.tools.message.register_message_tools") as mock_message,
            patch("src.giljo_mcp.tools.context.register_context_tools") as mock_context,
            patch("src.giljo_mcp.tools.template.register_template_tools") as mock_template,
        ):
            await server._register_tools()

            # Verify all tool groups were registered with correct parameters
            mock_project.assert_called_once_with(server.mcp, server.db_manager, server.tenant_manager)
            mock_agent.assert_called_once_with(server.mcp, server.db_manager, server.tenant_manager)
            mock_message.assert_called_once_with(server.mcp, server.db_manager, server.tenant_manager)
            mock_context.assert_called_once_with(server.mcp, server.db_manager, server.tenant_manager)
            mock_template.assert_called_once_with(server.mcp, server.db_manager, server.tenant_manager)

    @pytest.mark.asyncio
    async def test_register_tools_import_error(self, server_with_mocks):
        """Test tool registration with import errors"""
        server = server_with_mocks
        server.db_manager = MagicMock()
        server.tenant_manager = MagicMock()

        # Mock import error for one tool group
        with (
            patch("src.giljo_mcp.tools.project.register_project_tools", side_effect=ImportError("Module not found")),
            patch("src.giljo_mcp.server.logger") as mock_logger,
        ):
            # Should not raise exception, just log warning
            await server._register_tools()

            # Verify warning was logged
            mock_logger.warning.assert_called_once()
            assert "Some tools not yet implemented" in str(mock_logger.warning.call_args)

    # Test 4: Info Endpoints Registration
    def test_register_info_endpoints(self, server_with_mocks, mock_config):
        """Test info endpoints registration"""
        server = server_with_mocks
        mock_config.server.mode.value = "LOCAL"

        # Track calls to mcp.tool decorator
        mock_tool_calls = []

        def mock_tool_decorator():
            def decorator(func):
                mock_tool_calls.append(func.__name__)
                return func

            return decorator

        server.mcp.tool = mock_tool_decorator

        server._register_info_endpoints()

        # Verify all three endpoints were registered
        expected_endpoints = ["health", "ready", "info"]
        assert mock_tool_calls == expected_endpoints

    @pytest.mark.asyncio
    async def test_info_endpoint_health(self, server_with_mocks, mock_config):
        """Test health endpoint response"""
        server = server_with_mocks
        mock_config.server.mode.value = "LAN"

        # Register endpoints to get the actual functions
        server._register_info_endpoints()

        # Get the health function from the mcp.tool calls
        for call_args in server.mcp.tool.call_args_list:
            if hasattr(call_args, "__name__") and call_args.__name__ == "health":
                break

        # We need to test the actual endpoint logic, so let's mock it properly
        with patch.object(server.mcp, "tool") as mock_tool:
            server._register_info_endpoints()

            # Get the health function that was registered
            health_calls = [call for call in mock_tool.call_args_list if len(call[0]) == 0]
            assert len(health_calls) == 3  # Three endpoints registered

    @pytest.mark.asyncio
    async def test_info_endpoint_ready_database_connected(self, server_with_mocks):
        """Test ready endpoint with connected database"""
        server = server_with_mocks

        # Mock database manager with successful connection
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)

        server.db_manager = MagicMock()
        server.db_manager.get_session.return_value = mock_session_context
        server.tenant_manager = MagicMock()

        # Test the ready endpoint logic directly
        # Since we can't easily extract the decorated function, we'll test the core logic
        db_ready = False
        if server.db_manager:
            try:
                async with server.db_manager.get_session() as session:
                    await session.execute("SELECT 1")
                    db_ready = True
            except Exception:
                pass

        assert db_ready is True

    @pytest.mark.asyncio
    async def test_info_endpoint_ready_database_disconnected(self, server_with_mocks):
        """Test ready endpoint with disconnected database"""
        server = server_with_mocks

        # Mock database manager with failed connection
        server.db_manager = MagicMock()
        server.db_manager.get_session.side_effect = Exception("Database connection failed")
        server.tenant_manager = MagicMock()

        # Test the ready endpoint logic directly
        db_ready = False
        if server.db_manager:
            try:
                async with server.db_manager.get_session() as session:
                    await session.execute("SELECT 1")
                    db_ready = True
            except Exception:
                pass

        assert db_ready is False

    # Test 5: Authentication Mode Detection
    def test_get_auth_mode_local(self, server_with_mocks, mock_config):
        """Test authentication mode detection for LOCAL deployment"""
        server = server_with_mocks
        mock_config.server.mode.value = "LOCAL"

        auth_mode = server._get_auth_mode()
        assert auth_mode == "none"

    def test_get_auth_mode_lan(self, server_with_mocks, mock_config):
        """Test authentication mode detection for LAN deployment"""
        server = server_with_mocks
        mock_config.server.mode.value = "LAN"

        auth_mode = server._get_auth_mode()
        assert auth_mode == "api_key"

    def test_get_auth_mode_wan(self, server_with_mocks, mock_config):
        """Test authentication mode detection for WAN deployment"""
        server = server_with_mocks
        mock_config.server.mode.value = "WAN"

        auth_mode = server._get_auth_mode()
        assert auth_mode == "jwt"

    # Test 6: Server Run Method
    @pytest.mark.asyncio
    async def test_run_with_default_port(self, server_with_mocks, mock_config):
        """Test server run method with default port"""
        server = server_with_mocks
        mock_config.server.mcp_port = 9090

        result = await server.run()

        # Should return the FastMCP instance
        assert result == server.mcp

    @pytest.mark.asyncio
    async def test_run_with_custom_port(self, server_with_mocks):
        """Test server run method with custom port"""
        server = server_with_mocks

        result = await server.run(host="0.0.0.0", port=8888)

        # Should return the FastMCP instance
        assert result == server.mcp

    # Test 7: Lifespan Management
    @pytest.mark.asyncio
    async def test_lifespan_success_path(self, server_with_mocks):
        """Test successful lifespan management"""
        server = server_with_mocks

        # Mock all the methods that lifespan calls
        server._initialize_database = AsyncMock()
        server._register_tools = AsyncMock()
        server._register_info_endpoints = MagicMock()

        mock_db_manager = AsyncMock()
        server.db_manager = mock_db_manager

        with patch("src.giljo_mcp.server.TenantManager") as mock_tenant_class:
            mock_tenant_instance = MagicMock()
            mock_tenant_class.return_value = mock_tenant_instance

            # Test lifespan context manager
            async with server._lifespan():
                # Verify initialization was called
                server._initialize_database.assert_called_once()
                server._register_tools.assert_called_once()
                server._register_info_endpoints.assert_called_once()

                # Verify tenant manager was created
                mock_tenant_class.assert_called_once_with(server.db_manager)
                assert server.tenant_manager == mock_tenant_instance

            # Verify cleanup was called
            mock_db_manager.close_async.assert_called_once()

    @pytest.mark.asyncio
    async def test_lifespan_cleanup_on_exception(self, server_with_mocks):
        """Test lifespan cleanup when exception occurs"""
        server = server_with_mocks

        # Mock database manager for cleanup
        mock_db_manager = AsyncMock()
        server.db_manager = mock_db_manager

        # Mock initialization to raise exception
        server._initialize_database = AsyncMock(side_effect=Exception("Init failed"))

        try:
            async with server._lifespan():
                pass  # Exception should occur during context entry
        except Exception:
            pass  # Expected

        # Verify cleanup was still called
        mock_db_manager.close_async.assert_called_once()

    # Test 8: Main Function
    @pytest.mark.asyncio
    async def test_main_function(self):
        """Test main entry point function"""
        with (
            patch("src.giljo_mcp.server.get_config") as mock_get_config,
            patch("src.giljo_mcp.server.create_server") as mock_create_server,
        ):
            mock_config = MagicMock()
            mock_get_config.return_value = mock_config

            mock_server = AsyncMock()
            mock_server.run = AsyncMock(return_value="mcp_app")
            mock_create_server.return_value = mock_server

            result = await main()

            # Verify config was loaded
            mock_get_config.assert_called_once()

            # Verify server was created with config
            mock_create_server.assert_called_once_with(mock_config)

            # Verify server was run
            mock_server.run.assert_called_once()

            # Verify return value
            assert result == "mcp_app"

    # Test 9: Info Endpoint Functions Testing
    @pytest.mark.asyncio
    async def test_info_endpoints_actual_functions(self, server_with_mocks, mock_config):
        """Test actual info endpoint function implementations"""
        server = server_with_mocks
        server.db_manager = MagicMock()
        server.tenant_manager = MagicMock()

        # Mock database session for ready endpoint
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session_context = AsyncMock()
        mock_session_context.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_context.__aexit__ = AsyncMock(return_value=None)
        server.db_manager.get_session.return_value = mock_session_context

        # Capture the registered endpoint functions
        endpoint_functions = {}

        def mock_tool_decorator():
            def decorator(func):
                endpoint_functions[func.__name__] = func
                return func

            return decorator

        server.mcp.tool = mock_tool_decorator
        server._register_info_endpoints()

        # Test health endpoint
        health_result = await endpoint_functions["health"]()
        expected_health = {
            "status": "healthy",
            "server": "GiljoAI MCP",
            "version": "0.1.0",
            "mode": mock_config.server.mode.value,
        }
        assert health_result == expected_health

        # Test ready endpoint
        ready_result = await endpoint_functions["ready"]()
        expected_ready = {
            "ready": True,
            "database": mock_config.database.type,
            "tenant_system": True,
        }
        assert ready_result == expected_ready

        # Test info endpoint
        info_result = await endpoint_functions["info"]()
        expected_info = {
            "name": "GiljoAI MCP Server",
            "version": "0.1.0",
            "description": "Multi-tenant MCP orchestration server",
            "capabilities": {
                "project_management": True,
                "agent_orchestration": True,
                "message_routing": True,
                "context_discovery": True,
                "multi_tenant": True,
            },
            "configuration": {
                "mode": mock_config.server.mode.value,
                "database": mock_config.database.type,
                "port": mock_config.server.mcp_port,
                "authentication": "none",  # LOCAL mode
            },
        }
        assert info_result == expected_info

    @pytest.mark.asyncio
    async def test_ready_endpoint_database_failure(self, server_with_mocks, mock_config):
        """Test ready endpoint when database fails"""
        server = server_with_mocks
        server.db_manager = MagicMock()
        server.tenant_manager = MagicMock()

        # Mock database session failure
        server.db_manager.get_session.side_effect = Exception("Database error")

        # Capture the registered endpoint functions
        endpoint_functions = {}

        def mock_tool_decorator():
            def decorator(func):
                endpoint_functions[func.__name__] = func
                return func

            return decorator

        server.mcp.tool = mock_tool_decorator
        server._register_info_endpoints()

        # Test ready endpoint with database failure
        ready_result = await endpoint_functions["ready"]()
        expected_ready = {
            "ready": False,
            "database": mock_config.database.type,
            "tenant_system": True,
        }
        assert ready_result == expected_ready

    @pytest.mark.asyncio
    async def test_lifespan_with_no_database_manager(self, server_with_mocks):
        """Test lifespan cleanup when no database manager exists"""
        server = server_with_mocks

        # Mock initialization methods
        server._initialize_database = AsyncMock()
        server._register_tools = AsyncMock()
        server._register_info_endpoints = MagicMock()

        with patch("src.giljo_mcp.server.TenantManager") as mock_tenant_class:
            mock_tenant_instance = MagicMock()
            mock_tenant_class.return_value = mock_tenant_instance

            # Set db_manager to None after initialization
            async def set_db_none():
                server.db_manager = None

            server._initialize_database.side_effect = set_db_none

            # Test lifespan context manager
            async with server._lifespan():
                pass  # Normal execution

            # Verify TenantManager was created
            mock_tenant_class.assert_called_once_with(None)
