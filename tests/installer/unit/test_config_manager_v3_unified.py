"""
TDD Tests for v3.0 Unified ConfigManager (installer/core/config.py)

Tests verify:
1. No mode-based classes or logic
2. Config generates v3.0 structure (version: 3.0.0)
3. Database host always localhost
4. API host always 0.0.0.0
5. Authentication always enabled
6. Deployment context is metadata only
"""

import pytest
import yaml
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock

from installer.core.config import ConfigManager, seed_default_orchestrator_template


class TestNoModeBasedClasses:
    """Test that mode-based installer classes are removed"""

    def test_no_localhost_installer_references(self):
        """Verify no LocalhostInstaller class references in config.py"""
        import inspect
        from installer.core import config

        source = inspect.getsource(config)

        # Should not have LocalhostInstaller references
        assert 'LocalhostInstaller' not in source, \
            "config.py should not reference LocalhostInstaller class"
        assert 'class LocalhostInstaller' not in source, \
            "config.py should not define LocalhostInstaller class"

    def test_no_server_installer_references(self):
        """Verify no ServerInstaller class references in config.py"""
        import inspect
        from installer.core import config

        source = inspect.getsource(config)

        assert 'ServerInstaller' not in source, \
            "config.py should not reference ServerInstaller class"
        assert 'class ServerInstaller' not in source, \
            "config.py should not define ServerInstaller class"

    def test_no_mode_branching_in_generate_all(self):
        """Verify generate_all() doesn't have mode-based branching"""
        import inspect
        from installer.core.config import ConfigManager

        source = inspect.getsource(ConfigManager.generate_all)

        # Should not have mode-based conditionals
        assert 'if self.mode == "server"' not in source, \
            "generate_all() should not have mode-based branching"
        assert 'if self.mode == "local"' not in source, \
            "generate_all() should not check for local mode"


class TestConfigYamlV3Structure:
    """Test config.yaml generation for v3.0 unified architecture"""

    @pytest.fixture
    def config_manager(self, tmp_path):
        """Create ConfigManager with test settings"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test_owner_123',
            'user_password': 'test_user_123',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path),
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"
        return manager

    def test_config_version_is_v3(self, config_manager):
        """Verify generated config has version 3.0.0"""
        result = config_manager.generate_config_yaml()
        assert result['success'], f"Config generation failed: {result.get('errors')}"

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        assert config['version'] == '3.0.0', \
            "Config version should be 3.0.0"

    def test_config_no_mode_field(self, config_manager):
        """Verify config.yaml has no mode field anywhere"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        # Check all sections - mode should not exist
        assert 'mode' not in config.get('installation', {}), \
            "installation section should not have mode field"
        assert 'mode' not in config.get('server', {}), \
            "server section should not have mode field"
        assert 'mode' not in config.get('database', {}), \
            "database section should not have mode field"

    def test_config_has_deployment_context(self, config_manager):
        """Verify config has deployment_context as metadata only"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        assert 'deployment_context' in config, \
            "Config should have deployment_context field"
        assert config['deployment_context'] == 'localhost', \
            "Default deployment_context should be localhost"

    def test_database_host_always_localhost(self, config_manager):
        """Verify database.host is always localhost"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        db_config = config.get('database', {})
        assert db_config.get('host') == 'localhost', \
            "Database host should ALWAYS be localhost"

    def test_server_api_host_always_0_0_0_0(self, config_manager):
        """Verify server.api_host is always 0.0.0.0"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        server_config = config.get('server', {})
        assert server_config.get('api_host') == '0.0.0.0', \
            "API host should ALWAYS be 0.0.0.0 in v3.0"

    def test_services_api_host_always_0_0_0_0(self, config_manager):
        """Verify services.api.host is always 0.0.0.0"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        api_service = config.get('services', {}).get('api', {})
        assert api_service.get('host') == '0.0.0.0', \
            "API service host should be 0.0.0.0"

    def test_features_authentication_always_true(self, config_manager):
        """Verify features.authentication is always True"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        features = config.get('features', {})
        assert features.get('authentication') is True, \
            "Authentication should ALWAYS be enabled in v3.0"

    def test_features_auto_login_localhost_true(self, config_manager):
        """Verify features.auto_login_localhost is True"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        features = config.get('features', {})
        assert features.get('auto_login_localhost') is True, \
            "Auto-login for localhost should be enabled"

    def test_no_server_specific_config_section(self, config_manager):
        """Verify no separate server-specific configuration section"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config_text = f.read()

        # Should not have mode-based conditional sections
        assert 'SERVER MODE ADDITIONAL SETTINGS' not in config_text, \
            "Should not have server mode specific sections"


class TestEnvFileV3Structure:
    """Test .env generation for v3.0 unified architecture"""

    @pytest.fixture
    def config_manager(self, tmp_path):
        """Create ConfigManager with test settings"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test_owner_123',
            'user_password': 'test_user_123',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path),
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"
        return manager

    def test_env_deployment_context_localhost(self, config_manager):
        """Verify DEPLOYMENT_CONTEXT=localhost in .env"""
        result = config_manager.generate_env_file()
        assert result['success']

        env_content = config_manager.env_file.read_text()
        assert 'DEPLOYMENT_CONTEXT=localhost' in env_content, \
            ".env should have DEPLOYMENT_CONTEXT=localhost"

    def test_env_api_host_always_0_0_0_0(self, config_manager):
        """Verify GILJO_API_HOST=0.0.0.0 in .env"""
        result = config_manager.generate_env_file()
        assert result['success']

        env_content = config_manager.env_file.read_text()
        assert 'GILJO_API_HOST=0.0.0.0' in env_content, \
            ".env should have GILJO_API_HOST=0.0.0.0"

    def test_env_no_mode_based_conditionals(self, config_manager):
        """Verify .env content has no mode-based sections"""
        result = config_manager.generate_env_file()
        assert result['success']

        env_content = config_manager.env_file.read_text()

        # Should not have mode-based sections
        assert 'SERVER MODE ADDITIONAL SETTINGS' not in env_content, \
            ".env should not have server mode sections"
        assert 'LOCAL MODE SETTINGS' not in env_content, \
            ".env should not have local mode sections"

    def test_env_v3_header_comment(self, config_manager):
        """Verify .env has v3.0 header comment"""
        result = config_manager.generate_env_file()
        assert result['success']

        env_content = config_manager.env_file.read_text()
        assert 'v3.0' in env_content or 'Version 3.0' in env_content, \
            ".env should indicate v3.0 in header"

    def test_env_localhost_metadata_comment(self, config_manager):
        """Verify .env has comment about localhost being metadata"""
        result = config_manager.generate_env_file()
        assert result['success']

        env_content = config_manager.env_file.read_text()
        assert 'informational only' in env_content.lower() or 'metadata' in env_content.lower(), \
            ".env should explain deployment_context is informational"


class TestSecurityConfigV3:
    """Test security configuration for v3.0"""

    @pytest.fixture
    def config_manager(self, tmp_path):
        """Create ConfigManager with test settings"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test_owner_123',
            'user_password': 'test_user_123',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path),
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"
        return manager

    def test_security_config_cors_localhost_only(self, config_manager):
        """Verify CORS defaults to localhost origins only"""
        security_config = config_manager._generate_security_config()

        cors_origins = security_config.get('cors', {}).get('allowed_origins', [])

        # Should have localhost origins
        assert any('127.0.0.1' in origin for origin in cors_origins), \
            "CORS should include 127.0.0.1 origins"
        assert any('localhost' in origin for origin in cors_origins), \
            "CORS should include localhost origins"

    def test_security_config_no_mode_based_api_keys(self, config_manager):
        """Verify no mode-based API key requirements"""
        security_config = config_manager._generate_security_config()

        api_keys = security_config.get('api_keys', {})

        # v3.0: API keys are optional, info field explains this
        assert 'info' in api_keys, \
            "api_keys should have info field explaining optional nature"
        assert 'optional' in api_keys.get('info', '').lower(), \
            "API keys should be documented as optional for localhost"

    def test_security_config_rate_limiting_always_enabled(self, config_manager):
        """Verify rate limiting is always enabled"""
        security_config = config_manager._generate_security_config()

        rate_limiting = security_config.get('rate_limiting', {})
        assert rate_limiting.get('enabled') is True, \
            "Rate limiting should be enabled"


class TestNoServerSpecificMethods:
    """Test that server-specific methods are removed"""

    def test_no_generate_server_configs_method(self):
        """Verify generate_server_configs() is removed"""
        from installer.core.config import ConfigManager

        # Method should not exist
        assert not hasattr(ConfigManager, 'generate_server_configs'), \
            "generate_server_configs() should be removed in v3.0"

    def test_no_generate_nginx_config_method(self):
        """Verify generate_nginx_config() is removed"""
        from installer.core.config import ConfigManager

        assert not hasattr(ConfigManager, 'generate_nginx_config'), \
            "generate_nginx_config() should be removed (moved to docs)"

    def test_no_generate_systemd_service_method(self):
        """Verify generate_systemd_service() is removed"""
        from installer.core.config import ConfigManager

        assert not hasattr(ConfigManager, 'generate_systemd_service'), \
            "generate_systemd_service() should be removed (moved to docs)"

    def test_no_generate_api_keys_method(self):
        """Verify generate_api_keys() is removed"""
        from installer.core.config import ConfigManager

        assert not hasattr(ConfigManager, 'generate_api_keys'), \
            "generate_api_keys() should be removed (handled at runtime)"


class TestConfigManagerInitialization:
    """Test ConfigManager initialization without mode parameter"""

    def test_config_manager_accepts_settings_dict(self, tmp_path):
        """Verify ConfigManager accepts settings dict"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test123',
            'user_password': 'test123',
            'api_port': 7272,
            'dashboard_port': 7274,
        }

        manager = ConfigManager(settings)
        assert manager.settings == settings

    def test_config_manager_no_mode_attribute(self, tmp_path):
        """Verify ConfigManager doesn't have mode attribute"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test123',
            'user_password': 'test123',
        }

        manager = ConfigManager(settings)

        # Should not have mode attribute
        assert not hasattr(manager, 'mode'), \
            "ConfigManager should not have mode attribute in v3.0"


class TestBackwardCompatibility:
    """Test that old configs with mode field still work"""

    @pytest.fixture
    def config_manager(self, tmp_path):
        """Create ConfigManager with test settings"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test123',
            'user_password': 'test123',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path),
            # Include legacy mode field (should be ignored)
            'mode': 'server',
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"
        return manager

    def test_legacy_mode_in_settings_ignored(self, config_manager):
        """Verify legacy mode field in settings is ignored"""
        result = config_manager.generate_config_yaml()
        assert result['success']

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        # Mode should not appear in generated config
        assert 'mode' not in config.get('installation', {}), \
            "Legacy mode field should not appear in generated config"


class TestOrchestratorTemplateSeeding:
    """Test orchestrator template seeding function"""

    def test_seed_default_orchestrator_template_function_exists(self):
        """Verify seed_default_orchestrator_template function is defined"""
        from installer.core.config import seed_default_orchestrator_template

        assert callable(seed_default_orchestrator_template), \
            "seed_default_orchestrator_template should be a callable function"

    def test_seed_function_has_correct_signature(self):
        """Verify seed function has correct parameters"""
        import inspect
        from installer.core.config import seed_default_orchestrator_template

        sig = inspect.signature(seed_default_orchestrator_template)
        params = list(sig.parameters.keys())

        assert 'db_manager' in params, "Should accept db_manager parameter"
        assert 'tenant_key' in params, "Should accept tenant_key parameter"


class TestValidateConfig:
    """Test configuration validation"""

    @pytest.fixture
    def config_manager(self, tmp_path):
        """Create ConfigManager with test settings"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test123',
            'user_password': 'test123',
            'api_port': 7272,
            'dashboard_port': 7274,
            'install_dir': str(tmp_path),
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"
        return manager

    def test_validate_config_checks_required_vars(self, config_manager):
        """Verify validate_config checks required variables"""
        # Generate configs first
        config_manager.generate_env_file()
        config_manager.generate_config_yaml()

        result = config_manager.validate_config()

        assert 'valid' in result, "validate_config should return validation result"
        assert 'issues' in result, "validate_config should return issues list"

    def test_validate_config_requires_env_file(self, tmp_path):
        """Verify validation fails if .env is missing"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test123',
            'user_password': 'test123',
        }

        manager = ConfigManager(settings)
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"

        result = manager.validate_config()

        assert not result['valid'], "Validation should fail without .env file"
        assert len(result['issues']) > 0, "Should report missing .env issue"


class TestCrossPlatformPaths:
    """Test that ConfigManager uses cross-platform paths"""

    def test_config_manager_uses_pathlib(self):
        """Verify ConfigManager uses pathlib.Path for file operations"""
        import inspect
        from installer.core import config

        source = inspect.getsource(config)

        # Should use pathlib.Path
        assert 'from pathlib import Path' in source or 'pathlib.Path' in source, \
            "config.py should use pathlib.Path"

    def test_config_paths_are_path_objects(self, tmp_path):
        """Verify config file paths are Path objects"""
        settings = {
            'pg_host': 'localhost',
            'pg_port': 5432,
            'owner_password': 'test123',
            'user_password': 'test123',
        }

        manager = ConfigManager(settings)

        assert isinstance(manager.config_file, Path), \
            "config_file should be a Path object"
        assert isinstance(manager.env_file, Path), \
            "env_file should be a Path object"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
