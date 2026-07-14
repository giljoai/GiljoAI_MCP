# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression tests for BE-6060a — MCP transport + auth hot-path hardening.

This boundary (``MCPAuthMiddleware`` + ``api_key_utils``) shipped the GET /mcp
SSE storm with ZERO tests; per CLAUDE.md the fix MUST add regression coverage
at the failing layer (the ASGI middleware + the cached verify path), not at a
unit layer that the production bug bypassed.

The five mandated guarantees (DoD):

1. ``TestGetReturns405``         — GET /mcp → 405, empty body, NO SSE retry hint
                                   and NOT ``text/event-stream``; ``Allow: POST, DELETE``.
2. ``TestNo3xxEverEmitted``      — no 3xx for /mcp on GET/POST/DELETE/OPTIONS
                                   (the 307 trap is why the bridge route exists).
3. ``TestPostBodyByteParity``    — the inner SDK app sees the POST body bytes
                                   unchanged after the ``_replay_receive`` repair.
4. ``TestRevokedKeyIs401``       — a revoked/deactivated key + a still-valid
                                   ``Mcp-Session-Id`` → 401 (a session id must
                                   NEVER become a standalone bearer credential).
5. ``TestBcryptOffLoopAndCached``— ≤1 sync ``verify_api_key`` per key per TTL
                                   window under a 100-request burst, and an
                                   event-loop-lag probe proving bcrypt runs
                                   off-loop (``asyncio.to_thread``).

BE-6061 fold-in (REST dashboard X-API-Key path, ``get_current_user``):

6. ``TestDashboardApiKeyOffLoopAndCached`` — the dashboard X-API-Key dependency
                                   also verifies off-loop + caches: ≤1 bcrypt
                                   per key per TTL under a 100-request burst with
                                   the same loop-lag ceiling.
7. ``TestDashboardRevokedKeyBust`` — a revoked key on the dashboard path 401s
                                   once ``bust_api_key_cache`` fires, proving the
                                   shared cache-bust reaches this path too.

Failing-layer discipline: every case drives the real ASGI middleware, the real
``MCPSessionManager.authenticate_api_key``, or the real
``auth.dependencies.get_current_user`` — the exact code path a production client
hits. xdist-safe: unique tenant_key + key per test, no module-level mutable
state, no ordering deps.
"""

from __future__ import annotations

import asyncio
import json
import time
from datetime import UTC, datetime
from uuid import uuid4

import bcrypt
import pytest
import pytest_asyncio
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# ASGI drive harness (parameterized method — mirrors test_mcp_protocol_version)
# ---------------------------------------------------------------------------


class _CapturingInnerApp:
    """Minimal ASGI app that records whether the middleware reached it + the body."""

    def __init__(self, response_status: int = 200) -> None:
        self.called: bool = False
        self.body_seen: bytes = b""

    async def __call__(self, scope, receive, send) -> None:
        self.called = True
        message = await receive()
        self.body_seen = message.get("body", b"")
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b'{"jsonrpc":"2.0","id":1,"result":{}}'})


async def _drive_middleware(
    middleware,
    *,
    method: str,
    headers: list[tuple[bytes, bytes]],
    body: bytes = b"",
) -> tuple[int, dict[str, str], bytes]:
    """Run a single ASGI request through ``middleware`` for the given method/body."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "method": method,
        "path": "/mcp",
        "raw_path": b"/mcp",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "scheme": "http",
        "root_path": "",
    }

    captured_status: dict = {"code": 0}
    captured_headers: dict[str, str] = {}
    captured_body = bytearray()
    body_sent = {"done": False}

    async def receive() -> dict:
        if body_sent["done"]:
            return {"type": "http.disconnect"}
        body_sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message) -> None:
        if message["type"] == "http.response.start":
            captured_status["code"] = message["status"]
            for k, v in message.get("headers", []):
                key = k.decode("latin-1") if isinstance(k, bytes) else k
                val = v.decode("latin-1") if isinstance(v, bytes) else v
                captured_headers[key.lower()] = val
        elif message["type"] == "http.response.body":
            captured_body.extend(message.get("body", b""))

    await middleware(scope, receive, send)
    return captured_status["code"], captured_headers, bytes(captured_body)


def _jsonrpc_body(method: str, params: dict | None = None) -> bytes:
    payload: dict = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    return json.dumps(payload).encode("utf-8")


@pytest_asyncio.fixture
async def jwt_env(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    yield "test_secret_key"


async def _seed_api_key(db_manager) -> tuple[str, str, str]:
    """Create an org+user+api_key triplet.

    Returns ``(raw_api_key, tenant_key, api_key_id)``.
    """
    from giljo_mcp.api_key_utils import hash_api_key
    from giljo_mcp.models.auth import APIKey, User
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    tk = TenantManager.generate_tenant_key()
    unique = uuid4().hex[:8]
    # Unique hex immediately after gk_ so get_key_prefix() (first 12 chars) is
    # unique per key. This keeps authenticate_api_key's prefix-narrowed
    # candidate set at exactly one row even though seed data is committed,
    # avoiding cross-test/cross-run accumulation under the shared prefix.
    raw_key = f"gk_{uuid4().hex}{uuid4().hex}"
    key_id = str(uuid4())

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"BE6060a Org {unique}",
            slug=f"be6060a-org-{unique}",
            tenant_key=tk,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"be6060a_user_{unique}",
            email=f"be6060a_{unique}@example.com",
            password_hash=bcrypt.hashpw(b"pw", bcrypt.gensalt()).decode("utf-8"),
            tenant_key=tk,
            role="developer",
            org_id=org.id,
            is_active=True,
        )
        session.add(user)
        await session.flush()

        api_key = APIKey(
            id=key_id,
            tenant_key=tk,
            user_id=user.id,
            name=f"BE6060a Key {unique}",
            key_hash=hash_api_key(raw_key),
            key_prefix=f"{raw_key[:12]}...",
            permissions=["*"],
            is_active=True,
            created_at=datetime.now(UTC),
        )
        session.add(api_key)
        await session.commit()

    return raw_key, tk, key_id


# ---------------------------------------------------------------------------
# 1) GET /mcp → 405 pre-auth, no SSE retry hint
# ---------------------------------------------------------------------------


class TestGetReturns405:
    """GET /mcp must return 405 BEFORE auth, with no SSE retry hint."""

    @pytest.mark.asyncio
    async def test_get_returns_405_empty_body_no_sse_hint(self):
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        status, headers, body = await _drive_middleware(
            mw,
            method="GET",
            headers=[(b"accept", b"text/event-stream")],
        )

        assert status == 405, f"GET /mcp must be 405, got {status}"
        assert inner.called is False, "405 must short-circuit before the inner SDK app"
        # Empty (or trivially short) body — definitely not an SSE stream.
        assert b"retry:" not in body, "405 body must NOT carry an SSE `retry:` field"
        assert b"data:" not in body, "405 body must NOT be an SSE event stream"
        content_type = headers.get("content-type", "")
        assert "text/event-stream" not in content_type, (
            f"405 must NOT be text/event-stream (would trigger client re-poll): {content_type!r}"
        )

    @pytest.mark.asyncio
    async def test_get_405_advertises_allowed_methods(self):
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        _status, headers, _body = await _drive_middleware(
            mw,
            method="GET",
            headers=[],
        )

        allow = headers.get("allow", "")
        allowed = {m.strip().upper() for m in allow.split(",") if m.strip()}
        assert "POST" in allowed, f"Allow header must list POST: {allow!r}"
        assert "DELETE" in allowed, f"Allow header must list DELETE (session terminate): {allow!r}"
        assert "GET" not in allowed, f"Allow header must NOT list GET (that's what we reject): {allow!r}"

    @pytest.mark.asyncio
    async def test_get_405_precedes_auth(self):
        """An authless GET still gets 405 — proves the branch is pre-auth (not a 401)."""
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        status, _headers, _body = await _drive_middleware(mw, method="GET", headers=[])
        assert status == 405, f"405 (method) must win over 401 (no creds), got {status}"


# ---------------------------------------------------------------------------
# 2) No 3xx EVER on /mcp for any method
# ---------------------------------------------------------------------------


class TestNo3xxEverEmitted:
    """The middleware must never emit a 3xx for /mcp on any method."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["GET", "POST", "DELETE", "OPTIONS"])
    async def test_no_redirect_status(self, method):
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        body = _jsonrpc_body("tools/list") if method in ("POST", "DELETE") else b""
        status, _headers, _body = await _drive_middleware(
            mw,
            method=method,
            headers=[(b"content-type", b"application/json")],
            body=body,
        )

        assert not (300 <= status < 400), (
            f"/mcp {method} emitted a 3xx ({status}); the 307 trap is exactly why the bridge route exists"
        )


# ---------------------------------------------------------------------------
# 3) POST body byte-parity (the _replay_receive repair must not corrupt the body)
# ---------------------------------------------------------------------------


class TestPostBodyByteParity:
    """The inner SDK app must observe the POST body bytes unchanged after replay."""

    @pytest.mark.asyncio
    async def test_inner_app_sees_unchanged_body(self, db_manager, jwt_env):
        from api.app_state import state
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        raw_key, _tenant_key, _key_id = await _seed_api_key(db_manager)
        original_body = _jsonrpc_body(
            "initialize",
            params={"protocolVersion": "2025-06-18", "capabilities": {}, "marker": uuid4().hex},
        )

        prior_db = state.db_manager
        state.db_manager = db_manager
        try:
            inner = _CapturingInnerApp()
            mw = MCPAuthMiddleware(app=inner)

            status, _headers, _body = await _drive_middleware(
                mw,
                method="POST",
                headers=[
                    (b"x-api-key", raw_key.encode()),
                    (b"content-type", b"application/json"),
                ],
                body=original_body,
            )

            assert status == 200, f"valid initialize returned {status}"
            assert inner.called is True, "auth must reach inner app on valid key"
            assert inner.body_seen == original_body, (
                "inner SDK app saw a DIFFERENT body than was sent — _replay_receive corrupted the stream"
            )
        finally:
            state.db_manager = prior_db


# ---------------------------------------------------------------------------
# 4) Revoked key + valid session id → 401 (session id is not a bearer credential)
# ---------------------------------------------------------------------------


class TestRevokedKeyIs401:
    """A deactivated key must fail auth even when a valid Mcp-Session-Id is presented."""

    @pytest.mark.asyncio
    async def test_revoked_key_with_valid_session_id_returns_401(self, db_manager, jwt_env):
        from sqlalchemy import update

        from api.app_state import state
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware
        from giljo_mcp.api_key_utils import bust_api_key_cache
        from giljo_mcp.database import tenant_isolation_bypass
        from giljo_mcp.models.auth import APIKey

        raw_key, _tenant_key, key_id = await _seed_api_key(db_manager)

        prior_db = state.db_manager
        state.db_manager = db_manager
        try:
            # Step 1: initialize to mint a real session id while the key is valid.
            inner = _CapturingInnerApp()
            mw = MCPAuthMiddleware(app=inner)
            _status, init_headers, _body = await _drive_middleware(
                mw,
                method="POST",
                headers=[
                    (b"x-api-key", raw_key.encode()),
                    (b"content-type", b"application/json"),
                ],
                body=_jsonrpc_body(
                    "initialize",
                    params={"protocolVersion": "2025-06-18", "capabilities": {}},
                ),
            )
            session_id = init_headers.get("mcp-session-id")
            assert session_id, "initialize must mint a session id for this test to be meaningful"

            # Step 2: revoke (deactivate) the key + bust the verdict cache.
            async with db_manager.get_session_async() as session:
                with tenant_isolation_bypass(session, reason="test revoke", models=(APIKey,)):
                    await session.execute(
                        update(APIKey).where(APIKey.id == key_id).values(is_active=False, revoked_at=datetime.now(UTC))
                    )
                    await session.commit()
            bust_api_key_cache(key_id)

            # Step 3: reuse the still-valid session id with the now-revoked key.
            inner2 = _CapturingInnerApp()
            mw2 = MCPAuthMiddleware(app=inner2)
            status, _headers, _body = await _drive_middleware(
                mw2,
                method="POST",
                headers=[
                    (b"x-api-key", raw_key.encode()),
                    (b"mcp-protocol-version", b"2025-06-18"),
                    (b"mcp-session-id", session_id.encode("ascii")),
                    (b"content-type", b"application/json"),
                ],
                body=_jsonrpc_body("tools/list"),
            )

            assert status == 401, (
                f"revoked key + valid session id must be 401 (session id is NOT a bearer credential), got {status}"
            )
            assert inner2.called is False, "a revoked key must never reach the inner SDK app"
        finally:
            state.db_manager = prior_db


# ---------------------------------------------------------------------------
# 5) bcrypt off-loop + cached: ≤1 sync verify per key per TTL window + lag probe
# ---------------------------------------------------------------------------


class TestBcryptOffLoopAndCached:
    """A 100-request burst must trigger ≤1 bcrypt verify and keep the loop responsive."""

    @pytest.mark.asyncio
    async def test_one_bcrypt_per_ttl_window_under_burst(self, db_manager, jwt_env, monkeypatch):
        from api.endpoints import mcp_session as mcp_session_mod
        from giljo_mcp import api_key_utils
        from giljo_mcp.api_key_utils import bust_api_key_cache, verify_api_key

        raw_key, _tenant_key, key_id = await _seed_api_key(db_manager)
        # Start from a clean verdict cache for this key.
        bust_api_key_cache(key_id)

        call_count = {"n": 0}
        real_verify = verify_api_key

        def _counting_verify(api_key: str, key_hash: str) -> bool:
            call_count["n"] += 1
            return real_verify(api_key, key_hash)

        # Patch the sync verify at its definition module. verify_api_key_cached
        # resolves ``verify_api_key`` as a module global inside the to_thread
        # call, so patching here counts exactly the bcrypt comparisons.
        monkeypatch.setattr(api_key_utils, "verify_api_key", _counting_verify)

        async def _one_auth() -> None:
            async with db_manager.get_session_async() as db:
                mgr = mcp_session_mod.MCPSessionManager(db)
                result = await mgr.authenticate_api_key(raw_key)
                assert result is not None, "valid key must authenticate"

        # Warm the cache once. The candidate set is narrowed by key_prefix, so
        # other keys committed by sibling tests that share the gk_be6060a_
        # prefix also get verified-and-cached here — that's the realistic
        # multi-key-per-prefix production case. The invariant under test is
        # "≤1 bcrypt per key per TTL window", i.e. the burst adds ZERO further
        # bcrypt calls, not that the warm cost is globally 1.
        await _one_auth()
        warm_count = call_count["n"]
        assert warm_count >= 1, "first auth must run a real bcrypt verify"

        # Event-loop-lag probe: sample loop scheduling latency while the burst
        # runs. If bcrypt ran ON the loop, a single ~250-400ms checkpw would
        # spike a sample far above this threshold.
        max_lag = {"value": 0.0}
        stop = {"flag": False}

        async def _lag_probe() -> None:
            while not stop["flag"]:
                t0 = time.perf_counter()
                await asyncio.sleep(0)
                lag = time.perf_counter() - t0
                max_lag["value"] = max(max_lag["value"], lag)
                await asyncio.sleep(0.001)

        probe = asyncio.create_task(_lag_probe())
        try:
            for _ in range(100):
                await _one_auth()
        finally:
            stop["flag"] = True
            await probe

        assert call_count["n"] == warm_count, (
            "a 100-request burst added "
            f"{call_count['n'] - warm_count} bcrypt verifies on top of the warm cache — "
            "the verdict cache must absorb every repeat (≤1 bcrypt per key per TTL window)"
        )
        # 150ms ceiling: comfortably below a single bcrypt cost (~250-400ms),
        # proving the verify ran via asyncio.to_thread rather than blocking.
        assert max_lag["value"] < 0.15, (
            f"event-loop lag {max_lag['value'] * 1000:.0f}ms is too high — bcrypt likely ran ON the loop"
        )

    @pytest.mark.asyncio
    async def test_bust_forces_fresh_bcrypt(self, db_manager, jwt_env, monkeypatch):
        """After ``bust_api_key_cache`` the next auth must re-run the sync verify."""
        from api.endpoints import mcp_session as mcp_session_mod
        from giljo_mcp import api_key_utils
        from giljo_mcp.api_key_utils import bust_api_key_cache, verify_api_key

        raw_key, _tenant_key, key_id = await _seed_api_key(db_manager)
        bust_api_key_cache(key_id)

        call_count = {"n": 0}
        real_verify = verify_api_key

        def _counting_verify(api_key: str, key_hash: str) -> bool:
            call_count["n"] += 1
            return real_verify(api_key, key_hash)

        monkeypatch.setattr(api_key_utils, "verify_api_key", _counting_verify)
        monkeypatch.setattr(mcp_session_mod, "verify_api_key", _counting_verify, raising=False)

        async def _one_auth() -> None:
            async with db_manager.get_session_async() as db:
                mgr = mcp_session_mod.MCPSessionManager(db)
                await mgr.authenticate_api_key(raw_key)

        await _one_auth()
        assert call_count["n"] == 1, "first auth must run a real bcrypt verify"

        await _one_auth()
        assert call_count["n"] == 1, "second auth (cache hit) must NOT re-run bcrypt"

        bust_api_key_cache(key_id)
        await _one_auth()
        assert call_count["n"] == 2, "after a cache bust the next auth MUST re-run bcrypt"


# ---------------------------------------------------------------------------
# 6) BE-6061: REST dashboard X-API-Key auth (auth/dependencies.get_current_user)
#    inherits the same off-loop + cache-bust verify the /mcp transport uses.
#
# Failing layer = giljo_mcp.auth.dependencies.get_current_user (the FastAPI
# dependency every dashboard endpoint injects via get_current_active_user).
# Before BE-6061 this path called the SYNC verify_api_key (bcrypt) directly on
# the event loop on every request. These cases drive the REAL dependency.
# ---------------------------------------------------------------------------


class _StubRequest:
    """Minimal Request stand-in for get_current_user (reads .url.path + .client).

    TSK-9021: a failed X-API-Key auth now also runs the shared per-IP
    auth-failure throttle (``enforce_api_key_auth_failure``), which reads
    ``base_url`` off the request-like object. ``base_url`` starts with
    ``http://test`` so the limiter's existing test-bypass exempts this suite
    (it is testing bcrypt/cache behavior, not the throttle -- that has its
    own dedicated coverage in ``test_sec3004c_transport_parity.py``).
    """

    def __init__(self, path: str = "/api/me") -> None:
        self.url = type("_U", (), {"path": path})()
        self.client = None
        self.base_url = "http://test/api/me"


class TestDashboardApiKeyOffLoopAndCached:
    """get_current_user (dashboard X-API-Key) must verify off-loop + cache the verdict."""

    @pytest.mark.asyncio
    async def test_dashboard_one_bcrypt_per_ttl_window_under_burst(self, db_manager, jwt_env, monkeypatch):
        from giljo_mcp import api_key_utils
        from giljo_mcp.api_key_utils import bust_api_key_cache, verify_api_key
        from giljo_mcp.auth import dependencies as deps_mod

        raw_key, _tenant_key, key_id = await _seed_api_key(db_manager)
        bust_api_key_cache(key_id)

        call_count = {"n": 0}
        real_verify = verify_api_key

        def _counting_verify(api_key: str, key_hash: str) -> bool:
            call_count["n"] += 1
            return real_verify(api_key, key_hash)

        # Patch the sync bcrypt at its definition module — verify_api_key_cached
        # resolves it as a module global inside asyncio.to_thread, so this counts
        # exactly the bcrypt comparisons the dashboard path triggers.
        monkeypatch.setattr(api_key_utils, "verify_api_key", _counting_verify)

        async def _one_auth() -> None:
            async with db_manager.get_session_async() as db:
                user = await deps_mod.get_current_user(
                    request=_StubRequest(),
                    access_token=None,
                    x_api_key=raw_key,
                    authorization=None,
                    db=db,
                )
                assert user is not None, "valid dashboard key must authenticate"

        await _one_auth()
        warm_count = call_count["n"]
        assert warm_count >= 1, "first dashboard auth must run a real bcrypt verify"

        max_lag = {"value": 0.0}
        stop = {"flag": False}

        async def _lag_probe() -> None:
            while not stop["flag"]:
                t0 = time.perf_counter()
                await asyncio.sleep(0)
                max_lag["value"] = max(max_lag["value"], time.perf_counter() - t0)
                await asyncio.sleep(0.001)

        probe = asyncio.create_task(_lag_probe())
        try:
            for _ in range(100):
                await _one_auth()
        finally:
            stop["flag"] = True
            await probe

        assert call_count["n"] == warm_count, (
            "a 100-request dashboard burst added "
            f"{call_count['n'] - warm_count} bcrypt verifies on top of the warm cache — "
            "the shared verdict cache must absorb every repeat (≤1 bcrypt per key per TTL)"
        )
        assert max_lag["value"] < 0.15, (
            f"event-loop lag {max_lag['value'] * 1000:.0f}ms is too high — "
            "the dashboard X-API-Key bcrypt likely ran ON the loop (not via asyncio.to_thread)"
        )


class TestDashboardRevokedKeyBust:
    """A revoked dashboard key must 401 immediately once the shared cache is busted."""

    @pytest.mark.asyncio
    async def test_dashboard_revoked_key_is_401_after_bust(self, db_manager, jwt_env):
        from sqlalchemy import update

        from giljo_mcp.api_key_utils import bust_api_key_cache
        from giljo_mcp.auth import dependencies as deps_mod
        from giljo_mcp.database import tenant_isolation_bypass
        from giljo_mcp.models.auth import APIKey

        raw_key, _tenant_key, key_id = await _seed_api_key(db_manager)
        bust_api_key_cache(key_id)

        # Step 1: valid key authenticates and seeds a positive verdict in the cache.
        async with db_manager.get_session_async() as db:
            user = await deps_mod.get_current_user(
                request=_StubRequest(),
                access_token=None,
                x_api_key=raw_key,
                authorization=None,
                db=db,
            )
            assert user is not None, "pre-revoke dashboard auth must succeed"

        # Step 2: deactivate the key + bust the shared verdict cache (the exact two
        # operations AuthService._revoke_api_key_impl performs).
        async with db_manager.get_session_async() as db:
            with tenant_isolation_bypass(db, reason="test revoke", models=(APIKey,)):
                await db.execute(
                    update(APIKey).where(APIKey.id == key_id).values(is_active=False, revoked_at=datetime.now(UTC))
                )
                await db.commit()
        bust_api_key_cache(key_id)

        # Step 3: the revoked key must now be rejected — no stale positive survives.
        with pytest.raises(HTTPException) as exc_info:
            async with db_manager.get_session_async() as db:
                await deps_mod.get_current_user(
                    request=_StubRequest(),
                    access_token=None,
                    x_api_key=raw_key,
                    authorization=None,
                    db=db,
                )
        assert exc_info.value.status_code == 401, (
            "a revoked dashboard key must 401 once bust_api_key_cache fires — "
            "the cache-bust must reach this path, not only /mcp"
        )
