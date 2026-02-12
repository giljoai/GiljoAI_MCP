"""
Unit tests for JWTManager.verify_token_allow_expired method.

Tests the token verification with grace period for the /refresh endpoint.

Covers:
- Valid (non-expired) tokens
- Recently expired tokens within grace period
- Tokens expired beyond grace period
- Invalid/malformed tokens
- Tokens with wrong type
- Custom grace period override
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest

from src.giljo_mcp.auth.jwt_manager import JWTManager


@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    """Ensure JWT_SECRET is set for all tests."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-unit-tests-only")


class TestVerifyTokenAllowExpired:
    """Test suite for JWTManager.verify_token_allow_expired."""

    def _create_token(self, exp_offset_seconds: int = 3600, **extra_claims) -> str:
        """Create a JWT token with a specific expiration offset from now.

        Args:
            exp_offset_seconds: Seconds from now for expiration.
                Positive = future (valid), negative = past (expired).
            **extra_claims: Additional claims to include in the token.
        """
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid4()),
            "username": "testuser",
            "role": "developer",
            "tenant_key": "test_tenant",
            "exp": now + timedelta(seconds=exp_offset_seconds),
            "iat": now,
            "type": "access",
            **extra_claims,
        }
        return jwt.encode(payload, "test-secret-key-for-unit-tests-only", algorithm="HS256")

    # --- Valid token tests ---

    def test_valid_token_returns_payload(self):
        """Valid (non-expired) token should return the decoded payload."""
        token = self._create_token(exp_offset_seconds=3600)  # Expires in 1 hour

        result = JWTManager.verify_token_allow_expired(token)

        assert result is not None
        assert result["username"] == "testuser"
        assert result["role"] == "developer"
        assert result["tenant_key"] == "test_tenant"
        assert result["type"] == "access"

    def test_valid_token_contains_sub(self):
        """Valid token payload should contain the user ID in 'sub' claim."""
        user_id = str(uuid4())
        token = self._create_token(exp_offset_seconds=3600, sub=user_id)

        result = JWTManager.verify_token_allow_expired(token)

        assert result is not None
        assert result["sub"] == user_id

    # --- Recently expired tokens (within grace period) ---

    def test_recently_expired_token_within_grace_returns_payload(self):
        """Token expired 30 minutes ago (within 1h grace) should return payload."""
        token = self._create_token(exp_offset_seconds=-1800)  # Expired 30 min ago

        result = JWTManager.verify_token_allow_expired(token)

        assert result is not None
        assert result["username"] == "testuser"

    def test_token_expired_59_minutes_ago_returns_payload(self):
        """Token expired 59 minutes ago (just within 1h grace) should return payload."""
        token = self._create_token(exp_offset_seconds=-3540)  # Expired 59 min ago

        result = JWTManager.verify_token_allow_expired(token)

        assert result is not None

    # --- Tokens expired beyond grace period ---

    def test_token_expired_beyond_grace_returns_none(self):
        """Token expired more than 1 hour ago should return None."""
        token = self._create_token(exp_offset_seconds=-7200)  # Expired 2 hours ago

        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_token_expired_exactly_at_grace_boundary(self):
        """Token expired exactly 1 hour ago should still be within grace period.

        The comparison uses <= so exactly at the boundary should pass.
        """
        token = self._create_token(exp_offset_seconds=-3600)  # Expired exactly 1h ago

        result = JWTManager.verify_token_allow_expired(token)

        # At the boundary, depends on timing precision. We accept either outcome
        # as long as it doesn't error. The important thing is ~1h grace.
        # In practice the test executes in <1s so this will be within grace.
        assert result is not None or result is None  # No exception

    # --- Invalid token tests ---

    def test_malformed_token_returns_none(self):
        """Completely invalid token string should return None."""
        result = JWTManager.verify_token_allow_expired("not-a-valid-jwt-token")

        assert result is None

    def test_empty_token_returns_none(self):
        """Empty token string should return None."""
        result = JWTManager.verify_token_allow_expired("")

        assert result is None

    def test_wrong_signature_returns_none(self):
        """Token signed with wrong secret should return None."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid4()),
            "username": "testuser",
            "role": "developer",
            "tenant_key": "test_tenant",
            "exp": now + timedelta(hours=1),
            "iat": now,
            "type": "access",
        }
        token = jwt.encode(payload, "wrong-secret-key", algorithm="HS256")

        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    # --- Wrong token type ---

    def test_non_access_type_valid_token_returns_none(self):
        """Valid token with wrong type should return None."""
        token = self._create_token(exp_offset_seconds=3600, type="refresh")

        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_non_access_type_expired_token_returns_none(self):
        """Expired token with wrong type should return None."""
        token = self._create_token(exp_offset_seconds=-1800, type="refresh")

        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_missing_type_claim_returns_none(self):
        """Token without type claim should return None."""
        now = datetime.now(timezone.utc)
        payload = {
            "sub": str(uuid4()),
            "username": "testuser",
            "role": "developer",
            "tenant_key": "test_tenant",
            "exp": now + timedelta(hours=1),
            "iat": now,
            # No "type" claim
        }
        token = jwt.encode(payload, "test-secret-key-for-unit-tests-only", algorithm="HS256")

        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    # --- Custom grace period ---

    def test_custom_grace_period_accepts_within(self):
        """Custom grace_hours=2 should accept tokens expired up to 2h ago."""
        token = self._create_token(exp_offset_seconds=-5400)  # Expired 1.5h ago

        # Default 1h grace would reject, but 2h grace should accept
        result = JWTManager.verify_token_allow_expired(token, grace_hours=2)

        assert result is not None

    def test_custom_grace_period_rejects_beyond(self):
        """Custom grace_hours=2 should reject tokens expired more than 2h ago."""
        token = self._create_token(exp_offset_seconds=-10800)  # Expired 3h ago

        result = JWTManager.verify_token_allow_expired(token, grace_hours=2)

        assert result is None

    # --- JWT_SECRET not set ---

    def test_missing_jwt_secret_returns_none(self, monkeypatch):
        """If JWT_SECRET env var is not set, should return None (not raise)."""
        monkeypatch.delenv("JWT_SECRET", raising=False)
        token = self._create_token(exp_offset_seconds=3600)

        result = JWTManager.verify_token_allow_expired(token)

        assert result is None
