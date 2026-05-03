# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
AUTH-EMAIL Phase 4 -- Dual-lookup for PIN recovery + first-login endpoints.

Tests that verify-pin, verify-pin-and-reset-password, and check-first-login
accept either username OR email as the identifier (wire field still named
`username`), mirroring the Phase 1 dual-lookup pattern shipped in
AuthService.authenticate_user (commit 42842d18, handover af53e62b).

Also exercises the new AuthRepository helper
`get_user_by_username_or_email` that encapsulates the pattern.
"""

import os
from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import bcrypt
import pytest
import pytest_asyncio
from fastapi import HTTPException


# Snapshot DATABASE_URL before importing api.* (which sets it to the
# production config via api/__init__.py -> create_app()). Restoring
# immediately after import keeps the test fixtures pointed at giljo_mcp_test.
_db_url_before = os.environ.get("DATABASE_URL")

from api.endpoints.auth_models import (  # noqa: E402
    CheckFirstLoginRequest,
    PinPasswordResetRequest,
)
from api.endpoints.auth_pin_recovery import (  # noqa: E402
    VerifyPinRequest,
    check_first_login,
    verify_pin,
    verify_pin_and_reset_password,
)


if _db_url_before is None:
    os.environ.pop("DATABASE_URL", None)
else:
    os.environ["DATABASE_URL"] = _db_url_before

from giljo_mcp.models.auth import User  # noqa: E402
from giljo_mcp.repositories.auth_repository import AuthRepository  # noqa: E402


# ----------------------------------------------------------------------------
# Fixtures
# ----------------------------------------------------------------------------


@pytest_asyncio.fixture
async def pin_user(db_session, auth_test_org):
    """
    User with recovery PIN set and known credentials.

    Returns (user, password, pin).
    """
    suffix = uuid4().hex[:6]
    password = "Pin1234!A"
    pin = "4242"
    user = User(
        id=str(uuid4()),
        username=f"pinuser_{suffix}",
        email=f"pu_{suffix}@ex.com",
        full_name="Pin User",
        password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        recovery_pin_hash=bcrypt.hashpw(pin.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
        role="developer",
        tenant_key=auth_test_org.tenant_key,
        org_id=auth_test_org.id,
        is_active=True,
        must_change_password=True,
        must_set_pin=False,
        created_at=datetime.now(UTC),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user, password, pin


def _fake_request():
    """Minimal Request-like object that bypasses rate limiting (base_url http://test)."""
    return SimpleNamespace(
        base_url="http://test/",
        url=SimpleNamespace(path="/api/auth/verify-pin-and-reset-password"),
        client=SimpleNamespace(host="127.0.0.1"),
        headers={},
    )


# ----------------------------------------------------------------------------
# Repository helper: get_user_by_username_or_email
# ----------------------------------------------------------------------------


class TestRepoDualLookupHelper:
    """New helper on AuthRepository encapsulating the dual-lookup pattern."""

    @pytest.mark.asyncio
    async def test_resolves_by_username(self, db_session, pin_user):
        user, _, _ = pin_user
        repo = AuthRepository()

        found = await repo.get_user_by_username_or_email(db_session, user.username)

        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_resolves_by_email(self, db_session, pin_user):
        user, _, _ = pin_user
        repo = AuthRepository()

        found = await repo.get_user_by_username_or_email(db_session, user.email)

        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_email_lookup_is_case_insensitive(self, db_session, pin_user):
        user, _, _ = pin_user
        repo = AuthRepository()

        found = await repo.get_user_by_username_or_email(db_session, user.email.upper())

        assert found is not None
        assert found.id == user.id

    @pytest.mark.asyncio
    async def test_unknown_returns_none(self, db_session):
        repo = AuthRepository()

        found = await repo.get_user_by_username_or_email(db_session, "nobody_xyz")

        assert found is None

    @pytest.mark.asyncio
    async def test_username_match_wins_over_email_match(self, db_session, auth_test_org):
        """Username lookup runs first -- deterministic tie-breaker."""
        shared = f"collide_{uuid4().hex[:8]}"
        u1 = User(
            id=str(uuid4()),
            username=shared,  # identifier matches this row by username
            email=f"{shared}_u1@ex.com",
            password_hash="x",
            role="developer",
            tenant_key=auth_test_org.tenant_key,
            org_id=auth_test_org.id,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        u2 = User(
            id=str(uuid4()),
            username=f"other_{uuid4().hex[:6]}",
            email=shared,  # identifier also matches this row by email
            password_hash="x",
            role="developer",
            tenant_key=auth_test_org.tenant_key,
            org_id=auth_test_org.id,
            is_active=True,
            created_at=datetime.now(UTC),
        )
        db_session.add_all([u1, u2])
        await db_session.commit()

        repo = AuthRepository()
        found = await repo.get_user_by_username_or_email(db_session, shared)

        assert found is not None
        assert found.id == u1.id


# ----------------------------------------------------------------------------
# verify-pin endpoint
# ----------------------------------------------------------------------------


class TestVerifyPinDualLookup:
    @pytest.mark.asyncio
    async def test_by_username(self, db_session, pin_user):

        user, _, pin = pin_user
        req = VerifyPinRequest(username=user.username, recovery_pin=pin)

        resp = await verify_pin(request_data=req, db=db_session)

        assert resp.valid is True

    @pytest.mark.asyncio
    async def test_by_email(self, db_session, pin_user):

        user, _, pin = pin_user
        req = VerifyPinRequest(username=user.email, recovery_pin=pin)

        resp = await verify_pin(request_data=req, db=db_session)

        assert resp.valid is True

    @pytest.mark.asyncio
    async def test_unknown_identifier_returns_invalid(self, db_session):

        req = VerifyPinRequest(username="ghost_abc", recovery_pin="0000")

        resp = await verify_pin(request_data=req, db=db_session)

        assert resp.valid is False
        # Wire-text no-enumeration pattern
        assert "Invalid username or PIN" in resp.message


# ----------------------------------------------------------------------------
# verify-pin-and-reset-password endpoint
# ----------------------------------------------------------------------------


class TestVerifyPinAndResetDualLookup:
    @pytest.mark.asyncio
    async def test_by_username(self, db_session, pin_user):

        user, _, pin = pin_user
        new_password = "NewPwd123!Z"
        req = PinPasswordResetRequest(
            username=user.username,
            recovery_pin=pin,
            new_password=new_password,
            confirm_password=new_password,
        )

        resp = await verify_pin_and_reset_password(http_request=_fake_request(), request_data=req, db=db_session)

        assert "successful" in resp.message.lower()
        # Password actually changed
        await db_session.refresh(user)
        assert bcrypt.checkpw(new_password.encode("utf-8"), user.password_hash.encode("utf-8"))

    @pytest.mark.asyncio
    async def test_by_email(self, db_session, pin_user):

        user, _, pin = pin_user
        new_password = "NewPwd456!Y"
        req = PinPasswordResetRequest(
            username=user.email,  # wire field named username, accepts email
            recovery_pin=pin,
            new_password=new_password,
            confirm_password=new_password,
        )

        resp = await verify_pin_and_reset_password(http_request=_fake_request(), request_data=req, db=db_session)

        assert "successful" in resp.message.lower()
        await db_session.refresh(user)
        assert bcrypt.checkpw(new_password.encode("utf-8"), user.password_hash.encode("utf-8"))

    @pytest.mark.asyncio
    async def test_unknown_identifier_raises_generic_error(self, db_session):

        req = PinPasswordResetRequest(
            username="ghost_xyz",
            recovery_pin="0000",
            new_password="SomePwd9!A",
            confirm_password="SomePwd9!A",
        )

        with pytest.raises(HTTPException) as exc:
            await verify_pin_and_reset_password(http_request=_fake_request(), request_data=req, db=db_session)

        assert exc.value.status_code == 400
        # Wire-text: security no-enumeration pattern -- preserve literal
        assert "Invalid username or PIN" in exc.value.detail


# ----------------------------------------------------------------------------
# check-first-login endpoint
# ----------------------------------------------------------------------------


class TestCheckFirstLoginDualLookup:
    @pytest.mark.asyncio
    async def test_by_username(self, db_session, pin_user):

        user, _, _ = pin_user
        req = CheckFirstLoginRequest(username=user.username)

        resp = await check_first_login(request_data=req, db=db_session)

        # Fixture sets must_change_password=True
        assert resp.must_change_password is True
        assert resp.must_set_pin is False

    @pytest.mark.asyncio
    async def test_by_email(self, db_session, pin_user):

        user, _, _ = pin_user
        req = CheckFirstLoginRequest(username=user.email)

        resp = await check_first_login(request_data=req, db=db_session)

        assert resp.must_change_password is True
        assert resp.must_set_pin is False

    @pytest.mark.asyncio
    async def test_unknown_identifier_returns_safe_defaults(self, db_session):

        req = CheckFirstLoginRequest(username="ghost_ident")

        resp = await check_first_login(request_data=req, db=db_session)

        # Safe defaults prevent enumeration
        assert resp.must_change_password is False
        assert resp.must_set_pin is False
