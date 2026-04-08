# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Rate Limiting Middleware

Implements per-IP rate limiting to prevent abuse and DoS attacks.

Created in Handover 0129c - Security Hardening & OWASP Compliance
"""

import logging
import time
from collections import defaultdict, deque
from typing import Callable

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Token bucket rate limiter.

    Allows burst traffic while enforcing average rate limit.
    Uses sliding window algorithm for accurate rate limiting.
    """

    def __init__(self, requests_per_minute: int = 100):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute (default: 100)
        """
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1 minute in seconds
        self.requests: dict[str, deque[float]] = defaultdict(deque)
        logger.debug(f"RateLimiter initialized: {requests_per_minute} req/min")

    def is_allowed(self, key: str) -> bool:
        """
        Check if request is allowed for given key (e.g., IP address).

        Args:
            key: Identifier (typically IP address)

        Returns:
            True if request is allowed, False if rate limited
        """
        now = time.time()
        requests = self.requests[key]

        # Remove requests outside the time window
        while requests and requests[0] < now - self.window_size:
            requests.popleft()

        # Check if under limit
        if len(requests) < self.requests_per_minute:
            requests.append(now)
            return True

        return False

    def get_remaining(self, key: str) -> int:
        """
        Get remaining requests for key.

        Args:
            key: Identifier (IP address)

        Returns:
            Number of remaining requests in current window
        """
        now = time.time()
        requests = self.requests[key]

        # Remove old requests
        while requests and requests[0] < now - self.window_size:
            requests.popleft()

        return max(0, self.requests_per_minute - len(requests))

    def get_reset_time(self, key: str) -> float:
        """
        Get timestamp when rate limit resets.

        Args:
            key: Identifier (IP address)

        Returns:
            Unix timestamp when oldest request expires
        """
        requests = self.requests[key]
        if not requests:
            return time.time()
        return requests[0] + self.window_size


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Rate limiting middleware.

    Applies rate limits per IP address to prevent abuse and DoS attacks.

    Features:
    - Per-IP rate limiting with sliding window
    - Configurable exempt paths (health checks, metrics)
    - X-RateLimit-* headers for client information
    - Respects X-Forwarded-For for proxied requests
    """

    def __init__(self, app, requests_per_minute: int = 100, exempt_paths: list = None):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application instance
            requests_per_minute: Global rate limit (default: 100 req/min)
            exempt_paths: Paths excluded from rate limiting (default: /api/health, /api/metrics)
        """
        super().__init__(app)
        self.rate_limiter = RateLimiter(requests_per_minute)
        self.exempt_paths = exempt_paths or ["/api/health", "/api/metrics"]
        logger.info(
            f"RateLimitMiddleware initialized: {requests_per_minute} req/min, exempt paths: {self.exempt_paths}"
        )

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.

        Handles proxied requests by checking X-Forwarded-For and X-Real-IP headers.

        Args:
            request: Incoming HTTP request

        Returns:
            Client IP address as string
        """
        # Check X-Forwarded-For (if behind proxy/load balancer)
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            # X-Forwarded-For can be: "client, proxy1, proxy2"
            # We want the original client IP (first in list)
            return forwarded.split(",")[0].strip()

        # Check X-Real-IP (alternative proxy header)
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip

        # Fallback to direct connection IP
        return request.client.host if request.client else "unknown"

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Apply rate limiting to request.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response with rate limit headers

        Raises:
            HTTPException: 429 if rate limit exceeded
        """
        # Skip rate limiting for static file requests (production frontend serving)
        path = request.url.path
        if path in {"/", "/index.html", "/favicon.ico"} or path.startswith("/assets/"):
            return await call_next(request)

        # Exempt certain paths (health checks, metrics, etc.)
        if path in self.exempt_paths:
            return await call_next(request)

        # Get client IP
        client_ip = self._get_client_ip(request)

        # Check rate limit
        if not self.rate_limiter.is_allowed(client_ip):
            logger.warning(
                f"Rate limit exceeded for IP: {client_ip}, path: {request.url.path}, method: {request.method}"
            )

            # Calculate retry-after
            reset_time = self.rate_limiter.get_reset_time(client_ip)
            retry_after = int(reset_time - time.time())

            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded. Please try again later.",
                headers={
                    "Retry-After": str(max(1, retry_after)),  # At least 1 second
                    "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(int(reset_time)),
                },
            )

        # Add rate limit headers to response
        response = await call_next(request)

        remaining = self.rate_limiter.get_remaining(client_ip)
        reset_time = self.rate_limiter.get_reset_time(client_ip)

        response.headers["X-RateLimit-Limit"] = str(self.rate_limiter.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(int(reset_time))

        return response


class EndpointRateLimiter:
    """
    Decorator for per-endpoint rate limiting.

    Allows stricter rate limits on specific endpoints (e.g., login, signup).

    Usage:
        from api.middleware.rate_limiter import EndpointRateLimiter

        @router.post("/login")
        @EndpointRateLimiter(requests_per_minute=10)
        async def login(request: Request, credentials: LoginCredentials):
            # Login logic...
            pass

    This is ADDITIONAL to global rate limiting (both limits apply).
    """

    def __init__(self, requests_per_minute: int):
        """
        Initialize endpoint rate limiter.

        Args:
            requests_per_minute: Rate limit for this specific endpoint
        """
        self.rate_limiter = RateLimiter(requests_per_minute)
        self.requests_per_minute = requests_per_minute

    def __call__(self, func):
        """
        Decorate endpoint function with rate limiting.

        Args:
            func: Endpoint function to decorate

        Returns:
            Wrapped function with rate limiting
        """

        async def wrapper(*args, **kwargs):
            # Extract request from args or kwargs
            request = kwargs.get("request") or (args[0] if args else None)

            if not request or not isinstance(request, Request):
                logger.error("EndpointRateLimiter: Could not extract Request object")
                return await func(*args, **kwargs)

            # Get client IP
            client_ip = request.client.host if request.client else "unknown"

            # Check endpoint-specific rate limit
            if not self.rate_limiter.is_allowed(client_ip):
                logger.warning(
                    f"Endpoint rate limit exceeded for IP: {client_ip}, "
                    f"endpoint: {request.url.path}, limit: {self.requests_per_minute}/min"
                )

                reset_time = self.rate_limiter.get_reset_time(client_ip)
                retry_after = int(reset_time - time.time())

                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded for this endpoint. Limit: {self.requests_per_minute}/min",
                    headers={
                        "Retry-After": str(max(1, retry_after)),
                        "X-RateLimit-Limit": str(self.requests_per_minute),
                        "X-RateLimit-Remaining": "0",
                        "X-RateLimit-Reset": str(int(reset_time)),
                    },
                )

            return await func(*args, **kwargs)

        return wrapper
