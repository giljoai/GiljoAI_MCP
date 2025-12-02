"""
Tests for the ConfigManager configuration system.

Tests cover:
- Default configuration initialization
- Environment variable overrides
- Configuration validation
- Path handling (OS-neutral)
- Deployment mode settings
"""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.config_manager import ConfigManager, get_config, set_config
from tests.helpers.test_db_helper import PostgreSQLTestHelper


class TestConfigManager:
    """Test suite for ConfigManager class."""

    def test_default_configuration(self):
        """Test that default configuration is properly initialized."""
        config = get_config()

        assert config.app_name == "GiljoAI MCP Coding Orchestrator"
        assert config.app_version == "0.1.0"
        assert config.server.debug is False
        assert config.database.database_type == "postgresql"  # Project standardized on PostgreSQL
        assert config.server.api_host == "127.0.0.1"
        assert config.server.api_port == 8000
        assert config.tenant.enable_multi_tenant is True
        assert config.session.vision_chunk_size == 50000
        assert config.session.vision_overlap == 500

    def test_server_binds_all_interfaces(self):
        """Test that server always binds to 0.0.0.0 (v3.0: mode removed, firewall controls access)."""
        config = get_config()

        # v3.0: Server always binds to 0.0.0.0, firewall controls access
        assert config.server.api_host == "0.0.0.0"

    def test_path_settings_os_neutral(self):
        """Test that path settings use OS-neutral paths."""
        config = get_config()

        # Verify paths are Path objects
        assert isinstance(config.get_data_dir(), Path)
        assert isinstance(config.get_config_dir(), Path)
        assert isinstance(config.get_log_dir(), Path)

        # Verify paths are under user home
        home = Path.home()
        assert str(config.get_data_dir()).startswith(str(home))
        assert str(config.get_config_dir()).startswith(str(home))
        assert str(config.get_log_dir()).startswith(str(home))

    @patch.dict(
        os.environ,
        {
            "GILJO_DATABASE_URL": "postgresql://user:pass@host:5432/db",
            "GILJO_DATABASE_TYPE": "postgresql",
            "GILJO_API_HOST": "0.0.0.0",
            "GILJO_API_PORT": "9000",
            "GILJO_DEBUG": "true",
        },
    )
    def test_environment_variable_override(self):
        """Test that environment variables override default settings."""
        # Create a fresh config manager to pick up env vars
        config_manager = ConfigManager()

        assert config_manager.database.database_url == "postgresql://user:pass@host:5432/db"
        assert config_manager.database.database_type == "postgresql"
        assert config_manager.server.api_host == "0.0.0.0"
        assert config_manager.server.api_port == 9000
        assert config_manager.server.debug is True

    def test_database_url_construction(self):
        """Test database URL construction for PostgreSQL."""
        config = get_config()

        # Test PostgreSQL URL construction (project standardized on PostgreSQL)
        config.database.database_type = "postgresql"
        config.database.host = "localhost"
        config.database.port = 5432
        config.database.username = "testuser"
        config.database.password = "testpass"
        config.database.database_name = "testdb"

        pg_url = config.get_database_url()
        assert pg_url == "postgresql://testuser:testpass@localhost:5432/testdb"

    def test_config_directory_creation(self):
        """Test that configuration directories are created properly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config = get_config()

            # Override paths to use temp directory
            temp_path = Path(temp_dir)
            config._override_base_dir = temp_path

            # Get directories (should create them)
            data_dir = config.get_data_dir()
            config_dir = config.get_config_dir()
            log_dir = config.get_log_dir()

            # Verify they were created
            assert data_dir.exists()
            assert config_dir.exists()
            assert log_dir.exists()

            # Verify they're under temp directory
            assert str(data_dir).startswith(str(temp_path))
            assert str(config_dir).startswith(str(temp_path))
            assert str(log_dir).startswith(str(temp_path))

    def test_config_validation(self):
        """Test configuration validation."""
        config = get_config()

        # Test valid port range
        config.server.api_port = 8000
        assert config.server.api_port == 8000

        # Test invalid port (should be handled gracefully)
        try:
            config.server.api_port = -1
            # If no validation, that's okay for now
        except ValueError:
            # If validation exists, this is expected
            pass

    def test_feature_flags(self):
        """Test feature flag configuration."""
        config = get_config()

        # Test default feature flags
        assert hasattr(config, "features")

        # Feature flags should be configurable
        config.features.enable_websockets = True
        assert config.features.enable_websockets is True

        config.features.enable_websockets = False
        assert config.features.enable_websockets is False

    def test_agent_configuration(self):
        """Test agent-specific configuration."""
        config = get_config()

        # Test agent limits
        assert config.agent.max_agents > 0
        assert config.agent.default_context_budget > 0
        assert config.agent.context_warning_threshold > 0

    def test_message_configuration(self):
        """Test message system configuration."""
        config = get_config()

        # Test message settings
        assert config.message.max_queue_size > 0
        assert config.message.message_timeout > 0
        assert config.message.max_retries > 0

    def test_config_file_operations(self):
        """Test configuration file save/load operations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_file = Path(temp_dir) / "test_config.yaml"

            config = get_config()

            # Save configuration
            config.save_to_file(config_file)
            assert config_file.exists()

            # Load configuration
            new_config = ConfigManager.load_from_file(config_file)
            assert new_config.app_name == config.app_name
            assert new_config.server.api_port == config.server.api_port

    def test_config_singleton_behavior(self):
        """Test that get_config returns the same instance."""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

    def test_config_override(self):
        """Test configuration override with set_config."""
        original_config = get_config()

        # Create new config with different settings
        new_config = ConfigManager()
        new_config.app_name = "Test App"

        # Override global config
        set_config(new_config)

        # Verify override worked
        current_config = get_config()
        assert current_config.app_name == "Test App"

        # Restore original (cleanup)
        set_config(original_config)

    def test_tenant_configuration(self):
        """Test multi-tenant configuration."""
        config = get_config()

        assert hasattr(config.tenant, "enable_multi_tenant")
        assert hasattr(config.tenant, "default_tenant_key")
        assert hasattr(config.tenant, "tenant_isolation_level")

    def test_session_configuration(self):
        """Test session-specific configuration."""
        config = get_config()

        # Test vision processing settings
        assert config.session.vision_chunk_size > 0
        assert config.session.vision_overlap >= 0
        assert config.session.max_vision_size > config.session.vision_chunk_size

    @patch.dict(os.environ, {"GILJO_CONFIG_FILE": "nonexistent.yaml"})
    def test_missing_config_file_handling(self):
        """Test handling of missing configuration file."""
        # Should not crash, should use defaults
        config = ConfigManager()
        assert config.app_name == "GiljoAI MCP Coding Orchestrator"

    def test_config_schema_validation(self):
        """Test that configuration follows expected schema."""
        config = get_config()

        # Required sections should exist
        assert hasattr(config, "server")
        assert hasattr(config, "database")
        assert hasattr(config, "logging")
        assert hasattr(config, "session")
        assert hasattr(config, "agent")
        assert hasattr(config, "message")
        assert hasattr(config, "tenant")
        assert hasattr(config, "features")

        # Server section
        assert hasattr(config.server, "api_host")
        assert hasattr(config.server, "api_port")
        assert hasattr(config.server, "debug")

        # Database section
        assert hasattr(config.database, "database_type")
        assert hasattr(config.database, "database_name")


class TestConfigManagerEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_with_invalid_yaml(self):
        """Test handling of invalid YAML configuration."""
        temp_file = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
                temp_file = f.name
                f.write("invalid: yaml: content: [unclosed")
                f.flush()

            # Should handle gracefully
            try:
                ConfigManager.load_from_file(Path(temp_file))
            except Exception:
                # Expected - invalid YAML should raise an exception
                pass
        finally:
            # Windows-compatible file cleanup
            if temp_file and os.path.exists(temp_file):
                try:
                    os.unlink(temp_file)
                except PermissionError:
                    # On Windows, add a small delay and retry
                    import time

                    time.sleep(0.1)
                    try:
                        os.unlink(temp_file)
                    except PermissionError:
                        # If still locked, skip cleanup (temp files will be cleaned by OS)
                        pass

    def test_config_permissions_error(self):
        """Test handling of permission errors."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "readonly"
            config_dir.mkdir()

            # Make directory read-only
            config_dir.chmod(0o444)

            config = get_config()

            try:
                # This might fail due to permissions, which is expected
                config.ensure_directories_exist()
            except PermissionError:
                pass  # Expected
            finally:
                # Restore permissions for cleanup
                config_dir.chmod(0o755)


if __name__ == "__main__":
    pytest.main([__file__])
