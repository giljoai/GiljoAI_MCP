# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Endpoint-layer regression for SEC-3001a Wave 2 item 6 — login lockout wiring.

Drives the real HTTP ``POST /api/auth/login`` through FastAPI DI (the failing
layer / boundary) to prove the lockout is consulted: sustained wrong-password
attempts from one (identifier, IP) lock the account, the lock then refuses even
the CORRECT password (two-sided), and the window auto-unlocks.

The per-IP login rate limiter (5/min) is neutralized via ``GILJO_RL_LOGIN`` so
the test can reach the 10-attempt lockout threshold; the lockout itself is the
behavior under test.

Parallel-safe: unique user per test; lockout rows are keyed by the unique
username so they never collide across tests.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import update

from giljo_mcp.models import User
from giljo_mcp.models.auth import LoginLockout
from giljo_mcp.models.organizations import Organization
from giljo_mcp.services.login_lockout_service import MAX_FAILED_ATTEMPTS
from giljo_mcp.tenant import TenantManager


_LOGIN_URL = "/api/auth/login"
_PASSWORD = "test_password"


async def _seed_user(db_manager) -> dict:
    suffix = uuid.uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()
    password_hash = bcrypt.hashpw(_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    username = f"ll_user_{suffix}"

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"LL Org {suffix}",
            slug=f"ll-org-{suffix}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            email=f"ll_{suffix}@example.com",
            password_hash=password_hash,
            tenant_key=tenant_key,
            role="developer",
            org_id=org.id,
        )
        session.add(user)
        await session.commit()
    return {"username": username, "tenant_key": tenant_key}


@pytest_asyncio.fixture(scope="function")
async def seeded_user(db_manager) -> dict:
    return await _seed_user(db_manager)


@pytest.mark.asyncio
async def test_login_lockout_blocks_then_auto_unlocks(api_client, seeded_user, db_manager, monkeypatch) -> None:
    """Two-sided: 10 wrong attempts lock the account (correct password then 429),
    and forcing the window into the past auto-unlocks it (correct password 200)."""
    # Take the per-IP rate limiter out of the way so we can reach the threshold.
    monkeypatch.setenv("GILJO_RL_LOGIN", "10000")
    username = seeded_user["username"]

    # Attempts 1..9 are ordinary credential failures (401).
    for i in range(MAX_FAILED_ATTEMPTS - 1):
        resp = await api_client.post(_LOGIN_URL, json={"username": username, "password": "wrong-password"})
        assert resp.status_code == 401, f"attempt {i + 1}: {resp.text}"

    # Attempt 10 crosses the threshold and trips the lock (429).
    tripped = await api_client.post(_LOGIN_URL, json={"username": username, "password": "wrong-password"})
    assert tripped.status_code == 429, tripped.text

    # Kill half: the CORRECT password is refused while locked (lockout wins).
    locked = await api_client.post(_LOGIN_URL, json={"username": username, "password": _PASSWORD})
    assert locked.status_code == 429, locked.text
    assert locked.headers.get("Retry-After")

    # Auto-unlock: shove the window into the past, then the correct password works.
    async with db_manager.get_session_async() as session:
        await session.execute(
            update(LoginLockout)
            .where(LoginLockout.identifier == username.lower())
            .values(locked_until=datetime.now(UTC) - timedelta(seconds=1))
        )
        await session.commit()

    ok = await api_client.post(_LOGIN_URL, json={"username": username, "password": _PASSWORD})
    assert ok.status_code == 200, ok.text
    assert ok.json()["username"] == username


@pytest.mark.asyncio
async def test_successful_login_does_not_accumulate_lock(api_client, seeded_user, monkeypatch) -> None:
    """Happy path: a few failures then a success clears the counter, so the next
    failures start fresh (a legitimate fat-fingering user is never locked)."""
    monkeypatch.setenv("GILJO_RL_LOGIN", "10000")
    username = seeded_user["username"]

    for _ in range(MAX_FAILED_ATTEMPTS - 2):  # 8 failures, below threshold
        resp = await api_client.post(_LOGIN_URL, json={"username": username, "password": "nope"})
        assert resp.status_code == 401, resp.text

    # Correct password succeeds and clears the (identifier, IP) counter.
    ok = await api_client.post(_LOGIN_URL, json={"username": username, "password": _PASSWORD})
    assert ok.status_code == 200, ok.text

    # The counter restarted: another sub-threshold burst still authenticates.
    for _ in range(MAX_FAILED_ATTEMPTS - 1):  # 9 fresh failures
        resp = await api_client.post(_LOGIN_URL, json={"username": username, "password": "nope"})
        assert resp.status_code == 401, resp.text
    final = await api_client.post(_LOGIN_URL, json={"username": username, "password": _PASSWORD})
    assert final.status_code == 200, final.text
