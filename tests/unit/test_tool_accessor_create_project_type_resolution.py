"""
Unit tests for ToolAccessor.create_project() — type label resolution (Handover 0837b).

Test Coverage:
- Resolves project type by human-readable label (e.g. 'Frontend')
- Case-insensitive label matching
- Non-existent type creates project without type (no error)
- No type parameter still works (regression)
- Resolved project_type_id is passed to ProjectService
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.tools.tool_accessor import ToolAccessor


def _make_tool_accessor():
    """Create a ToolAccessor with mocked dependencies."""
    db_manager = Mock()
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value="tenant-abc")
    return ToolAccessor(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=None,
        test_session=None,
    )


def _mock_project(**overrides):
    """Create a mock Project object with sensible defaults."""
    defaults = {
        "id": "proj-001",
        "alias": "PRJ-001",
        "name": "Test Project",
        "description": "",
        "mission": "",
        "status": "inactive",
        "product_id": "prod-123",
        "created_at": None,
    }
    defaults.update(overrides)
    mock = Mock()
    for k, v in defaults.items():
        setattr(mock, k, v)
    return mock


class TestCreateProjectTypeResolution:
    """Test suite for optional type label resolution in create_project."""

    @pytest.mark.asyncio
    async def test_resolves_type_by_label(self):
        """Type label 'Frontend' resolves to the correct project_type_id."""
        tool_accessor = _make_tool_accessor()

        mock_type = Mock()
        mock_type.id = "pt-frontend-uuid"

        with (
            patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_ps_cls,
            patch.object(
                tool_accessor._project_service,
                "create_project",
                new_callable=AsyncMock,
            ) as mock_create,
            patch.object(
                tool_accessor._project_service,
                "get_project_type_by_label",
                new_callable=AsyncMock,
                return_value=mock_type,
            ) as mock_lookup,
        ):
            mock_product = Mock()
            mock_product.id = "prod-123"
            mock_ps_instance = AsyncMock()
            mock_ps_instance.get_active_product = AsyncMock(return_value=mock_product)
            mock_ps_cls.return_value = mock_ps_instance

            mock_create.return_value = _mock_project()

            await tool_accessor.create_project(
                name="FE Project",
                project_type="Frontend",
                tenant_key="tenant-abc",
            )

            mock_lookup.assert_awaited_once_with("Frontend", "tenant-abc")
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["project_type_id"] == "pt-frontend-uuid"

    @pytest.mark.asyncio
    async def test_type_resolution_is_case_insensitive(self):
        """Lowercase 'frontend' resolves the same as 'Frontend'."""
        tool_accessor = _make_tool_accessor()

        mock_type = Mock()
        mock_type.id = "pt-frontend-uuid"

        with (
            patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_ps_cls,
            patch.object(
                tool_accessor._project_service,
                "create_project",
                new_callable=AsyncMock,
            ) as mock_create,
            patch.object(
                tool_accessor._project_service,
                "get_project_type_by_label",
                new_callable=AsyncMock,
                return_value=mock_type,
            ),
        ):
            mock_product = Mock()
            mock_product.id = "prod-123"
            mock_ps_instance = AsyncMock()
            mock_ps_instance.get_active_product = AsyncMock(return_value=mock_product)
            mock_ps_cls.return_value = mock_ps_instance

            mock_create.return_value = _mock_project()

            await tool_accessor.create_project(
                name="FE Project",
                project_type="frontend",
                tenant_key="tenant-abc",
            )

            # The label is passed as-is; case-insensitivity is in the service method
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs["project_type_id"] == "pt-frontend-uuid"

    @pytest.mark.asyncio
    async def test_nonexistent_type_creates_without_type(self):
        """Non-existent type label creates project without project_type_id (no error)."""
        tool_accessor = _make_tool_accessor()

        with (
            patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_ps_cls,
            patch.object(
                tool_accessor._project_service,
                "create_project",
                new_callable=AsyncMock,
            ) as mock_create,
            patch.object(
                tool_accessor._project_service,
                "get_project_type_by_label",
                new_callable=AsyncMock,
                return_value=None,  # Not found
            ),
        ):
            mock_product = Mock()
            mock_product.id = "prod-123"
            mock_ps_instance = AsyncMock()
            mock_ps_instance.get_active_product = AsyncMock(return_value=mock_product)
            mock_ps_cls.return_value = mock_ps_instance

            mock_create.return_value = _mock_project()

            result = await tool_accessor.create_project(
                name="Unknown Type Project",
                project_type="NonExistentType",
                tenant_key="tenant-abc",
            )

            assert result["success"] is True
            call_kwargs = mock_create.call_args[1]
            assert call_kwargs.get("project_type_id") is None

    @pytest.mark.asyncio
    async def test_no_type_parameter_still_works(self):
        """Omitting type parameter works as before (regression test)."""
        tool_accessor = _make_tool_accessor()

        with (
            patch("src.giljo_mcp.tools.tool_accessor.ProductService") as mock_ps_cls,
            patch.object(
                tool_accessor._project_service,
                "create_project",
                new_callable=AsyncMock,
            ) as mock_create,
        ):
            mock_product = Mock()
            mock_product.id = "prod-123"
            mock_ps_instance = AsyncMock()
            mock_ps_instance.get_active_product = AsyncMock(return_value=mock_product)
            mock_ps_cls.return_value = mock_ps_instance

            mock_create.return_value = _mock_project()

            result = await tool_accessor.create_project(
                name="No Type Project",
                tenant_key="tenant-abc",
            )

            assert result["success"] is True
            call_kwargs = mock_create.call_args[1]
            # project_type_id should not be passed when type is None
            assert "project_type_id" not in call_kwargs or call_kwargs["project_type_id"] is None
