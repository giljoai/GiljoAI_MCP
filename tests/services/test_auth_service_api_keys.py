"""
Tests for AuthService - API key management.

Split from test_auth_service.py. Contains:
- TestListAPIKeys: API key listing (active only, including revoked, empty)
- TestCreateAPIKey: API key creation (success, custom permissions)
- TestRevokeAPIKey: API key revocation (success, not found, wrong user)

Handover 0731c: Updated for typed service returns (ApiKeyInfo, ApiKeyCreateResult).
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from passlib.hash import bcrypt
from sqlalchemy import select

from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models.auth import APIKey
from src.giljo_mcp.schemas.service_responses import (
    ApiKeyCreateResult,
    ApiKeyInfo,
)


# Fixtures local to this file


@pytest_asyncio.fixture
async def auth_api_key(db_session, auth_user_with_password):
    """Create test API key"""
    user, _ = auth_user_with_password
    unique_id = str(uuid4())[:8]
    raw_key = f"gk_test_key_{unique_id}_{uuid4().hex[:12]}"
    api_key = APIKey(
        id=str(uuid4()),
        tenant_key=user.tenant_key,
        user_id=user.id,
        name=f"Test API Key {unique_id}",
        key_hash=bcrypt.hash(raw_key),
        key_prefix="gk_test_key_",
        permissions=["*"],
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)
    return api_key, raw_key


# Test Cases


class TestListAPIKeys:
    """Tests for list_api_keys method - returns list[ApiKeyInfo]"""

    @pytest.mark.asyncio
    async def test_list_api_keys_active_only(self, auth_service, auth_user_with_password, auth_api_key):
        """Test listing only active API keys returns list[ApiKeyInfo]"""
        user, _ = auth_user_with_password

        result = await auth_service.list_api_keys(user.id, include_revoked=False)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ApiKeyInfo)
        assert result[0].name.startswith("Test API Key")  # Dynamic unique names
        assert result[0].is_active is True

    @pytest.mark.asyncio
    async def test_list_api_keys_include_revoked(self, auth_service, auth_user_with_password, auth_api_key, db_session):
        """Test listing API keys including revoked ones"""
        user, _ = auth_user_with_password
        api_key, _ = auth_api_key

        # Revoke the API key
        api_key.is_active = False
        api_key.revoked_at = datetime.now(timezone.utc)
        await db_session.commit()

        result = await auth_service.list_api_keys(user.id, include_revoked=True)

        assert isinstance(result, list)
        assert len(result) == 1
        assert isinstance(result[0], ApiKeyInfo)
        assert result[0].is_active is False
        assert result[0].revoked_at is not None

    @pytest.mark.asyncio
    async def test_list_api_keys_empty(self, auth_service, auth_user_with_password):
        """Test listing API keys when user has none returns empty list"""
        result = await auth_service.list_api_keys("user-no-keys", include_revoked=False)

        assert isinstance(result, list)
        assert len(result) == 0


class TestCreateAPIKey:
    """Tests for create_api_key method - returns ApiKeyCreateResult"""

    @pytest.mark.asyncio
    async def test_create_api_key_success(self, auth_service, auth_user_with_password):
        """Test creating new API key returns ApiKeyCreateResult"""
        user, _ = auth_user_with_password

        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="New Test Key", permissions=["*"]
        )

        # Typed return: ApiKeyCreateResult with attribute access
        assert isinstance(result, ApiKeyCreateResult)
        assert result.name == "New Test Key"
        assert result.api_key.startswith("gk_")  # Raw key returned once
        assert result.key_prefix is not None
        assert result.key_hash is not None  # Hashed version stored

    @pytest.mark.asyncio
    async def test_create_api_key_custom_permissions(self, auth_service, auth_user_with_password):
        """Test creating API key with custom permissions"""
        user, _ = auth_user_with_password

        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="Limited Key", permissions=["read", "write"]
        )

        assert isinstance(result, ApiKeyCreateResult)
        assert result.permissions == ["read", "write"]


class TestRevokeAPIKey:
    """Tests for revoke_api_key method"""

    @pytest.mark.asyncio
    async def test_revoke_api_key_success(self, auth_service, auth_user_with_password, auth_api_key, db_session):
        """Test revoking an active API key"""
        user, _ = auth_user_with_password
        api_key, _ = auth_api_key

        # Returns None on success
        result = await auth_service.revoke_api_key(api_key.id, user.id)
        assert result is None

        # Verify in database
        stmt = select(APIKey).where(APIKey.id == api_key.id)
        result_db = await db_session.execute(stmt)
        revoked_key = result_db.scalar_one()
        assert revoked_key.is_active is False
        assert revoked_key.revoked_at is not None

    @pytest.mark.asyncio
    async def test_revoke_api_key_not_found(self, auth_service, auth_user_with_password):
        """Test revoking non-existent API key raises ResourceNotFoundError"""
        user, _ = auth_user_with_password

        with pytest.raises(ResourceNotFoundError):
            await auth_service.revoke_api_key("nonexistent-key-id", user.id)

    @pytest.mark.asyncio
    async def test_revoke_api_key_wrong_user(self, auth_service, auth_api_key, db_session):
        """Test revoking API key belonging to another user fails"""
        api_key, _ = auth_api_key

        with pytest.raises(ResourceNotFoundError):
            await auth_service.revoke_api_key(api_key.id, "wrong-user-id")
