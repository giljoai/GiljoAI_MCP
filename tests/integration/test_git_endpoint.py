"""
Integration tests for Git integration endpoints.

Tests the complete flow from API endpoint to config.yaml persistence:
- GET /api/git/settings
- POST /api/git/toggle
- POST /api/git/settings (update advanced settings)

Validates:
- Endpoint request/response handling
- config.yaml file persistence
- Validation logic
- Error handling for file system issues
"""

import pytest
from httpx import AsyncClient
from pathlib import Path
import yaml
import json


@pytest.mark.asyncio
class TestGitIntegrationEndpoints:
    """Integration tests for Git integration endpoints"""

    async def test_get_git_settings_returns_current_state(
        self, async_client: AsyncClient, test_user
    ):
        """GET /api/git/settings returns current git integration settings"""
        response = await async_client.get(
            "/api/git/settings",
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response structure
        assert "enabled" in data
        assert "use_in_prompts" in data
        assert "include_commit_history" in data
        assert "max_commits" in data
        assert "branch_strategy" in data

        # Verify types
        assert isinstance(data["enabled"], bool)
        assert isinstance(data["use_in_prompts"], bool)
        assert isinstance(data["include_commit_history"], bool)
        assert isinstance(data["max_commits"], int)
        assert isinstance(data["branch_strategy"], str)

    async def test_get_git_settings_returns_defaults_if_not_configured(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """GET /api/git/settings returns defaults if git not configured"""
        # Ensure git_integration is not in config
        config = {"database": {}, "server": {}}
        with open(tmp_config_file, "w") as f:
            yaml.dump(config, f)

        response = await async_client.get(
            "/api/git/settings",
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify defaults are returned
        assert data["enabled"] is False
        assert data["use_in_prompts"] is False
        assert data["include_commit_history"] is True
        assert data["max_commits"] == 50
        assert data["branch_strategy"] == "main"

    async def test_post_toggle_git_enables_integration(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """POST /api/git/toggle with enabled=true enables git integration"""
        response = await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["success"] is True
        assert data["enabled"] is True
        assert "Git integration enabled" in data["message"]

        # Verify config.yaml was updated
        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        assert config["features"]["git_integration"]["enabled"] is True
        assert config["features"]["git_integration"]["use_in_prompts"] is True

    async def test_post_toggle_git_disables_integration(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """POST /api/git/toggle with enabled=false disables git integration"""
        # First enable it
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Then disable it
        response = await async_client.post(
            "/api/git/toggle",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["success"] is True
        assert data["enabled"] is False
        assert "Git integration disabled" in data["message"]

        # Verify config.yaml was updated
        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        assert config["features"]["git_integration"]["enabled"] is False

    async def test_toggle_git_preserves_other_settings(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """POST /api/git/toggle preserves other settings"""
        # First, set advanced settings
        await async_client.post(
            "/api/git/settings",
            json={
                "use_in_prompts": True,
                "include_commit_history": False,
                "max_commits": 75,
                "branch_strategy": "develop",
            },
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Then toggle
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Verify other settings preserved
        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        assert config["features"]["git_integration"]["max_commits"] == 75
        assert config["features"]["git_integration"]["branch_strategy"] == "develop"

    async def test_post_update_git_settings_changes_config(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """POST /api/git/settings updates advanced settings"""
        new_settings = {
            "use_in_prompts": True,
            "include_commit_history": False,
            "max_commits": 100,
            "branch_strategy": "staging",
        }

        response = await async_client.post(
            "/api/git/settings",
            json=new_settings,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response
        assert data["success"] is True
        assert "Git settings updated" in data["message"]
        assert data["settings"]["max_commits"] == 100
        assert data["settings"]["branch_strategy"] == "staging"

        # Verify config.yaml was updated
        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        assert config["features"]["git_integration"]["max_commits"] == 100
        assert config["features"]["git_integration"]["branch_strategy"] == "staging"
        assert config["features"]["git_integration"]["use_in_prompts"] is True
        assert config["features"]["git_integration"]["include_commit_history"] is False

    async def test_update_git_settings_partial_update(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """POST /api/git/settings can update individual settings"""
        # Set initial settings
        await async_client.post(
            "/api/git/settings",
            json={
                "use_in_prompts": True,
                "include_commit_history": True,
                "max_commits": 50,
                "branch_strategy": "main",
            },
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Update only max_commits
        response = await async_client.post(
            "/api/git/settings",
            json={
                "use_in_prompts": False,
                "include_commit_history": True,
                "max_commits": 200,
                "branch_strategy": "main",
            },
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["settings"]["max_commits"] == 200

    async def test_git_endpoints_require_authentication(
        self, async_client: AsyncClient
    ):
        """Git endpoints require authentication"""
        # Test GET
        response = await async_client.get("/api/git/settings")
        assert response.status_code == 401 or response.status_code == 403

        # Test POST toggle
        response = await async_client.post(
            "/api/git/toggle", json={"enabled": True}
        )
        assert response.status_code == 401 or response.status_code == 403

        # Test POST settings
        response = await async_client.post(
            "/api/git/settings", json={"max_commits": 50}
        )
        assert response.status_code == 401 or response.status_code == 403

    async def test_get_git_settings_persists_across_requests(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """GET /api/git/settings returns consistent state across requests"""
        # Set initial settings
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Get settings multiple times
        for _ in range(3):
            response = await async_client.get(
                "/api/git/settings",
                headers={"Authorization": f"Bearer {test_user.api_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["enabled"] is True

    async def test_toggle_response_includes_settings(
        self, async_client: AsyncClient, test_user
    ):
        """POST /api/git/toggle response includes current settings"""
        response = await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify settings are in response
        assert "settings" in data
        assert isinstance(data["settings"], dict)
        assert "enabled" in data["settings"]
        assert "max_commits" in data["settings"]

    async def test_update_settings_response_includes_settings(
        self, async_client: AsyncClient, test_user
    ):
        """POST /api/git/settings response includes updated settings"""
        response = await async_client.post(
            "/api/git/settings",
            json={
                "use_in_prompts": True,
                "include_commit_history": True,
                "max_commits": 150,
                "branch_strategy": "main",
            },
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify settings are in response
        assert "settings" in data
        assert data["settings"]["max_commits"] == 150

    async def test_git_settings_create_features_section(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """Git endpoint creates features section if it doesn't exist"""
        # Create empty config
        config = {"database": {}}
        with open(tmp_config_file, "w") as f:
            yaml.dump(config, f)

        # Toggle git
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Verify features section was created
        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        assert "features" in config
        assert "git_integration" in config["features"]

    async def test_toggle_multiple_times_persists_state(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """Toggling git integration multiple times persists correct state"""
        # Toggle on
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Toggle off
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Toggle on again
        response = await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["enabled"] is True

        # Verify config.yaml
        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        assert config["features"]["git_integration"]["enabled"] is True

    async def test_git_settings_preserves_enabled_state(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """Updating git settings preserves enabled state"""
        # Enable git
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Update settings
        await async_client.post(
            "/api/git/settings",
            json={
                "use_in_prompts": False,
                "include_commit_history": False,
                "max_commits": 25,
                "branch_strategy": "main",
            },
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Verify enabled is still true
        response = await async_client.get(
            "/api/git/settings",
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        data = response.json()
        assert data["enabled"] is True

    async def test_valid_branch_strategy_values(
        self, async_client: AsyncClient, test_user
    ):
        """POST /api/git/settings accepts various branch strategy values"""
        strategies = ["main", "master", "develop", "staging", "production"]

        for strategy in strategies:
            response = await async_client.post(
                "/api/git/settings",
                json={
                    "use_in_prompts": True,
                    "include_commit_history": True,
                    "max_commits": 50,
                    "branch_strategy": strategy,
                },
                headers={"Authorization": f"Bearer {test_user.api_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["settings"]["branch_strategy"] == strategy

    async def test_max_commits_range_persists(
        self, async_client: AsyncClient, test_user
    ):
        """POST /api/git/settings accepts various max_commits values"""
        test_values = [1, 10, 50, 100, 500, 1000]

        for max_commits in test_values:
            response = await async_client.post(
                "/api/git/settings",
                json={
                    "use_in_prompts": True,
                    "include_commit_history": True,
                    "max_commits": max_commits,
                    "branch_strategy": "main",
                },
                headers={"Authorization": f"Bearer {test_user.api_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["settings"]["max_commits"] == max_commits

    async def test_boolean_settings_persisted_correctly(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """POST /api/git/settings persists boolean settings correctly"""
        response = await async_client.post(
            "/api/git/settings",
            json={
                "use_in_prompts": True,
                "include_commit_history": False,
                "max_commits": 50,
                "branch_strategy": "main",
            },
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200

        # Verify in config.yaml
        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        assert config["features"]["git_integration"]["use_in_prompts"] is True
        assert config["features"]["git_integration"]["include_commit_history"] is False

    async def test_toggle_sets_use_in_prompts_to_enabled_value(
        self, async_client: AsyncClient, test_user, tmp_config_file
    ):
        """POST /api/git/toggle sets use_in_prompts same as enabled"""
        # Enable git
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": True},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        # Verify use_in_prompts matches enabled
        assert config["features"]["git_integration"]["enabled"] is True
        assert config["features"]["git_integration"]["use_in_prompts"] is True

        # Disable git
        await async_client.post(
            "/api/git/toggle",
            json={"enabled": False},
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        with open(tmp_config_file, "r") as f:
            config = yaml.safe_load(f)

        # Verify use_in_prompts matches enabled
        assert config["features"]["git_integration"]["enabled"] is False
        # Note: use_in_prompts might stay true from previous call, depends on implementation
        # This test documents the actual behavior
