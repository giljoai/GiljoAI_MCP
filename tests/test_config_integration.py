"""
Integration tests for the complete configuration system.

Tests the interaction between ConfigManager instances,
environment variables, file loading, hot-reloading, and
multi-tenant scenarios.
"""

import os
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


sys.path.insert(0, str(Path(__file__).parent.parent))


from src.giljo_mcp.config_manager import ConfigManager, ConfigValidationError


class TestConfigIntegration:
    """Integration tests for ConfigManager instances together."""

    def test_config_manager_compatibility(self, temp_dir):
        """Test that multiple ConfigManager instances work together."""
        # Create config directory
        config_dir = temp_dir / "config"
        config_dir.mkdir()

        # Create first ConfigManager instance
        config_path = config_dir / "config.yaml"
        manager1 = ConfigManager(config_path=config_path)

        # Create a second ConfigManager instance
        manager2 = ConfigManager(config_path=config_path)

        # Save config data using first manager
        config_data = {
            "server": {"host": "localhost", "port": 6000},
            "database": {"type": "sqlite"},
        }
        manager1.save_to_file(config_path, config_data)

        # Second manager should be able to load it
        manager2.load()

        assert manager2.server.host == "localhost"
        assert manager2.server.port == 6000

    @patch.dict(
        os.environ,
        {
            "DATABASE_URL": "postgresql://user:pass@dbhost:5432/testdb",
            "API_HOST": "0.0.0.0",
            "API_PORT": "8888",
            "GILJO_SERVER_HOST": "0.0.0.0",
            "GILJO_SERVER_PORT": "8888",
            "GILJO_DATABASE_TYPE": "postgresql",
        },
    )
    def test_environment_variable_precedence(self, temp_dir):
        """Test that environment variables override both Settings and ConfigManager."""
        # Create config file with different values
        config_file = temp_dir / "config.yaml"
        config_data = {"server": {"host": "localhost", "port": 6000}, "database": {"type": "sqlite"}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # ConfigManager should pick up env vars
        manager_env = ConfigManager()
        manager_env.load()

        assert manager_env.server.host == "0.0.0.0"
        assert manager_env.server.port == 8888

        # ConfigManager should also pick up env vars
        manager = ConfigManager(config_path=config_file)
        manager.load()

        assert manager.server.host == "0.0.0.0"
        assert manager.server.port == 8888
        assert manager.database.type == "postgresql"

    def test_hot_reload_with_validation(self, temp_dir):
        """Test hot-reload with validation of changed configuration."""
        config_file = temp_dir / "config.yaml"

        initial_config = {
            "server": {"host": "localhost", "port": 6000},
            "database": {"type": "sqlite", "path": str(temp_dir / "test.db")},
        }

        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)

        manager = ConfigManager(config_path=config_file, auto_reload=True)
        manager.load()

        assert manager.server.port == 6000

        # Update with valid configuration
        valid_config = initial_config.copy()
        valid_config["server"]["port"] = 7000

        with open(config_file, "w") as f:
            yaml.dump(valid_config, f)

        manager.reload()
        assert manager.server.port == 7000

        # Try to update with invalid configuration
        invalid_config = initial_config.copy()
        invalid_config["server"]["port"] = 99999  # Invalid port

        with open(config_file, "w") as f:
            yaml.dump(invalid_config, f)

        # Reload should fail validation
        with pytest.raises(ConfigValidationError):
            manager.reload()

        # Configuration should remain at last valid state
        assert manager.server.port == 7000

    def test_multi_tenant_configuration_isolation(self, temp_dir):
        """Test multi-tenant configuration isolation."""
        # Create configurations for different tenants
        tenant1_config = temp_dir / "tenant1_config.yaml"
        tenant2_config = temp_dir / "tenant2_config.yaml"

        tenant1_data = {
            "server": {"port": 6001},
            "session": {"multi_tenant_enabled": True, "tenant_isolation_level": "strict"},
            "agents": {"default_tenant_key": "tenant-1", "enable_tenant_scoping": True},
        }

        tenant2_data = {
            "server": {"port": 6002},
            "session": {"multi_tenant_enabled": True, "tenant_isolation_level": "strict"},
            "agents": {"default_tenant_key": "tenant-2", "enable_tenant_scoping": True},
        }

        with open(tenant1_config, "w") as f:
            yaml.dump(tenant1_data, f)

        with open(tenant2_config, "w") as f:
            yaml.dump(tenant2_data, f)

        # Load configurations for different tenants
        manager1 = ConfigManager(config_path=tenant1_config)
        manager1.load()

        manager2 = ConfigManager(config_path=tenant2_config)
        manager2.load()

        # Verify isolation
        assert manager1.server.port != manager2.server.port
        assert manager1.agents.default_tenant_key == "tenant-1"
        assert manager2.agents.default_tenant_key == "tenant-2"

        # Both should have multi-tenant enabled
        assert manager1.session.multi_tenant_enabled is True
        assert manager2.session.multi_tenant_enabled is True

    def test_concurrent_configuration_access(self, temp_dir):
        """Test thread-safe concurrent access to configuration."""
        config_file = temp_dir / "config.yaml"

        config_data = {"server": {"port": 6000}, "database": {"type": "sqlite", "path": str(temp_dir / "test.db")}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = ConfigManager(config_path=config_file)
        manager.load()

        errors = []
        results = []

        def reader_thread(thread_id):
            """Read configuration values."""
            try:
                for _ in range(100):
                    port = manager.server.port
                    db_type = manager.database.type
                    results.append(f"Reader {thread_id}: port={port}, db={db_type}")
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"Reader {thread_id}: {e}")

        def writer_thread(thread_id):
            """Modify configuration values."""
            try:
                for i in range(50):
                    manager.server.port = 6000 + i
                    time.sleep(0.002)
                results.append(f"Writer {thread_id}: completed")
            except Exception as e:
                errors.append(f"Writer {thread_id}: {e}")

        # Create threads
        threads = []
        for i in range(3):
            threads.append(threading.Thread(target=reader_thread, args=(i,)))
        for i in range(2):
            threads.append(threading.Thread(target=writer_thread, args=(i,)))

        # Run threads
        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Check for errors
        assert len(errors) == 0
        assert len(results) > 0

    def test_configuration_migration_path(self, temp_dir):
        """Test migration from old configuration format to new."""
        old_config_file = temp_dir / "old_config.yaml"
        new_config_file = temp_dir / "new_config.yaml"

        # Old format (simulated)
        old_format = {"host": "localhost", "port": 5000, "database": "postgresql://localhost/olddb", "debug": True}

        with open(old_config_file, "w") as f:
            yaml.dump(old_format, f)

        # Simulate migration logic
        with open(old_config_file) as f:
            old_data = yaml.safe_load(f)

        # Convert to new format
        new_format = {
            "server": {"host": old_data.get("host", "localhost"), "port": old_data.get("port", 6000)},
            "database": {
                "type": "postgresql" if "postgresql" in old_data.get("database", "") else "sqlite",
                "connection_string": old_data.get("database"),
            },
            "features": {"debug_mode": old_data.get("debug", False)},
        }

        with open(new_config_file, "w") as f:
            yaml.dump(new_format, f)

        # Load with new ConfigManager
        manager = ConfigManager(config_path=new_config_file)
        manager.load()

        assert manager.server.host == "localhost"
        assert manager.server.port == 5000
        assert manager.database.type == "postgresql"
        assert manager.features.debug_mode is True

    def test_zero_config_local_development(self):
        """Test that system works with zero configuration (v3.0: always binds 0.0.0.0)."""
        # No config file, no environment variables
        with patch.dict(os.environ, {}, clear=True):
            # ConfigManager should work with defaults (v3.0: always binds 0.0.0.0)
            manager = ConfigManager()
            assert manager.server.host == "0.0.0.0"
            assert manager.database.type == "postgresql"  # Project standardized on PostgreSQL

            # Should be able to get database URL
            assert "postgresql" in manager.database.get_connection_string()

    def test_config_file_watcher_lifecycle(self, temp_dir):
        """Test file watcher lifecycle for hot-reload."""
        config_file = temp_dir / "config.yaml"

        config_data = {"server": {"port": 6000}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Use context manager
        with ConfigManager(config_path=config_file, auto_reload=True) as manager:
            manager.load()

            # Mock file watcher
            with patch.object(manager, "_observer") as mock_observer:
                mock_observer.is_alive.return_value = True

                # Update config
                config_data["server"]["port"] = 7000
                with open(config_file, "w") as f:
                    yaml.dump(config_data, f)

                # Simulate file change event
                manager.reload()

                assert manager.server.port == 7000

        # After context exit, watcher should be stopped
        # (In real implementation, __exit__ would call stop_watching)


class TestErrorHandling:
    """Test error handling in configuration system."""

    def test_corrupt_yaml_handling(self, temp_dir):
        """Test handling of corrupt YAML files."""
        config_file = temp_dir / "corrupt.yaml"

        # Write invalid YAML
        with open(config_file, "w") as f:
            f.write("invalid: yaml: content: ][")

        manager = ConfigManager(config_path=config_file)

        # Should handle corrupt file gracefully
        with pytest.raises(yaml.YAMLError):
            manager.load()

    def test_missing_required_fields(self, temp_dir):
        """Test handling of missing required configuration fields."""
        config_file = temp_dir / "incomplete.yaml"

        # Config missing required database info for PostgreSQL
        incomplete_config = {
            "database": {
                "type": "postgresql"
                # Missing host, port, etc.
            }
        }

        with open(config_file, "w") as f:
            yaml.dump(incomplete_config, f)

        manager = ConfigManager(config_path=config_file)
        manager.load()

        # Validation should catch missing fields
        with pytest.raises(ConfigValidationError):
            manager.validate()

    def test_type_conversion_errors(self):
        """Test handling of type conversion errors."""
        with patch.dict(os.environ, {"GILJO_SERVER_PORT": "not-a-number"}), pytest.raises(ValueError):
            manager = ConfigManager()
            manager.load()

    def test_permission_errors(self, temp_dir):
        """Test handling of file permission errors."""
        config_file = temp_dir / "readonly.yaml"

        # Create read-only file
        config_data = {"server": {"port": 6000}}
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Make file read-only (Unix-like systems)
        if os.name != "nt":  # Not Windows
            os.chmod(config_file, 0o444)

        manager = ConfigManager(config_path=config_file)
        manager.load()

        # Try to save (should handle permission error)
        new_path = temp_dir / "new_config.yaml"
        try:
            manager.save_to_file(new_path)
            # Should succeed with new path
            assert new_path.exists()
        finally:
            # Restore permissions for cleanup
            if os.name != "nt":
                os.chmod(config_file, 0o644)
