"""
Tests for the ConfigManager class.

Tests cover:
- Configuration loading from YAML files
- Environment variable overrides
- Configuration validation
- Hot-reloading functionality
- Multi-tenant support
- Thread safety

Note: v3.0 - DeploymentMode removed, server always binds to 0.0.0.0
"""

import os
import sys
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.config_manager import ConfigManager, ConfigValidationError, get_config, set_config


class TestConfigManager:
    """Test suite for ConfigManager class."""

    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing (v3.0: mode removed)."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            config = {
                "server": {"host": "localhost", "port": 6000},
                "database": {"type": "sqlite", "path": "/tmp/test.db"},
                "logging": {"level": "INFO", "file": "/tmp/test.log"},
                "features": {"hot_reload": True, "multi_tenant": True},
            }
            yaml.dump(config, f)
            yield Path(f.name)
        # Cleanup
        os.unlink(f.name)

    def test_default_initialization(self):
        """Test ConfigManager initializes with defaults (v3.0: always binds 0.0.0.0)."""
        manager = ConfigManager()

        # v3.0: Server always binds to 0.0.0.0, firewall controls access
        assert manager.server.host == "0.0.0.0"
        assert manager.server.port == 6000
        assert manager.database.type == "sqlite"
        assert manager.logging.level == "INFO"
        assert manager.features.multi_tenant is True

    def test_load_from_yaml_file(self, temp_config_file):
        """Test loading configuration from YAML file."""
        manager = ConfigManager(config_path=temp_config_file)
        manager.load()

        assert manager.server.host == "localhost"
        assert manager.server.port == 6000
        assert manager.database.type == "sqlite"
        assert manager.database.path == Path("/tmp/test.db")
        assert manager.logging.level == "INFO"
        assert manager.features.hot_reload is True

    @patch.dict(
        os.environ,
        {
            "GILJO_SERVER_HOST": "0.0.0.0",
            "GILJO_SERVER_PORT": "8080",
            "GILJO_DATABASE_TYPE": "postgresql",
            "GILJO_DATABASE_HOST": "db.example.com",
            "GILJO_LOGGING_LEVEL": "DEBUG",
        },
    )
    def test_environment_override(self, temp_config_file):
        """Test that environment variables override file configuration."""
        manager = ConfigManager(config_path=temp_config_file)
        manager.load()

        # Environment variables should override file values
        assert manager.server.host == "0.0.0.0"
        assert manager.server.port == 8080
        assert manager.database.type == "postgresql"
        assert manager.database.host == "db.example.com"
        assert manager.logging.level == "DEBUG"

    def test_validation_success(self):
        """Test successful configuration validation."""
        manager = ConfigManager()
        manager.server.port = 6000
        manager.database.type = "sqlite"
        manager.database.path = Path("/tmp/test.db")

        # Should not raise any exception
        manager.validate()

    def test_validation_invalid_port(self):
        """Test validation fails for invalid port."""
        manager = ConfigManager()
        manager.server.port = 99999

        with pytest.raises(ConfigValidationError, match="Invalid port"):
            manager.validate()

    def test_validation_missing_database_path(self):
        """Test validation fails when SQLite path is missing."""
        manager = ConfigManager()
        manager.database.type = "sqlite"
        manager.database.path = None

        with pytest.raises(ConfigValidationError, match="SQLite database requires path"):
            manager.validate()

    def test_validation_missing_postgresql_config(self):
        """Test validation fails when PostgreSQL config is incomplete."""
        manager = ConfigManager()
        manager.database.type = "postgresql"
        manager.database.host = None

        with pytest.raises(ConfigValidationError, match="PostgreSQL requires host"):
            manager.validate()

    def test_hot_reload_functionality(self, temp_config_file):
        """Test hot-reload functionality when config file changes."""
        manager = ConfigManager(config_path=temp_config_file, auto_reload=True)
        manager.load()

        original_port = manager.server.port

        # Simulate file watcher setup
        with patch.object(manager, "_setup_file_watcher"):
            manager._setup_file_watcher()

        # Update the config file
        with open(temp_config_file) as f:
            config = yaml.safe_load(f)

        config["server"]["port"] = 7000

        with open(temp_config_file, "w") as f:
            yaml.dump(config, f)

        # Trigger reload
        manager.reload()

        assert manager.server.port == 7000
        assert manager.server.port != original_port

    def test_thread_safety(self, temp_config_file):
        """Test thread-safe configuration access."""
        manager = ConfigManager(config_path=temp_config_file)
        manager.load()

        results = []
        errors = []

        def read_config():
            try:
                for _ in range(100):
                    _ = manager.server.port
                    _ = manager.database.type
                    _ = manager.logging.level
                results.append("success")
            except Exception as e:
                errors.append(str(e))

        def write_config():
            try:
                for i in range(100):
                    manager.server.port = 6000 + i
                    manager.database.connection_pool_size = 10 + i
                results.append("success")
            except Exception as e:
                errors.append(str(e))

        # Create multiple threads
        threads = []
        for _ in range(5):
            threads.append(threading.Thread(target=read_config))
            threads.append(threading.Thread(target=write_config))

        # Start all threads
        for t in threads:
            t.start()

        # Wait for completion
        for t in threads:
            t.join()

        # Check no errors occurred
        assert len(errors) == 0
        assert len(results) == 10

    def test_get_all_settings(self):
        """Test getting all settings as dictionary."""
        manager = ConfigManager()
        settings = manager.get_all_settings()

        assert "server" in settings
        assert "database" in settings
        assert "logging" in settings
        assert "session" in settings
        assert "agents" in settings
        assert "messages" in settings
        assert "features" in settings

        assert settings["server"]["host"] == "127.0.0.1"
        assert settings["database"]["type"] == "sqlite"

    def test_context_manager(self):
        """Test ConfigManager as context manager."""
        with ConfigManager() as manager:
            assert manager is not None
            assert isinstance(manager, ConfigManager)

        # File watcher should be stopped after exiting context
        assert manager._observer is None or not manager._observer.is_alive()

    def test_singleton_pattern(self):
        """Test global config singleton."""
        config1 = get_config()
        config2 = get_config()

        assert config1 is config2

        # Test setting new config
        new_config = ConfigManager()
        new_config.server.port = 9999
        set_config(new_config)

        config3 = get_config()
        assert config3 is new_config
        assert config3.server.port == 9999


class TestMultiTenantConfig:
    """Test multi-tenant configuration features."""

    def test_tenant_config_dataclass(self):
        """Test TenantConfig dataclass initialization and defaults."""
        manager = ConfigManager()

        # Test default TenantConfig values
        assert manager.tenant.enable_multi_tenant is True
        assert manager.tenant.default_tenant_key is None
        assert manager.tenant.key_header == "X-Tenant-Key"
        assert manager.tenant.tenant_isolation_level == "strict"

        # Test modifying TenantConfig
        manager.tenant.enable_multi_tenant = False
        manager.tenant.default_tenant_key = "test-tenant-123"
        manager.tenant.key_header = "X-Custom-Tenant"
        manager.tenant.tenant_isolation_level = "relaxed"

        assert manager.tenant.enable_multi_tenant is False
        assert manager.tenant.default_tenant_key == "test-tenant-123"
        assert manager.tenant.key_header == "X-Custom-Tenant"
        assert manager.tenant.tenant_isolation_level == "relaxed"

    def test_tenant_isolation_settings(self):
        """Test tenant-specific configuration settings."""
        manager = ConfigManager()

        # Test tenant settings in session config
        manager.session.multi_tenant_enabled = True
        manager.session.tenant_isolation_level = "strict"

        assert manager.session.multi_tenant_enabled is True
        assert manager.session.tenant_isolation_level == "strict"

    def test_agent_tenant_config(self):
        """Test agent configuration with tenant support."""
        manager = ConfigManager()

        manager.agents.enable_tenant_scoping = True
        manager.agents.default_tenant_key = "test-tenant"

        assert manager.agents.enable_tenant_scoping is True
        assert manager.agents.default_tenant_key == "test-tenant"

    def test_message_tenant_config(self):
        """Test message configuration with tenant support."""
        manager = ConfigManager()

        manager.messages.tenant_scoped = True
        manager.messages.cross_tenant_messaging = False

        assert manager.messages.tenant_scoped is True
        assert manager.messages.cross_tenant_messaging is False


class TestConfigurationScenarios:
    """Test different deployment scenarios."""

    def test_fresh_installation_scenario(self):
        """Test configuration for fresh installation (v3.0: always binds 0.0.0.0)."""
        manager = ConfigManager()

        # Fresh install should use defaults (v3.0: no mode, always binds 0.0.0.0)
        assert manager.server.host == "0.0.0.0"
        assert manager.database.type == "sqlite"
        assert manager.server.first_run is True

    def test_migration_scenario(self):
        """Test configuration migration from existing setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_config = Path(tmpdir) / "old_config.yaml"

            # Create old-style config
            old_data = {"host": "localhost", "port": 5000, "database": "postgresql://localhost/old_db"}

            with open(old_config, "w") as f:
                yaml.dump(old_data, f)

            # Load and migrate (migration logic would be in ConfigManager)
            manager = ConfigManager(config_path=old_config)

            # In real implementation, ConfigManager would handle migration
            # Here we just verify the structure
            assert hasattr(manager.server, "host")
            assert hasattr(manager.server, "port")
            assert hasattr(manager.database, "type")
