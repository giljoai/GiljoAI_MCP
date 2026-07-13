# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
API Metrics Middleware

Tracks API and MCP call counts per tenant.

This is the existing APIMetricsMiddleware from api/middleware.py,
moved to the new middleware directory structure in Handover 0129c.
"""

import logging

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send


logger = logging.getLogger(__name__)


class APIMetricsMiddleware:
    """API metrics middleware - counts total API and MCP calls.

    Pure-ASGI (BE-6063c): no BaseHTTPMiddleware task-group/stream tax. Counting
    happens at request entry (the counter increment is a pre-call side effect in
    the original dispatch — it ran before ``call_next`` returned), so behavior is
    identical: every non-static request with a resolved ``tenant_key`` bumps the
    per-tenant counter exactly once.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        path = request.url.path
        if not (path == "/" or path.startswith("/assets/") or path == "/favicon.ico"):
            tenant_key = scope.get("state", {}).get("tenant_key")
            if tenant_key:
                request.app.state.api_state.api_call_count[tenant_key] = (
                    request.app.state.api_state.api_call_count.get(tenant_key, 0) + 1
                )
                # MCP tool calls are counted per-invocation in _call_tool()
                # (mcp_sdk_server.py), not per HTTP request here.

        await self.app(scope, receive, send)
