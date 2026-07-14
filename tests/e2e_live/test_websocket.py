# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""(e) WebSocket upgrade handshake is honored through the proxy path.

The unique value here is proving the Cloudflare -> nginx -> uvicorn chain
forwards an ``Upgrade: websocket`` handshake to the ASGI app at
``/ws/{client_id}`` (the regression class behind the BE-6029 WS storm). We send
a raw, dependency-free handshake and inspect the HTTP status line — no valid
auth required.
"""

from __future__ import annotations

import base64
import os
import socket
import ssl

import pytest


def _ws_handshake_status(target, path: str = "/ws/e2e-probe", timeout: int = 15):
    """Send a raw RFC 6455 upgrade handshake and return (status_code, status_line)."""
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {target.host}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        "\r\n"
    ).encode("ascii")

    raw = socket.create_connection((target.host, target.port), timeout=timeout)
    sock = raw
    try:
        if target.scheme == "https":
            ctx = ssl.create_default_context()
            sock = ctx.wrap_socket(raw, server_hostname=target.host)
        sock.settimeout(timeout)
        sock.sendall(request)
        data = sock.recv(4096)
    finally:
        sock.close()

    status_line = data.split(b"\r\n", 1)[0].decode("latin-1") if data else ""
    fields = status_line.split()
    code = int(fields[1]) if len(fields) >= 2 and fields[1].isdigit() else None
    return code, status_line


@pytest.mark.network
def test_websocket_upgrade_handshake(target):
    """The /ws route participates in the upgrade negotiation through the edge.

    Accepted outcomes:
      * 101 — upgrade accepted (setup mode or an authenticated probe).
      * 401/403 — the app's WS auth rejected an UNAUTHENTICATED probe (the
        common case on a configured host: authenticate_websocket raises before
        accept, so the handshake is refused at the HTTP layer). This still
        proves the route exists and the proxy forwarded the Upgrade.

    A 404 (route missing / SPA fallback) or 5xx (proxy dropped the upgrade) is a
    real failure.
    """
    code, status_line = _ws_handshake_status(target)
    assert code in (101, 401, 403), f"unexpected WS handshake response: {status_line!r}"
