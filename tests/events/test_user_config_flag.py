"""
Tests for User Config Flag in Event Schemas

Tests that event schemas correctly include and handle the user_config_applied
flag and field_priorities metadata for client-side display of optimization badges.

Handover 0086B Phase 5.1: Backend Integration Testing
Created: 2025-11-02
Coverage Target: 100%
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from pydantic import ValidationError

from api.events.schemas import (
    EventFactory,
    ProjectMissionUpdatedData,
    ProjectMissionUpdatedEvent,
)


# ============================================================================
# Test: EventFactory with user_config_applied Flag
# ============================================================================


def test_event_factory_mission_updated_with_user_config():
    """
    Test EventFactory.project_mission_updated includes user_config_applied flag.

    Validates that when user configuration is applied, the event schema
    correctly includes the flag for frontend "Optimized for you" badge display.
    """
    # Arrange
    project_id = str(uuid4())
    tenant_key = "tenant_abc"

    # Act
    event = EventFactory.project_mission_updated(
        project_id=project_id,
        tenant_key=tenant_key,
        mission="Implement authentication system",
        token_estimate=5000,
        user_config_applied=True,
        field_priorities={"security": 5, "performance": 4},
    )

    # Assert
    assert event["type"] == "project:mission_updated"
    assert "timestamp" in event
    assert event["schema_version"] == "1.0"

    # Verify data payload
    data = event["data"]
    assert data["project_id"] == project_id
    assert data["tenant_key"] == tenant_key
    assert data["mission"] == "Implement authentication system"
    assert data["token_estimate"] == 5000

    # CRITICAL: Verify user_config_applied flag
    assert data["user_config_applied"] is True

    # Verify field_priorities included
    assert data["field_priorities"] == {"security": 5, "performance": 4}


def test_event_factory_mission_updated_without_user_config():
    """
    Test EventFactory.project_mission_updated with user_config_applied=False.

    Validates that when user configuration is NOT applied (default generation),
    the flag is correctly set to False and field_priorities is None.
    """
    # Arrange
    project_id = str(uuid4())
    tenant_key = "tenant_abc"

    # Act
    event = EventFactory.project_mission_updated(
        project_id=project_id,
        tenant_key=tenant_key,
        mission="Generic mission",
        token_estimate=3000,
        user_config_applied=False,  # Default, no user config
    )

    # Assert
    data = event["data"]

    # Verify user_config_applied is False
    assert data["user_config_applied"] is False

    # Verify field_priorities is None (no config applied)
    assert data["field_priorities"] is None


def test_event_factory_mission_updated_default_user_config_false():
    """
    Test EventFactory.project_mission_updated defaults user_config_applied to False.

    Validates backwards compatibility: if user_config_applied is not specified,
    it defaults to False (safe default for existing code).
    """
    # Arrange
    project_id = str(uuid4())
    tenant_key = "tenant_abc"

    # Act - Don't specify user_config_applied
    event = EventFactory.project_mission_updated(
        project_id=project_id,
        tenant_key=tenant_key,
        mission="Default mission",
        token_estimate=2000,
        # user_config_applied not specified
    )

    # Assert
    data = event["data"]

    # CRITICAL: Verify default is False (backwards compatibility)
    assert data["user_config_applied"] is False
    assert data["field_priorities"] is None


# ============================================================================
# Test: Field Priorities Included When Config Applied
# ============================================================================


def test_event_schema_includes_field_priorities_with_config():
    """
    Test ProjectMissionUpdatedData includes field_priorities when provided.

    Validates that field priorities are correctly included in the event
    schema for frontend display and analytics.
    """
    # Arrange
    priorities = {"product_vision": 10, "project_description": 8, "codebase_summary": 6, "architecture": 4}

    # Act
    event = ProjectMissionUpdatedEvent(
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        data=ProjectMissionUpdatedData(
            project_id=str(uuid4()),
            tenant_key="tenant_abc",
            mission="Mission with priorities",
            token_estimate=4500,
            user_config_applied=True,
            field_priorities=priorities,
        ),
    )

    # Assert
    assert event.data.user_config_applied is True
    assert event.data.field_priorities == priorities

    # Verify serialization (JSON output)
    event_dict = event.model_dump(mode="json")
    assert event_dict["data"]["field_priorities"] == priorities


def test_event_schema_validates_field_priorities_dict():
    """
    Test ProjectMissionUpdatedData validates field_priorities as dict.

    Validates Pydantic type validation for field_priorities parameter.
    """
    # Arrange & Act
    event = ProjectMissionUpdatedEvent(
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        data=ProjectMissionUpdatedData(
            project_id=str(uuid4()),
            tenant_key="tenant_abc",
            mission="Test mission",
            token_estimate=1000,
            user_config_applied=True,
            field_priorities={"field1": 5, "field2": 3},  # Valid dict
        ),
    )

    # Assert
    assert isinstance(event.data.field_priorities, dict)


# ============================================================================
# Test: Backwards Compatibility
# ============================================================================


def test_event_schema_backwards_compatible_without_flag():
    """
    Test ProjectMissionUpdatedData works without user_config_applied.

    Validates backwards compatibility: existing code that doesn't provide
    user_config_applied still works (defaults to False).
    """
    # Arrange & Act
    event = ProjectMissionUpdatedEvent(
        timestamp=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        data=ProjectMissionUpdatedData(
            project_id=str(uuid4()),
            tenant_key="tenant_abc",
            mission="Legacy mission",
            token_estimate=2000,
            # user_config_applied not provided
        ),
    )

    # Assert
    assert event.data.user_config_applied is False  # Default value
    assert event.data.field_priorities is None


def test_event_factory_backwards_compatible():
    """
    Test EventFactory maintains backwards compatibility for existing callers.

    Validates that code using EventFactory without user_config_applied
    parameter still works correctly.
    """
    # Arrange & Act - Old-style call (minimal parameters)
    event = EventFactory.project_mission_updated(
        project_id=str(uuid4()), tenant_key="tenant_abc", mission="Legacy style mission", token_estimate=1500
    )

    # Assert
    data = event["data"]
    assert data["user_config_applied"] is False
    assert data["field_priorities"] is None
    assert data["generated_by"] == "orchestrator"  # Default


# ============================================================================
# Test: Generated By Field
# ============================================================================


def test_event_factory_generated_by_user():
    """
    Test EventFactory correctly sets generated_by="user" for user-initiated regeneration.

    Validates that user-initiated regenerations are properly tagged for
    analytics and logging.
    """
    # Arrange & Act
    event = EventFactory.project_mission_updated(
        project_id=str(uuid4()),
        tenant_key="tenant_abc",
        mission="User regenerated mission",
        token_estimate=4000,
        generated_by="user",  # User-initiated
        user_config_applied=True,
        field_priorities={"security": 5},
    )

    # Assert
    data = event["data"]
    assert data["generated_by"] == "user"
    assert data["user_config_applied"] is True


def test_event_factory_generated_by_orchestrator():
    """
    Test EventFactory correctly sets generated_by="orchestrator" by default.

    Validates that automatic mission generation is properly tagged.
    """
    # Arrange & Act
    event = EventFactory.project_mission_updated(
        project_id=str(uuid4()),
        tenant_key="tenant_abc",
        mission="Auto-generated mission",
        token_estimate=3000,
        generated_by="orchestrator",  # Default
    )

    # Assert
    data = event["data"]
    assert data["generated_by"] == "orchestrator"


# ============================================================================
# Test: Pydantic Validation
# ============================================================================


def test_event_schema_validates_tenant_key_not_empty():
    """
    Test ProjectMissionUpdatedData validates tenant_key is not empty.

    Validates critical security constraint: tenant_key must be provided.
    """
    # Arrange & Act & Assert
    with pytest.raises(ValidationError) as exc_info:
        ProjectMissionUpdatedData(
            project_id=str(uuid4()),
            tenant_key="",  # Invalid (empty)
            mission="Test mission",
            token_estimate=1000,
        )

    # Verify error message
    assert "at least 1 character" in str(exc_info.value).lower() or "min_length" in str(exc_info.value).lower()


# ============================================================================
# Test: JSON Serialization for WebSocket
# ============================================================================


def test_event_serialization_includes_all_fields():
    """
    Test event serialization includes all fields for WebSocket transmission.

    Validates that model_dump() produces JSON-ready output with all
    necessary fields for frontend consumption.
    """
    # Arrange
    priorities = {"security": 5, "performance": 4, "ux": 3}

    event = EventFactory.project_mission_updated(
        project_id=str(uuid4()),
        tenant_key="tenant_abc",
        mission="Complete mission",
        token_estimate=6000,
        generated_by="user",
        user_config_applied=True,
        field_priorities=priorities,
    )

    # Act - Serialize for WebSocket
    serialized = event  # EventFactory already returns dict

    # Assert
    assert isinstance(serialized, dict)
    assert "type" in serialized
    assert "timestamp" in serialized
    assert "schema_version" in serialized
    assert "data" in serialized

    data = serialized["data"]
    assert "project_id" in data
    assert "tenant_key" in data
    assert "mission" in data
    assert "token_estimate" in data
    assert "generated_by" in data
    assert "user_config_applied" in data
    assert "field_priorities" in data
    assert data["field_priorities"] == priorities
