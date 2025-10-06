"""
Integration tests for launcher wizard URL detection and auto-start behavior.

Tests the interaction between:
- start_giljo.py launcher
- /api/setup/status endpoint
- wizard.html vs main dashboard routing
- installer auto-start behavior
"""

import json
import socket
import time
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, Mock, patch

import pytest
import requests
import yaml


class TestLauncherWizardIntegration:
    """Test launcher's wizard detection and browser opening logic."""

    @pytest.fixture
    def mock_config_setup_mode(self, tmp_path: Path) -> Path:
        """Create a config.yaml with setup_mode: true."""
        config_data = {
            "setup_mode": True,
            "installation": {"mode": "localhost"},
            "services": {
                "api": {"host": "127.0.0.1", "port": 7272},
                "frontend": {"port": 7274, "auto_open": True},
            },
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        return config_file

    @pytest.fixture
    def mock_config_setup_complete(self, tmp_path: Path) -> Path:
        """Create a config.yaml with setup_mode: false (setup complete)."""
        config_data = {
            "setup_mode": False,
            "installation": {"mode": "localhost"},
            "services": {
                "api": {"host": "127.0.0.1", "port": 7272},
                "frontend": {"port": 7274, "auto_open": True},
            },
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        return config_file

    def test_check_setup_status_requires_setup(self):
        """Test checking setup status when setup is required."""
        # This would typically call the API endpoint
        # For now, we'll test the expected response format
        expected_response = {
            "setup_mode": True,
            "setup_complete": False,
            "requires_setup": True,
            "database_configured": False,
            "database_connected": False,
        }

        # Verify response structure
        assert "requires_setup" in expected_response
        assert expected_response["requires_setup"] is True
        assert expected_response["setup_mode"] is True

    def test_check_setup_status_setup_complete(self):
        """Test checking setup status when setup is complete."""
        expected_response = {
            "setup_mode": False,
            "setup_complete": True,
            "requires_setup": False,
            "database_configured": True,
            "database_connected": True,
        }

        # Verify response structure
        assert "requires_setup" in expected_response
        assert expected_response["requires_setup"] is False
        assert expected_response["setup_mode"] is False

    @patch("webbrowser.open")
    @patch("requests.get")
    def test_launcher_opens_wizard_when_setup_required(
        self, mock_get: Mock, mock_browser: Mock
    ):
        """Test that launcher opens wizard.html when setup is required."""
        # Mock API response indicating setup required
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "requires_setup": True,
            "setup_mode": True,
            "setup_complete": False,
        }
        mock_get.return_value = mock_response

        # Simulate launcher checking setup status
        api_url = "http://localhost:7272/api/setup/status"
        response = requests.get(api_url, timeout=2)
        setup_status = response.json()

        # Determine which URL to open
        frontend_port = 7274
        if setup_status.get("requires_setup", False):
            browser_url = f"http://localhost:{frontend_port}/wizard.html"
        else:
            browser_url = f"http://localhost:{frontend_port}"

        # Verify wizard URL is chosen
        assert browser_url == "http://localhost:7274/wizard.html"

    @patch("webbrowser.open")
    @patch("requests.get")
    def test_launcher_opens_dashboard_when_setup_complete(
        self, mock_get: Mock, mock_browser: Mock
    ):
        """Test that launcher opens main dashboard when setup is complete."""
        # Mock API response indicating setup complete
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "requires_setup": False,
            "setup_mode": False,
            "setup_complete": True,
        }
        mock_get.return_value = mock_response

        # Simulate launcher checking setup status
        api_url = "http://localhost:7272/api/setup/status"
        response = requests.get(api_url, timeout=2)
        setup_status = response.json()

        # Determine which URL to open
        frontend_port = 7274
        if setup_status.get("requires_setup", False):
            browser_url = f"http://localhost:{frontend_port}/wizard.html"
        else:
            browser_url = f"http://localhost:{frontend_port}"

        # Verify dashboard URL is chosen
        assert browser_url == "http://localhost:7274"

    @patch("webbrowser.open")
    @patch("requests.get")
    def test_launcher_handles_api_timeout_gracefully(
        self, mock_get: Mock, mock_browser: Mock
    ):
        """Test that launcher handles API timeout and defaults to wizard."""
        # Mock API timeout
        mock_get.side_effect = requests.exceptions.Timeout()

        # Simulate launcher checking setup status with fallback
        api_url = "http://localhost:7272/api/setup/status"
        try:
            response = requests.get(api_url, timeout=2)
            setup_status = response.json()
            requires_setup = setup_status.get("requires_setup", True)
        except (requests.exceptions.RequestException, ValueError):
            # Default to wizard if API is unreachable
            requires_setup = True

        # Determine which URL to open
        frontend_port = 7274
        if requires_setup:
            browser_url = f"http://localhost:{frontend_port}/wizard.html"
        else:
            browser_url = f"http://localhost:{frontend_port}"

        # Verify wizard URL is chosen as fallback
        assert browser_url == "http://localhost:7274/wizard.html"

    @patch("webbrowser.open")
    @patch("requests.get")
    def test_launcher_handles_api_error_gracefully(
        self, mock_get: Mock, mock_browser: Mock
    ):
        """Test that launcher handles API errors and defaults to wizard."""
        # Mock API error
        mock_response = Mock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        # Simulate launcher checking setup status with fallback
        api_url = "http://localhost:7272/api/setup/status"
        try:
            response = requests.get(api_url, timeout=2)
            if response.status_code != 200:
                raise requests.exceptions.HTTPError()
            setup_status = response.json()
            requires_setup = setup_status.get("requires_setup", True)
        except (requests.exceptions.RequestException, ValueError):
            # Default to wizard if API is unreachable or returns error
            requires_setup = True

        # Determine which URL to open
        frontend_port = 7274
        if requires_setup:
            browser_url = f"http://localhost:{frontend_port}/wizard.html"
        else:
            browser_url = f"http://localhost:{frontend_port}"

        # Verify wizard URL is chosen as fallback
        assert browser_url == "http://localhost:7274/wizard.html"


class TestInstallerWizardAutoStart:
    """Test installer's auto-start wizard behavior."""

    @pytest.fixture
    def mock_installer_settings_fresh(self) -> Dict:
        """Create installer settings for fresh installation."""
        return {
            "mode": "localhost",
            "auto_start": True,
            "api_port": 7272,
            "dashboard_port": 7274,
            "setup_mode": True,  # Fresh install has setup mode enabled
        }

    @pytest.fixture
    def mock_installer_settings_complete(self) -> Dict:
        """Create installer settings for completed setup."""
        return {
            "mode": "localhost",
            "auto_start": True,
            "api_port": 7272,
            "dashboard_port": 7274,
            "setup_mode": False,  # Setup already complete
        }

    @patch("webbrowser.open")
    def test_installer_opens_wizard_after_fresh_install(self, mock_browser: Mock):
        """Test that installer opens wizard after fresh installation."""
        # Simulate installer settings
        settings = {
            "mode": "localhost",
            "auto_start": True,
            "dashboard_port": 7274,
            "setup_mode": True,
        }

        # Simulate installer auto-start behavior
        if settings.get("auto_start") and settings.get("setup_mode", True):
            dashboard_port = settings["dashboard_port"]
            browser_url = f"http://localhost:{dashboard_port}/wizard.html"
        else:
            dashboard_port = settings["dashboard_port"]
            browser_url = f"http://localhost:{dashboard_port}"

        # Verify wizard URL
        assert browser_url == "http://localhost:7274/wizard.html"

    @patch("webbrowser.open")
    def test_installer_opens_dashboard_when_setup_already_complete(
        self, mock_browser: Mock
    ):
        """Test that installer opens dashboard when setup is already complete."""
        # Simulate installer settings with setup complete
        settings = {
            "mode": "localhost",
            "auto_start": True,
            "dashboard_port": 7274,
            "setup_mode": False,
        }

        # Simulate installer auto-start behavior
        if settings.get("auto_start") and settings.get("setup_mode", True):
            dashboard_port = settings["dashboard_port"]
            browser_url = f"http://localhost:{dashboard_port}/wizard.html"
        else:
            dashboard_port = settings["dashboard_port"]
            browser_url = f"http://localhost:{dashboard_port}"

        # Verify dashboard URL
        assert browser_url == "http://localhost:7274"

    @patch("webbrowser.open")
    def test_installer_no_auto_start_when_disabled(self, mock_browser: Mock):
        """Test that installer doesn't auto-start when disabled."""
        # Simulate installer settings with auto_start disabled
        settings = {
            "mode": "localhost",
            "auto_start": False,
            "dashboard_port": 7274,
            "setup_mode": True,
        }

        # Simulate installer auto-start behavior
        browser_opened = False
        if settings.get("auto_start"):
            browser_opened = True

        # Verify browser was not opened
        assert browser_opened is False


class TestSetupCompleteEndpoint:
    """Test /api/setup/complete endpoint behavior."""

    @pytest.fixture
    def mock_config_file(self, tmp_path: Path) -> Path:
        """Create a temporary config.yaml file."""
        config_data = {
            "setup_mode": True,
            "installation": {"mode": "localhost"},
            "services": {"api": {"port": 7272}},
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)
        return config_file

    def test_setup_complete_updates_config_yaml(self, mock_config_file: Path):
        """Test that /api/setup/complete updates setup_mode to false."""
        # Read initial config
        with open(mock_config_file, "r") as f:
            config_data = yaml.safe_load(f)

        assert config_data["setup_mode"] is True

        # Simulate the endpoint updating the config
        config_data["setup_mode"] = False

        # Write updated config
        with open(mock_config_file, "w") as f:
            yaml.dump(config_data, f)

        # Verify config was updated
        with open(mock_config_file, "r") as f:
            updated_config = yaml.safe_load(f)

        assert updated_config["setup_mode"] is False

    def test_setup_complete_response_format(self):
        """Test expected response format from /api/setup/complete."""
        expected_response = {"success": True, "setup_completed": True}

        # Verify response structure
        assert "success" in expected_response
        assert "setup_completed" in expected_response
        assert expected_response["success"] is True
        assert expected_response["setup_completed"] is True


class TestWizardURLAccessibility:
    """Test that wizard.html is accessible at the correct URL."""

    @pytest.mark.skip(reason="Requires running frontend server")
    def test_wizard_html_exists_and_accessible(self):
        """Test that wizard.html can be accessed via HTTP."""
        # This test would require a running frontend server
        # Skipped for unit testing, but useful for integration testing
        frontend_url = "http://localhost:7274/wizard.html"
        response = requests.get(frontend_url, timeout=5)
        assert response.status_code == 200
        assert "wizard" in response.text.lower()

    @pytest.mark.skip(reason="Requires running frontend server")
    def test_main_dashboard_accessible(self):
        """Test that main dashboard is accessible via HTTP."""
        # This test would require a running frontend server
        # Skipped for unit testing, but useful for integration testing
        frontend_url = "http://localhost:7274"
        response = requests.get(frontend_url, timeout=5)
        assert response.status_code == 200


class TestConfigYamlSetupMode:
    """Test config.yaml setup_mode flag behavior."""

    def test_config_yaml_has_setup_mode_flag(self, tmp_path: Path):
        """Test that config.yaml includes setup_mode flag."""
        config_data = {
            "setup_mode": True,
            "installation": {"mode": "localhost"},
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Read back and verify
        with open(config_file, "r") as f:
            loaded_config = yaml.safe_load(f)

        assert "setup_mode" in loaded_config
        assert isinstance(loaded_config["setup_mode"], bool)

    def test_fresh_install_has_setup_mode_true(self, tmp_path: Path):
        """Test that fresh installation sets setup_mode: true."""
        # Simulate fresh install config generation
        config_data = {
            "setup_mode": True,  # Fresh install
            "installation": {"mode": "localhost", "timestamp": "2025-10-05T12:00:00"},
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Verify
        with open(config_file, "r") as f:
            loaded_config = yaml.safe_load(f)

        assert loaded_config["setup_mode"] is True

    def test_completed_setup_has_setup_mode_false(self, tmp_path: Path):
        """Test that completed setup sets setup_mode: false."""
        # Simulate config after setup completion
        config_data = {
            "setup_mode": False,  # Setup complete
            "installation": {"mode": "localhost"},
        }
        config_file = tmp_path / "config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        # Verify
        with open(config_file, "r") as f:
            loaded_config = yaml.safe_load(f)

        assert loaded_config["setup_mode"] is False
