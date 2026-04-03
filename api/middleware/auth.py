"""
Authentication Middleware

Handles authentication for all API requests.

This is the existing AuthMiddleware from api/middleware.py,
moved to the new middleware directory structure in Handover 0129c.
"""

import time
from typing import Callable, Optional

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from giljo_mcp.logging import ErrorCode, get_logger


logger = get_logger(__name__)


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
                logger.error(
                    "auth_manager_not_configured",
                    error_code=ErrorCode.API_INTERNAL_ERROR.value,
                    path=request.url.path,
                    method=request.method,
                )
                return JSONResponse(
                    status_code=500,
                    content={
                        "error": "Authentication system error",
                        "detail": "AuthManager not configured",
                    },
                )

        # DIAGNOSTIC: Log incoming request details
        logger.info(
            "auth_request_received",
            method=request.method,
            path=request.url.path,
            ip_address=request.client.host if request.client else "unknown",
            has_cookie=bool(request.headers.get("cookie")),
            has_authorization=bool(request.headers.get("authorization")),
        )

        auth_result = await auth_manager.authenticate_request(request)

        # DIAGNOSTIC: Log auth result
        logger.info(
            "auth_result",
            authenticated=auth_result.get("authenticated"),
            user=auth_result.get("user"),
            error=auth_result.get("error"),
            is_auto_login=auth_result.get("is_auto_login", False),
        )

        # Set request state consistently
        request.state.authenticated = auth_result.get("authenticated", False)

        if auth_result.get("authenticated"):
            request.state.is_auto_login = auth_result.get("is_auto_login", False)
            tenant_key = auth_result.get("tenant_key")
            if not tenant_key:
                logger.warning(
                    "authenticated_missing_tenant_key",
                    user_id=auth_result.get("user_id"),
                    path=request.url.path,
                )
                # Fall back to config-based default for setup/localhost mode only
                from api.dependencies import _get_default_tenant_key

                tenant_key = _get_default_tenant_key()
            request.state.tenant_key = tenant_key
            # Stash token expiry for downstream use and response header
            request.state.token_exp = auth_result.get("exp")
        else:
            # Auth failed - return 401
            logger.warning(
                "authentication_failed",
                error_code=ErrorCode.AUTH_UNAUTHORIZED.value,
                path=request.url.path,
                method=request.method,
                ip_address=request.client.host if request.client else "unknown",
                reason=auth_result.get("error", "No credentials provided"),
            )
            return JSONResponse(
                status_code=401,
                content={
                    "error": "Authentication required",
                    "detail": auth_result.get("error", "No credentials provided"),
                },
            )

        response = await call_next(request)

        # Add token expiry header so frontend can track remaining session time
        if hasattr(request.state, "token_exp") and request.state.token_exp:
            seconds_remaining = max(0, int(request.state.token_exp - time.time()))
            response.headers["X-Token-Expires-In"] = str(seconds_remaining)

        return response

    def _is_public_endpoint(self, path: str) -> bool:
        """Check if endpoint is public (no authentication required)"""
        if path in {"/", "/index.html", "/favicon.ico"} or path.startswith("/assets/"):
            return True
        public_paths = [
            "/health",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/api/auth/login",  # Login endpoint
            "/api/auth/refresh",  # Token refresh (handles own auth via cookie)
            "/api/auth/create-first-admin",  # First admin creation (Handover 0034)
            "/api/setup/status",  # Fresh install detection (Handover 0034)
            "/api/v1/config/frontend",  # Frontend config
            "/api/auth/me",  # Auth status check
            "/mcp",  # MCP-over-HTTP endpoint (handles own auth via X-API-Key)
            "/api/download/slash-commands.zip",  # Public slash command downloads
            "/api/download/install-script",  # Public install scripts
            "/api/download/agent-templates.zip",  # Optional-auth downloads (handles own auth logic)
            "/api/download/temp",  # Public download with token auth (one-time tokens)
            "/api/oauth/token",  # OAuth token exchange (public, PKCE-protected)
            "/api/oauth/.well-known/oauth-authorization-server",  # OAuth server metadata
        ]
        # Always allow token download path (token is the auth)
        if path.startswith("/api/download/temp") or "/api/download/temp/" in path:
            return True
        return any(path.startswith(p) for p in public_paths)
