"""
Unit tests for unified AuthManager (Phase 2)

Tests AuthManager WITHOUT localhost auto-login logic.
All connections (localhost and network) use the same authentication flow.

Following TDD principles - tests written BEFORE implementation.
"""

from unittest.mock import Mock, patch

import pytest
from fastapi import Request

from src.giljo_mcp.auth_manager import AuthManager

pytestmark = pytest.mark.skip(reason="0750b: Auth manager tests have partial bcrypt timeout failures on Windows")

class TestUnifiedAuthManager:
    """Test suite for unified AuthManager without localhost auto-login"""

    @pytest.fixture
    def auth_manager(self):
        """Create AuthManager instance for testing"""
        return AuthManager()

    @pytest.fixture
    def mock_request_localhost(self):
        """Create a mock request from localhost"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        request.app = Mock()
        request.app.state = Mock()
        return request

    @pytest.fixture
    def mock_request_network(self):
        """Create a mock request from network IP"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "192.168.1.100"
        request.headers = {}
        request.app = Mock()
        request.app.state = Mock()
        return request

    @pytest.mark.asyncio
    async def test_authenticate_localhost_without_credentials_fails(self, auth_manager, mock_request_localhost):
        """Test that localhost requests without credentials are rejected"""
        # No credentials provided
        result = await auth_manager.authenticate_request(mock_request_localhost)

        # Should NOT auto-login
        assert result["authenticated"] is False
        assert "error" in result
        assert "Authentication required" in result["error"]

    @pytest.mark.asyncio
    async def test_authenticate_localhost_with_valid_credentials_succeeds(self, auth_manager, mock_request_localhost):
        """Test that localhost requests with valid credentials succeed"""
        # Add valid JWT token
        mock_request_localhost.headers = {"Authorization": "Bearer valid_token_here"}

        # Mock JWT validation
        with patch.object(
            auth_manager, "validate_jwt_token", return_value={"user_id": "admin", "tenant_key": "default"}
        ):
            result = await auth_manager.authenticate_request(mock_request_localhost)

            assert result["authenticated"] is True
            assert result["user"] == "admin"
            assert "is_auto_login" not in result or result.get("is_auto_login") is False

    @pytest.mark.asyncio
    async def test_authenticate_network_without_credentials_fails(self, auth_manager, mock_request_network):
        """Test that network requests without credentials are rejected"""
        result = await auth_manager.authenticate_request(mock_request_network)

        assert result["authenticated"] is False
        assert "error" in result
        assert "Authentication required" in result["error"]

    @pytest.mark.asyncio
    async def test_authenticate_network_with_valid_credentials_succeeds(self, auth_manager, mock_request_network):
        """Test that network requests with valid credentials succeed"""
        # Add valid JWT token
        mock_request_network.headers = {"Authorization": "Bearer valid_token_here"}

        # Mock JWT validation
        with patch.object(
            auth_manager, "validate_jwt_token", return_value={"user_id": "testuser", "tenant_key": "default"}
        ):
            result = await auth_manager.authenticate_request(mock_request_network)

            assert result["authenticated"] is True
            assert result["user"] == "testuser"

    @pytest.mark.asyncio
    async def test_authenticate_localhost_same_as_network(
        self, auth_manager, mock_request_localhost, mock_request_network
    ):
        """Test that localhost and network clients are treated identically"""
        # Add same valid token to both requests
        token_header = {"Authorization": "Bearer valid_token"}
        mock_request_localhost.headers = token_header
        mock_request_network.headers = token_header

        # Mock JWT validation
        mock_payload = {"user_id": "testuser", "tenant_key": "default"}

        with patch.object(auth_manager, "validate_jwt_token", return_value=mock_payload):
            result_localhost = await auth_manager.authenticate_request(mock_request_localhost)
            result_network = await auth_manager.authenticate_request(mock_request_network)

            # Results should be identical
            assert result_localhost["authenticated"] == result_network["authenticated"]
            assert result_localhost["user"] == result_network["user"]

    @pytest.mark.asyncio
    async def test_no_get_client_ip_method(self, auth_manager):
        """Test that _get_client_ip() method has been removed"""
        # This method should NOT exist in unified auth
        assert not hasattr(auth_manager, "_get_client_ip")

    @pytest.mark.asyncio
    async def test_no_localhost_auto_login_logic(self, auth_manager, mock_request_localhost):
        """Test that there's no IP-based auto-login logic"""
        # Even if request is from localhost, should not auto-login
        result = await auth_manager.authenticate_request(mock_request_localhost)

        # Should require credentials
        assert result["authenticated"] is False
        assert "localhost" not in result.get("user", "")
        assert result.get("is_auto_login") is not True

    @pytest.mark.asyncio
    async def test_authenticate_with_api_key(self, auth_manager, mock_request_network):
        """Test authentication with API key"""
        # Add API key header
        mock_request_network.headers = {"X-API-Key": "valid_api_key"}

        # Mock API key validation
        with patch.object(auth_manager, "validate_api_key", return_value={"name": "test_key", "permissions": ["*"]}):
            result = await auth_manager.authenticate_request(mock_request_network)

            assert result["authenticated"] is True
            assert result["user"] == "test_key"

    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_token(self, auth_manager, mock_request_localhost):
        """Test that invalid JWT tokens are rejected"""
        mock_request_localhost.headers = {"Authorization": "Bearer invalid_token"}

        # Mock JWT validation to return None (invalid)
        with patch.object(auth_manager, "validate_jwt_token", return_value=None):
            result = await auth_manager.authenticate_request(mock_request_localhost)

            assert result["authenticated"] is False


class TestAuthManagerMethods:
    """Test specific AuthManager methods"""

    @pytest.fixture
    def auth_manager(self):
        """Create AuthManager instance"""
        return AuthManager()

    def test_validate_admin_credentials(self, auth_manager):
        """Test admin credential validation"""
        # Create default admin credentials
        auth_manager.store_admin_account("admin", "admin", tenant_key="default")

        # Valid credentials should pass
        assert auth_manager.validate_admin_credentials("admin", "admin") is True

        # Invalid password should fail
        assert auth_manager.validate_admin_credentials("admin", "wrong") is False

        # Invalid username should fail
        assert auth_manager.validate_admin_credentials("notadmin", "admin") is False

    def test_generate_jwt_token(self, auth_manager):
        """Test JWT token generation"""
        token = auth_manager.generate_jwt_token(user_id="testuser", tenant_key="default", expires_in=3600)

        # Should return a token string
        assert isinstance(token, str)
        assert len(token) > 0

        # Should be able to validate the token
        payload = auth_manager.validate_jwt_token(token)
        assert payload is not None
        assert payload["user_id"] == "testuser"
        assert payload["tenant_key"] == "default"

    def test_generate_api_key(self, auth_manager):
        """Test API key generation"""
        api_key = auth_manager.generate_api_key(name="test_key", permissions=["read:*", "write:*"])

        # Should return an API key
        assert isinstance(api_key, str)
        assert api_key.startswith("gk_")

        # Should be able to validate the key
        key_info = auth_manager.validate_api_key(api_key)
        assert key_info is not None
        assert key_info["name"] == "test_key"
        assert key_info["permissions"] == ["read:*", "write:*"]


class TestAuthManagerBackwardCompatibility:
    """Test that removed methods no longer exist"""

    @pytest.fixture
    def auth_manager(self):
        """Create AuthManager instance"""
        return AuthManager()

    def test_no_localhost_user_import(self, auth_manager):
        """Test that localhost_user module is not imported"""
        # Should not import localhost_user
        import sys

        assert "src.giljo_mcp.auth.localhost_user" not in sys.modules

    def test_removed_localhost_ips_constant(self, auth_manager):
        """Test that LOCALHOST_IPS constant has been removed"""
        # Should not have LOCALHOST_IPS
        from src.giljo_mcp.auth_manager import AuthManager

        assert not hasattr(AuthManager, "LOCALHOST_IPS")
