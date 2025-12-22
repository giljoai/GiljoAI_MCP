"""
Security Headers Middleware

Adds production-grade security headers to all responses.

Created in Handover 0129c - Security Hardening & OWASP Compliance
"""
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from typing import Callable
import logging

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    Middleware to add security headers to all responses.

    Headers added:
    - Strict-Transport-Security (HSTS): Enforce HTTPS
    - Content-Security-Policy (CSP): Prevent XSS
    - X-Frame-Options: Prevent clickjacking
    - X-Content-Type-Options: Prevent MIME sniffing
    - Referrer-Policy: Control referrer information
    - Permissions-Policy: Control browser features
    - X-XSS-Protection: Legacy XSS protection

    All headers follow OWASP security best practices.
    """

    def __init__(self, app, hsts_max_age: int = 31536000):
        """
        Initialize security headers middleware.

        Args:
            app: FastAPI application instance
            hsts_max_age: HSTS max-age in seconds (default: 1 year)
        """
        super().__init__(app)
        self.hsts_max_age = hsts_max_age
        logger.info(f"SecurityHeadersMiddleware initialized with HSTS max-age: {hsts_max_age}s")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Add security headers to response.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with security headers added
        """
        response = await call_next(request)

        # HSTS: Only add for HTTPS connections (meaningless for HTTP)
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = (
                f"max-age={self.hsts_max_age}; includeSubDomains; preload"
            )

        # CSP: Strict policy preventing XSS
        # Note: Vue needs 'unsafe-inline' and 'unsafe-eval' for development
        # In production, use nonce-based CSP for tighter security
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "  # Vue needs eval
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss:; "  # WebSocket connections
            "frame-ancestors 'none'; "  # No embedding
            "base-uri 'self'; "
            "form-action 'self'"
        )

        # X-Frame-Options: Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"

        # X-Content-Type-Options: Prevent MIME sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy: Limit referrer information
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: Disable unnecessary features
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "magnetometer=(), "
            "gyroscope=(), "
            "accelerometer=()"
        )

        # X-XSS-Protection: Legacy XSS protection (deprecated but harmless)
        response.headers["X-XSS-Protection"] = "1; mode=block"

        return response


class CORSSecurityMiddleware(BaseHTTPMiddleware):
    """
    Enhanced CORS middleware with security controls.

    Replaces default CORS middleware with stricter controls:
    - Only allows configured origins
    - Validates Origin header
    - Supports credentials
    - Restricts allowed methods and headers

    This provides tighter security than FastAPI's default CORSMiddleware.
    """

    def __init__(self, app, allowed_origins: list = None):
        """
        Initialize CORS security middleware.

        Args:
            app: FastAPI application instance
            allowed_origins: List of allowed origin URLs (default: localhost:3000)
        """
        super().__init__(app)
        self.allowed_origins = allowed_origins or ["http://localhost:3000"]
        logger.info(f"CORSSecurityMiddleware initialized with allowed origins: {self.allowed_origins}")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Validate origin and add CORS headers.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with CORS headers (if origin allowed)
        """
        origin = request.headers.get("origin")

        # Handle preflight OPTIONS requests
        if request.method == "OPTIONS":
            if origin in self.allowed_origins:
                response = Response()
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
                response.headers["Access-Control-Allow-Headers"] = (
                    "Content-Type, X-Tenant-Key, Authorization, X-CSRF-Token"
                )
                response.headers["Access-Control-Max-Age"] = "3600"
                return response
            else:
                # Reject unknown origins
                logger.warning(f"CORS: Rejected preflight from unknown origin: {origin}")
                return Response(status_code=403, content="Origin not allowed")

        # Process normal request
        response = await call_next(request)

        # Only allow configured origins
        if origin in self.allowed_origins:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = (
                "Content-Type, X-Tenant-Key, Authorization, X-CSRF-Token"
            )
        else:
            # Reject unknown origins by not setting CORS headers
            if origin:
                logger.warning(f"CORS: Rejected request from unknown origin: {origin}")

        return response
