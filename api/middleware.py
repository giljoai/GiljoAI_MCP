"""
Middleware for FastAPI application
"""

import logging
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

        # Skip auth for public endpoints
        public_paths = ["/", "/health", "/docs", "/openapi.json", "/ws"]
        if any(request.url.path.startswith(path) for path in public_paths):
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

        # Validate API key if auth is enabled
        if auth_manager.is_enabled():
            if not api_key:
                return JSONResponse(status_code=401, content={"error": "Missing API key"})

            if not await auth_manager.validate_key(api_key):
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
