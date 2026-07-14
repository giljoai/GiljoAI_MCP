# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for BE-9000k — unify 3 divergent duplicate business rules.

Item 1: ONE shared CHAIN_TERMINAL_PROJECT_STATUSES set (wide) — a chain member
        ending failed/cancelled must release the conductor's complete_job guard.
Item 2: ONE shared completion-% computation — denominator EXCLUDES decommissioned.
Item 3: TODO step counts — the live rows are the single source of truth; the
        job_metadata cache is a drift-prone fallback (must not override live rows).
"""

import sys
import types
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models.sequence_runs import CHAIN_TERMINAL_PROJECT_STATUSES
from giljo_mcp.services.project_helpers import compute_completion_percent


if "api" not in sys.modules:
    _api_stub = types.ModuleType("api")
    _api_stub.__path__ = ["api"]
    _api_stub.__package__ = "api"
    sys.modules["api"] = _api_stub

from giljo_mcp.services.job_completion_service import JobCompletionService  # noqa: E402
from giljo_mcp.services.job_query_service import JobQueryService  # noqa: E402


# --- Item 1: shared terminal-status set --------------------------------------


class TestChainTerminalStatuses:
    def test_wide_set_includes_failed_and_cancelled(self):
        assert {"completed", "terminated", "cancelled", "failed"} == set(CHAIN_TERMINAL_PROJECT_STATUSES)

    def _make_service(self):
        return JobCompletionService(db_manager=Mock(), tenant_manager=Mock())

    @pytest.mark.asyncio
    async def test_conductor_can_complete_after_member_failed(self):
        """A member ending 'failed' is terminal — the guard must NOT block completion."""
        service = self._make_service()
        job = Mock(job_type="orchestrator")
        execution = Mock(agent_id="conductor-agent")
        run = {
            "id": "run-1",
            "resolved_order": ["p1", "p2"],
            "project_statuses": {"p1": "completed", "p2": "failed"},
        }
        with patch("giljo_mcp.services.sequence_run_service.SequenceRunService") as mock_svc:
            mock_svc.return_value.find_active_run_for_conductor = AsyncMock(return_value=run)
            # Must not raise — all members terminal (completed + failed).
            await service._guard_conductor_chain_incomplete(
                session=Mock(), job=job, execution=execution, tenant_key="tk", job_id="j1"
            )

    @pytest.mark.asyncio
    async def test_conductor_can_complete_after_member_cancelled(self):
        """A member ending 'cancelled' is terminal under the wide set."""
        service = self._make_service()
        job = Mock(job_type="orchestrator")
        execution = Mock(agent_id="conductor-agent")
        run = {
            "id": "run-1",
            "resolved_order": ["p1", "p2"],
            "project_statuses": {"p1": "completed", "p2": "cancelled"},
        }
        with patch("giljo_mcp.services.sequence_run_service.SequenceRunService") as mock_svc:
            mock_svc.return_value.find_active_run_for_conductor = AsyncMock(return_value=run)
            await service._guard_conductor_chain_incomplete(
                session=Mock(), job=job, execution=execution, tenant_key="tk", job_id="j1"
            )

    @pytest.mark.asyncio
    async def test_conductor_blocked_when_member_still_in_flight(self):
        """A non-terminal member ('implementing') still blocks — happy-path guard intact."""
        service = self._make_service()
        job = Mock(job_type="orchestrator")
        execution = Mock(agent_id="conductor-agent")
        run = {
            "id": "run-1",
            "resolved_order": ["p1", "p2"],
            "project_statuses": {"p1": "completed", "p2": "implementing"},
        }
        with patch("giljo_mcp.services.sequence_run_service.SequenceRunService") as mock_svc:
            mock_svc.return_value.find_active_run_for_conductor = AsyncMock(return_value=run)
            # BE-9055: on the "not finished" path the guard now self-heals the copy
            # from the real project rows (a DB read a Mock session cannot serve).
            # Stub it as "nothing to repair" — the heal itself has service-layer
            # coverage in tests/services/test_be9055_chain_completion_selfheal.py.
            with patch(
                "giljo_mcp.services.job_completion_staging.heal_chain_member_statuses",
                AsyncMock(return_value=run["project_statuses"]),
            ):
                with pytest.raises(ValidationError):
                    await service._guard_conductor_chain_incomplete(
                        session=Mock(), job=job, execution=execution, tenant_key="tk", job_id="j1"
                    )


# --- Item 2: shared completion-% (excludes decommissioned) -------------------


class TestCompletionPercent:
    def test_excludes_decommissioned_from_denominator(self):
        # 2 complete of 5 total, 1 decommissioned -> 2 / (5-1) = 50%
        assert compute_completion_percent(completed=2, total=5, decommissioned=1) == 50.0

    def test_project_with_retired_agents_can_reach_100(self):
        # 2 complete, 3 total, 1 decommissioned -> 2 / 2 = 100% (was impossible when
        # the summary view divided by the full total incl. decommissioned).
        assert compute_completion_percent(completed=2, total=3, decommissioned=1) == 100.0

    def test_zero_actionable_returns_zero(self):
        assert compute_completion_percent(completed=0, total=2, decommissioned=2) == 0.0
        assert compute_completion_percent(completed=0, total=0, decommissioned=0) == 0.0

    def test_default_decommissioned_zero(self):
        assert compute_completion_percent(completed=1, total=4) == 25.0


# --- Item 3: TODO counts — live rows are the single source of truth ----------


def _todo_item(status: str):
    item = MagicMock()
    item.status = status
    return item


class TestDeriveStepsSummaryDrift:
    def _service(self):
        return JobQueryService(MagicMock(), MagicMock())

    def test_live_rows_win_over_stale_cache(self):
        """When the cache disagrees with live rows, the live rows are authoritative."""
        service = self._service()
        job = MagicMock()
        # Stale cache claims 5/5 done...
        job.job_metadata = {"todo_steps": {"total_steps": 5, "completed_steps": 5, "skipped_steps": 0}}
        # ...but the live rows say 4 total, 1 completed.
        job.todo_items = [
            _todo_item("completed"),
            _todo_item("pending"),
            _todo_item("in_progress"),
            _todo_item("pending"),
        ]

        result = service._derive_steps_summary(job)

        assert result == {"total": 4, "completed": 1, "skipped": 0}

    def test_cache_used_only_when_no_live_rows(self):
        """Counts-only reporting path (no todo rows) still surfaces the cache."""
        service = self._service()
        job = MagicMock()
        job.job_metadata = {"todo_steps": {"total_steps": 3, "completed_steps": 2, "skipped_steps": 1}}
        job.todo_items = []

        result = service._derive_steps_summary(job)

        assert result == {"total": 3, "completed": 2, "skipped": 1}
