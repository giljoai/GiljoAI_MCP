"""
Tests for API key expiry checks in authentication paths.

Handover 0492: API Key Security Hardening - Expiry enforcement.

Tests cover two authentication paths:
1. MCPSessionManager.authenticate_api_key() in api/endpoints/mcp_session.py
2. get_current_user() in src/giljo_mcp/auth/dependencies.py

Each path must reject expired API keys while accepting:
- Keys with no expiry (expires_at IS NULL)
- Keys with future expiry (expires_at > now)
"""

import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from passlib.hash import bcrypt

from src.giljo_mcp.api_key_utils import (
    generate_api_key,
    get_key_prefix,
    hash_api_key,
    verify_api_key,
)
from src.giljo_mcp.models import APIKey, User


class TestMCPSessionManagerExpiryCheck:
    """Tests for MCPSessionManager.authenticate_api_key() expiry filtering."""

    @pytest_asyncio.fixture
    async def setup_user_and_keys(self, db_session):
        """Create a user with multiple API keys for testing expiry scenarios."""
        user = User(
            id=str(uuid4()),
            tenant_key="test_tenant_expiry",
            username="expiry_test_user",
            password_hash=bcrypt.hash("password"),
            is_active=True,
            org_id="00000000-0000-0000-0000-000000000001",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def create_api_key_with_expiry(self, db_session, setup_user_and_keys):
        """Helper to create an API key with a specific expires_at value."""
        user = setup_user_and_keys

        async def _create(expires_at=None, is_active=True):
            plaintext = generate_api_key()
            key_hash = hash_api_key(plaintext)
            key_prefix = get_key_prefix(plaintext)

            api_key = APIKey(
                id=str(uuid4()),
                tenant_key=user.tenant_key,
                user_id=user.id,
                name=f"Test Key {uuid4().hex[:6]}",
                key_hash=key_hash,
                key_prefix=key_prefix,
                permissions=["*"],
                is_active=is_active,
                expires_at=expires_at,
            )
            db_session.add(api_key)
            await db_session.commit()
            await db_session.refresh(api_key)
            return api_key, plaintext

        return _create

    @pytest.mark.asyncio
    async def test_active_key_no_expiry_authenticates(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """API key with no expiry (expires_at=None) should authenticate successfully."""
        from api.endpoints.mcp_session import MCPSessionManager

        api_key_record, plaintext = await create_api_key_with_expiry(expires_at=None)

        manager = MCPSessionManager(db_session)
        result = await manager.authenticate_api_key(plaintext)

        assert result is not None
        key_result, user_result = result
        assert key_result.id == api_key_record.id
        assert user_result.id == setup_user_and_keys.id

    @pytest.mark.asyncio
    async def test_active_key_future_expiry_authenticates(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """API key with future expiry should authenticate successfully."""
        from api.endpoints.mcp_session import MCPSessionManager

        future_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        api_key_record, plaintext = await create_api_key_with_expiry(expires_at=future_expiry)

        manager = MCPSessionManager(db_session)
        result = await manager.authenticate_api_key(plaintext)

        assert result is not None
        key_result, user_result = result
        assert key_result.id == api_key_record.id

    @pytest.mark.asyncio
    async def test_expired_key_rejected(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """API key that has expired should be rejected."""
        from api.endpoints.mcp_session import MCPSessionManager

        past_expiry = datetime.now(timezone.utc) - timedelta(hours=1)
        _, plaintext = await create_api_key_with_expiry(expires_at=past_expiry)

        manager = MCPSessionManager(db_session)
        result = await manager.authenticate_api_key(plaintext)

        assert result is None

    @pytest.mark.asyncio
    async def test_recently_expired_key_rejected(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """API key that expired just moments ago should be rejected."""
        from api.endpoints.mcp_session import MCPSessionManager

        just_expired = datetime.now(timezone.utc) - timedelta(seconds=30)
        _, plaintext = await create_api_key_with_expiry(expires_at=just_expired)

        manager = MCPSessionManager(db_session)
        result = await manager.authenticate_api_key(plaintext)

        assert result is None

    @pytest.mark.asyncio
    async def test_inactive_key_still_rejected(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """Inactive key with valid expiry should still be rejected (is_active check preserved)."""
        from api.endpoints.mcp_session import MCPSessionManager

        future_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        _, plaintext = await create_api_key_with_expiry(
            expires_at=future_expiry, is_active=False
        )

        manager = MCPSessionManager(db_session)
        result = await manager.authenticate_api_key(plaintext)

        assert result is None


class TestGetCurrentUserExpiryCheck:
    """Tests for get_current_user() API key expiry filtering in auth dependencies."""

    @pytest_asyncio.fixture
    async def setup_user_and_keys(self, db_session):
        """Create a user for dependency auth testing."""
        user = User(
            id=str(uuid4()),
            tenant_key="test_tenant_deps",
            username="deps_test_user",
            password_hash=bcrypt.hash("password"),
            is_active=True,
            org_id="00000000-0000-0000-0000-000000000001",
        )
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)
        return user

    @pytest_asyncio.fixture
    async def create_api_key_with_expiry(self, db_session, setup_user_and_keys):
        """Helper to create an API key with a specific expires_at value."""
        user = setup_user_and_keys

        async def _create(expires_at=None, is_active=True):
            plaintext = generate_api_key()
            key_hash = hash_api_key(plaintext)
            key_prefix = get_key_prefix(plaintext)

            api_key = APIKey(
                id=str(uuid4()),
                tenant_key=user.tenant_key,
                user_id=user.id,
                name=f"Dep Test Key {uuid4().hex[:6]}",
                key_hash=key_hash,
                key_prefix=key_prefix,
                permissions=["*"],
                is_active=is_active,
                expires_at=expires_at,
            )
            db_session.add(api_key)
            await db_session.commit()
            await db_session.refresh(api_key)
            return api_key, plaintext

        return _create

    def _make_request(self):
        """Create a mock FastAPI Request object."""
        request = MagicMock()
        request.url.path = "/api/test"
        return request

    @pytest.mark.asyncio
    async def test_valid_key_no_expiry_authenticates(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """API key with no expiry authenticates via get_current_user."""
        from src.giljo_mcp.auth.dependencies import get_current_user

        _, plaintext = await create_api_key_with_expiry(expires_at=None)

        request = self._make_request()
        user = await get_current_user(
            request=request,
            access_token=None,
            x_api_key=plaintext,
            authorization=None,
            db=db_session,
        )

        assert user is not None
        assert user.id == setup_user_and_keys.id

    @pytest.mark.asyncio
    async def test_valid_key_future_expiry_authenticates(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """API key with future expiry authenticates via get_current_user."""
        from src.giljo_mcp.auth.dependencies import get_current_user

        future_expiry = datetime.now(timezone.utc) + timedelta(days=90)
        _, plaintext = await create_api_key_with_expiry(expires_at=future_expiry)

        request = self._make_request()
        user = await get_current_user(
            request=request,
            access_token=None,
            x_api_key=plaintext,
            authorization=None,
            db=db_session,
        )

        assert user is not None
        assert user.id == setup_user_and_keys.id

    @pytest.mark.asyncio
    async def test_expired_key_rejected(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """Expired API key should fail authentication via get_current_user."""
        from fastapi import HTTPException
        from src.giljo_mcp.auth.dependencies import get_current_user

        past_expiry = datetime.now(timezone.utc) - timedelta(hours=2)
        _, plaintext = await create_api_key_with_expiry(expires_at=past_expiry)

        request = self._make_request()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=request,
                access_token=None,
                x_api_key=plaintext,
                authorization=None,
                db=db_session,
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_long_expired_key_rejected(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """API key that expired days ago should fail authentication."""
        from fastapi import HTTPException
        from src.giljo_mcp.auth.dependencies import get_current_user

        old_expiry = datetime.now(timezone.utc) - timedelta(days=30)
        _, plaintext = await create_api_key_with_expiry(expires_at=old_expiry)

        request = self._make_request()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=request,
                access_token=None,
                x_api_key=plaintext,
                authorization=None,
                db=db_session,
            )

        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_inactive_key_with_valid_expiry_rejected(
        self, db_session, setup_user_and_keys, create_api_key_with_expiry
    ):
        """Inactive (revoked) key with valid expiry should still fail."""
        from fastapi import HTTPException
        from src.giljo_mcp.auth.dependencies import get_current_user

        future_expiry = datetime.now(timezone.utc) + timedelta(days=30)
        _, plaintext = await create_api_key_with_expiry(
            expires_at=future_expiry, is_active=False
        )

        request = self._make_request()
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(
                request=request,
                access_token=None,
                x_api_key=plaintext,
                authorization=None,
                db=db_session,
            )

        assert exc_info.value.status_code == 401
