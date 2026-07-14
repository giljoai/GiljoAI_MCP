# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Unit tests for ``giljo_mcp.domain.task_status`` (FE-5041 Phase 1).

Mirrors the BE-5039 ``test_project_status_enum`` shape verbatim. Asserts
the canonical five members, the metadata structure, derived sets, and
``str``-mixin equality used by legacy callers.
"""

from __future__ import annotations

from giljo_mcp.domain.task_status import (
    TASK_LIFECYCLE_FINISHED_STATUSES,
    TASK_STATUS_META,
    VALID_TASK_STATUSES,
    TaskStatus,
    TaskStatusMeta,
)


# ----------------------------------------------------------------------
# Enum membership
# ----------------------------------------------------------------------


def test_enum_has_exactly_five_members() -> None:
    """Canonical task statuses match the legacy free-form list verbatim."""

    assert {s.value for s in TaskStatus} == {
        "pending",
        "in_progress",
        "completed",
        "blocked",
        "cancelled",
    }


def test_enum_declaration_order_is_canonical() -> None:
    """Order matches the comment in ``models/tasks.py`` and the badge component."""

    assert [s.value for s in TaskStatus] == [
        "pending",
        "in_progress",
        "completed",
        "blocked",
        "cancelled",
    ]


def test_enum_is_str_subclass_for_legacy_equality() -> None:
    """``TaskStatus.X == "x"`` must be True for legacy callers."""

    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.IN_PROGRESS == "in_progress"
    assert TaskStatus.COMPLETED.value == "completed"


def test_enum_supports_membership_via_string() -> None:
    """``"completed" in TASK_LIFECYCLE_FINISHED_STATUSES`` works thanks to str mixin."""

    assert "completed" in TASK_LIFECYCLE_FINISHED_STATUSES
    assert "cancelled" in TASK_LIFECYCLE_FINISHED_STATUSES
    assert "converted" not in TASK_LIFECYCLE_FINISHED_STATUSES
    assert "pending" not in TASK_LIFECYCLE_FINISHED_STATUSES
    assert "in_progress" not in TASK_LIFECYCLE_FINISHED_STATUSES


# ----------------------------------------------------------------------
# Metadata structure
# ----------------------------------------------------------------------


def test_every_member_has_metadata() -> None:
    assert set(TASK_STATUS_META.keys()) == set(TaskStatus)


def test_metadata_dataclass_is_frozen() -> None:
    meta = TASK_STATUS_META[TaskStatus.PENDING]
    assert isinstance(meta, TaskStatusMeta)
    try:
        meta.label = "Other"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("TaskStatusMeta should be frozen")


def test_color_tokens_are_scss_variable_names_not_hex() -> None:
    """Color tokens MUST be SCSS variable names -- no hex literals."""

    for member, meta in TASK_STATUS_META.items():
        assert not meta.color_token.startswith("#"), (
            f"{member} has a hex literal color: {meta.color_token!r}; "
            "use an SCSS token name like 'color-status-complete' instead."
        )
        assert meta.color_token.startswith("color-"), (
            f"{member} color_token {meta.color_token!r} should start with 'color-'."
        )


def test_label_is_non_empty_human_readable() -> None:
    for member, meta in TASK_STATUS_META.items():
        assert meta.label, f"{member} has empty label"
        assert meta.label[0].isupper(), f"{member} label {meta.label!r} not capitalized"


# ----------------------------------------------------------------------
# Derived sets
# ----------------------------------------------------------------------


def test_lifecycle_finished_set_matches_service_semantics() -> None:
    """The pair of statuses that block further progress in TaskService.

    ``completed`` + ``cancelled`` set ``completed_at`` (see
    ``task_service._change_status_impl``).
    """

    assert {s.value for s in TASK_LIFECYCLE_FINISHED_STATUSES} == {
        "completed",
        "cancelled",
    }


def test_valid_task_statuses_is_full_set() -> None:
    assert set(VALID_TASK_STATUSES) == set(TaskStatus)


# ----------------------------------------------------------------------
# Convenience properties on the enum members
# ----------------------------------------------------------------------


def test_member_meta_property_returns_registered_metadata() -> None:
    assert TaskStatus.COMPLETED.meta is TASK_STATUS_META[TaskStatus.COMPLETED]


def test_is_lifecycle_finished_property() -> None:
    assert TaskStatus.COMPLETED.is_lifecycle_finished is True
    assert TaskStatus.CANCELLED.is_lifecycle_finished is True
    assert TaskStatus.PENDING.is_lifecycle_finished is False
    assert TaskStatus.IN_PROGRESS.is_lifecycle_finished is False
    assert TaskStatus.BLOCKED.is_lifecycle_finished is False
