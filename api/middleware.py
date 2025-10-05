"""
Middleware for FastAPI application
"""

import logging
import os
import time
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """Authentication middleware for API endpoints"""

    def __init__(self, app, auth_manager: Callable):
        super().__init__(app)
        self.get_auth_manager = auth_manager

    async def dispatch(self, request: Request, call_next):
        """Process requests and check authentication"""
        from giljo_mcp.tenant import TenantManager

        # Always set tenant context for all requests (including public endpoints)
        tenant_key = request.headers.get("X-Tenant-Key")
        if tenant_key:
            logger.debug(f"Extracted tenant key from header: {tenant_key[:8]}...")
        else:
            # Use default tenant key from environment if header is missing
            tenant_key = os.getenv("DEFAULT_TENANT_KEY", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd")
            logger.debug(f"No tenant key in header, using default: {tenant_key[:8]}...")

        # Set tenant context AND store in request state (for persistence across async boundaries)
        try:
            TenantManager.set_current_tenant(tenant_key)
        except ValueError:
            # If tenant key is invalid, use the default
            logger.warning(f"Invalid tenant key format, using default")
            tenant_key = "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd"
            TenantManager.set_current_tenant(tenant_key)

        request.state.tenant_key = tenant_key

        # Skip auth for public endpoints
        public_paths = ["/", "/health", "/docs", "/openapi.json", "/ws", "/redoc"]
        if any(request.url.path.startswith(path) for path in public_paths):
            return await call_next(request)

        # OPTIONS requests should always pass through (CORS preflight)
        # They are handled by CORS middleware before reaching endpoints
        if request.method == "OPTIONS":
            return await call_next(request)

        # Get auth manager
        auth_manager = self.get_auth_manager()
        if not auth_manager:
            logger.warning("Auth manager not initialized")
            return await call_next(request)

        # Check for API key in header
        api_key = request.headers.get("X-API-Key")
        if not api_key:
            # Check for Bearer token
            auth_header = request.headers.get("Authorization")
            if auth_header and auth_header.startswith("Bearer "):
                api_key = auth_header[7:]

        # Validate API key if auth is enabled (mode-based: server/lan/wan require auth, localhost does not)
        if auth_manager.is_enabled():
            if not api_key:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": "Missing API key",
                        "detail": f"API key required for {auth_manager.mode.value} mode. Include X-API-Key header or Authorization: Bearer <key>"
                    }
                )

            # Validate API key - validate_api_key is synchronous
            if not auth_manager.validate_api_key(api_key):
                return JSONResponse(status_code=401, content={"error": "Invalid API key"})

        # Process request
        response = await call_next(request)
        return response


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
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self' data:; connect-src 'self' ws: wss:"

        # Strict Transport Security (only if HTTPS is enabled)
        # response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        # Referrer policy - control referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions policy - control browser features
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"

        return response
