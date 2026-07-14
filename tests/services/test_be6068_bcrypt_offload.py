# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6068 F1 regression: sync ``bcrypt`` must run OFF the event loop.

``bcrypt.checkpw``/``hashpw`` is ~250-400ms of pure CPU. Called directly inside
``async def`` it freezes the single uvicorn worker — every concurrent request,
MCP call and WS frame stalls for the duration. F1 wraps every remaining bcrypt
site in ``asyncio.to_thread`` (mirroring BE-6060a's ``verify_api_key_cached``).
Additionally, ``AuthService.authenticate_user`` was restructured so the verify
runs AFTER the user-lookup session is released, so the CPU work no longer pins a
pooled DB connection.

These tests patch ``asyncio.to_thread`` and assert the bcrypt call is dispatched
through it (not called inline), and that login still succeeds.
"""

from __future__ import annotations

import asyncio
import contextlib

import bcrypt
import pytest

from giljo_mcp.schemas.service_responses import AuthResult


pytestmark = pytest.mark.asyncio


async def test_authenticate_user_offloads_bcrypt_after_session_close(
    monkeypatch, auth_service, auth_user_with_password
):
    """Login dispatches bcrypt.checkpw via to_thread, AFTER releasing the session.

    Proves both halves of the F1 fix for the login hot path: (1) the verify runs
    off the event loop, and (2) it runs after the user-lookup ``async with
    _get_session()`` block exits, so the bcrypt CPU no longer pins a connection.
    """
    user, password = auth_user_with_password

    events: list[str] = []

    # Record when the lookup session context exits (delegates to the real one).
    original_get_session = auth_service._get_session

    def _recording_get_session(tenant_key: str | None = None):
        @contextlib.asynccontextmanager
        async def _wrap():
            async with original_get_session(tenant_key) as session:
                yield session
            events.append("session_closed")

        return _wrap()

    monkeypatch.setattr(auth_service, "_get_session", _recording_get_session)

    # Spy on the offload seam; record only the bcrypt dispatch.
    real_to_thread = asyncio.to_thread

    async def _spy(fn, *args, **kwargs):
        if fn is bcrypt.checkpw:
            events.append("bcrypt_offload")
        return await real_to_thread(fn, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", _spy)

    result = await auth_service.authenticate_user(user.username, password)

    # Behavior preserved: a valid login still returns an AuthResult.
    assert isinstance(result, AuthResult)
    assert result.user_id == user.id

    # Offload proven: bcrypt went through a worker thread, not the loop.
    assert "bcrypt_offload" in events, "bcrypt.checkpw was not offloaded via asyncio.to_thread"
    # Restructure proven: the lookup session released before the verify ran.
    assert events.index("session_closed") < events.index("bcrypt_offload"), (
        "bcrypt verify ran while the DB session was still open"
    )


async def test_authenticate_user_invalid_password_still_offloads(monkeypatch, auth_service, auth_user_with_password):
    """A failed login also routes through to_thread (no inline bcrypt fast-path)."""
    from giljo_mcp.exceptions import AuthenticationError

    user, _ = auth_user_with_password

    offloaded: list[bool] = []
    real_to_thread = asyncio.to_thread

    async def _spy(fn, *args, **kwargs):
        if fn is bcrypt.checkpw:
            offloaded.append(True)
        return await real_to_thread(fn, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", _spy)

    with pytest.raises(AuthenticationError):
        await auth_service.authenticate_user(user.username, "WrongPassword123!")

    assert offloaded, "bcrypt.checkpw was not offloaded on the invalid-password path"


async def test_oauth_client_secret_verify_offloads_bcrypt(monkeypatch):
    """Confidential-client secret verify (/token + /refresh) offloads bcrypt.

    DB-free: a stub ClientResolver returns a ResolvedClient carrying a real
    bcrypt hash. The single wrapped site at oauth_service.py is the only bcrypt
    on both the /token exchange and the /refresh grant paths.
    """
    from giljo_mcp.services.oauth_service import (
        OAuthService,
        ResolvedClient,
        get_client_resolver,
        set_client_resolver,
    )

    secret = "confidential-secret-value"
    secret_hash = bcrypt.hashpw(secret.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    client = ResolvedClient(
        client_id="test-client",
        client_name="Test Client",
        redirect_uris=["https://example.com/cb"],
        client_secret_hash=secret_hash,
    )

    saved_resolver = get_client_resolver()
    set_client_resolver(lambda client_id, tenant_key: client)
    try:
        offloaded: list[bool] = []
        real_to_thread = asyncio.to_thread

        async def _spy(fn, *args, **kwargs):
            if fn is bcrypt.checkpw:
                offloaded.append(True)
            return await real_to_thread(fn, *args, **kwargs)

        monkeypatch.setattr(asyncio, "to_thread", _spy)

        resolved = await OAuthService._verify_client_authentication(
            client_id="test-client",
            tenant_key="test-tenant",
            client_secret=secret,
        )

        assert resolved is client
        assert offloaded, "bcrypt.checkpw was not offloaded via asyncio.to_thread"
    finally:
        set_client_resolver(saved_resolver)
