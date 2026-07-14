# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-3010c — the three closeout-readiness sites share ONE gathering method.

Before BE-3010c, "is this project ready to close?" was answered by THREE divergent
implementations (``tools/project_closeout._check_agent_readiness``,
``tools/write_memory_entry._check_closeout_readiness`` and
``ProjectCloseoutService.can_close``) — a readiness bug fixed in one silently
persisted in the other two. They now all derive from the single
``ProjectCloseoutService.evaluate_closeout_readiness`` gathering method; a change
to the readiness RULE is made once and every site observes it. Rendering (the
blocker wire shape) legitimately differs per site and is preserved.

This suite locks: (1) all three sites call the one method, and (2) the two rich
sites SHAPE the same report into their respective (and different) wire formats.

Edition Scope: Both. No DB (the gathering method is patched); parallel-safe.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from giljo_mcp.services.project_closeout_service import (
    AgentReadinessFinding,
    CloseoutReadinessReport,
    ProjectCloseoutService,
)


def _report(findings=None, *, orchestrator_incomplete=None, status_counts=None) -> CloseoutReadinessReport:
    return CloseoutReadinessReport(
        findings=findings or [],
        agents_checked=len(findings or []),
        status_counts=status_counts or {"total": 0, "completed": 0, "blocked": 0, "silent": 0, "active": 0},
        orchestrator_incomplete=orchestrator_incomplete or [],
        orchestrator_pending=0,
        orchestrator_in_progress=0,
    )


def _still_working_finding() -> AgentReadinessFinding:
    return AgentReadinessFinding(
        job_id="job-1",
        agent_id="agent-1",
        agent_name="impl-1",
        status="working",
        messages_waiting=2,
        incomplete_todos=["finish the thing", "write tests"],
        incomplete_pending=1,
        incomplete_in_progress=1,
        awaiting_user=False,
        approval_id=None,
    )


@pytest.mark.asyncio
async def test_check_agent_readiness_routes_through_evaluate():
    """tools/project_closeout._check_agent_readiness derives from the one method."""
    from giljo_mcp.tools.project_closeout import _check_agent_readiness

    with patch.object(
        ProjectCloseoutService, "evaluate_closeout_readiness", new=AsyncMock(return_value=_report())
    ) as spy:
        is_ready, blockers = await _check_agent_readiness(Mock(), "proj-1", "tenant-1")

    spy.assert_awaited_once()
    assert is_ready is True
    assert blockers == []


@pytest.mark.asyncio
async def test_check_closeout_readiness_routes_through_evaluate():
    """tools/write_memory_entry._check_closeout_readiness derives from the one method."""
    from giljo_mcp.tools.write_memory_entry import _check_closeout_readiness

    with patch.object(
        ProjectCloseoutService, "evaluate_closeout_readiness", new=AsyncMock(return_value=_report())
    ) as spy:
        is_ready, result = await _check_closeout_readiness(Mock(), "proj-1", "tenant-1")

    spy.assert_awaited_once()
    assert is_ready is True
    assert result["verified"]["all_complete"] is True


@pytest.mark.asyncio
async def test_can_close_routes_through_evaluate():
    """ProjectCloseoutService.can_close derives its coarse counts from the one method."""
    service = ProjectCloseoutService(None, Mock())
    canned = _report(status_counts={"total": 2, "completed": 2, "blocked": 0, "silent": 0, "active": 0})

    with (
        patch.object(service, "_get_project_for_tenant", new=AsyncMock(return_value=Mock())),
        patch.object(service, "evaluate_closeout_readiness", new=AsyncMock(return_value=canned)) as spy,
    ):
        result = await service.can_close_project("proj-1", "tenant-1", db_session=Mock())

    spy.assert_awaited_once()
    assert result.can_close is True
    assert result.all_agents_finished is True


@pytest.mark.asyncio
async def test_rich_sites_shape_one_report_into_their_own_wire_formats():
    """One report -> A's merged-per-agent blocker; B's per-issue envelope (both blocked)."""
    from giljo_mcp.tools.project_closeout import _check_agent_readiness
    from giljo_mcp.tools.write_memory_entry import _check_closeout_readiness

    report = _report(findings=[_still_working_finding()])

    with patch.object(ProjectCloseoutService, "evaluate_closeout_readiness", new=AsyncMock(return_value=report)):
        a_ready, a_blockers = await _check_agent_readiness(Mock(), "proj-1", "tenant-1")
        b_ready, b_result = await _check_closeout_readiness(Mock(), "proj-1", "tenant-1")

    # A: ONE merged still_working blocker carrying message + todo detail, + trailing _summary.
    assert a_ready is False
    a_agent_blockers = [b for b in a_blockers if "_summary" not in b]
    assert len(a_agent_blockers) == 1
    assert a_agent_blockers[0]["issue_type"] == "still_working"
    assert a_agent_blockers[0]["messages_waiting"] == 2
    assert a_agent_blockers[0]["incomplete_todo_count"] == 2

    # B: a still_working blocker only (B reports message/todo issues for COMPLETE agents),
    #    wrapped in the envelope with summary + message + next_steps.
    assert b_ready is False
    assert b_result["summary"]["still_working"] == 1
    assert {blk["issue_type"] for blk in b_result["blockers"]} == {"still_working"}
    assert "next_steps" in b_result
