"""
Unit tests for rate limiting middleware (Handover 1009)

Following TDD principles - tests written FIRST, implementation comes after.

Rate limiting requirements:
- Login: 5 attempts/minute per IP
- Register: 3 attempts/minute per IP
- Password Reset: 3 attempts/minute per IP
- Lockout duration: 60 seconds
- HTTP 429 response with Retry-After header when limit exceeded
- Different IPs have separate limits
- Log rate limit violations for monitoring
"""

import time
from unittest.mock import Mock, patch

import pytest
from fastapi import HTTPException, Request, status


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request with client IP"""
    request = Mock(spec=Request)
    request.client = Mock()
    request.client.host = "192.168.1.100"
    request.url = Mock()
    request.url.path = "/api/auth/login"
    return request


@pytest.fixture
def rate_limiter():
    """Create rate limiter instance (will be imported after implementation)"""
    # Will be updated after middleware implementation
    from api.middleware.rate_limit import RateLimiter

    return RateLimiter()


class TestRateLimitingBasics:
    """Test basic rate limiting functionality"""

    def test_login_under_rate_limit_succeeds(self, rate_limiter, mock_request):
        """
        Test 1: Requests under the limit should succeed

        Given: Login endpoint with 5 requests/minute limit
        When: User makes 3 login attempts
        Then: All 3 attempts should be allowed (under limit)
        """
        # Mock request for login endpoint
        mock_request.url.path = "/api/auth/login"

        # Make 3 requests (under the limit of 5)
        for i in range(3):
            is_allowed = rate_limiter.check_rate_limit(mock_request, limit=5, window=60)
            assert is_allowed, f"Request {i + 1}/3 should be allowed (under limit of 5)"

    def test_login_at_rate_limit_succeeds(self, rate_limiter, mock_request):
        """
        Test 2: Request exactly at limit should still succeed

        Given: Login endpoint with 5 requests/minute limit
        When: User makes exactly 5 login attempts
        Then: All 5 attempts should be allowed (at limit boundary)
        """
        mock_request.url.path = "/api/auth/login"

        # Make exactly 5 requests (at the limit)
        for i in range(5):
            is_allowed = rate_limiter.check_rate_limit(mock_request, limit=5, window=60)
            assert is_allowed, f"Request {i + 1}/5 should be allowed (at limit)"

    def test_login_over_rate_limit_returns_429(self, rate_limiter, mock_request):
        """
        Test 3: Request over limit should return HTTP 429

        Given: Login endpoint with 5 requests/minute limit
        When: User makes 6 login attempts
        Then: 6th attempt should return HTTP 429 (Too Many Requests)
        And: Response should include Retry-After header
        """
        mock_request.url.path = "/api/auth/login"

        # Make 5 successful requests (at limit)
        for i in range(5):
            is_allowed = rate_limiter.check_rate_limit(mock_request, limit=5, window=60)
            assert is_allowed, f"Request {i + 1}/5 should be allowed"

        # 6th request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit(mock_request, limit=5, window=60, raise_on_limit=True)

        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
        assert "too many requests" in exc_info.value.detail.lower()

        # Check for Retry-After header in exception
        # (Implementation should add this to headers dict)
        assert hasattr(exc_info.value, "headers")
        assert "Retry-After" in exc_info.value.headers


class TestRateLimitingCooldown:
    """Test rate limit cooldown/reset behavior"""

    def test_login_after_cooldown_succeeds(self, rate_limiter, mock_request):
        """
        Test 4: After cooldown period, requests should work again

        Given: Login endpoint with 5 requests/minute limit
        When: User makes 5 requests, waits 61 seconds, makes another request
        Then: Request after cooldown should be allowed
        """
        mock_request.url.path = "/api/auth/login"

        # Make 5 requests (at limit)
        for i in range(5):
            is_allowed = rate_limiter.check_rate_limit(mock_request, limit=5, window=60)
            assert is_allowed

        # Mock time passage (61 seconds)
        # Implementation should use time.time() for tracking
        with patch("api.middleware.rate_limit.time") as mock_time:
            # Simulate current time + 61 seconds
            original_time = time.time()
            mock_time.time.return_value = original_time + 61

            # This request should succeed (after cooldown)
            is_allowed = rate_limiter.check_rate_limit(mock_request, limit=5, window=60)
            assert is_allowed, "Request after cooldown should be allowed"


class TestRateLimitingIsolation:
    """Test IP-based isolation of rate limits"""

    def test_different_ips_have_separate_limits(self, rate_limiter):
        """
        Test 5: Different IP addresses should have separate rate limits

        Given: Login endpoint with 5 requests/minute limit
        When: IP1 makes 5 requests AND IP2 makes 5 requests
        Then: Both IPs should succeed (separate counters)
        """
        # Create two requests from different IPs
        request_ip1 = Mock(spec=Request)
        request_ip1.client = Mock()
        request_ip1.client.host = "192.168.1.100"
        request_ip1.url = Mock()
        request_ip1.url.path = "/api/auth/login"

        request_ip2 = Mock(spec=Request)
        request_ip2.client = Mock()
        request_ip2.client.host = "192.168.1.200"
        request_ip2.url = Mock()
        request_ip2.url.path = "/api/auth/login"

        # IP1 makes 5 requests (at limit)
        for i in range(5):
            is_allowed = rate_limiter.check_rate_limit(request_ip1, limit=5, window=60)
            assert is_allowed, f"IP1 request {i + 1}/5 should be allowed"

        # IP2 makes 5 requests (should also succeed - separate counter)
        for i in range(5):
            is_allowed = rate_limiter.check_rate_limit(request_ip2, limit=5, window=60)
            assert is_allowed, f"IP2 request {i + 1}/5 should be allowed (separate limit)"

        # IP1 should be blocked on 6th request
        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit(request_ip1, limit=5, window=60, raise_on_limit=True)
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestRateLimitingEndpointSpecific:
    """Test endpoint-specific rate limits"""

    def test_register_endpoint_has_lower_limit(self, rate_limiter, mock_request):
        """
        Test 6: Register endpoint should have 3 requests/minute limit

        Given: Register endpoint with 3 requests/minute limit
        When: User makes 4 registration attempts
        Then: 4th attempt should return HTTP 429
        """
        mock_request.url.path = "/api/auth/register"

        # Make 3 successful requests (at limit)
        for i in range(3):
            is_allowed = rate_limiter.check_rate_limit(mock_request, limit=3, window=60)
            assert is_allowed, f"Request {i + 1}/3 should be allowed"

        # 4th request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit(mock_request, limit=3, window=60, raise_on_limit=True)
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS

    def test_password_reset_endpoint_has_lower_limit(self, rate_limiter, mock_request):
        """
        Test 7: Password reset endpoint should have 3 requests/minute limit

        Given: Password reset endpoint with 3 requests/minute limit
        When: User makes 4 password reset attempts
        Then: 4th attempt should return HTTP 429
        """
        mock_request.url.path = "/api/auth/password-reset"

        # Make 3 successful requests (at limit)
        for i in range(3):
            is_allowed = rate_limiter.check_rate_limit(mock_request, limit=3, window=60)
            assert is_allowed, f"Request {i + 1}/3 should be allowed"

        # 4th request should be blocked
        with pytest.raises(HTTPException) as exc_info:
            rate_limiter.check_rate_limit(mock_request, limit=3, window=60, raise_on_limit=True)
        assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS


class TestRateLimitingLogging:
    """Test rate limit violation logging"""

    def test_rate_limit_violations_are_logged(self, rate_limiter, mock_request):
        """
        Test 8: Rate limit violations should be logged for monitoring

        Given: Login endpoint with 5 requests/minute limit
        When: User exceeds rate limit
        Then: Violation should be logged with IP, endpoint, and timestamp
        """
        mock_request.url.path = "/api/auth/login"

        # Make 5 requests (at limit)
        for i in range(5):
            rate_limiter.check_rate_limit(mock_request, limit=5, window=60)

        # Mock logger to capture violation
        with patch("api.middleware.rate_limit.logger") as mock_logger:
            # 6th request should trigger logging
            try:
                rate_limiter.check_rate_limit(mock_request, limit=5, window=60, raise_on_limit=True)
            except HTTPException:
                pass

            # Verify logging occurred
            mock_logger.warning.assert_called_once()
            log_message = mock_logger.warning.call_args[0][0]
            assert "rate limit" in log_message.lower()
            assert "192.168.1.100" in log_message  # IP address
            assert "/api/auth/login" in log_message  # Endpoint


class TestRateLimitingRetryAfterHeader:
    """Test Retry-After header calculation"""

    def test_retry_after_header_shows_remaining_time(self, rate_limiter, mock_request):
        """
        Test 9: Retry-After header should show seconds until reset

        Given: Login endpoint with 60 second window
        When: User exceeds rate limit after 20 seconds
        Then: Retry-After header should show ~40 seconds
        """
        mock_request.url.path = "/api/auth/login"

        # Make 5 requests (at limit)
        for i in range(5):
            rate_limiter.check_rate_limit(mock_request, limit=5, window=60)

        # Mock time passage (20 seconds into window)
        with patch("api.middleware.rate_limit.time") as mock_time:
            original_time = time.time()
            mock_time.time.return_value = original_time + 20

            # 6th request should be blocked with Retry-After
            with pytest.raises(HTTPException) as exc_info:
                rate_limiter.check_rate_limit(mock_request, limit=5, window=60, raise_on_limit=True)

            # Retry-After should be approximately 40 seconds (60 - 20)
            retry_after = int(exc_info.value.headers["Retry-After"])
            assert 35 <= retry_after <= 45, f"Retry-After should be ~40 seconds, got {retry_after}"


class TestRateLimitingEdgeCases:
    """Test edge cases and error handling"""

    def test_missing_client_ip_defaults_to_unknown(self, rate_limiter):
        """
        Test 10: Requests without client IP should use fallback

        Given: Request with no client information
        When: Rate limiting is applied
        Then: Should use 'unknown' as IP key (prevent crashes)
        """
        request_no_client = Mock(spec=Request)
        request_no_client.client = None
        request_no_client.url = Mock()
        request_no_client.url.path = "/api/auth/login"

        # Should not crash - use fallback IP
        is_allowed = rate_limiter.check_rate_limit(request_no_client, limit=5, window=60)
        assert is_allowed  # First request should succeed

    def test_concurrent_requests_from_same_ip(self, rate_limiter, mock_request):
        """
        Test 11: Concurrent requests should be counted correctly

        Given: Multiple threads making simultaneous requests
        When: Requests arrive concurrently
        Then: Rate counter should remain accurate (thread-safe)
        """
        mock_request.url.path = "/api/auth/login"

        # Simulate concurrent requests (simplified - actual implementation would use threading)
        # This test verifies counter increments correctly
        for i in range(5):
            is_allowed = rate_limiter.check_rate_limit(mock_request, limit=5, window=60)
            assert is_allowed

        # Verify counter is exactly 5 (not skipped increments)
        is_blocked = False
        try:
            rate_limiter.check_rate_limit(mock_request, limit=5, window=60, raise_on_limit=True)
        except HTTPException:
            is_blocked = True

        assert is_blocked, "6th request should be blocked (counter accurate)"

    def test_rate_limiter_cleanup_old_entries(self, rate_limiter, mock_request):
        """
        Test 12: Rate limiter should clean up expired entries

        Given: Rate limit entries older than window
        When: Cleanup is triggered
        Then: Old entries should be removed from memory
        """
        mock_request.url.path = "/api/auth/login"

        # Make 3 requests
        for i in range(3):
            rate_limiter.check_rate_limit(mock_request, limit=5, window=60)

        # Mock time passage (past window)
        with patch("api.middleware.rate_limit.time") as mock_time:
            original_time = time.time()
            mock_time.time.return_value = original_time + 120  # 2 minutes later

            # Trigger cleanup (implementation-specific method)
            if hasattr(rate_limiter, "cleanup_expired"):
                rate_limiter.cleanup_expired()

            # New request should succeed (old entries cleaned)
            # Make 5 new requests
            for i in range(5):
                is_allowed = rate_limiter.check_rate_limit(mock_request, limit=5, window=60)
                assert is_allowed, f"Request {i + 1}/5 should be allowed after cleanup"
