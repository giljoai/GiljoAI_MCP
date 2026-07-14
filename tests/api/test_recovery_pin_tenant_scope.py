# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression: first-admin recovery-PIN persistence must be tenant-scoped.

Bug (comms thread TENANT-CTX-CREATE-FIRST-ADMIN-RECOVERY-PIN-20260605): inside
``create_first_admin_user`` the optional recovery-PIN block opened a NEW ad-hoc
session and ran ``select(User).where(User.username == ...)`` WITHOUT setting
tenant context. Under the fail-closed guard (``GILJO_TENANT_GUARD_MODE=enforce``)
``_enforce_tenant_scope`` raised ``TenantIsolationError`` -> unhandled -> HTTP 500.
The admin row was already committed by ``auth_service.create_first_admin`` first,
so login worked on refresh, but the recovery PIN was SILENTLY never saved.

Fix: wrap the lookup/update in ``tenant_session_context(db, tenant_key)`` using
the just-created admin's tenant_key (same pattern as the refresh handler).

This exercises the FAILING layer directly -- the tenant-isolation guard against
the exact ORM statement shape the endpoint uses -- because the full endpoint path
only reaches the recovery-PIN block on a true fresh install (zero users), which is
not reproducible in the shared per-worker test DB. Parallel-safe: unique tenant
per test, guard mode via monkeypatch.setenv, no module-level state.
"""

from __future__ import annotations

import uuid

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.database import TenantIsolationError, tenant_session_context
from giljo_mcp.models import User
from giljo_mcp.models.organizations import Organization
from giljo_mcp.tenant import TenantManager


async def _seed_admin(db_manager) -> dict:
    """Create a fresh admin (+ org) in a unique tenant (no enforce during seed)."""
    suffix = uuid.uuid4().hex[:8]
    tenant_key = TenantManager.generate_tenant_key()
    password_hash = bcrypt.hashpw(b"test_password", bcrypt.gensalt()).decode("utf-8")

    async with db_manager.get_session_async() as session:
        org = Organization(
            name=f"PINctx Org {suffix}",
            slug=f"pinctx-org-{suffix}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=f"pinctx_admin_{suffix}",
            email=f"pinctx_{suffix}@example.com",
            password_hash=password_hash,
            tenant_key=tenant_key,
            role="admin",
            org_id=org.id,
        )
        session.add(user)
        await session.commit()

    return {"tenant_key": tenant_key, "username": f"pinctx_admin_{suffix}"}


@pytest_asyncio.fixture(scope="function")
async def seeded_admin(db_manager) -> dict:
    return await _seed_admin(db_manager)


@pytest.mark.asyncio
async def test_unscoped_user_lookup_raises_under_enforce(db_manager, seeded_admin, monkeypatch) -> None:
    """Reproduces the bug: the recovery-PIN block's un-scoped User query raises."""
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")

    async with db_manager.get_session_async() as db:
        with pytest.raises(TenantIsolationError):
            await db.execute(select(User).where(User.username == seeded_admin["username"]))


@pytest.mark.asyncio
async def test_recovery_pin_persists_with_tenant_context_under_enforce(db_manager, seeded_admin, monkeypatch) -> None:
    """The fix: the same lookup+update succeeds when tenant-scoped, and the PIN is saved."""
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")
    tenant_key = seeded_admin["tenant_key"]
    username = seeded_admin["username"]
    pin = b"4827"

    async with db_manager.get_session_async() as db:
        with tenant_session_context(db, tenant_key):
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            assert user is not None
            user.recovery_pin_hash = bcrypt.hashpw(pin, bcrypt.gensalt()).decode("utf-8")
            await db.commit()

    # Persisted and verifiable on a fresh tenant-scoped session.
    async with db_manager.get_session_async() as db:
        with tenant_session_context(db, tenant_key):
            result = await db.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()
            assert user is not None
            assert user.recovery_pin_hash is not None
            assert bcrypt.checkpw(pin, user.recovery_pin_hash.encode("utf-8"))
