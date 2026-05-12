# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression tests for API-0021j Phase 1 — MCP-Protocol-Version header validation.

Per the MCP Streamable HTTP spec (2025-06-18+), every non-initialize request
SHOULD/MUST advertise its negotiated protocol version via the
``MCP-Protocol-Version`` HTTP header. Servers that receive an unsupported
version MUST reject the request with HTTP 400 — NOT 401 — so the validator
runs BEFORE the auth path inside :class:`MCPAuthMiddleware`. Initialize
requests are exempt because version negotiation lives in JSON-RPC params,
not the header.

Failing-layer discipline (per CLAUDE.md): tests drive the ASGI middleware
directly — the same boundary an unsupported-version client would hit in
production. The handler-level mcp.server.streamable_http validator does not
fire here because FastMCP runs ``stateless_http=True`` and the middleware
must reject before the SDK is invoked.

Test categories:
- TestUnsupportedVersionReturns400: non-initialize + unsupported header → 400
- TestInitializeIsExempt: method=='initialize' with no header → not rejected
- TestEachSupportedVersionAccepted: each version in the canonical SUPPORTED
  list passes the header validator (auth result is orthogonal).
- TestMissingHeaderOnNonInitialize: per spec SHOULD-default to 2025-03-26 —
  not 400 on header grounds when header absent.
"""

from __future__ import annotations

import json

import pytest

from api.endpoints.oauth import MCP_SPEC_VERSIONS_SUPPORTED


class _CapturingInnerApp:
    """Minimal ASGI app that records whether the middleware reached it."""

    def __init__(self) -> None:
        self.called: bool = False

    async def __call__(self, scope, receive, send) -> None:
        self.called = True
        # Drain the receive stream so wrapped-receive logic is exercised end-to-end.
        await receive()
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"OK"})


async def _drive_middleware_with_body(
    middleware,
    headers: list[tuple[bytes, bytes]],
    body: bytes,
) -> tuple[int, dict[str, str], bytes]:
    """Run a single ASGI request through ``middleware`` with the given JSON body."""
    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "method": "POST",
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
    """Build a minimal JSON-RPC 2.0 request body."""
    payload: dict = {"jsonrpc": "2.0", "id": 1, "method": method}
    if params is not None:
        payload["params"] = params
    return json.dumps(payload).encode("utf-8")


class TestUnsupportedVersionReturns400:
    """Non-initialize POST with an unsupported MCP-Protocol-Version returns 400."""

    @pytest.mark.asyncio
    async def test_deprecated_2024_11_05_rejected_with_400(self):
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        status, headers, body = await _drive_middleware_with_body(
            mw,
            headers=[
                (b"mcp-protocol-version", b"2024-11-05"),
                (b"content-type", b"application/json"),
            ],
            body=_jsonrpc_body("tools/list"),
        )

        assert status == 400, f"unsupported version returned {status}"
        assert inner.called is False, "validator must short-circuit before auth + inner app"
        assert headers.get("content-type", "").startswith("application/json")
        payload = json.loads(body)
        assert "error" in payload
        # The 400 body must enumerate the supported versions so the client can recover.
        for declared in MCP_SPEC_VERSIONS_SUPPORTED:
            assert declared in body.decode("utf-8"), f"supported version {declared} missing from 400 body: {body!r}"

    @pytest.mark.asyncio
    async def test_400_precedes_auth(self):
        """Validator runs BEFORE bearer extraction — even authless requests get 400."""
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        status, _headers, _body = await _drive_middleware_with_body(
            mw,
            headers=[(b"mcp-protocol-version", b"1999-01-01")],
            body=_jsonrpc_body("tools/list"),
        )

        # 400 (bad header) MUST win over 401 (no creds).
        assert status == 400, f"expected 400 (bad header before auth), got {status}"


class TestInitializeIsExempt:
    """``method=='initialize'`` requests are not rejected on header grounds."""

    @pytest.mark.asyncio
    async def test_initialize_without_header_is_not_400(self):
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        status, _headers, _body = await _drive_middleware_with_body(
            mw,
            headers=[(b"content-type", b"application/json")],
            body=_jsonrpc_body(
                "initialize",
                params={"protocolVersion": "2025-06-18", "capabilities": {}},
            ),
        )

        # No header on initialize must NOT be 400. Auth still rejects with 401.
        assert status != 400, "initialize must not be rejected on header grounds"
        assert status == 401, f"expected 401 (no auth), got {status}"

    @pytest.mark.asyncio
    async def test_initialize_with_unsupported_header_is_not_400(self):
        """Negotiation lives in JSON-RPC params on initialize — header is informational only."""
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        status, _headers, _body = await _drive_middleware_with_body(
            mw,
            headers=[
                (b"mcp-protocol-version", b"2024-11-05"),
                (b"content-type", b"application/json"),
            ],
            body=_jsonrpc_body(
                "initialize",
                params={"protocolVersion": "2025-06-18", "capabilities": {}},
            ),
        )

        assert status != 400, "initialize requests MUST bypass header version check (negotiation is in params)"


class TestEachSupportedVersionAccepted:
    """Every declared spec version passes the transport-layer header validator."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("version", MCP_SPEC_VERSIONS_SUPPORTED)
    async def test_supported_version_not_rejected_on_header(self, version):
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        status, _headers, _body = await _drive_middleware_with_body(
            mw,
            headers=[
                (b"mcp-protocol-version", version.encode("ascii")),
                (b"content-type", b"application/json"),
            ],
            body=_jsonrpc_body("tools/list"),
        )

        # Auth result is orthogonal — assert no 400 on header grounds.
        assert status != 400, f"declared-supported version {version} was rejected at the header validator"


class TestMissingHeaderOnNonInitialize:
    """Non-initialize requests with no MCP-Protocol-Version SHOULD default — not 400."""

    @pytest.mark.asyncio
    async def test_missing_header_defaults_silently(self):
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        inner = _CapturingInnerApp()
        mw = MCPAuthMiddleware(app=inner)

        status, _headers, _body = await _drive_middleware_with_body(
            mw,
            headers=[(b"content-type", b"application/json")],
            body=_jsonrpc_body("tools/list"),
        )

        assert status != 400, "spec SHOULD-default to 2025-03-26 on missing header — must not 400"
