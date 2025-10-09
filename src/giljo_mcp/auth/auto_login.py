"""
Auto-login middleware for localhost clients.

This module provides middleware that automatically authenticates requests
from localhost (127.0.0.1, ::1) as the system "localhost" user, enabling
zero-click authentication for local development and single-user setups.

This replaces the legacy LOCAL mode from the 3-mode architecture, providing
the same user experience with a cleaner, more maintainable implementation.
"""

import logging

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from .localhost_user import ensure_localhost_user


logger = logging.getLogger(__name__)

# Localhost IP addresses (IPv4 and IPv6)
LOCALHOST_IPS: set[str] = {"127.0.0.1", "::1"}


class AutoLoginMiddleware:
    """
    Middleware for automatic authentication of localhost requests.

    Requests from 127.0.0.1 or ::1 are automatically authenticated
    as the system "localhost" user. All other requests require
    JWT/API key authentication.

    Example:
        middleware = AutoLoginMiddleware(db_session)
        authenticated = await middleware.authenticate_request(request)
        if authenticated:
            # request.state.user is set to localhost user
            # request.state.is_auto_login is True
            pass
        else:
            # Require JWT/API key authentication
            pass
    """

    def __init__(self, db: AsyncSession):
        """
        Initialize middleware with database session.

        Args:
            db: Async database session for user lookup/creation
        """
        self.db = db

    async def authenticate_request(self, request: Request) -> bool:
        """
        Authenticate request based on client IP.

        Automatically authenticates localhost clients, returns False
        for network clients (requiring manual authentication).

        Args:
            request: FastAPI Request object

        Returns:
            bool: True if authenticated (localhost auto-login),
                  False if authentication required (network client)

        Side effects:
            If localhost client, sets request.state.user, request.state.is_auto_login,
            and request.state.authenticated
        """
        # Get client IP - check headers first (for proxy/load balancer support)
        client_ip = None

        # Check X-Forwarded-For header (proxy standard)
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For can have multiple IPs, get the first (original client)
            client_ip = forwarded_for.split(",")[0].strip()

        # Check X-Real-IP header (nginx standard)
        if not client_ip:
            client_ip = request.headers.get("X-Real-IP")

        # Fall back to request.client.host if headers not present
        if not client_ip:
            try:
                client_ip = request.client.host if request.client else None
            except (AttributeError, Exception):
                client_ip = None

        logger.debug(f"Auto-login check for client IP: {client_ip}")

        # Check if localhost client
        if client_ip in LOCALHOST_IPS:
            # Auto-login as localhost user
            logger.info(f"Auto-login: Authenticating localhost client ({client_ip})")

            user = await ensure_localhost_user(self.db)

            # Set request state
            request.state.user = user
            request.state.is_auto_login = True
            request.state.authenticated = True

            logger.debug(f"Auto-login successful: user_id={user.id}, username={user.username}")

            return True

        # Network client - requires manual authentication
        logger.debug(f"Network client detected ({client_ip}) - manual auth required")
        return False
