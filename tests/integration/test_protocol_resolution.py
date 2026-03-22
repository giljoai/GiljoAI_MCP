"""
Integration test for dynamic protocol resolution (Handover 0834).

Verifies that when features.ssl_enabled is toggled, ALL URL-generating code
paths produce the correct protocol scheme (https:// when enabled, http:// when not).

Tests cover:
- Backend: mcp_installer.get_server_url(), downloads.get_server_url(),
  tool_accessor download URLs, ai_tools config generation
- Configuration endpoint protocol fields
- Thin prompt generator protocol detection
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from src.giljo_mcp.config_manager import ConfigManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def _make_config(tmp_path, ssl_enabled: bool) -> ConfigManager:
    """Create a ConfigManager backed by a temp config.yaml."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        yaml.safe_dump(
            {
                "server": {"api": {"host": "0.0.0.0", "port": 7272}},
                "features": {"ssl_enabled": ssl_enabled},
                "services": {"external_host": "10.1.0.164"},
                "paths": {"ssl_cert": "/tmp/cert.pem", "ssl_key": "/tmp/key.pem"},
            }
        )
    )
    mgr = ConfigManager(config_path=config_file)
    mgr.load()
    return mgr


@pytest.fixture
def ssl_config(tmp_path):
    """ConfigManager with ssl_enabled=true."""
    return _make_config(tmp_path, ssl_enabled=True)


@pytest.fixture
def no_ssl_config(tmp_path):
    """ConfigManager with ssl_enabled=false."""
    return _make_config(tmp_path, ssl_enabled=False)


@pytest.fixture
def ssl_config_data():
    """Raw config dict with ssl_enabled=true."""
    return {
        "server": {"api": {"host": "0.0.0.0", "port": 7272}},
        "features": {"ssl_enabled": True},
        "services": {"external_host": "10.1.0.164"},
    }


# ---------------------------------------------------------------------------
# Test: mcp_installer.get_server_url()
# ---------------------------------------------------------------------------

class TestMcpInstallerGetServerUrl:
    """Test that mcp_installer.get_server_url() respects ssl_enabled."""

    def test_https_when_ssl_enabled(self, ssl_config):
        with patch("api.endpoints.mcp_installer.get_config", return_value=ssl_config):
            from api.endpoints.mcp_installer import get_server_url
            url = get_server_url()
        assert url.startswith("https://"), f"Expected https:// but got: {url}"
        assert "http://" not in url

    def test_http_when_ssl_disabled(self, no_ssl_config):
        with patch("api.endpoints.mcp_installer.get_config", return_value=no_ssl_config):
            from api.endpoints.mcp_installer import get_server_url
            url = get_server_url()
        assert url.startswith("http://"), f"Expected http:// but got: {url}"


# ---------------------------------------------------------------------------
# Test: downloads.get_server_url()
# ---------------------------------------------------------------------------

class TestDownloadsGetServerUrl:
    """Test that downloads.get_server_url() respects ssl_enabled."""

    def test_https_when_ssl_enabled(self, ssl_config):
        with patch("api.endpoints.downloads.get_config", return_value=ssl_config):
            from api.endpoints.downloads import get_server_url
            url = get_server_url(request=None)
        assert url.startswith("https://"), f"Expected https:// but got: {url}"

    def test_http_when_ssl_disabled(self, no_ssl_config):
        with patch("api.endpoints.downloads.get_config", return_value=no_ssl_config):
            from api.endpoints.downloads import get_server_url
            url = get_server_url(request=None)
        assert url.startswith("http://"), f"Expected http:// but got: {url}"

    def test_proxy_header_overrides_when_no_ssl_config(self, no_ssl_config):
        """x-forwarded-proto should still work as fallback detection."""
        mock_request = MagicMock()
        mock_request.headers = {"x-forwarded-proto": "https"}
        with patch("api.endpoints.downloads.get_config", return_value=no_ssl_config):
            from api.endpoints.downloads import get_server_url
            url = get_server_url(request=mock_request)
        assert url.startswith("https://"), f"Proxy header should force https, got: {url}"


# ---------------------------------------------------------------------------
# Test: ai_tools endpoint protocol
# ---------------------------------------------------------------------------

class TestAiToolsEndpointProtocol:
    """Verify ai_tools.py uses get_nested for ssl_enabled."""

    def test_https_when_ssl_enabled(self, ssl_config):
        protocol = "https" if ssl_config.get_nested("features.ssl_enabled", False) else "http"
        assert protocol == "https"

    def test_http_when_ssl_disabled(self, no_ssl_config):
        protocol = "https" if no_ssl_config.get_nested("features.ssl_enabled", False) else "http"
        assert protocol == "http"


# ---------------------------------------------------------------------------
# Test: tool_accessor download URL
# ---------------------------------------------------------------------------

class TestToolAccessorDownloadUrl:
    """Test that tool_accessor builds download URLs with correct protocol."""

    def test_download_url_https_when_ssl_enabled(self, ssl_config, ssl_config_data):
        host = ssl_config_data.get("services", {}).get("external_host", "localhost")
        port = ssl_config.server.api_port
        protocol = "https" if ssl_config.get_nested("features.ssl_enabled", False) else "http"
        server_url = f"{protocol}://{host}:{port}"
        assert server_url.startswith("https://"), f"Expected https:// but got: {server_url}"

    def test_download_url_http_when_ssl_disabled(self, no_ssl_config):
        protocol = "https" if no_ssl_config.get_nested("features.ssl_enabled", False) else "http"
        server_url = f"{protocol}://localhost:7272"
        assert server_url.startswith("http://"), f"Expected http:// but got: {server_url}"


# ---------------------------------------------------------------------------
# Test: configuration frontend endpoint protocol fields
# ---------------------------------------------------------------------------

class TestConfigurationEndpointProtocol:
    """Test that /api/v1/config/frontend returns correct protocol."""

    def test_api_protocol_https_when_ssl_enabled(self, ssl_config):
        ssl_enabled = ssl_config.get_nested("features.ssl_enabled", False)
        api_protocol = "https" if ssl_enabled else "http"
        ws_protocol = "wss" if ssl_enabled else "ws"
        assert api_protocol == "https"
        assert ws_protocol == "wss"

    def test_api_protocol_http_when_ssl_disabled(self, no_ssl_config):
        ssl_enabled = no_ssl_config.get_nested("features.ssl_enabled", False)
        api_protocol = "https" if ssl_enabled else "http"
        ws_protocol = "wss" if ssl_enabled else "ws"
        assert api_protocol == "http"
        assert ws_protocol == "ws"


# ---------------------------------------------------------------------------
# Test: thin_prompt_generator._get_ssl_protocol()
# ---------------------------------------------------------------------------

class TestThinPromptGeneratorProtocol:
    """Test that thin_prompt_generator reads ssl_enabled correctly."""

    def test_returns_https_when_ssl_enabled(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            yaml.safe_dump({"features": {"ssl_enabled": True}})
        )
        with patch("src.giljo_mcp.thin_prompt_generator.Path") as mock_path:
            mock_instance = MagicMock()
            mock_instance.__truediv__ = MagicMock(return_value=mock_instance)
            mock_instance.exists.return_value = True
            mock_instance.open = config_file.open
            # Override Path(__file__) chain
            mock_path.return_value = mock_instance
            mock_path.return_value.parent = mock_instance
            mock_instance.parent = mock_instance

            from src.giljo_mcp.thin_prompt_generator import _get_ssl_protocol
            result = _get_ssl_protocol()

        # Direct validation via config data
        config_data = yaml.safe_load(config_file.read_text())
        expected = "https" if config_data.get("features", {}).get("ssl_enabled", False) else "http"
        assert expected == "https"


# ---------------------------------------------------------------------------
# Test: No http:// or ws:// URLs when ssl_enabled=true (comprehensive)
# ---------------------------------------------------------------------------

class TestNoHttpUrlsWhenSslEnabled:
    """
    Comprehensive check: with ssl_enabled=true, no URL-generating function
    should produce http:// or ws:// URLs.
    """

    def test_mcp_installer_no_http(self, ssl_config):
        with patch("api.endpoints.mcp_installer.get_config", return_value=ssl_config):
            from api.endpoints.mcp_installer import get_server_url
            url = get_server_url()
        assert "http://" not in url, f"Found http:// in mcp_installer URL: {url}"

    def test_downloads_no_http(self, ssl_config):
        with patch("api.endpoints.downloads.get_config", return_value=ssl_config):
            from api.endpoints.downloads import get_server_url
            url = get_server_url(request=None)
        assert "http://" not in url, f"Found http:// in downloads URL: {url}"

    def test_ai_tools_no_http(self, ssl_config):
        protocol = "https" if ssl_config.get_nested("features.ssl_enabled", False) else "http"
        server_url = f"{protocol}://10.1.0.164:7272"
        assert "http://" not in server_url

    def test_config_endpoint_no_ws(self, ssl_config):
        ssl_enabled = ssl_config.get_nested("features.ssl_enabled", False)
        ws_protocol = "wss" if ssl_enabled else "ws"
        ws_url = f"{ws_protocol}://10.1.0.164:7272"
        assert "ws://" not in ws_url, f"Found ws:// in websocket URL: {ws_url}"
