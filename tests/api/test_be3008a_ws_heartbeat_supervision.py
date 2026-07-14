# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-3008a regression: realtime heartbeat supervision + unsafe-iteration snapshots.

Edition Scope: Both (api/websocket.py + api/startup/core_services.py are CE-shared;
WS broadcast logic does not differ by GILJO_MODE).

Three guarantees are pinned here:

1. ``notify_entity_update`` no longer crashes when a subscriber's send fails.
   Pre-fix it iterated the LIVE ``entity_subscribers`` set while a failed send
   triggered an inline ``disconnect()`` that mutated that very set -> CPython
   raised ``RuntimeError: Set changed size during iteration`` on the next step.
   The fix snapshots the set and routes all cleanup through one deferred path.

2. The heartbeat task is supervised: an unexpected death restarts it (with a
   Sentry breadcrumb + log), while a shutdown-driven ``cancel()`` does NOT
   resurrect it.

3. Happy path + the BE-6029 identity-safe registry are unchanged: a normal
   fan-out to N subscribers still delivers, and a wedged/failed client is
   dropped without aborting the broadcast.

4. BE-9016 (Sentry GILJOAI-BACKEND-B): ``send_heartbeat`` pinging a client that
   already disconnected raises ``WebSocketDisconnect`` / ``ConnectionClosed`` --
   NOT the ``(RuntimeError, OSError, TimeoutError)`` tuple this used to catch --
   so the exception escaped and killed the ``start_heartbeat`` loop. Both
   exception types must now be caught and the client dropped like any other
   send failure, AND ``start_heartbeat``'s loop body must log-and-continue on
   any other unexpected per-cycle exception while still letting a shutdown
   ``CancelledError`` propagate cleanly.

Tests drive the manager directly with lightweight fake sockets — no DB, no
module-level mutable state (parallel-safe under xdist).
"""

from __future__ import annotations

import asyncio
import contextlib
from types import SimpleNamespace

import pytest
import websockets.exceptions
from fastapi import WebSocketDisconnect

from api.websocket import WebSocketManager


class _FakeWS:
    """Minimal Starlette-WebSocket stand-in with configurable send behavior."""

    def __init__(
        self,
        *,
        fail: bool = False,
        hang_seconds: float | None = None,
        fail_exc: BaseException | None = None,
    ) -> None:
        self.fail = fail
        self.hang_seconds = hang_seconds
        self.fail_exc = fail_exc
        self.sent: list[dict] = []
        self.closed = False

    async def send_json(self, data: dict) -> None:
        if self.hang_seconds is not None:
            await asyncio.sleep(self.hang_seconds)
        if self.fail_exc is not None:
            raise self.fail_exc
        if self.fail:
            raise RuntimeError("simulated send failure")
        self.sent.append(data)

    async def send_text(self, data: str) -> None:
        if self.fail:
            raise RuntimeError("simulated send failure")
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True


def _wire_subscriber(mgr: WebSocketManager, client_id: str, ws: _FakeWS, entity_key: str) -> None:
    """Populate the manager so ``client_id`` is a live subscriber of ``entity_key``.

    Mirrors the post-connect+subscribe state without going through the auth
    check, so we can set up the exact crash condition deterministically.
    """
    mgr.active_connections[client_id] = ws
    mgr.auth_contexts[client_id] = {"tenant_key": "tk_x"}
    mgr.subscriptions[client_id] = {entity_key}
    mgr.entity_subscribers.setdefault(entity_key, set()).add(client_id)


# ---------------------------------------------------------------------------
# (1) notify_entity_update crash repro — the audit headline
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_notify_entity_update_survives_subscriber_send_failure():
    """A failing subscriber must NOT crash the fan-out (pre-fix: RuntimeError).

    Two subscribers share one entity; the first send fails, which triggers a
    disconnect that — pre-fix — mutated the set being iterated. Post-fix the
    iteration runs over a snapshot and the failed client is dropped cleanly.
    """
    mgr = WebSocketManager()
    entity_key = "project:p1"

    failing = _FakeWS(fail=True)
    healthy = _FakeWS()
    _wire_subscriber(mgr, "c-fail", failing, entity_key)
    _wire_subscriber(mgr, "c-ok", healthy, entity_key)

    # Pre-fix this raised "RuntimeError: Set changed size during iteration".
    await mgr.notify_entity_update("project", "p1", {"hello": "world"})

    # Healthy client received the update; failed client was disconnected.
    assert len(healthy.sent) == 1
    assert "c-fail" not in mgr.active_connections
    # The failed client was also removed from the entity subscriber set.
    assert "c-fail" not in mgr.entity_subscribers.get(entity_key, set())
    # The healthy subscriber survives.
    assert "c-ok" in mgr.entity_subscribers.get(entity_key, set())


@pytest.mark.asyncio
async def test_notify_entity_update_single_failing_subscriber():
    """Even a single failing subscriber triggers the size-change check pre-fix."""
    mgr = WebSocketManager()
    entity_key = "agent:p1:builder"

    failing = _FakeWS(fail=True)
    _wire_subscriber(mgr, "only-client", failing, entity_key)

    await mgr.notify_entity_update("agent", "p1:builder", {"x": 1})

    assert "only-client" not in mgr.active_connections
    assert entity_key not in mgr.entity_subscribers  # set emptied + pruned


# ---------------------------------------------------------------------------
# (2) bounded per-client send timeout — drop-not-abort
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_wedged_client_is_dropped_not_aborting_broadcast(monkeypatch):
    """A wedged client (send hangs) is dropped via the bounded timeout; the
    rest of the fan-out still completes."""
    import api.websocket as ws_mod

    monkeypatch.setattr(ws_mod, "_WS_SEND_TIMEOUT_SECONDS", 0.05)

    mgr = WebSocketManager()
    entity_key = "project:p2"

    wedged = _FakeWS(hang_seconds=5.0)  # far longer than the patched timeout
    healthy = _FakeWS()
    _wire_subscriber(mgr, "c-wedged", wedged, entity_key)
    _wire_subscriber(mgr, "c-ok", healthy, entity_key)

    await asyncio.wait_for(mgr.notify_entity_update("project", "p2", {"k": "v"}), timeout=2)

    assert len(healthy.sent) == 1
    assert "c-wedged" not in mgr.active_connections


# ---------------------------------------------------------------------------
# (3) heartbeat supervision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_heartbeat_supervisor_restarts_on_unexpected_death():
    from api.startup.core_services import _start_supervised_heartbeat

    calls = {"n": 0}
    alive = asyncio.Event()

    async def fake_start_heartbeat(interval: int = 30):
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("heartbeat boom")  # first body crashes
        alive.set()
        await asyncio.sleep(3600)  # restarted body stays alive

    state = SimpleNamespace(
        websocket_manager=SimpleNamespace(start_heartbeat=fake_start_heartbeat),
        heartbeat_task=None,
    )

    _start_supervised_heartbeat(state, interval=30)

    # Supervisor restarted the task after the crash.
    await asyncio.wait_for(alive.wait(), timeout=2)
    assert calls["n"] == 2
    assert state.heartbeat_task is not None
    assert not state.heartbeat_task.done()

    state.heartbeat_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await state.heartbeat_task


@pytest.mark.asyncio
async def test_heartbeat_supervisor_does_not_resurrect_on_shutdown_cancel():
    from api.startup.core_services import _start_supervised_heartbeat

    calls = {"n": 0}

    async def fake_start_heartbeat(interval: int = 30):
        calls["n"] += 1
        await asyncio.sleep(3600)

    state = SimpleNamespace(
        websocket_manager=SimpleNamespace(start_heartbeat=fake_start_heartbeat),
        heartbeat_task=None,
    )

    _start_supervised_heartbeat(state, interval=30)
    task = state.heartbeat_task
    await asyncio.sleep(0)  # let it start
    assert calls["n"] == 1

    # Shutdown cancels it — the supervisor must NOT create a replacement.
    task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await task
    await asyncio.sleep(0)  # let the done-callback run

    assert calls["n"] == 1  # no restart
    assert state.heartbeat_task is task  # reference unchanged
    assert state.heartbeat_task.cancelled()


# ---------------------------------------------------------------------------
# (4) happy path + BE-6029 identity-safe registry unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_heartbeat_delivers_to_all_and_drops_failures():
    mgr = WebSocketManager()
    ok1, ok2, bad = _FakeWS(), _FakeWS(), _FakeWS(fail=True)
    mgr.active_connections["a"] = ok1
    mgr.active_connections["b"] = ok2
    mgr.active_connections["c"] = bad

    await mgr.send_heartbeat()

    assert len(ok1.sent) == 1 and len(ok2.sent) == 1
    assert "c" not in mgr.active_connections  # failed client pruned
    assert "a" in mgr.active_connections and "b" in mgr.active_connections


@pytest.mark.asyncio
async def test_notify_entity_update_happy_path_delivers_to_all_subscribers():
    mgr = WebSocketManager()
    entity_key = "project:p3"
    subs = {f"c{i}": _FakeWS() for i in range(4)}
    for cid, ws in subs.items():
        _wire_subscriber(mgr, cid, ws, entity_key)

    await mgr.notify_entity_update("project", "p3", {"n": 1})

    for ws in subs.values():
        assert len(ws.sent) == 1
    assert mgr.entity_subscribers[entity_key] == set(subs)


# ---------------------------------------------------------------------------
# (5) BE-9016 (Sentry GILJOAI-BACKEND-B): WebSocketDisconnect / ConnectionClosed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_send_heartbeat_drops_client_on_websocket_disconnect():
    """A client whose send raises WebSocketDisconnect must be dropped, not
    propagate out of send_heartbeat (pre-fix: escaped the (RuntimeError, OSError,
    TimeoutError) tuple and killed the start_heartbeat loop)."""
    mgr = WebSocketManager()
    ok = _FakeWS()
    gone = _FakeWS(fail_exc=WebSocketDisconnect())
    mgr.active_connections["ok"] = ok
    mgr.active_connections["gone"] = gone

    # Must return normally -- no exception escapes.
    await mgr.send_heartbeat()

    assert len(ok.sent) == 1
    assert "gone" not in mgr.active_connections
    assert "ok" in mgr.active_connections


@pytest.mark.asyncio
async def test_send_heartbeat_drops_client_on_connection_closed():
    """Same guarantee for websockets.exceptions.ConnectionClosed (the other
    disconnect exception the pre-fix tuple did not catch)."""
    mgr = WebSocketManager()
    ok = _FakeWS()
    gone = _FakeWS(fail_exc=websockets.exceptions.ConnectionClosedError(None, None))
    mgr.active_connections["ok"] = ok
    mgr.active_connections["gone"] = gone

    await mgr.send_heartbeat()

    assert len(ok.sent) == 1
    assert "gone" not in mgr.active_connections
    assert "ok" in mgr.active_connections


@pytest.mark.asyncio
async def test_start_heartbeat_loop_survives_unexpected_cycle_exception(monkeypatch):
    """Defense-in-depth: an unexpected exception escaping one heartbeat cycle
    must not kill the start_heartbeat loop -- it should log-and-continue so the
    NEXT cycle still runs, without waiting on the outer task-level supervisor
    (api/startup/core_services.py) to restart it."""
    mgr = WebSocketManager()
    calls = {"n": 0}

    async def flaky_send_heartbeat():
        calls["n"] += 1
        if calls["n"] == 1:
            raise RuntimeError("simulated unexpected heartbeat failure")

    monkeypatch.setattr(mgr, "send_heartbeat", flaky_send_heartbeat)

    task = asyncio.create_task(mgr.start_heartbeat(interval=0))
    try:
        for _ in range(200):
            if calls["n"] >= 3:
                break
            await asyncio.sleep(0.01)
    finally:
        task.cancel()
        with contextlib.suppress(asyncio.CancelledError):
            await task

    assert calls["n"] >= 3, "start_heartbeat must keep looping after a cycle raises"


@pytest.mark.asyncio
async def test_start_heartbeat_lets_cancelled_error_propagate_for_shutdown():
    """CancelledError (clean shutdown) must NOT be swallowed by the loop-body
    log-and-continue catch -- cancelling the task must actually stop it."""
    mgr = WebSocketManager()

    async def slow_send_heartbeat():
        await asyncio.sleep(3600)

    mgr.send_heartbeat = slow_send_heartbeat  # type: ignore[method-assign]

    task = asyncio.create_task(mgr.start_heartbeat(interval=0))
    await asyncio.sleep(0.01)
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
