# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for shared/generic service-layer Pydantic response models.

Split from test_service_responses.py — covers DeleteResult, OperationResult,
TransferResult, PaginatedResult, and cross-cutting serialization tests.

Created: Handover 0731
"""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from src.giljo_mcp.schemas.service_responses import (
    AuthResult,
    DeleteResult,
    OperationResult,
    PaginatedResult,
    ProductStatistics,
    SpawnResult,
    TaskSummary,
    TransferResult,
)

# ---------------------------------------------------------------------------
# Shared Result Types
# ---------------------------------------------------------------------------


class TestDeleteResult:
    """Tests for DeleteResult model."""

    def test_creation_defaults(self):
        """DeleteResult should default deleted=True and deleted_at=None."""
        result = DeleteResult()
        assert result.deleted is True
        assert result.deleted_at is None

    def test_creation_with_timestamp(self):
        """DeleteResult accepts an explicit deleted_at timestamp."""
        ts = datetime(2026, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        result = DeleteResult(deleted=True, deleted_at=ts)
        assert result.deleted is True
        assert result.deleted_at == ts

    def test_model_dump(self):
        """model_dump should produce a plain dict."""
        result = DeleteResult()
        dumped = result.model_dump()
        assert isinstance(dumped, dict)
        assert dumped["deleted"] is True
        assert dumped["deleted_at"] is None

    def test_from_attributes_config(self):
        """Model should have from_attributes=True in config."""
        assert DeleteResult.model_config.get("from_attributes") is True


class TestOperationResult:
    """Tests for OperationResult model."""

    def test_creation_with_message(self):
        """OperationResult requires a message string."""
        result = OperationResult(message="Product activated successfully")
        assert result.message == "Product activated successfully"

    def test_missing_message_raises(self):
        """OperationResult without message should raise ValidationError."""
        with pytest.raises(ValidationError):
            OperationResult()

    def test_model_dump(self):
        """model_dump should serialize correctly."""
        result = OperationResult(message="Done")
        dumped = result.model_dump()
        assert dumped == {"message": "Done"}

    def test_from_attributes_config(self):
        assert OperationResult.model_config.get("from_attributes") is True


class TestTransferResult:
    """Tests for TransferResult model."""

    def test_creation_with_required_fields(self):
        """TransferResult requires from_user_id and to_user_id."""
        result = TransferResult(from_user_id="user-1", to_user_id="user-2")
        assert result.transferred is True
        assert result.from_user_id == "user-1"
        assert result.to_user_id == "user-2"

    def test_missing_from_user_id_raises(self):
        with pytest.raises(ValidationError):
            TransferResult(to_user_id="user-2")

    def test_missing_to_user_id_raises(self):
        with pytest.raises(ValidationError):
            TransferResult(from_user_id="user-1")

    def test_model_dump(self):
        result = TransferResult(from_user_id="a", to_user_id="b")
        dumped = result.model_dump()
        assert dumped["transferred"] is True
        assert dumped["from_user_id"] == "a"
        assert dumped["to_user_id"] == "b"

    def test_from_attributes_config(self):
        assert TransferResult.model_config.get("from_attributes") is True


class TestPaginatedResult:
    """Tests for PaginatedResult generic model."""

    def test_creation_with_string_items(self):
        """PaginatedResult[str] should hold a list of strings."""
        result = PaginatedResult[str](items=["a", "b", "c"], total=3)
        assert result.items == ["a", "b", "c"]
        assert result.total == 3
        assert result.page == 1
        assert result.page_size == 50

    def test_creation_with_int_items(self):
        """PaginatedResult[int] should hold a list of ints."""
        result = PaginatedResult[int](items=[1, 2], total=100, page=2, page_size=25)
        assert result.items == [1, 2]
        assert result.total == 100
        assert result.page == 2
        assert result.page_size == 25

    def test_creation_with_dict_items(self):
        """PaginatedResult[dict] should hold a list of dicts."""
        items = [{"id": "1", "name": "Product A"}, {"id": "2", "name": "Product B"}]
        result = PaginatedResult[dict](items=items, total=2)
        assert len(result.items) == 2
        assert result.items[0]["name"] == "Product A"

    def test_empty_items(self):
        """PaginatedResult with empty items list and total=0."""
        result = PaginatedResult[str](items=[], total=0)
        assert result.items == []
        assert result.total == 0

    def test_missing_total_raises(self):
        """total is required."""
        with pytest.raises(ValidationError):
            PaginatedResult[str](items=["a"])

    def test_missing_items_raises(self):
        """items is required."""
        with pytest.raises(ValidationError):
            PaginatedResult[str](total=5)

    def test_model_dump(self):
        result = PaginatedResult[str](items=["x"], total=1, page=3, page_size=10)
        dumped = result.model_dump()
        assert dumped["items"] == ["x"]
        assert dumped["total"] == 1
        assert dumped["page"] == 3
        assert dumped["page_size"] == 10

    def test_from_attributes_config(self):
        assert PaginatedResult.model_config.get("from_attributes") is True


# ---------------------------------------------------------------------------
# Cross-Cutting Concerns
# ---------------------------------------------------------------------------


class TestModelJsonSerialization:
    """Test JSON serialization round-trip for models with complex types."""

    def test_delete_result_with_datetime_json(self):
        """Datetime fields should serialize to JSON correctly."""
        ts = datetime(2026, 2, 1, 10, 30, 0, tzinfo=timezone.utc)
        result = DeleteResult(deleted_at=ts)
        json_str = result.model_dump_json()
        assert "2026" in json_str

    def test_paginated_result_json(self):
        """PaginatedResult should serialize to JSON correctly."""
        result = PaginatedResult[str](items=["a", "b"], total=2)
        json_str = result.model_dump_json()
        assert '"items"' in json_str
        assert '"total"' in json_str

    def test_task_summary_nested_dicts_json(self):
        """Nested dict fields should serialize to JSON correctly."""
        summary = TaskSummary(
            total=10,
            by_status={"pending": 5, "completed": 5},
        )
        json_str = summary.model_dump_json()
        assert '"pending"' in json_str


class TestModelFromDict:
    """Test model construction from dictionaries (common API pattern)."""

    def test_spawn_result_from_dict(self):
        data = {"job_id": "j1", "agent_id": "a1", "agent_prompt": "prompt"}
        result = SpawnResult(**data)
        assert result.job_id == "j1"

    def test_auth_result_from_dict(self):
        data = {
            "user_id": "u1",
            "username": "admin",
            "token": "jwt",
            "tenant_key": "tk",
            "role": "admin",
        }
        result = AuthResult(**data)
        assert result.role == "admin"

    def test_product_statistics_from_partial_dict(self):
        """Models with required+default fields should accept partial dicts with required fields."""
        data = {"product_id": "p1", "name": "Test", "is_active": True, "project_count": 5}
        stats = ProductStatistics(**data)
        assert stats.project_count == 5
        assert stats.task_count == 0
