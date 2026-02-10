"""
Depth Controls Unit Tests - Handover 0314 (Updated for 0347d, 0347e)

Tests for Context Management v2.0 depth configuration system.
Controls HOW MUCH detail to extract from each context source.

Test Coverage:
- Pydantic schema validation (DepthConfig)
- Valid depth options per field
- Invalid depth values rejection
- GET endpoint (returns defaults for new users)
- PUT endpoint (updates depth config)
- WebSocket event emission
- Multi-tenant isolation

TDD Discipline: Tests written FIRST (RED phase)

Updated for schema changes in Handovers 0347d, 0347e:
- vision_chunking -> vision_documents (none/optional/light/medium/full)
- agent_template_detail -> agent_templates (type_only/full)
- git_commits now includes 5 as valid option
"""

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from api.endpoints.users import DepthConfig, UpdateDepthConfigRequest


# ============================================================================
# TEST SUITE 1: Pydantic Schema Validation
# ============================================================================


class TestDepthConfigValidation:
    """Test Pydantic schema validation for DepthConfig"""

    def test_valid_depth_config_defaults(self):
        """Test that default depth configuration is valid"""
        config = DepthConfig()
        # Updated field names per 0347d, 0347e
        assert config.vision_documents == "medium"
        assert config.memory_last_n_projects == 3
        assert config.git_commits == 25
        assert config.agent_templates == "type_only"
        assert config.tech_stack_sections == "all"
        assert config.architecture_depth == "overview"

    def test_valid_depth_config_all_options(self):
        """Test valid depth configuration with all fields specified"""
        valid_config = {
            "vision_documents": "full",  # Updated field name
            "memory_last_n_projects": 10,
            "git_commits": 100,
            "agent_templates": "full",  # Updated field name
            "tech_stack_sections": "required",
            "architecture_depth": "detailed",
        }
        config = DepthConfig(**valid_config)
        assert config.vision_documents == "full"
        assert config.memory_last_n_projects == 10
        assert config.git_commits == 100
        assert config.agent_templates == "full"
        assert config.tech_stack_sections == "required"
        assert config.architecture_depth == "detailed"

    def test_invalid_vision_documents_value(self):
        """Test that invalid vision_documents value is rejected"""
        invalid_config = {
            "vision_documents": "ultra",  # Invalid - must be none/optional/light/medium/full
            "memory_last_n_projects": 3,
        }
        with pytest.raises(ValidationError):
            DepthConfig(**invalid_config)

    def test_invalid_memory_last_n_projects_value(self):
        """Test that invalid memory_last_n_projects value is rejected"""
        invalid_config = {
            "vision_documents": "medium",
            "memory_last_n_projects": 7,  # Invalid - must be 1/3/5/10
        }
        with pytest.raises(ValidationError):
            DepthConfig(**invalid_config)

    def test_invalid_git_commits_value(self):
        """Test that invalid git_commits value is rejected"""
        invalid_config = {
            "vision_documents": "medium",
            "git_commits": 75,  # Invalid - must be 5/10/25/50/100
        }
        with pytest.raises(ValidationError):
            DepthConfig(**invalid_config)

    def test_invalid_agent_templates_value(self):
        """Test that invalid agent_templates value is rejected"""
        invalid_config = {
            "agent_templates": "verbose"  # Invalid - must be type_only/full
        }
        with pytest.raises(ValidationError):
            DepthConfig(**invalid_config)

    def test_invalid_tech_stack_sections_value(self):
        """Test that invalid tech_stack_sections value is rejected"""
        invalid_config = {"tech_stack_sections": "some"}  # Invalid - must be required/all
        with pytest.raises(ValidationError):
            DepthConfig(**invalid_config)

    def test_invalid_architecture_depth_value(self):
        """Test that invalid architecture_depth value is rejected"""
        invalid_config = {
            "architecture_depth": "comprehensive"  # Invalid - must be overview/detailed
        }
        with pytest.raises(ValidationError):
            DepthConfig(**invalid_config)

    def test_update_depth_config_request_structure(self):
        """Test UpdateDepthConfigRequest wrapper schema"""
        depth_config = DepthConfig()
        request = UpdateDepthConfigRequest(depth_config=depth_config)
        assert request.depth_config.vision_documents == "medium"

    def test_valid_vision_documents_options(self):
        """Test all valid vision_documents options (0347e)"""
        for option in ["none", "optional", "light", "medium", "full"]:
            config = DepthConfig(vision_documents=option)
            assert config.vision_documents == option

    def test_valid_agent_templates_options(self):
        """Test all valid agent_templates options (0347d)"""
        for option in ["type_only", "full"]:
            config = DepthConfig(agent_templates=option)
            assert config.agent_templates == option

    def test_valid_git_commits_includes_five(self):
        """Test git_commits accepts 5 as valid option"""
        config = DepthConfig(git_commits=5)
        assert config.git_commits == 5


# ============================================================================
# TEST SUITE 3: API Endpoints
# ============================================================================


@pytest.mark.asyncio
class TestDepthConfigEndpoints:
    """Test depth configuration API endpoints"""

    async def test_get_depth_config_returns_defaults(self, api_client: AsyncClient, auth_headers: dict):
        """Test GET /me/context/depth returns default configuration for new users"""
        response = await api_client.get("/api/v1/users/me/context/depth", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "depth_config" in data

        # Verify default values (updated field names per 0347d, 0347e)
        depth_config = data["depth_config"]
        assert depth_config["vision_documents"] == "medium"
        assert depth_config["memory_last_n_projects"] == 3
        assert depth_config["git_commits"] == 25
        assert depth_config["agent_templates"] == "type_only"
        assert depth_config["tech_stack_sections"] == "all"
        assert depth_config["architecture_depth"] == "overview"

    async def test_put_depth_config_updates_successfully(self, api_client: AsyncClient, auth_headers: dict):
        """Test PUT /me/context/depth updates depth configuration"""
        new_config = {
            "depth_config": {
                "vision_documents": "full",
                "memory_last_n_projects": 5,
                "git_commits": 50,
                "agent_templates": "full",
                "tech_stack_sections": "all",
                "architecture_depth": "detailed",
            }
        }

        response = await api_client.put("/api/v1/users/me/context/depth", headers=auth_headers, json=new_config)
        assert response.status_code == 200
        data = response.json()

        # Verify updated values
        assert data["depth_config"]["vision_documents"] == "full"
        assert data["depth_config"]["memory_last_n_projects"] == 5
        assert data["depth_config"]["git_commits"] == 50
        assert data["depth_config"]["agent_templates"] == "full"

    async def test_put_depth_config_persists_across_requests(self, api_client: AsyncClient, auth_headers: dict):
        """Test depth configuration persists in database"""
        # Update config
        new_config = {
            "depth_config": {
                "vision_documents": "light",
                "memory_last_n_projects": 1,
                "git_commits": 10,
                "agent_templates": "type_only",
                "tech_stack_sections": "required",
                "architecture_depth": "overview",
            }
        }

        await api_client.put("/api/v1/users/me/context/depth", headers=auth_headers, json=new_config)

        # Retrieve config in new request
        response = await api_client.get("/api/v1/users/me/context/depth", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()

        # Verify persisted values
        assert data["depth_config"]["vision_documents"] == "light"
        assert data["depth_config"]["memory_last_n_projects"] == 1
        assert data["depth_config"]["git_commits"] == 10

    async def test_put_depth_config_rejects_invalid_values(self, api_client: AsyncClient, auth_headers: dict):
        """Test PUT /me/context/depth rejects invalid depth values"""
        invalid_config = {
            "depth_config": {
                "vision_documents": "ultra",  # Invalid
                "memory_last_n_projects": 3,
            }
        }

        response = await api_client.put("/api/v1/users/me/context/depth", headers=auth_headers, json=invalid_config)
        assert response.status_code == 422  # Validation error

    async def test_depth_config_multi_tenant_isolation(
        self, api_client: AsyncClient, auth_headers_tenant_a: dict, auth_headers_tenant_b: dict
    ):
        """Test depth configurations are isolated between tenants"""
        # Tenant A sets config
        config_a = {
            "depth_config": {
                "vision_documents": "full",
                "memory_last_n_projects": 10,
                "git_commits": 100,
                "agent_templates": "full",
                "tech_stack_sections": "all",
                "architecture_depth": "detailed",
            }
        }

        await api_client.put("/api/v1/users/me/context/depth", headers=auth_headers_tenant_a, json=config_a)

        # Tenant B sets different config
        config_b = {
            "depth_config": {
                "vision_documents": "light",
                "memory_last_n_projects": 1,
                "git_commits": 10,
                "agent_templates": "type_only",
                "tech_stack_sections": "required",
                "architecture_depth": "overview",
            }
        }

        await api_client.put("/api/v1/users/me/context/depth", headers=auth_headers_tenant_b, json=config_b)

        # Verify Tenant A's config unchanged
        response_a = await api_client.get("/api/v1/users/me/context/depth", headers=auth_headers_tenant_a)
        assert response_a.json()["depth_config"]["vision_documents"] == "full"

        # Verify Tenant B's config
        response_b = await api_client.get("/api/v1/users/me/context/depth", headers=auth_headers_tenant_b)
        assert response_b.json()["depth_config"]["vision_documents"] == "light"


# ============================================================================
# TEST SUITE 4: WebSocket Event Emission
# ============================================================================
# NOTE: WebSocket tests are integration-level and require full app setup.
# These tests are SKIPPED in unit test suite and should be run in integration tests.
# See: tests/integration/test_websocket_events.py for real WebSocket testing.


@pytest.mark.skip(reason="WebSocket tests require full app setup - run in integration tests")
@pytest.mark.asyncio
class TestDepthConfigWebSocketEvents:
    """Test WebSocket event emission for depth config updates"""

    async def test_websocket_event_emitted_on_update(
        self, api_client: AsyncClient, auth_headers: dict, websocket_listener
    ):
        """Test that depth_config_updated WebSocket event is emitted"""
        new_config = {
            "depth_config": {
                "vision_documents": "full",
                "memory_last_n_projects": 5,
                "git_commits": 50,
                "agent_templates": "full",
                "tech_stack_sections": "all",
                "architecture_depth": "detailed",
            }
        }

        # Update config
        await api_client.put("/api/v1/users/me/context/depth", headers=auth_headers, json=new_config)

        # Verify WebSocket event received
        events = await websocket_listener.get_events("depth_config_updated")
        assert len(events) > 0

        event_data = events[0]
        assert event_data["depth_config"]["vision_documents"] == "full"

    async def test_websocket_event_includes_user_id(
        self, api_client: AsyncClient, auth_headers: dict, websocket_listener, test_user
    ):
        """Test WebSocket event includes user_id for filtering"""
        new_config = {
            "depth_config": {
                "vision_documents": "light",
                "memory_last_n_projects": 3,
                "git_commits": 25,
                "agent_templates": "type_only",
                "tech_stack_sections": "all",
                "architecture_depth": "overview",
            }
        }

        await api_client.put("/api/v1/users/me/context/depth", headers=auth_headers, json=new_config)

        events = await websocket_listener.get_events("depth_config_updated")
        assert events[0]["user_id"] == str(test_user.id)
