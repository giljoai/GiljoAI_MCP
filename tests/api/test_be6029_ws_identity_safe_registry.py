# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6029 regression: identity-safe WebSocket connection registry.

The WebSocketManager registry is keyed by client_id. Before BE-6029:
  * connect() blindly overwrote active_connections[client_id], so a reconnect
    that reused an id left two live sockets fighting over one key, and
  * disconnect() removed purely by client_id, so a STALE socket's late teardown
    would evict the NEWER live socket — orphaning it from every broadcast (the
    "real-time silently stops until F5" symptom).

These guards exercise the manager directly with lightweight fake sockets.
"""

from __future__ import annotations

import pytest

from api.websocket import WebSocketManager


class _FakeWS:
    """Minimal stand-in for a Starlette WebSocket with an awaitable close()."""

    def __init__(self) -> None:
        self.closed = False
        self.close_code: int | None = None
        self.close_reason: str | None = None

    async def close(self, code: int = 1000, reason: str = "") -> None:
        self.closed = True
        self.close_code = code
        self.close_reason = reason


@pytest.mark.asyncio
async def test_reconnect_same_client_id_supersedes_and_closes_old_socket():
    mgr = WebSocketManager()
    ws1, ws2 = _FakeWS(), _FakeWS()

    await mgr.connect(ws1, "client-1", {"tenant_key": "tk_x"})
    assert mgr.active_connections["client-1"] is ws1

    # A second socket arrives under the SAME client_id.
    await mgr.connect(ws2, "client-1", {"tenant_key": "tk_x"})

    # New socket is registered; the superseded one is closed (code 1012).
    assert mgr.active_connections["client-1"] is ws2
    assert ws1.closed is True
    assert ws1.close_code == 1012
    assert ws2.closed is False


@pytest.mark.asyncio
async def test_stale_socket_teardown_does_not_evict_the_live_socket():
    mgr = WebSocketManager()
    ws1, ws2 = _FakeWS(), _FakeWS()

    await mgr.connect(ws1, "client-1", {"tenant_key": "tk_x"})
    await mgr.connect(ws2, "client-1", {"tenant_key": "tk_x"})  # ws2 now owns client-1

    # ws1's delayed receive-loop teardown calls identity-safe disconnect — it
    # must NOT remove ws2, which has taken over the client_id.
    mgr.disconnect("client-1", ws1)

    assert mgr.active_connections.get("client-1") is ws2


@pytest.mark.asyncio
async def test_identity_disconnect_removes_the_matching_socket():
    mgr = WebSocketManager()
    ws1 = _FakeWS()

    await mgr.connect(ws1, "client-1", {"tenant_key": "tk_x"})
    mgr.disconnect("client-1", ws1)

    assert "client-1" not in mgr.active_connections


@pytest.mark.asyncio
async def test_legacy_disconnect_without_socket_removes_by_id():
    # Internal send-failure cleanup calls disconnect(client_id) with no socket;
    # that path must still remove the entry by id (back-compat).
    mgr = WebSocketManager()
    ws1 = _FakeWS()

    await mgr.connect(ws1, "client-1", {"tenant_key": "tk_x"})
    mgr.disconnect("client-1")

    assert "client-1" not in mgr.active_connections
