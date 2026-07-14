# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-9071 — the 4th password-write path (PUT /api/v1/users) must evict sessions.

SEC-9047 closed 3 of 4 password-write paths (change / SaaS reset / CE PIN reset):
each now bumps ``token_revocation_epoch`` (SEC-6011's "log everyone out" switch)
and revokes the user's outstanding OAuth refresh tokens. A FOURTH path was
missed: ``PUT /api/v1/users/{user_id}`` accepts ``UserUpdate.password`` and, on
self-update, routes to ``UserService.update_user`` which set ``password_hash``
with NO epoch bump and NO refresh-token revoke. So an attacker holding a stolen
token could change the password here and their own session survived — the exact
hole SEC-9047 exists to close.

Failing-layer regression test, driven through the FastAPI route (the layer the
bug occurred at):

  - PUT /api/v1/users/{user_id}  (self-service profile update carrying password)

Proven two-sided (CLAUDE.md auth rule): after a self-service password change the
OTHER device's stale access token is rejected AND its refresh token can no longer
mint at /api/oauth/refresh, while a fresh token at the new epoch (re-login) keeps
working. A second test proves the happy path is preserved — a NON-password profile
update via the same endpoint does NOT bump the epoch or revoke sessions.

Out of scope (tracked on the SEC-9071 project, not built here): whether this
endpoint should additionally require ``old_password`` — a separate auth-posture
decision.

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

_CSRF = secrets.token_urlsafe(32)


async def _seed_user(db_manager) -> tuple[str, str, str]:
    """Create org+user (epoch 0); return (user_id, username, tenant_key)."""
    from giljo_mcp.models.auth import User
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    tk = TenantManager.generate_tenant_key()
    unique = uuid4().hex[:8]
    user_id = str(uuid4())
    username = f"sec9071_user_{unique}"

    async with db_manager.get_session_async(tenant_key=tk) as session:
        org = Organization(
            name=f"SEC9071 Org {unique}",
            slug=f"sec9071-org-{unique}",
            tenant_key=tk,
            is_active=True,
        )
        session.add(org)
        await session.flush()
        session.add(
            User(
                id=user_id,
                username=username,
                email=f"sec9071_{unique}@example.com",
                password_hash=bcrypt.hashpw(OLD_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
                tenant_key=tk,
                role="developer",
                org_id=org.id,
                is_active=True,
                token_revocation_epoch=0,
            )
        )
        await session.commit()

    return user_id, username, tk


async def _get_epoch(db_manager, *, tenant_key: str, user_id: str) -> int:
    """Read the persisted token_revocation_epoch for the user."""
    from giljo_mcp.models.auth import User

    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        user = await session.get(User, user_id)
        return int(user.token_revocation_epoch or 0)


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
            client_name="SEC9071 Test Client",
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
async def test_put_users_password_change_evicts_sessions_and_refresh_tokens(api_client, db_manager, monkeypatch):
    """Self-service password change via PUT /api/v1/users: the OTHER device's
    access token is rejected afterwards, its refresh token can no longer mint,
    and a fresh token at the new epoch authenticates (re-login works)."""
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

        # The user changes their own password via the profile-update endpoint.
        change = await api_client.put(
            f"/api/v1/users/{user_id}",
            json={"password": NEW_PASSWORD},
            headers=_cookie_headers(device_a),
        )
        assert change.status_code == 200, change.text

        # The epoch was bumped exactly once (0 -> 1).
        assert await _get_epoch(db_manager, tenant_key=tk, user_id=user_id) == 1

        # Device B's stale token (minted at epoch 0) must now be rejected.
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
async def test_put_users_non_password_update_does_not_evict_sessions(api_client, db_manager, monkeypatch):
    """Happy path preserved: a NON-password profile update via the same endpoint
    does NOT bump the epoch, so an existing session keeps authenticating and an
    outstanding refresh token keeps minting."""
    from giljo_mcp.services import oauth_refresh_service as _refresh_svc

    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)
    clear_revocation_cache()

    user_id, username, tk = await _seed_user(db_manager)

    device = _mint(user_id, username, tk, revocation_epoch=0)

    client_id = str(uuid4())
    client_secret = secrets.token_urlsafe(48)
    secret_hash = bcrypt.hashpw(client_secret.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    restore = _install_confidential_resolver(client_id, secret_hash)
    try:
        raw1 = await _seed_refresh_token(db_manager, client_id=client_id, tenant_key=tk, user_id=user_id)

        # A non-password profile field is updated.
        update = await api_client.put(
            f"/api/v1/users/{user_id}",
            json={"first_name": "Renamed"},
            headers=_cookie_headers(device),
        )
        assert update.status_code == 200, update.text
        assert update.json()["first_name"] == "Renamed"

        # Epoch is untouched — no session eviction on a non-credential change.
        assert await _get_epoch(db_manager, tenant_key=tk, user_id=user_id) == 0

        # The existing session still authenticates.
        clear_revocation_cache()
        still = await api_client.get(AUTH_PROBE, headers=_cookie_headers(device))
        assert still.status_code == 200, still.text

        # The outstanding refresh token still mints.
        after = await _refresh_call(api_client, refresh_token=raw1, client_id=client_id, client_secret=client_secret)
        assert after.status_code == 200, after.text
    finally:
        restore()
        clear_revocation_cache()
