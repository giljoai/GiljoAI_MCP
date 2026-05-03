# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
Unit tests for v1.2.1 list_projects server-side filtering contract.

Covers ProjectService.list_projects_for_mcp() new parameter surface:
- status: str | list[str] | None
- project_type: str | list[str] | None
- taxonomy_alias_prefix: str | None
- created_after / created_before: datetime | None
- completed_after / completed_before: datetime | None
- include_completed: bool (default False) -- new lifecycle filter
- hidden: bool | None

Default behavior change (BREAKING):
- status=None AND include_completed=False  ->  exclude {completed, cancelled}
- status explicitly set                    ->  user wins, ignore include_completed
- hidden defaults to None (do NOT auto-hide hidden projects)

Tenant isolation: every test passes an explicit tenant_key. Cross-tenant
test confirms tenant_key flows through unchanged.
"""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.schemas.responses.project import ProjectListItem, ProjectTypeInfo
from giljo_mcp.services.project_service import (
    LIFECYCLE_FINISHED_STATUSES,
    ProjectService,
)


_TENANT_A = "tenant-aaa"
_TENANT_B = "tenant-bbb"
_PRODUCT_SERVICE_PATH = "giljo_mcp.services.product_service.ProductService"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(tenant_key: str) -> ProjectService:
    db_manager = Mock()
    mock_session = AsyncMock()
    db_manager.get_session_async = Mock(return_value=mock_session)
    db_manager.get_tenant_session_async = Mock(return_value=mock_session)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=False)
    mock_result = Mock()
    mock_result.scalars = Mock(return_value=Mock(all=Mock(return_value=[])))
    mock_session.execute = AsyncMock(return_value=mock_result)

    tenant_manager = Mock()
    tenant_manager.get_current_tenant = Mock(return_value=tenant_key)

    return ProjectService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        websocket_manager=None,
    )


def _make_item(
    *,
    project_id: str = "p-1",
    name: str = "Project",
    status: str = "active",
    product_id: str = "prod-001",
    type_abbrev: str | None = "BE",
    series_number: int | None = 5036,
    subseries: str | None = None,
    hidden: bool = False,
    created_at: datetime | None = None,
    completed_at: datetime | None = None,
    tenant_key: str = _TENANT_A,
) -> ProjectListItem:
    """Build a ProjectListItem with the fields list_projects_for_mcp consumes."""
    created = (created_at or datetime(2026, 1, 1, tzinfo=UTC)).isoformat()
    completed_iso = completed_at.isoformat() if completed_at else None
    type_info = (
        ProjectTypeInfo(id="t-1", abbreviation=type_abbrev, label=type_abbrev or "X", color="#fff")
        if type_abbrev
        else None
    )
    parts = []
    if type_abbrev:
        parts.append(type_abbrev)
    if series_number is not None:
        if parts:
            parts.append("-")
        parts.append(f"{series_number:04d}")
        if subseries:
            parts.append(subseries)
    taxonomy_alias = "".join(parts) if parts else "abc123"
    return ProjectListItem(
        id=project_id,
        name=name,
        mission="",
        description="",
        status=status,
        staging_status=None,
        tenant_key=tenant_key,
        product_id=product_id,
        created_at=created,
        updated_at=created,
        completed_at=completed_iso,
        project_type_id="t-1" if type_abbrev else None,
        project_type=type_info,
        series_number=series_number,
        subseries=subseries,
        taxonomy_alias=taxonomy_alias,
        hidden=hidden,
    )


def _patch_active_product(product_id: str = "prod-001"):
    """Return a contextmanager-style patch object setting an active product."""
    p = patch(_PRODUCT_SERVICE_PATH)
    return p, product_id


async def _call_with_items(service: ProjectService, items, **kwargs):
    """Run list_projects_for_mcp with list_projects() returning the given items."""
    mock_product = Mock()
    mock_product.id = kwargs.pop("active_product_id", "prod-001")
    list_proj_mock = AsyncMock(return_value=items)
    with (
        patch.object(service, "list_projects", list_proj_mock),
        patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
        patch.object(
            service,
            "_build_mcp_project_list",
            new=AsyncMock(
                side_effect=lambda projects, depth, tk: [
                    {
                        "project_id": p.id,
                        "name": p.name,
                        "status": p.status,
                        "taxonomy_alias": p.taxonomy_alias,
                        "hidden": p.hidden,
                        "created_at": p.created_at,
                        "completed_at": p.completed_at,
                        "project_type": (p.project_type.abbreviation if p.project_type else None),
                    }
                    for p in projects
                ]
            ),
        ),
    ):
        mock_product_svc.return_value.get_active_product = AsyncMock(return_value=mock_product)
        result = await service.list_projects_for_mcp(tenant_key=_TENANT_A, **kwargs)
    return result, list_proj_mock


# ---------------------------------------------------------------------------
# Constant exposure
# ---------------------------------------------------------------------------


class TestLifecycleFinishedConstant:
    def test_lifecycle_finished_constant_exposed(self):
        # BE-5037 follow-up: extended to all four lifecycle-finished statuses
        # so default exclusion bucket matches the frontend StatusBadge enum.
        assert frozenset({"completed", "cancelled", "terminated", "deleted"}) == LIFECYCLE_FINISHED_STATUSES


# ---------------------------------------------------------------------------
# Default behavior (BREAKING change)
# ---------------------------------------------------------------------------


class TestDefaultLifecycleFilter:
    @pytest.mark.asyncio
    async def test_default_excludes_all_lifecycle_finished(self):
        """BE-5037 follow-up: default exclusion covers the full finished set
        {completed, cancelled, terminated, deleted}.

        On dogfood at the time of this test, two projects (INF-0002 Ops Panel
        and BE-5006 BE-SPRINT-002f) carry status=='terminated'. Before this
        change they leaked through the default response because terminated was
        not in the exclusion bucket; now they are filtered out by default.
        """
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="a", status="active"),
            _make_item(project_id="b", status="inactive"),
            _make_item(project_id="c", status="completed"),
            _make_item(project_id="d", status="cancelled"),
            _make_item(project_id="t1", status="terminated"),
            _make_item(project_id="t2", status="terminated"),
        ]
        result, _ = await _call_with_items(service, items)
        ids = {p["project_id"] for p in result["projects"]}
        # 6 in -> 2 out (active + inactive). Mirrors the dogfood 24->22 drop:
        # the two terminated rows are excluded by default.
        assert ids == {"a", "b"}, "Default must exclude completed, cancelled, terminated, deleted"

    @pytest.mark.asyncio
    async def test_default_includes_hidden_rows(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="a", status="active", hidden=False),
            _make_item(project_id="b", status="active", hidden=True),
        ]
        result, _ = await _call_with_items(service, items)
        ids = {p["project_id"] for p in result["projects"]}
        assert ids == {"a", "b"}, "hidden=None default must NOT auto-filter hidden"

    @pytest.mark.asyncio
    async def test_include_completed_true_returns_finished(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="a", status="active"),
            _make_item(project_id="c", status="completed"),
            _make_item(project_id="d", status="cancelled"),
        ]
        result, _ = await _call_with_items(service, items, include_completed=True)
        ids = {p["project_id"] for p in result["projects"]}
        assert ids == {"a", "c", "d"}

    @pytest.mark.asyncio
    async def test_explicit_status_overrides_include_completed(self):
        """When status is explicitly set, include_completed is ignored."""
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="c1", status="completed"),
            _make_item(project_id="c2", status="completed"),
            _make_item(project_id="a1", status="active"),
        ]
        result, _ = await _call_with_items(service, items, status="completed", include_completed=False)
        ids = {p["project_id"] for p in result["projects"]}
        assert ids == {"c1", "c2"}


# ---------------------------------------------------------------------------
# Status filter
# ---------------------------------------------------------------------------


class TestStatusFilter:
    @pytest.mark.asyncio
    async def test_status_string_single(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="a", status="active"),
            _make_item(project_id="i", status="inactive"),
        ]
        result, _ = await _call_with_items(service, items, status="active")
        assert {p["project_id"] for p in result["projects"]} == {"a"}

    @pytest.mark.asyncio
    async def test_status_list_or_within_field(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="a", status="active"),
            _make_item(project_id="i", status="inactive"),
            _make_item(project_id="c", status="completed"),
        ]
        result, _ = await _call_with_items(service, items, status=["active", "inactive"])
        assert {p["project_id"] for p in result["projects"]} == {"a", "i"}

    @pytest.mark.asyncio
    async def test_invalid_status_raises_validation_error(self):
        service = _make_service(_TENANT_A)
        with pytest.raises(ValidationError) as exc_info:
            await service.list_projects_for_mcp(tenant_key=_TENANT_A, status="bogus")
        # Error message must list valid values
        assert "active" in str(exc_info.value)
        assert "bogus" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invalid_status_in_list_raises(self):
        service = _make_service(_TENANT_A)
        with pytest.raises(ValidationError):
            await service.list_projects_for_mcp(tenant_key=_TENANT_A, status=["active", "bogus"])

    @pytest.mark.asyncio
    async def test_status_terminated_returns_only_terminated(self):
        """BE-5037 follow-up: status='terminated' must be a valid filter value
        (was rejected as 'bogus' by the v1.2.1 4-value enum). Returns only
        rows where status=='terminated'.
        """
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="a", status="active"),
            _make_item(project_id="t1", status="terminated"),
            _make_item(project_id="t2", status="terminated"),
            _make_item(project_id="c", status="completed"),
        ]
        result, _ = await _call_with_items(service, items, status="terminated")
        assert {p["project_id"] for p in result["projects"]} == {"t1", "t2"}

    @pytest.mark.asyncio
    async def test_status_deleted_filter_validates(self):
        """status='deleted' must validate (no ValidationError).

        At runtime, ProjectRepository.list_projects() special-cases
        status='deleted' by switching the soft-delete clause from
        deleted_at IS NULL (default) to deleted_at IS NOT NULL when the
        caller supplies that status, so soft-deleted rows ARE reachable
        when the agent asks for them by status. This unit test pins the
        validation contract and the in-memory status filter; the
        repository-layer reachability is covered by repository tests.
        """
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="a", status="active"),
            _make_item(project_id="d1", status="deleted"),
        ]
        result, _ = await _call_with_items(service, items, status="deleted")
        # Only the deleted row should pass the in-memory status filter.
        assert {p["project_id"] for p in result["projects"]} == {"d1"}

    @pytest.mark.asyncio
    async def test_status_validation_error_lists_all_six_values(self):
        """Validation message must enumerate all 6 valid statuses so agents
        get an actionable error.
        """
        service = _make_service(_TENANT_A)
        with pytest.raises(ValidationError) as exc_info:
            await service.list_projects_for_mcp(tenant_key=_TENANT_A, status="bogus")
        msg = str(exc_info.value)
        for expected in (
            "active",
            "inactive",
            "completed",
            "cancelled",
            "terminated",
            "deleted",
        ):
            assert expected in msg, f"Validation message missing '{expected}': {msg}"


# ---------------------------------------------------------------------------
# Project type filter
# ---------------------------------------------------------------------------


class TestProjectTypeFilter:
    @pytest.mark.asyncio
    async def test_project_type_single(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="be1", type_abbrev="BE"),
            _make_item(project_id="fe1", type_abbrev="FE"),
        ]
        with patch.object(
            ProjectService,
            "_get_valid_project_types",
            new=AsyncMock(return_value=[{"abbreviation": "BE"}, {"abbreviation": "FE"}]),
        ):
            result, _ = await _call_with_items(service, items, project_type="BE")
        assert {p["project_id"] for p in result["projects"]} == {"be1"}

    @pytest.mark.asyncio
    async def test_project_type_list(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="be1", type_abbrev="BE"),
            _make_item(project_id="fe1", type_abbrev="FE"),
            _make_item(project_id="inf1", type_abbrev="INF"),
        ]
        with patch.object(
            ProjectService,
            "_get_valid_project_types",
            new=AsyncMock(
                return_value=[
                    {"abbreviation": "BE"},
                    {"abbreviation": "FE"},
                    {"abbreviation": "INF"},
                ]
            ),
        ):
            result, _ = await _call_with_items(service, items, project_type=["BE", "INF"])
        assert {p["project_id"] for p in result["projects"]} == {"be1", "inf1"}

    @pytest.mark.asyncio
    async def test_invalid_project_type_raises(self):
        service = _make_service(_TENANT_A)
        with (
            patch.object(
                ProjectService,
                "_get_valid_project_types",
                new=AsyncMock(return_value=[{"abbreviation": "BE"}]),
            ),
            pytest.raises(ValidationError) as exc_info,
        ):
            await service.list_projects_for_mcp(tenant_key=_TENANT_A, project_type="BOGUS")
        assert "BOGUS" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Taxonomy alias prefix
# ---------------------------------------------------------------------------


class TestTaxonomyAliasPrefix:
    @pytest.mark.asyncio
    async def test_prefix_matches_series_subset(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="x1", type_abbrev="BE", series_number=5036),
            _make_item(project_id="x2", type_abbrev="BE", series_number=5099),
            _make_item(project_id="x3", type_abbrev="BE", series_number=5100),
        ]
        result, _ = await _call_with_items(service, items, taxonomy_alias_prefix="BE-50")
        ids = {p["project_id"] for p in result["projects"]}
        assert ids == {"x1", "x2"}, "BE-50 must match BE-5036, BE-5099 but NOT BE-5100"

    @pytest.mark.asyncio
    async def test_prefix_exact_match(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="x1", type_abbrev="BE", series_number=5036),
            _make_item(project_id="x2", type_abbrev="BE", series_number=5037),
        ]
        result, _ = await _call_with_items(service, items, taxonomy_alias_prefix="BE-5036")
        assert {p["project_id"] for p in result["projects"]} == {"x1"}


# ---------------------------------------------------------------------------
# Date range filters
# ---------------------------------------------------------------------------


class TestDateRangeFilters:
    @pytest.mark.asyncio
    async def test_created_after_before(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="old", created_at=datetime(2025, 1, 1, tzinfo=UTC)),
            _make_item(project_id="mid", created_at=datetime(2026, 1, 15, tzinfo=UTC)),
            _make_item(project_id="new", created_at=datetime(2026, 6, 1, tzinfo=UTC)),
        ]
        result, _ = await _call_with_items(
            service,
            items,
            created_after=datetime(2026, 1, 1, tzinfo=UTC),
            created_before=datetime(2026, 5, 1, tzinfo=UTC),
        )
        assert {p["project_id"] for p in result["projects"]} == {"mid"}

    @pytest.mark.asyncio
    async def test_completed_after_before(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(
                project_id="early",
                status="completed",
                completed_at=datetime(2026, 1, 5, tzinfo=UTC),
            ),
            _make_item(
                project_id="late",
                status="completed",
                completed_at=datetime(2026, 6, 5, tzinfo=UTC),
            ),
        ]
        result, _ = await _call_with_items(
            service,
            items,
            include_completed=True,
            completed_after=datetime(2026, 5, 1, tzinfo=UTC),
        )
        assert {p["project_id"] for p in result["projects"]} == {"late"}


# ---------------------------------------------------------------------------
# Combination filters
# ---------------------------------------------------------------------------


class TestCombinationFilters:
    @pytest.mark.asyncio
    async def test_status_and_project_type_intersection(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="be_active", status="active", type_abbrev="BE"),
            _make_item(project_id="fe_active", status="active", type_abbrev="FE"),
            _make_item(project_id="be_inactive", status="inactive", type_abbrev="BE"),
        ]
        with patch.object(
            ProjectService,
            "_get_valid_project_types",
            new=AsyncMock(return_value=[{"abbreviation": "BE"}, {"abbreviation": "FE"}]),
        ):
            result, _ = await _call_with_items(
                service,
                items,
                status="active",
                project_type="BE",
            )
        assert {p["project_id"] for p in result["projects"]} == {"be_active"}


# ---------------------------------------------------------------------------
# Hidden filter
# ---------------------------------------------------------------------------


class TestHiddenFilter:
    @pytest.mark.asyncio
    async def test_hidden_true_only_hidden(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="v", hidden=False),
            _make_item(project_id="h", hidden=True),
        ]
        result, _ = await _call_with_items(service, items, hidden=True)
        assert {p["project_id"] for p in result["projects"]} == {"h"}

    @pytest.mark.asyncio
    async def test_hidden_false_only_visible(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="v", hidden=False),
            _make_item(project_id="h", hidden=True),
        ]
        result, _ = await _call_with_items(service, items, hidden=False)
        assert {p["project_id"] for p in result["projects"]} == {"v"}

    @pytest.mark.asyncio
    async def test_hidden_none_returns_both(self):
        service = _make_service(_TENANT_A)
        items = [
            _make_item(project_id="v", hidden=False),
            _make_item(project_id="h", hidden=True),
        ]
        result, _ = await _call_with_items(service, items)  # default hidden=None
        assert {p["project_id"] for p in result["projects"]} == {"v", "h"}

    @pytest.mark.asyncio
    async def test_hidden_field_present_in_payload_regardless_of_filter(self):
        service = _make_service(_TENANT_A)
        items = [_make_item(project_id="v", hidden=False), _make_item(project_id="h", hidden=True)]
        result, _ = await _call_with_items(service, items, hidden=True)
        for row in result["projects"]:
            assert "hidden" in row, "hidden column must remain in row payload"


# ---------------------------------------------------------------------------
# Tenant isolation
# ---------------------------------------------------------------------------


class TestTenantIsolation:
    @pytest.mark.asyncio
    async def test_tenant_key_flows_through(self):
        for tenant_key, product_id in ((_TENANT_A, "prod-aaa"), (_TENANT_B, "prod-bbb")):
            service = _make_service(tenant_key)
            mock_product = Mock()
            mock_product.id = product_id
            list_proj_mock = AsyncMock(return_value=[])
            with (
                patch.object(service, "list_projects", list_proj_mock),
                patch(_PRODUCT_SERVICE_PATH) as mock_product_svc,
                patch.object(service, "_build_mcp_project_list", new=AsyncMock(return_value=[])),
            ):
                mock_product_svc.return_value.get_active_product = AsyncMock(return_value=mock_product)
                result = await service.list_projects_for_mcp(tenant_key=tenant_key)
            assert result["product_id"] == product_id
            # tenant_key passed to the inner list_projects call
            kwargs = list_proj_mock.call_args.kwargs
            assert kwargs.get("tenant_key") == tenant_key


# ---------------------------------------------------------------------------
# MCP tool surface (ToolAccessor) -- forwards new params
# ---------------------------------------------------------------------------


class TestToolAccessorListProjectsSurface:
    """ToolAccessor.list_projects must accept and forward the new params."""

    def test_tool_accessor_signature_exposes_new_params(self):
        import inspect

        from giljo_mcp.tools.tool_accessor import ToolAccessor

        sig = inspect.signature(ToolAccessor.list_projects)
        params = sig.parameters
        for new in (
            "status",
            "project_type",
            "taxonomy_alias_prefix",
            "created_after",
            "created_before",
            "completed_after",
            "completed_before",
            "include_completed",
            "hidden",
        ):
            assert new in params, f"ToolAccessor.list_projects must expose '{new}'"

    @pytest.mark.asyncio
    async def test_tool_accessor_forwards_to_service(self):
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        accessor = object.__new__(ToolAccessor)
        accessor._project_service = Mock()
        accessor._project_service.list_projects_for_mcp = AsyncMock(return_value={"projects": []})
        accessor._websocket_manager = None

        await accessor.list_projects(
            status="active",
            project_type=["BE", "FE"],
            taxonomy_alias_prefix="BE-50",
            include_completed=True,
            hidden=False,
            tenant_key=_TENANT_A,
        )
        kwargs = accessor._project_service.list_projects_for_mcp.call_args.kwargs
        assert kwargs["status"] == "active"
        assert kwargs["project_type"] == ["BE", "FE"]
        assert kwargs["taxonomy_alias_prefix"] == "BE-50"
        assert kwargs["include_completed"] is True
        assert kwargs["hidden"] is False


# ---------------------------------------------------------------------------
# Regression: list_projects vs fetch_context status agreement
# ---------------------------------------------------------------------------
#
# Reported bug: list_projects(status="inactive") returned a project that
# fetch_context(categories=["project"]) reported as status="completed". The
# same window also showed list_projects ignoring its status filter (returning
# all rows regardless of value). These regressions pin the contract:
#
#  1) The status filter must filter for EVERY canonical ProjectStatus value.
#  2) After a status transition, the next list_projects call must reflect it
#     (no stale cached row).
#  3) For a given (tenant_key, project_id), list_projects and the underlying
#     get_project read path must agree on the status value.


class TestStatusFilterCoversEntireEnum:
    """Parametrize over every ProjectStatus value: each must filter precisely."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "target_status",
        [s.value for s in __import__("giljo_mcp.domain.project_status", fromlist=["ProjectStatus"]).ProjectStatus],
    )
    async def test_status_filter_returns_only_matching_rows(self, target_status):
        from giljo_mcp.domain.project_status import ProjectStatus

        service = _make_service(_TENANT_A)
        items = [_make_item(project_id=f"id-{s.value}", status=s.value) for s in ProjectStatus]
        result, _ = await _call_with_items(service, items, status=target_status)
        ids = {p["project_id"] for p in result["projects"]}
        assert ids == {f"id-{target_status}"}, (
            f"status={target_status!r} must return exactly the row with that status; got {ids}"
        )


class TestStatusTransitionReflectedInList:
    """After a status transition, list_projects reflects the new value.

    This is a read-path regression: calling list_projects twice across a
    transition must return the row under its new status, never under the old.
    No sleeps, no caches in between -- if a cache layer is ever introduced,
    this test pins that it must be invalidated on write.
    """

    @pytest.mark.asyncio
    async def test_transition_active_to_completed_visible_in_next_call(self):
        service = _make_service(_TENANT_A)

        before = [_make_item(project_id="p-x", status="active")]
        result_active, _ = await _call_with_items(service, before, status="active")
        assert {p["project_id"] for p in result_active["projects"]} == {"p-x"}

        result_completed_pre, _ = await _call_with_items(service, before, status="completed")
        assert {p["project_id"] for p in result_completed_pre["projects"]} == set()

        after = [_make_item(project_id="p-x", status="completed")]
        result_completed, _ = await _call_with_items(service, after, status="completed")
        assert {p["project_id"] for p in result_completed["projects"]} == {"p-x"}, (
            "After transition active->completed, status='completed' filter must include the row"
        )

        result_active_post, _ = await _call_with_items(service, after, status="active")
        assert {p["project_id"] for p in result_active_post["projects"]} == set(), (
            "After transition active->completed, status='active' filter must NOT include the row"
        )


class TestListProjectsAndFetchContextAgree:
    """list_projects rows and the underlying get_project read path agree on status.

    Both paths read Project.status from the same model attribute. This
    regression asserts that the value flowing into the list payload (via
    ProjectListItem.status -> _build_mcp_project_list) matches the value the
    fetch_context project category reads (get_project -> project.status).
    Catches drift if either path ever introduces a derived/cached column.
    """

    @pytest.mark.asyncio
    @pytest.mark.parametrize("status_value", ["inactive", "active", "completed"])
    async def test_list_and_get_project_return_same_status_string(self, status_value):
        from unittest.mock import MagicMock

        from giljo_mcp.tools.context_tools.get_project import get_project

        service = _make_service(_TENANT_A)
        items = [_make_item(project_id="p-1", status=status_value)]
        # include_completed=True so 'completed' is not excluded by the default
        # lifecycle filter; we are testing read-path parity, not the default.
        result, _ = await _call_with_items(service, items, include_completed=True)
        list_status = next(p["status"] for p in result["projects"] if p["project_id"] == "p-1")

        fake_project = MagicMock()
        fake_project.name = "n"
        fake_project.alias = "abc123"
        fake_project.description = "d"
        fake_project.mission = "m"
        fake_project.status = status_value
        fake_project.staging_status = None
        fake_project.orchestrator_summary = None

        fake_session = AsyncMock()
        fake_session.__aenter__ = AsyncMock(return_value=fake_session)
        fake_session.__aexit__ = AsyncMock(return_value=False)
        fake_result = Mock()
        fake_result.scalar_one_or_none = Mock(return_value=fake_project)
        fake_session.execute = AsyncMock(return_value=fake_result)
        fake_db_manager = Mock()
        fake_db_manager.get_session_async = Mock(return_value=fake_session)

        ctx_result = await get_project(
            project_id="p-1",
            tenant_key=_TENANT_A,
            include_summary=False,
            db_manager=fake_db_manager,
        )
        ctx_status = ctx_result["data"]["status"]

        assert str(list_status) == str(ctx_status) == status_value, (
            f"list_projects status={list_status!r} but fetch_context status={ctx_status!r}"
        )
