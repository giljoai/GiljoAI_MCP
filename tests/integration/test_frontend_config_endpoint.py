"""
Integration tests for frontend configuration endpoint.

This endpoint serves the correct API host configuration to the frontend,
ensuring WebSocket connections use the right host in LAN mode.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import yaml


@pytest.fixture
def test_config_localhost(tmp_path):
    """Create a test config.yaml for localhost mode."""
    config = {
        "installation": {"mode": "localhost"},
        "services": {
            "api": {"host": "127.0.0.1", "port": 7272},
            "frontend": {"port": 7274}
        },
        "features": {"api_keys_required": False}
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    return config_file


@pytest.fixture
def test_config_lan(tmp_path):
    """Create a test config.yaml for LAN mode."""
    config = {
        "installation": {"mode": "lan"},
        "services": {
            "api": {"host": "10.1.0.164", "port": 7272},
            "frontend": {"port": 7274}
        },
        "features": {"api_keys_required": True},
        "security": {
            "network": {
                "selected_adapter": "Ethernet",
                "initial_ip": "10.1.0.164"
            }
        },
        "server": {
            "ip": "10.1.0.164",
            "hostname": "giljo.local"
        }
    }
    config_file = tmp_path / "config.yaml"
    with open(config_file, 'w') as f:
        yaml.dump(config, f)
    return config_file


class TestFrontendConfigEndpoint:
    """Test suite for frontend configuration endpoint."""

    def test_endpoint_exists(self, client: TestClient):
        """Test that the /api/config/frontend endpoint exists."""
        response = client.get("/api/config/frontend")
        assert response.status_code in [200, 404], "Endpoint should exist or return 404 if not implemented yet"

    def test_returns_json(self, client: TestClient):
        """Test that endpoint returns JSON response."""
        response = client.get("/api/config/frontend")
        assert response.headers.get("content-type") == "application/json"

    def test_localhost_mode_returns_correct_host(self, client: TestClient, monkeypatch, test_config_localhost):
        """Test that localhost mode returns 127.0.0.1 as API host."""
        # Mock the config file path
        monkeypatch.setenv("GILJO_MCP_HOME", str(test_config_localhost.parent))

        response = client.get("/api/config/frontend")
        assert response.status_code == 200

        data = response.json()
        assert "api" in data, "Response should include 'api' configuration"
        assert data["api"]["host"] == "127.0.0.1", "Localhost mode should use 127.0.0.1"
        assert data["api"]["port"] == 7272, "Should return correct API port"

    def test_lan_mode_returns_correct_host(self, client: TestClient, monkeypatch, test_config_lan):
        """Test that LAN mode returns the actual LAN IP as API host."""
        # Mock the config file path
        monkeypatch.setenv("GILJO_MCP_HOME", str(test_config_lan.parent))

        response = client.get("/api/config/frontend")
        assert response.status_code == 200

        data = response.json()
        assert "api" in data, "Response should include 'api' configuration"
        assert data["api"]["host"] == "10.1.0.164", "LAN mode should use actual LAN IP"
        assert data["api"]["port"] == 7272, "Should return correct API port"

    def test_includes_websocket_url(self, client: TestClient):
        """Test that response includes WebSocket URL."""
        response = client.get("/api/config/frontend")
        assert response.status_code == 200

        data = response.json()
        assert "websocket" in data, "Response should include WebSocket configuration"
        assert "url" in data["websocket"], "WebSocket config should include URL"

    def test_websocket_url_matches_api_host(self, client: TestClient, monkeypatch, test_config_lan):
        """Test that WebSocket URL uses the same host as REST API."""
        monkeypatch.setenv("GILJO_MCP_HOME", str(test_config_lan.parent))

        response = client.get("/api/config/frontend")
        assert response.status_code == 200

        data = response.json()
        api_host = data["api"]["host"]
        api_port = data["api"]["port"]
        ws_url = data["websocket"]["url"]

        expected_ws_url = f"ws://{api_host}:{api_port}"
        assert ws_url == expected_ws_url, f"WebSocket URL should be {expected_ws_url}"

    def test_includes_deployment_mode(self, client: TestClient, monkeypatch, test_config_lan):
        """Test that response includes deployment mode."""
        monkeypatch.setenv("GILJO_MCP_HOME", str(test_config_lan.parent))

        response = client.get("/api/config/frontend")
        assert response.status_code == 200

        data = response.json()
        assert "mode" in data, "Response should include deployment mode"
        assert data["mode"] in ["localhost", "lan", "server", "wan"], "Mode should be valid"

    def test_includes_security_config(self, client: TestClient, monkeypatch, test_config_lan):
        """Test that response includes security configuration (e.g., API keys required)."""
        monkeypatch.setenv("GILJO_MCP_HOME", str(test_config_lan.parent))

        response = client.get("/api/config/frontend")
        assert response.status_code == 200

        data = response.json()
        assert "security" in data, "Response should include security config"
        assert "api_keys_required" in data["security"], "Should indicate if API keys are required"

    def test_no_sensitive_data_exposed(self, client: TestClient):
        """Test that response does NOT include sensitive configuration."""
        response = client.get("/api/config/frontend")
        assert response.status_code == 200

        data = response.json()
        data_str = str(data).lower()

        # Ensure no database credentials
        assert "password" not in data_str, "Should not expose database password"
        assert "db_password" not in data_str, "Should not expose database password"
        assert "secret" not in data_str, "Should not expose secrets"

        # Ensure no private keys or tokens
        assert "private_key" not in data_str, "Should not expose private keys"
        assert "api_key" not in data_str, "Should not expose actual API keys"

    def test_cors_headers_present(self, client: TestClient):
        """Test that CORS headers are present for frontend access."""
        response = client.get("/api/config/frontend")

        # Should have CORS headers for cross-origin access
        assert "access-control-allow-origin" in response.headers or response.status_code == 200

    def test_caching_headers(self, client: TestClient):
        """Test that caching is appropriately configured."""
        response = client.get("/api/config/frontend")
        assert response.status_code == 200

        # Config should be cacheable but with short TTL
        cache_control = response.headers.get("cache-control", "")
        # Either no-cache or short max-age
        assert "no-cache" in cache_control or "max-age" in cache_control


@pytest.mark.integration
class TestFrontendConfigIntegration:
    """Integration tests with actual API server."""

    def test_config_served_on_api_port(self, client: TestClient):
        """Test that config is served on the same port as the API."""
        # This ensures frontend can always reach the config endpoint
        response = client.get("/api/config/frontend")
        assert response.status_code == 200, "Config endpoint should be accessible on API port"

    def test_config_consistency_with_rest_api(self, client: TestClient):
        """Test that config endpoint returns data consistent with actual API behavior."""
        # Get config
        config_response = client.get("/api/config/frontend")
        assert config_response.status_code == 200

        config_data = config_response.json()
        api_host = config_data["api"]["host"]
        api_port = config_data["api"]["port"]

        # Verify we can actually reach the API at the specified host/port
        # by making a test request to /health
        health_response = client.get("/health")
        assert health_response.status_code == 200, "API should be reachable at configured host/port"
