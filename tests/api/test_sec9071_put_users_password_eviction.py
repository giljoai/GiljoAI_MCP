# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-9170 — a browser cookie session is required for sensitive user-field
mutations (and for minting an API key), plus the SEC-9071 session-eviction
regression relocated to its canonical endpoint.

## SEC-9170 (the new guard)

``PUT /api/v1/users/{user_id}`` accepts ``password``, ``email``, ``is_active``
and ``recovery_pin`` in ``UserUpdate`` and applies them with no step-up. The
route authenticates via ``get_current_active_user``, which accepts a browser
cookie JWT, an ``Authorization: Bearer`` JWT (an MCP OAuth token) OR an
``X-API-Key`` interchangeably. So a leaked non-cookie credential for an account
could rewrite that account's own password/email — self-account takeover.

Verified reachability at HEAD (the RED tests below encode it):

* A **DB ``gk_`` API key alone** does NOT reach the route — CE ``AuthManager``
  validates only the file key store + JWT for REST, so a DB personal key is
  rejected with **401 at the auth middleware** (``test_pure_apikey_...``).
* An **``Authorization: Bearer`` token alone** authenticates but a state-changing
  PUT is blocked by CSRF (no ``csrf_token`` cookie).
* The **actual working vector** is a ``Bearer`` token PLUS any ``X-API-Key``
  header: the ``X-API-Key`` header trips the CSRF skip (``csrf.py:191``) while
  the Bearer authenticates. That combination is what the RED tests fire.

The fix requires the authenticating credential to be the ``access_token`` cookie
whenever a sensitive field is written; non-cookie credentials get **403** and
nothing is persisted. Dashboard callers (all cookie-based) are unaffected.

``recovery_pin`` is additionally CE-boundary-cleaned: hosted SaaS must never
accept or persist a recovery PIN (2026-07-14 product boundary), so the
``recovery_pin`` write is refused with 403 in SaaS regardless of credential.

## #3 (folded from SEC-9171) — API-key mint

``POST /api/auth/api-keys`` used the same multipurpose dependency, so a held
Bearer/OAuth token could mint a fresh 90-day key (persistence / audience
confusion). The same browser-session guard now gates the mint. LOW severity.

## SEC-9071 (relocated eviction regression)

SEC-9047 closed 3 of 4 password-write paths; the 4th
(``PUT /api/v1/users/{id}`` self password) was fixed to bump
``token_revocation_epoch`` + revoke refresh tokens. Under SEC-9170 that generic
route is cookie-only, so the full eviction regression now lives on the canonical
self password-change endpoint ``PUT /api/v1/users/{id}/password`` (which performs
the same epoch-bump + refresh-revoke), and a lean test keeps the generic route's
cookie eviction covered.

Parallel-safe: unique tenant/user per test, monkeypatch-only module patching,
no module-level mutable state.
"""

from __future__ import annotations

import secrets
from uuid import uuid4

import bcrypt
import pytest

from giljo_mcp.api_key_utils import (
    clear_api_key_verify_cache,
    generate_api_key,
    get_key_prefix,
    hash_api_key,
)
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


async def _seed_api_key(db_manager, *, user_id: str, tenant_key: str) -> str:
    """Persist an active DB ``gk_`` API key for the user; return the raw key."""
    from giljo_mcp.models.auth import APIKey

    raw = generate_api_key()
    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        session.add(
            APIKey(
                id=str(uuid4()),
                user_id=user_id,
                tenant_key=tenant_key,
                name="sec9170 test key",
                key_hash=hash_api_key(raw),
                key_prefix=get_key_prefix(raw),
                permissions=["*"],
                is_active=True,
            )
        )
        await session.commit()
    clear_api_key_verify_cache()
    return raw


async def _read_user(db_manager, *, tenant_key: str, user_id: str):
    """Detached snapshot of the persistence-check fields."""
    from types import SimpleNamespace

    from giljo_mcp.models.auth import User

    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        user = await session.get(User, user_id)
        return SimpleNamespace(
            email=user.email,
            password_hash=user.password_hash,
            is_active=user.is_active,
            recovery_pin_hash=user.recovery_pin_hash,
            token_revocation_epoch=int(user.token_revocation_epoch or 0),
        )


async def _get_epoch(db_manager, *, tenant_key: str, user_id: str) -> int:
    """Read the persisted token_revocation_epoch for the user."""
    snapshot = await _read_user(db_manager, tenant_key=tenant_key, user_id=user_id)
    return snapshot.token_revocation_epoch


def _cookie_headers(token: str) -> dict:
    """Cookie-auth headers with the CSRF double-submit pair (conftest pattern)."""
    return {
        "Cookie": f"access_token={token}; csrf_token={_CSRF}",
        "X-CSRF-Token": _CSRF,
    }


def _bearer_attack_headers(token: str) -> dict:
    """The reachable non-cookie attack shape: an ``Authorization: Bearer`` token
    authenticates while a bogus ``X-API-Key`` header trips the CSRF skip so a
    state-changing PUT reaches the handler (see module docstring)."""
    return {
        "Authorization": f"Bearer {token}",
        "X-API-Key": "gk_dummy_header_to_skip_csrf",
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


def _detail(body: dict) -> str:
    return (body.get("detail") or body.get("message") or "").lower()


AUTH_PROBE = "/api/v1/users/me/field-priority"


# ─────────────────────────────────────────────────────────────────────────────
# SEC-9170 RED — a non-cookie credential cannot write a sensitive field.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["password", "email", "is_active", "recovery_pin"])
async def test_generic_put_rejects_bearer_sensitive_field_write(api_client, db_manager, monkeypatch, field):
    """PUT /api/v1/users/{self} carrying a sensitive field, authenticated by an
    OAuth Bearer token (the reachable non-cookie vector), must be 403 and
    persist nothing — the browser-session guard, not a CSRF/auth accident."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    clear_revocation_cache()

    user_id, username, tk = await _seed_user(db_manager)
    # Unique attacker email so a (RED) unguarded write leaves no residue.
    value = {
        "password": NEW_PASSWORD,
        "email": f"attacker_{uuid4().hex[:8]}@evil.example.com",
        "is_active": False,
        "recovery_pin": "4321",
    }[field]
    before = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    token = _mint(user_id, username, tk, revocation_epoch=0)

    resp = await api_client.put(
        f"/api/v1/users/{user_id}",
        json={field: value},
        headers=_bearer_attack_headers(token),
    )

    assert resp.status_code == 403, resp.text
    assert "browser session" in _detail(resp.json()), resp.text

    after = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    assert after.password_hash == before.password_hash
    assert after.email == before.email
    assert after.is_active == before.is_active
    assert after.recovery_pin_hash == before.recovery_pin_hash
    assert after.token_revocation_epoch == before.token_revocation_epoch


@pytest.mark.asyncio
async def test_pure_apikey_cannot_reach_generic_put(api_client, db_manager, monkeypatch):
    """A DB ``gk_`` API key on its own never reaches the route — CE auth rejects
    a DB personal key on REST at the middleware (401), before the handler. This
    documents that the X-API-Key-alone path is already closed (no behavior
    change); the reachable takeover path is the Bearer vector above."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    user_id, _username, tk = await _seed_user(db_manager)
    raw = await _seed_api_key(db_manager, user_id=user_id, tenant_key=tk)
    before = await _read_user(db_manager, tenant_key=tk, user_id=user_id)

    resp = await api_client.put(
        f"/api/v1/users/{user_id}",
        json={"password": NEW_PASSWORD},
        headers={"X-API-Key": raw},
    )

    assert resp.status_code == 401, resp.text
    after = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    assert after.password_hash == before.password_hash


# ─────────────────────────────────────────────────────────────────────────────
# SEC-9170 GREEN — cookie (browser) callers are unaffected.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_generic_put_cookie_nonsensitive_fields_succeed(api_client, db_manager, monkeypatch):
    """A cookie PUT of username/first_name/last_name stays 200 and applies."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    user_id, username, tk = await _seed_user(db_manager)
    token = _mint(user_id, username, tk, revocation_epoch=0)

    resp = await api_client.put(
        f"/api/v1/users/{user_id}",
        json={"username": f"{username}_renamed", "first_name": "Given", "last_name": "Family"},
        headers=_cookie_headers(token),
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["first_name"] == "Given"
    assert body["last_name"] == "Family"


@pytest.mark.asyncio
async def test_generic_put_cookie_password_change_still_succeeds_and_evicts(api_client, db_manager, monkeypatch):
    """Cookie generic-route password change stays 200 AND still evicts (epoch
    bump) — preserves the SEC-9071 generic-route eviction and the browser
    happy-path for password."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    clear_revocation_cache()

    user_id, username, tk = await _seed_user(db_manager)
    device = _mint(user_id, username, tk, revocation_epoch=0)

    resp = await api_client.put(
        f"/api/v1/users/{user_id}",
        json={"password": NEW_PASSWORD},
        headers=_cookie_headers(device),
    )

    assert resp.status_code == 200, resp.text
    assert await _get_epoch(db_manager, tenant_key=tk, user_id=user_id) == 1


# ─────────────────────────────────────────────────────────────────────────────
# recovery_pin — CE-only boundary cleanup (hosted SaaS must not persist a PIN).
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_recovery_pin_write_rejected_in_saas(api_client, db_manager, monkeypatch):
    """In SaaS a cookie recovery_pin write is refused (403) and not persisted."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    monkeypatch.setattr("api.app_state.GILJO_MODE", "saas")

    user_id, username, tk = await _seed_user(db_manager)
    token = _mint(user_id, username, tk, revocation_epoch=0)

    resp = await api_client.put(
        f"/api/v1/users/{user_id}",
        json={"recovery_pin": "1234"},
        headers=_cookie_headers(token),
    )

    assert resp.status_code == 403, resp.text
    assert "hosted mode" in _detail(resp.json()), resp.text
    after = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    assert after.recovery_pin_hash is None


@pytest.mark.asyncio
async def test_recovery_pin_write_allowed_in_ce(api_client, db_manager, monkeypatch):
    """In CE a cookie recovery_pin write is applied (200, hash persisted)."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    monkeypatch.setattr("api.app_state.GILJO_MODE", "ce")

    user_id, username, tk = await _seed_user(db_manager)
    token = _mint(user_id, username, tk, revocation_epoch=0)

    resp = await api_client.put(
        f"/api/v1/users/{user_id}",
        json={"recovery_pin": "1234"},
        headers=_cookie_headers(token),
    )

    assert resp.status_code == 200, resp.text
    after = await _read_user(db_manager, tenant_key=tk, user_id=user_id)
    assert after.recovery_pin_hash is not None


# ─────────────────────────────────────────────────────────────────────────────
# SEC-9071 (relocated) — full session eviction on the canonical password path.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_self_password_change_via_password_endpoint_evicts_sessions_and_refresh_tokens(
    api_client, db_manager, monkeypatch
):
    """Self-service password change via PUT /api/v1/users/{id}/password: the
    OTHER device's access token is rejected afterwards, its refresh token can no
    longer mint, and a fresh token at the new epoch authenticates (re-login
    works). Relocated here from the generic route (SEC-9170 made that route
    cookie-only; this is the canonical self password-change surface)."""
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

        # The user changes their own password via the canonical endpoint
        # (non-admin self-change requires the current password).
        change = await api_client.put(
            f"/api/v1/users/{user_id}/password",
            json={"old_password": OLD_PASSWORD, "new_password": NEW_PASSWORD},
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
    """Happy path preserved: a NON-password profile update via the generic
    endpoint does NOT bump the epoch, so an existing session keeps
    authenticating and an outstanding refresh token keeps minting."""
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


# ─────────────────────────────────────────────────────────────────────────────
# #3 (folded from SEC-9171) — minting an API key requires a browser session.
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_apikey_mint_rejects_bearer(api_client, db_manager, monkeypatch):
    """POST /api/auth/api-keys authenticated by an OAuth Bearer token is 403 —
    a held token cannot mint a fresh long-lived key (SEC-9171 #3)."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    user_id, username, tk = await _seed_user(db_manager)
    token = _mint(user_id, username, tk, revocation_epoch=0)

    resp = await api_client.post(
        "/api/auth/api-keys",
        json={"name": "minted-by-bearer", "permissions": ["*"]},
        headers={"Authorization": f"Bearer {token}"},
    )

    assert resp.status_code == 403, resp.text
    assert "browser session" in _detail(resp.json()), resp.text


@pytest.mark.asyncio
async def test_apikey_mint_cookie_succeeds(api_client, db_manager, monkeypatch):
    """A cookie (browser) caller can still mint an API key (200/201)."""
    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    user_id, username, tk = await _seed_user(db_manager)
    token = _mint(user_id, username, tk, revocation_epoch=0)

    resp = await api_client.post(
        "/api/auth/api-keys",
        json={"name": "minted-by-cookie", "permissions": ["*"]},
        headers=_cookie_headers(token),
    )

    assert resp.status_code in (200, 201), resp.text
    assert resp.json()["api_key"].startswith("gk_")
