"""
Unit tests for v3.0 configuration system.

Tests verify that DeploymentMode enum and mode-dependent logic
have been completely removed from the configuration system.
"""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from src.giljo_mcp.config_manager import ConfigManager, ServerConfig


@pytest.fixture
def skip_db_validation():
    """Fixture to skip database password validation"""
    with patch.dict(os.environ, {"DB_PASSWORD": "test-password"}):
        yield


class TestDeploymentModeRemoval:
    """Test that DeploymentMode enum and related code are removed"""

    def test_deployment_mode_enum_removed(self):
        """Verify DeploymentMode enum no longer exists"""
        import src.giljo_mcp.config_manager as cm

        assert not hasattr(cm, "DeploymentMode"), "DeploymentMode enum should be removed from config_manager"

    def test_server_config_no_mode_field(self):
        """Verify ServerConfig doesn't have mode field"""
        config = ServerConfig()
        assert not hasattr(config, "mode"), "ServerConfig should not have 'mode' field"
        assert not hasattr(config, "deployment_mode"), "ServerConfig should not have 'deployment_mode' property"

    def test_no_detect_mode_method(self, skip_db_validation):
        """Verify _detect_mode() method removed"""
        config = ConfigManager()
        assert not hasattr(config, "_detect_mode"), "_detect_mode() method should be removed"

    def test_no_apply_mode_settings_method(self, skip_db_validation):
        """Verify _apply_mode_settings() method removed"""
        config = ConfigManager()
        assert not hasattr(config, "_apply_mode_settings"), "_apply_mode_settings() method should be removed"


class TestFixedNetworkBinding:
    """Test that network binding is always 0.0.0.0"""

    def test_server_always_binds_all_interfaces(self):
        """Verify api_host always defaults to 0.0.0.0"""
        config = ServerConfig()
        assert config.api_host == "0.0.0.0", "api_host should default to 0.0.0.0"

    def test_dashboard_host_binds_all_interfaces(self):
        """Verify dashboard_host defaults to 0.0.0.0"""
        config = ServerConfig()
        assert config.dashboard_host == "0.0.0.0", "dashboard_host should default to 0.0.0.0"

    def test_mcp_host_binds_all_interfaces(self):
        """Verify mcp_host defaults to 0.0.0.0"""
        config = ServerConfig()
        assert config.mcp_host == "0.0.0.0", "mcp_host should default to 0.0.0.0"

    def test_fixed_network_binding_from_config_manager(self, skip_db_validation):
        """Verify ConfigManager creates ServerConfig with 0.0.0.0 binding"""
        config = ConfigManager()
        assert config.server.api_host == "0.0.0.0"
        assert config.server.dashboard_host == "0.0.0.0"
        assert config.server.mcp_host == "0.0.0.0"


class TestAuthenticationAlwaysEnabled:
    """Test that authentication is always enabled (no is_enabled checks)"""

    def test_authentication_always_enabled(self, skip_db_validation):
        """Verify authentication always enabled (no conditional logic)"""
        config = ConfigManager()
        # Should NOT have is_enabled method for auth
        assert not hasattr(config, "is_enabled"), "Config should not have is_enabled() method (auth always on)"

    def test_api_key_always_generated(self, skip_db_validation):
        """Verify API key field exists for network clients"""
        config = ConfigManager()
        # ServerConfig should have api_key field
        assert hasattr(config.server, "api_key"), "ServerConfig should have api_key field"


class TestConfigLoadingWithoutMode:
    """Test config loading handles missing/deprecated mode field"""

    def test_config_loads_without_mode_field(self, skip_db_validation):
        """Verify config loads when mode field is missing"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create v3.0 config without mode field
            config_data = {
                "version": "3.0.0",
                "server": {
                    "api_host": "0.0.0.0",
                    "api_port": 7272,
                    "dashboard_host": "0.0.0.0",
                    "dashboard_port": 7273,
                },
                "database": {"url": "postgresql://localhost/test_db"},
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Should load successfully
            config = ConfigManager(config_path=config_path)

            assert config.server.api_host == "0.0.0.0"
            assert config.server.api_port == 7272

    def test_config_ignores_legacy_mode_field(self, skip_db_validation):
        """Verify old mode field is ignored if present (v2.x compatibility)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Create v2.x config WITH mode field
            config_data = {
                "version": "2.0.0",
                "server": {
                    "mode": "wan",  # Old field - should be ignored
                    "api_port": 7272,
                },
                "database": {"url": "postgresql://localhost/test_db"},
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            # Capture logs to verify warning
            with patch("src.giljo_mcp.config_manager.logger") as mock_logger:
                # Should load successfully and ignore mode
                config = ConfigManager(config_path=config_path)

                # Should log migration and/or warning messages
                # Check that logger was called (migration logs info messages)
                assert mock_logger.info.called or mock_logger.warning.called

            # Mode field should not exist on loaded config
            assert not hasattr(config.server, "mode")


class TestDatabaseManagerCreation:
    """Test database manager creation without mode checks"""

    @patch("giljo_mcp.database.DatabaseManager")
    def test_database_manager_always_async(self, mock_db_manager, skip_db_validation):
        """Verify database manager creation doesn't check mode"""
        config = ConfigManager()
        config.database.database_url = "postgresql://localhost/test_db"

        # Create database manager
        db_manager = config.create_database_manager()

        # Should be called with is_async=True (always async)
        mock_db_manager.assert_called_once()
        call_kwargs = mock_db_manager.call_args[1]
        assert call_kwargs.get("is_async") is True, "DatabaseManager should always be created with is_async=True"


class TestV2ConfigMigration:
    """Test v2.x config migration to v3.0 format"""

    def test_migrate_v2_local_mode_config(self, skip_db_validation):
        """Test migration from v2.x local mode config"""
        config = ConfigManager()

        v2_data = {
            "version": "2.0.0",
            "server": {
                "mode": "local",
                "api_port": 7272,
            },
            "database": {"url": "postgresql://localhost/test_db"},
        }

        migrated = config._migrate_v2_config(v2_data)

        # Version updated
        assert migrated["version"] == "3.0.0"

        # Mode field removed
        assert "mode" not in migrated["server"]

        # Deployment context preserved (informational)
        assert migrated["deployment_context"] == "local"

        # Network binding set to 0.0.0.0 (nested structure)
        assert migrated["server"]["api"]["host"] == "0.0.0.0"
        assert migrated["server"]["dashboard"]["host"] == "0.0.0.0"
        assert migrated["server"]["mcp"]["host"] == "0.0.0.0"

        # Features added
        assert migrated["features"]["authentication"] is True
        assert migrated["features"]["auto_login_localhost"] is True
        assert migrated["features"]["firewall_configured"] is False

    def test_migrate_v2_lan_mode_config(self, skip_db_validation):
        """Test migration from v2.x LAN mode config"""
        config = ConfigManager()

        v2_data = {
            "version": "2.0.0",
            "server": {
                "mode": "lan",
                "api_port": 7272,
            },
            "database": {"url": "postgresql://localhost/test_db"},
        }

        migrated = config._migrate_v2_config(v2_data)

        assert migrated["version"] == "3.0.0"
        assert migrated["deployment_context"] == "lan"
        assert "mode" not in migrated["server"]

    def test_migrate_v2_wan_mode_config(self, skip_db_validation):
        """Test migration from v2.x WAN mode config"""
        config = ConfigManager()

        v2_data = {
            "version": "2.0.0",
            "server": {
                "mode": "wan",
                "api_port": 7272,
                "api_key": "existing-key-123",
            },
            "database": {"url": "postgresql://localhost/test_db"},
        }

        migrated = config._migrate_v2_config(v2_data)

        assert migrated["version"] == "3.0.0"
        assert migrated["deployment_context"] == "wan"
        assert "mode" not in migrated["server"]

        # API key preserved
        assert migrated["server"]["api_key"] == "existing-key-123"

    def test_migrate_skips_v3_config(self, skip_db_validation):
        """Test that v3.0 config is not re-migrated"""
        config = ConfigManager()

        v3_data = {
            "version": "3.0.0",
            "server": {
                "api_host": "0.0.0.0",
            },
            "database": {"url": "postgresql://localhost/test_db"},
        }

        original_data = v3_data.copy()
        migrated = config._migrate_v2_config(v3_data)

        # Should return unchanged
        assert migrated == original_data

    def test_migration_logs_info(self, skip_db_validation):
        """Test that migration logs informational messages"""
        config = ConfigManager()

        v2_data = {
            "version": "2.0.0",
            "server": {"mode": "local"},
            "database": {"url": "postgresql://localhost/test_db"},
        }

        with patch("src.giljo_mcp.config_manager.logger") as mock_logger:
            config._migrate_v2_config(v2_data)

            # Should log migration start and completion
            assert mock_logger.info.call_count >= 2

            # Check for migration messages
            info_calls = [call[0][0] for call in mock_logger.info.call_args_list]
            assert any("migrat" in msg.lower() for msg in info_calls)


class TestEnvironmentVariables:
    """Test that environment variable loading no longer sets mode"""

    def test_env_loading_ignores_mode_var(self, skip_db_validation):
        """Verify GILJO_MCP_MODE env var is ignored"""
        with patch.dict("os.environ", {"GILJO_MCP_MODE": "wan", "DB_PASSWORD": "test"}):
            config = ConfigManager()
            config._load_from_env()

            # Should not have mode field
            assert not hasattr(config.server, "mode")

    def test_env_loading_accepts_api_host(self, skip_db_validation):
        """Verify GILJO_API_HOST env var still works"""
        with patch.dict("os.environ", {"GILJO_API_HOST": "192.168.1.100", "DB_PASSWORD": "test"}):
            config = ConfigManager()
            config._load_from_env()

            # Should accept custom api_host (for testing purposes)
            assert config.server.api_host == "192.168.1.100"


class TestConfigValidation:
    """Test config validation without mode checks"""

    def test_validation_no_longer_checks_wan_mode(self, skip_db_validation):
        """Verify validation doesn't check for WAN mode + API key"""
        config = ConfigManager()
        config.database.url = "postgresql://localhost/test_db"
        config.server.api_key = None  # No API key

        # Should not raise error (mode check removed)
        # validate() will check other things but not mode
        try:
            config.validate()
        except Exception as e:
            # If it raises, should NOT be about mode or API key
            error_msg = str(e).lower()
            assert "mode" not in error_msg
            assert "wan" not in error_msg or "api key" not in error_msg


class TestIntegration:
    """Integration tests for full config loading workflow"""

    def test_full_config_load_from_v3_file(self, skip_db_validation):
        """Test complete config loading from v3.0 file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            config_data = {
                "version": "3.0.0",
                "server": {
                    "api": {
                        "host": "0.0.0.0",
                        "port": 7272,
                    },
                    "dashboard": {
                        "host": "0.0.0.0",
                        "port": 7273,
                    },
                    "mcp": {
                        "host": "0.0.0.0",
                        "port": 6001,
                    },
                    "api_key": "test-key-123",
                },
                "database": {
                    "type": "postgresql",
                    "postgresql": {
                        "host": "localhost",
                        "database": "test_db",
                        "user": "postgres",
                        "password": "test-password",
                        "pool_size": 10,
                    },
                },
                "features": {
                    "authentication": True,
                    "auto_login_localhost": True,
                    "firewall_configured": False,
                },
                "deployment_context": "localhost",
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            config = ConfigManager(config_path=config_path)

            # Verify all settings loaded correctly
            assert config.server.api_host == "0.0.0.0"
            assert config.server.api_port == 7272
            assert config.server.dashboard_host == "0.0.0.0"
            assert config.server.dashboard_port == 7273
            assert config.server.mcp_host == "0.0.0.0"
            assert config.server.mcp_port == 6001
            assert config.server.api_key == "test-key-123"
            assert config.database.type == "postgresql"
            assert config.database.database_name == "test_db"
            assert config.database.pg_pool_size == 10

    def test_full_config_load_from_v2_file_with_migration(self, skip_db_validation):
        """Test complete config loading from v2.x file with auto-migration"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Write v2.x config
            config_data = {
                "version": "2.0.0",
                "server": {
                    "mode": "lan",  # Old field
                    "api_port": 7272,
                },
                "database": {"url": "postgresql://localhost/test_db"},
            }

            with open(config_path, "w") as f:
                yaml.dump(config_data, f)

            config = ConfigManager(config_path=config_path)

            # Should be migrated
            assert not hasattr(config.server, "mode")
            assert config.server.api_host == "0.0.0.0"
            assert config.server.dashboard_host == "0.0.0.0"
            assert config.server.mcp_host == "0.0.0.0"
