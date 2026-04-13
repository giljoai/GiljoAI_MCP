# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for ToolAccessor.list_projects() and ToolAccessor.update_project_metadata().

Test Coverage:
- list_projects: returns projects for active product, respects status filter, tenant isolation
- update_project_metadata: updates name, description, status; rejects invalid project_id;
  rejects cross-tenant access; validates field lengths; rejects invalid status values
"""

import inspect
from unittest.mock import AsyncMock, Mock, patch

import pytest

from src.giljo_mcp.tools.tool_accessor import ToolAccessor


_PRODUCT_SERVICE_PATH = "src.giljo_mcp.tools.tool_accessor.ProductService"


# ---------------------------------------------------------------------------
# Helper: create a ToolAccessor with mocked dependencies
# ---------------------------------------------------------------------------


def _make_accessor(tenant_key: str = "tenant-test") -> ToolAccessor:
    db_manager = Mock()
    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value=tenant_key)
    return ToolAccessor(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=None,
        test_session=None,
    )


def _mock_project(
    project_id="proj-001",
    name="Test Project",
    description="A test project",
    status="active",
    product_id="prod-001",
    project_type_id=None,
    series_number=None,
    taxonomy_alias=None,
    created_at=None,
    updated_at=None,
):
    """Create a mock project object."""
    proj = Mock()
    proj.id = project_id
    proj.name = name
    proj.description = description
    proj.status = status
    proj.product_id = product_id
    proj.project_type_id = project_type_id
    proj.series_number = series_number
    proj.taxonomy_alias = taxonomy_alias
    proj.created_at = created_at
    proj.updated_at = updated_at
    proj.mission = ""
    proj.execution_mode = "parallel"
    proj.auto_checkin_enabled = False
    proj.auto_checkin_interval = 15
    proj.cancellation_reason = None
    proj.deactivation_reason = None
    proj.early_termination = False
    proj.activated_at = None
    proj.completed_at = None
    proj.project_type = None
    proj.subseries = None
    proj.staging_status = None
    proj.tenant_key = "tenant-test"
    return proj


def _patch_active_product(product_id="prod-001"):
    """Return a patch context for ProductService with a mocked active product."""
    mock_product = Mock()
    mock_product.id = product_id

    p = patch(_PRODUCT_SERVICE_PATH)
    return p, mock_product


# ===========================================================================
# list_projects — Signature Tests
# ===========================================================================


class TestListProjectsSignature:
    """Verify list_projects method signature."""

    def test_method_exists(self):
        assert hasattr(ToolAccessor, "list_projects"), "ToolAccessor must have a list_projects method"

    def test_status_filter_parameter_is_optional(self):
        sig = inspect.signature(ToolAccessor.list_projects)
        params = sig.parameters
        assert "status_filter" in params
        assert params["status_filter"].default == "all"

    def test_tenant_key_parameter_present(self):
        sig = inspect.signature(ToolAccessor.list_projects)
        params = sig.parameters
        assert "tenant_key" in params
        assert params["tenant_key"].default is None


# ===========================================================================
# list_projects — Behavior Tests
# ===========================================================================


class TestListProjectsBehavior:
    """Test list_projects returns correct data and respects filters."""

    @pytest.mark.asyncio
    async def test_returns_projects_for_active_product(self):
        """list_projects should resolve active product and return its projects."""
        accessor = _make_accessor()

        mock_product = Mock()
        mock_product.id = "prod-001"

        mock_list_item = Mock()
        mock_list_item.id = "proj-001"
        mock_list_item.name = "Test Project"
        mock_list_item.description = "A test project description that is long"
        mock_list_item.status = "active"
        mock_list_item.product_id = "prod-001"
        mock_list_item.project_type_id = None
        mock_list_item.series_number = None
        mock_list_item.taxonomy_alias = None
        mock_list_item.created_at = "2026-04-13T00:00:00"

        with (
            patch.object(
                accessor._project_service,
                "list_projects",
                new_callable=AsyncMock,
                return_value=[mock_list_item],
            ),
            patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        ):
            mock_product_svc.return_value.get_active_product = AsyncMock(
                return_value=mock_product,
            )
            result = await accessor.list_projects(tenant_key="tenant-test")

        assert result["success"] is True
        assert len(result["projects"]) == 1
        assert result["projects"][0]["project_id"] == "proj-001"
        assert result["projects"][0]["name"] == "Test Project"

    @pytest.mark.asyncio
    async def test_passes_status_filter_to_service(self):
        """When status_filter is not 'all', it should be passed to ProjectService."""
        accessor = _make_accessor()

        mock_product = Mock()
        mock_product.id = "prod-001"

        with (
            patch.object(
                accessor._project_service,
                "list_projects",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_list,
            patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        ):
            mock_product_svc.return_value.get_active_product = AsyncMock(
                return_value=mock_product,
            )
            await accessor.list_projects(
                status_filter="active",
                tenant_key="tenant-test",
            )

        mock_list.assert_called_once()
        call_kwargs = mock_list.call_args[1]
        assert call_kwargs.get("status") == "active"

    @pytest.mark.asyncio
    async def test_status_filter_all_passes_none(self):
        """status_filter='all' should pass status=None to service."""
        accessor = _make_accessor()

        mock_product = Mock()
        mock_product.id = "prod-001"

        with (
            patch.object(
                accessor._project_service,
                "list_projects",
                new_callable=AsyncMock,
                return_value=[],
            ) as mock_list,
            patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        ):
            mock_product_svc.return_value.get_active_product = AsyncMock(
                return_value=mock_product,
            )
            await accessor.list_projects(
                status_filter="all",
                tenant_key="tenant-test",
            )

        call_kwargs = mock_list.call_args[1]
        assert call_kwargs.get("status") is None

    @pytest.mark.asyncio
    async def test_raises_on_no_active_product(self):
        """Should raise ValidationError when no active product."""
        accessor = _make_accessor()

        with patch(_PRODUCT_SERVICE_PATH) as mock_product_svc:
            mock_product_svc.return_value.get_active_product = AsyncMock(return_value=None)

            with pytest.raises(Exception, match="No active product"):
                await accessor.list_projects(tenant_key="tenant-test")

    @pytest.mark.asyncio
    async def test_description_returned_in_full(self):
        """Full descriptions should be returned without truncation."""
        accessor = _make_accessor()

        mock_product = Mock()
        mock_product.id = "prod-001"

        long_desc = "A" * 300
        mock_list_item = Mock()
        mock_list_item.id = "proj-001"
        mock_list_item.name = "Long Desc"
        mock_list_item.description = long_desc
        mock_list_item.status = "active"
        mock_list_item.product_id = "prod-001"
        mock_list_item.project_type_id = None
        mock_list_item.series_number = None
        mock_list_item.taxonomy_alias = None
        mock_list_item.created_at = "2026-04-13T00:00:00"

        with (
            patch.object(
                accessor._project_service,
                "list_projects",
                new_callable=AsyncMock,
                return_value=[mock_list_item],
            ),
            patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        ):
            mock_product_svc.return_value.get_active_product = AsyncMock(
                return_value=mock_product,
            )
            result = await accessor.list_projects(tenant_key="tenant-test")

        desc = result["projects"][0]["description"]
        assert desc == long_desc
        assert len(desc) == 300

    @pytest.mark.asyncio
    async def test_rejects_invalid_status_filter(self):
        """Invalid status_filter values should raise ValidationError."""
        accessor = _make_accessor()

        with pytest.raises(Exception, match=r"[Ii]nvalid.*status"):
            await accessor.list_projects(
                status_filter="bogus",
                tenant_key="tenant-test",
            )


# ===========================================================================
# update_project_metadata — Signature Tests
# ===========================================================================


class TestUpdateProjectMetadataSignature:
    """Verify update_project_metadata method signature."""

    def test_method_exists(self):
        assert hasattr(ToolAccessor, "update_project_metadata"), (
            "ToolAccessor must have an update_project_metadata method"
        )

    def test_project_id_is_required(self):
        sig = inspect.signature(ToolAccessor.update_project_metadata)
        params = sig.parameters
        assert "project_id" in params
        assert params["project_id"].default is inspect.Parameter.empty

    def test_optional_update_fields(self):
        sig = inspect.signature(ToolAccessor.update_project_metadata)
        params = sig.parameters
        assert params["name"].default is None
        assert params["description"].default is None
        assert params["status"].default is None


# ===========================================================================
# update_project_metadata — Behavior Tests
# ===========================================================================


class TestUpdateProjectMetadataBehavior:
    """Test update_project_metadata validates input and delegates to service."""

    @pytest.mark.asyncio
    async def test_updates_name_successfully(self):
        """Should pass name update through to ProjectService.update_project."""
        accessor = _make_accessor()

        mock_project_data = Mock()
        mock_project_data.id = "proj-001"
        mock_project_data.name = "New Name"
        mock_project_data.description = "Desc"
        mock_project_data.status = "active"
        mock_project_data.product_id = "prod-001"
        mock_project_data.created_at = "2026-04-13T00:00:00"
        mock_project_data.updated_at = "2026-04-13T01:00:00"
        mock_project_data.taxonomy_alias = None
        mock_project_data.series_number = None
        mock_project_data.project_type_id = None

        mock_project_obj = _mock_project(product_id="prod-001")
        mock_active_product = Mock()
        mock_active_product.id = "prod-001"

        with (
            patch.object(
                accessor._project_service,
                "get_project",
                new_callable=AsyncMock,
                return_value=mock_project_obj,
            ),
            patch.object(
                accessor._project_service,
                "update_project",
                new_callable=AsyncMock,
                return_value=mock_project_data,
            ) as mock_update,
            patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        ):
            mock_product_svc.return_value.get_active_product = AsyncMock(
                return_value=mock_active_product,
            )
            result = await accessor.update_project_metadata(
                project_id="proj-001",
                name="New Name",
                tenant_key="tenant-test",
            )

        assert result["success"] is True
        mock_update.assert_called_once()
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["updates"]["name"] == "New Name"

    @pytest.mark.asyncio
    async def test_updates_description_and_status(self):
        """Should pass description and status updates through to service."""
        accessor = _make_accessor()

        mock_project_data = Mock()
        mock_project_data.id = "proj-001"
        mock_project_data.name = "Test"
        mock_project_data.description = "Updated desc"
        mock_project_data.status = "completed"
        mock_project_data.product_id = "prod-001"
        mock_project_data.created_at = "2026-04-13T00:00:00"
        mock_project_data.updated_at = "2026-04-13T01:00:00"
        mock_project_data.taxonomy_alias = None
        mock_project_data.series_number = None
        mock_project_data.project_type_id = None

        mock_project_obj = _mock_project(product_id="prod-001")
        mock_active_product = Mock()
        mock_active_product.id = "prod-001"

        with (
            patch.object(
                accessor._project_service,
                "get_project",
                new_callable=AsyncMock,
                return_value=mock_project_obj,
            ),
            patch.object(
                accessor._project_service,
                "update_project",
                new_callable=AsyncMock,
                return_value=mock_project_data,
            ) as mock_update,
            patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        ):
            mock_product_svc.return_value.get_active_product = AsyncMock(
                return_value=mock_active_product,
            )
            result = await accessor.update_project_metadata(
                project_id="proj-001",
                description="Updated desc",
                status="completed",
                tenant_key="tenant-test",
            )

        assert result["success"] is True
        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["updates"]["description"] == "Updated desc"
        assert call_kwargs["updates"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_rejects_invalid_status_value(self):
        """Invalid status values should raise ValidationError."""
        accessor = _make_accessor()

        with pytest.raises(Exception, match=r"[Ii]nvalid.*status"):
            await accessor.update_project_metadata(
                project_id="proj-001",
                status="bogus",
                tenant_key="tenant-test",
            )

    @pytest.mark.asyncio
    async def test_rejects_name_exceeding_max_length(self):
        """Name over 200 chars should be rejected."""
        accessor = _make_accessor()

        with pytest.raises(Exception, match=r"[Nn]ame.*200|too long|exceed"):
            await accessor.update_project_metadata(
                project_id="proj-001",
                name="X" * 201,
                tenant_key="tenant-test",
            )

    @pytest.mark.asyncio
    async def test_rejects_description_exceeding_max_length(self):
        """Description over 5000 chars should be rejected."""
        accessor = _make_accessor()

        with pytest.raises(Exception, match=r"[Dd]escription.*5000|too long|exceed"):
            await accessor.update_project_metadata(
                project_id="proj-001",
                description="Y" * 5001,
                tenant_key="tenant-test",
            )

    @pytest.mark.asyncio
    async def test_rejects_empty_project_id(self):
        """Empty or whitespace project_id should be rejected."""
        accessor = _make_accessor()

        with pytest.raises(Exception, match=r"[Pp]roject.*required|[Pp]roject.*empty"):
            await accessor.update_project_metadata(
                project_id="  ",
                tenant_key="tenant-test",
            )

    @pytest.mark.asyncio
    async def test_rejects_no_fields_provided(self):
        """Should reject when no update fields are provided."""
        accessor = _make_accessor()

        with pytest.raises(Exception, match=r"[Aa]t least one"):
            await accessor.update_project_metadata(
                project_id="proj-001",
                tenant_key="tenant-test",
            )

    @pytest.mark.asyncio
    async def test_rejects_project_not_in_active_product(self):
        """Should reject if project does not belong to the active product."""
        accessor = _make_accessor()

        mock_project_obj = _mock_project(product_id="prod-OTHER")
        mock_active_product = Mock()
        mock_active_product.id = "prod-001"

        with (
            patch.object(
                accessor._project_service,
                "get_project",
                new_callable=AsyncMock,
                return_value=mock_project_obj,
            ),
            patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        ):
            mock_product_svc.return_value.get_active_product = AsyncMock(
                return_value=mock_active_product,
            )
            with pytest.raises(Exception, match=r"does not belong|not found|active product"):
                await accessor.update_project_metadata(
                    project_id="proj-001",
                    name="New Name",
                    tenant_key="tenant-test",
                )

    @pytest.mark.asyncio
    async def test_only_provided_fields_in_updates(self):
        """When only name is provided, updates dict should not contain description or status."""
        accessor = _make_accessor()

        mock_project_data = Mock()
        mock_project_data.id = "proj-001"
        mock_project_data.name = "Just Name"
        mock_project_data.description = "Orig"
        mock_project_data.status = "active"
        mock_project_data.product_id = "prod-001"
        mock_project_data.created_at = "2026-04-13T00:00:00"
        mock_project_data.updated_at = "2026-04-13T01:00:00"
        mock_project_data.taxonomy_alias = None
        mock_project_data.series_number = None
        mock_project_data.project_type_id = None

        mock_project_obj = _mock_project(product_id="prod-001")
        mock_active_product = Mock()
        mock_active_product.id = "prod-001"

        with (
            patch.object(
                accessor._project_service,
                "get_project",
                new_callable=AsyncMock,
                return_value=mock_project_obj,
            ),
            patch.object(
                accessor._project_service,
                "update_project",
                new_callable=AsyncMock,
                return_value=mock_project_data,
            ) as mock_update,
            patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        ):
            mock_product_svc.return_value.get_active_product = AsyncMock(
                return_value=mock_active_product,
            )
            await accessor.update_project_metadata(
                project_id="proj-001",
                name="Just Name",
                tenant_key="tenant-test",
            )

        call_kwargs = mock_update.call_args[1]
        assert "name" in call_kwargs["updates"]
        assert "description" not in call_kwargs["updates"]
        assert "status" not in call_kwargs["updates"]
