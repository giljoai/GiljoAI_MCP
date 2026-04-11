# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for JWTManager.verify_token_allow_expired method.

TDD: These tests are written FIRST, before the implementation.
They verify the grace-period token verification used for silent refresh.

Test matrix:
- Valid (non-expired) access token -> returns payload
- Expired within grace period -> returns payload
- Expired beyond grace period -> returns None
- Invalid token type (not "access") -> returns None
- Tampered/invalid token -> returns None
- Missing secret key -> returns None
- Custom grace_hours override -> respected
- Edge cases: exactly at grace boundary, zero grace period
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import jwt
import pytest


@pytest.fixture(autouse=True)
def set_jwt_secret(monkeypatch):
    """Ensure JWT_SECRET is set for all tests in this module."""
    monkeypatch.setenv("JWT_SECRET", "test-secret-key-for-unit-tests")


@pytest.fixture
def sample_user_id():
    return uuid4()


@pytest.fixture
def secret_key():
    return "test-secret-key-for-unit-tests"


def _make_token(
    secret_key: str,
    user_id,
    expire_delta: timedelta | None = None,
    token_type: str = "access",
    algorithm: str = "HS256",
) -> str:
    """Helper to create a JWT with a specific expiration offset."""
    now = datetime.now(timezone.utc)
    expire = now + (expire_delta if expire_delta is not None else timedelta(hours=24))
    payload = {
        "sub": str(user_id),
        "username": "testuser",
        "role": "developer",
        "tenant_key": "test-tenant",
        "exp": expire,
        "iat": now,
        "type": token_type,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


class TestVerifyTokenAllowExpired:
    """Tests for JWTManager.verify_token_allow_expired."""

    def test_valid_non_expired_token_returns_payload(self, sample_user_id, secret_key):
        """A valid, non-expired access token should return its payload."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(hours=1))
        result = JWTManager.verify_token_allow_expired(token)

        assert result is not None
        assert result["sub"] == str(sample_user_id)
        assert result["username"] == "testuser"
        assert result["role"] == "developer"
        assert result["tenant_key"] == "test-tenant"
        assert result["type"] == "access"

    def test_expired_within_grace_period_returns_payload(self, sample_user_id, secret_key):
        """A token expired 30 minutes ago (within 1-hour grace) returns payload."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(minutes=-30))
        result = JWTManager.verify_token_allow_expired(token)

        assert result is not None
        assert result["sub"] == str(sample_user_id)
        assert result["type"] == "access"

    def test_expired_beyond_grace_period_returns_none(self, sample_user_id, secret_key):
        """A token expired 2 hours ago (beyond 1-hour grace) returns None."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(hours=-2))
        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_expired_exactly_at_grace_boundary_returns_payload(self, sample_user_id, secret_key):
        """A token expired exactly 1 hour ago (at boundary) returns payload.

        The condition is (now - exp) <= timedelta(hours=grace), so exactly
        at the boundary should still pass.
        """
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        # Use slightly less than 1 hour to avoid timing flakiness
        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(minutes=-59, seconds=-50))
        result = JWTManager.verify_token_allow_expired(token)

        assert result is not None

    def test_expired_just_beyond_grace_boundary_returns_none(self, sample_user_id, secret_key):
        """A token expired 61 minutes ago (just beyond grace) returns None."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(minutes=-61))
        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_non_access_token_type_returns_none(self, sample_user_id, secret_key):
        """A token with type != 'access' (e.g. 'refresh') returns None."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = _make_token(secret_key, sample_user_id, token_type="refresh")
        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_expired_non_access_token_type_returns_none(self, sample_user_id, secret_key):
        """An expired token with wrong type returns None (not payload)."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = _make_token(
            secret_key,
            sample_user_id,
            expire_delta=timedelta(minutes=-30),
            token_type="refresh",
        )
        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_tampered_token_returns_none(self, sample_user_id, secret_key):
        """A token signed with wrong key returns None."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = _make_token("wrong-secret-key", sample_user_id, expire_delta=timedelta(hours=1))
        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_malformed_token_returns_none(self):
        """A completely invalid token string returns None."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        result = JWTManager.verify_token_allow_expired("not.a.valid.jwt")
        assert result is None

    def test_empty_token_returns_none(self):
        """An empty string returns None."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        result = JWTManager.verify_token_allow_expired("")
        assert result is None

    def test_missing_secret_key_returns_none(self, sample_user_id, monkeypatch):
        """When no secret key is configured, returns None (not an exception)."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        monkeypatch.delenv("JWT_SECRET", raising=False)
        monkeypatch.delenv("GILJO_MCP_SECRET_KEY", raising=False)
        monkeypatch.delenv("SECRET_KEY", raising=False)

        # Create a token with any key - it won't matter since secret is missing
        token = _make_token("any-key", sample_user_id, expire_delta=timedelta(hours=1))
        result = JWTManager.verify_token_allow_expired(token)

        assert result is None

    def test_custom_grace_hours_override(self, sample_user_id, secret_key):
        """Custom grace_hours parameter overrides the class default."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        # Token expired 3 hours ago - beyond default 1-hour grace
        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(hours=-3))

        # With default grace (1 hour), should return None
        assert JWTManager.verify_token_allow_expired(token) is None

        # With 4-hour grace, should return payload
        result = JWTManager.verify_token_allow_expired(token, grace_hours=4)
        assert result is not None
        assert result["sub"] == str(sample_user_id)

    def test_zero_grace_hours_rejects_all_expired(self, sample_user_id, secret_key):
        """With grace_hours=0, any expired token returns None."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        # Token expired 1 second ago
        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(seconds=-1))
        result = JWTManager.verify_token_allow_expired(token, grace_hours=0)

        assert result is None

    def test_class_attribute_exists(self):
        """REFRESH_GRACE_PERIOD_HOURS class attribute should be 1."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        assert hasattr(JWTManager, "REFRESH_GRACE_PERIOD_HOURS")
        assert JWTManager.REFRESH_GRACE_PERIOD_HOURS == 1

    def test_returns_dict_type(self, sample_user_id, secret_key):
        """Return type should be dict when successful."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(hours=1))
        result = JWTManager.verify_token_allow_expired(token)

        assert isinstance(result, dict)

    def test_does_not_raise_http_exception(self, sample_user_id, secret_key):
        """Unlike verify_token, this method should never raise HTTPException."""
        from fastapi import HTTPException

        from src.giljo_mcp.auth.jwt_manager import JWTManager

        # Expired beyond grace
        token = _make_token(secret_key, sample_user_id, expire_delta=timedelta(hours=-5))
        # Should return None, not raise
        try:
            result = JWTManager.verify_token_allow_expired(token)
            assert result is None
        except HTTPException:
            pytest.fail("verify_token_allow_expired should not raise HTTPException")

    def test_token_created_by_create_access_token(self, sample_user_id):
        """Tokens created by create_access_token should be accepted."""
        from src.giljo_mcp.auth.jwt_manager import JWTManager

        token = JWTManager.create_access_token(
            user_id=sample_user_id,
            username="testuser",
            role="developer",
            tenant_key="test-tenant",
        )
        result = JWTManager.verify_token_allow_expired(token)

        assert result is not None
        assert result["sub"] == str(sample_user_id)
        assert result["username"] == "testuser"
