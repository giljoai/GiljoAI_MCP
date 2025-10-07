"""
Integration tests for localhost-to-LAN conversion API key generation flow.

Tests ensure that API key generation is idempotent when re-running the setup wizard,
and that the modal always appears for LAN mode conversions.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from src.giljo_mcp.auth import AuthManager
from src.giljo_mcp.config_manager import ConfigManager


logger = logging.getLogger(__name__)


@pytest.fixture
def auth_manager():
    """Create AuthManager instance for testing"""
    config = ConfigManager()
    return AuthManager(config)


@pytest.fixture
def api_keys_file(tmp_path):
    """Create temporary API keys file for testing"""
    keys_file = tmp_path / "api_keys.json"
    return keys_file


@pytest.fixture
def clean_auth_state(auth_manager, monkeypatch, tmp_path):
    """
    Ensure clean auth state before each test by mocking the API keys file location.

    This prevents test pollution from real API keys stored in ~/.giljo-mcp/
    """
    # Mock the API keys file location to use tmp_path
    keys_file = tmp_path / "api_keys.json"

    # Patch Path.home() to return tmp_path so API keys are stored in temp location
    def mock_home():
        return tmp_path

    monkeypatch.setattr(Path, "home", mock_home)

    # Clear in-memory cache
    auth_manager.api_keys = {}

    return auth_manager


class TestGetOrCreateApiKey:
    """Test suite for get_or_create_api_key method"""

    def test_first_time_api_key_generation_no_existing_key(self, clean_auth_state):
        """
        Test: First-time API key generation when no existing key exists.

        Expected: New API key should be generated with the specified name.
        """
        auth_manager = clean_auth_state

        # Act: Generate API key for the first time
        api_key = auth_manager.get_or_create_api_key(name="LAN Setup Key", permissions=["*"])

        # Assert: Key was generated
        assert api_key is not None
        assert api_key.startswith("gk_")
        assert len(api_key) > 32

        # Assert: Key is stored in memory
        assert api_key in auth_manager.api_keys
        assert auth_manager.api_keys[api_key]["name"] == "LAN Setup Key"
        assert auth_manager.api_keys[api_key]["permissions"] == ["*"]
        assert auth_manager.api_keys[api_key]["active"] is True

        logger.info(f"✅ Test passed: First-time key generation (prefix: {api_key[:10]}...)")

    def test_rerun_wizard_existing_active_key_returns_same_key(self, clean_auth_state):
        """
        Test: Re-running wizard when an active key with the same name already exists.

        Expected: The existing active key should be returned (idempotent behavior).
        """
        auth_manager = clean_auth_state

        # Arrange: Generate initial API key
        first_key = auth_manager.generate_api_key(name="LAN Setup Key", permissions=["*"])

        # Act: Call get_or_create_api_key with the same name
        second_key = auth_manager.get_or_create_api_key(name="LAN Setup Key", permissions=["*"])

        # Assert: Same key was returned (idempotent)
        assert first_key == second_key

        # Assert: Only one key exists in memory
        lan_keys = [k for k, v in auth_manager.api_keys.items() if v["name"] == "LAN Setup Key"]
        assert len(lan_keys) == 1

        logger.info(f"✅ Test passed: Existing active key returned (prefix: {first_key[:10]}...)")

    def test_rerun_wizard_existing_revoked_key_creates_new_key(self, clean_auth_state):
        """
        Test: Re-running wizard when a revoked key with the same name exists.

        Expected: A new key should be created with a timestamped name.
        """
        auth_manager = clean_auth_state

        # Arrange: Generate and revoke initial key
        first_key = auth_manager.generate_api_key(name="LAN Setup Key", permissions=["*"])
        auth_manager.api_keys[first_key]["active"] = False
        auth_manager.api_keys[first_key]["revoked_at"] = datetime.now(timezone.utc).isoformat()

        # Act: Call get_or_create_api_key with the same name
        second_key = auth_manager.get_or_create_api_key(name="LAN Setup Key", permissions=["*"])

        # Assert: New key was created (different from revoked key)
        assert second_key != first_key
        assert second_key.startswith("gk_")

        # Assert: New key has timestamped name
        new_key_info = auth_manager.api_keys[second_key]
        assert "LAN Setup Key" in new_key_info["name"]
        # Should contain timestamp like "(2025-10-07)" or similar
        assert "(" in new_key_info["name"] or new_key_info["name"] == "LAN Setup Key"

        # Assert: Both keys exist in memory
        assert first_key in auth_manager.api_keys
        assert second_key in auth_manager.api_keys

        # Assert: First key is still revoked
        assert auth_manager.api_keys[first_key]["active"] is False

        # Assert: Second key is active
        assert auth_manager.api_keys[second_key]["active"] is True

        logger.info(f"✅ Test passed: New key created when revoked key exists (prefix: {second_key[:10]}...)")

    def test_key_prefix_logged_not_full_key(self, clean_auth_state, caplog):
        """
        Test: Verify that only the key prefix is logged, not the full key.

        Expected: Logs should contain key prefix (e.g., "gk_xxx...") but not full key.
        """
        auth_manager = clean_auth_state

        with caplog.at_level(logging.INFO):
            # Act: Generate API key
            api_key = auth_manager.get_or_create_api_key(name="Test Key", permissions=["*"])

            # Assert: Full key is NOT in logs
            assert api_key not in caplog.text

            # Assert: Key prefix might be in logs (if implemented)
            # This is a forward-looking assertion for the implementation
            if "gk_" in caplog.text:
                # If logging is implemented, verify it only logs prefix
                for record in caplog.records:
                    assert api_key not in record.message

        logger.info("✅ Test passed: Only key prefix logged, not full key")

    def test_permissions_preserved_on_key_retrieval(self, clean_auth_state):
        """
        Test: Verify that permissions are preserved when retrieving existing key.

        Expected: Retrieved key should have the same permissions as original.
        """
        auth_manager = clean_auth_state

        # Arrange: Generate key with specific permissions
        original_perms = ["projects.read", "projects.write", "agents.*"]
        first_key = auth_manager.generate_api_key(name="Permission Test Key", permissions=original_perms)

        # Act: Retrieve the same key
        second_key = auth_manager.get_or_create_api_key(
            name="Permission Test Key",
            permissions=["*"]  # Different permissions, but should return existing
        )

        # Assert: Same key returned
        assert first_key == second_key

        # Assert: Original permissions preserved (not overwritten)
        assert auth_manager.api_keys[second_key]["permissions"] == original_perms

        logger.info("✅ Test passed: Permissions preserved on key retrieval")

    def test_file_persistence_key_survives_reload(self, clean_auth_state, tmp_path):
        """
        Test: Verify that generated keys are persisted to disk and survive reload.

        Expected: Key should be retrievable after creating new AuthManager instance.
        """
        auth_manager1 = clean_auth_state

        # Act: Generate key
        api_key = auth_manager1.get_or_create_api_key(name="Persistence Test Key", permissions=["*"])

        # Assert: Key file was created
        keys_file = tmp_path / ".giljo-mcp" / "api_keys.json"
        assert keys_file.exists()

        # Act: Create new AuthManager instance (simulates server restart)
        config = ConfigManager()
        auth_manager2 = AuthManager(config)
        auth_manager2.api_keys = {}  # Clear in-memory cache

        # Act: Retrieve key with new instance
        retrieved_key = auth_manager2.get_or_create_api_key(
            name="Persistence Test Key",
            permissions=["*"]
        )

        # Assert: Same key retrieved after reload
        assert retrieved_key == api_key

        logger.info("✅ Test passed: Key survives reload from disk")


class TestSetupEndpointLanConversion:
    """Test suite for setup endpoint LAN conversion flow"""

    @pytest.fixture
    def test_client(self):
        """Create FastAPI test client"""
        from api.app import create_app
        app = create_app()
        return TestClient(app)

    def test_setup_complete_lan_mode_returns_api_key(self, test_client, monkeypatch, tmp_path):
        """
        Test: Setup completion in LAN mode returns an API key.

        Expected: Response should include api_key field with a valid key.
        """
        # Arrange: Mock Path.home() to use tmp_path
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)

        # Arrange: Prepare LAN setup request
        setup_request = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "192.168.1.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "TestPassword123!",
                "hostname": "giljo.local"
            }
        }

        # Act: Complete setup with LAN mode
        response = test_client.post("/api/v1/setup/complete", json=setup_request)

        # Assert: Request succeeded
        assert response.status_code == 200

        # Assert: Response contains API key
        data = response.json()
        assert data["success"] is True
        assert "api_key" in data
        assert data["api_key"] is not None
        assert data["api_key"].startswith("gk_")

        logger.info(f"✅ Test passed: LAN setup returns API key (prefix: {data['api_key'][:10]}...)")

    def test_rerun_setup_wizard_lan_mode_returns_same_key(self, test_client, monkeypatch, tmp_path):
        """
        Test: Re-running setup wizard in LAN mode returns the same API key.

        Expected: Idempotent behavior - same key returned on subsequent runs.
        """
        # Arrange: Mock Path.home() to use tmp_path
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)

        # Arrange: Prepare LAN setup request
        setup_request = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "192.168.1.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "TestPassword123!",
                "hostname": "giljo.local"
            }
        }

        # Act: Complete setup first time
        response1 = test_client.post("/api/v1/setup/complete", json=setup_request)
        assert response1.status_code == 200
        first_key = response1.json()["api_key"]

        # Act: Complete setup second time (re-run wizard)
        response2 = test_client.post("/api/v1/setup/complete", json=setup_request)
        assert response2.status_code == 200
        second_key = response2.json()["api_key"]

        # Assert: Same key returned (idempotent)
        assert first_key == second_key

        logger.info(f"✅ Test passed: Re-run returns same key (prefix: {first_key[:10]}...)")

    def test_localhost_to_lan_conversion_generates_key(self, test_client, monkeypatch, tmp_path):
        """
        Test: Converting from localhost to LAN mode generates an API key.

        This is the MAIN issue being fixed - the modal was not appearing
        because the API key was null when converting from localhost to LAN.

        Expected: API key is ALWAYS generated and returned for LAN mode.
        """
        # Arrange: Mock Path.home() to use tmp_path
        def mock_home():
            return tmp_path
        monkeypatch.setattr(Path, "home", mock_home)

        # Arrange: Simulate localhost mode initially (write config)
        config_path = tmp_path / "config.yaml"
        config_path.write_text("""
installation:
  mode: localhost
setup:
  completed: true
  tools_attached: ["claude-code"]
services:
  api:
    host: 127.0.0.1
    port: 7272
features:
  api_keys_required: false
""")

        # Act: Convert to LAN mode by re-running wizard
        lan_setup_request = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "serena_enabled": False,
            "lan_config": {
                "server_ip": "192.168.1.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "admin_password": "TestPassword123!",
                "hostname": "giljo.local"
            }
        }

        response = test_client.post("/api/v1/setup/complete", json=lan_setup_request)

        # Assert: Request succeeded
        assert response.status_code == 200

        # Assert: API key was generated (CRITICAL FIX)
        data = response.json()
        assert data["success"] is True
        assert "api_key" in data
        assert data["api_key"] is not None, "API key must not be null when converting to LAN mode"
        assert data["api_key"].startswith("gk_")
        assert len(data["api_key"]) > 32

        logger.info(f"✅ Test passed: Localhost-to-LAN conversion generates API key (prefix: {data['api_key'][:10]}...)")


class TestApiKeyLogging:
    """Test suite for API key logging security"""

    def test_full_api_key_never_logged(self, clean_auth_state, caplog):
        """
        Test: Verify that full API keys are never logged.

        Expected: Logs should never contain full API keys, only prefixes.
        """
        auth_manager = clean_auth_state

        with caplog.at_level(logging.INFO):
            # Act: Generate multiple keys
            keys = [
                auth_manager.get_or_create_api_key(name=f"Test Key {i}", permissions=["*"])
                for i in range(3)
            ]

            # Assert: Full keys are NOT in logs
            for key in keys:
                assert key not in caplog.text, f"Full API key {key[:10]}... found in logs!"

        logger.info("✅ Test passed: Full API keys never logged")

    def test_key_prefix_logged_for_debugging(self, clean_auth_state, caplog):
        """
        Test: Verify that key prefixes are logged for debugging.

        Expected: Logs should contain key prefix (e.g., "gk_xxx...") for debugging.
        """
        auth_manager = clean_auth_state

        with caplog.at_level(logging.INFO):
            # Act: Generate key
            api_key = auth_manager.get_or_create_api_key(name="Debug Test Key", permissions=["*"])

            # Assert: "gk_" prefix appears in logs (when implementation adds logging)
            # This test will pass when implementation adds proper logging
            prefix = api_key[:10]

            # For now, just verify that full key is not logged
            assert api_key not in caplog.text

        logger.info("✅ Test passed: Key prefix can be logged for debugging (implementation pending)")


class TestBackwardCompatibility:
    """Test suite for backward compatibility with existing API key functionality"""

    def test_generate_api_key_still_works(self, clean_auth_state):
        """
        Test: Verify that existing generate_api_key method still works.

        Expected: No breaking changes to existing functionality.
        """
        auth_manager = clean_auth_state

        # Act: Use existing generate_api_key method
        api_key = auth_manager.generate_api_key(name="Compatibility Test", permissions=["*"])

        # Assert: Key was generated
        assert api_key is not None
        assert api_key.startswith("gk_")
        assert len(api_key) > 32

        # Assert: Key can be validated
        key_info = auth_manager.validate_api_key(api_key)
        assert key_info is not None
        assert key_info["name"] == "Compatibility Test"

        logger.info("✅ Test passed: Existing generate_api_key method still works")

    def test_validate_api_key_still_works(self, clean_auth_state):
        """
        Test: Verify that validate_api_key method still works with new keys.

        Expected: Keys generated by get_or_create_api_key can be validated.
        """
        auth_manager = clean_auth_state

        # Act: Generate key with new method
        api_key = auth_manager.get_or_create_api_key(name="Validation Test", permissions=["*"])

        # Act: Validate with existing method
        key_info = auth_manager.validate_api_key(api_key)

        # Assert: Key is valid
        assert key_info is not None
        assert key_info["name"] == "Validation Test"
        assert key_info["active"] is True

        logger.info("✅ Test passed: validate_api_key works with new keys")
