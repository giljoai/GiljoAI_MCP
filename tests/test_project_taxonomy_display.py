"""
Tests for Project Taxonomy Display Integration - Handover 0440c

Tests cover:
- ProjectTypeInfo API schema (api/endpoints/projects/models.py)
- ProjectResponse nested project_type field
- ProjectTypeInfo service schema with from_attributes=True (service_responses.py)
- Service schemas (ProjectDetail, ProjectListItem, ActiveProjectDetail, ProjectData)
  accepting nested ProjectTypeInfo
"""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.endpoints.projects.models import (
    ProjectResponse,
)
from api.endpoints.projects.models import (
    ProjectTypeInfo as ApiProjectTypeInfo,
)
from src.giljo_mcp.schemas.service_responses import (
    ActiveProjectDetail,
    ProjectData,
    ProjectDetail,
    ProjectListItem,
)
from src.giljo_mcp.schemas.service_responses import (
    ProjectTypeInfo as ServiceProjectTypeInfo,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_TYPE_DATA = {
    "id": "type-001",
    "abbreviation": "BE",
    "label": "Backend",
    "color": "#4CAF50",
}


@pytest.fixture
def type_info_dict():
    """Return a plain dict representing a ProjectTypeInfo."""
    return dict(SAMPLE_TYPE_DATA)


@pytest.fixture
def type_info_orm():
    """Return a MagicMock that behaves like a SQLAlchemy ORM ProjectType row."""
    obj = MagicMock()
    obj.id = SAMPLE_TYPE_DATA["id"]
    obj.abbreviation = SAMPLE_TYPE_DATA["abbreviation"]
    obj.label = SAMPLE_TYPE_DATA["label"]
    obj.color = SAMPLE_TYPE_DATA["color"]
    return obj


# ---------------------------------------------------------------------------
# API Schema Tests (api/endpoints/projects/models.py)
# ---------------------------------------------------------------------------


class TestApiProjectTypeInfoSchema:
    """Validate the API-layer ProjectTypeInfo schema."""

    def test_project_type_info_schema(self, type_info_dict):
        """ProjectTypeInfo should accept all four required fields and expose them."""
        info = ApiProjectTypeInfo(**type_info_dict)

        assert info.id == "type-001"
        assert info.abbreviation == "BE"
        assert info.label == "Backend"
        assert info.color == "#4CAF50"

    def test_project_type_info_rejects_missing_fields(self):
        """ProjectTypeInfo should reject construction when required fields are missing."""
        with pytest.raises(Exception):
            ApiProjectTypeInfo(id="type-001", abbreviation="BE")

    def test_project_type_info_serialization(self, type_info_dict):
        """ProjectTypeInfo should round-trip through model_dump correctly."""
        info = ApiProjectTypeInfo(**type_info_dict)
        dumped = info.model_dump()

        assert dumped == type_info_dict


class TestProjectResponseWithNestedType:
    """Validate ProjectResponse accepts nested ProjectTypeInfo."""

    @staticmethod
    def _minimal_response(**overrides):
        """Build a minimal valid ProjectResponse dict with sensible defaults."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        base = {
            "id": "proj-001",
            "alias": "abc123",
            "name": "Test Project",
            "description": "A test project",
            "mission": "Test mission",
            "status": "active",
            "created_at": now,
            "updated_at": now,
            "agent_count": 0,
            "message_count": 0,
        }
        base.update(overrides)
        return base

    def test_project_response_with_nested_type(self, type_info_dict):
        """ProjectResponse should accept a nested ProjectTypeInfo object."""
        data = self._minimal_response(
            project_type_id="type-001",
            project_type=type_info_dict,
            series_number=42,
            subseries="a",
            taxonomy_alias="BE-0042a",
        )
        resp = ProjectResponse(**data)

        assert resp.project_type is not None
        assert resp.project_type.id == "type-001"
        assert resp.project_type.abbreviation == "BE"
        assert resp.project_type.label == "Backend"
        assert resp.project_type.color == "#4CAF50"
        assert resp.series_number == 42
        assert resp.subseries == "a"
        assert resp.taxonomy_alias == "BE-0042a"

    def test_project_response_without_type(self):
        """ProjectResponse should work when project_type is None (unclassified)."""
        data = self._minimal_response()
        resp = ProjectResponse(**data)

        assert resp.project_type is None
        assert resp.project_type_id is None
        assert resp.series_number is None
        assert resp.subseries is None
        assert resp.taxonomy_alias is None

    def test_project_response_serialization_includes_nested_type(self, type_info_dict):
        """model_dump() should include the full nested project_type structure."""
        data = self._minimal_response(
            project_type_id="type-001",
            project_type=type_info_dict,
        )
        resp = ProjectResponse(**data)
        dumped = resp.model_dump()

        assert dumped["project_type"]["abbreviation"] == "BE"
        assert dumped["project_type"]["color"] == "#4CAF50"


# ---------------------------------------------------------------------------
# Service Schema Tests (src/giljo_mcp/schemas/service_responses.py)
# ---------------------------------------------------------------------------


class TestServiceProjectTypeInfo:
    """Validate the service-layer ProjectTypeInfo with from_attributes support."""

    def test_service_project_type_info_from_dict(self, type_info_dict):
        """Service ProjectTypeInfo should construct from a plain dict."""
        info = ServiceProjectTypeInfo(**type_info_dict)

        assert info.id == "type-001"
        assert info.abbreviation == "BE"
        assert info.label == "Backend"
        assert info.color == "#4CAF50"

    def test_service_project_type_info_from_attributes(self, type_info_orm):
        """Service ProjectTypeInfo should construct from an ORM-like object via model_validate."""
        info = ServiceProjectTypeInfo.model_validate(type_info_orm)

        assert info.id == "type-001"
        assert info.abbreviation == "BE"
        assert info.label == "Backend"
        assert info.color == "#4CAF50"

    def test_service_project_type_info_from_attributes_config(self):
        """Verify the model_config enables from_attributes."""
        config = ServiceProjectTypeInfo.model_config
        assert config.get("from_attributes") is True


class TestServiceProjectDetailWithType:
    """Validate that ProjectDetail accepts a nested ProjectTypeInfo."""

    def test_service_project_detail_with_type(self, type_info_dict):
        """ProjectDetail should accept project_type as a nested dict."""
        detail = ProjectDetail(
            id="proj-001",
            name="Backend API",
            status="active",
            tenant_key="tenant-abc",
            project_type_id="type-001",
            project_type=type_info_dict,
            series_number=1,
            subseries=None,
            taxonomy_alias="BE-0001",
        )

        assert detail.project_type is not None
        assert detail.project_type.abbreviation == "BE"
        assert detail.project_type.color == "#4CAF50"
        assert detail.taxonomy_alias == "BE-0001"

    def test_service_project_detail_without_type(self):
        """ProjectDetail should work when project_type is None."""
        detail = ProjectDetail(
            id="proj-002",
            name="Untyped",
            status="inactive",
            tenant_key="tenant-abc",
        )

        assert detail.project_type is None
        assert detail.project_type_id is None

    def test_service_project_detail_from_orm(self, type_info_orm):
        """ProjectDetail should construct from an ORM-like object with nested type."""
        orm_obj = MagicMock()
        orm_obj.id = "proj-001"
        orm_obj.alias = "abc123"
        orm_obj.name = "Backend API"
        orm_obj.mission = "Build the backend"
        orm_obj.description = "Backend project"
        orm_obj.status = "active"
        orm_obj.staging_status = None
        orm_obj.product_id = None
        orm_obj.tenant_key = "tenant-abc"
        orm_obj.execution_mode = "multi_terminal"
        orm_obj.created_at = "2026-01-01T00:00:00Z"
        orm_obj.updated_at = "2026-01-15T00:00:00Z"
        orm_obj.completed_at = None
        orm_obj.agents = []
        orm_obj.agent_count = 0
        orm_obj.message_count = 0
        orm_obj.project_type_id = "type-001"
        orm_obj.project_type = type_info_orm
        orm_obj.series_number = 1
        orm_obj.subseries = None
        orm_obj.taxonomy_alias = "BE-0001"

        detail = ProjectDetail.model_validate(orm_obj)

        assert detail.project_type is not None
        assert detail.project_type.id == "type-001"
        assert detail.project_type.abbreviation == "BE"


class TestServiceProjectListItemWithType:
    """Validate that ProjectListItem accepts a nested ProjectTypeInfo."""

    def test_service_project_list_item_with_type(self, type_info_dict):
        """ProjectListItem should accept project_type as a nested dict."""
        item = ProjectListItem(
            id="proj-003",
            name="Frontend Dashboard",
            status="active",
            tenant_key="tenant-abc",
            created_at="2026-01-01T00:00:00Z",
            updated_at="2026-01-15T00:00:00Z",
            project_type_id="type-002",
            project_type={
                "id": "type-002",
                "abbreviation": "FE",
                "label": "Frontend",
                "color": "#2196F3",
            },
            series_number=3,
            subseries="b",
            taxonomy_alias="FE-0003b",
        )

        assert item.project_type is not None
        assert item.project_type.abbreviation == "FE"
        assert item.project_type.color == "#2196F3"
        assert item.taxonomy_alias == "FE-0003b"

    def test_service_project_list_item_without_type(self):
        """ProjectListItem should work when project_type is None."""
        item = ProjectListItem(
            id="proj-004",
            name="Plain Project",
            status="inactive",
            tenant_key="tenant-abc",
            created_at="2026-02-01T00:00:00Z",
            updated_at="2026-02-01T00:00:00Z",
        )

        assert item.project_type is None
        assert item.project_type_id is None

    def test_service_project_list_item_from_orm(self, type_info_orm):
        """ProjectListItem should construct from an ORM-like object with nested type."""
        orm_obj = MagicMock()
        orm_obj.id = "proj-003"
        orm_obj.name = "Frontend Dashboard"
        orm_obj.mission = "Build the frontend"
        orm_obj.description = "Frontend project"
        orm_obj.status = "active"
        orm_obj.staging_status = None
        orm_obj.tenant_key = "tenant-abc"
        orm_obj.product_id = None
        orm_obj.created_at = "2026-01-01T00:00:00Z"
        orm_obj.updated_at = "2026-01-15T00:00:00Z"
        orm_obj.project_type_id = "type-002"
        orm_obj.project_type = type_info_orm
        orm_obj.series_number = 3
        orm_obj.subseries = "b"
        orm_obj.taxonomy_alias = "FE-0003b"

        item = ProjectListItem.model_validate(orm_obj)

        assert item.project_type is not None
        assert item.project_type.id == "type-001"  # from fixture


class TestServiceActiveProjectDetailWithType:
    """Validate that ActiveProjectDetail accepts a nested ProjectTypeInfo."""

    def test_active_project_detail_with_type(self, type_info_dict):
        """ActiveProjectDetail should accept a nested project_type."""
        detail = ActiveProjectDetail(
            id="proj-005",
            name="Infra Setup",
            status="active",
            project_type_id="type-001",
            project_type=type_info_dict,
            series_number=10,
            taxonomy_alias="BE-0010",
        )

        assert detail.project_type is not None
        assert detail.project_type.abbreviation == "BE"
        assert detail.project_type.color == "#4CAF50"

    def test_active_project_detail_without_type(self):
        """ActiveProjectDetail should work when project_type is None."""
        detail = ActiveProjectDetail(
            id="proj-006",
            name="Quick Fix",
            status="active",
        )

        assert detail.project_type is None


class TestServiceProjectDataWithType:
    """Validate that ProjectData accepts a nested ProjectTypeInfo."""

    def test_project_data_with_type(self, type_info_dict):
        """ProjectData should accept a nested project_type."""
        data = ProjectData(
            id="proj-007",
            name="Security Audit",
            status="inactive",
            project_type_id="type-001",
            project_type=type_info_dict,
            series_number=5,
            subseries="a",
            taxonomy_alias="BE-0005a",
        )

        assert data.project_type is not None
        assert data.project_type.abbreviation == "BE"
        assert data.taxonomy_alias == "BE-0005a"

    def test_project_data_without_type(self):
        """ProjectData should work when project_type is None."""
        data = ProjectData(
            id="proj-008",
            name="Misc Work",
            status="active",
        )

        assert data.project_type is None
        assert data.project_type_id is None

    def test_project_data_serialization_round_trip(self, type_info_dict):
        """ProjectData should serialize and deserialize with nested type intact."""
        original = ProjectData(
            id="proj-009",
            name="Round Trip",
            status="active",
            project_type_id="type-001",
            project_type=type_info_dict,
            series_number=1,
        )

        dumped = original.model_dump()
        restored = ProjectData(**dumped)

        assert restored.project_type is not None
        assert restored.project_type.id == original.project_type.id
        assert restored.project_type.color == original.project_type.color


# ---------------------------------------------------------------------------
# Handover 0440d - Taxonomy Production Hardening Tests
# ---------------------------------------------------------------------------


class TestDeletedProjectExclusion:
    """Verify that soft-deleted projects are excluded from taxonomy namespace queries.

    The four query functions in api/endpoints/project_types/crud_ops.py now filter
    on Project.deleted_at.is_(None) so that deleting a project frees its taxonomy
    slot for reuse. These tests validate that behaviour by inspecting the SQL
    queries built by each function.
    """

    @pytest.fixture
    def mock_session(self):
        """Return an AsyncMock that behaves like a SQLAlchemy AsyncSession.

        The session.execute() call returns a mock result whose methods
        (.scalar_one_or_none, .scalar, .scalars, .all) are pre-wired.
        """
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock(spec=AsyncSession)
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_result.scalar.return_value = None
        mock_result.scalars.return_value.all.return_value = []
        mock_result.all.return_value = []
        session.execute.return_value = mock_result
        return session

    @pytest.mark.asyncio
    async def test_check_series_available_filters_deleted(self, mock_session):
        """check_series_available should include deleted_at IS NULL in query."""
        from api.endpoints.project_types.crud_ops import check_series_available

        result = await check_series_available(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
            series_number=1,
            subseries=None,
        )

        assert result == {"available": True}
        mock_session.execute.assert_awaited_once()
        compiled_sql = str(
            mock_session.execute.call_args[0][0].compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "deleted_at IS NULL" in compiled_sql

    @pytest.mark.asyncio
    async def test_check_series_available_with_subseries_filters_deleted(
        self, mock_session
    ):
        """check_series_available with a subseries still filters deleted_at."""
        from api.endpoints.project_types.crud_ops import check_series_available

        result = await check_series_available(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
            series_number=1,
            subseries="a",
        )

        assert result == {"available": True}
        compiled_sql = str(
            mock_session.execute.call_args[0][0].compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "deleted_at IS NULL" in compiled_sql

    @pytest.mark.asyncio
    async def test_check_series_available_excludes_project_id(self, mock_session):
        """check_series_available with exclude_project_id adds id != clause."""
        from api.endpoints.project_types.crud_ops import check_series_available

        await check_series_available(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
            series_number=1,
            subseries=None,
            exclude_project_id="proj-existing",
        )

        compiled_sql = str(
            mock_session.execute.call_args[0][0].compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "deleted_at IS NULL" in compiled_sql
        assert "proj-existing" in compiled_sql

    @pytest.mark.asyncio
    async def test_get_used_subseries_filters_deleted(self, mock_session):
        """get_used_subseries should include deleted_at IS NULL in query."""
        from api.endpoints.project_types.crud_ops import get_used_subseries

        result = await get_used_subseries(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
            series_number=1,
        )

        assert result == {"used_subseries": []}
        mock_session.execute.assert_awaited_once()
        compiled_sql = str(
            mock_session.execute.call_args[0][0].compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "deleted_at IS NULL" in compiled_sql

    @pytest.mark.asyncio
    async def test_get_used_subseries_excludes_project_id(self, mock_session):
        """get_used_subseries with exclude_project_id adds id != clause."""
        from api.endpoints.project_types.crud_ops import get_used_subseries

        await get_used_subseries(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
            series_number=1,
            exclude_project_id="proj-existing",
        )

        compiled_sql = str(
            mock_session.execute.call_args[0][0].compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "deleted_at IS NULL" in compiled_sql
        assert "proj-existing" in compiled_sql

    @pytest.mark.asyncio
    async def test_get_next_series_number_filters_deleted(self, mock_session):
        """get_next_series_number should include deleted_at IS NULL in query."""
        from api.endpoints.project_types.crud_ops import get_next_series_number

        result = await get_next_series_number(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
        )

        # With no existing projects (scalar returns None), next is 1
        assert result == 1
        mock_session.execute.assert_awaited_once()
        compiled_sql = str(
            mock_session.execute.call_args[0][0].compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "deleted_at IS NULL" in compiled_sql

    @pytest.mark.asyncio
    async def test_get_available_series_numbers_filters_deleted(self, mock_session):
        """get_available_series_numbers should include deleted_at IS NULL in query."""
        from api.endpoints.project_types.crud_ops import get_available_series_numbers

        result = await get_available_series_numbers(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
            limit=5,
        )

        # With no used numbers, returns [1, 2, 3, 4, 5]
        assert result == [1, 2, 3, 4, 5]
        mock_session.execute.assert_awaited_once()
        compiled_sql = str(
            mock_session.execute.call_args[0][0].compile(
                compile_kwargs={"literal_binds": True}
            )
        )
        assert "deleted_at IS NULL" in compiled_sql

    @pytest.mark.asyncio
    async def test_get_available_series_numbers_custom_limit(self, mock_session):
        """get_available_series_numbers respects the limit parameter."""
        from api.endpoints.project_types.crud_ops import get_available_series_numbers

        result = await get_available_series_numbers(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
            limit=3,
        )

        assert result == [1, 2, 3]
        assert len(result) == 3

    @pytest.mark.asyncio
    async def test_check_series_available_returns_unavailable(self, mock_session):
        """check_series_available returns available=False when a matching row exists."""
        from api.endpoints.project_types.crud_ops import check_series_available

        mock_session.execute.return_value.scalar_one_or_none.return_value = (
            "existing-proj-id"
        )

        result = await check_series_available(
            session=mock_session,
            tenant_key="tenant-abc",
            type_id="type-001",
            series_number=1,
            subseries=None,
        )

        assert result == {"available": False}


class TestInputValidation:
    """Verify that FastAPI Query constraints and Pydantic response models exist.

    Handover 0440d added:
    - series_number = Query(ge=1, le=9999) on check_series_number endpoint
    - subseries = Query(default=None, pattern=r"^[a-z]$") on check_series_number
    - Four Pydantic response models for series endpoints
    """

    def test_series_check_response_model_exists(self):
        """SeriesCheckResponse should be importable and have an 'available' bool field."""
        from api.endpoints.projects.models import SeriesCheckResponse

        resp = SeriesCheckResponse(available=True)
        assert resp.available is True

        resp_false = SeriesCheckResponse(available=False)
        assert resp_false.available is False

    def test_series_check_response_rejects_missing_fields(self):
        """SeriesCheckResponse should reject construction without 'available'."""
        from pydantic import ValidationError

        from api.endpoints.projects.models import SeriesCheckResponse

        with pytest.raises(ValidationError):
            SeriesCheckResponse()

    def test_used_subseries_response_model_exists(self):
        """UsedSubseriesResponse should accept a list of strings."""
        from api.endpoints.projects.models import UsedSubseriesResponse

        resp = UsedSubseriesResponse(used_subseries=["a", "b", "c"])
        assert resp.used_subseries == ["a", "b", "c"]

    def test_used_subseries_response_empty_list(self):
        """UsedSubseriesResponse should accept an empty list."""
        from api.endpoints.projects.models import UsedSubseriesResponse

        resp = UsedSubseriesResponse(used_subseries=[])
        assert resp.used_subseries == []

    def test_next_series_response_model_exists(self):
        """NextSeriesResponse should accept a next_series_number int."""
        from api.endpoints.projects.models import NextSeriesResponse

        resp = NextSeriesResponse(next_series_number=42)
        assert resp.next_series_number == 42

    def test_next_series_response_rejects_missing_fields(self):
        """NextSeriesResponse should reject construction without next_series_number."""
        from pydantic import ValidationError

        from api.endpoints.projects.models import NextSeriesResponse

        with pytest.raises(ValidationError):
            NextSeriesResponse()

    def test_available_series_response_model_exists(self):
        """AvailableSeriesResponse should accept a list of integers."""
        from api.endpoints.projects.models import AvailableSeriesResponse

        resp = AvailableSeriesResponse(available_series_numbers=[1, 3, 5, 7])
        assert resp.available_series_numbers == [1, 3, 5, 7]

    def test_available_series_response_empty_list(self):
        """AvailableSeriesResponse should accept an empty list."""
        from api.endpoints.projects.models import AvailableSeriesResponse

        resp = AvailableSeriesResponse(available_series_numbers=[])
        assert resp.available_series_numbers == []

    def test_series_check_response_serialization(self):
        """SeriesCheckResponse should round-trip through model_dump."""
        from api.endpoints.projects.models import SeriesCheckResponse

        resp = SeriesCheckResponse(available=True)
        dumped = resp.model_dump()
        assert dumped == {"available": True}

    def test_used_subseries_response_serialization(self):
        """UsedSubseriesResponse should round-trip through model_dump."""
        from api.endpoints.projects.models import UsedSubseriesResponse

        resp = UsedSubseriesResponse(used_subseries=["a", "z"])
        dumped = resp.model_dump()
        assert dumped == {"used_subseries": ["a", "z"]}

    def test_next_series_response_serialization(self):
        """NextSeriesResponse should round-trip through model_dump."""
        from api.endpoints.projects.models import NextSeriesResponse

        resp = NextSeriesResponse(next_series_number=1)
        dumped = resp.model_dump()
        assert dumped == {"next_series_number": 1}

    def test_available_series_response_serialization(self):
        """AvailableSeriesResponse should round-trip through model_dump."""
        from api.endpoints.projects.models import AvailableSeriesResponse

        resp = AvailableSeriesResponse(available_series_numbers=[2, 4, 6])
        dumped = resp.model_dump()
        assert dumped == {"available_series_numbers": [2, 4, 6]}

    def test_check_series_number_endpoint_has_query_constraints(self):
        """check_series_number endpoint should define Query(ge=1, le=9999) for series_number."""
        import inspect

        from api.endpoints.projects.crud import check_series_number

        sig = inspect.signature(check_series_number)

        series_param = sig.parameters["series_number"]
        # FastAPI Query constraints are stored in .metadata as Ge/Le objects
        series_default = series_param.default
        metadata_strs = [str(m) for m in series_default.metadata]
        assert any("ge=1" in s for s in metadata_strs)
        assert any("le=9999" in s for s in metadata_strs)

    def test_check_series_number_endpoint_subseries_pattern(self):
        """check_series_number endpoint should define Query(pattern=r'^[a-z]$') for subseries."""
        import inspect

        from api.endpoints.projects.crud import check_series_number

        sig = inspect.signature(check_series_number)

        subseries_param = sig.parameters["subseries"]
        subseries_default = subseries_param.default
        metadata_strs = [str(m) for m in subseries_default.metadata]
        assert any("pattern='^[a-z]$'" in s for s in metadata_strs)

    def test_check_series_number_endpoint_subseries_default_none(self):
        """check_series_number endpoint should default subseries to None."""
        import inspect

        from api.endpoints.projects.crud import check_series_number

        sig = inspect.signature(check_series_number)

        subseries_param = sig.parameters["subseries"]
        subseries_default = subseries_param.default
        assert subseries_default.default is None


class TestIntegrityErrorHandling:
    """Verify that ProjectService.create_project handles duplicate taxonomy gracefully.

    Handover 0440d added a unique constraint (uq_project_taxonomy) on
    (tenant_key, project_type_id, series_number, subseries). When an
    IntegrityError referencing that constraint is raised, the service
    should raise AlreadyExistsError with a user-friendly message.
    """

    @pytest.fixture
    def mock_db_manager(self):
        """Return a MagicMock DatabaseManager."""
        from unittest.mock import MagicMock

        return MagicMock()

    @pytest.fixture
    def mock_tenant_manager(self):
        """Return a MagicMock TenantManager."""
        from unittest.mock import MagicMock

        return MagicMock()

    @pytest.fixture
    def mock_session(self):
        """Return an AsyncMock session that can simulate IntegrityError on commit."""
        from unittest.mock import AsyncMock, MagicMock

        session = AsyncMock(spec=AsyncSession)
        session.add = MagicMock()
        return session

    @pytest.fixture
    def project_service(self, mock_db_manager, mock_tenant_manager, mock_session):
        """Create a ProjectService with injected test session."""
        from src.giljo_mcp.services.project_service import ProjectService

        return ProjectService(
            db_manager=mock_db_manager,
            tenant_manager=mock_tenant_manager,
            test_session=mock_session,
        )

    @pytest.mark.asyncio
    async def test_duplicate_taxonomy_raises_already_exists_error(
        self, project_service, mock_session
    ):
        """create_project should raise AlreadyExistsError for uq_project_taxonomy violation."""
        from sqlalchemy.exc import IntegrityError

        from src.giljo_mcp.exceptions import AlreadyExistsError

        mock_session.commit.side_effect = IntegrityError(
            statement="INSERT INTO projects ...",
            params={},
            orig=Exception(
                'duplicate key value violates unique constraint "uq_project_taxonomy"'
            ),
        )

        with pytest.raises(AlreadyExistsError) as exc_info:
            await project_service.create_project(
                name="Duplicate Taxonomy Project",
                mission="Test mission",
                tenant_key="tenant-abc",
                project_type_id="type-001",
                series_number=1,
                subseries="a",
            )

        assert "Taxonomy combination already in use" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_duplicate_taxonomy_error_includes_context(
        self, project_service, mock_session
    ):
        """AlreadyExistsError should include name and tenant_key in context."""
        from sqlalchemy.exc import IntegrityError

        from src.giljo_mcp.exceptions import AlreadyExistsError

        mock_session.commit.side_effect = IntegrityError(
            statement="INSERT INTO projects ...",
            params={},
            orig=Exception(
                'duplicate key value violates unique constraint "uq_project_taxonomy"'
            ),
        )

        with pytest.raises(AlreadyExistsError) as exc_info:
            await project_service.create_project(
                name="Context Check",
                mission="Test mission",
                tenant_key="tenant-xyz",
                project_type_id="type-002",
                series_number=5,
                subseries=None,
            )

        assert exc_info.value.context["name"] == "Context Check"
        assert exc_info.value.context["tenant_key"] == "tenant-xyz"

    @pytest.mark.asyncio
    async def test_non_taxonomy_integrity_error_raises_base_error(
        self, project_service, mock_session
    ):
        """IntegrityError without uq_project_taxonomy should raise BaseGiljoError."""
        from sqlalchemy.exc import IntegrityError

        from src.giljo_mcp.exceptions import BaseGiljoError

        mock_session.commit.side_effect = IntegrityError(
            statement="INSERT INTO projects ...",
            params={},
            orig=Exception(
                'duplicate key value violates unique constraint "uq_projects_name"'
            ),
        )

        with pytest.raises(BaseGiljoError) as exc_info:
            await project_service.create_project(
                name="Other Constraint",
                mission="Test mission",
                tenant_key="tenant-abc",
                project_type_id="type-001",
                series_number=1,
            )

        # Should NOT be AlreadyExistsError specifically
        assert type(exc_info.value) is BaseGiljoError

    @pytest.mark.asyncio
    async def test_already_exists_error_status_code(self):
        """AlreadyExistsError should have status code 409."""
        from src.giljo_mcp.exceptions import AlreadyExistsError

        err = AlreadyExistsError(message="duplicate", context={"name": "test"})
        assert err.default_status_code == 409

    @pytest.mark.asyncio
    async def test_already_exists_error_to_dict(self):
        """AlreadyExistsError.to_dict() should return structured error info."""
        from src.giljo_mcp.exceptions import AlreadyExistsError

        err = AlreadyExistsError(
            message="Taxonomy combination already in use.",
            context={"name": "Test", "tenant_key": "t-1"},
        )
        d = err.to_dict()
        assert d["message"] == "Taxonomy combination already in use."
        assert d["status_code"] == 409
        assert d["context"]["name"] == "Test"
        assert "error_code" in d
        assert "timestamp" in d
