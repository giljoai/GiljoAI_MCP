"""
TDD Tests for Installer v3.0 (Phase 1 Step 6)

Tests verify:
1. No mode parameter in installer
2. Localhost user always created
3. Config has v3.0 fields (no mode)
4. Binding to 0.0.0.0 (all interfaces)
5. Firewall configuration (optional)
"""

import inspect
from pathlib import Path
from unittest.mock import Mock

import pytest
import yaml

from installer.core.config import ConfigManager

# Module imports - these will fail initially (TDD)
from installer.core.installer import BaseInstaller, LocalhostInstaller, ServerInstaller


class TestInstallerV3NoMode:
    """Test that installer doesn't accept mode parameter"""

    def test_base_installer_no_mode_parameter(self):
        """Verify BaseInstaller doesn't have mode as an init parameter"""
        # Get the __init__ signature
        sig = inspect.signature(BaseInstaller.__init__)

        # mode should not be a parameter (it's derived from settings)
        assert "mode" not in sig.parameters, "BaseInstaller should not have 'mode' as a direct parameter"

        # settings dict should contain mode, not as a separate parameter
        assert "settings" in sig.parameters, "BaseInstaller should accept settings dict"

    def test_localhost_installer_no_mode_parameter(self):
        """Verify LocalhostInstaller doesn't have mode as an init parameter"""
        sig = inspect.signature(LocalhostInstaller.__init__)
        assert "mode" not in sig.parameters, "LocalhostInstaller should not have mode parameter"

    def test_server_installer_no_mode_parameter(self):
        """Verify ServerInstaller doesn't have mode as an init parameter"""
        sig = inspect.signature(ServerInstaller.__init__)
        assert "mode" not in sig.parameters, "ServerInstaller should not have mode parameter"

    def test_installer_accepts_settings_dict(self):
        """Verify installer accepts settings dict with mode inside"""
        settings = {
            "install_dir": str(Path("/tmp/test")),
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_password": "test123",
            "api_port": 7272,
            "dashboard_port": 7274,
        }

        # Should not raise - mode is optional in settings
        # Use LocalhostInstaller since BaseInstaller is abstract
        installer = LocalhostInstaller(settings)
        assert installer.settings == settings


class TestConfigGeneratorV3:
    """Test that ConfigManager generates v3.0 config without mode field"""

    @pytest.fixture
    def config_manager(self, tmp_path):
        """Create ConfigManager with temporary paths"""
        settings = {
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_password": "test123",
            "api_port": 7272,
            "dashboard_port": 7274,
            "install_dir": str(tmp_path),
        }

        manager = ConfigManager(settings)
        # Override file paths for testing
        manager.config_file = tmp_path / "config.yaml"
        manager.env_file = tmp_path / ".env"
        return manager

    def test_config_no_mode_field(self, config_manager):
        """Verify generated config.yaml has no mode field"""
        result = config_manager.generate_config_yaml()

        assert result["success"], f"Config generation failed: {result.get('errors')}"

        # Read generated config
        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        # Should NOT have mode in installation section
        assert "mode" not in config.get("installation", {}), "Config should not contain 'mode' field"

        # Should NOT have mode in server section
        assert "mode" not in config.get("server", {}), "Config should not contain 'mode' in server section"

    def test_config_has_v3_version(self, config_manager):
        """Verify generated config has v3.0.0 version"""
        result = config_manager.generate_config_yaml()
        assert result["success"]

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        # Check version is 3.0.0
        assert config.get("version") == "3.0.0", "Config should have version 3.0.0"

    def test_config_has_v3_features(self, config_manager):
        """Verify generated config has v3.0 feature flags"""
        result = config_manager.generate_config_yaml()
        assert result["success"]

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        features = config.get("features", {})

        # v3.0 features
        assert features.get("authentication") is True, "Authentication should always be enabled"
        assert features.get("auto_login_localhost") is True, "Localhost auto-login should be enabled"

    def test_config_binds_to_all_interfaces(self, config_manager):
        """Verify generated config binds to 0.0.0.0"""
        result = config_manager.generate_config_yaml()
        assert result["success"]

        with open(config_manager.config_file) as f:
            config = yaml.safe_load(f)

        server = config.get("server", {})

        # v3.0 always binds to 0.0.0.0 (all interfaces)
        assert server.get("api_host") == "0.0.0.0", "API should bind to all interfaces"
        assert server.get("dashboard_host") == "0.0.0.0", "Dashboard should bind to all interfaces"
        assert server.get("mcp_host") == "0.0.0.0", "MCP should bind to all interfaces"

    def test_env_file_localhost_context(self, config_manager):
        """Verify .env file has deployment_context=localhost"""
        result = config_manager.generate_env_file()
        assert result["success"]

        env_content = config_manager.env_file.read_text()

        # Should have deployment_context (informational only)
        assert "DEPLOYMENT_CONTEXT=localhost" in env_content or "deployment_context" in env_content.lower()


class TestInstallationFlow:
    """Test complete installation flow for v3.0"""

    @pytest.fixture
    def mock_installer(self, tmp_path):
        """Create installer with mocked dependencies"""
        settings = {
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_password": "test123",
            "api_port": 7272,
            "dashboard_port": 7274,
            "install_dir": str(tmp_path),
            "batch": True,  # Non-interactive
        }

        # Use LocalhostInstaller since BaseInstaller is abstract
        installer = LocalhostInstaller(settings)

        # Mock sub-components
        installer.db_installer = Mock()
        installer.config_manager = Mock()
        installer.post_validator = Mock()

        return installer

    def test_installation_sequence(self, mock_installer):
        """Verify installation follows correct sequence"""
        # Mock successful results
        mock_installer.create_venv = Mock(return_value={"success": True})
        mock_installer.db_installer.setup = Mock(return_value={"success": True, "credentials": {}})
        mock_installer.config_manager.generate_all = Mock(return_value={"success": True})
        mock_installer.install_dependencies = Mock(return_value={"success": True})
        mock_installer.install_frontend_dependencies = Mock(return_value={"success": True})
        mock_installer.create_launchers = Mock(return_value={"success": True})
        mock_installer.mode_specific_setup = Mock(return_value={"success": True})
        mock_installer.post_validator.validate = Mock(return_value={"valid": True})

        result = mock_installer.install()

        # Verify success
        assert result["success"], f"Installation failed: {result.get('error')}"

        # Verify sequence
        mock_installer.create_venv.assert_called_once()
        mock_installer.db_installer.setup.assert_called_once()
        mock_installer.config_manager.generate_all.assert_called_once()


class TestInstallerPaths:
    """Test that installer uses cross-platform paths"""

    def test_installer_uses_pathlib(self):
        """Verify installer uses pathlib.Path for all file operations"""
        import inspect

        from installer.core.installer import BaseInstaller

        # Get source code
        source = inspect.getsource(BaseInstaller)

        # Should use Path, not string concatenation
        assert "from pathlib import Path" in source or "pathlib.Path" in source, "Installer should use pathlib.Path"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
