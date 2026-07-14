# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-5107 regression: minimal duration timer on AgentExecution.

Product rule:
- Duration starts the first time status flips to 'working'
- Duration freezes once status reaches 'complete' or 'closed'
- Nothing else stops or pauses it (not blocked, idle, sleeping, awaiting_user,
  silent, or reactivation)

These tests exercise the failing layer (model attribute event + property)
because that is the chokepoint we own. All five status-flip call sites
funnel into the same SQLAlchemy `set` event listener.
"""

from datetime import UTC, datetime, timedelta

import pytest

from giljo_mcp.models.agent_identity import AgentExecution


def _make_execution(status: str = "waiting") -> AgentExecution:
    """Build an in-memory AgentExecution without touching the DB."""
    return AgentExecution(
        agent_id="00000000-0000-0000-0000-000000000001",
        job_id="00000000-0000-0000-0000-00000000000a",
        tenant_key="t",
        agent_display_name="test-agent",
        status=status,
    )


def test_waiting_agent_has_no_duration():
    execution = _make_execution(status="waiting")
    assert execution.working_started_at is None
    assert execution.duration_seconds is None


def test_transition_to_working_anchors_once_and_ticks():
    execution = _make_execution(status="waiting")
    assert execution.working_started_at is None

    execution.status = "working"
    first_anchor = execution.working_started_at
    assert first_anchor is not None

    first_reading = execution.duration_seconds
    assert first_reading is not None
    assert first_reading >= 0.0

    # Re-setting status to 'working' must NOT re-anchor (idempotent).
    execution.status = "working"
    assert execution.working_started_at == first_anchor


def test_reactivation_complete_to_working_does_not_reset_anchor():
    execution = _make_execution(status="waiting")
    execution.status = "working"
    original_anchor = execution.working_started_at
    assert original_anchor is not None

    # Run through complete -> working again (reactivation).
    execution.status = "complete"
    execution.completed_at = datetime.now(UTC)
    execution.status = "working"

    # Anchor stays at the original transition; reactivation does not reset it.
    assert execution.working_started_at == original_anchor


def test_complete_status_freezes_duration_at_completed_at():
    execution = _make_execution(status="waiting")
    anchor = datetime.now(UTC) - timedelta(seconds=42)
    completed_at = anchor + timedelta(seconds=30)

    execution.working_started_at = anchor
    execution.completed_at = completed_at
    execution.status = "complete"

    assert execution.duration_seconds == pytest.approx(30.0, abs=0.5)


def test_closed_status_freezes_duration_at_completed_at():
    execution = _make_execution(status="waiting")
    anchor = datetime.now(UTC) - timedelta(seconds=100)
    completed_at = anchor + timedelta(seconds=75)

    execution.working_started_at = anchor
    execution.completed_at = completed_at
    execution.status = "closed"

    assert execution.duration_seconds == pytest.approx(75.0, abs=0.5)
