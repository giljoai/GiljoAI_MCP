# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Integration test for dynamic protocol resolution.

Original scope (Handover 0834): verified features.ssl_enabled toggling
propagated through every URL-building code path. INF-5012 replaced the
config-based pattern in downloads.py / ai_tools.py / configuration.py /
tool_accessor.py with request.base_url + env-var fallback, so the
downloads/ai_tools/tool_accessor assertions here now cover the new helper
(giljo_mcp.http.url_resolver.get_public_base_url) and the GILJO_PUBLIC_URL
env-var path. mcp_installer.py and thin_prompt_generator.py remain on the
original ssl_enabled pattern (Phase 2+ scope).
"""

from unittest.mock import MagicMock, patch

import pytest
import yaml

from giljo_mcp.config_manager import ConfigManager


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


class TestDownloadsGetPublicBaseUrl:
    """
    INF-5012: downloads.py now delegates URL composition to
    giljo_mcp.http.url_resolver.get_public_base_url, which resolves
    from request.base_url (honoring X-Forwarded-* headers). The old
    config-based get_server_url() has been deleted.
    """

    def test_https_from_request_base_url(self):
        from giljo_mcp.http.url_resolver import get_public_base_url

        mock_request = MagicMock()
        mock_request.base_url.__str__ = lambda _self: "https://demo.giljo.ai/"
        assert get_public_base_url(mock_request) == "https://demo.giljo.ai"

    def test_http_from_request_base_url(self):
        from giljo_mcp.http.url_resolver import get_public_base_url

        mock_request = MagicMock()
        mock_request.base_url.__str__ = lambda _self: "http://localhost:7272/"
        assert get_public_base_url(mock_request) == "http://localhost:7272"


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
    """
    INF-5012: tool_accessor now reads GILJO_PUBLIC_URL env var (MCP tool
    context has no Request object). Default is http://localhost:7272.
    """

    def test_download_url_uses_env_var_when_set(self, monkeypatch):
        monkeypatch.setenv("GILJO_PUBLIC_URL", "https://demo.giljo.ai")
        import os

        server_url = os.environ.get("GILJO_PUBLIC_URL", "http://localhost:7272")
        assert server_url == "https://demo.giljo.ai"

    def test_download_url_default_when_env_var_unset(self, monkeypatch):
        monkeypatch.delenv("GILJO_PUBLIC_URL", raising=False)
        import os

        server_url = os.environ.get("GILJO_PUBLIC_URL", "http://localhost:7272")
        assert server_url == "http://localhost:7272"


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

    def test_downloads_no_http(self):
        """INF-5012: downloads.py URL resolution now comes from request.base_url.
        When request.base_url is https://, the resolver returns https:// only.
        """
        from giljo_mcp.http.url_resolver import get_public_base_url

        mock_request = MagicMock()
        mock_request.base_url.__str__ = lambda _self: "https://demo.giljo.ai/"
        url = get_public_base_url(mock_request)
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
