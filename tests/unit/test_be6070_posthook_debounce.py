# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6070 (F9): _call_tool post-hook debounce — reduction proof.

The hottest path is every authenticated MCP tool call. Today each call WITH a
job_id opens TWO sessions and runs two post-hooks (silent-clear probe +
heartbeat). BE-6070 gates both behind ONE in-process monotonic debounce per
job_id and, when they DO run, shares ONE session for both hooks.

Failing layer: the gate lives in ``api/endpoints/mcp_tools/_base._call_tool``,
so these tests drive that function directly (with the DB + hooks stubbed) and
assert the WRITE/round-trip reduction — the synthetic "N rapid calls -> bounded
DB visits" scenario a live trace cannot produce.
"""

from __future__ import annotations

import contextlib

import pytest

from api.endpoints.mcp_tools import _base
from giljo_mcp.services import debounce


pytestmark = pytest.mark.asyncio


class _FakeProgressService:
    """Stand-in for ToolAccessor._progress_service (BE-3010b dispatch target)."""

    async def report_progress(self, *, job_id=None, tenant_key=None, **kwargs):
        return {"ok": True}


class _FakeAccessor:
    """Minimal ToolAccessor stand-in. report_progress dispatches (post-BE-3010b)
    straight to the bound ``_progress_service.report_progress`` via TOOL_DISPATCH."""

    def __init__(self) -> None:
        self._progress_service = _FakeProgressService()


class _SessionCounter:
    """db_manager stand-in counting how many sessions _call_tool opens."""

    def __init__(self) -> None:
        self.opens = 0

    def get_session_async(self, tenant_key=None):
        self.opens += 1

        @contextlib.asynccontextmanager
        async def _cm():
            yield object()  # a sentinel "session"; hooks are stubbed so it's unused

        return _cm()


@pytest.fixture
def posthook_harness(monkeypatch):
    """Wire _call_tool with stubbed tenant resolution, accessor, DB, and hooks.

    Returns ``(call, counters)`` where ``call()`` invokes the post-hook path for
    a job_id and ``counters`` exposes session-open + hook-invocation counts.
    """
    from api import app_state
    from giljo_mcp.services import heartbeat, silence_detector

    debounce.reset("mcp_posthooks")

    state = app_state.state
    prior_accessor = state.tool_accessor
    prior_db = state.db_manager
    prior_ws = state.websocket_manager

    session_counter = _SessionCounter()
    state.tool_accessor = _FakeAccessor()
    state.db_manager = session_counter
    state.websocket_manager = None

    monkeypatch.setattr(_base, "_resolve_tenant", lambda ctx: "tk-test")
    monkeypatch.setattr(_base, "_set_tenant_context", lambda tenant_key: None)

    counters = {"silent": 0, "heartbeat": 0, "sessions": session_counter}

    async def _fake_auto_clear(db, job_id, ws_manager, tenant_key):
        counters["silent"] += 1

    async def _fake_heartbeat(db, job_id, tenant_key):
        counters["heartbeat"] += 1

    monkeypatch.setattr(silence_detector, "auto_clear_silent", _fake_auto_clear)
    monkeypatch.setattr(heartbeat, "touch_heartbeat", _fake_heartbeat)

    async def call(job_id="job-1"):
        return await _base._call_tool(None, "report_progress", {"job_id": job_id})

    try:
        yield call, counters
    finally:
        state.tool_accessor = prior_accessor
        state.db_manager = prior_db
        state.websocket_manager = prior_ws
        debounce.reset("mcp_posthooks")


async def test_first_call_runs_both_hooks_in_one_session(posthook_harness):
    """First call for a job_id: ONE shared session, both hooks fire."""
    call, counters = posthook_harness

    result = await call("job-A")

    assert result["ok"] is True
    assert counters["sessions"].opens == 1, "expected ONE shared session, not two"
    assert counters["silent"] == 1
    assert counters["heartbeat"] == 1


async def test_rapid_second_call_skips_both_hooks(posthook_harness):
    """A 2nd call within the debounce window touches the DB ZERO times."""
    call, counters = posthook_harness

    await call("job-A")
    await call("job-A")  # within window

    assert counters["sessions"].opens == 1, "2nd rapid call must NOT open a session"
    assert counters["silent"] == 1, "2nd rapid call must NOT re-run silent-clear"
    assert counters["heartbeat"] == 1, "2nd rapid call must NOT re-run heartbeat"


async def test_n_rapid_calls_bounded_to_one_db_visit(posthook_harness):
    """N rapid calls on one job_id -> exactly ONE post-hook DB visit."""
    call, counters = posthook_harness

    for _ in range(25):
        await call("job-A")

    assert counters["sessions"].opens == 1
    assert counters["silent"] == 1
    assert counters["heartbeat"] == 1


async def test_window_elapsed_runs_hooks_again(posthook_harness):
    """After the window clears, the next call writes again (never permanently muted)."""
    call, counters = posthook_harness

    await call("job-A")
    debounce.reset("mcp_posthooks")  # simulate the window elapsing
    await call("job-A")

    assert counters["sessions"].opens == 2
    assert counters["silent"] == 2
    assert counters["heartbeat"] == 2


async def test_distinct_job_ids_each_get_first_write(posthook_harness):
    """The gate is per-job_id: a different job_id is never debounced by another."""
    call, counters = posthook_harness

    await call("job-A")
    await call("job-B")

    assert counters["sessions"].opens == 2
    assert counters["silent"] == 2
    assert counters["heartbeat"] == 2


async def test_no_job_id_skips_posthooks_entirely(posthook_harness):
    """A call without a job_id runs no post-hooks (unchanged behavior)."""
    _call, counters = posthook_harness

    await _base._call_tool(None, "report_progress", {})

    assert counters["sessions"].opens == 0
    assert counters["silent"] == 0
    assert counters["heartbeat"] == 0
