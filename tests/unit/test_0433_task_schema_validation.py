# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unit tests for Handover 0433 Phase 4: TaskCreate schema validation.

Tests that the Pydantic schema properly validates product_id requirement
without needing full database setup.
"""

import pytest
from pydantic import ValidationError

from api.schemas.task import TaskCreate


def test_task_create_requires_product_id():
    """
    Test that TaskCreate schema requires product_id.

    Handover 0433 Phase 4 - Success Criteria:
    - product_id is a required field
    - Validation error raised when product_id is missing
    """
    with pytest.raises(ValidationError) as exc_info:
        TaskCreate(
            title="Test Task",
            description="Task without product_id",
            priority="medium",
            # Missing product_id - should raise ValidationError
        )

    # Verify error mentions product_id
    errors = exc_info.value.errors()
    assert any(error["loc"] == ("product_id",) for error in errors), "Error should be for product_id field"
    assert any(error["type"] == "missing" for error in errors), "Error type should be 'missing'"


def test_task_create_with_product_id_succeeds():
    """
    Test that TaskCreate schema accepts valid data with product_id.

    Handover 0433 Phase 4 - Success Criteria:
    - Schema validation succeeds when product_id is provided
    - All fields are properly assigned
    """
    task = TaskCreate(
        title="Test Task",
        description="Task with product_id",
        priority="high",
        product_id="test-product-123",
    )

    assert task.title == "Test Task"
    assert task.description == "Task with product_id"
    assert task.priority == "high"
    assert task.product_id == "test-product-123"
    assert task.status is None  # Optional field
    assert task.project_id is None  # Optional field


def test_task_create_product_id_is_string():
    """
    Test that product_id must be a string.

    Handover 0433 Phase 4 - Success Criteria:
    - product_id field accepts string values
    """
    task = TaskCreate(title="Test", product_id="uuid-string-here")
    assert isinstance(task.product_id, str)


def test_task_create_minimal_valid_data():
    """
    Test minimal valid TaskCreate (only required fields).

    Handover 0433 Phase 4 - Success Criteria:
    - Only title and product_id are required
    - Schema validates with just these fields
    """
    task = TaskCreate(title="Minimal Task", product_id="product-abc")

    assert task.title == "Minimal Task"
    assert task.product_id == "product-abc"
    # All other fields should be None or have defaults
    assert task.description is None
    assert task.status is None
    assert task.priority is None
    assert task.project_id is None


def test_task_create_with_all_fields():
    """
    Test TaskCreate with all optional fields provided.

    Handover 0433 Phase 4 - Success Criteria:
    - Schema accepts all valid fields
    - No regressions in optional field handling
    """
    from datetime import datetime, timezone

    due_date = datetime.now(timezone.utc)

    task = TaskCreate(
        title="Complete Task",
        description="Full task data",
        status="in_progress",
        priority="critical",
        category="bug",
        product_id="product-xyz",
        project_id="project-123",
        parent_task_id="parent-456",
        due_date=due_date,
        estimated_effort=5.5,
        actual_effort=3.2,
    )

    assert task.title == "Complete Task"
    assert task.description == "Full task data"
    assert task.status == "in_progress"
    assert task.priority == "critical"
    assert task.category == "bug"
    assert task.product_id == "product-xyz"
    assert task.project_id == "project-123"
    assert task.parent_task_id == "parent-456"
    assert task.due_date == due_date
    assert task.estimated_effort == 5.5
    assert task.actual_effort == 3.2


def test_task_create_model_fields_metadata():
    """
    Test that product_id field has correct metadata.

    Handover 0433 Phase 4 - Success Criteria:
    - product_id is marked as required in model metadata
    - Field description includes handover reference
    """
    # Access Pydantic model fields
    fields = TaskCreate.model_fields

    # Verify product_id exists and is required
    assert "product_id" in fields, "product_id should be in model fields"
    product_id_field = fields["product_id"]
    assert product_id_field.is_required(), "product_id should be required"

    # Check field description
    description = product_id_field.description
    assert description is not None, "product_id should have description"
    assert "0433" in description, "Description should reference Handover 0433"


# ---------------------------------------------------------------------------
# Handover 0962d: Enum validation tests
# ---------------------------------------------------------------------------


def test_task_create_invalid_status_rejected():
    """TaskCreate must reject unknown status values (0962d)."""
    with pytest.raises(ValidationError) as exc_info:
        TaskCreate(title="T", product_id="p", status="invalid_status")

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


def test_task_create_invalid_priority_rejected():
    """TaskCreate must reject unknown priority values (0962d)."""
    with pytest.raises(ValidationError) as exc_info:
        TaskCreate(title="T", product_id="p", priority="urgent")

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("priority",) for error in errors)


def test_task_create_valid_status_values():
    """TaskCreate accepts all valid status values (0962d)."""
    valid_statuses = ["pending", "in_progress", "completed", "blocked", "cancelled", "converted"]
    for status in valid_statuses:
        task = TaskCreate(title="T", product_id="p", status=status)
        assert task.status == status


def test_task_create_valid_priority_values():
    """TaskCreate accepts all valid priority values (0962d)."""
    valid_priorities = ["low", "medium", "high", "critical"]
    for priority in valid_priorities:
        task = TaskCreate(title="T", product_id="p", priority=priority)
        assert task.priority == priority


def test_status_update_invalid_status_rejected():
    """StatusUpdate must reject unknown status values (0962d)."""
    from api.schemas.task import StatusUpdate

    with pytest.raises(ValidationError) as exc_info:
        StatusUpdate(status="active")

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)


def test_task_update_invalid_status_rejected():
    """TaskUpdate must reject unknown status values (0962d)."""
    from api.schemas.task import TaskUpdate

    with pytest.raises(ValidationError) as exc_info:
        TaskUpdate(status="broken")

    errors = exc_info.value.errors()
    assert any(error["loc"] == ("status",) for error in errors)
