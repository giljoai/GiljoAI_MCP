# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6072 regression: WebSocket fan-out safety.

Edition Scope: Both (api/websocket.py is CE-shared; WS broadcast logic does not
differ by GILJO_MODE).

Pins the guarantees this work order hardens, each at the FAILING layer:

1. F4 (manager layer): ``broadcast_event_to_tenant`` was the only fan-out method
   still doing a bare, timeout-less ``send_json``. A wedged client could stall
   the whole per-tenant fan-out (and hold a pooled DB connection when called
   inside an open session) for ~40s. The send is now bounded by
   ``_WS_SEND_TIMEOUT_SECONDS`` and a stalled client is EVICTED, not waited on,
   while a healthy client in the same tenant still receives the event.

2. m15 (manager layer): on a single-worker deployment the cross-worker pg_notify
   publish is pure overhead, so it is skipped; and a pg_notify payload over the
   ~8000 byte limit raises ``asyncpg.PostgresError`` which is now caught +
   swallowed (local delivery already happened).

BE-9012d: m1 (``POST /api/messages`` swallowing a broadcast failure) was removed
with the bus REST layer (``api/endpoints/messages.py`` hard-removed) — F4's
manager-layer resilience is the general guarantee any REST caller now relies on.

Tests drive the manager directly with lightweight fakes — no DB, no module-level
mutable state (parallel-safe under xdist).
"""

from __future__ import annotations

import asyncio

import asyncpg
import pytest

from api.websocket import WebSocketManager


class _FakeWS:
    """Minimal Starlette-WebSocket stand-in with configurable send behavior."""

    def __init__(self, *, fail: bool = False, hang_seconds: float | None = None) -> None:
        self.fail = fail
        self.hang_seconds = hang_seconds
        self.sent: list[dict] = []
        self.closed = False

    async def send_json(self, data: dict) -> None:
        if self.hang_seconds is not None:
            await asyncio.sleep(self.hang_seconds)
        if self.fail:
            raise RuntimeError("simulated send failure")
        self.sent.append(data)

    async def send_text(self, data: str) -> None:
        # BE-3008b: the tenant fan-out now serializes once and delivers via
        # send_text; mirror the configurable hang/fail behaviour here.
        if self.hang_seconds is not None:
            await asyncio.sleep(self.hang_seconds)
        if self.fail:
            raise RuntimeError("simulated send failure")
        self.sent.append(data)

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True


class _FakeBroker:
    """Minimal WebSocketEventBroker stand-in tracking publish calls."""

    def __init__(self, *, raise_postgres_error: bool = False) -> None:
        self.publish_count = 0
        self.raise_postgres_error = raise_postgres_error

    def subscribe(self, handler):
        def _unsubscribe() -> None:
            return None

        return _unsubscribe

    async def publish(self, message) -> None:
        self.publish_count += 1
        if self.raise_postgres_error:
            # Mirrors the pg_notify ~8000-byte payload limit error class.
            raise asyncpg.PostgresError("payload string too long")


def _wire_client(mgr: WebSocketManager, client_id: str, ws: _FakeWS, tenant_key: str) -> None:
    """Register ``client_id`` as a live connection in ``tenant_key``."""
    mgr.active_connections[client_id] = ws
    mgr.auth_contexts[client_id] = {"tenant_key": tenant_key}
    # BE-3008b: the tenant fan-out now iterates the tenant index, so a directly
    # wired client must be registered there too (connect() does this in prod).
    mgr._index_tenant_connection(client_id, tenant_key)


def _event(tenant_key: str) -> dict:
    return {"type": "test:event", "data": {"tenant_key": tenant_key, "n": 1}}


# ---------------------------------------------------------------------------
# (1) F4 — broadcast_event_to_tenant bounds the send + evicts a stalled client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_event_to_tenant_evicts_stalled_client(monkeypatch):
    """A wedged client is dropped via the bounded timeout; a healthy client in
    the same tenant still receives the event, and the call returns promptly."""
    import api.websocket as ws_mod

    monkeypatch.setattr(ws_mod, "_WS_SEND_TIMEOUT_SECONDS", 0.05)

    mgr = WebSocketManager()
    tenant = "tk_f4"
    wedged = _FakeWS(hang_seconds=5.0)  # far longer than the patched timeout
    healthy = _FakeWS()
    _wire_client(mgr, "c-wedged", wedged, tenant)
    _wire_client(mgr, "c-ok", healthy, tenant)

    # (3) returns within ~timeout (does not hang); outer guard catches a regression.
    sent_count = await asyncio.wait_for(
        mgr.broadcast_event_to_tenant(tenant_key=tenant, event=_event(tenant)),
        timeout=2,
    )

    # (2) still delivers to the healthy client.
    assert sent_count == 1
    assert len(healthy.sent) == 1
    assert "c-ok" in mgr.active_connections
    # (1) evicts the stalled client.
    assert "c-wedged" not in mgr.active_connections


@pytest.mark.asyncio
async def test_broadcast_event_to_tenant_happy_path_delivers_to_all(monkeypatch):
    """Sanity: a healthy multi-client tenant fan-out still delivers to everyone."""
    import api.websocket as ws_mod

    monkeypatch.setattr(ws_mod, "_WS_SEND_TIMEOUT_SECONDS", 0.5)

    mgr = WebSocketManager()
    tenant = "tk_happy"
    clients = {f"c{i}": _FakeWS() for i in range(3)}
    for cid, ws in clients.items():
        _wire_client(mgr, cid, ws, tenant)

    sent_count = await mgr.broadcast_event_to_tenant(tenant_key=tenant, event=_event(tenant))

    assert sent_count == 3
    for ws in clients.values():
        assert len(ws.sent) == 1


# ---------------------------------------------------------------------------
# (3) m15 — single-worker publish skip + asyncpg.PostgresError swallow
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_worker_skips_broker_publish(monkeypatch):
    """When worker count == 1 the self-echo publish is skipped (pure overhead)."""
    monkeypatch.setattr("api.startup.database._worker_count", lambda: 1)

    mgr = WebSocketManager()
    broker = _FakeBroker()
    mgr.attach_broker(broker)
    assert mgr._publish_to_broker_enabled is False

    tenant = "tk_single"
    _wire_client(mgr, "c1", _FakeWS(), tenant)

    sent_count = await mgr.broadcast_event_to_tenant(tenant_key=tenant, event=_event(tenant))

    assert sent_count == 1  # local delivery unaffected
    assert broker.publish_count == 0  # publish skipped


@pytest.mark.asyncio
async def test_multi_worker_still_publishes(monkeypatch):
    """When worker count > 1 the cross-worker publish still happens."""
    monkeypatch.setattr("api.startup.database._worker_count", lambda: 2)

    mgr = WebSocketManager()
    broker = _FakeBroker()
    mgr.attach_broker(broker)
    assert mgr._publish_to_broker_enabled is True

    tenant = "tk_multi"
    _wire_client(mgr, "c1", _FakeWS(), tenant)

    sent_count = await mgr.broadcast_event_to_tenant(tenant_key=tenant, event=_event(tenant))

    assert sent_count == 1
    assert broker.publish_count == 1


@pytest.mark.asyncio
async def test_broker_postgres_error_is_swallowed(monkeypatch):
    """An asyncpg.PostgresError from publish (e.g. >8KB pg_notify payload) is
    logged + swallowed; broadcast still returns its sent_count (local delivery
    already happened)."""
    monkeypatch.setattr("api.startup.database._worker_count", lambda: 2)

    mgr = WebSocketManager()
    broker = _FakeBroker(raise_postgres_error=True)
    mgr.attach_broker(broker)

    tenant = "tk_pgerr"
    _wire_client(mgr, "c1", _FakeWS(), tenant)

    # Must NOT raise despite publish raising asyncpg.PostgresError.
    sent_count = await mgr.broadcast_event_to_tenant(tenant_key=tenant, event=_event(tenant))

    assert sent_count == 1
    assert broker.publish_count == 1


# BE-9012d: (2) test_send_message_endpoint_swallows_broadcast_failure (m1) was
# removed with api/endpoints/messages.py (the bus REST layer). F4's manager-layer
# send-failure resilience above is the surviving, general-purpose guarantee.
