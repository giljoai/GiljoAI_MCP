# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [SaaS] SaaS Edition only -- excluded from Community Edition builds.

"""Integration tests for SAAS-007 first-login org-setup wizard.

Regression guard for the 2026-04-24 live-demo 405 Method Not Allowed:

    16:12:21 PUT /api/saas/org-setup HTTP/1.1" 405 Method Not Allowed

Root cause was the router decorator pinning the PUT handler to the trailing-
slash path ("/") while the frontend called the no-slash form. FastAPI's
``redirect_slashes`` only rewrites GET/HEAD, so the verb was rejected.

These tests exercise the real router + real OrgService + real OrgRepository
against the integration Postgres. They assert:
 1. The wizard route exists on the canonical URL ``/api/saas/org-setup`` (no
    trailing slash) -- the form the frontend sends.
 2. A successful PUT flips ``org_setup_complete=True`` on the user's org row
    and merges ``timezone`` into ``settings`` JSONB.
 3. GET /status reflects the write -- ``needs_setup=False`` after setup.
 4. Cross-tenant isolation: a user from tenant B cannot mutate an org
    belonging to tenant A by spoofing its UUID.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.saas_endpoints.org_setup import router as org_setup_router
from giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from giljo_mcp.models import User
from giljo_mcp.models.organizations import Organization
from giljo_mcp.tenant import TenantManager


# ---------------------------------------------------------------------------
# App + client fixtures
# ---------------------------------------------------------------------------


def _build_app_with_overrides(db_session: AsyncSession, user: User) -> FastAPI:
    """Build a minimal FastAPI app mounting the real org-setup router.

    The mount prefix mirrors ``api/saas_endpoints/__init__.py``:
    ``/api/saas/org-setup``. Auth and DB dependencies are overridden to use
    the integration ``db_session`` and the supplied ``user``.
    """
    app = FastAPI()
    app.include_router(org_setup_router, prefix="/api/saas/org-setup")

    async def _override_user() -> User:
        return user

    async def _override_db() -> AsyncIterator[AsyncSession]:
        yield db_session

    app.dependency_overrides[get_current_active_user] = _override_user
    app.dependency_overrides[get_db_session] = _override_db
    return app


@pytest_asyncio.fixture
async def second_tenant_user(db_session: AsyncSession) -> User:
    """Create an isolated second tenant + user for cross-tenant checks."""
    unique = uuid4().hex[:8]
    tenant_key_b = TenantManager.generate_tenant_key()
    org_b = Organization(
        name=f"Tenant B Org {unique}",
        slug=f"tenant-b-org-{unique}",
        tenant_key=tenant_key_b,
        is_active=True,
    )
    db_session.add(org_b)
    await db_session.flush()
    user_b = User(
        username=f"tenant_b_user_{unique}",
        email=f"tenant_b_{unique}@example.com",
        tenant_key=tenant_key_b,
        role="developer",
        password_hash="hashed_password",
        org_id=org_b.id,
    )
    db_session.add(user_b)
    await db_session.commit()
    await db_session.refresh(user_b)
    return user_b


# ---------------------------------------------------------------------------
# Regression: PUT on the no-slash URL succeeds (the 405-reproducing path)
# ---------------------------------------------------------------------------


class TestPutOrgSetupNoTrailingSlashRegression:
    """The live demo received 405 on ``PUT /api/saas/org-setup`` (no slash)."""

    @pytest.mark.asyncio
    async def test_put_without_trailing_slash_returns_200(self, db_session: AsyncSession, test_user: User):
        """Canonical wizard call: PUT /api/saas/org-setup must not 405."""
        app = _build_app_with_overrides(db_session, test_user)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/saas/org-setup",
                json={"org_name": "Giljo Demo", "timezone": "America/New_York"},
            )
        assert resp.status_code == 200, f"expected 200, got {resp.status_code}: body={resp.text}"
        body = resp.json()
        assert body["message"] == "Organization setup complete"
        assert body["org_id"] == test_user.org_id

    @pytest.mark.asyncio
    async def test_put_with_trailing_slash_redirects_to_canonical(self, db_session: AsyncSession, test_user: User):
        """Trailing-slash form redirects (307) to the canonical no-slash URL.

        FastAPI's ``redirect_slashes`` rewrites the unmatched slash variant
        for any verb including PUT. Clients that follow the redirect land
        on the canonical handler. We assert the redirect target rather than
        a 200 body so the canonical URL remains the single source of truth.
        """
        app = _build_app_with_overrides(db_session, test_user)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/saas/org-setup/",
                json={"org_name": "Giljo Demo Slash", "timezone": "UTC"},
            )
        assert resp.status_code == 307, f"expected 307 redirect, got {resp.status_code}: body={resp.text}"
        assert resp.headers["location"].rstrip("/").endswith("/api/saas/org-setup"), (
            f"unexpected redirect target: {resp.headers.get('location')}"
        )


# ---------------------------------------------------------------------------
# Happy path: GET status -> PUT -> GET status round trip
# ---------------------------------------------------------------------------


class TestOrgSetupRoundTrip:
    """Full wizard flow: status=needs_setup -> PUT -> status=completed."""

    @pytest.mark.asyncio
    async def test_status_completes_after_put(self, db_session: AsyncSession, test_user: User):
        app = _build_app_with_overrides(db_session, test_user)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            # Step 1: wizard-needed check -> True (fresh org)
            status_before = await client.get("/api/saas/org-setup/status")
            assert status_before.status_code == 200
            assert status_before.json()["needs_setup"] is True

            # Step 2: complete setup via canonical no-slash URL
            put_resp = await client.put(
                "/api/saas/org-setup",
                json={"org_name": "Round Trip Org", "timezone": "Europe/Stockholm"},
            )
            assert put_resp.status_code == 200

            # Step 3: status now reports complete
            status_after = await client.get("/api/saas/org-setup/status")
            assert status_after.status_code == 200
            assert status_after.json()["needs_setup"] is False
            assert status_after.json()["org_name"] == "Round Trip Org"

        # Step 4: DB-level verification (no cached ORM state)
        await db_session.commit()
        result = await db_session.execute(select(Organization).where(Organization.id == test_user.org_id))
        org = result.scalar_one()
        assert org.org_setup_complete is True
        assert org.name == "Round Trip Org"
        assert org.settings.get("timezone") == "Europe/Stockholm"


# ---------------------------------------------------------------------------
# Tenant isolation: tenant B cannot mutate tenant A's org by spoofing user
# ---------------------------------------------------------------------------


class TestOrgSetupTenantIsolation:
    """Write path filters by tenant_key -- no cross-tenant mutation."""

    @pytest.mark.asyncio
    async def test_second_tenant_cannot_see_or_mutate_first_tenants_org(
        self,
        db_session: AsyncSession,
        test_user: User,
        second_tenant_user: User,
    ):
        """Tenant B user hitting PUT writes their own org, not tenant A's."""
        assert test_user.tenant_key != second_tenant_user.tenant_key
        assert test_user.org_id != second_tenant_user.org_id

        # Act as tenant B and send PUT. The endpoint uses the caller's
        # own org_id + tenant_key, so tenant B's write must not touch
        # tenant A's row under any circumstance.
        app_b = _build_app_with_overrides(db_session, second_tenant_user)
        async with AsyncClient(transport=ASGITransport(app=app_b), base_url="http://test") as client_b:
            resp = await client_b.put(
                "/api/saas/org-setup",
                json={"org_name": "Tenant B Display", "timezone": "UTC"},
            )
        assert resp.status_code == 200
        assert resp.json()["org_id"] == second_tenant_user.org_id

        await db_session.commit()

        # Tenant A's org must remain unchanged (still needs_setup=True).
        result_a = await db_session.execute(
            select(Organization).where(
                Organization.id == test_user.org_id,
                Organization.tenant_key == test_user.tenant_key,
            )
        )
        org_a = result_a.scalar_one()
        assert org_a.org_setup_complete is False, "Tenant A's org must not be mutated by a tenant B PUT"

        # Tenant B's org flipped to completed and got the new display name.
        result_b = await db_session.execute(
            select(Organization).where(
                Organization.id == second_tenant_user.org_id,
                Organization.tenant_key == second_tenant_user.tenant_key,
            )
        )
        org_b = result_b.scalar_one()
        assert org_b.org_setup_complete is True
        assert org_b.name == "Tenant B Display"

    @pytest.mark.asyncio
    async def test_put_404_when_org_id_belongs_to_other_tenant(
        self,
        db_session: AsyncSession,
        test_user: User,
        second_tenant_user: User,
    ):
        """If the caller's User points at an org outside their tenant_key,
        the service-layer tenant filter rejects with 404 rather than silently
        updating. This guards against a forged JWT with a spoofed org_id."""
        # Manufacture a poisoned user in the DB: tenant B's tenant_key, but
        # tenant A's org_id. The poisoned row lets the FK to organizations
        # resolve while forcing the service's tenant filter to miss.
        poisoned_suffix = uuid4().hex[:8]
        poisoned = User(
            username=f"poisoned_{poisoned_suffix}",
            email=f"poisoned_{poisoned_suffix}@example.com",
            tenant_key=second_tenant_user.tenant_key,
            role="developer",
            password_hash="hashed_password",
            org_id=test_user.org_id,  # Cross-tenant pointer
        )
        db_session.add(poisoned)
        await db_session.commit()
        await db_session.refresh(poisoned)

        app = _build_app_with_overrides(db_session, poisoned)
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            resp = await client.put(
                "/api/saas/org-setup",
                json={"org_name": "Should Not Apply", "timezone": "UTC"},
            )
        assert resp.status_code == 404, f"cross-tenant PUT must return 404, got {resp.status_code}: {resp.text}"

        # Re-read tenant A's org -- must still be pristine.
        result = await db_session.execute(select(Organization).where(Organization.id == test_user.org_id))
        org_a = result.scalar_one()
        assert org_a.org_setup_complete is False
        assert org_a.name != "Should Not Apply"
