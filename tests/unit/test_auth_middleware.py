# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Unit tests for AuthMiddleware (api/middleware/auth.py)

Tests for:
1. /api/auth/refresh is treated as a public endpoint (bypass auth)
2. X-Token-Expires-In response header is set when JWT token has exp claim
3. token_exp is stashed on request.state for downstream use

Following TDD principles - tests written BEFORE implementation.
"""

import time
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Request
from starlette.datastructures import Headers

from api.middleware.auth import AuthMiddleware, register_public_path_prefix


# ---------------------------------------------------------------------------
# Pure-ASGI driver (BE-6063c): AuthMiddleware is now pure ASGI
# (``__call__(scope, receive, send)``), so the unit tests drive it through the
# ASGI protocol directly instead of the old ``dispatch(request, call_next)``
# signature. ``_drive`` runs the middleware against an in-memory ASGI app that
# returns a 200, captures the response start message, and exposes the response
# headers — preserving the exact assertions the prior tests made.
# ---------------------------------------------------------------------------


class _CapturedResponse:
    """Minimal response view: status + headers captured from the ASGI send."""

    def __init__(self) -> None:
        self.status_code: int | None = None
        self.headers: Headers = Headers(raw=[])


async def _drive(middleware: AuthMiddleware, path: str, method: str = "GET", headers=None) -> _CapturedResponse:
    """Run an AuthMiddleware instance through the ASGI protocol for one request."""
    raw_headers = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    app_state = MagicMock()
    scope = {
        "type": "http",
        "method": method,
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": raw_headers,
        "client": ("127.0.0.1", 12345),
        "scheme": "http",
        "server": ("test", 80),
        "app": MagicMock(state=app_state),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    captured = _CapturedResponse()

    async def send(message):
        if message["type"] == "http.response.start":
            captured.status_code = message["status"]
            captured.headers = Headers(raw=message["headers"])

    async def downstream_app(scope, receive, send):
        await send({"type": "http.response.start", "status": 200, "headers": [(b"content-type", b"text/plain")]})
        await send({"type": "http.response.body", "body": b"ok"})

    middleware.app = downstream_app
    await middleware(scope, receive, send)
    return captured


class TestPublicEndpoints:
    """Tests that certain endpoints bypass authentication."""

    def _make_middleware(self):
        """Create an AuthMiddleware instance with a mock app."""
        app = MagicMock()
        return AuthMiddleware(app)

    def test_refresh_endpoint_is_public(self):
        """The /api/auth/refresh endpoint should be public (handles its own auth)."""
        middleware = self._make_middleware()
        assert middleware._is_public_endpoint("/api/auth/refresh") is True

    def test_refresh_endpoint_with_trailing_slash_is_public(self):
        """The /api/auth/refresh/ endpoint should also be public via startswith."""
        middleware = self._make_middleware()
        # startswith will match /api/auth/refresh/ since it starts with /api/auth/refresh
        assert middleware._is_public_endpoint("/api/auth/refresh/") is True

    def test_login_endpoint_still_public(self):
        """Verify existing public endpoint /api/auth/login is still public."""
        middleware = self._make_middleware()
        assert middleware._is_public_endpoint("/api/auth/login") is True

    def test_private_endpoint_not_public(self):
        """Verify that non-public endpoints are not treated as public."""
        middleware = self._make_middleware()
        assert middleware._is_public_endpoint("/api/projects") is False

    def test_private_edition_public_prefix_registry(self):
        """Private edition modules can register additional public prefixes."""
        register_public_path_prefix("/private/public/")
        middleware = self._make_middleware()
        assert middleware._is_public_endpoint("/private/public/register") is True
        assert middleware._is_public_endpoint("/private/other") is False


class TestTokenExpiryHeader:
    """Tests for X-Token-Expires-In response header and request.state.token_exp."""

    @staticmethod
    def _authed_result(exp_present: bool, exp_value: int | None = None) -> dict:
        result = {
            "authenticated": True,
            "user": "testuser",
            "user_id": "testuser",
            "tenant_key": "tk_test",
            "is_auto_login": False,
            "user_obj": None,
        }
        if exp_present:
            result["exp"] = exp_value
        return result

    @pytest.mark.asyncio
    async def test_token_exp_stashed_on_request_state(self):
        """When JWT auth succeeds with exp claim, token_exp is set on scope state."""
        future_exp = int(time.time()) + 3600  # 1 hour from now
        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(return_value=self._authed_result(True, future_exp))

        captured_state: dict = {}

        async def downstream_app(scope, receive, send):
            # Auth writes request.state (backed by scope["state"]) before dispatch.
            captured_state.update(scope.get("state", {}))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = AuthMiddleware(downstream_app, auth_manager=lambda: mock_auth_mgr)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/projects",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
            "app": MagicMock(state=MagicMock()),
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            pass

        await middleware(scope, receive, send)

        assert captured_state.get("token_exp") == future_exp
        assert captured_state.get("tenant_key") == "tk_test"

    @pytest.mark.asyncio
    async def test_x_token_expires_in_header_set(self):
        """Response should include X-Token-Expires-In header with seconds remaining."""
        future_exp = int(time.time()) + 3600  # 1 hour from now
        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(return_value=self._authed_result(True, future_exp))

        middleware = AuthMiddleware(MagicMock(), auth_manager=lambda: mock_auth_mgr)
        result = await _drive(middleware, "/api/projects")

        assert "X-Token-Expires-In" in result.headers
        seconds_remaining = int(result.headers["X-Token-Expires-In"])
        # Should be approximately 3600 (give or take a few seconds for test execution)
        assert 3590 <= seconds_remaining <= 3600

    @pytest.mark.asyncio
    async def test_no_header_when_no_exp_claim(self):
        """When auth result has no exp claim, no X-Token-Expires-In header should be set."""
        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(return_value=self._authed_result(False))

        middleware = AuthMiddleware(MagicMock(), auth_manager=lambda: mock_auth_mgr)
        result = await _drive(middleware, "/api/projects")

        assert "X-Token-Expires-In" not in result.headers

    @pytest.mark.asyncio
    async def test_expired_token_shows_zero_seconds(self):
        """When token is already expired (exp in the past), header should show 0."""
        past_exp = int(time.time()) - 100  # 100 seconds ago
        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(return_value=self._authed_result(True, past_exp))

        middleware = AuthMiddleware(MagicMock(), auth_manager=lambda: mock_auth_mgr)
        result = await _drive(middleware, "/api/projects")

        assert "X-Token-Expires-In" in result.headers
        assert int(result.headers["X-Token-Expires-In"]) == 0

    @pytest.mark.asyncio
    async def test_public_endpoint_no_header(self):
        """Public endpoints bypass auth and should not have X-Token-Expires-In."""
        middleware = AuthMiddleware(MagicMock())
        result = await _drive(middleware, "/api/auth/refresh")

        assert "X-Token-Expires-In" not in result.headers


class TestMissingTenantKeyFallback:
    """BE-9119: authenticated request with no tenant_key falls back to the default.

    Regression at the failing layer (the auth middleware fallback branch,
    api/middleware/auth.py). Before the fix, that branch did
    ``from api.dependencies import _get_default_tenant_key`` — but the
    ``api.dependencies`` PACKAGE re-exports only get_tenant_key/get_db, never the
    private ``_get_default_tenant_key``, so the import raised ImportError and the
    branch returned a guaranteed 500 for any authenticated principal that arrived
    without a tenant_key. This test drives that exact branch; it fails (ImportError)
    against the pre-fix import and passes once the import targets
    ``api.dependencies.core``.
    """

    @pytest.mark.asyncio
    async def test_authenticated_missing_tenant_key_uses_default(self, monkeypatch):
        import api.app_state

        # Deterministic + xdist-safe: neutralise the config branch of
        # _get_default_tenant_key (some suites set state.config on the shared
        # global) and pin the env default. monkeypatch auto-reverts both.
        monkeypatch.setattr(api.app_state.state, "config", None, raising=False)
        monkeypatch.setenv("DEFAULT_TENANT_KEY", "tk_fallback_default")

        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(
            return_value={
                "authenticated": True,
                "user": "testuser",
                "user_id": "testuser",
                "tenant_key": None,  # authenticated but NO tenant_key -> fallback branch
                "is_auto_login": False,
                "user_obj": None,
            }
        )

        captured_state: dict = {}

        async def downstream_app(scope, receive, send):
            captured_state.update(scope.get("state", {}))
            await send({"type": "http.response.start", "status": 200, "headers": []})
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = AuthMiddleware(downstream_app, auth_manager=lambda: mock_auth_mgr)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/api/projects",
            "headers": [],
            "client": ("127.0.0.1", 12345),
            "scheme": "http",
            "app": MagicMock(state=MagicMock()),
        }

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(message):
            pass

        await middleware(scope, receive, send)

        # Fallback resolved to the configured default instead of raising a 500.
        assert captured_state.get("tenant_key") == "tk_fallback_default"


class TestTokenExpInAuthResult:
    """Tests that the auth manager propagates exp from JWT payload."""

    @pytest.mark.asyncio
    async def test_jwt_auth_result_includes_exp(self):
        """When JWT is validated, the exp claim from payload should be in auth result."""
        from giljo_mcp.auth_manager import AuthManager

        auth_mgr = AuthManager()

        # Create a JWT with known exp
        import jwt as pyjwt

        future_exp = int(time.time()) + 3600
        payload = {
            "username": "testuser",
            "tenant_key": "tk_test",
            "exp": future_exp,
        }
        token = pyjwt.encode(payload, auth_mgr.jwt_secret, algorithm="HS256")

        # Create mock request with the token in Authorization header
        request = MagicMock(spec=Request)
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = {
            "Authorization": f"Bearer {token}",
            "cookie": "",
        }
        request.app = MagicMock()
        request.app.state = MagicMock()
        request.app.state.db_manager = None

        result = await auth_mgr.authenticate_request(request)

        assert result["authenticated"] is True
        assert result["exp"] == future_exp
