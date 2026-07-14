# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9152 -- the admin Settings cookie-domain whitelist must actually drive
cookie-scoping enforcement.

Bug (BE-6263b audit finding #2): the admin Settings UI writes
``cookie_domain_whitelist`` to the DB-backed tenant settings store
(``SettingsService`` -> ``Settings.settings_data['security']``), but the
enforcement in ``api/endpoints/auth/session.py`` (``_build_cookie_params``, run by
login/logout/refresh) read a *separate* file-based ``config.yaml`` store that was
never synced. A self-hoster who whitelisted a domain via the panel saw success on
the GET round-trip, but the value never reached ``_build_cookie_params`` -- so
cross-domain cookie auth silently did nothing.

Failing layer = the session auth endpoints. This test drives the real HTTP
``/api/auth/refresh`` endpoint (the simplest of the three cookie-setting seams: it
sources ``tenant_key`` from the signed JWT and mints a fresh access_token cookie
via the same ``_build_cookie_params`` path as login). Before the fix, a domain in
the DB store has NO effect on the Set-Cookie ``Domain`` attribute; after the fix,
the DB-store domain is honored.

Two-sided:
- honored: a domain written to the DB store IS applied as the cookie Domain.
- default unchanged: with an untouched panel (empty DB store), a domain-name host
  still gets NO cookie Domain (fail-secure origin-matching), exactly as before.

Parallel-safe: each test seeds its own unique tenant + org + user; no
module-level mutable state; ``db_manager`` sessions are the test-scoped DB.

Project: BE-9152.
"""

from __future__ import annotations

import uuid

import bcrypt
import pytest

from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.models import User
from giljo_mcp.models.organizations import Organization
from giljo_mcp.services.settings_service import SettingsService
from giljo_mcp.tenant import TenantManager


_REFRESH_URL = "/api/auth/refresh"
_WHITELISTED_HOST = "myapp.example.com"


async def _seed_user(db_manager) -> dict:
    """Create a fresh active user (+ org) in a unique tenant. Returns ids + valid token."""
    suffix = uuid.uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()
    password_hash = bcrypt.hashpw(b"test_password", bcrypt.gensalt()).decode("utf-8")

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"BE9152 Org {suffix}",
            slug=f"be9152-org-{suffix}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"be9152_user_{suffix}",
            email=f"be9152_{suffix}@example.com",
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
        username=f"be9152_user_{suffix}",
        role="developer",
        tenant_key=tenant_key,
    )
    return {"tenant_key": tenant_key, "user_id": user_id, "token": token}


async def _write_whitelist(db_manager, tenant_key: str, domains: list[str]) -> None:
    """Write the cookie-domain whitelist through the SAME store the admin UI writes."""
    async with db_manager.get_session_async() as session:
        service = SettingsService(session, tenant_key)
        await service.update_settings("security", {"cookie_domain_whitelist": domains})


def _domain_in_set_cookie(set_cookie: str) -> str | None:
    """Extract the Domain attribute value from a Set-Cookie header, or None."""
    for part in set_cookie.split(";"):
        key, _, value = part.strip().partition("=")
        if key.lower() == "domain":
            return value.lower()
    return None


@pytest.mark.asyncio
async def test_db_whitelisted_domain_is_honored_by_enforcement(api_client, db_manager) -> None:
    """A domain written via the admin Settings store IS applied as the cookie Domain.

    RED before the fix: enforcement read only the file-based config, so the
    DB-written domain never reached ``_build_cookie_params`` and no Domain was set.
    """
    seeded = await _seed_user(db_manager)
    await _write_whitelist(db_manager, seeded["tenant_key"], [_WHITELISTED_HOST])

    api_client.cookies.set("access_token", seeded["token"])
    resp = await api_client.post(_REFRESH_URL, headers={"host": _WHITELISTED_HOST})

    assert resp.status_code == 200, resp.text
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie, set_cookie
    assert _domain_in_set_cookie(set_cookie) == _WHITELISTED_HOST, (
        f"DB-store whitelist must drive the cookie Domain; got: {set_cookie!r}"
    )


@pytest.mark.asyncio
async def test_untouched_panel_leaves_default_behavior_unchanged(api_client, db_manager) -> None:
    """With an empty (never-touched) whitelist store, a domain-name host still gets
    NO cookie Domain -- fail-secure origin-matching, exactly as before the fix."""
    seeded = await _seed_user(db_manager)  # no whitelist written

    api_client.cookies.set("access_token", seeded["token"])
    resp = await api_client.post(_REFRESH_URL, headers={"host": _WHITELISTED_HOST})

    assert resp.status_code == 200, resp.text
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie, set_cookie
    assert _domain_in_set_cookie(set_cookie) is None, (
        f"an untouched panel must not scope the cookie to any domain; got: {set_cookie!r}"
    )
