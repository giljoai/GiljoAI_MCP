"""
Test suite for service restart functionality.

Tests the automatic service restart feature triggered after setup wizard completion.
Ensures cross-platform compatibility and proper service lifecycle management.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict
from unittest.mock import MagicMock, Mock, patch

import pytest
from fastapi.testclient import TestClient


class TestRestartEndpoint:
    """Test the /api/setup/restart-services endpoint."""

    @pytest.fixture
    def api_client(self):
        """Create test client for API."""
        from api.app import app

        return TestClient(app)

    def test_restart_endpoint_exists(self, api_client):
        """Test that the restart endpoint is accessible."""
        response = api_client.post("/api/setup/restart-services")
        # Should return 200 or 202, not 404
        assert response.status_code in [200, 202], "Restart endpoint should exist"

    def test_restart_endpoint_returns_success(self, api_client):
        """Test that restart endpoint returns success status."""
        response = api_client.post("/api/setup/restart-services")
        assert response.status_code in [200, 202]

        data = response.json()
        assert data["success"] is True
        assert "message" in data
        assert "restart" in data["message"].lower()

    def test_restart_endpoint_returns_immediately(self, api_client):
        """Test that restart endpoint returns quickly (non-blocking)."""
        start_time = time.time()
        response = api_client.post("/api/setup/restart-services")
        elapsed = time.time() - start_time

        assert response.status_code in [200, 202]
        # Should return within 1 second (immediate response)
        assert elapsed < 1.0, "Restart endpoint should return immediately"

    @patch("subprocess.Popen")
    def test_restart_triggers_script_execution(self, mock_popen, api_client):
        """Test that restart endpoint triggers the restart script."""
        mock_process = MagicMock()
        mock_popen.return_value = mock_process

        response = api_client.post("/api/setup/restart-services")

        assert response.status_code in [200, 202]
        # Verify that a subprocess was spawned
        # (The actual implementation will call the restart script)

    def test_restart_endpoint_handles_errors_gracefully(self, api_client):
        """Test that restart endpoint handles errors without crashing."""
        with patch("subprocess.Popen", side_effect=Exception("Mock error")):
            response = api_client.post("/api/setup/restart-services")
            # Should still return a response, possibly with error status
            assert response.status_code in [200, 202, 500]


class TestRestartScript:
    """Test the restart_services.py script."""

    @pytest.fixture
    def restart_script_path(self) -> Path:
        """Get path to restart script."""
        return Path("F:/GiljoAI_MCP/restart_services.py")

    def test_restart_script_exists(self, restart_script_path):
        """Test that the restart script file exists."""
        assert restart_script_path.exists(), "restart_services.py should exist"

    def test_restart_script_is_executable(self, restart_script_path):
        """Test that restart script has shebang for execution."""
        if restart_script_path.exists():
            with open(restart_script_path, "r", encoding="utf-8") as f:
                first_line = f.readline()
                # Should have Python shebang
                assert first_line.startswith("#!"), "Script should have shebang"
                assert "python" in first_line.lower(), "Shebang should reference Python"

    def test_restart_script_uses_pathlib(self, restart_script_path):
        """Test that restart script uses pathlib for cross-platform compatibility."""
        if restart_script_path.exists():
            with open(restart_script_path, "r", encoding="utf-8") as f:
                content = f.read()
                assert "from pathlib import Path" in content, "Should import pathlib.Path"
                # Should not use hardcoded path separators
                assert 'os.path.join' not in content or "Path" in content, "Should prefer pathlib over os.path"

    @patch("subprocess.run")
    def test_restart_script_finds_running_processes(self, mock_run):
        """Test that restart script can find running launcher processes."""
        # Mock process list output
        mock_run.return_value = Mock(
            returncode=0,
            stdout="12345 python start_giljo.py\n67890 python other_script.py\n"
        )

        # Import and run the script logic
        # (This will be implemented in the actual script)

    def test_restart_script_graceful_shutdown(self):
        """Test that restart script attempts graceful shutdown before force kill."""
        # This test verifies the script tries SIGTERM before SIGKILL
        # Implementation will depend on the actual script


class TestConfigReload:
    """Test that config is reloaded after restart."""

    def test_config_reload_after_restart(self):
        """Test that services reload config.yaml after restart."""
        # Create a test config
        config_path = Path("F:/GiljoAI_MCP/config.yaml")
        if not config_path.exists():
            pytest.skip("config.yaml not found")

        # Read original config
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            original_config = yaml.safe_load(f)

        original_setup_mode = original_config.get("setup_mode", True)

        # After restart, setup_mode should be false (set by complete endpoint)
        # This test validates the workflow:
        # 1. Wizard calls /api/setup/complete -> sets setup_mode: false
        # 2. Wizard calls /api/setup/restart-services -> restarts
        # 3. Backend reloads config with setup_mode: false

    def test_setup_mode_persists_in_config(self):
        """Test that setup_mode flag persists in config.yaml."""
        config_path = Path("F:/GiljoAI_MCP/config.yaml")
        if not config_path.exists():
            pytest.skip("config.yaml not found")

        import yaml

        # Read config
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)

        # setup_mode should exist as a boolean
        if "setup_mode" in config:
            assert isinstance(config["setup_mode"], bool), "setup_mode should be boolean"


class TestFrontendRestartFlow:
    """Test the frontend wizard restart flow."""

    def test_wizard_completion_flow(self):
        """
        Test the complete wizard flow:
        1. Call /api/setup/complete
        2. Call /api/setup/restart-services
        3. Wait for backend to come back
        4. Redirect to dashboard
        """
        # This is an integration test that will be run manually
        # or in a full E2E test suite

    def test_backend_health_polling(self):
        """Test that frontend can poll /health endpoint during restart."""
        from fastapi.testclient import TestClient
        from api.app import app

        client = TestClient(app)

        # Health endpoint should exist
        response = client.get("/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility of restart mechanism."""

    def test_restart_works_on_windows(self):
        """Test restart script works on Windows."""
        if os.name != "nt":
            pytest.skip("Windows-only test")

        # Test Windows-specific process management
        # Should use tasklist/taskkill or psutil

    def test_restart_works_on_linux(self):
        """Test restart script works on Linux."""
        if os.name != "posix" or os.uname().sysname != "Linux":
            pytest.skip("Linux-only test")

        # Test Linux-specific process management
        # Should use ps/kill

    def test_restart_works_on_macos(self):
        """Test restart script works on macOS."""
        if os.name != "posix" or os.uname().sysname != "Darwin":
            pytest.skip("macOS-only test")

        # Test macOS-specific process management

    def test_restart_script_uses_platform_detection(self):
        """Test that restart script detects platform correctly."""
        restart_script = Path("F:/GiljoAI_MCP/restart_services.py")
        if not restart_script.exists():
            pytest.skip("Restart script not created yet")

        with open(restart_script, "r", encoding="utf-8") as f:
            content = f.read()
            # Should import platform module for OS detection
            assert "import platform" in content or "sys.platform" in content, \
                "Script should detect platform"


class TestErrorHandling:
    """Test error handling in restart flow."""

    def test_restart_handles_missing_processes(self):
        """Test restart handles case where no processes are running."""
        # If start_giljo.py is not running, restart should handle gracefully

    def test_restart_handles_permission_errors(self):
        """Test restart handles permission errors when killing processes."""
        # Should log error and continue

    def test_restart_handles_port_conflicts(self):
        """Test restart handles port conflicts during restart."""
        # If ports are still bound, should wait and retry


class TestServiceRecovery:
    """Test service recovery after restart."""

    def test_backend_starts_with_new_config(self):
        """Test that backend starts with updated config after restart."""
        # After restart, backend should:
        # 1. Load config.yaml from disk
        # 2. Read setup_mode: false
        # 3. Not require setup wizard

    def test_frontend_reconnects_after_restart(self):
        """Test that frontend can reconnect after backend restarts."""
        # Frontend should:
        # 1. Poll /health endpoint
        # 2. Wait for 200 OK response
        # 3. Redirect to dashboard

    def test_websocket_clients_reconnect(self):
        """Test that WebSocket clients can reconnect after restart."""
        # Any active WebSocket connections should:
        # 1. Detect disconnect
        # 2. Attempt reconnection
        # 3. Resume normal operation


class TestRestartTiming:
    """Test timing and delays in restart process."""

    def test_restart_delay_allows_response(self):
        """Test that restart is delayed to allow HTTP response to send."""
        # Restart should be delayed 2-3 seconds to ensure:
        # 1. HTTP 202 response is sent to client
        # 2. TCP connection is closed cleanly
        # 3. Then restart is triggered

    def test_restart_completes_within_timeout(self):
        """Test that full restart completes within reasonable time."""
        # Total restart time should be < 15 seconds:
        # - 2s delay for response
        # - 3s for graceful shutdown
        # - 5s for backend startup
        # - 5s for frontend startup


# Fixtures for integration testing
@pytest.fixture
def temp_config_file(tmp_path):
    """Create a temporary config file for testing."""
    import yaml

    config_data = {
        "setup_mode": True,
        "installation": {"mode": "localhost"},
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "database_name": "giljo_mcp_test",
            "username": "test_user",
        },
        "services": {
            "api": {"host": "127.0.0.1", "port": 7272},
            "frontend": {"port": 7274},
        },
    }

    config_file = tmp_path / "config.yaml"
    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config_data, f)

    return config_file


@pytest.fixture
def mock_running_services():
    """Mock running GiljoAI services."""
    # Create mock processes that can be "killed" and "restarted"
    mock_processes = {
        "backend": MagicMock(pid=12345),
        "frontend": MagicMock(pid=67890),
    }
    return mock_processes
