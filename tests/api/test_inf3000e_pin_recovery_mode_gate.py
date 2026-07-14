# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
INF-3000e regression: the CE-only PIN-recovery endpoints must treat ``""``
(GILJO_MODE unset/default) as CE, exactly like the literal ``"ce"``.

Before INF-3000e, ``api/endpoints/auth_pin_recovery.py`` gated four sites on
``== "ce"`` / ``!= "ce"`` only, so a CE self-hoster on ``GILJO_MODE=""`` (the
default, and the value CI runs the CE step with) was wrongly served:
  - verify-pin-and-reset-password -> 404 (recovery surface vanished)
  - verify-pin                    -> 404
  - check-first-login             -> must_set_pin always False (PIN setup skipped)
  - complete-first-login          -> PIN treated as optional (CE's only recovery
                                     channel silently downgraded)

This locks the contract two-sided, at the FAILING LAYER (the endpoint handlers):
  (1) CE-"" REACHES the routes and enforces CE behavior (PIN required).
  (2) SaaS ("saas") STAYS HIDDEN / PIN-less (the load-bearing regression half).

GILJO_MODE is imported at MODULE level in auth_pin_recovery (frozen at import),
so we patch the module-local name ``api.endpoints.auth_pin_recovery.GILJO_MODE``
rather than ``api.app_state.GILJO_MODE`` (the latter would not reach the
handlers). Handlers are invoked directly with fakes — no live DB, no rate-limit
infra — so the suite is parallel-safe (monkeypatch only, no shared state).

Edition Scope: Both (the gate is CE core code; SaaS-hiding is the SaaS half).
"""

from __future__ import annotations

import contextlib

import bcrypt
import pytest
from fastapi import HTTPException

from api.endpoints.auth_models import (
    CheckFirstLoginRequest,
    CompleteFirstLoginRequest,
    PinPasswordResetRequest,
)
from api.endpoints.auth_pin_recovery import (
    VerifyPinRequest,
    check_first_login,
    complete_first_login,
    verify_pin,
    verify_pin_and_reset_password,
)
from giljo_mcp.repositories.auth_repository import AuthRepository


_GILJO_MODE_ATTR = "api.endpoints.auth_pin_recovery.GILJO_MODE"


class _NoopRateLimiter:
    """Stub so the reachable-in-CE tests don't depend on rate-limit infra."""

    async def check_rate_limit(self, *args, **kwargs):
        return None


class _FakeUser:
    def __init__(self, must_set_pin: bool, must_change_password: bool, password_hash: str | None = None):
        self.must_set_pin = must_set_pin
        self.must_change_password = must_change_password
        self.password_hash = password_hash
        self.recovery_pin_hash = None
        self.username = "first_login_user"
        # SEC-9084: complete_first_login now evicts sessions on success — the
        # handler reads these on the user before delegating to the (stubbed)
        # revocation collaborators.
        self.id = "fake-user-id"
        self.tenant_key = "fake-tenant"
        self.token_revocation_epoch = 0


class _FakeDB:
    async def commit(self):
        return None


def _patch_repo_user(monkeypatch, user):
    """Force the dual-lookup repository call to return ``user`` (or None)."""

    async def _fake_lookup(self, db, identifier):
        return user

    monkeypatch.setattr(AuthRepository, "get_user_by_username_or_email", _fake_lookup)


# ---------------------------------------------------------------------------
# Site api/endpoints/auth_pin_recovery.py:85 — verify-pin-and-reset-password
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_pin_reset_hidden_in_saas(monkeypatch):
    """SaaS must NOT expose the PIN reset surface (404 before the handler runs)."""
    monkeypatch.setattr(_GILJO_MODE_ATTR, "saas")
    req = PinPasswordResetRequest(
        username="someuser", recovery_pin="1234", new_password="NewPass1!B", confirm_password="NewPass1!B"
    )
    with pytest.raises(HTTPException) as exc:
        await verify_pin_and_reset_password(http_request=None, request_data=req, db=None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_verify_pin_reset_reachable_in_ce_empty(monkeypatch):
    """CE-"" must REACH the handler: the mode gate passes, so a mismatched
    password confirmation surfaces the real 400 (not the gate's 404)."""
    monkeypatch.setattr(_GILJO_MODE_ATTR, "")
    # get_rate_limiter() is called with no args; the class itself is a valid
    # zero-arg factory returning a fresh stub.
    monkeypatch.setattr("api.endpoints.auth_pin_recovery.get_rate_limiter", _NoopRateLimiter)
    req = PinPasswordResetRequest(
        username="someuser", recovery_pin="1234", new_password="NewPass1!B", confirm_password="Different1!C"
    )
    with pytest.raises(HTTPException) as exc:
        await verify_pin_and_reset_password(http_request=object(), request_data=req, db=object())
    assert exc.value.status_code == 400
    assert "do not match" in exc.value.detail.lower()


# ---------------------------------------------------------------------------
# Site api/endpoints/auth_pin_recovery.py:194 — verify-pin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_pin_hidden_in_saas(monkeypatch):
    """SaaS must NOT expose verify-pin (404 before the handler runs)."""
    monkeypatch.setattr(_GILJO_MODE_ATTR, "saas")
    req = VerifyPinRequest(username="someuser", recovery_pin="1234")
    with pytest.raises(HTTPException) as exc:
        await verify_pin(request_data=req, db=None)
    assert exc.value.status_code == 404


@pytest.mark.asyncio
async def test_verify_pin_reachable_in_ce_empty(monkeypatch):
    """CE-"" must REACH the handler: the gate passes, the repo lookup runs, and
    an unknown user yields a normal (valid=False) response — never a 404."""
    monkeypatch.setattr(_GILJO_MODE_ATTR, "")
    _patch_repo_user(monkeypatch, None)
    resp = await verify_pin(request_data=VerifyPinRequest(username="ghost", recovery_pin="1234"), db=object())
    assert resp.valid is False


# ---------------------------------------------------------------------------
# Site api/endpoints/auth_pin_recovery.py:247 — check-first-login must_set_pin
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_first_login_requires_pin_setup_in_ce_empty(monkeypatch):
    """CE-"": a user flagged must_set_pin gets must_set_pin=True (PIN setup on)."""
    monkeypatch.setattr(_GILJO_MODE_ATTR, "")
    _patch_repo_user(monkeypatch, _FakeUser(must_set_pin=True, must_change_password=True))
    resp = await check_first_login(request_data=CheckFirstLoginRequest(username="first_login_user"), db=object())
    assert resp.must_set_pin is True
    assert resp.must_change_password is True


@pytest.mark.asyncio
async def test_check_first_login_suppresses_pin_setup_in_saas(monkeypatch):
    """SaaS: must_set_pin is force-suppressed to False even for a flagged user
    (must_change_password still True — proves it's the mode gate, not the user)."""
    monkeypatch.setattr(_GILJO_MODE_ATTR, "saas")
    _patch_repo_user(monkeypatch, _FakeUser(must_set_pin=True, must_change_password=True))
    resp = await check_first_login(request_data=CheckFirstLoginRequest(username="first_login_user"), db=object())
    assert resp.must_set_pin is False
    assert resp.must_change_password is True


# ---------------------------------------------------------------------------
# Site api/endpoints/auth_pin_recovery.py:301 — complete-first-login pin_required
# ---------------------------------------------------------------------------


def _complete_request(with_pin: bool) -> CompleteFirstLoginRequest:
    kwargs = {
        "current_password": "OldPass1!A",
        "new_password": "NewPass1!B",
        "confirm_password": "NewPass1!B",
    }
    if with_pin:
        kwargs.update({"recovery_pin": "4242", "confirm_pin": "4242"})
    return CompleteFirstLoginRequest(**kwargs)


def _user_with_password(password: str) -> _FakeUser:
    return _FakeUser(
        must_set_pin=True,
        must_change_password=True,
        password_hash=bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
    )


@pytest.mark.asyncio
async def test_complete_first_login_requires_pin_in_ce_empty(monkeypatch):
    """CE-"": completing first login WITHOUT a PIN must be rejected — the PIN is
    CE's only recovery channel."""
    monkeypatch.setattr(_GILJO_MODE_ATTR, "")
    user = _user_with_password("OldPass1!A")
    with pytest.raises(HTTPException) as exc:
        await complete_first_login(request_data=_complete_request(with_pin=False), current_user=user, db=_FakeDB())
    assert exc.value.status_code == 400
    assert "pin is required" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_complete_first_login_ignores_missing_pin_in_saas(monkeypatch):
    """SaaS: a missing PIN must NOT block completion (email reset replaces it).
    The handler proceeds, clears the first-login flags, and never sets a PIN."""
    monkeypatch.setattr(_GILJO_MODE_ATTR, "saas")

    # SEC-9084: a successful completion now evicts sessions (epoch bump + refresh
    # revoke) in the same transaction. Stub the DB-touching collaborators so this
    # fakes-only unit test still exercises the mode gate without a live session.
    @contextlib.contextmanager
    def _noop_tenant_ctx(db, tenant_key):
        yield

    async def _fake_revoke(db, *, user_id, tenant_key):
        return 0

    monkeypatch.setattr("api.endpoints.auth_pin_recovery.tenant_session_context", _noop_tenant_ctx)
    monkeypatch.setattr("api.endpoints.auth_pin_recovery.revoke_all_refresh_tokens_for_user", _fake_revoke)

    user = _user_with_password("OldPass1!A")
    resp = await complete_first_login(request_data=_complete_request(with_pin=False), current_user=user, db=_FakeDB())
    assert resp is not None
    assert user.must_change_password is False
    assert user.must_set_pin is False
    assert user.recovery_pin_hash is None  # SaaS never mints a PIN
    assert user.token_revocation_epoch == 1  # SEC-9084: completion evicts sessions
