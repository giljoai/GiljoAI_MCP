"""
Middleware for FastAPI application
"""

import logging
import time
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

        # (already handled above)

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
            import os

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


class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware"""

    async def dispatch(self, request: Request, call_next):
        """Log requests and responses"""
        start_time = time.time()

        # Log request
        logger.info(f"Request: {request.method} {request.url.path}")

        # Process request
        response = await call_next(request)

        # Calculate duration
        duration = time.time() - start_time

        # Log response
        logger.info(f"Response: {response.status_code} ({duration:.3f}s)")

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware"""

    def __init__(self, app, requests_per_minute: int = 60):
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.request_times = {}
        # Exempt endpoints from rate limiting (health checks, auth status, etc.)
        self.exempt_paths = [
            "/api/health",
            "/api/auth/me",  # Auth status check
            "/api/v1/ws",  # WebSocket connections
            "/docs",  # API documentation
            "/openapi.json",  # OpenAPI schema
        ]

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting"""

        # Check if path is exempt from rate limiting
        request_path = request.url.path
        for exempt_path in self.exempt_paths:
            if request_path.startswith(exempt_path):
                response = await call_next(request)
                return response

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # All clients are rate limited (production parity)
        # No special treatment for localhost

        # Get current time
        current_time = time.time()

        # Clean old entries
        if client_ip in self.request_times:
            self.request_times[client_ip] = [t for t in self.request_times[client_ip] if current_time - t < 60]
        else:
            self.request_times[client_ip] = []

        # Check rate limit
        if len(self.request_times[client_ip]) >= self.requests_per_minute:
            logger.warning(
                f"[Rate Limit] Exceeded for {client_ip}: {len(self.request_times[client_ip])} requests in last minute"
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "detail": f"Maximum {self.requests_per_minute} requests per minute",
                    "retry_after": "60",
                },
            )

        # Add current request time
        self.request_times[client_ip].append(current_time)

        # Process request
        response = await call_next(request)
        return response


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Security headers middleware - adds standard security headers to all responses"""

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response"""
        response = await call_next(request)

        # Prevent clickjacking attacks
        response.headers["X-Frame-Options"] = "DENY"

        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Enable XSS protection in older browsers
        response.headers["X-XSS-Protection"] = "1; mode=block"

        # Content Security Policy - restrict resource loading
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' ws: wss:"
        )

        # Strict Transport Security (only if HTTPS is enabled)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Referrer policy - control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - control browser features
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response


class APIMetricsMiddleware(BaseHTTPMiddleware):
    """API metrics middleware - counts total API and MCP calls."""

    async def dispatch(self, request: Request, call_next):
        """Increment API and MCP call counters."""
        tenant_key = getattr(request.state, "tenant_key", "default")
        if tenant_key:
            request.app.state.api_state.api_call_count[tenant_key] = request.app.state.api_state.api_call_count.get(tenant_key, 0) + 1
            if request.url.path.startswith("/mcp"):
                request.app.state.api_state.mcp_call_count[tenant_key] = request.app.state.api_state.mcp_call_count.get(tenant_key, 0) + 1
        response = await call_next(request)
        return response
