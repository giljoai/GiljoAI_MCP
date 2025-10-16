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
    Authentication middleware - ALWAYS ACTIVE.

    - Localhost (127.0.0.1, ::1): Auto-login
    - Network clients: Require JWT or API key

    This middleware replaces the mode-based authentication logic
    with a unified approach that always authenticates requests.
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

        # Check if system is in setup mode
        setup_mode = False
        try:
            # Get config from app state
            config = getattr(request.app.state, "api_state", None)
            if config:
                config = getattr(config, "config", None)
                if config:
                    setup_mode = getattr(config, "setup_mode", False)
        except Exception as e:
            logger.warning(f"Could not check setup mode in AuthMiddleware: {e}")

        # In setup mode, allow additional endpoints that setup wizard needs
        if setup_mode and self._is_setup_allowed_endpoint(request.url.path):
            # Set minimal request state for setup mode
            request.state.authenticated = True
            request.state.user_id = "setup-mode"
            request.state.user = None
            request.state.is_auto_login = True
            request.state.tenant_key = "default"
            return await call_next(request)

        # Public endpoints bypass auth
        if self._is_public_endpoint(request.url.path):
            return await call_next(request)

        # DIAGNOSTIC: Log incoming request details
        logger.info(f"[AuthMiddleware] {request.method} {request.url.path} - IP: {request.client.host if request.client else 'unknown'}")
        logger.info(f"[AuthMiddleware] Cookie header present: {bool(request.headers.get('cookie'))}")
        logger.info(f"[AuthMiddleware] Authorization header present: {bool(request.headers.get('authorization'))}")

        # Authenticate (auto-login or credentials)
        auth_result = await auth_manager.authenticate_request(request)

        # DIAGNOSTIC: Log auth result
        logger.info(f"[AuthMiddleware] Auth result: authenticated={auth_result.get('authenticated')}, user={auth_result.get('user')}, error={auth_result.get('error')}")

        # Set request state consistently
        request.state.authenticated = auth_result.get("authenticated", False)

        if auth_result.get("authenticated"):
            # Always set both user_id (string) and user (object if available)
            request.state.user_id = auth_result.get("user_id") or auth_result.get("user")
            request.state.user = auth_result.get("user_obj")  # User object or None
            request.state.is_auto_login = auth_result.get("is_auto_login", False)
            request.state.tenant_key = auth_result.get("tenant_key", "default")
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
            "/api/setup",  # All setup endpoints (setup wizard)
            "/api/auth/login",  # Login endpoint
            "/api/auth/change-password",  # Password change (first-time setup)
            "/api/v1/config/frontend",  # Frontend config (needed during setup)
            "/api/v1/products",  # Product listing (needed during setup)
            "/api/v1/agents",  # Agent listing (returns empty during setup)
            "/api/v1/messages",  # Message listing (returns empty during setup)
            "/api/auth/me",  # Auth status check
        ]
        return any(path.startswith(p) for p in PUBLIC_PATHS)

    def _is_setup_allowed_endpoint(self, path: str) -> bool:
        """Check if endpoint is allowed during setup mode"""
        SETUP_ALLOWED_PATHS = [
            "/api/v1/config/frontend",  # Frontend needs this for API connection info
            "/api/v1/products",  # Product listing may be needed
            "/api/v1/agents",  # Agent listing (returns empty in setup mode)
            "/api/v1/messages",  # Message listing (returns empty in setup mode)
            "/api/auth/me",  # Auth status check
            "/api/setup",  # All setup endpoints
            "/ws",  # WebSocket connections
        ]
        return any(path.startswith(p) for p in SETUP_ALLOWED_PATHS)


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

    async def dispatch(self, request: Request, call_next):
        """Apply rate limiting"""

        # Get client identifier (IP address)
        client_ip = request.client.host if request.client else "unknown"

        # Get current time
        current_time = time.time()

        # Clean old entries
        if client_ip in self.request_times:
            self.request_times[client_ip] = [t for t in self.request_times[client_ip] if current_time - t < 60]
        else:
            self.request_times[client_ip] = []

        # Check rate limit
        if len(self.request_times[client_ip]) >= self.requests_per_minute:
            return JSONResponse(status_code=429, content={"error": "Rate limit exceeded"})

        # Add current request time
        self.request_times[client_ip].append(current_time)

        # Process request
        response = await call_next(request)
        return response


class SetupModeMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle setup mode - blocks most API access when database is not configured.
    Only allows setup-related endpoints and essential system endpoints.
    """

    def __init__(self, app, config_getter: Callable):
        super().__init__(app)
        self.get_config = config_getter
        logger.info("[SetupModeMiddleware] Middleware initialized")

    async def dispatch(self, request: Request, call_next):
        """Check if system is in setup mode and restrict access accordingly"""

        # Always allow these endpoints regardless of setup mode
        always_allowed = [
            "/",
            "/health",
            "/docs",
            "/openapi.json",
            "/redoc",
            "/api/setup",  # All setup endpoints
            "/api/setup/status",
            "/api/setup/database",  # Database setup endpoints
            "/api/setup/reset",
            "/api/setup/detect-tools",
            "/api/setup/test-mcp-connection",
            "/api/setup/configure-deployment-mode",
            "/api/setup/complete",
            "/api/setup/test-database",
        ]

        # Check if path is always allowed
        path = request.url.path
        if any(path.startswith(allowed) for allowed in always_allowed):
            return await call_next(request)

        # Get config and check setup mode
        try:
            config = self.get_config()
        except Exception as e:
            logger.error(f"Error getting config in SetupModeMiddleware: {e}", exc_info=True)
            # If we can't get config, block access to be safe
            return JSONResponse(
                status_code=503,
                content={
                    "error": "System configuration error",
                    "detail": "Unable to load system configuration. Please contact administrator.",
                    "requires_setup": True,
                },
            )

        setup_mode = getattr(config, "setup_mode", False)
        logger.info(f"[SetupModeMiddleware] path={path}, setup_mode={setup_mode}")

        # If not in setup mode, check if database is actually configured
        if not setup_mode:
            database_configured = False
            if hasattr(config, "database") and config.database:
                # Log what we're checking
                logger.debug(
                    f"Database config: host={getattr(config.database, 'host', None)}, "
                    f"port={getattr(config.database, 'port', None)}, "
                    f"name={getattr(config.database, 'name', None)}, "
                    f"database_name={getattr(config.database, 'database_name', None)}, "
                    f"username={getattr(config.database, 'username', None)}, "
                    f"user={getattr(config.database, 'user', None)}"
                )

                # Check for both 'name' and 'database_name' fields
                db_name = getattr(config.database, "database_name", None) or getattr(config.database, "name", None)
                db_user = getattr(config.database, "username", None) or getattr(config.database, "user", None)

                database_configured = bool(config.database.host and config.database.port and db_name and db_user)
                logger.debug(f"Database configured: {database_configured}")

            if database_configured:
                # Database configured and not in setup mode - allow request
                logger.debug("Allowing request - database configured and not in setup mode")
                return await call_next(request)
            # Database not configured even though not in setup mode - block
            logger.warning(f"Blocking access to {path} - database not configured")
        else:
            # In setup mode - block
            logger.warning(f"Blocking access to {path} - system in setup mode")

        # Block the request
        return JSONResponse(
            status_code=503,
            content={
                "error": "System setup required",
                "detail": "Database configuration is required. Please complete the setup wizard.",
                "setup_url": "/setup",
                "requires_setup": True,
            },
        )


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
