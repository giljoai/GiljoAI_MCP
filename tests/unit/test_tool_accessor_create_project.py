"""
Unit tests for ToolAccessor.create_project() MCP tool.

Test Coverage:
- Method signature: mission is optional, no context_budget, no status param
- Active product resolution when product_id not provided
- Raises ValidationError when no active product exists
- Returns serializable dict (not ORM object)
- Always creates projects with status "inactive"
- Uses tenant_manager fallback when tenant_key not provided
"""

import inspect
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.tools.tool_accessor import ToolAccessor


class TestCreateProjectSignature:
    """Test suite for create_project() method signature validation."""

    def test_mission_parameter_is_optional_with_empty_default(self):
        """Verify mission parameter has default empty string."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        assert "mission" in params, "create_project() must accept mission parameter"
        assert params["mission"].default == "", (
            "mission should default to empty string"
        )

    def test_no_context_budget_parameter(self):
        """Verify context_budget parameter has been removed."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        assert "context_budget" not in params, (
            "context_budget parameter should be removed from create_project()"
        )

    def test_no_status_parameter(self):
        """Verify status parameter has been removed (hardcoded to inactive)."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        assert "status" not in params, (
            "status parameter should be removed from create_project()"
        )

    def test_expected_parameters(self):
        """Verify all expected parameters exist with correct defaults."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        expected = {
            "self": inspect.Parameter.empty,
            "name": inspect.Parameter.empty,
            "mission": "",
            "description": "",
            "product_id": None,
            "tenant_key": None,
        }

        for param_name, default in expected.items():
            assert param_name in params, (
                f"Parameter '{param_name}' should be in signature"
            )
            if default is not inspect.Parameter.empty:
                assert params[param_name].default == default, (
                    f"Parameter '{param_name}' should have default {default!r}"
                )

    def test_tenant_key_parameter_present(self):
        """Verify tenant_key parameter exists with None default."""
        sig = inspect.signature(ToolAccessor.create_project)
        params = sig.parameters

        assert "tenant_key" in params, (
            "create_project() must accept tenant_key parameter"
        )
        assert params["tenant_key"].default is None, (
            "tenant_key should have default value of None"
        )


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
                "name",
                "description",
                "mission",
                "status",
                "product_id",
                "created_at",
                "message",
            }
            assert set(result.keys()) == expected_keys, (
                f"Expected keys {expected_keys}, got {set(result.keys())}"
            )


class TestCreateProjectHardcodedBehavior:
    """Test suite for hardcoded behaviors (status always inactive)."""

    @pytest.mark.asyncio
    async def test_always_creates_with_inactive_status(self):
        """Test that status is always 'inactive' regardless of any other input."""
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
            mock_project.id = "proj-status"
            mock_project.alias = "PRJ-STS"
            mock_project.name = "Status Test"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-status"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Status Test",
                product_id="prod-status",
                tenant_key="tenant-abc",
            )

            # Verify ProjectService was called with status="inactive"
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["status"] == "inactive", (
                "Status must always be 'inactive'"
            )

    @pytest.mark.asyncio
    async def test_mission_defaults_to_empty_string(self):
        """Test that mission defaults to empty string when not provided."""
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
            mock_project.id = "proj-mission"
            mock_project.alias = "PRJ-MSN"
            mock_project.name = "Mission Default Test"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-mission"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Mission Default Test",
                product_id="prod-mission",
                tenant_key="tenant-abc",
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["mission"] == "", (
                "Mission should default to empty string"
            )

    @pytest.mark.asyncio
    async def test_passes_explicit_mission_when_provided(self):
        """Test that an explicitly provided mission is forwarded correctly."""
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
            mock_project.id = "proj-expl"
            mock_project.alias = "PRJ-EXP"
            mock_project.name = "Explicit Mission Test"
            mock_project.description = ""
            mock_project.mission = ""
            mock_project.status = "inactive"
            mock_project.product_id = "prod-expl"
            mock_project.created_at = None
            mock_create.return_value = mock_project

            await tool_accessor.create_project(
                name="Explicit Mission Test",
                mission="Build the REST API for user management",
                product_id="prod-expl",
                tenant_key="tenant-abc",
            )

            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["mission"] == "Build the REST API for user management"
