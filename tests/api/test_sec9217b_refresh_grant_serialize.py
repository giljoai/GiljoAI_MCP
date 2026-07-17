# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-9217b — the OAuth refresh grant must serialize against session invalidation.

TOCTOU race (confirmed against code): ``refresh_token_grant`` loads the refresh
row with NO row lock, then the reuse-detection gate ``if row.revoked:`` reads the
ORM attribute cached from that initial load. A concurrent invalidation
(force-logout / password change / deactivation) that flips ``revoked=true`` and
bumps the epoch, committing in the window between the load and the check -- a
window WIDENED by the bcrypt client-secret verify that sits between them -- is not
seen: the stale attribute reads False, reuse-detection is skipped, and the grant
re-reads ``User`` fresh (post-bump epoch), mints a NEW access JWT at the new epoch
and inserts a fresh un-revoked refresh row. Net: after "invalidation" the holder
still has a live access+refresh pair.

Fix: a user-first ``SELECT ... FOR UPDATE`` on the owning User row in both the
grant and the eviction paths, plus a FRESH re-read of ``row.revoked`` under the
lock, so the two cannot interleave.

Regression at the failing layer -- the refresh-grant service path, driven through
the real ``/api/oauth/refresh`` route. The concurrent invalidation is injected
deterministically at the bcrypt-verify seam (``_verify_client_authentication``),
committed on a SEPARATE session so it lands exactly in the TOCTOU window.

Parallel-safe: unique tenant/user per test, monkeypatch-only patching, committed
seed rows keyed by a unique tenant_key (no shared mutable state, no ordering deps).
"""

from __future__ import annotations

import secrets
from uuid import uuid4

import bcrypt
import pytest
from sqlalchemy import select

from giljo_mcp.models.oauth import OAuthRefreshToken
from giljo_mcp.services.oauth_refresh_service import issue_refresh_token, new_family_id
from giljo_mcp.services.oauth_revocation_service import clear_revocation_cache
from giljo_mcp.services.oauth_service import OAuthService
from giljo_mcp.services.session_eviction import evict_user_tokens


async def _seed_user(db_manager) -> tuple[str, str, str]:
    """Create org+user (epoch 0), committed; return (user_id, username, tenant_key)."""
    from giljo_mcp.models.auth import User
    from giljo_mcp.models.organizations import Organization
    from giljo_mcp.tenant import TenantManager

    tk = TenantManager.generate_tenant_key()
    unique = uuid4().hex[:8]
    user_id = str(uuid4())
    username = f"sec9217b_user_{unique}"

    async with db_manager.get_session_async(tenant_key=tk) as session:
        org = Organization(name=f"SEC9217b Org {unique}", slug=f"sec9217b-org-{unique}", tenant_key=tk, is_active=True)
        session.add(org)
        await session.flush()
        session.add(
            User(
                id=user_id,
                username=username,
                email=f"sec9217b_{unique}@example.com",
                password_hash=bcrypt.hashpw(b"SeedPassword1!", bcrypt.gensalt()).decode("utf-8"),
                tenant_key=tk,
                role="developer",
                org_id=org.id,
                is_active=True,
                token_revocation_epoch=0,
            )
        )
        await session.commit()

    return user_id, username, tk


def _install_confidential_resolver(client_id: str, secret_hash: str):
    """Stub resolver recognizing one confidential client (test_sec9047 pattern)."""
    from giljo_mcp.services import oauth_service as svc

    prior = svc.get_client_resolver()

    def _resolver(cid: str, tenant_key: str):
        assert tenant_key
        if cid != client_id:
            return None
        return svc.ResolvedClient(
            client_id=cid,
            client_name="SEC9217b Test Client",
            redirect_uris=["http://localhost:3000/callback"],
            client_secret_hash=secret_hash,
        )

    svc.set_client_resolver(_resolver)
    return lambda: svc.set_client_resolver(prior)


async def _seed_refresh_token(db_manager, *, client_id: str, tenant_key: str, user_id: str) -> str:
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


async def _live_refresh_rows(db_manager, *, tenant_key: str, user_id: str) -> int:
    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        rows = (
            (
                await session.execute(
                    select(OAuthRefreshToken).where(
                        OAuthRefreshToken.user_id == user_id,
                        OAuthRefreshToken.tenant_key == tenant_key,
                        OAuthRefreshToken.revoked.is_(False),
                    )
                )
            )
            .scalars()
            .all()
        )
    return len(rows)


@pytest.mark.asyncio
async def test_refresh_grant_loses_to_concurrent_invalidation(api_client, db_manager, monkeypatch):
    """A session invalidation committing mid-grant (at the bcrypt-verify seam) must
    NOT leave the holder with a surviving access+refresh pair: the grant re-reads
    the revocation state under a user-first lock, detects the revoke, revokes the
    family durably, and returns invalid_grant. No new live refresh row survives."""
    from giljo_mcp.services import oauth_refresh_service as _refresh_svc

    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    # Disable the idempotency window so the grant does not short-circuit before the
    # reuse-detection gate this test targets.
    monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 0)
    clear_revocation_cache()

    user_id, _username, tk = await _seed_user(db_manager)

    client_id = str(uuid4())
    client_secret = secrets.token_urlsafe(48)
    secret_hash = bcrypt.hashpw(client_secret.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    restore = _install_confidential_resolver(client_id, secret_hash)

    # Inject the concurrent invalidation deterministically at the bcrypt-verify
    # seam: a SEPARATE, committed session bumps the epoch + revokes every refresh
    # token, landing in the exact TOCTOU window between the grant's unlocked row
    # load and its reuse-detection check.
    from giljo_mcp.models.auth import User

    orig_verify = OAuthService._verify_client_authentication
    injected = {"done": False}

    async def _verify_then_invalidate(*, client_id: str, tenant_key: str, client_secret: str | None):
        if not injected["done"]:
            injected["done"] = True
            async with db_manager.get_session_async(tenant_key=tk) as inval:
                user = (await inval.execute(select(User).where(User.id == user_id, User.tenant_key == tk))).scalar_one()
                await evict_user_tokens(inval, user)
                await inval.commit()
        return await orig_verify(client_id=client_id, tenant_key=tenant_key, client_secret=client_secret)

    monkeypatch.setattr(OAuthService, "_verify_client_authentication", staticmethod(_verify_then_invalidate))

    try:
        raw = await _seed_refresh_token(db_manager, client_id=client_id, tenant_key=tk, user_id=user_id)
        resp = await _refresh_call(api_client, refresh_token=raw, client_id=client_id, client_secret=client_secret)

        assert injected["done"], "the invalidation seam must have fired mid-grant"
        # The grant must lose: invalid_grant, no access/refresh pair minted.
        assert resp.status_code == 401, resp.text
        assert "invalid_grant" in _oauth_err_text(resp.json()).lower()
        assert "access_token" not in resp.json()

        # The family ends durably revoked -- no surviving live refresh row exists
        # for the user (neither the original nor any freshly minted rotation).
        assert await _live_refresh_rows(db_manager, tenant_key=tk, user_id=user_id) == 0
    finally:
        restore()
        clear_revocation_cache()


@pytest.mark.asyncio
async def test_idempotency_window_retry_still_returns_same_pair(api_client, db_manager, monkeypatch):
    """API-0021l unregressed: the user-first lock is taken AFTER the idempotency
    fast-path, so a same-token/same-client retry inside the window still returns
    the SAME rotated pair (not a second rotation, not reuse-detection)."""
    from giljo_mcp.services import oauth_refresh_service as _refresh_svc

    monkeypatch.setenv("JWT_SECRET", "test_secret_key")
    # A real, positive idempotency window so the retry hits the cache fast-path.
    monkeypatch.setattr(_refresh_svc, "OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", 30)
    clear_revocation_cache()

    user_id, _username, tk = await _seed_user(db_manager)

    client_id = str(uuid4())
    client_secret = secrets.token_urlsafe(48)
    secret_hash = bcrypt.hashpw(client_secret.encode("utf-8"), bcrypt.gensalt()).decode("ascii")
    restore = _install_confidential_resolver(client_id, secret_hash)
    try:
        raw = await _seed_refresh_token(db_manager, client_id=client_id, tenant_key=tk, user_id=user_id)

        first = await _refresh_call(api_client, refresh_token=raw, client_id=client_id, client_secret=client_secret)
        assert first.status_code == 200, first.text

        # Retry the SAME original token inside the window: idempotency hit, same pair.
        again = await _refresh_call(api_client, refresh_token=raw, client_id=client_id, client_secret=client_secret)
        assert again.status_code == 200, again.text
        assert again.json()["refresh_token"] == first.json()["refresh_token"]
        assert again.json()["access_token"] == first.json()["access_token"]
    finally:
        restore()
        clear_revocation_cache()
