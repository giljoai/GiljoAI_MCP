# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE-6042f characterization test — locks the endpoint surface of ``api/endpoints/auth.py``.

This suite is the behavior lock for the mechanical, security-sensitive split of
``auth.py`` (980 lines) into an ``api/endpoints/auth/`` subpackage. It runs GREEN
against the unmodified module FIRST, then unchanged against the split package. It
asserts the things a behavior-preserving extraction must keep identical:

- The FULL auth route table: the set of ``(path, frozenset(methods))`` over the
  auth router is EXACTLY preserved (catches a dropped, duplicated, renamed,
  reordered, or method-shifted route — the one real failure mode of a route
  split). Shape copied from BE-6042b (commit 7eb1cb866).
- The login cookie/CSRF contract via ``_build_cookie_params``: cookie name,
  HttpOnly, SameSite, Secure, Path, Max-Age on a successful login.
- The 401 (unauthenticated ``GET /me``) and 403 (forbidden ``POST /register``
  under the member-management gate) paths.
- The load-bearing import + monkeypatch surface other modules/tests reach via
  ``api.endpoints.auth.<symbol>`` (router + the Pydantic request models +
  ``_build_cookie_params``).

The route-signature baseline below is frozen from the UNMODIFIED ``auth.py`` —
it is NOT re-derived from the live router (that would make the assertion
tautological and unable to catch a regression).
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from api.endpoints import auth as auth_endpoints
from api.endpoints.dependencies import get_auth_service
from api.exception_handlers import register_exception_handlers
from giljo_mcp.auth.dependencies import (
    get_db_session,
    require_admin,
)
from tests.helpers.route_surface import route_signatures


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Frozen baseline (snapshotted from the unmodified api/endpoints/auth.py — DO
# NOT regenerate from the live router; that would defeat the characterization).
# Paths are relative to the router (no /api/auth prefix), matching how the
# router is mounted in api/wiring/routers.py.
# ---------------------------------------------------------------------------
EXPECTED_AUTH_ROUTE_SIGNATURES = frozenset(
    {
        ("/login", frozenset({"POST"})),
        ("/logout", frozenset({"POST"})),
        ("/refresh", frozenset({"POST"})),
        ("/me", frozenset({"GET"})),
        ("/me/setup-state", frozenset({"PATCH"})),
        ("/api-keys/active", frozenset({"GET"})),
        ("/api-keys", frozenset({"GET"})),
        ("/api-keys", frozenset({"POST"})),
        ("/api-keys/{key_id}", frozenset({"DELETE"})),
        ("/register", frozenset({"POST"})),
        ("/create-first-admin", frozenset({"POST"})),
    }
)


def _route_signatures(router) -> set[tuple[str, frozenset]]:
    """Collect (path, frozenset(methods)) for every route on the router.

    Flattens fastapi 0.137 ``_IncludedRouter`` wrappers (the auth package router
    is assembled via ``include_router`` of its split sub-routers) so the set
    equals the frozen baseline captured from the pre-0.137 flat router. See
    ``tests/helpers/route_surface``.
    """
    return route_signatures(router.routes)


# --------------------------------------------------------------------------- #
# Route-table set-equality lock (the authoritative behavior guard).
# --------------------------------------------------------------------------- #


def test_full_auth_route_signature_set_equality():
    """The live auth router must produce EXACTLY the frozen signature set.

    Any dropped, added, renamed, shadowed, or method-shifted route fails here —
    the one real failure mode of a route-group split.
    """
    assert _route_signatures(auth_endpoints.router) == EXPECTED_AUTH_ROUTE_SIGNATURES


# --------------------------------------------------------------------------- #
# Import + monkeypatch surface (load-bearing for other modules and tests).
# --------------------------------------------------------------------------- #


def test_load_bearing_symbols_importable():
    """Symbols other modules/tests reach via api.endpoints.auth must resolve."""
    from api.endpoints.auth import (  # noqa: F401
        LoginRequest,
        SetupStateUpdate,
        _build_cookie_params,
        router,
    )

    assert router is auth_endpoints.router
    # Real route-function name (mission wording "create_first_admin" was loose).
    assert hasattr(auth_endpoints, "create_first_admin_user")


# --------------------------------------------------------------------------- #
# Cookie / CSRF contract on a successful login.
# --------------------------------------------------------------------------- #


def _auth_result() -> SimpleNamespace:
    return SimpleNamespace(
        token="test.jwt.token",
        user_id="33333333-3333-3333-3333-333333333333",
        username="alice",
        role="admin",
        tenant_key="tk_test",
    )


def _build_app() -> FastAPI:
    app = FastAPI()
    app.include_router(auth_endpoints.router, prefix="/api/auth")
    register_exception_handlers(app)

    auth_service = MagicMock()
    auth_service.authenticate_user = AsyncMock(return_value=_auth_result())
    auth_service.update_last_login = AsyncMock(return_value=None)
    auth_service.register_user = AsyncMock(return_value=_auth_result())

    async def _override_db():
        # Login now consults the login_lockouts table (SEC-3001a Wave 2 item 6).
        # Yield an async-capable session whose lockout lookup returns "not locked"
        # so the happy-path cookie contract below is exercised unchanged.
        session = MagicMock()
        _not_locked = MagicMock()
        _not_locked.first.return_value = None
        session.execute = AsyncMock(return_value=_not_locked)
        session.commit = AsyncMock(return_value=None)
        yield session

    async def _override_admin() -> SimpleNamespace:
        return SimpleNamespace(
            id="44444444-4444-4444-4444-444444444444",
            username="admin",
            role="admin",
            tenant_key="tk_test",
        )

    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_db_session] = _override_db
    app.dependency_overrides[require_admin] = _override_admin

    app.state._auth_service = auth_service
    return app


async def test_login_sets_httponly_access_token_cookie():
    """Login must set the access_token cookie with the security flags from
    _build_cookie_params (HttpOnly, SameSite=lax, Path=/, Max-Age=86400)."""
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "whatever"},
        )

    assert resp.status_code == 200, resp.text
    set_cookie = resp.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie
    lowered = set_cookie.lower()
    assert "httponly" in lowered
    assert "samesite=lax" in lowered
    assert "path=/" in lowered
    assert "max-age=86400" in lowered
    # default config (no secure flag) -> cookie must NOT be marked Secure
    assert "secure" not in lowered


async def test_unauthenticated_me_returns_401():
    """GET /me with no session returns a clean 401 JSON (not a 500/redirect)."""
    app = _build_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/api/auth/me")

    assert resp.status_code == 401, resp.text
    assert "detail" in resp.json()


async def test_register_forbidden_under_member_management_gate():
    """POST /register is 403 in every shipping edition (member-management gate)."""
    app = _build_app()
    transport = ASGITransport(app=app)
    with patch("api.app_state.member_management_enabled", return_value=False):
        async with AsyncClient(transport=transport, base_url="http://testserver") as client:
            resp = await client.post(
                "/api/auth/register",
                json={"username": "newseat", "password": "ValidPass123", "role": "developer"},
            )

    assert resp.status_code == 403, resp.text
