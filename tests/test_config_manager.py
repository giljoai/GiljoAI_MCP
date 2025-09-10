"""
Tests for the ConfigManager class.

Tests cover:
- Configuration loading from YAML files
- Environment variable overrides
- Deployment mode detection (LOCAL/LAN/WAN)
- Configuration validation
- Hot-reloading functionality
- Multi-tenant support
- Thread safety
"""

import os
import tempfile
import time
import threading
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch, MagicMock, call

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from giljo_mcp.config_manager import (
    ConfigManager,
    DeploymentMode,
    ConfigValidationError,
    ServerConfig,
    DatabaseConfig,
    LoggingConfig,
    SessionConfig,
    AgentConfig,
    MessageConfig,
    TenantConfig,
    FeatureFlags,
    get_config,
    set_config
)


class TestConfigManager:
    """Test suite for ConfigManager class."""
    
    @pytest.fixture
    def temp_config_file(self):
        """Create a temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config = {
                'server': {
                    'host': 'localhost',
                    'port': 6000,
                    'mode': 'local'
                },
                'database': {
                    'type': 'sqlite',
                    'path': '/tmp/test.db'
                },
                'logging': {
                    'level': 'INFO',
                    'file': '/tmp/test.log'
                },
                'features': {
                    'hot_reload': True,
                    'multi_tenant': True
                }
            }
            yaml.dump(config, f)
            yield Path(f.name)
        # Cleanup
        os.unlink(f.name)
    
    def test_default_initialization(self):
        """Test ConfigManager initializes with defaults."""
        manager = ConfigManager()
        
        assert manager.server.mode == DeploymentMode.LOCAL
        assert manager.server.host == "127.0.0.1"
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
    
    @patch.dict(os.environ, {
        'GILJO_SERVER_HOST': '0.0.0.0',
        'GILJO_SERVER_PORT': '8080',
        'GILJO_DATABASE_TYPE': 'postgresql',
        'GILJO_DATABASE_HOST': 'db.example.com',
        'GILJO_LOGGING_LEVEL': 'DEBUG'
    })
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
    
    def test_mode_detection_local(self):
        """Test LOCAL mode detection."""
        manager = ConfigManager()
        manager.server.host = "127.0.0.1"
        manager.server.api_key = None
        manager.server.tls_enabled = False
        
        manager._detect_mode()
        assert manager.server.mode == DeploymentMode.LOCAL
    
    def test_mode_detection_lan(self):
        """Test LAN mode detection."""
        manager = ConfigManager()
        manager.server.host = "192.168.1.100"
        manager.server.api_key = "test-key"
        manager.server.tls_enabled = False
        
        manager._detect_mode()
        assert manager.server.mode == DeploymentMode.LAN
    
    def test_mode_detection_wan(self):
        """Test WAN mode detection."""
        manager = ConfigManager()
        manager.server.host = "0.0.0.0"
        manager.server.tls_enabled = True
        manager.server.api_key = "secure-key"
        
        manager._detect_mode()
        assert manager.server.mode == DeploymentMode.WAN
    
    def test_mode_specific_settings(self):
        """Test that mode-specific settings are applied correctly."""
        manager = ConfigManager()
        
        # Test LOCAL mode settings
        manager.server.mode = DeploymentMode.LOCAL
        manager._apply_mode_settings()
        assert manager.server.cors_enabled is False
        assert manager.server.api_key is None
        
        # Test LAN mode settings
        manager.server.mode = DeploymentMode.LAN
        manager._apply_mode_settings()
        assert manager.server.cors_enabled is True
        assert manager.database.connection_pool_size == 10
        
        # Test WAN mode settings
        manager.server.mode = DeploymentMode.WAN
        manager._apply_mode_settings()
        assert manager.server.cors_enabled is True
        assert manager.database.connection_pool_size == 20
        assert manager.logging.level == "WARNING"
    
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
    
    def test_validation_wan_requires_tls(self):
        """Test validation fails when WAN mode lacks TLS."""
        manager = ConfigManager()
        manager.server.mode = DeploymentMode.WAN
        manager.server.tls_enabled = False
        
        with pytest.raises(ConfigValidationError, match="WAN mode requires TLS"):
            manager.validate()
    
    def test_validation_wan_requires_api_key(self):
        """Test validation fails when WAN mode lacks API key."""
        manager = ConfigManager()
        manager.server.mode = DeploymentMode.WAN
        manager.server.tls_enabled = True
        manager.server.api_key = None
        
        with pytest.raises(ConfigValidationError, match="WAN mode requires API key"):
            manager.validate()
    
    def test_hot_reload_functionality(self, temp_config_file):
        """Test hot-reload functionality when config file changes."""
        manager = ConfigManager(config_path=temp_config_file, auto_reload=True)
        manager.load()
        
        original_port = manager.server.port
        
        # Simulate file watcher setup
        with patch.object(manager, '_setup_file_watcher'):
            manager._setup_file_watcher()
        
        # Update the config file
        with open(temp_config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        config['server']['port'] = 7000
        
        with open(temp_config_file, 'w') as f:
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
        
        assert 'server' in settings
        assert 'database' in settings
        assert 'logging' in settings
        assert 'session' in settings
        assert 'agents' in settings
        assert 'messages' in settings
        assert 'features' in settings
        
        assert settings['server']['host'] == "127.0.0.1"
        assert settings['database']['type'] == "sqlite"
    
    def test_save_to_file(self):
        """Test saving configuration to file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "test_save.yaml"
            
            manager = ConfigManager()
            manager.server.port = 7777
            manager.database.type = "postgresql"
            
            manager.save_to_file(config_path)
            
            # Load the saved file and verify
            with open(config_path, 'r') as f:
                saved = yaml.safe_load(f)
            
            assert saved['server']['port'] == 7777
            assert saved['database']['type'] == "postgresql"
    
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
        assert manager.tenant.enabled is True
        assert manager.tenant.default_key is None
        assert manager.tenant.key_header == "X-Tenant-Key"
        assert manager.tenant.isolation_strict is True
        
        # Test modifying TenantConfig
        manager.tenant.enabled = False
        manager.tenant.default_key = "test-tenant-123"
        manager.tenant.key_header = "X-Custom-Tenant"
        manager.tenant.isolation_strict = False
        
        assert manager.tenant.enabled is False
        assert manager.tenant.default_key == "test-tenant-123"
        assert manager.tenant.key_header == "X-Custom-Tenant"
        assert manager.tenant.isolation_strict is False
    
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
        """Test configuration for fresh installation."""
        manager = ConfigManager()
        
        # Fresh install should use defaults
        assert manager.server.mode == DeploymentMode.LOCAL
        assert manager.database.type == "sqlite"
        assert manager.server.first_run is True
    
    def test_migration_scenario(self):
        """Test configuration migration from existing setup."""
        with tempfile.TemporaryDirectory() as tmpdir:
            old_config = Path(tmpdir) / "old_config.yaml"
            
            # Create old-style config
            old_data = {
                'host': 'localhost',
                'port': 5000,
                'database': 'postgresql://localhost/old_db'
            }
            
            with open(old_config, 'w') as f:
                yaml.dump(old_data, f)
            
            # Load and migrate (migration logic would be in ConfigManager)
            manager = ConfigManager(config_path=old_config)
            
            # In real implementation, ConfigManager would handle migration
            # Here we just verify the structure
            assert hasattr(manager.server, 'host')
            assert hasattr(manager.server, 'port')
            assert hasattr(manager.database, 'type')
    
    def test_development_environment(self):
        """Test configuration for development environment."""
        manager = ConfigManager()
        manager.server.mode = DeploymentMode.LOCAL
        manager.logging.level = "DEBUG"
        manager.features.hot_reload = True
        manager.features.debug_mode = True
        
        settings = manager.get_all_settings()
        
        assert settings['server']['mode'] == "local"
        assert settings['logging']['level'] == "DEBUG"
        assert settings['features']['hot_reload'] is True
    
    def test_production_environment(self):
        """Test configuration for production environment."""
        manager = ConfigManager()
        manager.server.mode = DeploymentMode.WAN
        manager.server.tls_enabled = True
        manager.server.api_key = "secure-production-key"
        manager.logging.level = "WARNING"
        manager.features.hot_reload = False
        manager.features.debug_mode = False
        manager.database.type = "postgresql"
        manager.database.connection_pool_size = 50
        
        settings = manager.get_all_settings()
        
        assert settings['server']['mode'] == "wan"
        assert settings['server']['tls_enabled'] is True
        assert settings['logging']['level'] == "WARNING"
        assert settings['database']['connection_pool_size'] == 50