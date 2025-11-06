"""
Unit tests for unified WebSocket authentication (Phase 2)

Tests WebSocket auth WITHOUT IP-based auto-login.
During setup: Allow connection without auth
After setup: Require credentials for ALL connections (localhost and network)

Following TDD principles - tests written BEFORE implementation.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import WebSocket, WebSocketException

from api.auth_utils import authenticate_websocket


class TestWebSocketAuthDuringSetup:
    """Test WebSocket authentication during setup mode"""

    @pytest.fixture
    def mock_websocket_localhost(self):
        """Create mock WebSocket from localhost"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = "127.0.0.1"
        ws.query_params = {}
        ws.headers = {}
        return ws

    @pytest.fixture
    def mock_websocket_network(self):
        """Create mock WebSocket from network"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = "192.168.1.100"
        ws.query_params = {}
        ws.headers = {}
        return ws

    @pytest.mark.asyncio
    async def test_setup_mode_allows_localhost_without_auth(self, mock_websocket_localhost):
        """Test that setup mode allows localhost connections without auth"""
        # Mock setup state as NOT completed
        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": False}):
            result = await authenticate_websocket(mock_websocket_localhost)

            assert result["authenticated"] is True
            assert result["context"] == "setup"

    @pytest.mark.asyncio
    async def test_setup_mode_allows_network_without_auth(self, mock_websocket_network):
        """Test that setup mode allows network connections without auth"""
        # During setup, all connections allowed (for setup progress updates)
        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": False}):
            result = await authenticate_websocket(mock_websocket_network)

            assert result["authenticated"] is True
            assert result["context"] == "setup"

    @pytest.mark.asyncio
    async def test_post_setup_localhost_without_auth_fails(self, mock_websocket_localhost):
        """Test that post-setup localhost connections require auth"""
        # Setup completed
        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}):
            # No token provided
            with pytest.raises(WebSocketException) as exc_info:
                await authenticate_websocket(mock_websocket_localhost)

            # Should reject connection
            assert exc_info.value.code == 1008  # Policy violation

    @pytest.mark.asyncio
    async def test_post_setup_network_without_auth_fails(self, mock_websocket_network):
        """Test that post-setup network connections require auth"""
        with (
            patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}),
            pytest.raises(WebSocketException),
        ):
            await authenticate_websocket(mock_websocket_network)


class TestWebSocketAuthPostSetup:
    """Test WebSocket authentication after setup complete"""

    @pytest.fixture
    def mock_websocket_with_token(self):
        """Create WebSocket with valid JWT token"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = "127.0.0.1"
        ws.query_params = {"token": "valid_jwt_token"}
        ws.headers = {}
        return ws

    @pytest.fixture
    def mock_auth_manager(self):
        """Create mock auth manager"""
        manager = Mock()
        manager.validate_jwt_token = Mock()
        return manager

    @pytest.mark.asyncio
    async def test_post_setup_with_valid_token_succeeds(self, mock_websocket_with_token, mock_auth_manager):
        """Test that valid JWT token allows connection"""
        # Mock setup completed
        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}):
            # Mock valid token
            mock_auth_manager.validate_jwt_token.return_value = {"user_id": "testuser", "tenant_key": "default"}

            with patch("api.auth_utils.validate_jwt_token", mock_auth_manager.validate_jwt_token):
                result = await authenticate_websocket(mock_websocket_with_token)

                assert result["authenticated"] is True
                assert result["user"]["user_id"] == "testuser"

    @pytest.mark.asyncio
    async def test_post_setup_with_invalid_token_fails(self, mock_websocket_with_token, mock_auth_manager):
        """Test that invalid JWT token is rejected"""
        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}):
            # Mock invalid token
            mock_auth_manager.validate_jwt_token.return_value = None

            with patch("api.auth_utils.validate_jwt_token", mock_auth_manager.validate_jwt_token):
                with pytest.raises(WebSocketException):
                    await authenticate_websocket(mock_websocket_with_token)

    @pytest.mark.asyncio
    async def test_post_setup_localhost_same_as_network(self):
        """Test that localhost and network WebSockets treated identically"""
        # Create both types
        ws_localhost = Mock(spec=WebSocket)
        ws_localhost.client = Mock()
        ws_localhost.client.host = "127.0.0.1"
        ws_localhost.query_params = {"token": "test_token"}

        ws_network = Mock(spec=WebSocket)
        ws_network.client = Mock()
        ws_network.client.host = "192.168.1.100"
        ws_network.query_params = {"token": "test_token"}

        # Mock setup completed
        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}):
            # Mock valid token
            with patch(
                "api.auth_utils.validate_jwt_token", return_value={"user_id": "testuser", "tenant_key": "default"}
            ):
                result_localhost = await authenticate_websocket(ws_localhost)
                result_network = await authenticate_websocket(ws_network)

                # Should be identical
                assert result_localhost["authenticated"] == result_network["authenticated"]
                assert result_localhost["user"] == result_network["user"]


class TestWebSocketAuthNoIPDetection:
    """Test that IP-based detection has been removed"""

    @pytest.mark.asyncio
    async def test_no_localhost_auto_login(self):
        """Test that localhost IPs do NOT trigger auto-login"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = "127.0.0.1"
        ws.query_params = {}  # No token

        # Post-setup should require auth regardless of IP
        with (
            patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}),
            pytest.raises(WebSocketException),
        ):
            await authenticate_websocket(ws)

    @pytest.mark.asyncio
    async def test_no_localhost_ips_constant(self):
        """Test that LOCALHOST_IPS constant has been removed"""
        # Should not have LOCALHOST_IPS in auth_utils
        import api.auth_utils

        assert not hasattr(api.auth_utils, "LOCALHOST_IPS")

    @pytest.mark.asyncio
    async def test_no_ip_based_branching(self):
        """Test that there's no IP-based conditional logic"""
        # Check the function signature - should not check IPs
        from inspect import getsource

        import api.auth_utils

        # Get authenticate_websocket source
        source = getsource(api.auth_utils.authenticate_websocket)

        # Should not contain IP-based checks (after implementation)
        assert "client.host" not in source or "setup" in source  # Only check IP during setup check
        assert "LOCALHOST_IPS" not in source
        assert "auto_login" not in source or "setup" in source  # No auto-login except setup mode


class TestWebSocketAuthWithAPIKey:
    """Test WebSocket authentication with API keys"""

    @pytest.fixture
    def mock_websocket_with_api_key(self):
        """Create WebSocket with API key"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = "192.168.1.100"
        ws.query_params = {"api_key": "valid_api_key"}
        ws.headers = {}
        return ws

    @pytest.mark.asyncio
    async def test_websocket_with_valid_api_key(self, mock_websocket_with_api_key):
        """Test WebSocket connection with valid API key"""
        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}):
            # Mock API key validation
            with patch("api.auth_utils.validate_api_key", return_value={"name": "test_key", "permissions": ["*"]}):
                result = await authenticate_websocket(mock_websocket_with_api_key)

                assert result["authenticated"] is True

    @pytest.mark.asyncio
    async def test_websocket_with_invalid_api_key(self, mock_websocket_with_api_key):
        """Test WebSocket connection with invalid API key"""
        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}):
            # Mock invalid API key
            with patch("api.auth_utils.validate_api_key", return_value=None):
                with pytest.raises(WebSocketException):
                    await authenticate_websocket(mock_websocket_with_api_key)


class TestWebSocketAuthEdgeCases:
    """Test edge cases in WebSocket authentication"""

    @pytest.mark.asyncio
    async def test_missing_client_object(self):
        """Test handling of WebSocket without client object"""
        ws = Mock(spec=WebSocket)
        ws.client = None  # No client object
        ws.query_params = {}

        with patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}):
            # Should handle gracefully
            with pytest.raises(WebSocketException):
                await authenticate_websocket(ws)

    @pytest.mark.asyncio
    async def test_empty_token(self):
        """Test handling of empty token"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = "127.0.0.1"
        ws.query_params = {"token": ""}  # Empty token

        with (
            patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}),
            pytest.raises(WebSocketException),
        ):
            await authenticate_websocket(ws)

    @pytest.mark.asyncio
    async def test_malformed_token(self):
        """Test handling of malformed JWT token"""
        ws = Mock(spec=WebSocket)
        ws.client = Mock()
        ws.client.host = "127.0.0.1"
        ws.query_params = {"token": "not.a.valid.jwt"}

        with (
            patch("api.auth_utils.get_setup_state", return_value={"setup_completed": True}),
            patch("api.auth_utils.validate_jwt_token", return_value=None),
            pytest.raises(WebSocketException),
        ):
            await authenticate_websocket(ws)
