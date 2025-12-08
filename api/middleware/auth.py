"""
Authentication Middleware

Handles authentication for all API requests.

This is the existing AuthMiddleware from api/middleware.py,
moved to the new middleware directory structure in Handover 0129c.
"""

import logging
import os
from typing import Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Authentication middleware - ALWAYS ACTIVE (unified auth).

    All clients (localhost and network) require JWT or API key.
    No special treatment for localhost - ensures production parity.

    This middleware provides consistent authentication regardless
    of client location (localhost or network).
    """

    def __init__(self, app, auth_manager: Optional[Callable] = None):
        """
        Initialize authentication middleware.

        Args:
            app: FastAPI application
            auth_manager: Optional callable that returns AuthManager instance
                         (e.g., lambda: state.auth)
        """
        super().__init__(app)
        # Store callable that returns auth manager
        self.get_auth_manager = auth_manager
        self._auth_manager = None

    async def dispatch(self, request: Request, call_next):
        """Process all requests through authentication"""
        # Public endpoints bypass auth as early as possible
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # Get auth manager (from callable or fallback to app state)
        if self.get_auth_manager:
            auth_manager = self.get_auth_manager()
        else:
            # Fallback: get from app state
            auth_manager = getattr(request.app.state, "auth", None)
            if not auth_manager:
                logger.error("AuthManager not configured in middleware or app state")
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Authentication system error",
                        "detail": "AuthManager not configured",
                    },
                )

        # DIAGNOSTIC: Log incoming request details
        logger.info(
            f"[AuthMiddleware] {request.method} {request.url.path} - IP: {request.client.host if request.client else 'unknown'}"
        )
        logger.info(f"[AuthMiddleware] Cookie header present: {bool(request.headers.get('cookie'))}")
        logger.info(f"[AuthMiddleware] Authorization header present: {bool(request.headers.get('authorization'))}")

        # Authenticate (auto-login or credentials)
        auth_result = await auth_manager.authenticate_request(request)

        # DIAGNOSTIC: Log auth result
        logger.info(
            f"[AuthMiddleware] Auth result: authenticated={auth_result.get('authenticated')}, user={auth_result.get('user')}, error={auth_result.get('error')}"
        )

        # Set request state consistently
        request.state.authenticated = auth_result.get("authenticated", False)

        if auth_result.get("authenticated"):
            # Always set both user_id (string) and user (object if available)
            request.state.user_id = auth_result.get("user_id") or auth_result.get("user")
            request.state.user = auth_result.get("user_obj")  # User object or None
            request.state.is_auto_login = auth_result.get("is_auto_login", False)
            request.state.tenant_key = auth_result.get(
                "tenant_key", os.getenv("DEFAULT_TENANT_KEY", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd")
            )
        else:
            # Auth failed - return 401
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "detail": auth_result.get("error", "No credentials provided"),
                },
            )

        return await call_next(request)

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no authentication required)"""
        PUBLIC_PATHS = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/auth/login",  # Login endpoint
            "/api/auth/create-first-admin",  # First admin creation (Handover 0034)
            "/api/setup/status",  # Fresh install detection (Handover 0034)
            "/api/v1/config/frontend",  # Frontend config
            "/api/auth/me",  # Auth status check
            "/mcp",  # MCP-over-HTTP endpoint (handles own auth via X-API-Key)
            "/api/v1/ws-bridge",  # Internal MCP-to-WebSocket bridge (localhost-only, no auth required)
            "/api/download/slash-commands.zip",  # Public slash command downloads
            "/api/download/install-script",  # Public install scripts
            "/api/download/agent-templates.zip",  # Optional-auth downloads (handles own auth logic)
            "/api/download/temp",  # Public download with token auth (one-time tokens)
        ]
        # Always allow token download path (token is the auth)
        if path.startswith("/api/download/temp") or "/api/download/temp/" in path:
            return True
        return any(path.startswith(p) for p in PUBLIC_PATHS)
