# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Boundary (HTTP) regression tests for the IMP-5042 member-management gate.

There are two admin user-CREATION surfaces, and before IMP-5042 only one was
gated:

* ``POST /api/auth/register``  — was edition-gated.
* ``POST /api/v1/users/`` (``create_user``) — was ``require_admin`` only, with
  NO edition gate. A Solo admin could therefore add additional seats by calling
  the API directly, bypassing the hidden dashboard button (a single-user-license
  / seat-limit enforcement gap, not an auth vulnerability — the caller is already
  an authenticated admin).

Both now gate on ``api.app_state.member_management_enabled()``, which returns
``False`` for every shipping edition (CE single-user, SaaS Solo single-seat) and
will return ``True`` only for the future SaaS Team tier. These tests run at the
failing layer — the FastAPI HTTP boundary — per the CLAUDE.md mandate that a
boundary fix gets a boundary test.

They also prove the gate does NOT over-reach: the self-service password-change
endpoint still returns 200. The two live "money paths" the gate must never
catch — SaaS signup (``ProvisioningService.provision_tenant``) and first-admin
bootstrap (``AuthService.create_first_admin``) — go through different code and
stay covered by tests/saas/test_provisioning.py,
tests/api/test_auth_org_endpoints.py and
tests/saas/test_auth_create_first_admin_mode_gate.py (run alongside this module).
"""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.endpoints import auth as auth_endpoints
from api.endpoints import users as users_endpoints
from api.endpoints.dependencies import get_auth_service, get_user_service
from api.exception_handlers import register_exception_handlers
from giljo_mcp.auth.dependencies import (
    get_current_active_user,
    get_db_session,
    require_admin,
)


pytestmark = pytest.mark.asyncio

_ADMIN_ID = "11111111-1111-1111-1111-111111111111"


def _admin_user() -> SimpleNamespace:
    """A minimal authenticated admin stand-in (the gate fires before any ORM use)."""
    return SimpleNamespace(
        id=_ADMIN_ID,
        username="solo_admin",
        role="admin",
        tenant_key="tk_test_solo",
    )


def _fake_created_user() -> SimpleNamespace:
    """A fully-shaped user object so user_to_response() / RegisterUserResponse
    serialize cleanly on the 'gate-open' path (simulating a future Team tier)."""
    return SimpleNamespace(
        id="22222222-2222-2222-2222-222222222222",
        username="newseat",
        email="seat@example.com",
        first_name="New",
        last_name="Seat",
        full_name="New Seat",
        role="developer",
        tenant_key="tk_test_solo",
        is_active=True,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
        last_login=None,
    )


def _build_app() -> FastAPI:
    """Mount the auth + users routers with auth/service/db deps overridden.

    FastAPI resolves every dependency (require_admin, the services, the db
    session) before the endpoint body runs; the member-management gate then
    fires first in the body. On the 403 path the overridden services are never
    reached but must still resolve, so we provide harmless mocks.
    """
    app = FastAPI()
    app.include_router(users_endpoints.router, prefix="/api/v1/users")
    app.include_router(auth_endpoints.router, prefix="/api/auth")
    register_exception_handlers(app)

    admin = _admin_user()

    async def _override_admin() -> SimpleNamespace:
        return admin

    user_service = MagicMock()
    user_service.create_user = AsyncMock(return_value=_fake_created_user())
    user_service.auth = MagicMock()
    user_service.auth.change_password = AsyncMock(return_value=None)

    auth_service = MagicMock()
    auth_service.register_user = AsyncMock(return_value=_fake_created_user())

    async def _override_db():
        yield MagicMock()

    app.dependency_overrides[require_admin] = _override_admin
    app.dependency_overrides[get_current_active_user] = _override_admin
    app.dependency_overrides[get_user_service] = lambda: user_service
    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_db_session] = _override_db

    # Stash for assertions.
    app.state._user_service = user_service
    app.state._auth_service = auth_service
    return app


# --------------------------------------------------------------------------- #
# The gate: 403 in every shipping edition (the mandated boundary regression)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize("mode", ["ce", "saas"])
async def test_create_user_endpoint_is_403_in_all_shipping_editions(mode: str) -> None:
    """POST /api/v1/users/ must 403 in ce AND saas — closing the seat-limit gap."""
    app = _build_app()
    transport = ASGITransport(app=app)
    with patch("api.app_state.GILJO_MODE", mode):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/users/",
                json={"username": "newseat", "password": "ValidPass123", "role": "developer"},
            )
    assert resp.status_code == 403, resp.text
    detail = (resp.json().get("detail") or resp.json().get("message") or "").lower()
    assert "available" in detail
    # The service mechanism must never be invoked when the gate is closed.
    app.state._user_service.create_user.assert_not_awaited()


@pytest.mark.parametrize("mode", ["ce", "saas"])
async def test_register_endpoint_is_403_in_all_shipping_editions(mode: str) -> None:
    """POST /api/auth/register must 403 in ce AND saas (the pre-existing gate,
    now unified on the same edition-policy helper)."""
    app = _build_app()
    transport = ASGITransport(app=app)
    with patch("api.app_state.GILJO_MODE", mode):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/register",
                json={"username": "newseat", "password": "ValidPass123", "role": "developer"},
            )
    assert resp.status_code == 403, resp.text
    detail = (resp.json().get("detail") or resp.json().get("message") or "").lower()
    assert "available" in detail
    app.state._auth_service.register_user.assert_not_awaited()


# --------------------------------------------------------------------------- #
# The flip point: when the capability is enabled (future Team tier), the gate
# opens and the endpoint proceeds — proving the gate is helper-driven, not a
# hardcoded refusal.
# --------------------------------------------------------------------------- #


async def test_create_user_proceeds_when_member_management_enabled() -> None:
    app = _build_app()
    transport = ASGITransport(app=app)
    with patch("api.app_state.member_management_enabled", return_value=True):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/v1/users/",
                json={"username": "newseat", "password": "ValidPass123", "role": "developer"},
            )
    assert resp.status_code != 403, resp.text
    app.state._user_service.create_user.assert_awaited_once()


async def test_register_proceeds_when_member_management_enabled() -> None:
    app = _build_app()
    transport = ASGITransport(app=app)
    fake_limiter = MagicMock()
    fake_limiter.check_rate_limit = AsyncMock(return_value=None)
    with (
        patch("api.app_state.member_management_enabled", return_value=True),
        patch("api.endpoints.auth.registration.get_rate_limiter", return_value=fake_limiter),
    ):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/auth/register",
                json={"username": "newseat", "password": "ValidPass123", "role": "developer"},
            )
    assert resp.status_code != 403, resp.text
    app.state._auth_service.register_user.assert_awaited_once()


# --------------------------------------------------------------------------- #
# The gate must NOT over-reach: changing YOUR OWN password is not seat creation.
# --------------------------------------------------------------------------- #


async def test_self_password_change_is_not_gated() -> None:
    """PUT /api/v1/users/{id}/password (self-service) stays 200 — it is the
    user-facing password rotation the matrix requires in every edition, and the
    member-management gate must never touch it."""
    app = _build_app()
    transport = ASGITransport(app=app)
    with patch("api.app_state.GILJO_MODE", "saas"):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.put(
                f"/api/v1/users/{_ADMIN_ID}/password",
                json={"old_password": "OldPass123", "new_password": "NewPass456"},
            )
    assert resp.status_code == 200, resp.text
    app.state._user_service.auth.change_password.assert_awaited_once()


# --------------------------------------------------------------------------- #
# Capability invariant: documents the single edition-wide flip point.
# --------------------------------------------------------------------------- #


async def test_member_management_disabled_for_all_current_editions() -> None:
    """No shipping edition supports multi-seat administration yet. When SaaS Team
    ships, this is the one place that flips — and the two creation endpoints open
    with it (see the 'proceeds_when_enabled' tests above)."""
    from api.app_state import member_management_enabled

    assert member_management_enabled() is False
