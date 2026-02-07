"""
Unit tests for ToolAccessor.create_task() with tenant_key parameter (Handover 0433 Phase 3).

Test Coverage:
- Method signature includes tenant_key parameter
- Fetches active product before creating task
- Raises ValidationError when no active product exists
- Passes tenant_key and product_id to TaskService
"""

import inspect
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


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
        """Test that create_task raises ValidationError when no active product exists"""
        # Setup mocks
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        # Create ToolAccessor
        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        # Mock ProductService to return no active product
        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as MockProductService:
            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value={"success": True, "product": None, "message": "No active product"}
            )
            MockProductService.return_value = mock_product_service_instance

            # Attempt to create task - should raise ValidationError
            with pytest.raises(ValidationError) as exc_info:
                await tool_accessor.create_task(
                    title="Test Task",
                    description="Should fail",
                    priority="medium",
                    tenant_key="tenant-abc",
                )

            # Verify error message
            error_message = str(exc_info.value)
            assert "active product" in error_message.lower()
            assert "activate" in error_message.lower() or "set" in error_message.lower()

    @pytest.mark.asyncio
    async def test_uses_tenant_manager_when_tenant_key_not_provided(self):
        """Test that tenant_manager is used when tenant_key parameter is None"""
        # Setup mocks
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-from-manager")

        # Create ToolAccessor
        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        # Mock ProductService and TaskService
        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as MockProductService, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value={
                    "success": True,
                    "product": {"id": "prod-123", "name": "Test Product"},
                }
            )
            MockProductService.return_value = mock_product_service_instance

            mock_log_task.return_value = {"success": True, "task_id": "task-123"}

            # Call without tenant_key parameter
            await tool_accessor.create_task(
                title="Test Task", description="Test description", tenant_key=None
            )

            # Verify ProductService was instantiated with tenant from manager
            MockProductService.assert_called_once()
            call_kwargs = MockProductService.call_args[1]
            assert call_kwargs["tenant_key"] == "tenant-from-manager"

    @pytest.mark.asyncio
    async def test_passes_product_id_and_tenant_key_to_task_service(self):
        """Test that product_id and tenant_key are passed to TaskService.log_task()"""
        # Setup mocks
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        # Create ToolAccessor
        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        # Mock ProductService and TaskService
        with patch("src.giljo_mcp.tools.tool_accessor.ProductService") as MockProductService, patch.object(
            tool_accessor._task_service, "log_task", new_callable=AsyncMock
        ) as mock_log_task:

            mock_product_service_instance = AsyncMock()
            mock_product_service_instance.get_active_product = AsyncMock(
                return_value={
                    "success": True,
                    "product": {"id": "prod-456", "name": "Active Product"},
                }
            )
            MockProductService.return_value = mock_product_service_instance

            mock_log_task.return_value = {"success": True, "task_id": "task-789"}

            # Call create_task
            result = await tool_accessor.create_task(
                title="Integration Task",
                description="Task description here",
                priority="high",
                category="backend",
                tenant_key="tenant-abc",
            )

            # Verify TaskService.log_task was called with correct parameters
            mock_log_task.assert_called_once()
            call_kwargs = mock_log_task.call_args[1]
            assert call_kwargs["product_id"] == "prod-456"
            assert call_kwargs["tenant_key"] == "tenant-abc"
            assert call_kwargs["content"] == "Task description here"
            assert call_kwargs["priority"] == "high"
            assert call_kwargs["category"] == "backend"

            # Verify result
            assert result["success"] is True
            assert result["task_id"] == "task-789"
