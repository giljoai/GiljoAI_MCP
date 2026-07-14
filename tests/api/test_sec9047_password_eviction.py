# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-9047 — password change / CE PIN reset must evict live sessions + refresh tokens.

Before SEC-9047, no password change or reset path bumped the user's
``token_revocation_epoch`` (SEC-6011's "log everyone out" switch) or revoked
their outstanding OAuth refresh tokens. Consequence: after the standard
stolen-session remediation (change/reset the password), a second device's
access token stayed valid until expiry and a refresh token kept minting fresh
access tokens indefinitely.

Failing-layer regression tests, driven through the FastAPI routes (the layer
the bug occurred at):

  - PUT /api/v1/users/{user_id}/password (authenticated change, service path
    ``UserAuthService._change_password_impl``)
  - POST /api/auth/verify-pin-and-reset-password (CE PIN reset)

Each path is proven two-sided (CLAUDE.md auth rule): the OTHER device's stale
access token is rejected AND its refresh token can no longer mint at
/api/oauth/refresh, while a fresh token at the new epoch (re-login) and the
normal refresh grant keep working.

The SaaS email-reset path (api/saas_endpoints/password_reset.py confirm) is
covered separately in tests/saas/test_sec9047_reset_eviction.py.

Parallel-safe: unique tenant/user per test, monkeypatch-only module patching,
no module-level mutable state.
"""

from __future__ import annotations

import secrets
from uuid import uuid4

import bcrypt
import pytest

from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.services.oauth_refresh_service import issue_refresh_token, new_family_id
from giljo_mcp.services.oauth_revocation_service import clear_revocation_cache


OLD_PASSWORD = "OldPassword1!"
NEW_PASSWORD = "NewPassword2@"
RECOVERY_PIN = "4242"

_CSRF = secrets.token_urlsafe(32)


async def _seed_user(db_manager, *, with_pin: bool = False) -> tuple[str, str, str]:
    """Create org+user (epoch 0); return (user_id, username, tenant_key)."""
    from giljo_mcp.models.auth import User
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    tk = TenantManager.generate_tenant_key()
    unique = uuid4().hex[:8]
    user_id = str(uuid4())
    username = f"sec9047_user_{unique}"

    async with db_manager.get_session_async(tenant_key=tk) as session:
        org = Organization(
            name=f"SEC9047 Org {unique}",
            slug=f"sec9047-org-{unique}",
            tenant_key=tk,
            is_active=True,
        )
        session.add(org)
        await session.flush()
        session.add(
            User(
                id=user_id,
                username=username,
                email=f"sec9047_{unique}@example.com",
                password_hash=bcrypt.hashpw(OLD_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                recovery_pin_hash=(
                    bcrypt.hashpw(RECOVERY_PIN.encode("utf-8"), bcrypt.gensalt()).decode("utf-8") if with_pin else None
                ),
                tenant_key=tk,
                role="developer",
                org_id=org.id,
                is_active=True,
                token_revocation_epoch=0,
            )
        )
        await session.commit()

    return user_id, username, tk


def _cookie_headers(token: str) -> dict:
    """Cookie-auth headers with the CSRF double-submit pair (conftest pattern)."""
    return {
        "Cookie": f"access_token={token}; csrf_token={_CSRF}",
        "X-CSRF-Token": _CSRF,
    }


def _mint(user_id: str, username: str, tenant_key: str, *, revocation_epoch: int) -> str:
    return JWTManager.create_access_token(
        user_id=user_id,
        username=username,
        role="developer",
        tenant_key=tenant_key,
        revocation_epoch=revocation_epoch,
    )


def _install_confidential_resolver(client_id: str, secret_hash: str):
    """Stub resolver recognizing one confidential client (test_oauth_refresh pattern)."""
    from giljo_mcp.services import oauth_service as svc

    prior = svc.get_client_resolver()

    def _resolver(cid: str, tenant_key: str):
        assert tenant_key
        if cid != client_id:
            return None
        return svc.ResolvedClient(
            client_id=cid,
            client_name="SEC9047 Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            client_secret_hash=secret_hash,
        )

    svc.set_client_resolver(_resolver)

    def _restore() -> None:
        svc.set_client_resolver(prior)

    return _restore


async def _seed_refresh_token(db_manager, *, client_id: str, tenant_key: str, user_id: str) -> str:
    """Persist a live refresh-token row; return the raw token."""
    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        raw = await issue_refresh_token(
            session,
            family_id=new_family_id(),
            client_id=client_id,
            tenant_key=tenant_key,
            user_id=user_id,
            scope="mcp:read mcp:write",
            aud="",
            lifetime_seconds=3600,
        )
        await session.commit()
    return raw


async def _refresh_call(api_client, *, refresh_token: str, client_id: str, client_secret: str):
    return await api_client.post(
        "/api/oauth/refresh",
        data={
            "grant_type": "refresh_token",
            "refresh_token": refresh_token,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )


def _oauth_err_text(body: dict) -> str:
    return " ".join(str(body.get(k, "")) for k in ("error", "error_description", "detail", "message"))


AUTH_PROBE = "/api/v1/users/me/field-priority"


@pytest.mark.asyncio
async def test_password_change_evicts_other_sessions_and_refresh_tokens(api_client, db_manager, monkeypatch):
    """Authenticated password change: the OTHER device's access token is rejected
    afterwards, its refresh token can no longer mint, and a fresh token at the
    new epoch authenticates (re-login works)."""
    from giljo_mcp.services import oauth_refresh_service as _refresh_svc

    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)
    clear_revocation_cache()

    user_id, username, tk = await _seed_user(db_manager)

    device_a = _mint(user_id, username, tk, revocation_epoch=0)  # the device changing the password
    device_b = _mint(user_id, username, tk, revocation_epoch=0)  # a second (possibly stolen) session

    # Two-sided baseline: device B authenticates before the change.
    probe = await api_client.get(AUTH_PROBE, headers=_cookie_headers(device_b))
    assert probe.status_code == 200, probe.text

    # A live OAuth refresh token that mints normally before the change.
    client_id = str(uuid4())
    client_secret = secrets.token_urlsafe(48)
    secret_hash = bcrypt.hashpw(client_secret.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    restore = _install_confidential_resolver(client_id, secret_hash)
    try:
        raw1 = await _seed_refresh_token(db_manager, client_id=client_id, tenant_key=tk, user_id=user_id)
        before = await _refresh_call(api_client, refresh_token=raw1, client_id=client_id, client_secret=client_secret)
        assert before.status_code == 200, before.text
        rotated = before.json()["refresh_token"]

        # The user changes their own password from device A.
        change = await api_client.put(
            f"/api/v1/users/{user_id}/password",
            json={"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
            headers=_cookie_headers(device_a),
        )
        assert change.status_code == 200, change.text

        # Device B's stale token (minted at epoch 0, different jti — NOT the
        # token presented to the change endpoint) must now be rejected.
        clear_revocation_cache()
        stale = await api_client.get(AUTH_PROBE, headers=_cookie_headers(device_b))
        assert stale.status_code == 401, stale.text

        # The outstanding (rotated) refresh token can no longer mint.
        after = await _refresh_call(api_client, refresh_token=rotated, client_id=client_id, client_secret=client_secret)
        assert after.status_code == 401, after.text
        assert "invalid_grant" in _oauth_err_text(after.json()).lower()

        # Re-login works: a token minted at the NEW epoch authenticates.
        fresh = _mint(user_id, username, tk, revocation_epoch=1)
        relogin = await api_client.get(AUTH_PROBE, headers=_cookie_headers(fresh))
        assert relogin.status_code == 200, relogin.text
    finally:
        restore()
        clear_revocation_cache()


@pytest.mark.asyncio
async def test_pin_reset_evicts_sessions_and_refresh_tokens(api_client, db_manager, monkeypatch):
    """CE PIN reset: after the reset, a pre-reset access token is rejected, the
    outstanding refresh token can no longer mint, and a fresh token at the new
    epoch authenticates."""
    from giljo_mcp.services import oauth_refresh_service as _refresh_svc

    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)
    # PIN recovery is CE-only; GILJO_MODE is frozen at module import, so pin the
    # module-local name (test_inf3000e pattern) — deterministic in both CI jobs.
    monkeypatch.setattr("api.endpoints.auth_pin_recovery.GILJO_MODE", "")

    # Keep the test independent of shared per-IP rate-limit state (parallel-safe).
    class _NoopRateLimiter:
        async def check_rate_limit(self, *args, **kwargs):
            return None

    monkeypatch.setattr("api.endpoints.auth_pin_recovery.get_rate_limiter", _NoopRateLimiter)
    clear_revocation_cache()

    user_id, username, tk = await _seed_user(db_manager, with_pin=True)

    stale_token = _mint(user_id, username, tk, revocation_epoch=0)
    probe = await api_client.get(AUTH_PROBE, headers=_cookie_headers(stale_token))
    assert probe.status_code == 200, probe.text

    client_id = str(uuid4())
    client_secret = secrets.token_urlsafe(48)
    secret_hash = bcrypt.hashpw(client_secret.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    restore = _install_confidential_resolver(client_id, secret_hash)
    try:
        raw1 = await _seed_refresh_token(db_manager, client_id=client_id, tenant_key=tk, user_id=user_id)
        before = await _refresh_call(api_client, refresh_token=raw1, client_id=client_id, client_secret=client_secret)
        assert before.status_code == 200, before.text
        rotated = before.json()["refresh_token"]

        reset = await api_client.post(
            "/api/auth/verify-pin-and-reset-password",
            json={
                "username": username,
                "recovery_pin": RECOVERY_PIN,
                "new_password": NEW_PASSWORD,
                "confirm_password": NEW_PASSWORD,
            },
        )
        assert reset.status_code == 200, reset.text

        clear_revocation_cache()
        stale = await api_client.get(AUTH_PROBE, headers=_cookie_headers(stale_token))
        assert stale.status_code == 401, stale.text

        after = await _refresh_call(api_client, refresh_token=rotated, client_id=client_id, client_secret=client_secret)
        assert after.status_code == 401, after.text
        assert "invalid_grant" in _oauth_err_text(after.json()).lower()

        fresh = _mint(user_id, username, tk, revocation_epoch=1)
        relogin = await api_client.get(AUTH_PROBE, headers=_cookie_headers(fresh))
        assert relogin.status_code == 200, relogin.text
    finally:
        restore()
        clear_revocation_cache()
