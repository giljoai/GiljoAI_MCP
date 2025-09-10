"""
Pytest configuration and shared fixtures for configuration tests.
"""

import os
import tempfile
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_home_directory(temp_dir):
    """Mock the user's home directory for testing."""
    with patch('pathlib.Path.home', return_value=temp_dir):
        yield temp_dir


@pytest.fixture
def sample_config_yaml(temp_dir):
    """Create a sample config.yaml file."""
    config_file = temp_dir / "config.yaml"
    
    config = {
        'server': {
            'host': '127.0.0.1',
            'port': 6000,
            'mode': 'local',
            'api_key': None,
            'tls_enabled': False,
            'cors_enabled': False
        },
        'database': {
            'type': 'sqlite',
            'path': str(temp_dir / 'test.db'),
            'connection_pool_size': 5
        },
        'logging': {
            'level': 'INFO',
            'file': str(temp_dir / 'logs' / 'app.log'),
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'rotate': True,
            'max_bytes': 10485760,
            'backup_count': 5
        },
        'session': {
            'timeout': 3600,
            'max_sessions': 100,
            'multi_tenant_enabled': True,
            'tenant_isolation_level': 'strict'
        },
        'agents': {
            'max_agents': 20,
            'default_timeout': 300,
            'enable_tenant_scoping': True,
            'default_tenant_key': None
        },
        'messages': {
            'max_queue_size': 1000,
            'retention_days': 30,
            'tenant_scoped': True,
            'cross_tenant_messaging': False
        },
        'features': {
            'hot_reload': True,
            'multi_tenant': True,
            'debug_mode': False,
            'telemetry': False
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return config_file


@pytest.fixture
def lan_config_yaml(temp_dir):
    """Create a LAN mode config.yaml file."""
    config_file = temp_dir / "lan_config.yaml"
    
    config = {
        'server': {
            'host': '192.168.1.100',
            'port': 6000,
            'mode': 'lan',
            'api_key': 'test-lan-key-123',
            'tls_enabled': False,
            'cors_enabled': True
        },
        'database': {
            'type': 'postgresql',
            'host': '192.168.1.50',
            'port': 5432,
            'database': 'giljo_mcp',
            'username': 'giljo_user',
            'password': 'secure_password',
            'connection_pool_size': 10
        },
        'logging': {
            'level': 'INFO',
            'file': str(temp_dir / 'logs' / 'app.log')
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return config_file


@pytest.fixture
def wan_config_yaml(temp_dir):
    """Create a WAN mode config.yaml file."""
    config_file = temp_dir / "wan_config.yaml"
    
    config = {
        'server': {
            'host': '0.0.0.0',
            'port': 443,
            'mode': 'wan',
            'api_key': 'secure-wan-key-xyz789',
            'tls_enabled': True,
            'tls_cert': '/etc/ssl/certs/server.crt',
            'tls_key': '/etc/ssl/private/server.key',
            'cors_enabled': True,
            'cors_origins': ['https://app.example.com', 'https://admin.example.com']
        },
        'database': {
            'type': 'postgresql',
            'host': 'db.example.com',
            'port': 5432,
            'database': 'giljo_production',
            'username': 'giljo_prod',
            'password': 'ultra_secure_password',
            'connection_pool_size': 20,
            'ssl_mode': 'require'
        },
        'logging': {
            'level': 'WARNING',
            'file': '/var/log/giljo/app.log',
            'syslog': True
        },
        'features': {
            'hot_reload': False,
            'debug_mode': False,
            'telemetry': True
        }
    }
    
    with open(config_file, 'w') as f:
        yaml.dump(config, f, default_flow_style=False)
    
    return config_file


@pytest.fixture
def clean_environment():
    """Clean environment variables before each test."""
    env_vars = [
        'GILJO_SERVER_HOST',
        'GILJO_SERVER_PORT',
        'GILJO_SERVER_MODE',
        'GILJO_DATABASE_TYPE',
        'GILJO_DATABASE_HOST',
        'GILJO_DATABASE_PORT',
        'GILJO_DATABASE_NAME',
        'GILJO_DATABASE_USER',
        'GILJO_DATABASE_PASSWORD',
        'GILJO_LOGGING_LEVEL',
        'GILJO_API_KEY',
        'DATABASE_URL',
        'DB_TYPE',
        'API_HOST',
        'API_PORT',
        'API_KEY'
    ]
    
    # Store original values
    original = {}
    for var in env_vars:
        if var in os.environ:
            original[var] = os.environ[var]
            del os.environ[var]
    
    yield
    
    # Restore original values
    for var, value in original.items():
        os.environ[var] = value


@pytest.fixture
def mock_file_watcher():
    """Mock file watcher for hot-reload tests."""
    from unittest.mock import MagicMock
    
    watcher = MagicMock()
    watcher.is_alive.return_value = False
    watcher.stop.return_value = None
    watcher.join.return_value = None
    
    return watcher


@pytest.fixture
def create_test_config():
    """Factory fixture for creating test configurations."""
    def _create_config(mode='local', **kwargs):
        """
        Create a test configuration dictionary.
        
        Args:
            mode: Deployment mode (local, lan, wan)
            **kwargs: Additional config overrides
        """
        base_config = {
            'server': {
                'host': '127.0.0.1' if mode == 'local' else '0.0.0.0',
                'port': 6000,
                'mode': mode,
                'api_key': None if mode == 'local' else f'{mode}-key-123',
                'tls_enabled': mode == 'wan',
                'cors_enabled': mode != 'local'
            },
            'database': {
                'type': 'sqlite' if mode == 'local' else 'postgresql',
                'path': '/tmp/test.db' if mode == 'local' else None,
                'host': 'localhost' if mode != 'local' else None,
                'port': 5432 if mode != 'local' else None,
                'connection_pool_size': 5 if mode == 'local' else (10 if mode == 'lan' else 20)
            },
            'logging': {
                'level': 'DEBUG' if mode == 'local' else ('INFO' if mode == 'lan' else 'WARNING')
            },
            'features': {
                'hot_reload': mode == 'local',
                'debug_mode': mode == 'local',
                'multi_tenant': True
            }
        }
        
        # Apply overrides
        for key, value in kwargs.items():
            if '.' in key:
                # Handle nested keys like 'server.port'
                parts = key.split('.')
                current = base_config
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = value
            else:
                base_config[key] = value
        
        return base_config
    
    return _create_config


@pytest.fixture
def assert_config_valid():
    """Helper fixture for validating configuration."""
    def _assert_valid(config_manager):
        """
        Assert that a ConfigManager instance has valid configuration.
        
        Args:
            config_manager: ConfigManager instance to validate
        """
        # Check required attributes exist
        assert hasattr(config_manager, 'server')
        assert hasattr(config_manager, 'database')
        assert hasattr(config_manager, 'logging')
        assert hasattr(config_manager, 'session')
        assert hasattr(config_manager, 'agents')
        assert hasattr(config_manager, 'messages')
        assert hasattr(config_manager, 'features')
        
        # Validate port range
        assert 1 <= config_manager.server.port <= 65535
        
        # Validate database configuration
        if config_manager.database.type == 'sqlite':
            assert config_manager.database.path is not None
        elif config_manager.database.type == 'postgresql':
            assert config_manager.database.host is not None
            assert config_manager.database.port is not None
        
        # Validate mode-specific requirements
        if config_manager.server.mode == 'wan':
            assert config_manager.server.tls_enabled is True
            assert config_manager.server.api_key is not None
        
        return True
    
    return _assert_valid