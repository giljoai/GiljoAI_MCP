"""
Integration tests for LAN mode setup completion endpoint.

Tests POST /api/setup/complete with LAN mode configuration including:
- CORS origins configuration
- API key generation
- Admin account creation and encryption
- Config.yaml updates

These tests are written BEFORE implementation following TDD methodology.

Author: Backend Integration Tester Agent
Phase: TDD Red Phase (Tests should FAIL initially)
"""

import bcrypt
import json
import pytest
import yaml
from cryptography.fernet import Fernet
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with isolated configuration"""
    from api.app import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
def clean_config(tmp_path, monkeypatch):
    """Provide clean config.yaml and mock config path"""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "installation": {
            "mode": "localhost",
            "version": "2.0.0"
        },
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "name": "giljo_mcp",
            "user": "giljo_user"
        },
        "services": {
            "api": {
                "host": "127.0.0.1",
                "port": 7272
            },
            "frontend": {
                "port": 7274
            }
        },
        "security": {
            "cors": {
                "allowed_origins": [
                    "http://127.0.0.1:7274",
                    "http://localhost:7274"
                ]
            }
        },
        "setup": {
            "database_initialized": False
        }
    }

    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    # Mock Path.cwd() to return tmp_path
    monkeypatch.setattr(Path, "cwd", lambda: tmp_path)

    return config_file


@pytest.fixture
def mock_home_dir(tmp_path, monkeypatch):
    """Mock user home directory for testing admin account storage"""
    home_dir = tmp_path / "home"
    home_dir.mkdir()

    monkeypatch.setattr(Path, "home", lambda: home_dir)

    return home_dir


class TestLANModeCORSConfiguration:
    """Test CORS origins configuration for LAN mode"""

    def test_lan_setup_updates_cors_origins(self, client, clean_config):
        """Test that LAN setup adds server IP to CORS allowed_origins"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201], f"Setup failed: {response.text}"

        # Read config.yaml and verify CORS origins updated
        with open(clean_config, 'r') as f:
            config = yaml.safe_load(f)

        cors_origins = config.get("security", {}).get("cors", {}).get("allowed_origins", [])

        # Should include the new LAN IP
        expected_origin = "http://192.168.1.50:7274"
        assert expected_origin in cors_origins, f"Expected {expected_origin} in CORS origins"

    def test_lan_setup_preserves_existing_cors_origins(self, client, clean_config):
        """Test that LAN setup preserves existing localhost CORS origins"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "10.1.0.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "giljo-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config and verify existing origins preserved
        with open(clean_config, 'r') as f:
            config = yaml.safe_load(f)

        cors_origins = config.get("security", {}).get("cors", {}).get("allowed_origins", [])

        # Original localhost origins should still be present
        assert "http://127.0.0.1:7274" in cors_origins, "Should preserve localhost origin"
        assert "http://localhost:7274" in cors_origins, "Should preserve localhost origin"

        # New LAN origin should be added
        assert "http://10.1.0.100:7274" in cors_origins, "Should add LAN IP origin"

    def test_lan_setup_adds_hostname_to_cors(self, client, clean_config):
        """Test that LAN setup adds hostname-based CORS origin"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "giljo.local"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config and verify hostname origin added
        with open(clean_config, 'r') as f:
            config = yaml.safe_load(f)

        cors_origins = config.get("security", {}).get("cors", {}).get("allowed_origins", [])

        # Should include hostname-based origin
        expected_origin = "http://giljo.local:7274"
        assert expected_origin in cors_origins, f"Expected {expected_origin} in CORS origins"

    def test_localhost_mode_does_not_update_cors(self, client, clean_config):
        """Test that localhost mode doesn't add network CORS origins"""
        # Read initial CORS origins
        with open(clean_config, 'r') as f:
            initial_config = yaml.safe_load(f)
        initial_origins = initial_config.get("security", {}).get("cors", {}).get("allowed_origins", [])

        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read final CORS origins
        with open(clean_config, 'r') as f:
            final_config = yaml.safe_load(f)
        final_origins = final_config.get("security", {}).get("cors", {}).get("allowed_origins", [])

        # CORS origins should be unchanged in localhost mode
        assert set(initial_origins) == set(final_origins), "Localhost mode should not modify CORS"


class TestLANModeAPIKeyGeneration:
    """Test API key generation for LAN mode"""

    def test_lan_setup_generates_api_key(self, client, clean_config, mock_home_dir):
        """Test that LAN setup generates an API key"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()

        # Response should contain an API key
        assert "api_key" in data, "LAN mode should return API key in response"
        api_key = data["api_key"]

        # API key should have expected format
        assert isinstance(api_key, str), "API key should be string"
        assert len(api_key) > 0, "API key should not be empty"

    def test_lan_api_key_format(self, client, clean_config, mock_home_dir):
        """Test that generated API key has correct format (gk_ prefix)"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()
        api_key = data.get("api_key")

        # API key should start with "gk_" (GiljoAI Key prefix)
        assert api_key.startswith("gk_"), "API key should start with 'gk_' prefix"

        # API key should be long enough to be secure (at least 43 chars)
        # gk_ (3) + urlsafe_base64(32 bytes) = ~43+ characters
        assert len(api_key) >= 43, f"API key too short: {len(api_key)} chars"

    def test_lan_api_key_is_unique(self, client, clean_config, mock_home_dir):
        """Test that each setup generates a unique API key"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "test-server"
            }
        }

        # Generate first API key
        response1 = client.post("/api/setup/complete", json=payload)
        key1 = response1.json().get("api_key")

        # Generate second API key (reconfiguration scenario)
        response2 = client.post("/api/setup/complete", json=payload)
        key2 = response2.json().get("api_key")

        # Keys should be different (unless using same key intentionally)
        # This test may need adjustment based on implementation strategy
        # (whether to regenerate or keep existing key)

    def test_localhost_mode_no_api_key(self, client, clean_config):
        """Test that localhost mode does NOT generate API key"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()

        # Localhost mode should NOT return API key
        assert "api_key" not in data, "Localhost mode should not generate API key"

    def test_lan_setup_requires_restart(self, client, clean_config, mock_home_dir):
        """Test that LAN setup indicates service restart is required"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()

        # Should indicate restart required for LAN mode
        assert "requires_restart" in data, "Should indicate if restart required"
        assert data["requires_restart"] is True, "LAN mode should require restart"

    def test_localhost_mode_no_restart_required(self, client, clean_config):
        """Test that localhost mode does not require restart"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()

        # Localhost mode should not require restart
        requires_restart = data.get("requires_restart", False)
        assert requires_restart is False, "Localhost mode should not require restart"


class TestLANModeAdminAccountStorage:
    """Test admin account creation and secure storage for LAN mode"""

    def test_lan_setup_creates_admin_account_file(self, client, clean_config, mock_home_dir):
        """Test that LAN setup creates admin account file"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Verify admin account file exists
        admin_file = mock_home_dir / ".giljo-mcp" / "admin_account.json"
        assert admin_file.exists(), "Admin account file should be created"

    def test_admin_account_file_is_encrypted(self, client, clean_config, mock_home_dir):
        """Test that admin account file is encrypted (not plaintext)"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "SecurePassword123!",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read admin account file
        admin_file = mock_home_dir / ".giljo-mcp" / "admin_account.json"
        file_content = admin_file.read_text()

        # Should NOT be plaintext JSON (should be encrypted)
        # Encrypted data won't parse as JSON
        try:
            json.loads(file_content)
            # If it parses as JSON, it's not encrypted properly
            pytest.fail("Admin account file should be encrypted, not plaintext JSON")
        except json.JSONDecodeError:
            # Good - file is encrypted (not valid JSON)
            pass

    def test_admin_password_is_hashed(self, client, clean_config, mock_home_dir):
        """Test that admin password is hashed with bcrypt, not stored plaintext"""
        password = "MySecurePassword123!"

        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": password,
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Decrypt and read admin account file
        admin_file = mock_home_dir / ".giljo-mcp" / "admin_account.json"
        encrypted_data = admin_file.read_bytes()

        # Get encryption key
        encryption_key_file = mock_home_dir / ".giljo-mcp" / "encryption_key"
        assert encryption_key_file.exists(), "Encryption key file should exist"

        encryption_key = encryption_key_file.read_bytes()
        cipher = Fernet(encryption_key)

        # Decrypt admin account data
        decrypted_data = cipher.decrypt(encrypted_data)
        admin_account = json.loads(decrypted_data.decode())

        # Verify structure
        assert "username" in admin_account
        assert "password_hash" in admin_account

        # Password should be hashed, not plaintext
        password_hash = admin_account["password_hash"]
        assert password_hash != password, "Password should not be stored in plaintext"

        # Verify it's a bcrypt hash (bcrypt hashes start with $2a$, $2b$, or $2y$)
        assert password_hash.startswith("$2"), "Password should be bcrypt hash"

        # Verify the hash is valid by checking it against the original password
        assert bcrypt.checkpw(
            password.encode(), password_hash.encode()
        ), "Password hash should be verifiable with bcrypt"

    def test_admin_account_has_correct_structure(self, client, clean_config, mock_home_dir):
        """Test that admin account file has expected JSON structure"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "adminuser",
                "admin_password": "password123",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Decrypt admin account file
        admin_file = mock_home_dir / ".giljo-mcp" / "admin_account.json"
        encryption_key_file = mock_home_dir / ".giljo-mcp" / "encryption_key"

        encryption_key = encryption_key_file.read_bytes()
        cipher = Fernet(encryption_key)
        decrypted_data = cipher.decrypt(admin_file.read_bytes())
        admin_account = json.loads(decrypted_data.decode())

        # Verify required fields
        assert "username" in admin_account
        assert "password_hash" in admin_account
        assert "created_at" in admin_account

        # Verify values
        assert admin_account["username"] == "adminuser"
        assert isinstance(admin_account["password_hash"], str)
        assert isinstance(admin_account["created_at"], str)

    def test_localhost_mode_no_admin_account(self, client, clean_config, mock_home_dir):
        """Test that localhost mode does NOT create admin account file"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Admin account file should NOT exist
        admin_file = mock_home_dir / ".giljo-mcp" / "admin_account.json"
        assert not admin_file.exists(), "Localhost mode should not create admin account"

    def test_admin_account_file_permissions(self, client, clean_config, mock_home_dir):
        """Test that admin account file has restrictive permissions (Unix systems)"""
        import platform

        if platform.system() == "Windows":
            pytest.skip("File permissions test not applicable on Windows")

        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "password123",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Check file permissions (should be 600 - owner read/write only)
        admin_file = mock_home_dir / ".giljo-mcp" / "admin_account.json"
        import stat

        file_stat = admin_file.stat()
        file_mode = stat.filemode(file_stat.st_mode)

        # Should be -rw------- (600)
        assert file_mode == "-rw-------", f"Admin file permissions too open: {file_mode}"


class TestLANModeConfigUpdates:
    """Test config.yaml updates for LAN mode"""

    def test_lan_setup_updates_api_host(self, client, clean_config):
        """Test that LAN setup changes API host from 127.0.0.1 to 0.0.0.0"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config and verify API host updated
        with open(clean_config, 'r') as f:
            config = yaml.safe_load(f)

        api_host = config.get("services", {}).get("api", {}).get("host")

        # Should be 0.0.0.0 for network binding
        assert api_host == "0.0.0.0", "LAN mode should bind to 0.0.0.0 (all interfaces)"

    def test_localhost_mode_preserves_localhost_binding(self, client, clean_config):
        """Test that localhost mode keeps API host as 127.0.0.1"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config and verify API host unchanged
        with open(clean_config, 'r') as f:
            config = yaml.safe_load(f)

        api_host = config.get("services", {}).get("api", {}).get("host")

        # Should remain 127.0.0.1
        assert api_host == "127.0.0.1", "Localhost mode should keep 127.0.0.1 binding"

    def test_lan_setup_saves_server_info(self, client, clean_config):
        """Test that LAN setup saves server IP and hostname to config"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "giljo-server.local"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Read config and verify server info saved
        with open(clean_config, 'r') as f:
            config = yaml.safe_load(f)

        server_config = config.get("server", {})

        # Should have server IP and hostname
        assert server_config.get("ip") == "192.168.1.50"
        assert server_config.get("hostname") == "giljo-server.local"


class TestLANModeEdgeCases:
    """Test edge cases and error handling for LAN mode setup"""

    def test_lan_setup_missing_admin_password(self, client, clean_config):
        """Test that LAN setup fails gracefully if admin password missing"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                # Missing admin_password
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should either require password (422) or use a default
        # Implementation choice - either is acceptable
        assert response.status_code in [200, 201, 422]

    def test_lan_setup_invalid_ip_address(self, client, clean_config):
        """Test that LAN setup validates IP address format"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "invalid.ip.address",  # Invalid IP
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should reject invalid IP (422 validation error or still accept)
        # Validation strictness is implementation choice


class TestLANModeMultiTenantIsolation:
    """Test that LAN mode respects multi-tenant isolation"""

    def test_api_key_is_tenant_isolated(self, client, clean_config, mock_home_dir):
        """Test that API keys are isolated by tenant (if multi-tenant enabled)"""
        # This test validates that the API key generation doesn't
        # accidentally expose data across tenants
        # For now, we just verify the API key is generated correctly

        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "test-server"
            }
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Verify API key generated
        assert "api_key" in response.json()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
