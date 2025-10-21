"""
Integration tests for v3.0 unified architecture cleanup.

Tests verify that:
1. API server always binds to 0.0.0.0 (all interfaces)
2. get_default_host() returns "0.0.0.0" (no mode-based logic)
3. Frontend config endpoint returns correct configuration
4. No deployment mode field in frontend config response
5. Authentication always enabled (v3.0 unified architecture)

This test suite follows TDD methodology - tests are written FIRST to define expected behavior,
then code is refactored to pass these tests.
"""

import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock


class TestV3UnifiedArchitecture:
    """Test v3.0 unified architecture - always bind 0.0.0.0, firewall controls access."""

    def test_get_default_host_always_returns_all_interfaces(self, tmp_path):
        """
        Test that get_default_host() ALWAYS returns "0.0.0.0".

        v3.0 Unified Architecture:
        - Server binds to all interfaces (0.0.0.0)
        - OS firewall controls access (defense in depth)
        - No mode-based binding logic
        - Single codebase for all deployment contexts
        """
        # Import the function we're testing
        from api.run_api import get_default_host

        # Create a test config.yaml without mode-based configuration
        config_data = {
            "installation": {
                "version": "3.0.0",
                "completed_at": "2025-01-20T00:00:00Z"
            },
            "services": {
                "api": {
                    "port": 7272,
                    # Note: No host configuration - using v3.0 default
                }
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        # Mock Path to return our test config
        with patch('pathlib.Path.__new__') as mock_path_new:
            mock_path_new.return_value = MagicMock()
            mock_path_new.return_value.parent.parent.parent = tmp_path
            mock_path_new.return_value.exists.return_value = True

            with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
                # Call get_default_host() - should ALWAYS return 0.0.0.0
                result = get_default_host()

        # CRITICAL: v3.0 always binds to all interfaces
        assert result == "0.0.0.0", "v3.0 unified architecture must ALWAYS bind to 0.0.0.0"

    def test_get_default_host_ignores_legacy_mode_field(self, tmp_path):
        """
        Test that get_default_host() ignores legacy 'mode' field if present.

        Even if config.yaml contains legacy mode field, v3.0 should ignore it
        and always return "0.0.0.0".
        """
        from api.run_api import get_default_host

        # Create config with legacy mode field (should be ignored)
        config_data = {
            "installation": {
                "mode": "localhost",  # Legacy field - should be ignored
                "version": "3.0.0"
            },
            "services": {
                "api": {
                    "port": 7272
                }
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        with patch('pathlib.Path.__new__') as mock_path_new:
            mock_path_new.return_value = MagicMock()
            mock_path_new.return_value.parent.parent.parent = tmp_path

            with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
                result = get_default_host()

        # Even with legacy mode=localhost, v3.0 MUST return 0.0.0.0
        assert result == "0.0.0.0", "v3.0 must ignore legacy mode field and always bind to 0.0.0.0"

    def test_get_default_host_respects_explicit_host_configuration(self, tmp_path):
        """
        Test that get_default_host() respects explicit host configuration.

        If user explicitly configures services.api.host, that should be honored.
        This allows advanced users to override default behavior if needed.
        """
        from api.run_api import get_default_host

        # User explicitly configures a specific host
        config_data = {
            "installation": {
                "version": "3.0.0"
            },
            "services": {
                "api": {
                    "host": "192.168.1.100",  # Explicit override
                    "port": 7272
                }
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        with patch('pathlib.Path.__new__') as mock_path_new:
            mock_path_new.return_value = MagicMock()
            mock_path_new.return_value.parent.parent.parent = tmp_path

            with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
                result = get_default_host()

        # Explicit configuration should be honored
        assert result == "192.168.1.100", "Explicit host configuration should be respected"

    def test_get_default_host_fallback_when_config_missing(self):
        """
        Test that get_default_host() returns "0.0.0.0" when config.yaml is missing.

        v3.0 safe default: bind to all interfaces (firewall controls access).
        """
        from api.run_api import get_default_host

        # Mock config file not existing
        with patch('pathlib.Path.exists', return_value=False):
            result = get_default_host()

        # v3.0 fallback should be 0.0.0.0 (not 127.0.0.1)
        assert result == "0.0.0.0", "v3.0 fallback must be 0.0.0.0 when config missing"


class TestFrontendConfigEndpointV3:
    """Test /api/v1/config/frontend endpoint for v3.0 unified architecture."""

    def test_frontend_config_excludes_mode_field(self, tmp_path):
        """
        Test that frontend config response DOES NOT include 'mode' field.

        v3.0 Unified Architecture:
        - No deployment modes
        - Single authentication flow
        - Frontend doesn't need mode information
        """
        # This test will fail until we remove 'mode' from the response

        # Create minimal config
        config_data = {
            "installation": {
                "version": "3.0.0"
            },
            "services": {
                "api": {
                    "port": 7272
                },
                "external_host": "192.168.1.100"
            },
            "features": {
                "api_keys_required": False,
                "ssl_enabled": False
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        # Mock the config file reading in configuration.py
        with patch('pathlib.Path.__truediv__') as mock_div:
            mock_div.return_value = config_path

            # Import endpoint function
            from api.endpoints.configuration import get_frontend_configuration

            # Mock the path resolution to use our test config
            import asyncio
            with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
                with patch('pathlib.Path.exists', return_value=True):
                    # Call endpoint (it's async)
                    response = asyncio.run(get_frontend_configuration())

        # CRITICAL: Response must NOT contain 'mode' field in v3.0
        assert "mode" not in response, "v3.0 frontend config must NOT include 'mode' field"

    def test_frontend_config_includes_necessary_fields(self, tmp_path):
        """
        Test that frontend config includes all necessary fields (but not mode).

        Required fields:
        - api.host
        - api.port
        - websocket.url
        - security.api_keys_required
        """
        config_data = {
            "installation": {
                "version": "3.0.0"
            },
            "services": {
                "api": {
                    "port": 7272
                },
                "external_host": "192.168.1.100"
            },
            "features": {
                "api_keys_required": True,
                "ssl_enabled": False
            }
        }

        config_path = tmp_path / "config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config_data, f)

        from api.endpoints.configuration import get_frontend_configuration
        import asyncio

        with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
            with patch('pathlib.Path.exists', return_value=True):
                response = asyncio.run(get_frontend_configuration())

        # Verify required fields are present
        assert "api" in response, "Response must include 'api' configuration"
        assert "host" in response["api"], "API config must include 'host'"
        assert "port" in response["api"], "API config must include 'port'"

        assert "websocket" in response, "Response must include 'websocket' configuration"
        assert "url" in response["websocket"], "WebSocket config must include 'url'"

        assert "security" in response, "Response must include 'security' configuration"
        assert "api_keys_required" in response["security"], "Security config must include api_keys_required"

        # Verify mode is NOT present
        assert "mode" not in response, "v3.0 must NOT include 'mode' field"

    def test_frontend_config_websocket_url_format(self, tmp_path):
        """
        Test that WebSocket URL is correctly formatted.

        Should use:
        - ws:// for HTTP
        - wss:// for HTTPS (SSL enabled)
        """
        config_data = {
            "services": {
                "api": {
                    "port": 7272
                },
                "external_host": "192.168.1.100"
            },
            "features": {
                "ssl_enabled": False,
                "api_keys_required": False
            }
        }

        from api.endpoints.configuration import get_frontend_configuration
        import asyncio

        with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
            with patch('pathlib.Path.exists', return_value=True):
                response = asyncio.run(get_frontend_configuration())

        # Verify WebSocket URL uses ws:// (not SSL)
        ws_url = response["websocket"]["url"]
        assert ws_url.startswith("ws://"), "WebSocket URL should use ws:// when SSL disabled"
        assert "192.168.1.100" in ws_url, "WebSocket URL should include external host"
        assert "7272" in ws_url, "WebSocket URL should include API port"

    def test_frontend_config_ssl_websocket_url(self, tmp_path):
        """
        Test that WebSocket URL uses wss:// when SSL is enabled.
        """
        config_data = {
            "services": {
                "api": {
                    "port": 7272
                },
                "external_host": "192.168.1.100"
            },
            "features": {
                "ssl_enabled": True,  # SSL enabled
                "api_keys_required": False
            }
        }

        from api.endpoints.configuration import get_frontend_configuration
        import asyncio

        with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
            with patch('pathlib.Path.exists', return_value=True):
                response = asyncio.run(get_frontend_configuration())

        # Verify WebSocket URL uses wss:// (SSL)
        ws_url = response["websocket"]["url"]
        assert ws_url.startswith("wss://"), "WebSocket URL should use wss:// when SSL enabled"


class TestV3ArchitectureDocumentation:
    """Test that code includes proper v3.0 architecture documentation."""

    def test_get_default_host_docstring_reflects_v3_architecture(self):
        """
        Test that get_default_host() docstring explains v3.0 unified architecture.

        Docstring should mention:
        - Always returns 0.0.0.0 (binds to all interfaces)
        - Firewall controls access (defense in depth)
        - No mode-based logic
        - Explicit host configuration can override
        """
        from api.run_api import get_default_host

        docstring = get_default_host.__doc__
        assert docstring is not None, "get_default_host() must have docstring"

        # Verify docstring mentions v3.0 architecture
        docstring_lower = docstring.lower()
        assert "v3.0" in docstring_lower or "unified" in docstring_lower, \
            "Docstring should reference v3.0 unified architecture"
        assert "0.0.0.0" in docstring, \
            "Docstring should mention 0.0.0.0 binding"
        assert "firewall" in docstring_lower or "defense" in docstring_lower, \
            "Docstring should explain firewall-based access control"

    def test_frontend_config_endpoint_docstring_reflects_v3_architecture(self):
        """
        Test that get_frontend_configuration() docstring reflects v3.0 architecture.

        Docstring should mention:
        - No mode field in response
        - v3.0 unified architecture
        - Essential frontend configuration only
        """
        from api.endpoints.configuration import get_frontend_configuration

        docstring = get_frontend_configuration.__doc__
        assert docstring is not None, "get_frontend_configuration() must have docstring"

        docstring_lower = docstring.lower()

        # Docstring should mention v3.0 or unified architecture
        assert "v3.0" in docstring_lower or "unified" in docstring_lower, \
            "Docstring should reference v3.0 unified architecture"


class TestBackwardCompatibility:
    """Test that refactored code maintains backward compatibility where appropriate."""

    def test_explicit_host_configuration_still_works(self, tmp_path):
        """
        Test that explicitly configured host is still respected.

        This ensures backward compatibility for users who explicitly
        configured services.api.host in config.yaml.
        """
        from api.run_api import get_default_host

        config_data = {
            "services": {
                "api": {
                    "host": "10.1.0.164",  # Explicit configuration
                    "port": 7272
                }
            }
        }

        with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
            with patch('pathlib.Path.exists', return_value=True):
                result = get_default_host()

        # Explicit configuration should be honored for backward compatibility
        assert result == "10.1.0.164", \
            "Explicit host configuration should still be respected for backward compatibility"

    def test_frontend_config_response_structure_backward_compatible(self, tmp_path):
        """
        Test that frontend config response structure is backward compatible.

        Frontend code may expect certain fields - ensure we don't break existing
        clients, only remove the 'mode' field.
        """
        config_data = {
            "services": {
                "api": {
                    "port": 7272
                },
                "external_host": "192.168.1.100"
            },
            "features": {
                "api_keys_required": False,
                "ssl_enabled": False
            }
        }

        from api.endpoints.configuration import get_frontend_configuration
        import asyncio

        with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
            with patch('pathlib.Path.exists', return_value=True):
                response = asyncio.run(get_frontend_configuration())

        # Ensure all expected fields are present (except mode)
        expected_top_level_keys = {"api", "websocket", "security"}
        actual_keys = set(response.keys())

        # All expected keys should be present
        assert expected_top_level_keys.issubset(actual_keys), \
            f"Response missing expected keys. Expected: {expected_top_level_keys}, Got: {actual_keys}"

        # 'mode' should NOT be present
        assert "mode" not in actual_keys, "v3.0 response must not include 'mode' field"


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_get_default_host_handles_empty_config(self):
        """
        Test that get_default_host() handles empty config.yaml gracefully.
        """
        from api.run_api import get_default_host

        # Empty config
        config_data = {}

        with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
            with patch('pathlib.Path.exists', return_value=True):
                result = get_default_host()

        # Should return v3.0 default
        assert result == "0.0.0.0", "Empty config should return v3.0 default (0.0.0.0)"

    def test_get_default_host_handles_malformed_config(self):
        """
        Test that get_default_host() handles malformed config.yaml gracefully.
        """
        from api.run_api import get_default_host

        # Malformed YAML
        malformed_yaml = "{ invalid yaml: ["

        with patch('builtins.open', mock_open(read_data=malformed_yaml)):
            with patch('pathlib.Path.exists', return_value=True):
                # Should not crash, should return safe default
                result = get_default_host()

        # Should return v3.0 default even with malformed config
        assert result == "0.0.0.0", "Malformed config should return v3.0 default (0.0.0.0)"

    def test_frontend_config_handles_missing_external_host(self, tmp_path):
        """
        Test that frontend config handles missing external_host gracefully.

        Should fall back to 'localhost' if external_host not configured.
        """
        config_data = {
            "services": {
                "api": {
                    "port": 7272
                }
                # No external_host configured
            },
            "features": {
                "api_keys_required": False,
                "ssl_enabled": False
            }
        }

        from api.endpoints.configuration import get_frontend_configuration
        import asyncio

        with patch('builtins.open', mock_open(read_data=yaml.dump(config_data))):
            with patch('pathlib.Path.exists', return_value=True):
                response = asyncio.run(get_frontend_configuration())

        # Should not crash, should fall back to localhost
        assert "api" in response
        assert "host" in response["api"]
        # Fallback should be 'localhost' for frontend connection
        assert response["api"]["host"] == "localhost", \
            "Missing external_host should fall back to 'localhost'"
