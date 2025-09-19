"""
Comprehensive tests for tool_accessor.py
Target: 9.60% → 95%+ coverage

Tests the ToolAccessor class and its methods:
- ToolAccessor initialization
- Tool discovery and registration
- Tool invocation patterns
- Error handling and retries
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from src.giljo_mcp.tools.tool_accessor import ToolAccessor
from tests.utils.tools_helpers import (
    AssertionHelpers,
    ToolsTestHelper,
)


class TestToolAccessor:
    """Test class for ToolAccessor"""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, tools_test_setup):
        """Setup for each test method"""
        self.setup = tools_test_setup
        self.db_manager = tools_test_setup['db_manager']
        self.tenant_manager = tools_test_setup['tenant_manager']

        # Create test project and set as current tenant
        async with self.db_manager.get_session_async() as session:
            self.project = await ToolsTestHelper.create_test_project(session, "ToolAccessor Test Project")
            self.tenant_manager.set_current_tenant(self.project.tenant_key)

    def test_tool_accessor_initialization(self):
        """Test ToolAccessor initialization"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        assert accessor.db_manager == self.db_manager
        assert accessor.tenant_manager == self.tenant_manager
        assert hasattr(accessor, 'registered_tools')

    def test_tool_accessor_initialization_with_config(self):
        """Test ToolAccessor initialization with configuration"""
        config = {
            "retry_attempts": 5,
            "timeout": 30,
            "enable_caching": True
        }

        accessor = ToolAccessor(self.db_manager, self.tenant_manager, config=config)

        assert accessor.db_manager == self.db_manager
        assert accessor.tenant_manager == self.tenant_manager

    @pytest.mark.asyncio
    async def test_tool_discovery(self):
        """Test tool discovery functionality"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Mock tool discovery
        mock_tools = {
            "create_task": {"description": "Create a new task", "parameters": []},
            "list_tasks": {"description": "List all tasks", "parameters": []},
            "send_message": {"description": "Send a message", "parameters": []}
        }

        with patch.object(accessor, '_discover_available_tools', return_value=mock_tools):
            discovered_tools = await accessor.discover_tools()

            assert len(discovered_tools) == 3
            assert "create_task" in discovered_tools
            assert "list_tasks" in discovered_tools
            assert "send_message" in discovered_tools

    @pytest.mark.asyncio
    async def test_tool_registration(self):
        """Test tool registration functionality"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Test registering a tool
        tool_name = "test_tool"
        tool_config = {
            "description": "A test tool",
            "parameters": ["param1", "param2"],
            "handler": AsyncMock()
        }

        success = await accessor.register_tool(tool_name, tool_config)

        assert success is True
        assert tool_name in accessor.registered_tools

    @pytest.mark.asyncio
    async def test_tool_invocation_success(self):
        """Test successful tool invocation"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Mock tool handler
        mock_handler = AsyncMock(return_value={"success": True, "result": "Tool executed"})

        # Register mock tool
        await accessor.register_tool("mock_tool", {
            "description": "Mock tool",
            "handler": mock_handler
        })

        # Invoke tool
        result = await accessor.invoke_tool("mock_tool", {"param1": "value1"})

        assert result["success"] is True
        assert result["result"] == "Tool executed"
        mock_handler.assert_called_once_with({"param1": "value1"})

    @pytest.mark.asyncio
    async def test_tool_invocation_not_found(self):
        """Test tool invocation for non-existent tool"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        result = await accessor.invoke_tool("nonexistent_tool", {})

        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_tool_invocation_with_retry(self):
        """Test tool invocation with retry logic"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Mock tool handler that fails first time, succeeds second time
        mock_handler = AsyncMock(side_effect=[
            Exception("Temporary failure"),
            {"success": True, "result": "Success on retry"}
        ])

        await accessor.register_tool("retry_tool", {
            "description": "Tool with retry",
            "handler": mock_handler,
            "retry_attempts": 3
        })

        result = await accessor.invoke_tool("retry_tool", {})

        assert result["success"] is True
        assert result["result"] == "Success on retry"
        assert mock_handler.call_count == 2

    @pytest.mark.asyncio
    async def test_tool_invocation_timeout(self):
        """Test tool invocation with timeout"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Mock tool handler that takes too long
        async def slow_handler(params):
            await asyncio.sleep(2)
            return {"success": True}

        await accessor.register_tool("slow_tool", {
            "description": "Slow tool",
            "handler": slow_handler,
            "timeout": 0.5  # 0.5 second timeout
        })

        result = await accessor.invoke_tool("slow_tool", {})

        assert result["success"] is False
        assert "timeout" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_tool_invocation_exception_handling(self):
        """Test tool invocation exception handling"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Mock tool handler that raises exception
        mock_handler = AsyncMock(side_effect=ValueError("Invalid parameter"))

        await accessor.register_tool("error_tool", {
            "description": "Tool that errors",
            "handler": mock_handler
        })

        result = await accessor.invoke_tool("error_tool", {})

        assert result["success"] is False
        assert "Invalid parameter" in result["error"]

    @pytest.mark.asyncio
    async def test_batch_tool_invocation(self):
        """Test batch tool invocation"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Register multiple tools
        tools = {
            "tool1": AsyncMock(return_value={"success": True, "result": "Result 1"}),
            "tool2": AsyncMock(return_value={"success": True, "result": "Result 2"}),
            "tool3": AsyncMock(return_value={"success": True, "result": "Result 3"})
        }

        for name, handler in tools.items():
            await accessor.register_tool(name, {
                "description": f"Tool {name}",
                "handler": handler
            })

        # Batch invoke
        batch_requests = [
            {"tool": "tool1", "params": {"a": 1}},
            {"tool": "tool2", "params": {"b": 2}},
            {"tool": "tool3", "params": {"c": 3}}
        ]

        results = await accessor.batch_invoke(batch_requests)

        assert len(results) == 3
        for result in results:
            assert result["success"] is True

    @pytest.mark.asyncio
    async def test_tool_caching(self):
        """Test tool result caching"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager, {
            "enable_caching": True,
            "cache_ttl": 300
        })

        call_count = 0

        async def cached_handler(params):
            nonlocal call_count
            call_count += 1
            return {"success": True, "result": f"Call {call_count}"}

        await accessor.register_tool("cached_tool", {
            "description": "Cached tool",
            "handler": cached_handler,
            "cacheable": True
        })

        # First call
        result1 = await accessor.invoke_tool("cached_tool", {"key": "value"})
        assert result1["result"] == "Call 1"

        # Second call with same params should use cache
        result2 = await accessor.invoke_tool("cached_tool", {"key": "value"})
        assert result2["result"] == "Call 1"  # Same result, cached
        assert call_count == 1

        # Third call with different params should not use cache
        result3 = await accessor.invoke_tool("cached_tool", {"key": "different"})
        assert result3["result"] == "Call 2"
        assert call_count == 2

    @pytest.mark.asyncio
    async def test_tool_parameter_validation(self):
        """Test tool parameter validation"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        mock_handler = AsyncMock(return_value={"success": True})

        await accessor.register_tool("validated_tool", {
            "description": "Tool with validation",
            "handler": mock_handler,
            "required_params": ["param1", "param2"],
            "optional_params": ["param3"]
        })

        # Test with missing required parameters
        result1 = await accessor.invoke_tool("validated_tool", {"param1": "value1"})
        assert result1["success"] is False
        assert "required" in result1["error"].lower()

        # Test with all required parameters
        result2 = await accessor.invoke_tool("validated_tool", {
            "param1": "value1",
            "param2": "value2"
        })
        assert result2["success"] is True

    @pytest.mark.asyncio
    async def test_tool_metrics_collection(self):
        """Test tool execution metrics collection"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager, {
            "collect_metrics": True
        })

        mock_handler = AsyncMock(return_value={"success": True})

        await accessor.register_tool("metrics_tool", {
            "description": "Tool with metrics",
            "handler": mock_handler
        })

        # Invoke tool multiple times
        for i in range(3):
            await accessor.invoke_tool("metrics_tool", {"run": i})

        # Check metrics
        metrics = accessor.get_tool_metrics("metrics_tool")
        assert metrics["invocation_count"] == 3
        assert "average_duration" in metrics
        assert "success_rate" in metrics

    @pytest.mark.asyncio
    async def test_tool_lifecycle_events(self):
        """Test tool lifecycle event handling"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        events = []

        def on_tool_register(tool_name, config):
            events.append(f"registered:{tool_name}")

        def on_tool_invoke(tool_name, params):
            events.append(f"invoked:{tool_name}")

        def on_tool_complete(tool_name, result):
            events.append(f"completed:{tool_name}")

        # Register event handlers
        accessor.on("tool_register", on_tool_register)
        accessor.on("tool_invoke", on_tool_invoke)
        accessor.on("tool_complete", on_tool_complete)

        # Register and invoke tool
        mock_handler = AsyncMock(return_value={"success": True})
        await accessor.register_tool("event_tool", {
            "description": "Tool with events",
            "handler": mock_handler
        })

        await accessor.invoke_tool("event_tool", {})

        # Check events were fired
        assert "registered:event_tool" in events
        assert "invoked:event_tool" in events
        assert "completed:event_tool" in events

    @pytest.mark.asyncio
    async def test_tool_discovery_from_modules(self):
        """Test automatic tool discovery from modules"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Mock module discovery
        mock_modules = [
            "src.giljo_mcp.tools.task",
            "src.giljo_mcp.tools.agent",
            "src.giljo_mcp.tools.message"
        ]

        with patch.object(accessor, '_scan_tool_modules', return_value=mock_modules):
            discovered = await accessor.auto_discover_tools()

            assert isinstance(discovered, dict)
            assert len(discovered) >= 0

    def test_tool_accessor_configuration(self):
        """Test ToolAccessor configuration handling"""
        config = {
            "retry_attempts": 5,
            "timeout": 30,
            "enable_caching": True,
            "cache_ttl": 600,
            "collect_metrics": True,
            "batch_size": 10
        }

        accessor = ToolAccessor(self.db_manager, self.tenant_manager, config)

        assert accessor.config["retry_attempts"] == 5
        assert accessor.config["timeout"] == 30
        assert accessor.config["enable_caching"] is True

    @pytest.mark.asyncio
    async def test_tool_unregistration(self):
        """Test tool unregistration"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Register tool
        mock_handler = AsyncMock()
        await accessor.register_tool("temp_tool", {
            "description": "Temporary tool",
            "handler": mock_handler
        })

        assert "temp_tool" in accessor.registered_tools

        # Unregister tool
        success = await accessor.unregister_tool("temp_tool")

        assert success is True
        assert "temp_tool" not in accessor.registered_tools

    @pytest.mark.asyncio
    async def test_tool_listing(self):
        """Test listing available tools"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager)

        # Register some tools
        tools = ["tool1", "tool2", "tool3"]
        for tool in tools:
            await accessor.register_tool(tool, {
                "description": f"Description for {tool}",
                "handler": AsyncMock()
            })

        # List tools
        tool_list = accessor.list_tools()

        assert len(tool_list) == 3
        for tool in tools:
            assert tool in tool_list

    @pytest.mark.asyncio
    async def test_tool_accessor_error_recovery(self):
        """Test error recovery mechanisms"""
        accessor = ToolAccessor(self.db_manager, self.tenant_manager, {
            "error_recovery": True,
            "circuit_breaker": True
        })

        failure_count = 0

        async def unreliable_handler(params):
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise Exception("Simulated failure")
            return {"success": True, "recovered": True}

        await accessor.register_tool("unreliable_tool", {
            "description": "Unreliable tool",
            "handler": unreliable_handler,
            "retry_attempts": 5
        })

        result = await accessor.invoke_tool("unreliable_tool", {})

        assert result["success"] is True
        assert result["recovered"] is True
        assert failure_count == 3  # Failed twice, succeeded on third try