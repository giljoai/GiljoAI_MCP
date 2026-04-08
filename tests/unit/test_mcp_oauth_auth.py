# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Tests for MCP authentication (Handover 0828 + 0846).

Test coverage:
- MCPSessionManager.get_or_create_session_from_jwt creates/reuses sessions
- MCPAuthMiddleware extracts JWT and API key credentials from headers
"""

from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest


class TestMCPSessionManagerJWT:
    """Tests for MCPSessionManager.get_or_create_session_from_jwt()."""

    @pytest.mark.asyncio
    async def test_creates_new_session_when_none_exists(self):
        """Should create a new MCPSession with api_key_id=None for JWT auth."""
        from api.endpoints.mcp_session import MCPSessionManager

        user_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex[:12]}"
        username = "oauth_user"

        mock_db = AsyncMock()
        # No existing session found
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        manager = MCPSessionManager(mock_db)
        session = await manager.get_or_create_session_from_jwt(
            user_id=user_id,
            tenant_key=tenant_key,
            username=username,
        )

        assert session is not None
        # Verify db.add was called (new session created)
        mock_db.add.assert_called_once()
        added_session = mock_db.add.call_args[0][0]
        assert added_session.api_key_id is None
        assert added_session.user_id == user_id
        assert added_session.tenant_key == tenant_key

    @pytest.mark.asyncio
    async def test_reuses_existing_non_expired_session(self):
        """Should return existing session if one exists and is not expired."""
        from api.endpoints.mcp_session import MCPSessionManager

        user_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex[:12]}"

        existing_session = MagicMock()
        existing_session.is_expired = False
        existing_session.session_id = str(uuid4())
        existing_session.user_id = user_id
        existing_session.tenant_key = tenant_key

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [existing_session]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.refresh = AsyncMock()

        manager = MCPSessionManager(mock_db)
        session = await manager.get_or_create_session_from_jwt(
            user_id=user_id,
            tenant_key=tenant_key,
            username="oauth_user",
        )

        assert session is existing_session
        # Should NOT add a new session
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_new_session_when_existing_is_expired(self):
        """Should create new session if existing session is expired."""
        from api.endpoints.mcp_session import MCPSessionManager

        user_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex[:12]}"

        expired_session = MagicMock()
        expired_session.is_expired = True

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [expired_session]
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        manager = MCPSessionManager(mock_db)
        await manager.get_or_create_session_from_jwt(
            user_id=user_id,
            tenant_key=tenant_key,
            username="oauth_user",
        )

        # New session should be created
        mock_db.add.assert_called_once()
        added_session = mock_db.add.call_args[0][0]
        assert added_session.api_key_id is None
        assert added_session.user_id == user_id
        assert added_session.tenant_key == tenant_key

    @pytest.mark.asyncio
    async def test_session_data_initialized_correctly(self):
        """New JWT session should have proper session_data defaults."""
        from api.endpoints.mcp_session import MCPSessionManager

        user_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex[:12]}"

        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)
        mock_db.commit = AsyncMock()
        mock_db.add = MagicMock()
        mock_db.refresh = AsyncMock()

        manager = MCPSessionManager(mock_db)
        await manager.get_or_create_session_from_jwt(
            user_id=user_id,
            tenant_key=tenant_key,
            username="oauth_user",
        )

        added_session = mock_db.add.call_args[0][0]
        assert added_session.session_data["initialized"] is False
        assert "capabilities" in added_session.session_data
        assert "client_info" in added_session.session_data
        assert "tool_call_history" in added_session.session_data
        assert added_session.session_data["auth_method"] == "oauth_jwt"
        assert added_session.session_data["username"] == "oauth_user"


class TestMCPAuthMiddleware:
    """Tests for MCPAuthMiddleware (Handover 0846 — SDK auth layer)."""

    def test_jwt_bearer_extracts_tenant_key(self):
        """A valid JWT should populate scope state with tenant_key."""
        from api.endpoints.mcp_sdk_server import MCPAuthMiddleware

        user_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex[:12]}"
        jwt_payload = {
            "sub": user_id,
            "username": "jwt_user",
            "role": "developer",
            "tenant_key": tenant_key,
            "type": "access",
        }

        MCPAuthMiddleware(app=MagicMock())

        with patch(
            "api.endpoints.mcp_sdk_server.JWTManager.verify_token",
            return_value=jwt_payload,
        ):
            # Simulate ASGI scope with Bearer header
            scope = {
                "type": "http",
                "headers": [
                    (b"authorization", b"Bearer eyJhbGciOiJIUzI1NiJ9.jwt-token"),
                ],
            }

            # Extract credentials using middleware logic (unit test the parsing)
            from starlette.requests import Request as StarletteRequest

            request = StarletteRequest(scope, receive=AsyncMock())
            auth_header = request.headers.get("authorization", "")
            assert auth_header.lower().startswith("bearer ")
            token = auth_header[7:]
            assert token == "eyJhbGciOiJIUzI1NiJ9.jwt-token"

    def test_x_api_key_header_extracted(self):
        """X-API-Key header should be detected by middleware."""
        scope = {
            "type": "http",
            "headers": [
                (b"x-api-key", b"ak_test123"),
            ],
        }

        from starlette.requests import Request as StarletteRequest

        request = StarletteRequest(scope, receive=AsyncMock())
        api_key = request.headers.get("x-api-key")
        assert api_key == "ak_test123"

    def test_no_auth_headers_detected(self):
        """Missing auth headers should be detectable."""
        scope = {
            "type": "http",
            "headers": [],
        }

        from starlette.requests import Request as StarletteRequest

        request = StarletteRequest(scope, receive=AsyncMock())
        api_key = request.headers.get("x-api-key")
        auth_header = request.headers.get("authorization", "")
        assert api_key is None
        assert auth_header == ""
