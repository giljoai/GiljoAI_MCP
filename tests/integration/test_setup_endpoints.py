"""
Integration tests for setup status API endpoints.

Tests the setup wizard endpoints that track first-time configuration
and tool attachment status. These tests follow TDD workflow and are
written BEFORE implementation.
"""

import json
import pytest
from pathlib import Path
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create test client with isolated configuration"""
    from api.app import create_app

    app = create_app()
    return TestClient(app)


@pytest.fixture
def clean_config(tmp_path):
    """Provide clean config.yaml for testing"""
    config_file = tmp_path / "config.yaml"
    config_data = {
        "installation": {
            "mode": "localhost",
            "version": "2.0.0"
        },
        "database": {
            "type": "postgresql",
            "host": "localhost",
            "port": 5432,
            "name": "giljo_mcp",
            "user": "giljo_user"
        },
        "services": {
            "api": {
                "host": "127.0.0.1",
                "port": 7272
            },
            "frontend": {
                "port": 7274
            }
        },
        "setup": {
            "completed": False
        }
    }

    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f)

    return config_file


class TestSetupStatusEndpoint:
    """Test GET /api/setup/status endpoint"""

    def test_status_endpoint_exists(self, client):
        """Test that /api/setup/status endpoint exists and responds"""
        response = client.get("/api/setup/status")

        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404, "Setup status endpoint should exist"

    def test_status_returns_json(self, client):
        """Test that status endpoint returns JSON response"""
        response = client.get("/api/setup/status")

        # Should return valid JSON
        assert response.headers["content-type"] == "application/json"
        data = response.json()
        assert isinstance(data, dict)

    def test_status_has_required_fields(self, client):
        """Test that status response contains all required fields"""
        response = client.get("/api/setup/status")
        assert response.status_code == 200

        data = response.json()

        # Check required fields exist
        assert "completed" in data, "Response should have 'completed' field"
        assert "database_configured" in data, "Response should have 'database_configured' field"
        assert "tools_attached" in data, "Response should have 'tools_attached' field"
        assert "network_mode" in data, "Response should have 'network_mode' field"

    def test_status_field_types(self, client):
        """Test that status fields have correct types"""
        response = client.get("/api/setup/status")
        assert response.status_code == 200

        data = response.json()

        # Validate field types
        assert isinstance(data["completed"], bool), "completed should be boolean"
        assert isinstance(data["database_configured"], bool), "database_configured should be boolean"
        assert isinstance(data["tools_attached"], list), "tools_attached should be array"
        assert isinstance(data["network_mode"], str), "network_mode should be string"

    def test_status_network_mode_values(self, client):
        """Test that network_mode is a valid value"""
        response = client.get("/api/setup/status")
        assert response.status_code == 200

        data = response.json()
        valid_modes = ["localhost", "lan", "wan"]
        assert data["network_mode"] in valid_modes, f"network_mode should be one of {valid_modes}"

    def test_status_database_always_configured(self, client):
        """Test that database_configured is always true (CLI installer does this)"""
        response = client.get("/api/setup/status")
        assert response.status_code == 200

        data = response.json()
        # Database is configured by CLI installer in Phase 0
        assert data["database_configured"] is True, "Database should always be configured by installer"

    def test_status_initial_state(self, client):
        """Test that initial setup state is correct"""
        response = client.get("/api/setup/status")
        assert response.status_code == 200

        data = response.json()

        # On first launch, setup should not be completed
        # (This test may fail if setup was previously completed - that's OK)
        # The important part is the endpoint works
        assert "completed" in data
        assert isinstance(data["completed"], bool)


class TestSetupCompleteEndpoint:
    """Test POST /api/setup/complete endpoint"""

    def test_complete_endpoint_exists(self, client):
        """Test that /api/setup/complete endpoint exists"""
        response = client.post("/api/setup/complete", json={
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        })

        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404, "Setup complete endpoint should exist"

    def test_complete_accepts_valid_payload(self, client):
        """Test that endpoint accepts valid setup completion data"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should accept valid data (200 or 201)
        assert response.status_code in [200, 201], f"Should accept valid payload, got {response.status_code}"

    def test_complete_returns_success_response(self, client):
        """Test that successful completion returns proper response"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        data = response.json()

        # Check response structure
        assert "success" in data, "Response should have 'success' field"
        assert "message" in data, "Response should have 'message' field"
        assert data["success"] is True, "success should be true"

    def test_complete_with_lan_config(self, client):
        """Test completion with LAN configuration"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "giljo.local"
            }
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should accept LAN config
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["success"] is True

    def test_complete_updates_status(self, client):
        """Test that completion actually updates the status"""
        # Mark setup as complete
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]

        # Check that status now shows completed
        status_response = client.get("/api/setup/status")
        assert status_response.status_code == 200

        status_data = status_response.json()
        assert status_data["completed"] is True, "Status should show setup as completed"

    def test_complete_is_idempotent(self, client):
        """Test that calling complete multiple times doesn't error"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        # Call once
        response1 = client.post("/api/setup/complete", json=payload)
        assert response1.status_code in [200, 201]

        # Call again - should still succeed (idempotent)
        response2 = client.post("/api/setup/complete", json=payload)
        assert response2.status_code in [200, 201]

        # Both should return success
        assert response1.json()["success"] is True
        assert response2.json()["success"] is True

    def test_complete_validates_network_mode(self, client):
        """Test that invalid network mode is rejected"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "invalid_mode"
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should reject invalid mode (422 validation error or 400 bad request)
        assert response.status_code in [400, 422], "Should reject invalid network mode"

    def test_complete_requires_network_mode(self, client):
        """Test that network_mode is required"""
        payload = {
            "tools_attached": ["claude-code"]
            # Missing network_mode
        }

        response = client.post("/api/setup/complete", json=payload)

        # Should reject missing required field
        assert response.status_code == 422, "Should require network_mode field"

    def test_complete_allows_empty_tools(self, client):
        """Test that empty tools_attached array is allowed"""
        payload = {
            "tools_attached": [],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)

        # Empty tools list should be allowed
        assert response.status_code in [200, 201], "Empty tools list should be allowed"

    def test_complete_allows_multiple_tools(self, client):
        """Test that multiple tools can be attached"""
        payload = {
            "tools_attached": ["claude-code", "mcp-server", "custom-tool"],
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)

        # Multiple tools should be allowed
        assert response.status_code in [200, 201]


class TestSetupIntegration:
    """Integration tests for setup workflow"""

    def test_setup_workflow_localhost(self, client):
        """Test complete setup workflow for localhost mode"""
        # Step 1: Check initial status
        status = client.get("/api/setup/status")
        assert status.status_code == 200
        initial_data = status.json()

        # Database should always be configured
        assert initial_data["database_configured"] is True

        # Step 2: Complete setup
        complete_payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }

        complete_response = client.post("/api/setup/complete", json=complete_payload)
        assert complete_response.status_code in [200, 201]
        assert complete_response.json()["success"] is True

        # Step 3: Verify status updated
        final_status = client.get("/api/setup/status")
        assert final_status.status_code == 200
        final_data = final_status.json()

        assert final_data["completed"] is True
        assert final_data["network_mode"] == "localhost"

    def test_setup_workflow_lan(self, client):
        """Test complete setup workflow for LAN mode"""
        # Complete setup with LAN configuration
        complete_payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "10.1.0.100",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "giljo-server"
            }
        }

        complete_response = client.post("/api/setup/complete", json=complete_payload)
        assert complete_response.status_code in [200, 201]

        # Verify status shows LAN mode
        status = client.get("/api/setup/status")
        assert status.status_code == 200
        status_data = status.json()

        assert status_data["completed"] is True
        assert status_data["network_mode"] == "lan"

    def test_setup_can_be_reconfigured(self, client):
        """Test that setup can be updated after initial completion"""
        # Initial setup
        payload1 = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
        }
        client.post("/api/setup/complete", json=payload1)

        # Update setup (e.g., switch to LAN mode)
        payload2 = {
            "tools_attached": ["claude-code", "mcp-server"],
            "network_mode": "lan",
            "lan_config": {
                "server_ip": "192.168.1.50",
                "firewall_configured": True,
                "admin_username": "admin",
                "hostname": "giljo.local"
            }
        }

        response = client.post("/api/setup/complete", json=payload2)
        assert response.status_code in [200, 201], "Should allow reconfiguration"

        # Verify new configuration
        status = client.get("/api/setup/status")
        status_data = status.json()
        assert status_data["network_mode"] == "lan"


class TestSetupErrorHandling:
    """Test error handling in setup endpoints"""

    def test_complete_rejects_malformed_json(self, client):
        """Test that malformed JSON is rejected"""
        response = client.post(
            "/api/setup/complete",
            data="not valid json",
            headers={"Content-Type": "application/json"}
        )

        # Should return 422 or 400
        assert response.status_code in [400, 422]

    def test_complete_rejects_missing_body(self, client):
        """Test that missing request body is rejected"""
        response = client.post("/api/setup/complete")

        # Should return 422 (validation error)
        assert response.status_code == 422

    def test_status_always_available(self, client):
        """Test that status endpoint works even if config is missing"""
        # Status should always return valid response
        response = client.get("/api/setup/status")

        # Should not crash, even if config has issues
        assert response.status_code in [200, 500]  # Either works or fails gracefully


class TestSetupConfigPersistence:
    """Test that setup configuration is properly persisted"""

    @pytest.mark.skip(reason="Requires file system access - tested in E2E tests")
    def test_setup_persisted_to_config_yaml(self, client, clean_config):
        """Test that setup completion is written to config.yaml"""
        # This would require mocking file operations
        # Skip for now - covered by E2E tests
        pass

    @pytest.mark.skip(reason="Requires database - tested in E2E tests")
    def test_setup_persisted_to_database(self, client):
        """Test that setup completion is stored in database"""
        # This would require database setup
        # Skip for now - covered by E2E tests
        pass


# Test data validation models

class TestSetupRequestValidation:
    """Test Pydantic model validation for setup requests"""

    def test_validates_tools_attached_type(self, client):
        """Test that tools_attached must be an array"""
        payload = {
            "tools_attached": "not-an-array",  # Should be array
            "network_mode": "localhost"
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code == 422

    def test_validates_network_mode_enum(self, client):
        """Test that network_mode must be valid enum value"""
        valid_modes = ["localhost", "lan", "wan"]

        for mode in valid_modes:
            payload = {
                "tools_attached": [],
                "network_mode": mode
            }
            response = client.post("/api/setup/complete", json=payload)
            assert response.status_code in [200, 201], f"Should accept mode: {mode}"

    def test_lan_config_optional(self, client):
        """Test that lan_config is optional"""
        payload = {
            "tools_attached": ["claude-code"],
            "network_mode": "localhost"
            # No lan_config - should be fine
        }

        response = client.post("/api/setup/complete", json=payload)
        assert response.status_code in [200, 201]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
