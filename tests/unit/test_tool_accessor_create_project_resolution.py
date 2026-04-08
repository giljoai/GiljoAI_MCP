# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for ToolAccessor.create_project() — product resolution and return value.

Test Coverage:
- Active product resolution when product_id not provided
- Raises ValidationError when no active product exists
- Uses tenant_manager fallback when tenant_key not provided
- Returns serializable dict (not ORM object)
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


class TestCreateProjectActiveProductResolution:
    """Test suite for active product resolution logic."""

    @pytest.mark.asyncio
    async def test_resolves_active_product_when_product_id_not_provided(self):
        """Test that active product is fetched when product_id is None."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        # Mock ProductService with active product
        with (
            patch(
                "src.giljo_mcp.tools.tool_accessor.ProductService"
            ) as mock_product_service_cls,
            patch.object(
                tool_accessor._project_service,
                "create_project",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            mock_product = Mock()
            mock_product.id = "prod-123"

            mock_ps_instance = AsyncMock()
            mock_ps_instance.get_active_product = AsyncMock(
                return_value=mock_product
            )
            mock_product_service_cls.return_value = mock_ps_instance

            mock_project = Mock()
            mock_project.id = "proj-456"
            mock_project.alias = "PRJ-001"
            mock_project.name = "Test Project"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-123"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Test Project",
                tenant_key="tenant-abc",
            )

            # Verify ProductService was instantiated for active product lookup
            mock_product_service_cls.assert_called_once()
            mock_ps_instance.get_active_product.assert_awaited_once()

            # Verify create_project was called with resolved product_id
            mock_create.assert_awaited_once()
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["product_id"] == "prod-123"

    @pytest.mark.asyncio
    async def test_skips_resolution_when_product_id_provided(self):
        """Test that active product lookup is skipped when product_id is given."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        with (
            patch(
                "src.giljo_mcp.tools.tool_accessor.ProductService"
            ) as mock_product_service_cls,
            patch.object(
                tool_accessor._project_service,
                "create_project",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            mock_project = Mock()
            mock_project.id = "proj-789"
            mock_project.alias = "PRJ-002"
            mock_project.name = "Explicit Product Project"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "explicit-prod-id"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Explicit Product Project",
                product_id="explicit-prod-id",
                tenant_key="tenant-abc",
            )

            # ProductService should NOT be instantiated when product_id is given
            mock_product_service_cls.assert_not_called()

            # Verify create_project used the explicit product_id
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["product_id"] == "explicit-prod-id"

    @pytest.mark.asyncio
    async def test_raises_validation_error_when_no_active_product(self):
        """Test that ValidationError is raised when no active product exists."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        with patch(
            "src.giljo_mcp.tools.tool_accessor.ProductService"
        ) as mock_product_service_cls:
            mock_ps_instance = AsyncMock()
            mock_ps_instance.get_active_product = AsyncMock(return_value=None)
            mock_product_service_cls.return_value = mock_ps_instance

            with pytest.raises(ValidationError) as exc_info:
                await tool_accessor.create_project(
                    name="Should Fail Project",
                    tenant_key="tenant-abc",
                )

            error_message = str(exc_info.value)
            assert "active product" in error_message.lower()

    @pytest.mark.asyncio
    async def test_uses_tenant_manager_when_tenant_key_not_provided(self):
        """Test that tenant_manager is used when tenant_key is None."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-from-manager")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        with (
            patch(
                "src.giljo_mcp.tools.tool_accessor.ProductService"
            ) as mock_product_service_cls,
            patch.object(
                tool_accessor._project_service,
                "create_project",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            mock_product = Mock()
            mock_product.id = "prod-999"

            mock_ps_instance = AsyncMock()
            mock_ps_instance.get_active_product = AsyncMock(
                return_value=mock_product
            )
            mock_product_service_cls.return_value = mock_ps_instance

            mock_project = Mock()
            mock_project.id = "proj-111"
            mock_project.alias = "PRJ-003"
            mock_project.name = "Fallback Tenant Project"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-999"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Fallback Tenant Project",
                tenant_key=None,
            )

            # Verify tenant_manager was called
            tenant_manager.get_current_tenant.assert_called_once()

            # Verify ProductService was instantiated with manager's tenant_key
            call_kwargs = mock_product_service_cls.call_args[1]
            assert call_kwargs["tenant_key"] == "tenant-from-manager"


class TestCreateProjectReturnValue:
    """Test suite for return value serialization."""

    @pytest.mark.asyncio
    async def test_returns_serializable_dict(self):
        """Test that create_project returns a plain dict, not an ORM object."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        with patch.object(
            tool_accessor._project_service,
            "create_project",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_project = Mock()
            mock_project.id = "proj-aaa"
            mock_project.alias = "PRJ-010"
            mock_project.name = "Serialization Test"
            mock_project.description = "Test description"
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-bbb"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            result = await tool_accessor.create_project(
                name="Serialization Test",
                product_id="prod-bbb",
                tenant_key="tenant-abc",
            )

            assert isinstance(result, dict), "Return value must be a dict"
            assert result["success"] is True
            assert result["project_id"] == "proj-aaa"
            assert result["alias"] == "PRJ-010"
            assert result["name"] == "Serialization Test"
            assert result["status"] == "inactive"
            assert result["product_id"] == "prod-bbb"
            assert "message" in result
            assert "Serialization Test" in result["message"]

    @pytest.mark.asyncio
    async def test_return_dict_contains_all_expected_keys(self):
        """Test that the returned dict has exactly the expected keys."""
        db_manager = Mock()
        tenant_manager = Mock()
        tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")

        tool_accessor = ToolAccessor(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            websocket_manager=None,
            test_session=None,
        )

        with patch.object(
            tool_accessor._project_service,
            "create_project",
            new_callable=AsyncMock,
        ) as mock_create:
            mock_project = Mock()
            mock_project.id = "proj-xyz"
            mock_project.alias = "PRJ-099"
            mock_project.name = "Keys Test"
            mock_project.description = "Keys Test desc"
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-xyz"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            result = await tool_accessor.create_project(
                name="Keys Test",
                product_id="prod-xyz",
                tenant_key="tenant-abc",
            )

            expected_keys = {
                "success",
                "project_id",
                "alias",
                "taxonomy_alias",
                "name",
                "description",
                "mission",
                "status",
                "product_id",
                "created_at",
                "message",
                "project_type",
                "series_number",
            }
            assert set(result.keys()) == expected_keys, (
                f"Expected keys {expected_keys}, got {set(result.keys())}"
            )
