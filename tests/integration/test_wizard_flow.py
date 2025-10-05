"""
Integration tests for the complete setup wizard flow.

Following TDD: These tests define the expected end-to-end behavior.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
from unittest.mock import patch, MagicMock


class TestCompleteWizardFlow:
    """Test the complete wizard flow from start to finish."""

    def test_wizard_flow_localhost_with_claude_code(self, client, db_session):
        """
        Test complete wizard flow:
        1. Detect tools (Claude Code found)
        2. Generate MCP config for localhost
        3. Register MCP config
        4. Test connection
        5. Mark setup complete
        """

        # Step 1: Detect tools
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0,
                stdout="Claude Code CLI v1.2.3\n"
            )

            detect_response = client.get("/api/setup/detect-tools")
            assert detect_response.status_code == 200

            tools = detect_response.json()["tools"]
            claude_tool = next((t for t in tools if t["id"] == "claude_code"), None)
            assert claude_tool is not None
            assert claude_tool["detected"] is True

        # Step 2: Generate MCP config
        config_response = client.post(
            "/api/setup/generate-mcp-config",
            json={
                "tool": "Claude Code",
                "mode": "localhost"
            }
        )
        assert config_response.status_code == 200

        mcp_config = config_response.json()
        assert "mcpServers" in mcp_config
        assert "giljo-mcp" in mcp_config["mcpServers"]

        # Step 3: Register MCP config
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("builtins.open", create=True) as mock_open, \
             patch("shutil.copy") as mock_copy:

            mock_exists.return_value = False  # No existing config
            mock_file = MagicMock()
            mock_open.return_value.__enter__.return_value = mock_file

            register_response = client.post(
                "/api/setup/register-mcp",
                json={
                    "tool": "Claude Code",
                    "config": mcp_config
                }
            )
            assert register_response.status_code == 200

            register_data = register_response.json()
            assert register_data["success"] is True

        # Step 4: Test MCP connection
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("builtins.open", create=True) as mock_open, \
             patch("subprocess.run") as mock_run:

            mock_exists.return_value = True
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(mcp_config)
            mock_open.return_value.__enter__.return_value = mock_file
            mock_run.return_value = MagicMock(returncode=0)

            test_response = client.post(
                "/api/setup/test-mcp-connection",
                json={"tool": "Claude Code"}
            )
            assert test_response.status_code == 200

            test_data = test_response.json()
            assert test_data["success"] is True
            assert test_data["status"] == "connected"

        # Step 5: Mark setup complete
        complete_response = client.post("/api/setup/complete")
        assert complete_response.status_code == 200

        complete_data = complete_response.json()
        assert complete_data["success"] is True
        assert complete_data["setup_completed"] is True

    def test_wizard_flow_lan_deployment(self, client, db_session):
        """
        Test wizard flow for LAN deployment:
        1. Configure LAN mode
        2. Detect tools
        3. Generate LAN MCP config
        4. Register with API key
        5. Test connection
        6. Complete
        """

        # Step 1: Configure LAN deployment mode
        mode_response = client.post(
            "/api/setup/configure-deployment-mode",
            json={
                "mode": "lan",
                "lan_ip": "192.168.1.100"
            }
        )
        assert mode_response.status_code == 200

        mode_data = mode_response.json()
        assert mode_data["mode"] == "lan"
        assert "192.168.1.100" in mode_data["api_url"]

        # Step 2-5: Similar to localhost but with LAN config
        config_response = client.post(
            "/api/setup/generate-mcp-config",
            json={
                "tool": "Claude Code",
                "mode": "lan"
            }
        )
        assert config_response.status_code == 200

        mcp_config = config_response.json()
        giljo_config = mcp_config["mcpServers"]["giljo-mcp"]

        # Verify LAN-specific config
        assert "GILJO_API_KEY" in giljo_config["env"]
        assert "192.168.1.100" in giljo_config["env"]["GILJO_API_URL"]

    def test_wizard_flow_no_tools_detected(self, client, db_session):
        """
        Test wizard flow when no tools are detected:
        - Should still allow manual selection
        - Should still generate config
        - Should warn user about tool installation
        """

        # Mock no tools detected
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            detect_response = client.get("/api/setup/detect-tools")
            assert detect_response.status_code == 200

            tools = detect_response.json()["tools"]
            detected_tools = [t for t in tools if t.get("detected", False)]
            assert len(detected_tools) == 0

        # User can still manually select a tool
        config_response = client.post(
            "/api/setup/generate-mcp-config",
            json={
                "tool": "Claude Code",
                "mode": "localhost"
            }
        )
        assert config_response.status_code == 200

        # Config should be generated even if tool not detected
        mcp_config = config_response.json()
        assert "mcpServers" in mcp_config

    def test_wizard_flow_with_existing_config_backup(self, client, db_session):
        """
        Test that wizard backs up existing MCP config.
        """

        existing_config = {
            "mcpServers": {
                "other-server": {
                    "command": "other"
                }
            }
        }

        with patch("pathlib.Path.exists") as mock_exists, \
             patch("builtins.open", create=True) as mock_open, \
             patch("shutil.copy") as mock_copy:

            # Mock existing config file
            mock_exists.return_value = True
            mock_file = MagicMock()
            mock_file.read.return_value = json.dumps(existing_config)
            mock_open.return_value.__enter__.return_value = mock_file

            # Register new config
            new_config = {
                "mcpServers": {
                    "giljo-mcp": {
                        "command": "python",
                        "args": ["-m", "giljo_mcp"]
                    }
                }
            }

            register_response = client.post(
                "/api/setup/register-mcp",
                json={
                    "tool": "Claude Code",
                    "config": new_config
                }
            )

            assert register_response.status_code == 200
            register_data = register_response.json()

            # Verify backup was created
            assert register_data["backup_path"] is not None
            assert ".backup_" in register_data["backup_path"]

            # Verify shutil.copy was called for backup
            mock_copy.assert_called_once()

    def test_wizard_flow_database_connection_test(self, client, db_session):
        """
        Test database connection verification step in wizard.
        """

        # This endpoint will be part of the wizard
        # Testing that database is accessible before proceeding
        db_test_response = client.get("/api/setup/test-database")
        assert db_test_response.status_code == 200

        db_data = db_test_response.json()
        assert "success" in db_data
        assert "database" in db_data
        assert "host" in db_data


class TestWizardErrorHandling:
    """Test error handling in wizard flow."""

    def test_generate_config_with_invalid_mode(self, client):
        """Test error when invalid deployment mode provided."""
        response = client.post(
            "/api/setup/generate-mcp-config",
            json={
                "tool": "Claude Code",
                "mode": "invalid_mode"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "mode" in data["detail"].lower()

    def test_register_mcp_write_permission_error(self, client):
        """Test error when unable to write config file."""
        with patch("builtins.open", create=True) as mock_open:
            mock_open.side_effect = PermissionError("Access denied")

            response = client.post(
                "/api/setup/register-mcp",
                json={
                    "tool": "Claude Code",
                    "config": {"mcpServers": {}}
                }
            )

            assert response.status_code == 500
            data = response.json()
            assert "permission" in data["detail"].lower()

    def test_connection_test_with_invalid_config(self, client):
        """Test connection test with malformed config file."""
        with patch("pathlib.Path.exists") as mock_exists, \
             patch("builtins.open", create=True) as mock_open:

            mock_exists.return_value = True
            mock_file = MagicMock()
            mock_file.read.return_value = "invalid json"
            mock_open.return_value.__enter__.return_value = mock_file

            response = client.post(
                "/api/setup/test-mcp-connection",
                json={"tool": "Claude Code"}
            )

            assert response.status_code == 500
            data = response.json()
            assert "config" in data["detail"].lower() or "json" in data["detail"].lower()


# Pytest fixtures
@pytest.fixture
def client():
    """Create test client."""
    # Will be implemented after main.py exists
    pytest.skip("API app not yet implemented - TDD placeholder")


@pytest.fixture
def db_session():
    """Create test database session."""
    # Will be implemented with actual database setup
    pytest.skip("Database session not yet implemented - TDD placeholder")
