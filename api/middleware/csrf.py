# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
CSRF Protection Middleware

Implements CSRF token validation for state-changing requests.

CSRF (Cross-Site Request Forgery) protection prevents malicious websites
from making unauthorized requests on behalf of authenticated users.

Created in Handover 0129c - Security Hardening & OWASP Compliance
"""

import logging
import secrets
from typing import Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


logger = logging.getLogger(__name__)


class CSRFProtectionMiddleware(BaseHTTPMiddleware):
    """
    CSRF (Cross-Site Request Forgery) protection.

    Generates CSRF tokens and validates them on state-changing requests.

    How it works:
    1. On first request, generates CSRF token and sets it in cookie
    2. Frontend reads token from cookie and includes in requests
    3. State-changing requests (POST, PUT, PATCH, DELETE) must include token
    4. Middleware validates token matches cookie before allowing request

    This prevents malicious sites from making requests on behalf of users.
    """

    def __init__(
        self,
        app,
        exempt_paths: list = None,
        exempt_prefixes: list = None,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        api_key_header: str = "X-API-Key",
    ):
        """
        Initialize CSRF protection middleware.

        Args:
            app: FastAPI application instance
            exempt_paths: Exact paths excluded from CSRF validation
            exempt_prefixes: Path prefixes excluded from CSRF validation
            cookie_name: Name of CSRF cookie (default: csrf_token)
            header_name: Name of CSRF header (default: X-CSRF-Token)
            api_key_header: Header name for API key auth (requests with this header skip CSRF)
        """
        super().__init__(app)
        self.exempt_paths = exempt_paths or []
        self.exempt_prefixes = exempt_prefixes or []
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.api_key_header = api_key_header
        logger.info(
            f"CSRFProtectionMiddleware initialized: "
            f"cookie={cookie_name}, header={header_name}, "
            f"exempt_paths={self.exempt_paths}, exempt_prefixes={self.exempt_prefixes}"
        )

    def _generate_token(self) -> str:
        """
        Generate a new cryptographically secure CSRF token.

        Returns:
            URL-safe token string (32 bytes = 43 characters base64)
        """
        return secrets.token_urlsafe(32)

    def _get_token_from_request(self, request: Request) -> str:
        """
        Extract CSRF token from request headers or form data.

        Args:
            request: Incoming HTTP request

        Returns:
            CSRF token string or None if not found
        """
        # Check header first (preferred for API requests)
        token = request.headers.get(self.header_name)
        if token:
            return token

        # For traditional form submissions, token might be in form data
        # (handled by endpoint, not middleware)

        return None

    def _get_token_from_cookie(self, request: Request) -> str:
        """
        Extract CSRF token from cookie.

        Args:
            request: Incoming HTTP request

        Returns:
            CSRF token string or None if not found
        """
        return request.cookies.get(self.cookie_name)

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Validate CSRF token for state-changing requests.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with CSRF cookie set

        Raises:
            HTTPException: 403 if CSRF validation fails
        """
        # Exempt certain paths (login, public endpoints)
        path = request.url.path
        if path in self.exempt_paths or any(path.startswith(p) for p in self.exempt_prefixes):
            response = await call_next(request)
            return response

        # Skip CSRF for API key-authenticated requests (not cookie-based)
        if request.headers.get(self.api_key_header):
            response = await call_next(request)
            return response

        # Only validate state-changing methods
        # GET, HEAD, and OPTIONS are safe methods (no state changes)
        if request.method in ["POST", "PUT", "PATCH", "DELETE"]:
            request_token = self._get_token_from_request(request)
            cookie_token = self._get_token_from_cookie(request)

            # Both tokens must exist and match
            if not request_token or not cookie_token:
                logger.warning(
                    f"CSRF validation failed - missing token: "
                    f"path={request.url.path}, method={request.method}, "
                    f"IP={request.client.host if request.client else 'unknown'}, "
                    f"has_cookie={bool(cookie_token)}, has_header={bool(request_token)}"
                )
                # Return JSONResponse directly instead of raising HTTPException.
                # BaseHTTPMiddleware wraps raised exceptions in an ExceptionGroup,
                # which bypasses FastAPI's exception handlers and causes a 500.
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": "CSRF validation failed - missing token. "
                        "Include X-CSRF-Token header in state-changing requests."
                    },
                )

            if request_token != cookie_token:
                logger.warning(
                    f"CSRF validation failed - token mismatch: "
                    f"path={request.url.path}, method={request.method}, "
                    f"IP={request.client.host if request.client else 'unknown'}"
                )
                # Return JSONResponse directly (same BaseHTTPMiddleware reason as above).
                return JSONResponse(
                    status_code=403,
                    content={"detail": "CSRF validation failed - invalid token"},
                )

        # Process request
        response = await call_next(request)

        # Set or refresh CSRF token cookie.
        # Generate on first visit; refresh on every GET to keep it alive during active use.
        # max_age matches JWT lifetime (24 hours) so the cookie doesn't expire mid-session.
        existing_token = request.cookies.get(self.cookie_name)
        if not existing_token or request.method == "GET":
            token = existing_token or self._generate_token()
            response.set_cookie(
                key=self.cookie_name,
                value=token,
                httponly=False,  # Must be False: JS reads cookie for double-submit pattern
                secure=request.url.scheme == "https",  # Adapt to connection scheme
                samesite="lax",  # Lax required for cross-origin LAN access (strict blocks cookie on IP-based origins)
                path="/",  # Must be root so cookie is sent on all API paths
                max_age=86400,  # 24 hours — matches JWT token lifetime
            )
            if not existing_token:
                logger.debug(f"Generated new CSRF token for IP: {request.client.host if request.client else 'unknown'}")

        return response


def get_csrf_token(request: Request) -> str:
    """
    Helper function to get CSRF token for current request.

    Useful for server-side rendering or templates.

    Args:
        request: Current HTTP request

    Returns:
        CSRF token string or empty string if not found

    Example usage in templates:
        <input type="hidden" name="csrf_token" value="{{ get_csrf_token(request) }}">

    Example usage in endpoints:
        from api.middleware.csrf import get_csrf_token

        @router.get("/form")
        async def get_form(request: Request):
            csrf_token = get_csrf_token(request)
            return {"csrf_token": csrf_token}
    """
    return request.cookies.get("csrf_token", "")


class CSRFProtectionOptional:
    """
    Optional CSRF protection decorator for specific endpoints.

    Use this when you want CSRF protection on specific endpoints
    but haven't enabled global CSRF middleware.

    Usage:
        from api.middleware.csrf import CSRFProtectionOptional

        @router.post("/sensitive-operation")
        @CSRFProtectionOptional()
        async def sensitive_operation(request: Request):
            # Operation logic...
            pass
    """

    def __init__(self, cookie_name: str = "csrf_token", header_name: str = "X-CSRF-Token"):
        """
        Initialize optional CSRF protection.

        Args:
            cookie_name: Name of CSRF cookie
            header_name: Name of CSRF header
        """
        self.cookie_name = cookie_name
        self.header_name = header_name

    def __call__(self, func):
        """
        Decorate endpoint function with CSRF protection.

        Args:
            func: Endpoint function to protect

        Returns:
            Wrapped function with CSRF validation
        """

        async def wrapper(*args, **kwargs):
            # Extract request
            request = kwargs.get("request") or (args[0] if args else None)

            if not request or not isinstance(request, Request):
                logger.error("CSRFProtectionOptional: Could not extract Request object")
                return await func(*args, **kwargs)

            # Get tokens
            request_token = request.headers.get(self.header_name)
            cookie_token = request.cookies.get(self.cookie_name)

            # Validate
            if not request_token or not cookie_token or request_token != cookie_token:
                logger.warning(
                    f"CSRF validation failed in decorator: "
                    f"path={request.url.path}, IP={request.client.host if request.client else 'unknown'}"
                )
                raise HTTPException(status_code=403, detail="CSRF validation failed")

            return await func(*args, **kwargs)

        return wrapper
