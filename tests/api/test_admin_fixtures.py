"""
Pure unit tests for admin authentication utilities used by conftest fixtures.

Tests TenantManager, JWTManager, and bcrypt password hashing WITHOUT any
database dependency. The actual conftest fixtures (admin_user, admin_token)
are implicitly validated by any test that consumes them.

No db_manager needed - zero risk of connection pool hangs (Handover 0495).
"""

import pytest
from passlib.hash import bcrypt

from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.tenant import TenantManager


class TestTenantKeyGeneration:
    """Verify TenantManager produces valid, unique tenant keys."""

    def test_generates_valid_key(self):
        key = TenantManager.generate_tenant_key()
        assert key is not None
        assert len(key) > 0
        assert TenantManager.validate_tenant_key(key)

    def test_keys_are_unique(self):
        key1 = TenantManager.generate_tenant_key()
        key2 = TenantManager.generate_tenant_key()
        assert key1 != key2

    def test_key_format(self):
        key = TenantManager.generate_tenant_key()
        assert key.startswith("tk_")
        assert len(key) == 35  # tk_ + 32 hex chars


class TestPasswordHashing:
    """Verify bcrypt hashing works for admin fixture passwords."""

    def test_hash_verifies(self):
        password = "admin_password"
        hashed = bcrypt.hash(password)
        assert hashed != password
        assert bcrypt.verify(password, hashed)

    def test_wrong_password_fails(self):
        hashed = bcrypt.hash("admin_password")
        assert not bcrypt.verify("wrong_password", hashed)


class TestJWTTokenCreation:
    """Verify JWTManager creates valid tokens with correct claims."""

    def test_creates_valid_token(self):
        tenant_key = TenantManager.generate_tenant_key()
        token = JWTManager.create_access_token(
            user_id=1,
            username="admin_test",
            role="admin",
            tenant_key=tenant_key,
        )
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_token_contains_claims(self):
        tenant_key = TenantManager.generate_tenant_key()
        token = JWTManager.create_access_token(
            user_id=42,
            username="admin_fixture_user",
            role="admin",
            tenant_key=tenant_key,
        )
        jwt_manager = JWTManager()
        payload = jwt_manager.verify_token(token)
        assert payload is not None
        assert payload.get("username") == "admin_fixture_user"
        assert payload.get("role") == "admin"
        assert payload.get("tenant_key") == tenant_key

    def test_admin_role_preserved(self):
        token = JWTManager.create_access_token(
            user_id=1,
            username="test",
            role="admin",
            tenant_key=TenantManager.generate_tenant_key(),
        )
        payload = JWTManager().verify_token(token)
        assert payload["role"] == "admin"

    def test_developer_role_preserved(self):
        token = JWTManager.create_access_token(
            user_id=1,
            username="test",
            role="developer",
            tenant_key=TenantManager.generate_tenant_key(),
        )
        payload = JWTManager().verify_token(token)
        assert payload["role"] == "developer"
