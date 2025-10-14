"""
Tests for AI tools configuration generator API endpoints.

Following TDD: These tests are written BEFORE implementation.
They define the expected behavior of the AI tool config generator API.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestAIToolConfigGeneratorEndpoint:
    """Test /api/ai-tools/config-generator/{tool_name} endpoint."""

    def test_config_generator_requires_valid_tool_name(self, api_client):
        """Test that endpoint requires a valid tool name."""
        response = api_client.get("/api/ai-tools/config-generator/invalid_tool")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
        assert "not supported" in data["detail"].lower() or "unknown" in data["detail"].lower()

    def test_generate_config_for_claude_code(self, api_client):
        """Test MCP config generation for Claude Code."""
        response = api_client.get("/api/ai-tools/config-generator/claude")

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "tool" in data
        assert data["tool"] == "claude"
        assert "config_format" in data
        assert data["config_format"] == "json"
        assert "config_content" in data
        assert "file_location" in data
        assert "instructions" in data
        assert "download_filename" in data

        # Verify config content structure
        config = json.loads(data["config_content"])
        assert "mcpServers" in config
        assert "giljo-mcp" in config["mcpServers"]

        # Verify server config
        server_config = config["mcpServers"]["giljo-mcp"]
        assert "command" in server_config
        assert "args" in server_config
        assert "env" in server_config

        # Verify environment variables
        assert "GILJO_SERVER_URL" in server_config["env"]
        server_url = server_config["env"]["GILJO_SERVER_URL"]
        assert "://" in server_url  # Should be a valid URL

        # Verify file location
        assert "~/.claude.json" in data["file_location"] or ".claude.json" in data["file_location"]

        # Verify instructions
        assert isinstance(data["instructions"], list)
        assert len(data["instructions"]) > 0

        # Verify download filename
        assert data["download_filename"].endswith(".md")
        assert "claude" in data["download_filename"].lower()

    def test_generate_config_uses_current_server_url(self, api_client):
        """Test that config uses the actual server URL from config."""
        response = api_client.get("/api/ai-tools/config-generator/claude")

        assert response.status_code == 200
        data = response.json()

        config = json.loads(data["config_content"])
        server_url = config["mcpServers"]["giljo-mcp"]["env"]["GILJO_SERVER_URL"]

        # Should use localhost or actual IP based on server configuration
        assert "localhost" in server_url or "127.0.0.1" in server_url or "192.168." in server_url or "10." in server_url

    def test_generate_config_includes_tenant_key(self, api_client, mock_user):
        """Test that config includes user's tenant key in environment."""
        # Mock authenticated user
        with patch('api.endpoints.ai_tools.get_current_active_user', return_value=mock_user):
            response = api_client.get(
                "/api/ai-tools/config-generator/claude",
                headers={"Authorization": "Bearer fake_token"}
            )

            assert response.status_code == 200
            data = response.json()

            config = json.loads(data["config_content"])
            env = config["mcpServers"]["giljo-mcp"]["env"]

            # Tenant key should be in environment
            assert "GILJO_TENANT_KEY" in env
            assert env["GILJO_TENANT_KEY"] == mock_user.tenant_key

    def test_generate_config_for_codex(self, api_client):
        """Test MCP config generation for CODEX."""
        response = api_client.get("/api/ai-tools/config-generator/codex")

        assert response.status_code == 200
        data = response.json()

        assert data["tool"] == "codex"
        # CODEX might use YAML or JSON format
        assert data["config_format"] in ["json", "yaml"]
        assert "config_content" in data
        assert "file_location" in data
        assert "instructions" in data

    def test_generate_config_for_gemini(self, api_client):
        """Test MCP config generation for Gemini."""
        response = api_client.get("/api/ai-tools/config-generator/gemini")

        assert response.status_code == 200
        data = response.json()

        assert data["tool"] == "gemini"
        assert "config_content" in data
        assert "file_location" in data
        assert "instructions" in data

    def test_config_includes_cross_platform_paths(self, api_client):
        """Test that config uses cross-platform path handling."""
        response = api_client.get("/api/ai-tools/config-generator/claude")

        assert response.status_code == 200
        data = response.json()

        # File location should use ~ for home directory (cross-platform)
        file_location = data["file_location"]
        assert "~" in file_location or "%USERPROFILE%" in file_location or "$HOME" in file_location

        # Should not have hardcoded Windows or Unix paths
        assert not file_location.startswith("C:\\")
        assert not file_location.startswith("/home/")

    def test_config_instructions_are_clear(self, api_client):
        """Test that instructions are clear and actionable."""
        response = api_client.get("/api/ai-tools/config-generator/claude")

        assert response.status_code == 200
        data = response.json()

        instructions = data["instructions"]

        # Should have multiple steps
        assert len(instructions) >= 3

        # Each instruction should be a non-empty string
        for instruction in instructions:
            assert isinstance(instruction, str)
            assert len(instruction) > 0

        # Should mention key steps
        instructions_text = " ".join(instructions).lower()
        assert "file" in instructions_text or "config" in instructions_text
        assert "restart" in instructions_text or "reload" in instructions_text

    def test_config_download_filename_format(self, api_client):
        """Test that download filename follows consistent format."""
        response = api_client.get("/api/ai-tools/config-generator/claude")

        assert response.status_code == 200
        data = response.json()

        filename = data["download_filename"]

        # Should be a markdown file
        assert filename.endswith(".md")

        # Should include tool name
        assert "claude" in filename.lower() or "giljo" in filename.lower()

        # Should not have spaces (use hyphens or underscores)
        assert " " not in filename

    def test_config_handles_network_deployment(self, api_client):
        """Test that config adapts to LAN deployment mode."""
        # Mock LAN configuration
        with patch('api.endpoints.ai_tools.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.services.api.host = "192.168.1.100"
            mock_config.services.api.port = 7272
            mock_get_config.return_value = mock_config

            response = api_client.get("/api/ai-tools/config-generator/claude")

            assert response.status_code == 200
            data = response.json()

            config = json.loads(data["config_content"])
            server_url = config["mcpServers"]["giljo-mcp"]["env"]["GILJO_SERVER_URL"]

            # Should use the LAN IP
            assert "192.168.1.100" in server_url

    def test_config_includes_authentication_if_required(self, api_client, mock_user):
        """Test that config includes API key or auth token if needed."""
        with patch('api.endpoints.ai_tools.get_current_active_user', return_value=mock_user):
            response = api_client.get(
                "/api/ai-tools/config-generator/claude",
                headers={"Authorization": "Bearer fake_token"}
            )

            assert response.status_code == 200
            data = response.json()

            config = json.loads(data["config_content"])
            env = config["mcpServers"]["giljo-mcp"]["env"]

            # Should include tenant key for authentication
            assert "GILJO_TENANT_KEY" in env

    def test_multiple_tool_configs_are_consistent(self, api_client):
        """Test that different tools follow consistent response structure."""
        tools = ["claude", "codex", "gemini"]
        responses = []

        for tool in tools:
            response = api_client.get(f"/api/ai-tools/config-generator/{tool}")
            if response.status_code == 200:
                responses.append(response.json())

        # All successful responses should have same structure
        assert len(responses) > 0

        required_fields = ["tool", "config_format", "config_content", "file_location", "instructions", "download_filename"]

        for data in responses:
            for field in required_fields:
                assert field in data

    def test_config_validates_json_format(self, api_client):
        """Test that JSON config content is valid JSON."""
        response = api_client.get("/api/ai-tools/config-generator/claude")

        assert response.status_code == 200
        data = response.json()

        if data["config_format"] == "json":
            # Should be parseable JSON
            config = json.loads(data["config_content"])
            assert isinstance(config, dict)

    def test_config_includes_tool_specific_settings(self, api_client):
        """Test that each tool gets tool-specific configuration."""
        response = api_client.get("/api/ai-tools/config-generator/claude")

        assert response.status_code == 200
        data = response.json()

        config = json.loads(data["config_content"])

        # Claude-specific: Should have command and args for Python
        server_config = config["mcpServers"]["giljo-mcp"]
        assert server_config["command"] == "python" or server_config["command"] == "python3"
        assert "-m" in server_config["args"]
        assert "giljo_mcp" in " ".join(server_config["args"])

    def test_unauthorized_access_handled_gracefully(self, api_client):
        """Test that unauthorized access returns appropriate response."""
        # Try to access without authentication (if auth is required)
        response = api_client.get("/api/ai-tools/config-generator/claude")

        # Should either succeed (public endpoint) or return 401
        assert response.status_code in [200, 401]

        if response.status_code == 401:
            data = response.json()
            assert "detail" in data

    def test_config_handles_custom_ports(self, api_client):
        """Test that config adapts to custom API ports."""
        with patch('api.endpoints.ai_tools.get_config') as mock_get_config:
            mock_config = MagicMock()
            mock_config.services.api.host = "localhost"
            mock_config.services.api.port = 8888
            mock_get_config.return_value = mock_config

            response = api_client.get("/api/ai-tools/config-generator/claude")

            assert response.status_code == 200
            data = response.json()

            config = json.loads(data["config_content"])
            server_url = config["mcpServers"]["giljo-mcp"]["env"]["GILJO_SERVER_URL"]

            # Should use custom port
            assert "8888" in server_url


class TestAIToolsList:
    """Test listing supported AI tools."""

    def test_list_supported_tools(self, api_client):
        """Test endpoint that lists all supported AI tools."""
        response = api_client.get("/api/ai-tools/supported")

        assert response.status_code == 200
        data = response.json()

        assert "tools" in data
        assert isinstance(data["tools"], list)
        assert len(data["tools"]) > 0

        # Each tool should have required fields
        for tool in data["tools"]:
            assert "id" in tool
            assert "name" in tool
            assert "config_format" in tool
            assert "supported" in tool

    def test_supported_tools_include_claude(self, api_client):
        """Test that Claude Code is in supported tools list."""
        response = api_client.get("/api/ai-tools/supported")

        assert response.status_code == 200
        data = response.json()

        tool_ids = [tool["id"] for tool in data["tools"]]
        assert "claude" in tool_ids


# Pytest fixtures
@pytest.fixture
def api_client():
    """Create FastAPI test client."""
    from fastapi.testclient import TestClient

    try:
        from api.app import app
        return TestClient(app)
    except ImportError:
        pytest.skip("API app not available - implementation pending")


@pytest.fixture
def mock_user():
    """Mock authenticated user for testing."""
    from unittest.mock import MagicMock

    user = MagicMock()
    user.id = "test-user-123"
    user.username = "testuser"
    user.tenant_key = "test-tenant-456"
    user.role = "developer"

    return user


@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    config = MagicMock()
    config.services.api.host = "localhost"
    config.services.api.port = 7272
    config.services.external_host = "localhost"

    return config
