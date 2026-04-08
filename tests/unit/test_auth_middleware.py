# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
from starlette.responses import Response

from api.middleware.auth import AuthMiddleware


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


class TestTokenExpiryHeader:
    """Tests for X-Token-Expires-In response header and request.state.token_exp."""

    @pytest.fixture
    def mock_app(self):
        app = MagicMock()
        app.state = MagicMock()
        return app

    @pytest.fixture
    def mock_auth_manager(self):
        return MagicMock()

    def _make_request(self, path="/api/projects"):
        """Create a mock Request with required attributes."""
        request = MagicMock(spec=Request)
        request.url = MagicMock()
        request.url.path = path
        request.method = "GET"
        request.client = MagicMock()
        request.client.host = "127.0.0.1"
        request.headers = Headers(raw=[])
        request.state = MagicMock()
        # Make hasattr work correctly for token_exp
        del request.state.token_exp
        return request

    @pytest.mark.asyncio
    async def test_token_exp_stashed_on_request_state(self):
        """When JWT auth succeeds with exp claim, token_exp is set on request.state."""
        future_exp = int(time.time()) + 3600  # 1 hour from now
        auth_result = {
            "authenticated": True,
            "user": "testuser",
            "user_id": "testuser",
            "tenant_key": "tk_test",
            "is_auto_login": False,
            "user_obj": None,
            "exp": future_exp,
        }

        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(return_value=auth_result)

        app = MagicMock()
        middleware = AuthMiddleware(app, auth_manager=lambda: mock_auth_mgr)

        request = self._make_request()
        # Use a real SimpleNamespace for state so we can track assignments
        import types
        request.state = types.SimpleNamespace()

        response = Response(content="ok", status_code=200)
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert request.state.token_exp == future_exp

    @pytest.mark.asyncio
    async def test_x_token_expires_in_header_set(self):
        """Response should include X-Token-Expires-In header with seconds remaining."""
        future_exp = int(time.time()) + 3600  # 1 hour from now
        auth_result = {
            "authenticated": True,
            "user": "testuser",
            "user_id": "testuser",
            "tenant_key": "tk_test",
            "is_auto_login": False,
            "user_obj": None,
            "exp": future_exp,
        }

        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(return_value=auth_result)

        app = MagicMock()
        middleware = AuthMiddleware(app, auth_manager=lambda: mock_auth_mgr)

        import types
        request = self._make_request()
        request.state = types.SimpleNamespace()

        response = Response(content="ok", status_code=200)
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "X-Token-Expires-In" in result.headers
        seconds_remaining = int(result.headers["X-Token-Expires-In"])
        # Should be approximately 3600 (give or take a few seconds for test execution)
        assert 3590 <= seconds_remaining <= 3600

    @pytest.mark.asyncio
    async def test_no_header_when_no_exp_claim(self):
        """When auth result has no exp claim, no X-Token-Expires-In header should be set."""
        auth_result = {
            "authenticated": True,
            "user": "testuser",
            "user_id": "testuser",
            "tenant_key": "tk_test",
            "is_auto_login": False,
            "user_obj": None,
            # No "exp" key
        }

        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(return_value=auth_result)

        app = MagicMock()
        middleware = AuthMiddleware(app, auth_manager=lambda: mock_auth_mgr)

        import types
        request = self._make_request()
        request.state = types.SimpleNamespace()

        response = Response(content="ok", status_code=200)
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "X-Token-Expires-In" not in result.headers

    @pytest.mark.asyncio
    async def test_expired_token_shows_zero_seconds(self):
        """When token is already expired (exp in the past), header should show 0."""
        past_exp = int(time.time()) - 100  # 100 seconds ago
        auth_result = {
            "authenticated": True,
            "user": "testuser",
            "user_id": "testuser",
            "tenant_key": "tk_test",
            "is_auto_login": False,
            "user_obj": None,
            "exp": past_exp,
        }

        mock_auth_mgr = MagicMock()
        mock_auth_mgr.authenticate_request = AsyncMock(return_value=auth_result)

        app = MagicMock()
        middleware = AuthMiddleware(app, auth_manager=lambda: mock_auth_mgr)

        import types
        request = self._make_request()
        request.state = types.SimpleNamespace()

        response = Response(content="ok", status_code=200)
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "X-Token-Expires-In" in result.headers
        assert int(result.headers["X-Token-Expires-In"]) == 0

    @pytest.mark.asyncio
    async def test_public_endpoint_no_header(self):
        """Public endpoints bypass auth and should not have X-Token-Expires-In."""
        app = MagicMock()
        middleware = AuthMiddleware(app)

        request = self._make_request(path="/api/auth/refresh")

        response = Response(content="ok", status_code=200)
        call_next = AsyncMock(return_value=response)

        result = await middleware.dispatch(request, call_next)

        assert "X-Token-Expires-In" not in result.headers


class TestTokenExpInAuthResult:
    """Tests that the auth manager propagates exp from JWT payload."""

    @pytest.mark.asyncio
    async def test_jwt_auth_result_includes_exp(self):
        """When JWT is validated, the exp claim from payload should be in auth result."""
        from src.giljo_mcp.auth_manager import AuthManager

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
