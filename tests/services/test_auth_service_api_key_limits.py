# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tests for API Key Security Hardening (Handover 0492).

Covers:
- unlimited active keys per user (the prior 5-key cap was removed — BE-6147)
- 90-day expiry on newly created keys
- expires_at field in ApiKeyInfo and ApiKeyCreateResult schemas
- expires_at returned by list_api_keys

TDD: Tests written FIRST, implementation follows.
"""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.models.auth import APIKey, User
from giljo_mcp.models.notifications import Notification
from giljo_mcp.models.organizations import Organization
from giljo_mcp.schemas.service_responses import ApiKeyCreateResult, ApiKeyInfo
from giljo_mcp.services.auth_service import AuthService
from giljo_mcp.services.notification_service import NotificationService


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
async def notification_service(db_manager, db_session):
    """NotificationService sharing the test session (rollback isolation)."""
    return NotificationService(
        db_manager=db_manager,
        websocket_manager=None,
        session=db_session,
    )


async def _count_open_expiry_notifications(db_session, api_key_id: str) -> int:
    """Count un-resolved api_key.expiring_soon notifications for a key."""
    stmt = select(Notification).where(
        Notification.dedupe_key == f"api_key.expiring_soon:{api_key_id}",
        Notification.resolved_at.is_(None),
    )
    result = await db_session.execute(stmt)
    return len(list(result.scalars().all()))


async def _get_expiry_notification(db_session, api_key_id: str) -> Notification | None:
    """Fetch the api_key.expiring_soon notification for a key (any state)."""
    stmt = select(Notification).where(Notification.dedupe_key == f"api_key.expiring_soon:{api_key_id}")
    result = await db_session.execute(stmt)
    return result.scalars().first()


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
        password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        role="developer",
        tenant_key=test_org.tenant_key,
        org_id=test_org.id,
        is_active=True,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, password


async def _create_api_key_in_db(db_session, user, *, is_active: bool = True, expires_at=None) -> APIKey:
    """Helper to create an API key directly in the database."""
    unique_id = str(uuid4())[:8]
    raw_key = f"gk_test_key_{unique_id}_{uuid4().hex[:12]}"
    api_key = APIKey(
        id=str(uuid4()),
        tenant_key=user.tenant_key,
        user_id=user.id,
        name=f"Test API Key {unique_id}",
        key_hash=bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        key_prefix="gk_test_key_",
        permissions=["*"],
        is_active=is_active,
        created_at=datetime.now(UTC),
        expires_at=expires_at,
    )
    db_session.add(api_key)
    await db_session.commit()
    await db_session.refresh(api_key)
    return api_key


# ---------------------------------------------------------------------------
# Tests: unlimited active keys (the prior 5-key cap was removed — BE-6147)
# ---------------------------------------------------------------------------


class TestApiKeyLimit:
    """Active API keys per user are UNLIMITED (the prior 5-key cap was removed
    in BE-6147). Sprawl control remains via 90-day expiry + revocation, not a
    count cap. Keys stay scoped by tenant_key + user_id (ADR-009 Teams-readiness).
    """

    @pytest.mark.asyncio
    async def test_create_api_key_succeeds(self, auth_service, test_user):
        """Creating a key for a user with no existing keys succeeds."""
        user, _ = test_user

        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="Key 1", permissions=["*"]
        )

        assert isinstance(result, ApiKeyCreateResult)
        assert result.name == "Key 1"

    @pytest.mark.asyncio
    async def test_create_api_key_unlimited(self, auth_service, test_user, db_session):
        """A 6th (and 10th) active key now SUCCEEDS — the 5-key cap is gone."""
        user, _ = test_user

        # Seed 5 active, unexpired keys directly in the DB (the old at-cap count).
        for _i in range(5):
            await _create_api_key_in_db(
                db_session,
                user,
                expires_at=datetime.now(UTC) + timedelta(days=90),
            )

        # 6th active key: previously rejected with "Maximum of 5..." — must now succeed.
        sixth = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="Key 6", permissions=["*"]
        )
        assert isinstance(sixth, ApiKeyCreateResult)
        assert sixth.name == "Key 6"

        # Keep going well past the old cap — keys 7..10 also succeed.
        for n in range(7, 11):
            result = await auth_service.create_api_key(
                user_id=user.id, tenant_key=user.tenant_key, name=f"Key {n}", permissions=["*"]
            )
            assert isinstance(result, ApiKeyCreateResult)

        # 10 active keys now coexist for this user — no cap.
        active = await auth_service.list_api_keys(user.id, include_revoked=False)
        assert len([k for k in active if k.is_active]) == 10


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
        before = datetime.now(UTC)

        result = await auth_service.create_api_key(
            user_id=user.id, tenant_key=user.tenant_key, name="90-Day Test", permissions=["*"]
        )

        after = datetime.now(UTC)
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
        future_expiry = datetime.now(UTC) + timedelta(days=90)
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


# ---------------------------------------------------------------------------
# Tests: 7-day expiry notification scan (IMP-5037a Phase 3)
# ---------------------------------------------------------------------------


class TestApiKeyExpiryNotificationScan:
    """scan_expiring_api_keys + auto-clear hooks via NotificationService."""

    @pytest.mark.asyncio
    async def test_scan_creates_notification_for_key_expiring_in_5_days(
        self, auth_service, notification_service, test_user, db_session
    ):
        """A key expiring in 5 days should produce one expiry notification."""
        user, _ = test_user
        key = await _create_api_key_in_db(db_session, user, expires_at=datetime.now(UTC) + timedelta(days=5))

        result = await auth_service.scan_expiring_api_keys(
            tenant_key=user.tenant_key, notification_service=notification_service
        )

        assert any(api_key_id == key.id for (_uid, api_key_id, _exp, _name) in result)
        assert await _count_open_expiry_notifications(db_session, key.id) == 1

    @pytest.mark.asyncio
    async def test_scan_skips_revoked_key_expiring_in_5_days(
        self, auth_service, notification_service, test_user, db_session
    ):
        """A revoked key expiring in 5 days should NOT produce a notification."""
        user, _ = test_user
        key = await _create_api_key_in_db(
            db_session,
            user,
            is_active=False,
            expires_at=datetime.now(UTC) + timedelta(days=5),
        )

        await auth_service.scan_expiring_api_keys(tenant_key=user.tenant_key, notification_service=notification_service)

        assert await _count_open_expiry_notifications(db_session, key.id) == 0

    @pytest.mark.asyncio
    async def test_scan_skips_key_expiring_in_30_days(self, auth_service, notification_service, test_user, db_session):
        """A key expiring in 30 days is outside the 7-day window — no notification."""
        user, _ = test_user
        key = await _create_api_key_in_db(db_session, user, expires_at=datetime.now(UTC) + timedelta(days=30))

        await auth_service.scan_expiring_api_keys(tenant_key=user.tenant_key, notification_service=notification_service)

        assert await _count_open_expiry_notifications(db_session, key.id) == 0

    @pytest.mark.asyncio
    async def test_scan_twice_dedupes_to_one_notification(
        self, auth_service, notification_service, test_user, db_session
    ):
        """Re-running the scan must not duplicate the expiry notification."""
        user, _ = test_user
        key = await _create_api_key_in_db(db_session, user, expires_at=datetime.now(UTC) + timedelta(days=5))

        await auth_service.scan_expiring_api_keys(tenant_key=user.tenant_key, notification_service=notification_service)
        await auth_service.scan_expiring_api_keys(tenant_key=user.tenant_key, notification_service=notification_service)

        assert await _count_open_expiry_notifications(db_session, key.id) == 1

    @pytest.mark.asyncio
    async def test_regenerate_resolves_prior_notification(
        self, auth_service, notification_service, test_user, db_session
    ):
        """Creating a replacement key resolves the prior key's expiry notification."""
        user, _ = test_user
        key = await _create_api_key_in_db(db_session, user, expires_at=datetime.now(UTC) + timedelta(days=5))
        await auth_service.scan_expiring_api_keys(tenant_key=user.tenant_key, notification_service=notification_service)
        assert await _count_open_expiry_notifications(db_session, key.id) == 1

        await auth_service.create_api_key(
            user_id=user.id,
            tenant_key=user.tenant_key,
            name="Regenerated Key",
            permissions=["*"],
            replaces_key_id=key.id,
            notification_service=notification_service,
        )

        notification = await _get_expiry_notification(db_session, key.id)
        assert notification is not None
        assert notification.resolved_at is not None
        assert await _count_open_expiry_notifications(db_session, key.id) == 0

    @pytest.mark.asyncio
    async def test_revoke_resolves_notification(self, auth_service, notification_service, test_user, db_session):
        """Revoking a key resolves its expiry notification."""
        user, _ = test_user
        key = await _create_api_key_in_db(db_session, user, expires_at=datetime.now(UTC) + timedelta(days=5))
        await auth_service.scan_expiring_api_keys(tenant_key=user.tenant_key, notification_service=notification_service)
        assert await _count_open_expiry_notifications(db_session, key.id) == 1

        await auth_service.revoke_api_key(key.id, user.id, notification_service=notification_service)

        notification = await _get_expiry_notification(db_session, key.id)
        assert notification is not None
        assert notification.resolved_at is not None
        assert await _count_open_expiry_notifications(db_session, key.id) == 0
