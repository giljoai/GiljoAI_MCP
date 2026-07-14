# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Direct tests for the staging-end machinery extracted in BE-9060 item 2.

``job_completion_staging`` was carved out of ``job_completion_service`` as a
pure move; the service now keeps thin delegators. These tests exercise the
moved C1 conductor completion guard (``guard_conductor_chain_incomplete``)
AT ITS NEW HOME, including the BE-9055 self-heal that this rebase grafted into
the moved function — the correctness-sensitive line the split had to preserve.

The DB-backed end-to-end coverage of the self-heal lives in
tests/services/test_be9055_chain_completion_selfheal.py (through the service
delegator); here we pin the guard's branch logic directly with mocks so a
future edit to the moved function fails fast at this layer.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock, patch

import pytest

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.services.job_completion_staging import guard_conductor_chain_incomplete


def _orchestrator_job() -> Mock:
    return Mock(job_type="orchestrator")


def _conductor_execution() -> Mock:
    return Mock(agent_id="conductor-agent")


async def _run_guard(run: dict) -> None:
    """Invoke the moved guard with a mocked SequenceRunService returning ``run``."""
    with patch("giljo_mcp.services.sequence_run_service.SequenceRunService") as mock_svc:
        mock_svc.return_value.find_active_run_for_conductor = AsyncMock(return_value=run)
        await guard_conductor_chain_incomplete(
            Mock(),  # session
            _orchestrator_job(),
            _conductor_execution(),
            "tk",
            "j1",
            db_manager=Mock(),
            tenant_manager=Mock(),
        )


@pytest.mark.asyncio
async def test_guard_noop_for_non_orchestrator() -> None:
    """Only orchestrator jobs can be conductors — anything else returns immediately."""
    # No SequenceRunService patch: a lookup would explode, proving we never reach it.
    await guard_conductor_chain_incomplete(
        Mock(),
        Mock(job_type="worker"),
        _conductor_execution(),
        "tk",
        "j1",
        db_manager=Mock(),
        tenant_manager=Mock(),
    )


@pytest.mark.asyncio
async def test_guard_passes_when_all_members_terminal() -> None:
    """Every member terminal -> no self-heal needed, conductor may complete."""
    run = {
        "id": "run-1",
        "resolved_order": ["p1", "p2"],
        "project_statuses": {"p1": "completed", "p2": "failed"},
    }
    with patch(
        "giljo_mcp.services.job_completion_staging.heal_chain_member_statuses",
        AsyncMock(),
    ) as mock_heal:
        await _run_guard(run)
        mock_heal.assert_not_awaited()  # fast path: no stale members, zero extra queries


@pytest.mark.asyncio
async def test_guard_self_heals_stale_copy_then_passes() -> None:
    """BE-9055 graft: a stale 'implementing' copy that REALLY finished heals and passes.

    The denormalized copy says p2 is in flight, but the self-heal re-reads the
    real rows and returns an all-terminal copy — the guard must NOT raise.
    """
    run = {
        "id": "run-1",
        "resolved_order": ["p1", "p2"],
        "project_statuses": {"p1": "completed", "p2": "implementing"},
    }
    healed = {"p1": "completed", "p2": "completed"}
    with patch(
        "giljo_mcp.services.job_completion_staging.heal_chain_member_statuses",
        AsyncMock(return_value=healed),
    ) as mock_heal:
        await _run_guard(run)  # must not raise
        mock_heal.assert_awaited_once()


@pytest.mark.asyncio
async def test_guard_blocks_when_genuinely_incomplete() -> None:
    """A member that is really still in flight (heal repairs nothing) still blocks."""
    run = {
        "id": "run-1",
        "resolved_order": ["p1", "p2"],
        "project_statuses": {"p1": "completed", "p2": "implementing"},
    }
    with patch(
        "giljo_mcp.services.job_completion_staging.heal_chain_member_statuses",
        AsyncMock(return_value=run["project_statuses"]),  # nothing to repair
    ):
        with pytest.raises(ValidationError) as exc_info:
            await _run_guard(run)
    assert exc_info.value.error_code == "CONDUCTOR_CHAIN_INCOMPLETE"
    assert "chain run" in str(exc_info.value)  # BE-9055 vocabulary survived the move
