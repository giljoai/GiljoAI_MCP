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

from api.endpoints.projects.models import (
    ProjectResponse,
    ProjectTypeInfo as ApiProjectTypeInfo,
)
from src.giljo_mcp.schemas.service_responses import (
    ActiveProjectDetail,
    ProjectData,
    ProjectDetail,
    ProjectListItem,
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


@pytest.fixture()
def type_info_dict():
    """Return a plain dict representing a ProjectTypeInfo."""
    return dict(SAMPLE_TYPE_DATA)


@pytest.fixture()
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
