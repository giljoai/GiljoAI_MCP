"""Tests for MCP endpoint OAuth JWT authentication (Handover 0828 Phase 4).

Verifies that the MCP HTTP endpoint accepts both OAuth JWT tokens and
API keys for authentication, with proper session creation for each.

Test coverage:
- JWT Bearer token creates session via get_or_create_session_from_jwt
- API key Bearer token still works (backward compatibility)
- X-API-Key header still works (backward compatibility)
- Invalid JWT falls back to API key authentication
- get_or_create_session_from_jwt creates new session with api_key_id=None
- get_or_create_session_from_jwt reuses existing non-expired session
- get_or_create_session_from_jwt filters by tenant_key
"""

from datetime import datetime, timedelta, timezone
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
        session = await manager.get_or_create_session_from_jwt(
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


class TestMCPEndpointAuth:
    """Tests for mcp_endpoint() authentication logic with JWT support."""

    @pytest.mark.asyncio
    async def test_jwt_bearer_token_creates_session(self):
        """A valid JWT in Authorization: Bearer should authenticate via JWT path."""
        from api.endpoints.mcp_http import mcp_endpoint

        user_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex[:12]}"
        jwt_payload = {
            "sub": user_id,
            "username": "jwt_user",
            "role": "developer",
            "tenant_key": tenant_key,
            "type": "access",
        }

        mock_session = MagicMock()
        mock_session.session_id = str(uuid4())
        mock_session.tenant_key = tenant_key
        mock_session.api_key_id = None

        rpc_request = MagicMock()
        rpc_request.method = "initialize"
        rpc_request.params = {}
        rpc_request.id = 1

        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_db = AsyncMock()

        with (
            patch(
                "api.endpoints.mcp_http.JWTManager.verify_token",
                return_value=jwt_payload,
            ) as mock_verify,
            patch(
                "api.endpoints.mcp_http.MCPSessionManager",
            ) as MockSessionManagerClass,
            patch(
                "api.endpoints.mcp_http.handle_initialize",
                new_callable=AsyncMock,
                return_value={"protocolVersion": "2024-11-05"},
            ),
        ):
            mock_manager = AsyncMock()
            mock_manager.get_or_create_session_from_jwt = AsyncMock(return_value=mock_session)
            MockSessionManagerClass.return_value = mock_manager

            result = await mcp_endpoint(
                rpc_request=rpc_request,
                request=mock_request,
                x_api_key=None,
                authorization="Bearer eyJhbGciOiJIUzI1NiJ9.long-jwt-token",
                db=mock_db,
            )

            mock_verify.assert_called_once_with("eyJhbGciOiJIUzI1NiJ9.long-jwt-token")
            mock_manager.get_or_create_session_from_jwt.assert_called_once_with(
                user_id=user_id,
                tenant_key=tenant_key,
                username="jwt_user",
            )

    @pytest.mark.asyncio
    async def test_api_key_bearer_token_still_works(self):
        """When JWT verification fails, Bearer token should fall back to API key auth."""
        from fastapi import HTTPException

        from api.endpoints.mcp_http import mcp_endpoint

        api_key_value = "ak_" + uuid4().hex[:20]
        mock_session = MagicMock()
        mock_session.session_id = str(uuid4())
        mock_session.tenant_key = "tk_test"
        mock_session.api_key_id = str(uuid4())

        rpc_request = MagicMock()
        rpc_request.method = "initialize"
        rpc_request.params = {}
        rpc_request.id = 1

        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_db = AsyncMock()

        with (
            patch(
                "api.endpoints.mcp_http.JWTManager.verify_token",
                side_effect=HTTPException(status_code=401, detail="Invalid token"),
            ),
            patch(
                "api.endpoints.mcp_http.MCPSessionManager",
            ) as MockSessionManagerClass,
            patch(
                "api.endpoints.mcp_http.handle_initialize",
                new_callable=AsyncMock,
                return_value={"protocolVersion": "2024-11-05"},
            ),
        ):
            mock_manager = AsyncMock()
            mock_manager.get_or_create_session = AsyncMock(return_value=mock_session)
            MockSessionManagerClass.return_value = mock_manager

            result = await mcp_endpoint(
                rpc_request=rpc_request,
                request=mock_request,
                x_api_key=None,
                authorization=f"Bearer {api_key_value}",
                db=mock_db,
            )

            # Should fall back to API key auth
            mock_manager.get_or_create_session.assert_called_once_with(api_key_value)

    @pytest.mark.asyncio
    async def test_x_api_key_header_still_works(self):
        """X-API-Key header should bypass JWT logic entirely (backward compat)."""
        from api.endpoints.mcp_http import mcp_endpoint

        api_key_value = "ak_" + uuid4().hex[:20]
        mock_session = MagicMock()
        mock_session.session_id = str(uuid4())
        mock_session.tenant_key = "tk_test"
        mock_session.api_key_id = str(uuid4())

        rpc_request = MagicMock()
        rpc_request.method = "initialize"
        rpc_request.params = {}
        rpc_request.id = 1

        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_db = AsyncMock()

        with (
            patch(
                "api.endpoints.mcp_http.MCPSessionManager",
            ) as MockSessionManagerClass,
            patch(
                "api.endpoints.mcp_http.handle_initialize",
                new_callable=AsyncMock,
                return_value={"protocolVersion": "2024-11-05"},
            ),
        ):
            mock_manager = AsyncMock()
            mock_manager.get_or_create_session = AsyncMock(return_value=mock_session)
            MockSessionManagerClass.return_value = mock_manager

            result = await mcp_endpoint(
                rpc_request=rpc_request,
                request=mock_request,
                x_api_key=api_key_value,
                authorization=None,
                db=mock_db,
            )

            # Should use API key path directly
            mock_manager.get_or_create_session.assert_called_once_with(api_key_value)

    @pytest.mark.asyncio
    async def test_no_auth_returns_error(self):
        """Missing auth headers should return JSON-RPC error."""
        from api.endpoints.mcp_http import mcp_endpoint

        rpc_request = MagicMock()
        rpc_request.id = 1

        mock_request = MagicMock()
        mock_db = AsyncMock()

        result = await mcp_endpoint(
            rpc_request=rpc_request,
            request=mock_request,
            x_api_key=None,
            authorization=None,
            db=mock_db,
        )

        assert result.error.code == -32600
        assert "Authentication required" in result.error.message

    @pytest.mark.asyncio
    async def test_jwt_session_skips_ip_logging(self):
        """JWT-authenticated sessions (api_key_id=None) should skip IP logging."""
        from api.endpoints.mcp_http import mcp_endpoint

        user_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex[:12]}"
        jwt_payload = {
            "sub": user_id,
            "username": "jwt_user",
            "role": "developer",
            "tenant_key": tenant_key,
            "type": "access",
        }

        mock_session = MagicMock()
        mock_session.session_id = str(uuid4())
        mock_session.tenant_key = tenant_key
        mock_session.api_key_id = None

        rpc_request = MagicMock()
        rpc_request.method = "initialize"
        rpc_request.params = {}
        rpc_request.id = 1

        mock_request = MagicMock()
        mock_request.client = MagicMock()
        mock_request.client.host = "127.0.0.1"

        mock_db = AsyncMock()

        with (
            patch(
                "api.endpoints.mcp_http.JWTManager.verify_token",
                return_value=jwt_payload,
            ),
            patch(
                "api.endpoints.mcp_http.MCPSessionManager",
            ) as MockSessionManagerClass,
            patch(
                "api.endpoints.mcp_http.handle_initialize",
                new_callable=AsyncMock,
                return_value={"protocolVersion": "2024-11-05"},
            ),
        ):
            mock_manager = AsyncMock()
            mock_manager.get_or_create_session_from_jwt = AsyncMock(return_value=mock_session)
            MockSessionManagerClass.return_value = mock_manager

            await mcp_endpoint(
                rpc_request=rpc_request,
                request=mock_request,
                x_api_key=None,
                authorization="Bearer eyJhbGciOiJIUzI1NiJ9.jwt-token",
                db=mock_db,
            )

            # log_ip should NOT be called for JWT sessions (no api_key_id)
            mock_manager.log_ip.assert_not_called()
