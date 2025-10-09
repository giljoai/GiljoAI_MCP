"""
Unit tests for MCP Installer API endpoints.

Tests cover:
- Script template rendering with user credentials
- Token generation and validation
- Download endpoints (authenticated and public)
- Share link generation
- Error handling (invalid tokens, missing templates, etc.)

Following TDD principles: tests written before implementation.
"""

import pytest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from fastapi.testclient import TestClient

# Import the functions we'll implement
from api.endpoints import mcp_installer

# Test configuration
TEST_SERVER_URL = "http://localhost:7272"
TEST_USER_ID = "test-user-123"
TEST_USERNAME = "test_user"
TEST_API_KEY = "gk_test_key_abc123"
TEST_ORGANIZATION = "Test Org"


class TestTokenGeneration:
    """Tests for secure token generation and validation"""

    def test_generate_token_creates_valid_jwt(self):
        """Token should be valid JWT with user_id and expiry"""
        token = mcp_installer.generate_secure_token(user_id=TEST_USER_ID, expires_in=3600)

        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 20  # JWT tokens are long

    def test_validate_token_accepts_valid_token(self):
        """Valid token should return user info"""
        token = mcp_installer.generate_secure_token(TEST_USER_ID, 3600)
        user_info = mcp_installer.validate_token(token)

        assert user_info is not None
        assert user_info["user_id"] == TEST_USER_ID
        assert "expires_at" in user_info

    def test_validate_token_rejects_expired_token(self):
        """Expired token should return None"""
        # Create token that expires immediately
        token = mcp_installer.generate_secure_token(TEST_USER_ID, -1)
        user_info = mcp_installer.validate_token(token)

        assert user_info is None

    def test_validate_token_rejects_malformed_token(self):
        """Malformed token should return None"""
        malformed_token = "not-a-valid-jwt-token"
        user_info = mcp_installer.validate_token(malformed_token)

        assert user_info is None

    def test_token_contains_expiration_time(self):
        """Token should include expiration timestamp"""
        from datetime import timezone as tz

        expires_in = 7200  # 2 hours
        token = mcp_installer.generate_secure_token(TEST_USER_ID, expires_in)
        user_info = mcp_installer.validate_token(token)

        assert user_info is not None
        assert "expires_at" in user_info

        # Check expiration is approximately correct (within 10 seconds)
        expected_expiry = datetime.now(tz.utc) + timedelta(seconds=expires_in)
        actual_expiry = datetime.fromisoformat(user_info["expires_at"].replace('Z', '+00:00'))
        time_diff = abs((expected_expiry - actual_expiry).total_seconds())

        assert time_diff < 10  # Should be very close


class TestTemplateRendering:
    """Tests for script template rendering"""

    def test_render_template_with_all_placeholders(self):
        """Template should render with all user data placeholders"""
        from unittest.mock import mock_open

        template_content = """
SERVER_URL={server_url}
API_KEY={api_key}
USERNAME={username}
ORG={organization}
TIMESTAMP={timestamp}
"""
        # Mock Path.exists() to return True and Path.read_text() to return template
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=template_content):
            rendered = mcp_installer.render_template(
                template_path=Path("test.template"),
                server_url=TEST_SERVER_URL,
                api_key=TEST_API_KEY,
                username=TEST_USERNAME,
                organization=TEST_ORGANIZATION,
                timestamp="2024-01-01T00:00:00"
            )

        assert TEST_SERVER_URL in rendered
        assert TEST_API_KEY in rendered
        assert TEST_USERNAME in rendered
        assert TEST_ORGANIZATION in rendered
        assert "2024-01-01T00:00:00" in rendered

    def test_render_template_escapes_special_chars(self):
        """Template should handle special characters in user data"""
        template_content = "USERNAME={username}"

        # Mock Path.exists() and Path.read_text()
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.read_text', return_value=template_content):
            # Username with special characters
            special_username = "test&user<script>"
            rendered = mcp_installer.render_template(
                template_path=Path("test.template"),
                server_url=TEST_SERVER_URL,
                api_key=TEST_API_KEY,
                username=special_username,
                organization=TEST_ORGANIZATION,
                timestamp="2024-01-01T00:00:00"
            )

        # Should contain the special username (no escaping for scripts)
        assert special_username in rendered


class TestDownloadWindowsEndpoint:
    """Tests for GET /api/mcp-installer/windows endpoint"""

    @pytest.fixture
    def mock_user(self):
        """Create mock user object"""
        user = Mock()
        user.id = TEST_USER_ID
        user.username = TEST_USERNAME
        user.api_key = TEST_API_KEY
        org = Mock()
        org.name = TEST_ORGANIZATION
        user.organization = org
        return user

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.render_template')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_download_windows_returns_bat_file(self, mock_get_server, mock_render, mock_user):
        """Endpoint should return .bat file with correct content type"""
        mock_get_server.return_value = TEST_SERVER_URL
        mock_render.return_value = "@echo off\nREM Test script"

        response = await mcp_installer.download_windows_installer(current_user=mock_user)

        assert response.media_type == "application/bat"
        assert "giljo-mcp-setup.bat" in response.headers.get("Content-Disposition", "")

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.render_template')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_download_windows_embeds_user_credentials(self, mock_get_server, mock_render, mock_user):
        """Script should contain embedded user credentials"""
        mock_get_server.return_value = TEST_SERVER_URL

        response = await mcp_installer.download_windows_installer(current_user=mock_user)

        # Verify render_template was called with user credentials
        mock_render.assert_called_once()
        call_kwargs = mock_render.call_args.kwargs

        assert call_kwargs["server_url"] == TEST_SERVER_URL
        assert call_kwargs["api_key"] == TEST_API_KEY
        assert call_kwargs["username"] == TEST_USERNAME
        assert call_kwargs["organization"] == TEST_ORGANIZATION


class TestDownloadUnixEndpoint:
    """Tests for GET /api/mcp-installer/unix endpoint"""

    @pytest.fixture
    def mock_user(self):
        """Create mock user object"""
        user = Mock()
        user.id = TEST_USER_ID
        user.username = TEST_USERNAME
        user.api_key = TEST_API_KEY
        org = Mock()
        org.name = TEST_ORGANIZATION
        user.organization = org
        return user

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.render_template')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_download_unix_returns_sh_file(self, mock_get_server, mock_render, mock_user):
        """Endpoint should return .sh file with correct content type"""
        mock_get_server.return_value = TEST_SERVER_URL
        mock_render.return_value = "#!/bin/bash\n# Test script"

        response = await mcp_installer.download_unix_installer(current_user=mock_user)

        assert response.media_type == "application/x-sh"
        assert "giljo-mcp-setup.sh" in response.headers.get("Content-Disposition", "")

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.render_template')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_download_unix_embeds_user_credentials(self, mock_get_server, mock_render, mock_user):
        """Script should contain embedded user credentials"""
        mock_get_server.return_value = TEST_SERVER_URL

        response = await mcp_installer.download_unix_installer(current_user=mock_user)

        # Verify render_template was called with user credentials
        mock_render.assert_called_once()
        call_kwargs = mock_render.call_args.kwargs

        assert call_kwargs["server_url"] == TEST_SERVER_URL
        assert call_kwargs["api_key"] == TEST_API_KEY
        assert call_kwargs["username"] == TEST_USERNAME


class TestShareLinkEndpoint:
    """Tests for POST /api/mcp-installer/share-link endpoint"""

    @pytest.fixture
    def mock_user(self):
        """Create mock user object"""
        user = Mock()
        user.id = TEST_USER_ID
        user.username = TEST_USERNAME
        return user

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.generate_secure_token')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_generate_share_link_returns_urls(self, mock_get_server, mock_gen_token, mock_user):
        """Endpoint should return Windows and Unix URLs"""
        mock_get_server.return_value = TEST_SERVER_URL
        mock_gen_token.return_value = "test-token-123"

        result = await mcp_installer.generate_share_link(current_user=mock_user)

        assert hasattr(result, "windows_url")
        assert hasattr(result, "unix_url")
        assert hasattr(result, "expires_at")
        assert hasattr(result, "token")

        assert result.windows_url.startswith(TEST_SERVER_URL)
        assert "windows" in result.windows_url
        assert "unix" in result.unix_url

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.generate_secure_token')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_share_link_token_expires_in_7_days(self, mock_get_server, mock_gen_token, mock_user):
        """Token should expire in 7 days"""
        mock_get_server.return_value = TEST_SERVER_URL
        mock_gen_token.return_value = "test-token-123"

        result = await mcp_installer.generate_share_link(current_user=mock_user)

        # Verify generate_secure_token called with 7 days
        mock_gen_token.assert_called_once_with(
            user_id=TEST_USER_ID,
            expires_in=7*24*3600
        )

        # Verify expires_at is approximately 7 days from now
        expires_at = datetime.fromisoformat(result.expires_at.replace('Z', '+00:00'))
        expected_expiry = datetime.now(timezone.utc) + timedelta(days=7)
        time_diff = abs((expected_expiry - expires_at).total_seconds())

        assert time_diff < 60  # Within 1 minute


class TestDownloadViaTokenEndpoint:
    """Tests for GET /download/mcp/{token}/{platform} endpoint"""

    @pytest.fixture
    def mock_user(self):
        """Create mock user object"""
        user = Mock()
        user.id = TEST_USER_ID
        user.username = TEST_USERNAME
        user.api_key = TEST_API_KEY
        org = Mock()
        org.name = TEST_ORGANIZATION
        user.organization = org
        return user

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.validate_token')
    @patch('api.endpoints.mcp_installer.get_user_by_id')
    @patch('api.endpoints.mcp_installer.render_template')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_download_via_valid_token_windows(self, mock_get_server, mock_render,
                                               mock_get_user, mock_validate, mock_user):
        """Valid token should allow download without authentication"""
        mock_validate.return_value = {"user_id": TEST_USER_ID}
        mock_get_user.return_value = mock_user
        mock_get_server.return_value = TEST_SERVER_URL
        mock_render.return_value = "@echo off"

        response = await mcp_installer.download_via_token(token="valid-token", platform="windows")

        assert response.media_type == "application/bat"
        mock_validate.assert_called_once_with("valid-token")

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.validate_token')
    async def test_download_via_invalid_token_raises_401(self, mock_validate):
        """Invalid token should raise 401 Unauthorized"""
        mock_validate.return_value = None  # Invalid token

        with pytest.raises(HTTPException) as exc_info:
            await mcp_installer.download_via_token(token="invalid-token", platform="windows")

        assert exc_info.value.status_code == 401
        assert "Invalid or expired token" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.validate_token')
    @patch('api.endpoints.mcp_installer.get_user_by_id')
    async def test_download_via_invalid_platform_raises_400(self, mock_get_user, mock_validate, mock_user):
        """Invalid platform should raise 400 Bad Request"""
        mock_validate.return_value = {"user_id": TEST_USER_ID}
        mock_get_user.return_value = mock_user

        with pytest.raises(HTTPException) as exc_info:
            await mcp_installer.download_via_token(token="valid-token", platform="invalid")

        assert exc_info.value.status_code == 400
        assert "Invalid platform" in str(exc_info.value.detail)


class TestErrorHandling:
    """Tests for error handling scenarios"""

    @pytest.fixture
    def mock_user(self):
        """Create mock user object"""
        user = Mock()
        user.id = TEST_USER_ID
        user.username = TEST_USERNAME
        user.api_key = TEST_API_KEY
        org = Mock()
        org.name = TEST_ORGANIZATION
        user.organization = org
        return user

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.render_template')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_missing_template_file_raises_error(self, mock_get_server, mock_render, mock_user):
        """Missing template file should raise HTTPException 500"""
        mock_get_server.return_value = TEST_SERVER_URL
        mock_render.side_effect = FileNotFoundError("Template file not found")

        with pytest.raises(HTTPException) as exc_info:
            await mcp_installer.download_windows_installer(current_user=mock_user)

        assert exc_info.value.status_code == 500
        assert "template not found" in str(exc_info.value.detail).lower()

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.render_template')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_user_without_organization_uses_personal(self, mock_get_server, mock_render, mock_user):
        """User without organization should default to 'Personal'"""
        mock_user.organization = None
        mock_get_server.return_value = TEST_SERVER_URL

        response = await mcp_installer.download_windows_installer(current_user=mock_user)

        # Verify render_template was called with "Personal"
        call_kwargs = mock_render.call_args.kwargs
        assert call_kwargs["organization"] == "Personal"


class TestIntegration:
    """Integration tests for full workflow"""

    @pytest.fixture
    def mock_user(self):
        """Create mock user object"""
        user = Mock()
        user.id = TEST_USER_ID
        user.username = TEST_USERNAME
        user.api_key = TEST_API_KEY
        org = Mock()
        org.name = TEST_ORGANIZATION
        user.organization = org
        return user

    @pytest.mark.asyncio
    @patch('api.endpoints.mcp_installer.validate_token')
    @patch('api.endpoints.mcp_installer.get_user_by_id')
    @patch('api.endpoints.mcp_installer.generate_secure_token')
    @patch('api.endpoints.mcp_installer.render_template')
    @patch('api.endpoints.mcp_installer.get_server_url')
    async def test_full_share_link_workflow(self, mock_get_server, mock_render,
                                       mock_gen_token, mock_get_user,
                                       mock_validate, mock_user):
        """Test complete workflow: generate link -> download via token"""
        # Setup mocks
        mock_get_server.return_value = TEST_SERVER_URL
        mock_gen_token.return_value = "test-token-123"
        mock_validate.return_value = {"user_id": TEST_USER_ID}
        mock_get_user.return_value = mock_user
        mock_render.return_value = "@echo off"

        # Step 1: Generate share link
        link_result = await mcp_installer.generate_share_link(current_user=mock_user)
        token = link_result.token

        assert token == "test-token-123"
        assert link_result.windows_url.endswith(f"/download/mcp/{token}/windows")

        # Step 2: Download via token (simulates user clicking link)
        response = await mcp_installer.download_via_token(token=token, platform="windows")

        assert response.media_type == "application/bat"
        mock_validate.assert_called_once_with(token)
        mock_get_user.assert_called_once_with(TEST_USER_ID)


class TestHelperFunctions:
    """Tests for helper functions"""

    @patch('api.endpoints.mcp_installer.get_config')
    def test_get_server_url_from_config(self, mock_config):
        """get_server_url should read from config"""
        mock_cfg = Mock()
        mock_cfg.api.host = "127.0.0.1"
        mock_cfg.api.port = 7272
        mock_config.return_value = mock_cfg

        url = mcp_installer.get_server_url()

        assert url == "http://127.0.0.1:7272"

    @patch('api.endpoints.mcp_installer.get_db_session')
    async def test_get_user_by_id_queries_database(self, mock_get_session):
        """get_user_by_id should query database for user"""
        # This test would need async support
        pass  # Placeholder for async test
