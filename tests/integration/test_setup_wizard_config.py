"""
Integration tests for Setup Wizard Configuration Generation.

Tests verify that the setup wizard correctly generates config.yaml for all deployment modes:
- Localhost mode: 127.0.0.1 binding, no API keys, no network CORS
- LAN mode: Selected adapter IP binding, API key generation, network CORS
- Mode conversions: Localhost -> LAN, LAN -> Localhost

These tests follow TDD methodology - written BEFORE implementation to define expected behavior.

Author: Backend Integration Tester Agent
Test Focus: Configuration file generation and deployment mode handling
Critical: Multi-tenant isolation, network binding correctness, security settings
"""

import pytest
import yaml
from pathlib import Path
from datetime import datetime, timezone
from fastapi.testclient import TestClient


@pytest.fixture
def client(monkeypatch):
    """
    Create test client with proper lifespan context.
    
    TestClient must be used as a context manager to trigger lifespan events.
    This ensures the database manager and other app state are properly
    initialized, which is critical for LAN mode tests that create users.
    """
    import os
    
    # Set up database environment for tests
    # This ensures the app can initialize the database manager
    monkeypatch.setenv("DATABASE_URL", "postgresql://postgres:***@localhost:5432/giljo_mcp_test")
    
    from api.app import create_app

    app = create_app()
    
    # Use TestClient as context manager to trigger lifespan
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def fresh_config_file(tmp_path, monkeypatch):
    """
    Create a fresh config.yaml file for testing.

    Simulates a clean installation with no prior configuration.
    """
    config_file = tmp_path / "config.yaml"

    # Initial minimal config (as created by installer)
    initial_config = {
        "installation": {
            "version": "2.0.0",
            "mode": "localhost",  # Default mode
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "name": "giljo_mcp",
            "user": "giljo_user",
        },
        "services": {
            "api": {
                "host": "127.0.0.1",  # Default: localhost binding
                "port": 7272,
            },
            "frontend": {
                "port": 7274,
            },
        },
        "security": {
            "cors": {
                "allowed_origins": [
                    "http://127.0.0.1:7274",
                    "http://localhost:7274",
                ]
            }
        },
        "setup": {
            "completed": False,  # Start uncompleted - wizard will complete it
        },
    }

    with open(config_file, 'w', encoding='utf-8') as f:
        yaml.dump(initial_config, f, default_flow_style=False)

    # Mock get_config_path() to use tmp_path
    import api.endpoints.setup as setup_module

    original_get_config_path = setup_module.get_config_path

    def mock_get_config_path():
        return config_file

    monkeypatch.setattr(setup_module, "get_config_path", mock_get_config_path)

    yield config_file

    # Cleanup: restore original function
    monkeypatch.setattr(setup_module, "get_config_path", original_get_config_path)


@pytest.fixture
def mock_db_session(monkeypatch):
    """Mock database session for tests that don't need real database"""
    from unittest.mock import AsyncMock, MagicMock

    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()
    mock_session.flush = AsyncMock()
    mock_session.commit = AsyncMock()
    mock_session.add = MagicMock()

    # Mock get_session_async context manager
    async def mock_get_session():
        yield mock_session

    return mock_session


class TestFreshLocalhostInstall:
    """Test 1: Fresh Localhost Mode Installation"""

    def test_localhost_mode_configuration(self, client, fresh_config_file):
        """
        Verify localhost mode generates correct config.

        Expected Behavior:
        - config["services"]["api"]["host"] == "127.0.0.1"
        - config["database"]["host"] == "localhost" (unchanged)
        - config["installation"]["mode"] == "localhost"
        - No API key generated
        - CORS origins remain localhost-only
        """
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost",
            "serena_enabled": False,
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201], f"Setup failed: {response.text}"

        # Verify response
        data = response.json()
        assert data["success"] is True
        assert data.get("api_key") is None, "Localhost mode should NOT generate API key"
        assert data.get("requires_restart") is False, "Localhost mode should not require restart"
        assert data.get("mode") == "localhost"

        # Read generated config.yaml
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # CRITICAL: Verify API host binding
        assert config["services"]["api"]["host"] == "127.0.0.1", \
            "Localhost mode must bind to 127.0.0.1 (NOT 0.0.0.0)"

        # Verify database host unchanged (always localhost)
        assert config["database"]["host"] == "localhost", \
            "Database host should remain 'localhost'"

        # Verify installation mode
        assert config["installation"]["mode"] == "localhost"

        # Verify setup completion
        assert config["setup"]["completed"] is True

        # Verify CORS origins (should be localhost only)
        cors_origins = config["security"]["cors"]["allowed_origins"]
        assert "http://127.0.0.1:7274" in cors_origins
        assert "http://localhost:7274" in cors_origins

        # Should NOT have network IPs
        for origin in cors_origins:
            assert not origin.startswith("http://192.168."), \
                "Localhost mode should not have LAN IPs in CORS"
            assert not origin.startswith("http://10."), \
                "Localhost mode should not have LAN IPs in CORS"

    def test_localhost_mode_no_server_section(self, client, fresh_config_file):
        """
        Verify localhost mode does NOT create server section.

        The server section is only for LAN/WAN modes with network configuration.
        """
        payload = {
            "tools_attached": [],
            "network_mode": "localhost",
            "serena_enabled": False,
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Should NOT have server section
        assert "server" not in config, \
            "Localhost mode should not create server section"

    def test_localhost_mode_features_config(self, client, fresh_config_file):
        """
        Verify localhost mode disables API key authentication.
        """
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost",
            "serena_enabled": False,
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Verify feature flags
        features = config.get("features", {})
        assert features.get("api_keys_required") is False, \
            "Localhost mode should disable API key requirement"
        assert features.get("multi_user") is False, \
            "Localhost mode should disable multi-user features"


class TestFreshLANInstall:
    """Test 2: Fresh LAN Mode Installation with Adapter IP"""

    def test_lan_mode_uses_adapter_ip(self, client, fresh_config_file):
        """
        CRITICAL: Verify LAN mode uses selected adapter IP (NOT 0.0.0.0).

        This is a key fix - the wizard should bind to the specific adapter IP
        selected by the user, not to all interfaces (0.0.0.0).

        Expected Behavior:
        - config["services"]["api"]["host"] == "10.1.0.164" (adapter IP)
        - config["database"]["host"] == "localhost" (unchanged!)
        - config["installation"]["mode"] == "lan"
        - API key is generated
        - selected_adapter metadata is saved
        """
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "10.1.0.164",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "hostname": "giljo.local",
                "adapter_name": "Ethernet",
                "adapter_id": "eth0",
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201], f"Setup failed: {response.text}"

        # Verify response
        data = response.json()
        assert data["success"] is True
        assert data.get("requires_restart") is True, "LAN mode requires restart"
        assert data.get("mode") == "lan"

        # Read generated config.yaml
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # CRITICAL: Verify API host is adapter IP (NOT 0.0.0.0)
        assert config["services"]["api"]["host"] == "10.1.0.164", \
            "LAN mode must use selected adapter IP, NOT 0.0.0.0"

        # Verify database host unchanged (always localhost)
        assert config["database"]["host"] == "localhost", \
            "Database host should ALWAYS remain 'localhost' (never network IP)"

        # Verify installation mode
        assert config["installation"]["mode"] == "lan"

        # Verify server section created
        assert "server" in config, "LAN mode should create server section"
        server_config = config["server"]

        assert server_config["ip"] == "10.1.0.164"
        assert server_config["hostname"] == "giljo.local"
        assert server_config["admin_user"] == "admin"
        assert server_config["firewall_configured"] is True

        # CRITICAL: Verify selected adapter metadata saved
        assert "selected_adapter" in server_config, \
            "LAN mode should save selected adapter metadata"

        adapter = server_config["selected_adapter"]
        assert adapter["name"] == "Ethernet"
        assert adapter["id"] == "eth0"
        assert adapter["initial_ip"] == "10.1.0.164"
        assert "detected_at" in adapter

    def test_lan_mode_cors_origins(self, client, fresh_config_file):
        """
        Verify LAN mode adds adapter IP to CORS origins.

        CORS origins should include:
        - http://127.0.0.1:7274 (preserved)
        - http://localhost:7274 (preserved)
        - http://10.1.0.164:7274 (NEW - adapter IP)
        - http://giljo.local:7274 (NEW - hostname)
        """
        payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "10.1.0.164",
                "firewall_configured": False,
                "admin_username": "admin",
                "admin_password": "password123",
                "hostname": "giljo.local",
                "adapter_name": "WiFi",
                "adapter_id": "wlan0",
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        cors_origins = config["security"]["cors"]["allowed_origins"]

        # Verify localhost origins preserved
        assert "http://127.0.0.1:7274" in cors_origins, \
            "Should preserve localhost origin"
        assert "http://localhost:7274" in cors_origins, \
            "Should preserve localhost origin"

        # Verify adapter IP added
        assert "http://10.1.0.164:7274" in cors_origins, \
            "Should add adapter IP to CORS origins"

        # Verify hostname added
        assert "http://giljo.local:7274" in cors_origins, \
            "Should add hostname to CORS origins"

    def test_lan_mode_api_key_authentication(self, client, fresh_config_file):
        """
        Verify LAN mode enables API key authentication.
        """
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "192.168.1.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "SecurePass789!",
                "hostname": "giljo-server",
                "adapter_name": "Ethernet 2",
                "adapter_id": "eth1",
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Verify features
        features = config.get("features", {})
        assert features.get("api_keys_required") is True, \
            "LAN mode should enable API key requirement"
        assert features.get("multi_user") is True, \
            "LAN mode should enable multi-user features"

    def test_lan_mode_without_adapter_metadata(self, client, fresh_config_file):
        """
        Verify LAN mode works even if adapter metadata not provided.

        This handles backward compatibility - if adapter_name/adapter_id
        not provided, still configure LAN mode correctly.
        """
        payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": False,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
                # No adapter_name or adapter_id
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Should still use server IP
        assert config["services"]["api"]["host"] == "192.168.1.50"

        # Server section should exist but without adapter metadata
        server_config = config.get("server", {})
        assert server_config.get("ip") == "192.168.1.50"

        # selected_adapter may not exist (backward compat)
        # This is acceptable


class TestLocalhostToLANConversion:
    """Test 3: Converting from Localhost to LAN Mode"""

    def test_localhost_to_lan_conversion(self, client, fresh_config_file):
        """
        Verify mode conversion updates config correctly.

        Scenario: User initially set up localhost mode, now converting to LAN.

        Expected Changes:
        - config["services"]["api"]["host"]: 127.0.0.1 -> 10.1.0.164
        - config["database"]["host"]: "localhost" (unchanged)
        - config["installation"]["mode"]: "localhost" -> "lan"
        - API key generated
        - CORS origins updated with LAN IPs
        - Server section created
        """
        # Step 1: Initial localhost setup
        localhost_payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost",
            "serena_enabled": False,
        }

        response1 = client.post("/api/setup/complete", json=localhost_payload)
        assert response1.status_code in [200, 201]

        # Verify localhost mode active
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config_before = yaml.safe_load(f)

        assert config_before["services"]["api"]["host"] == "127.0.0.1"
        assert config_before["installation"]["mode"] == "localhost"
        assert "server" not in config_before

        # Step 2: Convert to LAN mode
        lan_payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "10.1.0.164",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "NewPassword123!",
                "hostname": "giljo.local",
                "adapter_name": "Ethernet",
                "adapter_id": "eth0",
            }
        }

        response2 = client.post("/api/setup/complete", json=lan_payload)
        assert response2.status_code in [200, 201]

        # Verify conversion successful
        data = response2.json()
        assert data["success"] is True
        assert data["mode"] == "lan"
        assert data["requires_restart"] is True

        # Read final config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config_after = yaml.safe_load(f)

        # CRITICAL: Verify API host changed to adapter IP
        assert config_after["services"]["api"]["host"] == "10.1.0.164", \
            "Conversion should update API host to adapter IP"

        # Verify database host UNCHANGED
        assert config_after["database"]["host"] == "localhost", \
            "Database host should NEVER change"

        # Verify mode changed
        assert config_after["installation"]["mode"] == "lan"

        # Verify server section created
        assert "server" in config_after
        assert config_after["server"]["ip"] == "10.1.0.164"

        # Verify CORS origins updated
        cors_origins = config_after["security"]["cors"]["allowed_origins"]
        assert "http://10.1.0.164:7274" in cors_origins, \
            "CORS should include new LAN IP"

        # Verify features updated
        assert config_after["features"]["api_keys_required"] is True

    def test_lan_to_localhost_conversion(self, client, fresh_config_file):
        """
        Verify LAN -> Localhost conversion cleans up network config.

        Scenario: User had LAN mode, now converting back to localhost.

        Expected Changes:
        - config["services"]["api"]["host"]: 10.1.0.164 -> 127.0.0.1
        - config["installation"]["mode"]: "lan" -> "localhost"
        - Server section REMOVED
        - CORS origins cleaned up (only localhost)
        - API key auth disabled
        """
        # Step 1: Set up LAN mode
        lan_payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "192.168.1.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
                "adapter_name": "WiFi",
                "adapter_id": "wlan0",
            }
        }

        client.post("/api/setup/complete", json=lan_payload)

        # Verify LAN mode active
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config_before = yaml.safe_load(f)

        assert config_before["services"]["api"]["host"] == "192.168.1.100"
        assert "server" in config_before

        # Step 2: Convert to localhost
        localhost_payload = {
            "tools_attached": [],
            "network_mode": "localhost",
            "serena_enabled": False,
        }

        response = client.post("/api/setup/complete", json=localhost_payload)
        assert response.status_code in [200, 201]

        # Read final config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config_after = yaml.safe_load(f)

        # Verify API host changed back to localhost
        assert config_after["services"]["api"]["host"] == "127.0.0.1", \
            "Should revert to localhost binding"

        # Verify mode changed
        assert config_after["installation"]["mode"] == "localhost"

        # CRITICAL: Verify server section REMOVED
        assert "server" not in config_after, \
            "Localhost conversion should remove server section"

        # Verify CORS origins cleaned up
        cors_origins = config_after["security"]["cors"]["allowed_origins"]
        assert "http://127.0.0.1:7274" in cors_origins
        assert "http://localhost:7274" in cors_origins

        # Should NOT have LAN IPs anymore
        for origin in cors_origins:
            assert not origin.startswith("http://192.168."), \
                "Should remove LAN IPs from CORS"

        # Verify features disabled
        assert config_after["features"]["api_keys_required"] is False


class TestInvalidIPHandling:
    """Test 4: Invalid IP Address Handling"""

    def test_lan_mode_with_empty_ip(self, client, fresh_config_file):
        """
        Verify wizard validates empty IP address.

        Expected: Should raise validation error (400/422) or fall back gracefully.
        """
        payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "",  # Empty IP
                "firewall_configured": False,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
            }
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should either reject (400/422) or handle gracefully
        # Implementation choice - either is acceptable
        if response.status_code in [200, 201]:
            # If accepted, verify fallback behavior
            with open(fresh_config_file, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)

            # Should fall back to 0.0.0.0 or reject
            api_host = config["services"]["api"]["host"]
            assert api_host in ["0.0.0.0", "127.0.0.1"], \
                f"Invalid IP should fall back to safe default, got: {api_host}"
        else:
            # Validation error is also acceptable
            assert response.status_code in [400, 422], \
                "Should reject empty IP with validation error"

    def test_lan_mode_with_invalid_ip_format(self, client, fresh_config_file):
        """
        Verify wizard validates IP address format.

        Expected: Should reject malformed IPs.
        """
        invalid_ips = [
            "999.999.999.999",  # Out of range
            "not.an.ip.address",  # Invalid format
            "192.168.1",  # Incomplete
            "192.168.1.1.1",  # Too many octets
        ]

        for invalid_ip in invalid_ips:
            payload = {
                "tools_attached": [],
                "network_mode": "lan",
                "serena_enabled": False,
                "lan_config": {
                    "server_ip": invalid_ip,
                    "firewall_configured": False,
                    "admin_username": "admin",
                    "admin_password": "password",
                    "hostname": "giljo.local",
                }
            }

            response = client.post("/api/setup/complete", json=payload)

            # Should reject invalid IP
            assert response.status_code in [400, 422], \
                f"Should reject invalid IP: {invalid_ip}"

    def test_lan_mode_with_loopback_ip(self, client, fresh_config_file):
        """
        Verify wizard rejects loopback IPs in LAN mode.

        Loopback IPs (127.x.x.x) don't make sense for LAN mode.
        """
        payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "127.0.0.1",  # Loopback in LAN mode - invalid
                "firewall_configured": False,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
            }
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should reject loopback IP in LAN mode
        assert response.status_code in [400, 422], \
            "LAN mode should reject loopback IP (use localhost mode instead)"

    def test_lan_mode_with_link_local_ip(self, client, fresh_config_file):
        """
        Verify wizard rejects link-local IPs (169.254.x.x).

        Link-local IPs indicate network configuration issues.
        """
        payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "169.254.1.1",  # Link-local IP
                "firewall_configured": False,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
            }
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should reject link-local IP
        assert response.status_code in [400, 422], \
            "Should reject link-local IP (169.254.x.x)"

    def test_lan_mode_with_none_ip(self, client, fresh_config_file):
        """
        Verify wizard handles None/null IP gracefully.
        """
        payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": None,  # None/null IP
                "firewall_configured": False,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
            }
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should reject None IP
        assert response.status_code in [400, 422], \
            "Should reject None/null IP"


class TestConfigValidation:
    """Test configuration validation after wizard completion"""

    def test_config_yaml_is_valid_after_localhost_setup(self, client, fresh_config_file):
        """Verify config.yaml is valid YAML after localhost setup"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost",
            "serena_enabled": True,
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Verify config file is valid YAML
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Should be a dictionary
        assert isinstance(config, dict)

        # Should have required top-level sections
        required_sections = ["installation", "database", "services", "security", "setup"]
        for section in required_sections:
            assert section in config, f"Missing required section: {section}"

    def test_config_yaml_is_valid_after_lan_setup(self, client, fresh_config_file):
        """Verify config.yaml is valid YAML after LAN setup"""
        payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "10.1.0.164",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
                "adapter_name": "Ethernet",
                "adapter_id": "eth0",
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Verify config file is valid YAML
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Should be a dictionary
        assert isinstance(config, dict)

        # Should have server section for LAN mode
        assert "server" in config, "LAN mode should create server section"

    def test_serena_toggle_persisted(self, client, fresh_config_file):
        """Verify Serena MCP enabled flag is persisted correctly"""
        # Test with Serena enabled
        payload_enabled = {
            "tools_attached": [],
            "network_mode": "localhost",
            "serena_enabled": True,
        }

        response = client.post("/api/setup/complete", json=payload_enabled)
        assert response.status_code in [200, 201]

        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        serena_enabled = config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts")
        assert serena_enabled is True, "Serena enabled should be persisted"

        # Test with Serena disabled
        payload_disabled = {
            "tools_attached": [],
            "network_mode": "localhost",
            "serena_enabled": False,
        }

        response = client.post("/api/setup/complete", json=payload_disabled)
        assert response.status_code in [200, 201]

        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        serena_enabled = config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts")
        assert serena_enabled is False, "Serena disabled should be persisted"


class TestDatabaseHostIsolation:
    """CRITICAL: Test that database host NEVER changes from localhost"""

    def test_database_host_unchanged_in_lan_mode(self, client, fresh_config_file):
        """
        CRITICAL: Verify database host stays 'localhost' in LAN mode.

        The database is ALWAYS accessed via localhost, even in LAN mode.
        Only the API binds to the network IP.
        """
        payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "192.168.1.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # CRITICAL: Database host must be localhost
        assert config["database"]["host"] == "localhost", \
            "Database host should NEVER change from localhost, even in LAN mode"

    def test_database_host_unchanged_after_mode_conversion(self, client, fresh_config_file):
        """
        CRITICAL: Verify database host stays 'localhost' through mode conversions.
        """
        # Start with localhost
        localhost_payload = {
            "tools_attached": [],
            "network_mode": "localhost",
            "serena_enabled": False,
        }

        client.post("/api/setup/complete", json=localhost_payload)

        # Convert to LAN
        lan_payload = {
            "tools_attached": [],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "10.1.0.50",
                "firewall_configured": False,
                "admin_username": "admin",
                "admin_password": "password",
                "hostname": "giljo.local",
            }
        }

        client.post("/api/setup/complete", json=lan_payload)

        # Convert back to localhost
        client.post("/api/setup/complete", json=localhost_payload)

        # Read final config
        with open(fresh_config_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)

        # Database host should ALWAYS be localhost
        assert config["database"]["host"] == "localhost", \
            "Database host should remain 'localhost' through all mode conversions"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
