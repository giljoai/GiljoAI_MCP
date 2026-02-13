"""
Tests for API Key Security Hardening (Handover 0492).

Covers:
- 5-key limit enforcement per user
- 90-day expiry on newly created keys
- expires_at field in ApiKeyInfo and ApiKeyCreateResult schemas
- expires_at returned by list_api_keys

TDD: Tests written FIRST, implementation follows.
"""

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
from passlib.hash import bcrypt

from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.models.auth import APIKey, User
from src.giljo_mcp.models.organizations import Organization
from src.giljo_mcp.schemas.service_responses import ApiKeyCreateResult, ApiKeyInfo
from src.giljo_mcp.services.auth_service import AuthService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def auth_service(db_manager, db_session):
    """Create AuthService instance for testing with shared session."""
    return AuthService(
        db_manager=db_manager,
        websocket_manager=None,
        session=db_session,
    )


@pytest_asyncio.fixture
async def test_org(db_session):
    """Create test organization."""
    unique_id = str(uuid4())[:8]
    org = Organization(
        id=str(uuid4()),
        tenant_key=f"test_tenant_{unique_id}",
        name=f"Test Organization {unique_id}",
        slug=f"test-org-{unique_id}",
        is_active=True,
    )
    db_session.add(org)
    await db_session.commit()
    await db_session.refresh(org)
    return org


@pytest_asyncio.fixture
async def test_user(db_session, test_org):
    """Create test user with known credentials."""
    unique_id = str(uuid4())[:8]
    password = "Test1234!"
    user = User(
        id=str(uuid4()),
        username=f"testuser_{unique_id}",
        email=f"test_{unique_id}@example.com",
        full_name="Test User",
        password_hash=bcrypt.hash(password),
        role="developer",
        tenant_key=test_org.tenant_key,
        org_id=test_org.id,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, password


async def _create_api_key_in_db(
    db_session, user, *, is_active: bool = True, expires_at=None
) -> APIKey:
    """Helper to create an API key directly in the database."""
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
        is_active=is_active,
        created_at=datetime.now(timezone.utc),
        expires_at=expires_at,
    )
    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)
    return api_key


# ---------------------------------------------------------------------------
# Tests: 5-key limit
# ---------------------------------------------------------------------------


class TestApiKeyLimit:
    """Tests for the 5 active API key limit per user."""

    @pytest.mark.asyncio
    async def test_create_api_key_under_limit(self, auth_service, test_user):
        """Creating a key when user has fewer than 5 should succeed."""
        user, _ = test_user

        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="Key 1", permissions=["*"]
        )

        assert isinstance(result, ApiKeyCreateResult)
        assert result.name == "Key 1"

    @pytest.mark.asyncio
    async def test_create_api_key_at_limit_raises(self, auth_service, test_user, db_session):
        """Creating a 6th active key should raise ValidationError."""
        user, _ = test_user

        # Create 5 active keys directly in DB
        for i in range(5):
            await _create_api_key_in_db(
                db_session,
                user,
                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            )

        with pytest.raises(ValidationError, match="Maximum of 5 active API keys"):
            await auth_service.create_api_key(
                user_id=user.id, tenant_key=user.tenant_key, name="Key 6", permissions=["*"]
            )

    @pytest.mark.asyncio
    async def test_revoked_keys_not_counted_toward_limit(
        self, auth_service, test_user, db_session
    ):
        """Revoked (inactive) keys should not count toward the 5-key limit."""
        user, _ = test_user

        # Create 5 revoked keys
        for i in range(5):
            await _create_api_key_in_db(
                db_session,
                user,
                is_active=False,
                expires_at=datetime.now(timezone.utc) + timedelta(days=90),
            )

        # Should succeed because revoked keys are not counted
        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="New Key", permissions=["*"]
        )
        assert isinstance(result, ApiKeyCreateResult)

    @pytest.mark.asyncio
    async def test_expired_keys_not_counted_toward_limit(
        self, auth_service, test_user, db_session
    ):
        """Expired keys (past expires_at) should not count toward the 5-key limit."""
        user, _ = test_user

        # Create 5 active but expired keys
        for i in range(5):
            await _create_api_key_in_db(
                db_session,
                user,
                is_active=True,
                expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            )

        # Should succeed because expired keys are not counted
        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="New Key", permissions=["*"]
        )
        assert isinstance(result, ApiKeyCreateResult)


# ---------------------------------------------------------------------------
# Tests: 90-day expiry
# ---------------------------------------------------------------------------


class TestApiKeyExpiry:
    """Tests for 90-day expiry on newly created API keys."""

    @pytest.mark.asyncio
    async def test_new_key_has_expires_at(self, auth_service, test_user):
        """Newly created API key should have expires_at set."""
        user, _ = test_user

        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="Expiry Test", permissions=["*"]
        )

        assert result.expires_at is not None

    @pytest.mark.asyncio
    async def test_new_key_expires_in_90_days(self, auth_service, test_user):
        """Newly created API key should expire approximately 90 days from now."""
        user, _ = test_user
        before = datetime.now(timezone.utc)

        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="90-Day Test", permissions=["*"]
        )

        after = datetime.now(timezone.utc)
        expires_at = datetime.fromisoformat(result.expires_at)
        expected_min = before + timedelta(days=89, hours=23)
        expected_max = after + timedelta(days=90, minutes=1)
        assert expected_min <= expires_at <= expected_max


# ---------------------------------------------------------------------------
# Tests: Schema fields
# ---------------------------------------------------------------------------


class TestApiKeySchemaFields:
    """Tests for expires_at in ApiKeyInfo and ApiKeyCreateResult."""

    def test_api_key_info_has_expires_at_field(self):
        """ApiKeyInfo schema should accept expires_at."""
        info = ApiKeyInfo(
            id="test-id",
            name="Test Key",
            key_prefix="gk_test_",
            permissions=["*"],
            is_active=True,
            expires_at="2026-05-13T00:00:00+00:00",
        )
        assert info.expires_at == "2026-05-13T00:00:00+00:00"

    def test_api_key_info_expires_at_defaults_to_none(self):
        """ApiKeyInfo expires_at should default to None."""
        info = ApiKeyInfo(
            id="test-id",
            name="Test Key",
            key_prefix="gk_test_",
            permissions=["*"],
            is_active=True,
        )
        assert info.expires_at is None

    def test_api_key_create_result_has_expires_at_field(self):
        """ApiKeyCreateResult schema should accept expires_at."""
        result = ApiKeyCreateResult(
            id="test-id",
            name="Test Key",
            api_key="gk_raw_key_value",
            key_prefix="gk_test_",
            key_hash="hashed_value",
            permissions=["*"],
            expires_at="2026-05-13T00:00:00+00:00",
        )
        assert result.expires_at == "2026-05-13T00:00:00+00:00"

    def test_api_key_create_result_expires_at_defaults_to_none(self):
        """ApiKeyCreateResult expires_at should default to None."""
        result = ApiKeyCreateResult(
            id="test-id",
            name="Test Key",
            api_key="gk_raw_key_value",
            key_prefix="gk_test_",
            key_hash="hashed_value",
            permissions=["*"],
        )
        assert result.expires_at is None


# ---------------------------------------------------------------------------
# Tests: list_api_keys returns expires_at
# ---------------------------------------------------------------------------


class TestListApiKeysExpiresAt:
    """Tests for expires_at in list_api_keys response."""

    @pytest.mark.asyncio
    async def test_list_keys_includes_expires_at(self, auth_service, test_user, db_session):
        """list_api_keys should include expires_at for each key."""
        user, _ = test_user
        future_expiry = datetime.now(timezone.utc) + timedelta(days=90)
        await _create_api_key_in_db(db_session, user, expires_at=future_expiry)

        result = await auth_service.list_api_keys(user.id, include_revoked=False)

        assert len(result) == 1
        assert result[0].expires_at is not None

    @pytest.mark.asyncio
    async def test_list_keys_expires_at_none_for_legacy(self, auth_service, test_user, db_session):
        """list_api_keys should return None expires_at for keys without expiry."""
        user, _ = test_user
        await _create_api_key_in_db(db_session, user, expires_at=None)

        result = await auth_service.list_api_keys(user.id, include_revoked=False)

        assert len(result) == 1
        assert result[0].expires_at is None

    @pytest.mark.asyncio
    async def test_created_key_appears_in_list_with_expiry(self, auth_service, test_user):
        """A key created via create_api_key should appear in list_api_keys with expires_at."""
        user, _ = test_user

        create_result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="Listed Key", permissions=["*"]
        )

        list_result = await auth_service.list_api_keys(user.id, include_revoked=False)

        assert len(list_result) >= 1
        matching = [k for k in list_result if k.name == "Listed Key"]
        assert len(matching) == 1
        assert matching[0].expires_at is not None
        assert matching[0].expires_at == create_result.expires_at
