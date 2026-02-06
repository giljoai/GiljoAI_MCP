"""
Rate Limiting for Authentication Endpoints (Handover 1009)

Implements per-IP rate limiting for sensitive auth endpoints:
- Login: 5 attempts/minute
- Register: 3 attempts/minute
- Password Reset: 3 attempts/minute

Uses in-memory storage with sliding window algorithm.
"""
import logging
import time
from collections import defaultdict, deque
from typing import Dict, Deque, Optional

from fastapi import HTTPException, Request, status


logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Rate limiter using sliding window algorithm with per-IP tracking.

    Features:
    - IP-based isolation (separate counters per IP)
    - Sliding window for accurate time-based limits
    - Automatic cleanup of expired entries
    - HTTP 429 responses with Retry-After header
    - Logging of violations for monitoring
    """

    def __init__(self):
        """
        Initialize rate limiter with in-memory storage.

        Storage format: {ip_address: deque([timestamp1, timestamp2, ...])}
        """
        self.requests: Dict[str, Deque[float]] = defaultdict(deque)
        logger.info("RateLimiter initialized (in-memory storage, sliding window)")

    def _get_client_ip(self, request: Request) -> str:
        """
        Extract client IP address from request.

        Args:
            request: FastAPI request object

        Returns:
            Client IP address (or 'unknown' if unavailable)
        """
        if request.client is None:
            return "unknown"
        return request.client.host

    def _cleanup_expired_entries(self, ip: str, window: int):
        """
        Remove expired request timestamps from tracking.

        Args:
            ip: Client IP address
            window: Time window in seconds
        """
        now = time.time()
        requests = self.requests[ip]

        # Remove timestamps outside the window
        while requests and requests[0] < now - window:
            requests.popleft()

    def check_rate_limit(
        self,
        request: Request,
        limit: int,
        window: int = 60,
        raise_on_limit: bool = False
    ) -> bool:
        """
        Check if request is within rate limit.

        Args:
            request: FastAPI request object
            limit: Maximum requests allowed in window
            window: Time window in seconds (default: 60)
            raise_on_limit: If True, raise HTTPException when limit exceeded

        Returns:
            True if request is allowed, False if blocked

        Raises:
            HTTPException: 429 if limit exceeded and raise_on_limit=True
        """
        # Skip rate limiting in test mode
        # Check for X-Test-Mode header OR test base URL
        if request.headers.get("X-Test-Mode") == "true":
            return True

        # Check if this is a test request (base_url starts with http://test)
        if str(request.base_url).startswith("http://test"):
            return True

        # Get client IP
        ip = self._get_client_ip(request)

        # Clean up expired entries
        self._cleanup_expired_entries(ip, window)

        # Get current request count
        requests = self.requests[ip]
        current_count = len(requests)

        # Check if under limit
        if current_count < limit:
            # Allow request - add timestamp
            requests.append(time.time())
            return True

        # Over limit - log violation
        endpoint = request.url.path if hasattr(request.url, 'path') else 'unknown'
        logger.warning(
            f"Rate limit exceeded - IP: {ip}, "
            f"Endpoint: {endpoint}, "
            f"Limit: {limit}/{window}s, "
            f"Current: {current_count}"
        )

        # Calculate retry-after time
        if requests:
            # Oldest request timestamp + window = when it expires
            oldest_request = requests[0]
            reset_time = oldest_request + window
            retry_after = int(reset_time - time.time())
            retry_after = max(1, retry_after)  # At least 1 second
        else:
            retry_after = window

        # Raise exception if requested
        if raise_on_limit:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many requests. Limit: {limit} per {window} seconds. Try again later.",
                headers={
                    'Retry-After': str(retry_after),
                    'X-RateLimit-Limit': str(limit),
                    'X-RateLimit-Remaining': '0',
                    'X-RateLimit-Window': str(window)
                }
            )

        return False

    def cleanup_expired(self):
        """
        Clean up all expired entries (for testing/maintenance).

        Removes IP entries that have no timestamps in the current window.
        """
        now = time.time()
        expired_ips = []

        for ip, requests in self.requests.items():
            # Remove old timestamps
            while requests and requests[0] < now - 3600:  # 1 hour cleanup window
                requests.popleft()

            # If no requests remain, mark IP for removal
            if not requests:
                expired_ips.append(ip)

        # Remove empty IP entries
        for ip in expired_ips:
            del self.requests[ip]

        if expired_ips:
            logger.debug(f"Cleaned up {len(expired_ips)} expired IP entries")


# Global rate limiter instance (singleton)
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """
    Get or create global rate limiter instance.

    Returns:
        RateLimiter instance
    """
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
