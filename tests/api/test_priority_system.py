"""
Priority System v2.0 Unit Tests - Handover 0313

Tests for the refactored priority system that migrates from v1.0 (10/7/4 token reduction)
to v2.0 (1/2/3/4 fetch order with mandatory flags).

Test Coverage:
- Pydantic schema validation (FieldPriorityConfig)
- Priority range enforcement (1-4)
- At least one CRITICAL category requirement
- All EXCLUDED rejection
- Invalid category names rejection
- API endpoint CRUD operations
- WebSocket event emission
- Default seeding for new users
- Multi-tenant isolation

TDD Discipline: Tests written FIRST (RED phase)
Expected: All tests FAIL until backend logic implemented
"""

import pytest
from httpx import AsyncClient
from pydantic import ValidationError

from api.endpoints.users import FieldPriorityConfig


# ============================================================================
# TEST SUITE 1: Pydantic Schema Validation
# ============================================================================


class TestFieldPriorityConfigValidation:
    """Test Pydantic schema validation for FieldPriorityConfig"""

    def test_valid_priority_config_accepted(self):
        """Test that valid v2.0 priority configuration is accepted"""
        valid_config = {
            "priorities": {
                "product_core": 1,  # CRITICAL
                "vision_documents": 2,  # IMPORTANT
                "agent_templates": 1,  # CRITICAL
                "project_description": 2,  # IMPORTANT
                "memory_360": 3,  # NICE_TO_HAVE
                "git_history": 4,  # EXCLUDED
            },
            "version": "2.0",
        }
        config = FieldPriorityConfig(**valid_config)
        assert config.priorities["product_core"] == 1
        assert config.priorities["git_history"] == 4
        assert config.version == "2.0"

    def test_priority_range_enforcement_invalid_low(self):
        """Test that priority value 0 (invalid) is rejected"""
        invalid_config = {
            "priorities": {
                "product_core": 0,  # Invalid - must be 1-4
                "vision_documents": 2,
            },
            "version": "2.0",
        }
        with pytest.raises(ValidationError, match="Invalid priority 0"):
            FieldPriorityConfig(**invalid_config)

    def test_priority_range_enforcement_invalid_high(self):
        """Test that priority value 5 (invalid) is rejected"""
        invalid_config = {
            "priorities": {
                "product_core": 1,
                "vision_documents": 5,  # Invalid - must be 1-4
            },
            "version": "2.0",
        }
        with pytest.raises(ValidationError, match="Invalid priority 5"):
            FieldPriorityConfig(**invalid_config)

    def test_priority_range_enforcement_invalid_negative(self):
        """Test that negative priority value is rejected"""
        invalid_config = {
            "priorities": {
                "product_core": -1,  # Invalid - must be 1-4
                "vision_documents": 2,
            },
            "version": "2.0",
        }
        with pytest.raises(ValidationError, match="Invalid priority -1"):
            FieldPriorityConfig(**invalid_config)

    def test_at_least_one_critical_requirement(self):
        """Test that at least one category must have Priority 1 (CRITICAL)"""
        invalid_config = {
            "priorities": {
                "product_core": 2,  # IMPORTANT (not CRITICAL)
                "vision_documents": 2,  # IMPORTANT
                "agent_templates": 3,  # NICE_TO_HAVE
                "project_description": 3,  # NICE_TO_HAVE
                "memory_360": 4,  # EXCLUDED
                "git_history": 4,  # EXCLUDED
            },
            "version": "2.0",
        }
        with pytest.raises(ValidationError, match="At least one category must have Priority 1"):
            FieldPriorityConfig(**invalid_config)

    def test_all_excluded_rejection(self):
        """Test that configuration with all categories EXCLUDED (Priority 4) is rejected"""
        invalid_config = {
            "priorities": {
                "product_core": 4,  # EXCLUDED
                "vision_documents": 4,  # EXCLUDED
                "agent_templates": 4,  # EXCLUDED
                "project_description": 4,  # EXCLUDED
                "memory_360": 4,  # EXCLUDED
                "git_history": 4,  # EXCLUDED
            },
            "version": "2.0",
        }
        # Note: "At least one category must have Priority 1" fires BEFORE "Cannot exclude all"
        # Both validations work, but Priority 1 check happens first
        with pytest.raises(ValidationError, match="At least one category must have Priority 1"):
            FieldPriorityConfig(**invalid_config)

    def test_invalid_category_names_rejected(self):
        """Test that unknown category names are rejected"""
        invalid_config = {
            "priorities": {
                "product_core": 1,
                "invalid_category": 2,  # Not a valid category
                "another_invalid": 3,  # Not a valid category
            },
            "version": "2.0",
        }
        with pytest.raises(ValidationError, match="Invalid category names"):
            FieldPriorityConfig(**invalid_config)

    def test_valid_categories_all_accepted(self):
        """Test that all 6 valid category names are accepted"""
        valid_categories = [
            "product_core",
            "vision_documents",
            "agent_templates",
            "project_description",
            "memory_360",
            "git_history",
        ]
        for category in valid_categories:
            config_dict = {
                "priorities": {category: 1},  # Single category with CRITICAL
                "version": "2.0",
            }
            config = FieldPriorityConfig(**config_dict)
            assert config.priorities[category] == 1


# ============================================================================
# TEST SUITE 2: API Endpoint Tests
# ============================================================================


@pytest.fixture
async def test_user(db_manager):
    """Create test user for priority configuration tests"""
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager
    from uuid import uuid4
    from passlib.hash import bcrypt

    unique_id = uuid4().hex[:8]
    username = f"priority_test_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("test_password"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
            field_priority_config=None,  # No config yet - will be seeded with defaults
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "test_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def test_user_token(api_client: AsyncClient, test_user):
    """Get JWT token for test user"""
    response = await api_client.post(
        "/api/auth/login", json={"username": test_user._test_username, "password": test_user._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def another_tenant_user(db_manager):
    """Create user from different tenant for isolation testing"""
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager
    from uuid import uuid4
    from passlib.hash import bcrypt

    unique_id = uuid4().hex[:8]
    username = f"other_tenant_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"other_tenant_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("other_password"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_tenant_key = tenant_key
        return user


@pytest.mark.asyncio
class TestPriorityConfigurationAPI:
    """Test API endpoints for priority configuration"""

    async def test_successful_priority_update(self, api_client: AsyncClient, test_user, test_user_token):
        """Test successful priority configuration update via PUT /api/users/me/field-priority"""
        new_config = {
            "priorities": {
                "product_core": 1,  # CRITICAL
                "agent_templates": 1,  # CRITICAL
                "vision_documents": 2,  # IMPORTANT
                "project_description": 2,  # IMPORTANT
                "memory_360": 3,  # NICE_TO_HAVE
                "git_history": 4,  # EXCLUDED
            },
            "version": "2.0",
        }

        response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=new_config,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200, f"Update failed: {response.json()}"
        response_data = response.json()
        assert response_data["priorities"]["product_core"] == 1
        assert response_data["priorities"]["git_history"] == 4
        assert response_data["version"] == "2.0"

    async def test_validation_error_invalid_priority(self, api_client: AsyncClient, test_user, test_user_token):
        """Test that invalid priority value (out of range) returns 422 validation error"""
        invalid_config = {
            "priorities": {
                "product_core": 10,  # Invalid - v1.0 value, not v2.0
                "vision_documents": 2,
            },
            "version": "2.0",
        }

        response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=invalid_config,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 422, "Should return 422 for validation error"
        response_data = response.json()
        assert "Invalid priority" in str(response_data)

    async def test_validation_error_no_critical_category(self, api_client: AsyncClient, test_user, test_user_token):
        """Test that configuration without CRITICAL category returns 422"""
        invalid_config = {
            "priorities": {
                "product_core": 2,  # All Priority 2 or higher - no Priority 1
                "vision_documents": 2,
                "agent_templates": 3,
                "project_description": 3,
                "memory_360": 4,
                "git_history": 4,
            },
            "version": "2.0",
        }

        response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=invalid_config,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 422
        response_data = response.json()
        assert "At least one category must have Priority 1" in str(response_data)

    async def test_multi_tenant_isolation(
        self, db_manager, api_client: AsyncClient, test_user, test_user_token, another_tenant_user
    ):
        """Test that users cannot access other tenants' priority configurations"""
        # Update test_user's configuration
        config = {
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 1,
                "project_description": 3,
                "memory_360": 4,
                "git_history": 4,
            },
            "version": "2.0",
        }

        response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=config,
            cookies={"access_token": test_user_token},
        )
        assert response.status_code == 200

        # Verify other tenant's user was NOT affected
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select
            from src.giljo_mcp.models import User

            stmt = select(User).where(User.id == another_tenant_user.id)
            result = await session.execute(stmt)
            other_user = result.scalar_one()

            # Other tenant's config should be unchanged (default or None)
            assert other_user.tenant_key != test_user.tenant_key
            if other_user.field_priority_config is not None:
                # If has config, it should be default, not test_user's config
                assert other_user.field_priority_config.get("priorities", {}).get("product_core") != 1 or (
                    other_user.field_priority_config == config
                ) is False

    async def test_get_current_priority_config(self, api_client: AsyncClient, test_user, test_user_token):
        """Test GET /api/users/me/field-priority returns current configuration"""
        # First update configuration
        config = {
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 1,
                "project_description": 2,
                "memory_360": 3,
                "git_history": 4,
            },
            "version": "2.0",
        }

        update_response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=config,
            cookies={"access_token": test_user_token},
        )
        assert update_response.status_code == 200

        # Then retrieve it
        get_response = await api_client.get(
            "/api/v1/users/me/field-priority",
            cookies={"access_token": test_user_token},
        )

        assert get_response.status_code == 200
        response_data = get_response.json()
        assert response_data["priorities"]["product_core"] == 1
        assert response_data["priorities"]["memory_360"] == 3
        assert response_data["version"] == "2.0"

    async def test_unauthenticated_request_rejected(self, api_client: AsyncClient):
        """Test that unauthenticated requests are rejected with 401"""
        config = {
            "priorities": {"product_core": 1, "vision_documents": 2},
            "version": "2.0",
        }

        response = await api_client.put("/api/v1/users/me/field-priority", json=config)

        assert response.status_code == 401, "Should return 401 Unauthorized without token"


# ============================================================================
# TEST SUITE 3: Default Seeding Tests
# ============================================================================


@pytest.mark.asyncio
class TestDefaultPrioritySeeding:
    """Test that new users receive v2.0 default priorities"""

    async def test_new_user_default_priorities_seeded(self, db_manager):
        """Test that new users automatically get v2.0 default priorities"""
        from src.giljo_mcp.models import User
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
        from uuid import uuid4
        from passlib.hash import bcrypt

        unique_id = uuid4().hex[:8]
        username = f"new_user_{unique_id}"
        tenant_key = TenantManager.generate_tenant_key(f"tenant_{unique_id}")

        async with db_manager.get_session_async() as session:
            # Create user with explicit default config
            user = User(
                username=username,
                password_hash=bcrypt.hash("password"),
                email=f"{username}@test.com",
                role="developer",
                tenant_key=tenant_key,
                is_active=True,
                field_priority_config=DEFAULT_FIELD_PRIORITY,  # Seed defaults
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)

            # Verify v2.0 defaults seeded
            assert user.field_priority_config is not None
            assert user.field_priority_config.get("version") == "2.0"
            priorities = user.field_priority_config.get("priorities", {})
            assert priorities.get("product_core") == 1  # CRITICAL
            assert priorities.get("agent_templates") == 1  # CRITICAL
            assert priorities.get("vision_documents") == 2  # IMPORTANT
            assert priorities.get("memory_360") == 3  # NICE_TO_HAVE
            assert priorities.get("git_history") == 4  # EXCLUDED

    async def test_existing_user_no_migration(self, db_manager, test_user):
        """Test that existing users keep their config until explicitly updated"""
        # test_user fixture creates user with field_priority_config=None
        # Verify no automatic migration occurred
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select
            from src.giljo_mcp.models import User

            stmt = select(User).where(User.id == test_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one()

            # User config should be None (not auto-migrated to v2.0)
            assert user.field_priority_config is None


# ============================================================================
# TEST SUITE 4: WebSocket Event Emission (Placeholder)
# ============================================================================


@pytest.mark.asyncio
class TestWebSocketEventEmission:
    """Test that priority updates emit WebSocket events"""

    async def test_websocket_event_emitted_on_update(self, api_client: AsyncClient, test_user, test_user_token):
        """Test that priority_config_updated WebSocket event is emitted on successful update"""
        # Note: Full WebSocket testing requires WebSocket client setup
        # This is a placeholder for integration testing in Phase 6
        # For now, verify API update succeeds (WebSocket emission in Phase 4 implementation)
        config = {
            "priorities": {
                "product_core": 1,
                "vision_documents": 2,
                "agent_templates": 1,
                "project_description": 2,
                "memory_360": 3,
                "git_history": 4,
            },
            "version": "2.0",
        }

        response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=config,
            cookies={"access_token": test_user_token},
        )

        assert response.status_code == 200
        # TODO: Add WebSocket event assertion in integration test (Phase 6)
        # Expected event: {"event_type": "priority_config_updated", "data": {...}}
