# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for ProjectService helper methods extracted from update_project.

Tests cover:
- _apply_project_updates: field validation, allowed fields, execution_mode lock
- _build_project_data: DTO construction from Project model
"""

from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from src.giljo_mcp.exceptions import ProjectStateError
from src.giljo_mcp.schemas.service_responses import ProjectData
from src.giljo_mcp.services.project_service import ProjectService


@pytest.fixture
def project_service():
    """Create a ProjectService with mocked dependencies."""
    db_manager = Mock()
    tenant_manager = Mock()
    return ProjectService(db_manager, tenant_manager)


@pytest.fixture
def mock_project():
    """Create a mock Project model with all fields populated."""
    project = Mock()
    project.id = "proj-001"
    project.name = "Original Name"
    project.status = "active"
    project.mission = None
    project.description = "Original Description"
    project.execution_mode = "orchestrated"
    project.cancellation_reason = None
    project.deactivation_reason = None
    project.early_termination = False
    project.auto_checkin_enabled = False
    project.auto_checkin_interval = 10
    project.created_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    project.updated_at = datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)
    project.activated_at = datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)
    project.completed_at = None
    project.product_id = "product-001"
    project.project_type_id = "type-001"
    project_type_mock = Mock()
    project_type_mock.id = "type-001"
    project_type_mock.abbreviation = "FT"
    project_type_mock.label = "Feature"
    project_type_mock.color = "#FF0000"
    project.project_type = project_type_mock
    project.series_number = 42
    project.subseries = "a"
    project.taxonomy_alias = "0042a"
    return project


class TestApplyProjectUpdates:
    """Tests for ProjectService._apply_project_updates"""

    def test_applies_allowed_name_field(self, project_service, mock_project):
        """Applying name update sets the attribute on the project."""
        project_service._apply_project_updates(mock_project, {"name": "New Name"})
        assert mock_project.name == "New Name"

    def test_applies_allowed_description_field(self, project_service, mock_project):
        """Applying description update sets the attribute on the project."""
        project_service._apply_project_updates(mock_project, {"description": "New Desc"})
        assert mock_project.description == "New Desc"

    def test_applies_allowed_mission_field(self, project_service, mock_project):
        """Applying mission update sets the attribute on the project."""
        project_service._apply_project_updates(mock_project, {"mission": "New Mission"})
        assert mock_project.mission == "New Mission"

    def test_applies_allowed_status_field(self, project_service, mock_project):
        """Applying status update sets the attribute on the project."""
        project_service._apply_project_updates(mock_project, {"status": "completed"})
        assert mock_project.status == "completed"

    def test_applies_multiple_fields(self, project_service, mock_project):
        """Applying multiple updates sets all allowed attributes."""
        project_service._apply_project_updates(mock_project, {
            "name": "Updated",
            "description": "Updated Desc",
            "series_number": 99,
        })
        assert mock_project.name == "Updated"
        assert mock_project.description == "Updated Desc"
        assert mock_project.series_number == 99

    def test_ignores_disallowed_fields(self, project_service, mock_project):
        """Fields not in the allowed set are silently ignored."""
        original_id = mock_project.id
        project_service._apply_project_updates(mock_project, {"id": "hacked-id", "name": "Valid"})
        assert mock_project.id == original_id
        assert mock_project.name == "Valid"

    def test_sets_updated_at_timestamp(self, project_service, mock_project):
        """_apply_project_updates always sets updated_at to current UTC time."""
        before = datetime.now(timezone.utc)
        project_service._apply_project_updates(mock_project, {"name": "Updated"})
        after = datetime.now(timezone.utc)
        assert before <= mock_project.updated_at <= after

    def test_raises_on_execution_mode_change_after_staging(self, project_service, mock_project):
        """Cannot change execution_mode when mission is already set (post-staging)."""
        mock_project.mission = "Existing mission"
        with pytest.raises(ProjectStateError):
            project_service._apply_project_updates(
                mock_project, {"execution_mode": "cli"}
            )

    def test_allows_execution_mode_change_when_no_mission(self, project_service, mock_project):
        """Can change execution_mode when mission is None."""
        mock_project.mission = None
        project_service._apply_project_updates(mock_project, {"execution_mode": "cli"})
        assert mock_project.execution_mode == "cli"

    def test_allows_execution_mode_change_when_mission_empty(self, project_service, mock_project):
        """Can change execution_mode when mission is empty/whitespace."""
        mock_project.mission = "   "
        project_service._apply_project_updates(mock_project, {"execution_mode": "cli"})
        assert mock_project.execution_mode == "cli"

    def test_all_allowed_fields_are_accepted(self, project_service, mock_project):
        """All nine allowed fields are applied when provided."""
        updates = {
            "name": "N",
            "description": "D",
            "mission": "M",
            "execution_mode": "cli",
            "status": "completed",
            "completed_at": datetime(2026, 3, 1, tzinfo=timezone.utc),
            "project_type_id": "type-new",
            "series_number": 100,
            "subseries": "b",
        }
        # mission is None so execution_mode is allowed
        mock_project.mission = None
        project_service._apply_project_updates(mock_project, updates)
        assert mock_project.name == "N"
        assert mock_project.description == "D"
        assert mock_project.mission == "M"
        assert mock_project.execution_mode == "cli"
        assert mock_project.status == "completed"
        assert mock_project.completed_at == datetime(2026, 3, 1, tzinfo=timezone.utc)
        assert mock_project.project_type_id == "type-new"
        assert mock_project.series_number == 100
        assert mock_project.subseries == "b"


class TestBuildProjectData:
    """Tests for ProjectService._build_project_data"""

    def test_returns_project_data_instance(self, mock_project):
        """_build_project_data returns a ProjectData instance."""
        result = ProjectService._build_project_data(mock_project)
        assert isinstance(result, ProjectData)

    def test_maps_all_direct_fields(self, mock_project):
        """All direct fields are correctly mapped from the project model."""
        result = ProjectService._build_project_data(mock_project)
        assert result.id == "proj-001"
        assert result.name == "Original Name"
        assert result.status == "active"
        assert result.mission is None
        assert result.description == "Original Description"
        assert result.execution_mode == "orchestrated"
        assert result.product_id == "product-001"
        assert result.project_type_id == "type-001"
        assert result.series_number == 42
        assert result.subseries == "a"
        assert result.taxonomy_alias == "0042a"

    def test_formats_datetime_fields_as_isoformat(self, mock_project):
        """Datetime fields are converted to ISO format strings."""
        result = ProjectService._build_project_data(mock_project)
        assert result.created_at == "2026-01-01T12:00:00+00:00"
        assert result.updated_at == "2026-01-02T12:00:00+00:00"
        assert result.activated_at == "2026-01-01T13:00:00+00:00"

    def test_handles_none_datetime_fields(self, mock_project):
        """None datetime fields remain None in the result."""
        mock_project.created_at = None
        mock_project.updated_at = None
        mock_project.activated_at = None
        mock_project.completed_at = None
        result = ProjectService._build_project_data(mock_project)
        assert result.created_at is None
        assert result.updated_at is None
        assert result.activated_at is None
        assert result.completed_at is None

    def test_cancellation_reason_defaults_to_none(self, mock_project):
        """cancellation_reason is None by default."""
        result = ProjectService._build_project_data(mock_project)
        assert result.cancellation_reason is None

    def test_cancellation_reason_preserved_when_set(self, mock_project):
        """cancellation_reason is passed through when set on the project."""
        mock_project.cancellation_reason = "Budget exceeded"
        result = ProjectService._build_project_data(mock_project)
        assert result.cancellation_reason == "Budget exceeded"

    def test_deactivation_reason_preserved_when_set(self, mock_project):
        """deactivation_reason is passed through when set on the project."""
        mock_project.deactivation_reason = "User requested"
        result = ProjectService._build_project_data(mock_project)
        assert result.deactivation_reason == "User requested"

    def test_early_termination_defaults_to_false(self, mock_project):
        """early_termination defaults to False."""
        result = ProjectService._build_project_data(mock_project)
        assert result.early_termination is False

    def test_early_termination_preserved_when_true(self, mock_project):
        """early_termination is passed through when True."""
        mock_project.early_termination = True
        result = ProjectService._build_project_data(mock_project)
        assert result.early_termination is True

    def test_project_type_object_passed_through(self, mock_project):
        """project_type relationship object is passed through."""
        result = ProjectService._build_project_data(mock_project)
        assert result.project_type is not None
        assert result.project_type.label == "Feature"
        assert result.project_type.abbreviation == "FT"

    def test_completed_at_formatted_when_present(self, mock_project):
        """completed_at is formatted as ISO string when not None."""
        mock_project.completed_at = datetime(2026, 3, 1, 15, 30, 0, tzinfo=timezone.utc)
        result = ProjectService._build_project_data(mock_project)
        assert result.completed_at == "2026-03-01T15:30:00+00:00"
