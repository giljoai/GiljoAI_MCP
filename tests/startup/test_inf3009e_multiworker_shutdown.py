# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-3009e — graceful-shutdown verification under the multi-worker web posture.

Deliverable (c) of the multi-worker unlock: confirm that a web process running the
real multi-worker posture (``WEB_CONCURRENCY=2`` with the background-job split ON,
so reapers live in the dedicated worker service, ``GILJO_RUN_BACKGROUND_JOBS=off``)
still drains cleanly on shutdown — in-flight WebSocket connections get close frames,
the cross-worker broker is stopped, and the supervised per-worker tasks cancel
without propagating ``CancelledError`` or any reaper-cancellation error.

The generic step behaviour is already covered by tests/startup/test_shutdown.py;
this file pins the specific invariant the multi-worker flip depends on, wired
through the same ``shutdown()`` entry point at the layer it runs.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.app_state import APIState
from api.startup.shutdown import shutdown


@pytest.mark.asyncio
async def test_graceful_shutdown_under_multiworker_web_posture(monkeypatch):
    """WEB_CONCURRENCY=2 + jobs-off: WS close frames sent, broker stopped, tasks
    cancelled cleanly, no error propagated."""
    monkeypatch.setenv("WEB_CONCURRENCY", "2")
    monkeypatch.setenv("GILJO_RUN_BACKGROUND_JOBS", "off")

    state = APIState()

    # A live supervised per-worker task (heartbeat) that must cancel cleanly.
    async def _forever():
        while True:
            await asyncio.sleep(1)

    state.heartbeat_task = asyncio.create_task(_forever())

    # In-flight WebSocket connections must each receive a close frame.
    ws_a = MagicMock()
    ws_a.close = AsyncMock()
    ws_b = MagicMock()
    ws_b.close = AsyncMock()
    state.connections = {"a": ws_a, "b": ws_b}

    # Cross-worker broker must be stopped.
    state.websocket_broker = MagicMock()
    state.websocket_broker.stop = AsyncMock()

    state.db_manager = MagicMock()
    state.db_manager.close_async = AsyncMock()

    # Must not raise — reapers are in the worker service, so no reaper task exists
    # here to mis-cancel; the web tasks drain gracefully.
    await shutdown(state)

    ws_a.close.assert_awaited_once()  # WS close frames sent
    ws_b.close.assert_awaited_once()
    state.websocket_broker.stop.assert_awaited_once()  # broker stopped
    state.db_manager.close_async.assert_awaited_once()
    assert state.heartbeat_task.cancelled()  # supervised task cancelled cleanly
