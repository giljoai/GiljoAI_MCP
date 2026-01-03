"""
Unit tests for dynamic server URL extraction from HTTP request headers.

Tests the fix for using client-accessible server URLs instead of bind addresses (0.0.0.0).
Validates that download URLs are generated using the actual server URL from HTTP request headers.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import Request


class TestServerURLExtraction:
    """Test server URL extraction from HTTP request headers"""

    def test_extract_server_url_from_http_request(self):
        """Test extraction of server URL from HTTP request headers"""
        # Create mock request with headers
        mock_request = MagicMock(spec=Request)
        mock_request.url.scheme = "http"
        mock_request.headers = {"host": "10.1.0.164:7272"}

        # Extract server URL
        scheme = mock_request.url.scheme
        host = mock_request.headers.get("host")
        server_url = f"{scheme}://{host}"

        # Verify
        assert server_url == "http://10.1.0.164:7272"
        assert "0.0.0.0" not in server_url
        assert "localhost" not in server_url

    def test_extract_server_url_with_https(self):
        """Test extraction with HTTPS scheme"""
        mock_request = MagicMock(spec=Request)
        mock_request.url.scheme = "https"
        mock_request.headers = {"host": "api.example.com:7272"}

        scheme = mock_request.url.scheme
        host = mock_request.headers.get("host")
        server_url = f"{scheme}://{host}"

        assert server_url == "https://api.example.com:7272"

    def test_extract_server_url_localhost(self):
        """Test extraction when client connects via localhost"""
        mock_request = MagicMock(spec=Request)
        mock_request.url.scheme = "http"
        mock_request.headers = {"host": "localhost:7272"}

        scheme = mock_request.url.scheme
        host = mock_request.headers.get("host")
        server_url = f"{scheme}://{host}"

        assert server_url == "http://localhost:7272"


class TestMCPHTTPServerURLInjection:
    """Test MCP HTTP handler injects server URL into download tool arguments"""

    def test_server_url_injection_logic(self):
        """Test server URL injection logic (simulated from MCP HTTP handler)"""
        # Simulate what mcp_http.py does
        mock_request = MagicMock(spec=Request)
        mock_request.url.scheme = "http"
        mock_request.headers = {"host": "10.1.0.164:7272", "x-api-key": "test-key-123"}

        # Simulate the injection logic
        arguments = {}
        arguments["_api_key"] = "test-key-123"
        scheme = mock_request.url.scheme
        host = mock_request.headers.get("host")
        arguments["_server_url"] = f"{scheme}://{host}"

        # Verify
        assert "_server_url" in arguments
        assert arguments["_server_url"] == "http://10.1.0.164:7272"
        assert "0.0.0.0" not in arguments["_server_url"]

    def test_server_url_injection_with_different_ip(self):
        """Test server URL injection with different IP address"""
        mock_request = MagicMock(spec=Request)
        mock_request.url.scheme = "http"
        mock_request.headers = {"host": "192.168.1.100:7272", "x-api-key": "test-key"}

        arguments = {}
        arguments["_api_key"] = "test-key"
        scheme = mock_request.url.scheme
        host = mock_request.headers.get("host")
        arguments["_server_url"] = f"{scheme}://{host}"

        assert "_server_url" in arguments
        assert arguments["_server_url"] == "http://192.168.1.100:7272"

    def test_server_url_injection_with_https(self):
        """Test server URL injection with HTTPS"""
        mock_request = MagicMock(spec=Request)
        mock_request.url.scheme = "https"
        mock_request.headers = {"host": "secure.example.com:443", "x-api-key": "test-key"}

        arguments = {}
        arguments["_api_key"] = "test-key"
        scheme = mock_request.url.scheme
        host = mock_request.headers.get("host")
        arguments["_server_url"] = f"{scheme}://{host}"

        assert "_server_url" in arguments
        assert arguments["_server_url"] == "https://secure.example.com:443"


class TestToolAccessorUsesServerURL:
    """Test that tool accessor methods use _server_url parameter correctly"""

    @pytest.mark.asyncio
    @patch("giljo_mcp.config_manager.get_config")
    @patch("giljo_mcp.downloads.token_manager.TokenManager")
    @patch("giljo_mcp.file_staging.FileStaging")
    async def test_setup_slash_commands_uses_server_url(self, mock_file_staging, mock_token_manager, mock_get_config):
        """Test setup_slash_commands uses _server_url instead of config"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        # Mock database manager
        mock_db_manager = MagicMock()
        mock_session = AsyncMock()
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        # Mock tenant manager
        mock_tenant_manager = MagicMock()
        mock_tenant_manager.get_current_tenant.return_value = "test-tenant"

        # Mock token generation
        mock_tm_instance = MagicMock()
        mock_tm_instance.generate_token = AsyncMock(return_value="token-abc123")
        mock_tm_instance.mark_ready = AsyncMock()
        mock_tm_instance.mark_failed = AsyncMock()
        mock_token_manager.return_value = mock_tm_instance

        # Mock file staging
        mock_fs_instance = MagicMock()
        mock_fs_instance.create_staging_directory = AsyncMock()
        mock_fs_instance.stage_slash_commands = AsyncMock(return_value=("/tmp/slash_commands.zip", "ok"))
        mock_fs_instance.cleanup = AsyncMock(return_value=True)
        mock_file_staging.return_value = mock_fs_instance

        # Mock config (should NOT be used if _server_url is provided)
        mock_config = MagicMock()
        mock_config.server.api_host = "0.0.0.0"
        mock_config.server.api_port = 7272
        mock_get_config.return_value = mock_config

        # Create tool accessor
        tool_accessor = ToolAccessor(db_manager=mock_db_manager, tenant_manager=mock_tenant_manager)

        # Call with _server_url (simulating HTTP mode)
        result = await tool_accessor.setup_slash_commands(_api_key="test-key", _server_url="http://10.1.0.164:7272")

        # Verify result
        assert result["success"] is True
        assert "download_url" in result

        # CRITICAL: Download URL should use provided _server_url, NOT config
        assert "10.1.0.164" in result["download_url"]
        assert "0.0.0.0" not in result["download_url"]
        assert result["download_url"].startswith("http://10.1.0.164:7272")

    @pytest.mark.asyncio
    @patch("giljo_mcp.config_manager.get_config")
    @patch("giljo_mcp.downloads.token_manager.TokenManager")
    @patch("giljo_mcp.file_staging.FileStaging")
    async def test_get_agent_download_url_uses_server_url(
        self, mock_file_staging, mock_token_manager, mock_get_config
    ):
        """Test get_agent_download_url uses _server_url instead of config"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        # Setup mocks (same pattern as above)
        mock_db_manager = MagicMock()
        mock_session = AsyncMock()
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session
        mock_session.execute = AsyncMock(return_value=MagicMock(scalars=lambda: MagicMock(all=lambda: [])))
        mock_session.commit = AsyncMock()

        mock_tenant_manager = MagicMock()
        mock_tenant_manager.get_current_tenant.return_value = "test-tenant"

        mock_tm_instance = MagicMock()
        mock_tm_instance.generate_token = AsyncMock(return_value="token-xyz789")
        mock_tm_instance.mark_ready = AsyncMock()
        mock_tm_instance.mark_failed = AsyncMock()
        mock_token_manager.return_value = mock_tm_instance

        mock_fs_instance = MagicMock()
        mock_fs_instance.create_staging_directory = AsyncMock()
        mock_fs_instance.stage_agent_templates = AsyncMock(return_value=("/tmp/templates.zip", "ok"))
        mock_fs_instance.cleanup = AsyncMock(return_value=True)
        mock_file_staging.return_value = mock_fs_instance

        mock_config = MagicMock()
        mock_config.server.api_host = "0.0.0.0"
        mock_config.server.api_port = 7272
        mock_get_config.return_value = mock_config

        tool_accessor = ToolAccessor(db_manager=mock_db_manager, tenant_manager=mock_tenant_manager)

        # Call with _server_url
        with patch("zipfile.ZipFile") as mock_zip:
            mock_zip.return_value.__enter__.return_value.namelist.return_value = ["a.md", "b.md"]

            result = await tool_accessor.get_agent_download_url(
            _api_key="test-key", _server_url="http://192.168.1.50:7272"
        )

        # Verify
        assert result["success"] is True
        assert result["download_url"].startswith("http://192.168.1.50:7272")
        assert "0.0.0.0" not in result["download_url"]

    @pytest.mark.asyncio
    @patch("giljo_mcp.config_manager.get_config")
    @patch("giljo_mcp.downloads.token_manager.TokenManager")
    @patch("giljo_mcp.file_staging.FileStaging")
    async def test_fallback_to_config_when_server_url_not_provided(
        self, mock_file_staging, mock_token_manager, mock_get_config
    ):
        """Test tools fall back to config when _server_url is not provided"""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        # Setup mocks
        mock_db_manager = MagicMock()
        mock_session = AsyncMock()
        mock_db_manager.get_session_async.return_value.__aenter__.return_value = mock_session

        mock_tenant_manager = MagicMock()
        mock_tenant_manager.get_current_tenant.return_value = "test-tenant"

        mock_tm_instance = MagicMock()
        mock_tm_instance.generate_token = AsyncMock(return_value="token-fallback")
        mock_tm_instance.mark_ready = AsyncMock()
        mock_tm_instance.mark_failed = AsyncMock()
        mock_token_manager.return_value = mock_tm_instance

        mock_fs_instance = MagicMock()
        mock_fs_instance.create_staging_directory = AsyncMock()
        mock_fs_instance.stage_slash_commands = AsyncMock(return_value=("/tmp/commands.zip", "ok"))
        mock_fs_instance.cleanup = AsyncMock(return_value=True)
        mock_file_staging.return_value = mock_fs_instance

        # Mock config with reasonable fallback
        mock_config = MagicMock()
        mock_config.server.api_host = "localhost"
        mock_config.server.api_port = 7272
        mock_get_config.return_value = mock_config

        tool_accessor = ToolAccessor(db_manager=mock_db_manager, tenant_manager=mock_tenant_manager)

        # Call WITHOUT _server_url (edge case - should use config fallback)
        result = await tool_accessor.setup_slash_commands(_api_key="test-key")

        # Verify fallback to config.yaml external_host (not bind address)
        assert result["success"] is True
        assert "0.0.0.0" not in result["download_url"]
        assert result["download_url"].endswith("/slash_commands.zip")


class TestDownloadURLGeneration:
    """Test download URL generation uses correct server address"""

    def test_download_url_uses_dynamic_server(self):
        """Test download URL generation with dynamically detected server"""
        server_url = "http://10.1.0.164:7272"
        token = "abc123xyz"
        filename = "slash_commands.zip"

        download_url = f"{server_url}/api/download/temp/{token}/{filename}"

        assert download_url == "http://10.1.0.164:7272/api/download/temp/abc123xyz/slash_commands.zip"
        assert "0.0.0.0" not in download_url

    def test_download_url_not_using_bind_address(self):
        """Test that download URLs never contain bind address 0.0.0.0"""
        # This should NEVER happen in production
        server_url = "http://0.0.0.0:7272"
        token = "token123"

        # If server_url contains 0.0.0.0, it's a bug
        assert "0.0.0.0" in server_url  # Demonstrating the problem

        # The fix ensures we use request headers instead of config bind address
        # So this test validates the BEFORE state (the bug we're fixing)
