# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6039 (project BE-6255): MCP Tasks SHAPE prototype -- mapping core + overlay.

Covers the reusable status mapping (our AgentExecution status -> MCP TaskStatus), the
project-aggregate reduction, the SDK-validated Task-shape builder, and the dormant
flag+capability-gated ``task_view`` overlay on ``get_workflow_status``.

Parallel-safe: no DB, no module-level mutable state. Flag toggled with
``monkeypatch.setenv``; ctx mocked. NO-SHIP-UNTIL-GA.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from api.endpoints.mcp_tools._tasks_prototype import (
    build_task_view,
    derive_aggregate_task_status,
    map_execution_status_to_task_status,
    maybe_attach_task_view,
)


_FLAG = "GILJO_TASKS_PROTOTYPE"
_TS = datetime(2026, 6, 30, 12, 0, 0, tzinfo=UTC)
_VALID_TASK_STATUSES = {"working", "input_required", "completed", "failed", "cancelled"}


def _make_ctx(*, supports: bool = True):
    ctx = MagicMock()
    ctx.session.check_client_capability.return_value = supports
    return ctx


@pytest.mark.parametrize(
    "our_status,expected",
    [
        ("working", "working"),
        ("pending", "working"),
        ("silent", "working"),
        ("blocked", "working"),
        ("awaiting_user", "input_required"),
        # BE-9058: "complete" is what AgentExecution rows actually write; the old
        # mapping only knew the speculative "completed" and reported finished
        # executions as "working".
        ("complete", "completed"),
        ("completed", "completed"),
        ("failed", "failed"),
        ("closed", "cancelled"),
        ("decommissioned", "cancelled"),
        ("terminated", "cancelled"),
        ("cancelled", "cancelled"),
        ("some_unknown_status", "working"),  # default
        (None, "working"),
        ("", "working"),
    ],
)
def test_status_mapping_is_one_to_one_and_valid(our_status, expected):
    mapped = map_execution_status_to_task_status(our_status)
    assert mapped == expected
    assert mapped in _VALID_TASK_STATUSES


@pytest.mark.parametrize(
    "counts,expected_status",
    [
        ({}, "working"),  # no agents
        ({"active": 2, "completed": 1}, "working"),
        ({"pending": 3}, "working"),
        ({"silent": 1, "completed": 2}, "working"),
        ({"blocked": 1, "completed": 1}, "working"),  # blocked is non-terminal
        ({"completed": 3}, "completed"),
        ({"completed": 2, "closed": 1}, "completed"),
        ({"active": 0, "completed": 0, "closed": 2}, "working"),  # all closed, none completed
    ],
)
def test_aggregate_status_reduction(counts, expected_status):
    status, message = derive_aggregate_task_status(counts)
    assert status == expected_status
    assert status in _VALID_TASK_STATUSES
    assert isinstance(message, str) and message


def test_aggregate_tolerates_garbage_counts():
    status, _ = derive_aggregate_task_status({"active": "nope", "completed": None})
    assert status in _VALID_TASK_STATUSES


def test_build_task_view_produces_sdk_valid_shape():
    view = build_task_view("proj-1", "working", status_message="active=1", created_at=_TS, last_updated_at=_TS)
    assert view["prototype"] is True
    assert "spec_note" in view
    task = view["create_task_result"]["task"]
    assert task["taskId"] == "proj-1"
    assert task["status"] == "working"
    assert task["status"] in _VALID_TASK_STATUSES
    assert task["ttl"] > 0
    assert task["createdAt"].startswith("2026-06-30")


def test_overlay_flag_off_returns_unchanged(monkeypatch):
    monkeypatch.delenv(_FLAG, raising=False)
    ctx = _make_ctx()
    result = {"active": 1, "completed": 0}
    out = maybe_attach_task_view(ctx, result, task_id="p1", created_at=_TS, last_updated_at=_TS)
    assert out == result
    assert "task_view" not in out


def test_overlay_flag_on_no_capability_unchanged(monkeypatch):
    monkeypatch.setenv(_FLAG, "1")
    ctx = _make_ctx(supports=False)
    result = {"active": 1}
    out = maybe_attach_task_view(ctx, result, task_id="p1", created_at=_TS, last_updated_at=_TS)
    assert out == result
    assert "task_view" not in out


def test_overlay_flag_on_with_capability_attaches_view(monkeypatch):
    monkeypatch.setenv(_FLAG, "on")
    ctx = _make_ctx(supports=True)
    result = {"active": 2, "completed": 1, "progress_percent": 33}
    out = maybe_attach_task_view(ctx, result, task_id="proj-9", created_at=_TS, last_updated_at=_TS)
    # Original keys preserved (additive).
    assert out["active"] == 2
    assert out["progress_percent"] == 33
    view = out["task_view"]
    assert view["prototype"] is True
    task = view["create_task_result"]["task"]
    assert task["taskId"] == "proj-9"
    assert task["status"] == "working"


def test_overlay_ctx_none_unchanged(monkeypatch):
    monkeypatch.setenv(_FLAG, "1")
    result = {"active": 1}
    out = maybe_attach_task_view(None, result, task_id="p1", created_at=_TS, last_updated_at=_TS)
    assert out == result


def test_overlay_non_dict_result_unchanged(monkeypatch):
    monkeypatch.setenv(_FLAG, "1")
    ctx = _make_ctx(supports=True)
    out = maybe_attach_task_view(ctx, "not-a-dict", task_id="p1", created_at=_TS, last_updated_at=_TS)
    assert out == "not-a-dict"
