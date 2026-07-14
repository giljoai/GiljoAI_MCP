# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9053 items 1+2: degraded-services visibility + maintenance-loop resilience.

Item 2 failing layer: a CE maintenance loop hit by ONE unexpected exception
(anything outside the old narrow catch tuple) died permanently and silently —
the API-metrics flusher was proven killable by a single transient DB error.
The loops now catch-log-continue (SaaS reaper pattern), and every loop task
carries a done-callback that logs at ERROR if the task ever finishes for any
reason other than cancellation.

Item 1 failing layer: the /health endpoint never read state.degraded_services.

Parallel-safe: no DB, no module-level mutable state; monkeypatch everywhere.
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import MagicMock

import pytest

from api.startup import metrics_flushers
from api.startup.background_tasks import cleanup_expired_download_tokens
from api.startup.metrics_flushers import log_task_death, sync_api_metrics_to_db


def _fast_sleep(monkeypatch, max_iterations: int):
    """Replace asyncio.sleep in the loop modules with an instant, bounded fake.

    After ``max_iterations`` awaited sleeps it cancels the loop naturally, so a
    broken continue-path can never hang the test.
    """
    real_sleep = asyncio.sleep
    calls = {"n": 0}

    async def fake_sleep(_seconds):
        calls["n"] += 1
        if calls["n"] > max_iterations:
            raise asyncio.CancelledError
        await real_sleep(0)

    monkeypatch.setattr(metrics_flushers.asyncio, "sleep", fake_sleep)
    return calls


@pytest.mark.asyncio
async def test_api_metrics_flusher_survives_unexpected_error(monkeypatch, caplog):
    """One unexpected (non-SQLAlchemy) error must be logged and the loop must
    keep iterating — this exact loop was proven killable by one DB hiccup."""
    state = MagicMock()
    state.api_call_count = {"tk_test": 3}
    state.mcp_call_count = {}

    def _boom():
        raise RuntimeError("transient DB connect failure")

    state.db_manager.get_session_async = MagicMock(side_effect=_boom)

    calls = _fast_sleep(monkeypatch, max_iterations=3)

    with caplog.at_level(logging.ERROR, logger="api.startup.metrics_flushers"):
        with pytest.raises(asyncio.CancelledError):
            await sync_api_metrics_to_db(state)

    # The loop iterated PAST the first failure (sleep awaited again after it).
    assert calls["n"] > 1
    assert any("Error during API metrics sync" in rec.message for rec in caplog.records)
    # Counters restored on failure so the window is retried next cycle.
    assert state.api_call_count == {"tk_test": 3}


@pytest.mark.asyncio
async def test_download_token_cleanup_survives_unexpected_error(monkeypatch, caplog):
    """Same guarantee for a representative gated maintenance loop."""
    from api.startup import background_tasks

    state = MagicMock()

    def _boom():
        raise KeyError("outside the old narrow catch tuple")

    state.db_manager.get_session_async = MagicMock(side_effect=_boom)

    real_sleep = asyncio.sleep
    calls = {"n": 0}

    async def fake_sleep(_seconds):
        calls["n"] += 1
        if calls["n"] > 3:
            raise asyncio.CancelledError
        await real_sleep(0)

    monkeypatch.setattr(background_tasks.asyncio, "sleep", fake_sleep)

    with caplog.at_level(logging.ERROR, logger="api.startup.background_tasks"):
        with pytest.raises(asyncio.CancelledError):
            await cleanup_expired_download_tokens(state)

    assert calls["n"] > 1
    assert any("Error during download token cleanup" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_log_task_death_logs_error_when_loop_dies(caplog):
    """A maintenance task finishing with an escaped exception logs at ERROR."""

    async def doomed():
        raise ValueError("escaped the loop")

    task = asyncio.get_running_loop().create_task(doomed(), name="doomed-loop")
    task.add_done_callback(log_task_death)
    with caplog.at_level(logging.ERROR, logger="api.startup.metrics_flushers"):
        with pytest.raises(ValueError):
            await task
        # done-callbacks run via call_soon — yield once so it fires.
        await asyncio.sleep(0)

    assert any("maintenance_loop_died" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_log_task_death_logs_error_when_loop_returns(caplog):
    """A maintenance task RETURNING (loop exited without exception) also logs."""

    async def returns():
        return None

    task = asyncio.get_running_loop().create_task(returns(), name="returning-loop")
    task.add_done_callback(log_task_death)
    with caplog.at_level(logging.ERROR, logger="api.startup.metrics_flushers"):
        await task
        await asyncio.sleep(0)

    assert any("maintenance_loop_exited" in rec.message for rec in caplog.records)


@pytest.mark.asyncio
async def test_log_task_death_silent_on_cancellation(caplog):
    """Cancellation is the one legitimate exit — no ERROR noise at shutdown."""

    async def forever():
        while True:
            await asyncio.sleep(3600)

    task = asyncio.get_running_loop().create_task(forever(), name="cancelled-loop")
    task.add_done_callback(log_task_death)
    await asyncio.sleep(0)
    task.cancel()
    with caplog.at_level(logging.ERROR, logger="api.startup.metrics_flushers"):
        with pytest.raises(asyncio.CancelledError):
            await task
        await asyncio.sleep(0)

    assert not any("maintenance_loop" in rec.message for rec in caplog.records)


# ---------------------------------------------------------------------------
# Item 1: /health exposes degraded_services
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_endpoint_exposes_degraded_services(monkeypatch):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from api.app_state import state
    from api.wiring.events import register_event_handlers

    app = FastAPI()
    register_event_handlers(app)
    monkeypatch.setattr(state, "degraded_services", ["backup_scheduler", "deletion_reaper"])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    body = response.json()
    assert body["status"] == "degraded"
    assert body["checks"]["degraded_services"] == ["backup_scheduler", "deletion_reaper"]


@pytest.mark.asyncio
async def test_health_endpoint_omits_degraded_services_when_empty(monkeypatch):
    from fastapi import FastAPI
    from httpx import ASGITransport, AsyncClient

    from api.app_state import state
    from api.wiring.events import register_event_handlers

    app = FastAPI()
    register_event_handlers(app)
    monkeypatch.setattr(state, "degraded_services", [])

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert "degraded_services" not in response.json()["checks"]
