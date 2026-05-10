# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""API-0021d Phase 3 — CORS preflight tests for the MCP /mcp handshake.

Failing-layer regression tests for the analyzer's F4 (claude.ai + claude.com
origin allowlist) and F5 (MCP-Protocol-Version + Mcp-Session-Id allow_headers)
findings. Both fixes live in ``api/app.py`` where ``CORSMiddleware`` is wired:
the values added there guarantee the browser preflight from the claude.com
connector backend reaches the auth middleware instead of being rejected at
the preflight boundary.

These tests drive the full ASGI stack via ``api_client`` so they exercise
the same middleware chain that production uses — exactly the layer the
analyzer's curl probe failed at.
"""

from __future__ import annotations

import pytest


class TestCorsClaudeConnectorOrigins:
    """F4: https://claude.ai AND https://claude.com must echo on preflight.

    The values are appended in code as a defensive fallback (api/app.py)
    even when the env-sourced config.yaml allowlist omits them — so this
    test passes regardless of the test harness's CORS configuration.
    """

    @pytest.mark.parametrize("origin", ["https://claude.ai", "https://claude.com"])
    @pytest.mark.asyncio
    async def test_preflight_allows_anthropic_connector_origin(self, api_client, origin):
        response = await api_client.options(
            "/mcp",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )
        # CORS middleware returns 200 on accepted preflight; if the origin
        # were rejected we'd get 400 or no allow-origin header echoed.
        assert response.status_code == 200, (
            f"Preflight for {origin} returned {response.status_code}; body: {response.text}"
        )
        echoed = response.headers.get("access-control-allow-origin", "")
        assert echoed == origin, f"Expected access-control-allow-origin: {origin}, got: {echoed!r}"


class TestCorsMcpProtocolHeaders:
    """F5: MCP Streamable HTTP spec headers must pass preflight.

    Spec: ``MCP-Protocol-Version`` (required by 2025-06-18) and
    ``Mcp-Session-Id`` (returned in initialize response and echoed back on
    subsequent requests). The browser's preflight asks the server to
    confirm these headers are allowed — without them in
    ``allow_headers`` the preflight returns 400 and the spec request
    never runs.
    """

    @pytest.mark.asyncio
    async def test_preflight_allows_mcp_protocol_version_header(self, api_client):
        response = await api_client.options(
            "/mcp",
            headers={
                "Origin": "https://claude.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "mcp-protocol-version,authorization,content-type",
            },
        )
        assert response.status_code == 200, response.text
        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "mcp-protocol-version" in allowed_headers, (
            f"MCP-Protocol-Version not in allow_headers: {allowed_headers!r}"
        )

    @pytest.mark.asyncio
    async def test_preflight_allows_mcp_session_id_header(self, api_client):
        response = await api_client.options(
            "/mcp",
            headers={
                "Origin": "https://claude.com",
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "mcp-session-id,authorization,content-type",
            },
        )
        assert response.status_code == 200, response.text
        allowed_headers = response.headers.get("access-control-allow-headers", "").lower()
        assert "mcp-session-id" in allowed_headers, f"Mcp-Session-Id not in allow_headers: {allowed_headers!r}"
