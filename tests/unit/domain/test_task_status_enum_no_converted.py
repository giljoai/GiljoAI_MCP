# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression guard: ``converted`` is dead and must stay dead (BE-5095).

The Convert button is a one-shot user action that:
  1. Sets ``Task.converted_to_project_id`` (FK)
  2. Deletes the task row

A ``converted`` task status was never reachable post-conversion (the row
is gone). Keeping it in the enum advertised a non-existent state to
agents via the ``task-statuses`` metadata endpoint and the ``update_task``
MCP tool docstring, which could be abused to set status="converted" on
tasks that were never run through the Convert flow. This test ensures
the enum stays at exactly 5 members.
"""

from __future__ import annotations

from giljo_mcp.domain.task_status import TASK_STATUS_META, TaskStatus


def test_converted_not_in_enum_values() -> None:
    assert "converted" not in [s.value for s in TaskStatus]


def test_converted_not_in_status_meta() -> None:
    assert all(member.value != "converted" for member in TASK_STATUS_META)


def test_enum_has_exactly_five_members() -> None:
    assert {s.name for s in TaskStatus} == {
        "PENDING",
        "IN_PROGRESS",
        "COMPLETED",
        "BLOCKED",
        "CANCELLED",
    }
    assert len(list(TaskStatus)) == 5
