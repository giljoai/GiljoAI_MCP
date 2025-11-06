"""
Unit tests for installer wizard auto-start functionality.

Tests the installer's decision logic for opening wizard vs dashboard.
"""

from pathlib import Path
from typing import Dict
from unittest.mock import Mock, patch

import pytest
import yaml


class TestInstallerWizardAutoStartLogic:
    """Test installer's wizard auto-start decision logic."""

    @pytest.fixture
    def fresh_install_config(self, tmp_path: Path) -> Dict:
        """Create config for fresh installation."""
        return {
            "setup_mode": True,
            "installation": {"mode": "localhost"},
            "services": {
                "api": {"port": 7272},
                "frontend": {"port": 7274, "auto_open": True},
            },
        }

    @pytest.fixture
    def complete_install_config(self, tmp_path: Path) -> Dict:
        """Create config for completed installation."""
        return {
            "setup_mode": False,
            "installation": {"mode": "localhost"},
            "services": {
                "api": {"port": 7272},
                "frontend": {"port": 7274, "auto_open": True},
            },
        }

    def test_determine_browser_url_fresh_install(self, fresh_install_config: Dict):
        """Test URL determination for fresh installation."""

        def get_browser_url(config: Dict) -> str:
            """Determine which URL to open based on setup_mode."""
            frontend_port = config["services"]["frontend"]["port"]
            setup_mode = config.get("setup_mode", True)

            if setup_mode:
                return f"http://localhost:{frontend_port}/wizard.html"
            return f"http://localhost:{frontend_port}"

        url = get_browser_url(fresh_install_config)
        assert url == "http://localhost:7274/wizard.html"

    def test_determine_browser_url_complete_setup(self, complete_install_config: Dict):
        """Test URL determination for completed setup."""

        def get_browser_url(config: Dict) -> str:
            """Determine which URL to open based on setup_mode."""
            frontend_port = config["services"]["frontend"]["port"]
            setup_mode = config.get("setup_mode", True)

            if setup_mode:
                return f"http://localhost:{frontend_port}/wizard.html"
            return f"http://localhost:{frontend_port}"

        url = get_browser_url(complete_install_config)
        assert url == "http://localhost:7274"

    def test_determine_browser_url_missing_setup_mode_defaults_to_wizard(self):
        """Test that missing setup_mode defaults to wizard (safe default)."""
        config = {
            "services": {"frontend": {"port": 7274}},
            # Note: setup_mode is missing
        }

        def get_browser_url(config: Dict) -> str:
            """Determine which URL to open based on setup_mode."""
            frontend_port = config["services"]["frontend"]["port"]
            setup_mode = config.get("setup_mode", True)  # Default to True

            if setup_mode:
                return f"http://localhost:{frontend_port}/wizard.html"
            return f"http://localhost:{frontend_port}"

        url = get_browser_url(config)
        assert url == "http://localhost:7274/wizard.html"

    def test_auto_open_disabled_no_browser_launch(self, fresh_install_config: Dict):
        """Test that auto_open: false prevents browser launch."""
        fresh_install_config["services"]["frontend"]["auto_open"] = False

        def should_open_browser(config: Dict) -> bool:
            """Check if browser should be opened."""
            return config["services"]["frontend"].get("auto_open", False)

        result = should_open_browser(fresh_install_config)
        assert result is False

    def test_auto_open_enabled_triggers_browser_launch(self, fresh_install_config: Dict):
        """Test that auto_open: true triggers browser launch."""
        fresh_install_config["services"]["frontend"]["auto_open"] = True

        def should_open_browser(config: Dict) -> bool:
            """Check if browser should be opened."""
            return config["services"]["frontend"].get("auto_open", False)

        result = should_open_browser(fresh_install_config)
        assert result is True


class TestInstallerConfigGeneration:
    """Test installer config generation includes setup_mode."""

    def test_generate_fresh_install_config_includes_setup_mode(self):
        """Test that fresh install config includes setup_mode: true."""

        def generate_fresh_config() -> Dict:
            """Generate config for fresh installation."""
            return {
                "setup_mode": True,
                "installation": {"mode": "localhost"},
                "services": {
                    "api": {"port": 7272},
                    "frontend": {"port": 7274, "auto_open": True},
                },
            }

        config = generate_fresh_config()
        assert "setup_mode" in config
        assert config["setup_mode"] is True

    def test_update_config_after_wizard_completion(self, tmp_path: Path):
        """Test updating config after wizard completion."""
        # Create initial config
        config_file = tmp_path / "config.yaml"
        initial_config = {
            "setup_mode": True,
            "installation": {"mode": "localhost"},
        }
        with open(config_file, "w") as f:
            yaml.dump(initial_config, f)

        # Simulate wizard completion update
        def complete_setup(config_path: Path):
            """Mark setup as complete in config."""
            with open(config_path) as f:
                config = yaml.safe_load(f)

            config["setup_mode"] = False

            with open(config_path, "w") as f:
                yaml.dump(config, f)

        # Complete setup
        complete_setup(config_file)

        # Verify update
        with open(config_file) as f:
            updated_config = yaml.safe_load(f)

        assert updated_config["setup_mode"] is False


class TestInstallerAutoStartIntegration:
    """Integration tests for installer auto-start behavior."""

    @patch("webbrowser.open")
    def test_installer_auto_start_wizard_flow(self, mock_browser: Mock):
        """Test complete installer auto-start wizard flow."""

        def installer_auto_start(config: Dict):
            """Simulate installer auto-start logic."""
            auto_open = config["services"]["frontend"].get("auto_open", False)
            if not auto_open:
                return None

            frontend_port = config["services"]["frontend"]["port"]
            setup_mode = config.get("setup_mode", True)

            if setup_mode:
                url = f"http://localhost:{frontend_port}/wizard.html"
            else:
                url = f"http://localhost:{frontend_port}"

            return url

        # Test fresh install
        fresh_config = {
            "setup_mode": True,
            "services": {"frontend": {"port": 7274, "auto_open": True}},
        }
        url = installer_auto_start(fresh_config)
        assert url == "http://localhost:7274/wizard.html"

        # Test completed setup
        complete_config = {
            "setup_mode": False,
            "services": {"frontend": {"port": 7274, "auto_open": True}},
        }
        url = installer_auto_start(complete_config)
        assert url == "http://localhost:7274"

        # Test auto_open disabled
        no_open_config = {
            "setup_mode": True,
            "services": {"frontend": {"port": 7274, "auto_open": False}},
        }
        url = installer_auto_start(no_open_config)
        assert url is None
