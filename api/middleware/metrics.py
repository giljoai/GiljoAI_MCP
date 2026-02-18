"""
API Metrics Middleware

Tracks API and MCP call counts per tenant.

This is the existing APIMetricsMiddleware from api/middleware.py,
moved to the new middleware directory structure in Handover 0129c.
"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class APIMetricsMiddleware(BaseHTTPMiddleware):
    """API metrics middleware - counts total API and MCP calls."""

    async def dispatch(self, request: Request, call_next):
        """Increment API and MCP call counters."""
        tenant_key = getattr(request.state, "tenant_key", None)
        if tenant_key:
            request.app.state.api_state.api_call_count[tenant_key] = (
                request.app.state.api_state.api_call_count.get(tenant_key, 0) + 1
            )
            if request.url.path.startswith("/mcp"):
                request.app.state.api_state.mcp_call_count[tenant_key] = (
                    request.app.state.api_state.mcp_call_count.get(tenant_key, 0) + 1
                )
        response = await call_next(request)
        return response
