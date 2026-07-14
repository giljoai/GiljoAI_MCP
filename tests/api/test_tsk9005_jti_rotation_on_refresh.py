# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression tests for TSK-9005: dashboard access-token jti rotation on refresh.

Edition Scope: Both (core dashboard auth).

Control: ``POST /api/auth/refresh`` now rotates the PRIOR access-token jti --
writing a ``TOKEN_TYPE_ACCESS_ROTATED`` revocation-ledger row -- so a stolen
cookie cannot be silently refreshed into a fresh 24h token indefinitely past
revocation (SEC-3001a Wave 2 item 4). Previously refresh minted a new token but
left the prior jti fully valid for its whole 24h life AND independently
refreshable forever.

The deferral reason was the concurrent-refresh race: a naive immediate
revocation of the prior jti would 401 an in-flight request (or a second /refresh
from another tab) that is still carrying the just-superseded cookie, because the
shared validator (``validate_principal`` -> ``is_access_token_jti_revoked``)
enforces jti revocation on EVERY dashboard request. The fix resolves this with a
short grace/overlap window (``ROTATION_GRACE_SECONDS``): a rotation row is
honored -- the prior jti stays valid -- until the window elapses.

Coverage (exercised at the failing layers -- the real HTTP refresh endpoint AND
the shared-validation path via GET /api/auth/me, both through the ASGI client):

1. old jti rejected AFTER rotation (grace elapsed) -- at /refresh AND at /me.
2. concurrent-refresh race does NOT lock out -- a second refresh and an
   in-flight /me presenting the same prior cookie WITHIN the grace window still
   succeed; a genuinely-concurrent double refresh returns 200/200.
3. happy path unchanged -- a single normal refresh returns 200 + a fresh cookie
   whose new jti authenticates.
4. logout/RFC 7009 revocation stays IMMEDIATE despite the rotation grace -- the
   grace applies only to rotation rows, never to logout rows.

Grace is driven off the module-level ``ROTATION_GRACE_SECONDS`` constant, which
each test sets explicitly via ``monkeypatch.setattr`` (0 = immediate,
large = overlap) so assertions are deterministic without sleeps. The in-process
revocation cache is cleared at the seams where a prior read would otherwise
serve a stale verdict (its short negative TTL is subsumed by the real grace in
production, but must be bypassed for a deterministic post-grace assertion).

Parallel-safe: every test seeds its own unique tenant + org + user; the grace
constant and guard mode are set via monkeypatch; no module-level mutable state;
no ordering dependency.

Project: TSK-9005.
"""

from __future__ import annotations

import asyncio
import uuid

import bcrypt
import pytest
import pytest_asyncio

from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.models import User
from giljo_mcp.models.organizations import Organization
from giljo_mcp.services import oauth_revocation_service
from giljo_mcp.services.oauth_revocation_service import clear_revocation_cache
from giljo_mcp.tenant import TenantManager


_REFRESH_URL = "/api/auth/refresh"
_ME_URL = "/api/auth/me"
_LOGOUT_URL = "/api/auth/logout"


async def _seed_user(db_manager) -> dict:
    """Create a fresh active user (+ org) in a unique tenant. Returns ids + a valid token."""
    suffix = uuid.uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()
    password_hash = bcrypt.hashpw(b"test_password", bcrypt.gensalt()).decode("utf-8")

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"TSK9005 Org {suffix}",
            slug=f"tsk9005-org-{suffix}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"tsk9005_user_{suffix}",
            email=f"tsk9005_{suffix}@example.com",
            password_hash=password_hash,
            tenant_key=tenant_key,
            role="developer",
            org_id=org.id,
        )
        session.add(user)
        await session.commit()
        user_id = user.id

    token = JWTManager.create_access_token(
        user_id=user_id,
        username=f"tsk9005_user_{suffix}",
        role="developer",
        tenant_key=tenant_key,
    )
    return {"tenant_key": tenant_key, "user_id": user_id, "username": f"tsk9005_user_{suffix}", "token": token}


@pytest_asyncio.fixture(scope="function")
async def seeded_user(db_manager) -> dict:
    return await _seed_user(db_manager)


def _pin(api_client, token: str) -> None:
    """Re-pin exactly one token in the jar (a successful refresh rotates the cookie)."""
    api_client.cookies.clear()
    api_client.cookies.set("access_token", token)


@pytest.mark.asyncio
async def test_old_jti_rejected_after_rotation(api_client, seeded_user, monkeypatch) -> None:
    """The prior jti is dead once the rotation grace elapses -- at BOTH seams.

    Grace 0 makes the rotation effective immediately (post-grace behavior). A
    first refresh mints a new cookie AND rotates the presented jti; re-presenting
    that SAME (now-rotated) token is then refused at /refresh (no new cookie) and
    at the shared-validation layer (GET /me). The cache is cleared before each
    kill-half assertion so the deterministic post-grace verdict is read from the
    DB rather than the short-lived negative-cache entry left by the gate check.
    """
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")
    monkeypatch.setattr(oauth_revocation_service, "ROTATION_GRACE_SECONDS", 0)
    clear_revocation_cache()
    token = seeded_user["token"]

    # Happy half: a pristine token refreshes and rotates its own jti.
    _pin(api_client, token)
    ok = await api_client.post(_REFRESH_URL)
    assert ok.status_code == 200, ok.text
    assert "access_token=" in ok.headers.get("set-cookie", "")

    # Kill half A -- refresh seam: the rotated jti cannot be refreshed again.
    clear_revocation_cache()
    _pin(api_client, token)
    blocked = await api_client.post(_REFRESH_URL)
    assert blocked.status_code == 401, blocked.text
    assert "revoked" in blocked.text.lower(), blocked.text
    assert "set-cookie" not in {k.lower() for k in blocked.headers}, "rotated refresh must not mint a new cookie"

    # Kill half B -- shared-validation seam: the rotated jti fails a normal request.
    clear_revocation_cache()
    _pin(api_client, token)
    me = await api_client.get(_ME_URL)
    assert me.status_code == 401, me.text


@pytest.mark.asyncio
async def test_concurrent_refresh_within_grace_not_locked_out(api_client, seeded_user, monkeypatch) -> None:
    """A request racing the rotation is NOT spuriously 401'd within the grace window.

    Grace 30s (production default): after a first refresh rotates the jti, the
    SAME prior cookie is still honored during the overlap -- both a second
    /refresh (models a concurrent tab) and a normal GET /me (models an in-flight
    request) succeed. The cache is cleared before each within-grace assertion so
    the grace math is exercised against the DB row's ``revoked_at`` rather than a
    cached verdict.
    """
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")
    monkeypatch.setattr(oauth_revocation_service, "ROTATION_GRACE_SECONDS", 30)
    clear_revocation_cache()
    token = seeded_user["token"]

    # First refresh rotates the jti (revoked_at = now); grace window opens.
    _pin(api_client, token)
    first = await api_client.post(_REFRESH_URL)
    assert first.status_code == 200, first.text

    # Within grace: a second refresh presenting the same prior cookie is honored.
    clear_revocation_cache()
    _pin(api_client, token)
    overlap_refresh = await api_client.post(_REFRESH_URL)
    assert overlap_refresh.status_code == 200, overlap_refresh.text

    # Within grace: an in-flight normal request with the same prior cookie authenticates.
    clear_revocation_cache()
    _pin(api_client, token)
    overlap_me = await api_client.get(_ME_URL)
    assert overlap_me.status_code == 200, overlap_me.text
    assert overlap_me.json()["username"] == seeded_user["username"]


@pytest.mark.asyncio
async def test_truly_concurrent_double_refresh_no_lockout(api_client, seeded_user, monkeypatch) -> None:
    """Two genuinely-concurrent refreshes of the same cookie both succeed.

    The race the deferral feared: two tabs fire /refresh with the same cookie at
    once. Neither must lock the user out. Cookies are passed per-request so the
    shared jar's Set-Cookie churn cannot perturb the inputs; the race-safe
    ON CONFLICT rotation insert means the loser does not hit an IntegrityError.
    """
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")
    monkeypatch.setattr(oauth_revocation_service, "ROTATION_GRACE_SECONDS", 30)
    clear_revocation_cache()
    token = seeded_user["token"]

    # Pin on the client instance, then dispatch both concurrently: gather builds
    # and sends both requests before either response's Set-Cookie can churn the
    # jar, so both carry the same prior cookie into the server-side race.
    _pin(api_client, token)
    r1, r2 = await asyncio.gather(
        api_client.post(_REFRESH_URL),
        api_client.post(_REFRESH_URL),
    )
    assert r1.status_code == 200, r1.text
    assert r2.status_code == 200, r2.text


@pytest.mark.asyncio
async def test_happy_path_new_jti_authenticates(api_client, seeded_user, monkeypatch) -> None:
    """A single refresh yields a fresh cookie whose NEW jti authenticates normally.

    Guards that rotation does not collateral-damage the token it just minted:
    the new cookie works at the shared-validation layer even after the prior jti
    is rotated.
    """
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")
    monkeypatch.setattr(oauth_revocation_service, "ROTATION_GRACE_SECONDS", 0)
    clear_revocation_cache()

    _pin(api_client, seeded_user["token"])
    refreshed = await api_client.post(_REFRESH_URL)
    assert refreshed.status_code == 200, refreshed.text

    # The jar now holds the freshly-minted cookie (Set-Cookie applied). It must
    # authenticate a normal request -- its jti was never rotated.
    clear_revocation_cache()
    me = await api_client.get(_ME_URL)
    assert me.status_code == 200, me.text
    assert me.json()["username"] == seeded_user["username"]


@pytest.mark.asyncio
async def test_logout_revocation_stays_immediate_despite_grace(api_client, seeded_user, monkeypatch) -> None:
    """The rotation grace must NOT leak into logout/RFC 7009 revocation.

    Grace 30s is in effect, but a logged-out token is refused immediately -- the
    grace is a property of rotation rows (``TOKEN_TYPE_ACCESS_ROTATED``) only,
    never of the immediate ``access_token`` revocation rows logout writes. Guards
    the token_type discrimination in ``_row_is_effective_revocation``.
    """
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")
    monkeypatch.setattr(oauth_revocation_service, "ROTATION_GRACE_SECONDS", 30)
    clear_revocation_cache()
    token = seeded_user["token"]

    # Logout writes an immediate access_token revocation row for the jti.
    _pin(api_client, token)
    out = await api_client.post(_LOGOUT_URL)
    assert out.status_code == 200, out.text

    # Immediately (no 30s wait): the logged-out token is refused at /refresh.
    clear_revocation_cache()
    _pin(api_client, token)
    blocked = await api_client.post(_REFRESH_URL)
    assert blocked.status_code == 401, blocked.text
    assert "revoked" in blocked.text.lower(), blocked.text
