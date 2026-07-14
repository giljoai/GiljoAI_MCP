# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Tests for the top-level /mcp ASGI dispatcher (BE-6060c).

The dispatcher (``api/mcp_dispatcher.py``) replaces the response-buffering bridge
route deleted from ``api/wiring/routers.py``. It sits ABOVE the FastAPI middleware
onion and routes ``/mcp`` HTTP traffic straight to the MCP ASGI app, unbuffered,
while everything else (REST, OAuth ``/.well-known`` + ``/api/oauth``, websockets,
the lifespan scope) flows to the FastAPI app unchanged.

Coverage maps to the work-order items:
- Routing matrix incl. the PRECISE ``/mcp`` match (``/mcpfoo`` must NOT be captured)
  and OAuth/well-known staying on FastAPI (items #1, #2).
- Conformance re-asserted THROUGH the dispatcher path against the REAL MCP app:
  401 + ``WWW-Authenticate`` resource_metadata (RFC 9728), 400-before-401, no 3xx
  on ``/mcp`` or ``/mcp/`` (item #3).
- Explicit middleware-policy test: ``/mcp`` routes AROUND the FastAPI onion (item #5).
- Streaming pass-through: the dispatcher hands ``(scope, receive, send)`` straight
  through — same objects, multi-frame, unbuffered — under an SSE Accept header (item #6).
- Boot smoke: the dispatcher forwards the lifespan scope so the wrapped app boots
  (the real export wraps the FastAPI app whose lifespan starts the shared MCP session
  manager); decoupled from the SDK's run-once session-manager singleton.

xdist-safe: no DB, no module-level mutable state, ``monkeypatch.setenv`` for env.
"""

from __future__ import annotations

import json

import pytest

from api.mcp_dispatcher import McpDispatcher


# ---------------------------------------------------------------------------
# Spy ASGI apps + drive harness
# ---------------------------------------------------------------------------


class _SpyApp:
    """Records whether it was invoked and the exact (scope, receive, send) it saw."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.called = False
        self.seen_scope = None
        self.seen_receive = None
        self.seen_send = None
        # http body frames to emit; default a single frame. Set to a list to
        # exercise multi-frame unbuffered streaming.
        self.emit_frames: list[bytes] | None = None

    async def __call__(self, scope, receive, send) -> None:
        self.called = True
        self.seen_scope = scope
        self.seen_receive = receive
        self.seen_send = send
        kind = scope["type"]
        if kind == "http":
            frames = self.emit_frames if self.emit_frames is not None else [b"OK"]
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"x-app", self.name.encode())],
                }
            )
            for i, frame in enumerate(frames):
                await send(
                    {
                        "type": "http.response.body",
                        "body": frame,
                        "more_body": i < len(frames) - 1,
                    }
                )
        elif kind == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return
        elif kind == "websocket":
            await receive()  # websocket.connect
            await send({"type": "websocket.close"})


def _http_scope(path: str, *, method: str = "POST", headers: list[tuple[bytes, bytes]] | None = None) -> dict:
    return {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": headers or [],
        "client": ("127.0.0.1", 12345),
        "server": ("test", 80),
        "scheme": "http",
        "root_path": "",
    }


async def _drive_http(app, scope: dict, *, body: bytes = b""):
    """Drive one HTTP request; return (captured, receive, send)."""
    captured: dict = {"status": 0, "headers": {}, "frames": []}
    body_sent = {"done": False}

    async def receive() -> dict:
        if body_sent["done"]:
            return {"type": "http.disconnect"}
        body_sent["done"] = True
        return {"type": "http.request", "body": body, "more_body": False}

    async def send(message) -> None:
        if message["type"] == "http.response.start":
            captured["status"] = message["status"]
            for k, v in message.get("headers", []):
                key = k.decode("latin-1") if isinstance(k, bytes) else k
                val = v.decode("latin-1") if isinstance(v, bytes) else v
                captured["headers"][key.lower()] = val
        elif message["type"] == "http.response.body":
            captured["frames"].append(message.get("body", b""))

    await app(scope, receive, send)
    return captured, receive, send


async def _drive_lifespan(app) -> list[str]:
    sent: list[str] = []
    queue = [{"type": "lifespan.startup"}, {"type": "lifespan.shutdown"}]
    idx = {"i": 0}

    async def receive() -> dict:
        message = queue[idx["i"]]
        idx["i"] += 1
        return message

    async def send(message) -> None:
        sent.append(message["type"])

    await app({"type": "lifespan", "asgi": {"version": "3.0"}}, receive, send)
    return sent


async def _drive_websocket(app) -> list[str]:
    sent: list[str] = []
    queue = [{"type": "websocket.connect"}]
    idx = {"i": 0}

    async def receive() -> dict:
        if idx["i"] < len(queue):
            message = queue[idx["i"]]
            idx["i"] += 1
            return message
        return {"type": "websocket.disconnect", "code": 1000}

    async def send(message) -> None:
        sent.append(message["type"])

    await app({"type": "websocket", "path": "/ws/x", "headers": []}, receive, send)
    return sent


def _jsonrpc_body(method: str, params: dict | None = None) -> bytes:
    payload: dict = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    return json.dumps(payload).encode("utf-8")


@pytest.fixture
def dispatcher_with_spies():
    fastapi_spy = _SpyApp("fastapi")
    mcp_spy = _SpyApp("mcp")
    return McpDispatcher(fastapi_spy, mcp_spy), fastapi_spy, mcp_spy


# ---------------------------------------------------------------------------
# 1) Routing matrix — precise /mcp match; everything else to FastAPI
# ---------------------------------------------------------------------------


class TestHttpRouting:
    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("path", "to_mcp"),
        [
            ("/mcp", True),
            ("/mcp/", True),
            ("/mcp/messages", True),
            ("/mcp/anything/deep", True),
            # PRECISE match: a bare startswith("/mcp") would wrongly catch these.
            ("/mcpfoo", False),
            ("/mcp-installer/windows", False),
            ("/api/mcp-installer/windows", False),
            # REST + OAuth surface stays on FastAPI (recon: no /mcp-prefixed OAuth path).
            ("/api/health", False),
            ("/", False),
            ("/.well-known/oauth-protected-resource", False),
            ("/.well-known/oauth-authorization-server", False),
            ("/api/oauth/token", False),
        ],
    )
    async def test_http_path_routes_correctly(self, dispatcher_with_spies, path, to_mcp):
        dispatcher, fastapi_spy, mcp_spy = dispatcher_with_spies

        captured, _r, _s = await _drive_http(dispatcher, _http_scope(path))

        if to_mcp:
            assert mcp_spy.called is True, f"{path} must route to the MCP app"
            assert fastapi_spy.called is False, f"{path} must NOT touch the FastAPI app"
            assert captured["headers"].get("x-app") == "mcp"
        else:
            assert fastapi_spy.called is True, f"{path} must route to the FastAPI app"
            assert mcp_spy.called is False, f"{path} must NOT touch the MCP app"
            assert captured["headers"].get("x-app") == "fastapi"

    @pytest.mark.asyncio
    async def test_lifespan_routes_to_fastapi(self, dispatcher_with_spies):
        """The FastAPI lifespan owns startup AND the MCP session-manager run-context."""
        dispatcher, fastapi_spy, mcp_spy = dispatcher_with_spies

        sent = await _drive_lifespan(dispatcher)

        assert fastapi_spy.called is True, "lifespan MUST reach the FastAPI app (it starts the app)"
        assert mcp_spy.called is False, "lifespan must NOT be forwarded to the MCP app"
        assert sent == ["lifespan.startup.complete", "lifespan.shutdown.complete"]

    @pytest.mark.asyncio
    async def test_websocket_routes_to_fastapi(self, dispatcher_with_spies):
        dispatcher, fastapi_spy, mcp_spy = dispatcher_with_spies

        await _drive_websocket(dispatcher)

        assert fastapi_spy.called is True, "websocket scopes belong to FastAPI (no WS under /mcp)"
        assert mcp_spy.called is False


# ---------------------------------------------------------------------------
# 5) Explicit middleware policy — /mcp routes AROUND the FastAPI onion
# ---------------------------------------------------------------------------


class TestMiddlewarePolicy:
    """A /mcp request must NOT execute the FastAPI middleware onion; a non-/mcp must."""

    @pytest.mark.asyncio
    async def test_mcp_bypasses_fastapi_onion(self, dispatcher_with_spies):
        dispatcher, fastapi_onion_marker, mcp_marker = dispatcher_with_spies

        await _drive_http(dispatcher, _http_scope("/mcp"), body=_jsonrpc_body("tools/list"))

        assert mcp_marker.called is True, "/mcp must reach the MCP app"
        assert fastapi_onion_marker.called is False, (
            "/mcp executed the FastAPI app (and therefore its Auth/CSRF/RateLimit/SaaS onion) — "
            "the dispatcher must route /mcp AROUND the middleware stack"
        )

    @pytest.mark.asyncio
    async def test_non_mcp_executes_fastapi_onion(self, dispatcher_with_spies):
        dispatcher, fastapi_onion_marker, mcp_marker = dispatcher_with_spies

        await _drive_http(dispatcher, _http_scope("/api/v1/projects", method="GET"))

        assert fastapi_onion_marker.called is True, "a non-/mcp request MUST run the FastAPI onion"
        assert mcp_marker.called is False

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ["/mcp", "/mcp/", "/mcp/messages"])
    async def test_options_mcp_preflight_routes_to_fastapi_for_cors(self, dispatcher_with_spies, path):
        """A CORS preflight (OPTIONS /mcp) MUST go to FastAPI so CORSMiddleware can answer it.

        Regression for the BE-6060c break: routing OPTIONS to the MCP app made the browser
        claude.ai/claude.com connector preflight hit the MCP transport's credential-less-401
        path (no preflight exemption) instead of CORS, returning 401 and breaking the
        handshake (tests/api/test_cors_mcp_handshake.py). OPTIONS carries no MCP payload and
        never streams, so this carve-out does not undermine the unbuffered /mcp split."""
        dispatcher, fastapi_spy, mcp_spy = dispatcher_with_spies

        captured, _r, _s = await _drive_http(dispatcher, _http_scope(path, method="OPTIONS"))

        assert fastapi_spy.called is True, f"OPTIONS {path} (CORS preflight) MUST reach FastAPI/CORS"
        assert mcp_spy.called is False, (
            f"OPTIONS {path} must NOT hit the MCP app — its auth has no preflight exemption and would 401"
        )
        assert captured["headers"].get("x-app") == "fastapi"

    @pytest.mark.asyncio
    @pytest.mark.parametrize("method", ["GET", "POST", "DELETE"])
    async def test_non_options_mcp_methods_still_reach_mcp_app(self, dispatcher_with_spies, method):
        """The OPTIONS carve-out must NOT leak to real MCP traffic: GET/POST/DELETE /mcp
        still route straight to the unbuffered MCP app, around the onion."""
        dispatcher, fastapi_spy, mcp_spy = dispatcher_with_spies

        await _drive_http(dispatcher, _http_scope("/mcp", method=method), body=_jsonrpc_body("tools/list"))

        assert mcp_spy.called is True, f"{method} /mcp must reach the MCP app"
        assert fastapi_spy.called is False, f"{method} /mcp must NOT touch the FastAPI onion"


# ---------------------------------------------------------------------------
# 6) Streaming pass-through — same objects, multi-frame, unbuffered
# ---------------------------------------------------------------------------


class TestUnbufferedPassThrough:
    @pytest.mark.asyncio
    async def test_scope_receive_send_passed_through_identically(self, dispatcher_with_spies):
        """The deleted bridge wrapped `send` to buffer frames; the dispatcher must
        forward the SAME scope/receive/send objects — proof of zero buffering."""
        dispatcher, _fastapi_spy, mcp_spy = dispatcher_with_spies
        scope = _http_scope("/mcp")

        _captured, receive, send = await _drive_http(dispatcher, scope)

        assert mcp_spy.seen_scope is scope, "dispatcher must pass the SAME scope object"
        assert mcp_spy.seen_receive is receive, "dispatcher must pass the SAME receive callable (no wrap)"
        assert mcp_spy.seen_send is send, "dispatcher must pass the SAME send callable (no buffering wrap)"

    @pytest.mark.asyncio
    async def test_sse_multi_frame_streams_unbuffered(self, dispatcher_with_spies):
        """Multiple body frames reach the outer send AS separate frames (not coalesced
        into one Response the way the buffering bridge did) under an SSE Accept header."""
        dispatcher, _fastapi_spy, mcp_spy = dispatcher_with_spies
        mcp_spy.emit_frames = [b"data: one\n\n", b"data: two\n\n", b"data: three\n\n"]

        captured, _r, _s = await _drive_http(
            dispatcher,
            _http_scope("/mcp", headers=[(b"accept", b"text/event-stream")]),
        )

        assert captured["frames"] == [b"data: one\n\n", b"data: two\n\n", b"data: three\n\n"], (
            "streamed frames were coalesced/buffered — the dispatcher must forward each send frame as-is"
        )


# ---------------------------------------------------------------------------
# 3) Conformance re-asserted THROUGH the dispatcher against the REAL MCP app
# ---------------------------------------------------------------------------


@pytest.fixture
def mcp_canonical_uri_env(monkeypatch):
    monkeypatch.setenv("GILJO_MCP_CANONICAL_URI", "http://test/mcp")
    return "http://test/mcp"


@pytest.fixture
def real_dispatcher(mcp_canonical_uri_env):
    """Dispatcher wrapping a FastAPI spy + the REAL MCP ASGI app (auth middleware)."""
    from api.endpoints.mcp_sdk_server import get_mcp_asgi_app

    fastapi_spy = _SpyApp("fastapi")
    return McpDispatcher(fastapi_spy, get_mcp_asgi_app()), fastapi_spy


class TestConformanceThroughDispatcher:
    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
    async def test_unauthed_post_is_401_with_resource_metadata(self, real_dispatcher, path):
        dispatcher, fastapi_spy = real_dispatcher

        captured, _r, _s = await _drive_http(
            dispatcher,
            _http_scope(path, headers=[(b"content-type", b"application/json")]),
            body=_jsonrpc_body("tools/list"),
        )

        assert captured["status"] == 401, f"unauthed POST {path} must be 401, got {captured['status']}"
        assert fastapi_spy.called is False, f"{path} must be served by the MCP app, never FastAPI"
        www_auth = captured["headers"].get("www-authenticate", "")
        assert "resource_metadata=" in www_auth, (
            f"401 on {path} must carry RFC 9728 resource_metadata in WWW-Authenticate: {www_auth!r}"
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ["/mcp", "/mcp/"])
    @pytest.mark.parametrize("method", ["GET", "POST", "DELETE", "OPTIONS"])
    async def test_no_3xx_ever(self, real_dispatcher, path, method):
        dispatcher, _fastapi_spy = real_dispatcher
        body = _jsonrpc_body("tools/list") if method in ("POST", "DELETE") else b""

        captured, _r, _s = await _drive_http(
            dispatcher,
            _http_scope(path, method=method, headers=[(b"content-type", b"application/json")]),
            body=body,
        )

        assert not (300 <= captured["status"] < 400), (
            f"{method} {path} emitted a 3xx ({captured['status']}); the 307 trap must never reappear"
        )

    @pytest.mark.asyncio
    async def test_unsupported_version_is_400_before_401(self, real_dispatcher):
        """Through the dispatcher, an unsupported MCP-Protocol-Version on a non-initialize
        POST still returns 400 (transport) BEFORE auth would return 401."""
        dispatcher, _fastapi_spy = real_dispatcher

        captured, _r, _s = await _drive_http(
            dispatcher,
            _http_scope(
                "/mcp",
                headers=[
                    (b"mcp-protocol-version", b"2024-11-05"),
                    (b"content-type", b"application/json"),
                ],
            ),
            body=_jsonrpc_body("tools/list"),
        )

        assert captured["status"] == 400, (
            f"unsupported version through the dispatcher must be 400 (not 401), got {captured['status']}"
        )

    @pytest.mark.asyncio
    async def test_oauth_well_known_stays_on_fastapi(self, real_dispatcher):
        """The OAuth discovery surface MUST remain on the FastAPI (human) plane."""
        dispatcher, fastapi_spy = real_dispatcher

        captured, _r, _s = await _drive_http(
            dispatcher,
            _http_scope("/.well-known/oauth-protected-resource", method="GET"),
        )

        assert fastapi_spy.called is True, "OAuth well-known must be served by FastAPI, not the MCP app"
        assert captured["headers"].get("x-app") == "fastapi"


# ---------------------------------------------------------------------------
# Boot smoke — module imports + dispatcher forwards lifespan so the app boots
# ---------------------------------------------------------------------------


class TestBootSmoke:
    def test_real_export_is_dispatcher_over_fastapi_and_mcp(self):
        """`import api.app` succeeds and the export wraps the FastAPI app + MCP app.

        Proves get_mcp_asgi_app() is import-safe at module load (it lazily builds the
        session-manager singleton the FastAPI lifespan later runs)."""
        import api.app as app_module

        assert isinstance(app_module.app, McpDispatcher), "api.app.app must be the McpDispatcher export"
        # The wrapped FastAPI app exposes its router/lifespan (the real one starts the
        # MCP session manager); the MCP app is a pure-ASGI callable.
        assert hasattr(app_module.app.fastapi_app, "router"), "wrapped FastAPI app missing .router"
        assert callable(app_module.app.mcp_app), "wrapped MCP app must be an ASGI callable"
        # Backward-compat delegation: attribute access falls through to FastAPI.
        assert app_module.app.router is app_module.app.fastapi_app.router

    def test_lifespan_forwarding_boots_the_wrapped_app(self):
        """A dispatcher-wrapped app boots: TestClient enters/exits the lifespan via the
        dispatcher, and routing works for both planes. This is the generic proof that
        forwarding the lifespan scope starts the wrapped app (the real export's FastAPI
        lifespan is what calls start_mcp_session_manager())."""
        from contextlib import asynccontextmanager

        from fastapi import FastAPI
        from starlette.testclient import TestClient

        flags = {"started": False, "stopped": False}

        @asynccontextmanager
        async def _lifespan(_app):
            flags["started"] = True
            yield
            flags["stopped"] = True

        fastapi_app = FastAPI(lifespan=_lifespan)

        @fastapi_app.get("/api/ping")
        async def _ping():
            return {"pong": True}

        mcp_spy = _SpyApp("mcp")
        dispatcher = McpDispatcher(fastapi_app, mcp_spy)

        with TestClient(dispatcher) as client:
            assert flags["started"] is True, "dispatcher must forward lifespan.startup so the app boots"
            rest = client.get("/api/ping")
            assert rest.status_code == 200 and rest.json() == {"pong": True}
            mcp = client.post("/mcp", content=b"{}")
            assert mcp.status_code == 200
            assert mcp.headers.get("x-app") == "mcp", "/mcp must route to the MCP app through the dispatcher"

        assert flags["stopped"] is True, "dispatcher must forward lifespan.shutdown on exit"
