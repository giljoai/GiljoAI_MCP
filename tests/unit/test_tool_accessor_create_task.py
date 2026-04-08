# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for ToolAccessor.create_task() - Bug fixes for return type, title preservation,
and category fallback.

Test Coverage:
- Bug 1: Returns structured dict (not bare string)
- Bug 2: Title is preserved separately from description
- Bug 3: Category defaults to "general" (not title)
- Logging on successful task creation
- Method signature validation
- Tenant isolation
"""

import inspect
import logging
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


def _make_mock_product(product_id="prod-123", name="Test Product"):
    """Create a mock product object with .id attribute (not a dict)."""
    product = Mock()
    product.id = product_id
    product.name = name
    return product


def _make_tool_accessor(tenant_key="tenant-abc"):
    """Create a ToolAccessor with standard mocks."""
    db_manager = Mock()
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value=tenant_key)

    tool_accessor = ToolAccessor(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=None,
        test_session=None,
    )
    return tool_accessor


class TestToolAccessorCreateTaskSignature:
    """Test suite for create_task() method signature and basic validation."""

    def test_create_task_signature_includes_tenant_key(self):
        """Verify create_task() method signature includes tenant_key parameter"""
        sig = inspect.signature(ToolAccessor.create_task)
        params = sig.parameters

        assert "tenant_key" in params, "create_task() must accept tenant_key parameter"
        assert params["tenant_key"].default is None, "tenant_key should have default value of None"

    def test_create_task_signature_parameters(self):
        """Verify all expected parameters exist"""
        sig = inspect.signature(ToolAccessor.create_task)
        params = list(sig.parameters.keys())

        expected_params = [
            "self",
            "title",
            "description",
            "priority",
            "category",
            "assigned_to",
            "tenant_key",
        ]

        for param in expected_params:
            assert param in params, f"Parameter '{param}' should be in signature"


class TestToolAccessorCreateTaskValidation:
    """Test suite for create_task() validation logic."""

    @pytest.mark.asyncio
    async def test_raises_validation_error_when_no_active_product(self):
        """Test that create_task raises ValidationError when no active product exists."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls:
            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(return_value=None)
            mock_product_service_cls.return_value = mock_product_service_instance

            with pytest.raises(ValidationError) as exc_info:
                await tool_accessor.create_task(
                    title="Test Task",
                    description="Should fail",
                    priority="medium",
                    tenant_key="tenant-abc",
                )

            error_message = str(exc_info.value)
            assert "active product" in error_message.lower()

    @pytest.mark.asyncio
    async def test_uses_tenant_manager_when_tenant_key_not_provided(self):
        """Test that tenant_manager is used when tenant_key parameter is None."""
        tool_accessor = _make_tool_accessor(tenant_key="tenant-from-manager")

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-123")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-123"

            await tool_accessor.create_task(
                title="Test Task", description="Test description", tenant_key=None
            )

            mock_product_service_cls.assert_called_once()
            call_kwargs = mock_product_service_cls.call_args[1]
            assert call_kwargs["tenant_key"] == "tenant-from-manager"


class TestToolAccessorCreateTaskReturnValue:
    """Bug 1: create_task must return a structured dict, not a bare string."""

    @pytest.mark.asyncio
    async def test_returns_dict_with_success_and_task_id(self):
        """Return value must be a dict containing success, task_id, and message fields."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-456")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-789"

            result = await tool_accessor.create_task(
                title="Integration Task",
                description="Task description here",
                priority="high",
                category="backend",
                tenant_key="tenant-abc",
            )

            # Must be a dict, not a string
            assert isinstance(result, dict), f"Expected dict, got {type(result).__name__}"
            assert result["success"] is True
            assert result["task_id"] == "task-789"
            assert result["title"] == "Integration Task"
            assert result["priority"] == "high"
            assert result["category"] == "backend"
            assert "message" in result
            assert "Integration Task" in result["message"]

    @pytest.mark.asyncio
    async def test_return_dict_includes_product_id(self):
        """Return dict should include the product_id for traceability."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-999")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-001"

            result = await tool_accessor.create_task(
                title="Task A",
                description="Description A",
                tenant_key="tenant-abc",
            )

            assert result["product_id"] == "prod-999"


class TestToolAccessorCreateTaskTitlePreservation:
    """Bug 2: Title must be passed through to TaskService, not discarded."""

    @pytest.mark.asyncio
    async def test_passes_title_to_task_service_log_task(self):
        """log_task must receive the title parameter so it can be stored separately."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-456")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-789"

            await tool_accessor.create_task(
                title="Fix login bug",
                description="Users cannot login with email containing special chars",
                priority="high",
                category="bug",
                tenant_key="tenant-abc",
            )

            mock_log_task.assert_called_once()
            call_kwargs = mock_log_task.call_args[1]
            # Title must be passed as the 'title' kwarg
            assert call_kwargs["title"] == "Fix login bug"
            # Description must be passed as the 'description' kwarg
            assert call_kwargs["description"] == "Users cannot login with email containing special chars"

    @pytest.mark.asyncio
    async def test_content_parameter_uses_title_for_backwards_compat(self):
        """The content parameter (backwards compat) should use the title value."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-456")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-789"

            await tool_accessor.create_task(
                title="My Task Title",
                description="Extended details about the task",
                tenant_key="tenant-abc",
            )

            call_kwargs = mock_log_task.call_args[1]
            assert call_kwargs["content"] == "My Task Title"


class TestToolAccessorCreateTaskCategoryFallback:
    """Bug 3: Category must default to 'general', not the title."""

    @pytest.mark.asyncio
    async def test_category_defaults_to_general_when_none(self):
        """When category is None, it should default to 'general', not the task title."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-456")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-789"

            await tool_accessor.create_task(
                title="Fix login bug",
                description="Detail here",
                category=None,
                tenant_key="tenant-abc",
            )

            call_kwargs = mock_log_task.call_args[1]
            assert call_kwargs["category"] == "general"

    @pytest.mark.asyncio
    async def test_category_defaults_to_general_when_empty_string(self):
        """When category is empty string, it should default to 'general'."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-456")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-789"

            await tool_accessor.create_task(
                title="Fix login bug",
                description="Detail here",
                category="",
                tenant_key="tenant-abc",
            )

            call_kwargs = mock_log_task.call_args[1]
            assert call_kwargs["category"] == "general"

    @pytest.mark.asyncio
    async def test_explicit_category_is_preserved(self):
        """When an explicit category is provided, it should be used as-is."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-456")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-789"

            await tool_accessor.create_task(
                title="Fix login bug",
                description="Detail here",
                category="frontend",
                tenant_key="tenant-abc",
            )

            call_kwargs = mock_log_task.call_args[1]
            assert call_kwargs["category"] == "frontend"

    @pytest.mark.asyncio
    async def test_return_dict_category_defaults_to_general(self):
        """The return dict should show 'general' as category when none was provided."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-456")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-789"

            result = await tool_accessor.create_task(
                title="Some task",
                description="Detail",
                category=None,
                tenant_key="tenant-abc",
            )

            assert result["category"] == "general"


class TestToolAccessorCreateTaskLogging:
    """Logging: create_task should log on successful task creation."""

    @pytest.mark.asyncio
    async def test_logs_on_successful_task_creation(self, caplog):
        """A log.info message should be emitted on successful task creation."""
        tool_accessor = _make_tool_accessor()

        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_product_service_cls, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value=_make_mock_product("prod-456")
            )
            mock_product_service_cls.return_value = mock_product_service_instance

            mock_log_task.return_value = "task-789"

            with caplog.at_level(logging.INFO, logger="src.giljo_mcp.tools.tool_accessor"):
                await tool_accessor.create_task(
                    title="Logged Task",
                    description="This should produce a log message",
                    tenant_key="tenant-abc",
                )

            # Check that an info log was produced containing the task id and tenant
            assert any("task-789" in record.message for record in caplog.records), (
                "Expected log message containing task_id 'task-789'"
            )
            assert any("tenant-abc" in record.message for record in caplog.records), (
                "Expected log message containing tenant_key 'tenant-abc'"
            )
