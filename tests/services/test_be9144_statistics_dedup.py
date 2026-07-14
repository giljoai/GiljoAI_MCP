# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9144 — statistics_service duplicate-call fix (result-equivalence + call count).

``get_system_stats`` populated both ``total_agents`` and ``total_agents_spawned``
by awaiting the IDENTICAL ``count_total_agents`` query twice. The fix computes it
once and assigns the value to both keys. This suite locks:

- **result-equivalence**: both keys still carry the same count value (unchanged
  observable output), and every other key is untouched;
- **query dedup**: ``count_total_agents`` is now awaited exactly ONCE per call
  (was 2 before the fix — this assertion is the fail-first guard).

Edition Scope: CE. No DB (repos stubbed); parallel-safe.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, Mock

import pytest

from giljo_mcp.services.statistics_service import StatisticsService


pytestmark = pytest.mark.asyncio

_PRODUCT_METHODS = (
    "count_total_projects",
    "count_projects_by_status",
    "count_total_messages",
    "count_messages_by_status",
    "count_total_tasks",
    "count_completed_tasks",
    "count_projects_staged",
)


def _service_with_stubbed_repos(total_agents: int) -> StatisticsService:
    """StatisticsService whose repo calls are stubbed to return ints, no DB."""
    session = MagicMock()
    session.info = {}  # tenant_session_context save/restore target
    svc = StatisticsService(db_manager=Mock(), test_session=session)

    svc._product_repo = Mock()
    for name in _PRODUCT_METHODS:
        setattr(svc._product_repo, name, AsyncMock(return_value=0))

    svc._job_repo = Mock()
    svc._job_repo.count_total_agents = AsyncMock(return_value=total_agents)
    svc._job_repo.count_active_agents = AsyncMock(return_value=0)
    svc._job_repo.count_completed_agents = AsyncMock(return_value=0)
    return svc


async def test_get_system_stats_counts_total_agents_once():
    """The duplicate count_total_agents query is issued exactly once now."""
    svc = _service_with_stubbed_repos(total_agents=7)

    await svc.get_system_stats("tenant-x")

    # Fail-first guard: pre-BE-9144 this was 2 (the exact-duplicate call).
    assert svc._job_repo.count_total_agents.await_count == 1


async def test_get_system_stats_both_agent_keys_share_the_count():
    """Result-equivalence: total_agents and total_agents_spawned carry the same value."""
    svc = _service_with_stubbed_repos(total_agents=7)

    stats = await svc.get_system_stats("tenant-x")

    assert stats["total_agents"] == 7
    assert stats["total_agents_spawned"] == 7
    # Full key set is preserved (no key dropped or added by the refactor).
    assert set(stats) == {
        "total_projects",
        "active_projects",
        "completed_projects",
        "total_agents",
        "active_agents",
        "total_messages",
        "pending_messages",
        "total_tasks",
        "completed_tasks",
        "total_agents_spawned",
        "total_jobs_completed",
        "projects_staged",
        "projects_cancelled",
    }
