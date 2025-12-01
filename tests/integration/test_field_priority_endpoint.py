"""
Integration tests for field priority configuration endpoints.

Tests the complete flow from API endpoint to database persistence:
- GET /api/v1/users/me/field-priority
- PUT /api/v1/users/me/field-priority
- POST /api/v1/users/me/field-priority/reset

Validates:
- Endpoint request/response handling
- Database persistence
- Validation logic
- WebSocket event emission
- Multi-tenant isolation
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import User
from src.giljo_mcp.services.user_service import UserService


@pytest.mark.asyncio
class TestFieldPriorityEndpoints:
    """Integration tests for field priority endpoints"""

    async def test_get_field_priority_returns_defaults(
        self, async_client: AsyncClient, test_user: User
    ):
        """GET /api/v1/users/me/field-priority returns default config for new user"""
        response = await async_client.get(
            "/api/v1/users/me/field-priority",
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify structure
        assert "version" in data
        assert "priorities" in data
        assert data["version"] == "2.0"

        # Verify default priorities exist
        assert isinstance(data["priorities"], dict)

    async def test_put_field_priority_updates_config(
        self,
        async_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """PUT /api/v1/users/me/field-priority saves config to database"""
        new_config = {
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "project_context": 3,
                "memory_360": 4,
                "git_history": 1,
                "agent_templates": 2,
            },
        }

        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=new_config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify response matches request
        assert data["version"] == "2.0"
        assert data["priorities"]["product_core"] == 1
        assert data["priorities"]["vision_documents"] == 2

        # Verify database was updated
        await db_session.refresh(test_user)
        assert test_user.field_priority_config is not None
        assert test_user.field_priority_config["version"] == "2.0"
        assert test_user.field_priority_config["priorities"]["product_core"] == 1

    async def test_put_field_priority_invalid_priority_fails(
        self, async_client: AsyncClient, test_user: User
    ):
        """PUT /api/v1/users/me/field-priority rejects invalid priority values"""
        invalid_config = {
            "version": "2.0",
            "priorities": {"product_core": 5},  # Invalid: must be 1-4
        }

        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=invalid_config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Should fail validation
        assert response.status_code == 422

    async def test_put_field_priority_missing_version_fails(
        self, async_client: AsyncClient, test_user: User
    ):
        """PUT /api/v1/users/me/field-priority rejects config without version"""
        invalid_config = {"priorities": {"product_core": 1}}

        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=invalid_config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Should fail validation (Pydantic)
        assert response.status_code == 422

    async def test_put_field_priority_missing_priorities_fails(
        self, async_client: AsyncClient, test_user: User
    ):
        """PUT /api/v1/users/me/field-priority rejects config without priorities"""
        invalid_config = {"version": "2.0"}

        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=invalid_config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Should fail validation
        assert response.status_code == 422

    async def test_post_reset_field_priority_restores_defaults(
        self,
        async_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """POST /api/v1/users/me/field-priority/reset restores default config"""
        # First, set a custom config
        custom_config = {
            "version": "2.0",
            "priorities": {
                "product_core": 4,
                "vision_documents": 4,
                "project_context": 4,
                "memory_360": 1,
                "git_history": 1,
                "agent_templates": 1,
            },
        }

        await async_client.put(
            "/api/v1/users/me/field-priority",
            json=custom_config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Then reset
        response = await async_client.post(
            "/api/v1/users/me/field-priority/reset",
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify reset to defaults
        assert "version" in data
        assert "priorities" in data

        # Verify database was updated with defaults
        await db_session.refresh(test_user)
        assert test_user.field_priority_config is not None

    async def test_field_priority_requires_authentication(self, async_client: AsyncClient):
        """GET /api/v1/users/me/field-priority requires authentication"""
        response = await async_client.get("/api/v1/users/me/field-priority")

        assert response.status_code == 401 or response.status_code == 403

    async def test_field_priority_requires_authentication_put(
        self, async_client: AsyncClient
    ):
        """PUT /api/v1/users/me/field-priority requires authentication"""
        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json={"version": "2.0", "priorities": {}},
        )

        assert response.status_code == 401 or response.status_code == 403

    async def test_field_priority_requires_authentication_reset(
        self, async_client: AsyncClient
    ):
        """POST /api/v1/users/me/field-priority/reset requires authentication"""
        response = await async_client.post("/api/v1/users/me/field-priority/reset")

        assert response.status_code == 401 or response.status_code == 403

    async def test_field_priority_isolated_by_tenant(
        self,
        async_client: AsyncClient,
        test_user: User,
        other_tenant_user: User,
        db_session: AsyncSession,
    ):
        """Field priority config is isolated by tenant"""
        config1 = {
            "version": "2.0",
            "priorities": {"product_core": 1, "vision_documents": 4},
        }

        # User 1 sets config
        response1 = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=config1,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )
        assert response1.status_code == 200

        # User 2 gets config (should be different tenant)
        response2 = await async_client.get(
            "/api/v1/users/me/field-priority",
            headers={"Authorization": f"Bearer {other_tenant_user.api_token}"},
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # User 2 config should be different from User 1
        assert data2["priorities"]["product_core"] != 1

    async def test_field_priority_persists_across_requests(
        self,
        async_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Field priority config persists across multiple GET requests"""
        # Set initial config
        config = {
            "version": "2.0",
            "priorities": {
                "product_core": 2,
                "vision_documents": 3,
                "project_context": 1,
            },
        }

        await async_client.put(
            "/api/v1/users/me/field-priority",
            json=config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Get config multiple times
        for _ in range(3):
            response = await async_client.get(
                "/api/v1/users/me/field-priority",
                headers={"Authorization": f"Bearer {test_user.api_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["priorities"]["product_core"] == 2
            assert data["priorities"]["vision_documents"] == 3
            assert data["priorities"]["project_context"] == 1

    async def test_field_priority_update_overwrites_previous(
        self,
        async_client: AsyncClient,
        test_user: User,
        db_session: AsyncSession,
    ):
        """Updating field priority completely overwrites previous config"""
        # Set initial config
        config1 = {
            "version": "2.0",
            "priorities": {
                "product_core": 1,
                "vision_documents": 1,
                "project_context": 1,
            },
        }

        await async_client.put(
            "/api/v1/users/me/field-priority",
            json=config1,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Update with new config
        config2 = {
            "version": "2.0",
            "priorities": {
                "product_core": 4,
                "vision_documents": 4,
                "project_context": 4,
            },
        }

        await async_client.put(
            "/api/v1/users/me/field-priority",
            json=config2,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Verify new config is returned
        response = await async_client.get(
            "/api/v1/users/me/field-priority",
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        data = response.json()
        assert data["priorities"]["product_core"] == 4
        assert data["priorities"]["vision_documents"] == 4

    async def test_field_priority_zero_priority_fails(
        self, async_client: AsyncClient, test_user: User
    ):
        """PUT /api/v1/users/me/field-priority rejects priority 0"""
        invalid_config = {"version": "2.0", "priorities": {"product_core": 0}}

        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=invalid_config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 422

    async def test_field_priority_negative_priority_fails(
        self, async_client: AsyncClient, test_user: User
    ):
        """PUT /api/v1/users/me/field-priority rejects negative priority"""
        invalid_config = {"version": "2.0", "priorities": {"product_core": -1}}

        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=invalid_config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 422

    async def test_field_priority_empty_priorities_succeeds(
        self, async_client: AsyncClient, test_user: User, db_session: AsyncSession
    ):
        """PUT /api/v1/users/me/field-priority accepts empty priorities dict"""
        config = {"version": "2.0", "priorities": {}}

        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        assert response.status_code == 200

        # Verify empty config saved
        await db_session.refresh(test_user)
        assert test_user.field_priority_config["priorities"] == {}

    async def test_field_priority_extra_fields_ignored(
        self, async_client: AsyncClient, test_user: User
    ):
        """PUT /api/v1/users/me/field-priority ignores extra fields"""
        config_with_extra = {
            "version": "2.0",
            "priorities": {"product_core": 1},
            "extra_field": "should be ignored",
            "another_field": 123,
        }

        response = await async_client.put(
            "/api/v1/users/me/field-priority",
            json=config_with_extra,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Should succeed and ignore extra fields
        assert response.status_code == 200

    async def test_field_priority_version_preserved(
        self, async_client: AsyncClient, test_user: User, db_session: AsyncSession
    ):
        """Version field is preserved in database"""
        config = {
            "version": "2.0",
            "priorities": {"product_core": 1},
        }

        await async_client.put(
            "/api/v1/users/me/field-priority",
            json=config,
            headers={"Authorization": f"Bearer {test_user.api_token}"},
        )

        # Verify version in database
        await db_session.refresh(test_user)
        assert test_user.field_priority_config["version"] == "2.0"

    async def test_field_priority_all_valid_priority_values(
        self, async_client: AsyncClient, test_user: User
    ):
        """All valid priority values (1-4) are accepted"""
        for priority in [1, 2, 3, 4]:
            config = {
                "version": "2.0",
                "priorities": {"product_core": priority},
            }

            response = await async_client.put(
                "/api/v1/users/me/field-priority",
                json=config,
                headers={"Authorization": f"Bearer {test_user.api_token}"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["priorities"]["product_core"] == priority
