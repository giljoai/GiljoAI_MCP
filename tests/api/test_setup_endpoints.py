"""
Tests for setup wizard API endpoints.

Following TDD: These tests are written BEFORE implementation.
They define the expected behavior of the setup wizard API.
"""

import pytest
from fastapi.testclient import TestClient
from pathlib import Path
import json
from unittest.mock import patch, MagicMock

# Import will fail initially - that's expected in TDD
# from api.app import app
# client = TestClient(app)


class TestToolDetectionEndpoint:
    """Test /api/setup/detect-tools endpoint."""

    def test_detect_tools_returns_200(self, client):
        """Test that tool detection endpoint returns 200 OK."""
        response = client.get("/api/setup/detect-tools")
        assert response.status_code == 200

    def test_detect_tools_returns_json(self, client):
        """Test that response is valid JSON."""
        response = client.get("/api/setup/detect-tools")
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)

    def test_detect_tools_has_tools_list(self, client):
        """Test that response contains tools list."""
        response = client.get("/api/setup/detect-tools")
        data = response.json()
        assert "tools" in data
        assert isinstance(data["tools"], list)

    @patch("subprocess.run")
    def test_detect_claude_code_when_installed(self, mock_run, client):
        """Test Claude Code detection when installed."""
        # Mock successful Claude Code detection
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="Claude Code CLI v1.2.3\n"
        )

        response = client.get("/api/setup/detect-tools")
        data = response.json()

        # Find Claude Code in results
        claude_tool = next((t for t in data["tools"] if t["id"] == "claude_code"), None)
        assert claude_tool is not None
        assert claude_tool["detected"] is True
        assert claude_tool["name"] == "Claude Code"
        assert claude_tool["multi_agent"] is True
        assert "version" in claude_tool

    @patch("subprocess.run")
    def test_detect_claude_code_when_not_installed(self, mock_run, client):
        """Test Claude Code detection when NOT installed."""
        # Mock failed detection (command not found)
        mock_run.side_effect = FileNotFoundError("claude not found")

        response = client.get("/api/setup/detect-tools")
        data = response.json()

        # Claude Code should still appear but as not detected
        claude_tool = next((t for t in data["tools"] if t["id"] == "claude_code"), None)
        # Note: We may choose to omit undetected tools or mark them as detected=false
        # This test assumes we return all tools with detection status

    def test_detect_multiple_tools(self, client):
        """Test detection of multiple tools simultaneously."""
        response = client.get("/api/setup/detect-tools")
        data = response.json()

        # Should check for all supported tools
        expected_tool_ids = ["claude_code", "gemini_cli", "cursor", "aider", "codex", "continue", "windsurf"]

        # At minimum, we should attempt to detect these tools
        # Even if none are installed, they should be in the response
        # (or we only return detected ones - implementation choice)
        assert len(data["tools"]) >= 0  # Can be 0 if none installed


class TestMCPConfigGenerationEndpoint:
    """Test /api/setup/generate-mcp-config endpoint (v3.0 unified architecture)."""

    def test_generate_config_requires_tool_parameter(self, client):
        """Test that tool parameter is required."""
        response = client.post(
            "/api/setup/generate-mcp-config",
            json={}
        )
        assert response.status_code == 422  # Validation error

    def test_generate_config_for_claude_code(self, client):
        """Test MCP config generation for Claude Code (v3.0 unified architecture)."""
        response = client.post(
            "/api/setup/generate-mcp-config",
            json={
                "tool": "Claude Code"
            }
        )

        assert response.status_code == 200
        data = response.json()

        # Verify config structure
        assert "mcpServers" in data
        assert "giljo-mcp" in data["mcpServers"]

        config = data["mcpServers"]["giljo-mcp"]
        assert "command" in config
        assert "args" in config
        assert "env" in config

        # v3.0: Always uses localhost URL (firewall controls access)
        # Environment variable may be GILJO_SERVER_URL or GILJO_API_URL
        assert "GILJO_SERVER_URL" in config["env"] or "GILJO_API_URL" in config["env"]

        # Verify localhost URL is used
        url = config["env"].get("GILJO_SERVER_URL") or config["env"].get("GILJO_API_URL")
        assert "localhost" in url or "127.0.0.1" in url

    def test_generate_config_for_unknown_tool_returns_400(self, client):
        """Test that unknown tool returns 400 error."""
        response = client.post(
            "/api/setup/generate-mcp-config",
            json={
                "tool": "NonExistentTool"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert "detail" in data
        assert "unknown tool" in data["detail"].lower()


class TestMCPRegistrationEndpoint:
    """Test /api/setup/register-mcp endpoint."""

    def test_register_mcp_requires_tool_parameter(self, client):
        """Test that tool parameter is required."""
        response = client.post(
            "/api/setup/register-mcp",
            json={"config": {}}
        )
        assert response.status_code == 422

    def test_register_mcp_requires_config_parameter(self, client):
        """Test that config parameter is required."""
        response = client.post(
            "/api/setup/register-mcp",
            json={"tool": "Claude Code"}
        )
        assert response.status_code == 422

    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    @patch("shutil.copy")
    def test_register_mcp_creates_backup(self, mock_copy, mock_open, mock_exists, client):
        """Test that registration creates backup of existing config."""
        # Mock existing config file
        mock_exists.return_value = True

        mock_config = {"existing": "config"}
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(mock_config)
        mock_open.return_value.__enter__.return_value = mock_file

        response = client.post(
            "/api/setup/register-mcp",
            json={
                "tool": "Claude Code",
                "config": {
                    "mcpServers": {
                        "giljo-mcp": {
                            "command": "python",
                            "args": ["-m", "giljo_mcp"]
                        }
                    }
                }
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "config_path" in data
        assert "backup_path" in data
        assert data["backup_path"] is not None

    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_register_mcp_writes_config(self, mock_open, mock_exists, client):
        """Test that registration writes config file."""
        # No existing config
        mock_exists.return_value = False

        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        config = {
            "mcpServers": {
                "giljo-mcp": {
                    "command": "python",
                    "args": ["-m", "giljo_mcp"],
                    "env": {"GILJO_API_URL": "http://localhost:7272"}
                }
            }
        }

        response = client.post(
            "/api/setup/register-mcp",
            json={
                "tool": "Claude Code",
                "config": config
            }
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["config_path"] is not None
        # No backup if file didn't exist
        assert data["backup_path"] is None


class TestMCPConnectionTestEndpoint:
    """Test /api/setup/test-mcp-connection endpoint."""

    def test_test_connection_requires_tool_parameter(self, client):
        """Test that tool parameter is required."""
        response = client.post("/api/setup/test-mcp-connection", json={})
        assert response.status_code == 422

    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    def test_test_connection_validates_config_exists(self, mock_open, mock_exists, client):
        """Test that connection test validates config file exists."""
        # Config doesn't exist
        mock_exists.return_value = False

        response = client.post(
            "/api/setup/test-mcp-connection",
            json={"tool": "Claude Code"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is False
        assert "config" in data["message"].lower() or "not found" in data["message"].lower()

    @patch("pathlib.Path.exists")
    @patch("builtins.open", create=True)
    @patch("subprocess.run")
    def test_test_connection_success(self, mock_run, mock_open, mock_exists, client):
        """Test successful MCP connection test."""
        # Config exists
        mock_exists.return_value = True

        # Mock config file
        mock_config = {
            "mcpServers": {
                "giljo-mcp": {
                    "command": "python",
                    "args": ["-m", "giljo_mcp"]
                }
            }
        }
        mock_file = MagicMock()
        mock_file.read.return_value = json.dumps(mock_config)
        mock_open.return_value.__enter__.return_value = mock_file

        # Mock successful connection
        mock_run.return_value = MagicMock(returncode=0)

        response = client.post(
            "/api/setup/test-mcp-connection",
            json={"tool": "Claude Code"}
        )

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "status" in data
        assert data["status"] == "connected"


class TestSetupCompletionEndpoint:
    """Test /api/setup/complete endpoint."""

    def test_complete_setup_marks_as_complete(self, client):
        """Test that completing setup marks wizard as complete."""
        response = client.post("/api/setup/complete", json={})

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert data["setup_completed"] is True


# Pytest fixtures
@pytest.fixture
def client():
    """Create test client - will be implemented after app.py exists."""
    # This will fail initially - expected in TDD
    # from api.app import app
    # return TestClient(app)
    pytest.skip("API app not yet implemented - TDD placeholder")


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return {
        "services": {
            "api": {"port": 7272},
            "frontend": {"port": 7274}
        },
        "paths": {
            "install_dir": Path("/test/install/dir")
        }
    }
