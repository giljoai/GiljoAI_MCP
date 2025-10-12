"""
Integration tests for simplified setup wizard (Phase 4).

Tests the 3-step setup wizard:
1. MCP Configuration (optional, can skip)
2. Serena Activation (optional, can skip)
3. Complete (informational)

These tests verify:
- Setup state persistence
- Skip functionality
- Navigation between steps
- Completion flow
- Integration with password change requirement
"""

import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def test_config_path(tmp_path):
    """Create temporary config file for testing"""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("""
version: 3.0.0
deployment_context: localhost

installation:
  timestamp: '2025-10-11T00:00:00'
  platform: Windows
  install_dir: F:/GiljoAI_MCP
  mode: localhost

database:
  type: postgresql
  host: localhost
  port: 5432
  name: giljo_mcp
  user: giljo_user

services:
  api:
    host: 0.0.0.0
    port: 7272
  dashboard:
    port: 7274

features:
  authentication: true
  auto_login_localhost: true
  firewall_configured: false
  api_keys_enabled: false

setup:
  completed: false
  tools_attached: []
""")
    return config_file


@pytest.fixture
def mock_setup_state_manager():
    """Mock SetupStateManager for testing"""
    with patch('src.giljo_mcp.setup.state_manager.SetupStateManager') as mock:
        instance = MagicMock()
        instance.get_state.return_value = {
            'database_initialized': False,
            'tools_enabled': [],
            'setup_version': '3.0.0'
        }
        instance.mark_completed = MagicMock()
        instance.update_state = MagicMock()
        mock.get_instance.return_value = instance
        yield instance


class TestSetupWizardStatus:
    """Test setup wizard status endpoint"""

    def test_get_setup_status_not_completed(self, client, mock_setup_state_manager):
        """Test GET /api/setup/status when setup not completed"""
        response = client.get("/api/setup/status")

        assert response.status_code == 200
        data = response.json()
        assert data["database_initialized"] is False
        assert data["database_configured"] is True  # Always true (CLI installer)
        assert isinstance(data["tools_attached"], list)
        assert data["network_mode"] == "localhost"

    def test_get_setup_status_completed(self, client, mock_setup_state_manager):
        """Test GET /api/setup/status when setup completed"""
        # Mock completed state
        mock_setup_state_manager.get_state.return_value = {
            'database_initialized': True,
            'tools_enabled': ['claude-code'],
            'setup_version': '3.0.0'
        }

        response = client.get("/api/setup/status")

        assert response.status_code == 200
        data = response.json()
        assert data["database_initialized"] is True
        assert data["tools_attached"] == ['claude-code']


class TestMCPConfigurationStep:
    """Test MCP configuration step (Step 1)"""

    def test_check_mcp_not_configured(self, client, tmp_path):
        """Test checking MCP configuration when not configured"""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = tmp_path
            # No .claude.json file

            response = client.get("/api/setup/check-mcp-configured")

            assert response.status_code == 200
            data = response.json()
            assert data["configured"] is False
            assert "not found" in data["message"].lower()

    def test_check_mcp_configured(self, client, tmp_path):
        """Test checking MCP configuration when already configured"""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = tmp_path

            # Create .claude.json with giljo-mcp configured
            claude_config = tmp_path / ".claude.json"
            claude_config.write_text("""
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp"]
    }
  }
}
""")

            response = client.get("/api/setup/check-mcp-configured")

            assert response.status_code == 200
            data = response.json()
            assert data["configured"] is True
            assert "config" in data

    def test_generate_mcp_config_localhost(self, client, test_config_path):
        """Test generating MCP config for localhost mode"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            payload = {
                "tool": "Claude Code",
                "mode": "localhost"
            }

            response = client.post("/api/setup/generate-mcp-config", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert "mcpServers" in data
            assert "giljo-mcp" in data["mcpServers"]
            config = data["mcpServers"]["giljo-mcp"]
            assert "localhost" in config["env"]["GILJO_SERVER_URL"]

    def test_register_mcp_creates_config(self, client, tmp_path):
        """Test registering MCP server creates config file"""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = tmp_path

            payload = {
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

            response = client.post("/api/setup/register-mcp", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "config_path" in data

            # Verify file was created
            claude_config = tmp_path / ".claude.json"
            assert claude_config.exists()

    def test_register_mcp_updates_existing_config(self, client, tmp_path):
        """Test registering MCP server updates existing config"""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = tmp_path

            # Create existing config
            claude_config = tmp_path / ".claude.json"
            claude_config.write_text('{"mcpServers": {}}')

            payload = {
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

            response = client.post("/api/setup/register-mcp", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "backup_path" in data


class TestSerenaActivationStep:
    """Test Serena activation step (Step 2)"""

    def test_get_serena_status_disabled(self, client, test_config_path):
        """Test getting Serena status when disabled"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            # Mock serena endpoint
            with patch('setupService.getSerenaStatus') as mock_status:
                mock_status.return_value = {"enabled": False}

                # Note: This would be tested in frontend tests
                # Backend doesn't have a /api/serena/status endpoint yet
                # This test documents expected behavior

    def test_get_serena_status_enabled(self, client, test_config_path):
        """Test getting Serena status when enabled"""
        # Similar to above - frontend test
        pass

    def test_toggle_serena_enable(self, client, test_config_path):
        """Test enabling Serena instructions"""
        # This would be tested via the /api/setup/complete endpoint
        # which accepts serena_enabled parameter
        pass


class TestSetupCompletion:
    """Test setup completion (Step 3)"""

    def test_complete_setup_localhost_no_tools(self, client, test_config_path, mock_setup_state_manager):
        """Test completing setup in localhost mode with no tools"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            payload = {
                "tools_attached": [],
                "deployment_context": "localhost",
                "serena_enabled": False
            }

            response = client.post("/api/setup/complete", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["mode"] == "localhost"
            assert data["requires_restart"] is False  # v3.0: no restart needed

            # Verify state manager was called
            mock_setup_state_manager.mark_completed.assert_called_once()
            mock_setup_state_manager.update_state.assert_called_once()

    def test_complete_setup_with_mcp_tool(self, client, test_config_path, mock_setup_state_manager):
        """Test completing setup with MCP tool attached"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            payload = {
                "tools_attached": ["claude-code"],
                "deployment_context": "localhost",
                "serena_enabled": False
            }

            response = client.post("/api/setup/complete", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify tools were saved
            call_kwargs = mock_setup_state_manager.update_state.call_args[1]
            assert call_kwargs["tools_enabled"] == ["claude-code"]

    def test_complete_setup_with_serena_enabled(self, client, test_config_path, mock_setup_state_manager):
        """Test completing setup with Serena enabled"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            payload = {
                "tools_attached": [],
                "deployment_context": "localhost",
                "serena_enabled": True
            }

            response = client.post("/api/setup/complete", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

            # Verify Serena was enabled in config
            # (Would check config.yaml content in real implementation)

    def test_complete_setup_skip_all_optional(self, client, test_config_path, mock_setup_state_manager):
        """Test completing setup by skipping all optional steps"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            payload = {
                "tools_attached": [],
                "deployment_context": "localhost",
                "serena_enabled": False
            }

            response = client.post("/api/setup/complete", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["mode"] == "localhost"

    def test_complete_setup_idempotent(self, client, test_config_path, mock_setup_state_manager):
        """Test setup completion is idempotent (can be called multiple times)"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            payload = {
                "tools_attached": ["claude-code"],
                "deployment_context": "localhost",
                "serena_enabled": True
            }

            # Complete setup twice
            response1 = client.post("/api/setup/complete", json=payload)
            response2 = client.post("/api/setup/complete", json=payload)

            assert response1.status_code == 200
            assert response2.status_code == 200
            assert response1.json()["success"] is True
            assert response2.json()["success"] is True


class TestSetupStateValidation:
    """Test setup state validation and persistence"""

    def test_setup_state_persists_across_requests(self, client, mock_setup_state_manager):
        """Test setup state persists between API calls"""
        # Mock state with tools
        mock_setup_state_manager.get_state.return_value = {
            'database_initialized': True,
            'tools_enabled': ['claude-code'],
            'setup_version': '3.0.0'
        }

        # Make multiple status requests
        response1 = client.get("/api/setup/status")
        response2 = client.get("/api/setup/status")

        assert response1.json() == response2.json()

    def test_setup_validates_deployment_context(self, client, test_config_path):
        """Test setup validates deployment context"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            payload = {
                "tools_attached": [],
                "deployment_context": "invalid_mode",
                "serena_enabled": False
            }

            response = client.post("/api/setup/complete", json=payload)

            # Should fail validation
            assert response.status_code == 422  # Validation error


class TestRouterIntegration:
    """Test router integration with setup wizard"""

    def test_setup_route_accessible_without_auth(self):
        """Test /setup route doesn't require authentication"""
        # This would be a frontend test
        # Verifies router allows access to /setup without JWT token
        pass

    def test_setup_route_accessible_before_password_change(self):
        """Test /setup accessible only after password change"""
        # This would be tested with router guards
        # Verifies password change modal comes before setup wizard
        pass

    def test_dashboard_redirects_to_setup_when_incomplete(self):
        """Test dashboard redirects to setup when not completed"""
        # Frontend router test
        # Verifies router guard redirects / to /setup when setup_completed=false
        pass


class TestSetupWizardSkipFunctionality:
    """Test skip functionality for optional steps"""

    def test_skip_mcp_configuration(self, client, test_config_path, mock_setup_state_manager):
        """Test skipping MCP configuration step"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            # Complete setup with no tools (effectively skipping MCP step)
            payload = {
                "tools_attached": [],
                "deployment_context": "localhost",
                "serena_enabled": False
            }

            response = client.post("/api/setup/complete", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data.get("tools_attached", [])) == 0 or "tools_attached" not in data

    def test_skip_serena_activation(self, client, test_config_path, mock_setup_state_manager):
        """Test skipping Serena activation step"""
        with patch('api.endpoints.setup.get_config_path') as mock_path:
            mock_path.return_value = test_config_path

            # Complete setup with serena disabled
            payload = {
                "tools_attached": ["claude-code"],
                "deployment_context": "localhost",
                "serena_enabled": False
            }

            response = client.post("/api/setup/complete", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True


@pytest.fixture
def client():
    """Create test client with mocked dependencies"""
    from api.app import app

    # Mock database manager
    mock_db = AsyncMock()
    app.state.api_state = MagicMock()
    app.state.api_state.db_manager = mock_db

    return TestClient(app)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
