# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6236 — WebSocket auth over plain HTTP (non-Secure access_token cookie).

Failing layer = the WS auth path in ``api/auth_utils.py`` (``authenticate_websocket``),
the exact code the ``/ws/{client_id}`` handshake runs.

The HTTP-default-LAN work makes ``http://<lan-ip>`` a first-class deployment.
Over plain http the browser writes the keystone ``access_token`` cookie WITHOUT
the Secure flag (``_build_cookie_params`` derives Secure from the request scheme
-- covered in ``tests/unit/test_build_cookie_params.py``). This test pins the
OTHER half of the round-trip: the server-side WS handshake authenticates from
that non-Secure cookie value sent over an http origin. A Cookie *request* header
never carries the Secure attribute (Secure only appears in Set-Cookie responses),
so the server must authenticate purely on the token value -- it must not depend
on scheme or on any Secure marker.

Two-sided: a valid cookie authenticates; a garbage cookie is rejected (1008).
xdist-safe: unique tenant_key per test, no module-level mutable state,
``db_session`` is transaction-rolled-back.
"""

from __future__ import annotations

from uuid import uuid4

import bcrypt
import pytest
from fastapi import WebSocketException

from api.auth_utils import authenticate_websocket
from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.models.auth import User
from giljo_mcp.models.organizations import Organization
from giljo_mcp.tenant import TenantManager


class _CookieWebSocket:
    """WebSocket stand-in carrying an access_token cookie over an http handshake.

    Mirrors what Starlette exposes to ``authenticate_websocket``: ``query_params``
    and a header mapping whose ``cookie`` entry is the raw Cookie request header.
    A real Cookie header is just ``name=value`` pairs -- there is no Secure marker
    on the request side, which is exactly why a non-Secure (http) cookie still
    presents identically here.
    """

    def __init__(self, cookie_header: str) -> None:
        self.query_params: dict[str, str] = {}
        self.headers: dict[str, str] = {"cookie": cookie_header}


async def _seed_user(db_session) -> tuple[str, str, str, str]:
    """Seed org+user (flushed, not committed). Returns (user_id, username, role, tenant_key)."""
    tk = TenantManager.generate_tenant_key()
    unique = uuid4().hex[:8]

    org = Organization(
        name=f"INF6236 Org {unique}",
        slug=f"inf6236-org-{unique}",
        tenant_key=tk,
        is_active=True,
    )
    db_session.add(org)
    await db_session.flush()

    user_id = str(uuid4())
    username = f"inf6236_user_{unique}"
    user = User(
        id=user_id,
        username=username,
        email=f"inf6236_{unique}@example.com",
        password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
        tenant_key=tk,
        role="developer",
        org_id=org.id,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    return user_id, username, "developer", tk


class TestWebSocketAuthOverHttp:
    """A non-Secure access_token cookie sent over http must authenticate the WS handshake."""

    @pytest.mark.asyncio
    async def test_non_secure_cookie_authenticates(self, db_session):
        user_id, username, role, tk = await _seed_user(db_session)
        token = JWTManager.create_access_token(user_id=user_id, username=username, role=role, tenant_key=tk)

        # Plain "access_token=<jwt>" -- exactly how the browser presents a cookie
        # that was set WITHOUT Secure over http (no Secure attribute on the wire).
        ws = _CookieWebSocket(cookie_header=f"access_token={token}")

        result = await authenticate_websocket(ws, db=db_session)

        assert result["authenticated"] is True, "a valid http (non-Secure) cookie must authenticate the WS"
        assert result["user"]["tenant_key"] == tk

    @pytest.mark.asyncio
    async def test_garbage_cookie_rejected(self, db_session):
        # Allow-bad side: a non-Secure cookie carrying junk must still be rejected
        # (1008) -- relaxing the transport does not relax token validation.
        await _seed_user(db_session)  # ensure DB is "initialized" so we hit the auth branch
        ws = _CookieWebSocket(cookie_header="access_token=not-a-real-jwt")

        with pytest.raises(WebSocketException):
            await authenticate_websocket(ws, db=db_session)
