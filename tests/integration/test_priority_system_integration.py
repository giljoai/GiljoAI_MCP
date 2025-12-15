"""
Priority System v2.0 Integration Tests - Handover 0313

End-to-end integration tests for the refactored priority system. Tests complete
workflows from API request through database persistence to WebSocket emission.

Test Coverage:
- E2E priority update workflow (API → DB → WebSocket)
- Frontend drag-and-drop simulation (priority ordering)
- Real-time UI synchronization via WebSocket events
- Multi-tenant isolation verification
- Persistence across sessions

TDD Discipline: Integration tests written FIRST (RED phase)
Expected: All tests FAIL until backend + WebSocket implementation complete
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


# ============================================================================
# TEST SUITE 1: End-to-End Workflow Tests
# ============================================================================


@pytest.fixture
async def integration_test_user(db_manager):
    """Create integration test user with default v2.0 priorities"""
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
    from uuid import uuid4
    from passlib.hash import bcrypt

    unique_id = uuid4().hex[:8]
    username = f"integration_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("integration_password"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
            field_priority_config=DEFAULT_FIELD_PRIORITY,  # Seed v2.0 defaults
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "integration_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def integration_test_user_token(api_client: AsyncClient, integration_test_user):
    """Get JWT token for integration test user"""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": integration_test_user._test_username, "password": integration_test_user._test_password},
    )
    assert response.status_code == 200
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.mark.asyncio
class TestEndToEndPriorityWorkflow:
    """Test complete end-to-end priority configuration workflows"""

    async def test_e2e_priority_update_workflow(
        self, db_manager, api_client: AsyncClient, integration_test_user, integration_test_user_token
    ):
        """
        Test complete workflow: API request → Database update → Response

        Steps:
        1. Create user with default priorities
        2. Verify default v2.0 priorities seeded
        3. Update priorities via PUT /api/users/me/field-priority
        4. Verify database updated correctly
        5. Fetch updated priorities via GET /api/users/me/field-priority
        6. Verify response matches update
        """
        # Step 1: Verify user created with defaults
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select
            from src.giljo_mcp.models import User

            stmt = select(User).where(User.id == integration_test_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one()

            # Verify default v2.0 priorities
            assert user.field_priority_config is not None
            assert user.field_priority_config.get("version") == "2.0"
            default_priorities = user.field_priority_config.get("priorities", {})
            assert default_priorities.get("product_core") == 1  # CRITICAL
            assert default_priorities.get("git_history") == 4  # EXCLUDED

        # Step 2: Update priorities via API
        new_config = {
            "priorities": {
                "product_core": 1,  # CRITICAL (unchanged)
                "agent_templates": 1,  # CRITICAL (unchanged)
                "vision_documents": 3,  # NICE_TO_HAVE (changed from 2)
                "project_description": 2,  # IMPORTANT (unchanged)
                "memory_360": 2,  # IMPORTANT (changed from 3)
                "git_history": 1,  # CRITICAL (changed from 4 - now enabled)
            },
            "version": "2.0",
        }

        update_response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=new_config,
            cookies={"access_token": integration_test_user_token},
        )

        assert update_response.status_code == 200, f"Update failed: {update_response.json()}"
        update_response_data = update_response.json()
        assert update_response_data["priorities"]["vision_documents"] == 3
        assert update_response_data["priorities"]["git_history"] == 1

        # Step 3: Verify database updated
        async with db_manager.get_session_async() as session:
            stmt = select(User).where(User.id == integration_test_user.id)
            result = await session.execute(stmt)
            user = result.scalar_one()

            updated_config = user.field_priority_config
            assert updated_config is not None
            assert updated_config.get("version") == "2.0"
            updated_priorities = updated_config.get("priorities", {})
            assert updated_priorities.get("vision_documents") == 3
            assert updated_priorities.get("memory_360") == 2
            assert updated_priorities.get("git_history") == 1

        # Step 4: Fetch via GET endpoint
        get_response = await api_client.get(
            "/api/v1/users/me/field-priority",
            cookies={"access_token": integration_test_user_token},
        )

        assert get_response.status_code == 200
        get_response_data = get_response.json()
        assert get_response_data["priorities"] == new_config["priorities"]
        assert get_response_data["version"] == "2.0"

    async def test_persistence_across_sessions(
        self, db_manager, api_client: AsyncClient, integration_test_user, integration_test_user_token
    ):
        """Test that priority configuration persists across login sessions"""
        # Update configuration
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

        update_response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=config,
            cookies={"access_token": integration_test_user_token},
        )
        assert update_response.status_code == 200

        # Simulate logout (new session - get new token)
        new_login_response = await api_client.post(
            "/api/auth/login",
            json={
                "username": integration_test_user._test_username,
                "password": integration_test_user._test_password,
            },
        )
        assert new_login_response.status_code == 200
        new_token = new_login_response.cookies.get("access_token")

        # Fetch configuration with new token (new session)
        get_response = await api_client.get(
            "/api/v1/users/me/field-priority",
            cookies={"access_token": new_token},
        )

        assert get_response.status_code == 200
        response_data = get_response.json()
        assert response_data["priorities"] == config["priorities"]
        # Configuration persisted across sessions


# ============================================================================
# TEST SUITE 2: Frontend Integration Simulation
# ============================================================================


@pytest.mark.asyncio
class TestFrontendIntegration:
    """Simulate frontend drag-and-drop and priority toggle interactions"""

    async def test_drag_drop_priority_reordering(
        self, api_client: AsyncClient, integration_test_user, integration_test_user_token
    ):
        """
        Simulate frontend drag-and-drop reordering of category cards.

        User drags categories to reorder fetch priority:
        1. agent_templates (Priority 1 - CRITICAL)
        2. product_core (Priority 1 - CRITICAL)
        3. vision_documents (Priority 2 - IMPORTANT)
        4. project_description (Priority 2 - IMPORTANT)
        5. memory_360 (Priority 3 - NICE_TO_HAVE)
        6. git_history (Priority 4 - EXCLUDED)
        """
        drag_drop_config = {
            "priorities": {
                "agent_templates": 1,  # Top priority (dragged to position 1)
                "product_core": 1,  # Second priority (position 2)
                "vision_documents": 2,  # Third (position 3)
                "project_description": 2,  # Fourth (position 4)
                "memory_360": 3,  # Fifth (position 5)
                "git_history": 4,  # Last (position 6)
            },
            "version": "2.0",
        }

        response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=drag_drop_config,
            cookies={"access_token": integration_test_user_token},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["priorities"]["agent_templates"] == 1
        assert response_data["priorities"]["git_history"] == 4

    async def test_priority_label_toggle(
        self, api_client: AsyncClient, integration_test_user, integration_test_user_token
    ):
        """
        Simulate user toggling priority labels via UI dropdown.

        User clicks dropdown for "vision_documents":
        - CRITICAL (1) → IMPORTANT (2) → NICE_TO_HAVE (3) → EXCLUDED (4)
        """
        # Initial state: vision_documents = IMPORTANT (2)
        initial_config = {
            "priorities": {
                "product_core": 1,
                "agent_templates": 1,
                "vision_documents": 2,  # IMPORTANT
                "project_description": 2,
                "memory_360": 3,
                "git_history": 4,
            },
            "version": "2.0",
        }

        await api_client.put(
            "/api/v1/users/me/field-priority",
            json=initial_config,
            cookies={"access_token": integration_test_user_token},
        )

        # User toggles vision_documents: IMPORTANT (2) → NICE_TO_HAVE (3)
        toggled_config = initial_config.copy()
        toggled_config["priorities"]["vision_documents"] = 3

        toggle_response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=toggled_config,
            cookies={"access_token": integration_test_user_token},
        )

        assert toggle_response.status_code == 200
        response_data = toggle_response.json()
        assert response_data["priorities"]["vision_documents"] == 3  # Updated

    async def test_enable_git_history_via_ui(
        self, api_client: AsyncClient, integration_test_user, integration_test_user_token
    ):
        """
        Simulate user enabling git_history (default EXCLUDED → IMPORTANT).

        User toggles git_history dropdown: EXCLUDED (4) → IMPORTANT (2)
        """
        # Default: git_history = EXCLUDED (4)
        # User changes to: git_history = IMPORTANT (2)
        updated_config = {
            "priorities": {
                "product_core": 1,
                "agent_templates": 1,
                "vision_documents": 2,
                "project_description": 2,
                "memory_360": 3,
                "git_history": 2,  # Changed from 4 to 2 (enabled)
            },
            "version": "2.0",
        }

        response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=updated_config,
            cookies={"access_token": integration_test_user_token},
        )

        assert response.status_code == 200
        response_data = response.json()
        assert response_data["priorities"]["git_history"] == 2  # Now IMPORTANT


# ============================================================================
# TEST SUITE 3: Multi-Tenant Isolation Integration
# ============================================================================


@pytest.fixture
async def tenant_a_user(db_manager):
    """Create Tenant A user"""
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager
    from uuid import uuid4
    from passlib.hash import bcrypt

    unique_id = uuid4().hex[:8]
    username = f"tenant_a_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("tenant_a_password"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "tenant_a_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_b_user(db_manager):
    """Create Tenant B user (different tenant)"""
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager
    from uuid import uuid4
    from passlib.hash import bcrypt

    unique_id = uuid4().hex[:8]
    username = f"tenant_b_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("tenant_b_password"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "tenant_b_password"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_a_token(api_client: AsyncClient, tenant_a_user):
    """Get JWT token for Tenant A user"""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_a_user._test_username, "password": tenant_a_user._test_password},
    )
    assert response.status_code == 200
    return response.cookies.get("access_token")


@pytest.fixture
async def tenant_b_token(api_client: AsyncClient, tenant_b_user):
    """Get JWT token for Tenant B user"""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_b_user._test_username, "password": tenant_b_user._test_password},
    )
    assert response.status_code == 200
    return response.cookies.get("access_token")


@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """Verify zero cross-tenant leakage for priority configurations"""

    async def test_zero_cross_tenant_leakage(
        self, db_manager, api_client: AsyncClient, tenant_a_user, tenant_a_token, tenant_b_user, tenant_b_token
    ):
        """
        Test that Tenant A's priority updates do NOT affect Tenant B's configuration.

        Steps:
        1. Tenant A updates their priorities
        2. Tenant B updates their priorities (different values)
        3. Verify Tenant A's config unchanged by Tenant B's update
        4. Verify Tenant B's config unchanged by Tenant A's update
        """
        # Tenant A updates config
        tenant_a_config = {
            "priorities": {
                "product_core": 1,
                "agent_templates": 1,
                "vision_documents": 2,
                "project_description": 3,
                "memory_360": 4,
                "git_history": 4,
            },
            "version": "2.0",
        }

        tenant_a_response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=tenant_a_config,
            cookies={"access_token": tenant_a_token},
        )
        assert tenant_a_response.status_code == 200

        # Tenant B updates config (different values)
        tenant_b_config = {
            "priorities": {
                "product_core": 1,
                "agent_templates": 1,
                "vision_documents": 3,  # Different from Tenant A
                "project_description": 2,  # Different from Tenant A
                "memory_360": 2,  # Different from Tenant A
                "git_history": 1,  # Different from Tenant A (enabled)
            },
            "version": "2.0",
        }

        tenant_b_response = await api_client.put(
            "/api/v1/users/me/field-priority",
            json=tenant_b_config,
            cookies={"access_token": tenant_b_token},
        )
        assert tenant_b_response.status_code == 200

        # Verify Tenant A's config unchanged
        tenant_a_get_response = await api_client.get(
            "/api/v1/users/me/field-priority",
            cookies={"access_token": tenant_a_token},
        )
        assert tenant_a_get_response.status_code == 200
        tenant_a_data = tenant_a_get_response.json()
        assert tenant_a_data["priorities"] == tenant_a_config["priorities"]
        assert tenant_a_data["priorities"]["vision_documents"] == 2  # NOT 3 (Tenant B's value)

        # Verify Tenant B's config unchanged
        tenant_b_get_response = await api_client.get(
            "/api/v1/users/me/field-priority",
            cookies={"access_token": tenant_b_token},
        )
        assert tenant_b_get_response.status_code == 200
        tenant_b_data = tenant_b_get_response.json()
        assert tenant_b_data["priorities"] == tenant_b_config["priorities"]
        assert tenant_b_data["priorities"]["git_history"] == 1  # NOT 4 (Tenant A's value)

        # Verify database-level isolation
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select
            from src.giljo_mcp.models import User

            # Fetch both users
            stmt_a = select(User).where(User.id == tenant_a_user.id)
            result_a = await session.execute(stmt_a)
            user_a = result_a.scalar_one()

            stmt_b = select(User).where(User.id == tenant_b_user.id)
            result_b = await session.execute(stmt_b)
            user_b = result_b.scalar_one()

            # Verify different tenant_keys
            assert user_a.tenant_key != user_b.tenant_key

            # Verify different configurations
            assert user_a.field_priority_config.get("priorities") != user_b.field_priority_config.get("priorities")
            assert user_a.field_priority_config["priorities"]["memory_360"] == 4
            assert user_b.field_priority_config["priorities"]["memory_360"] == 2


# ============================================================================
# TEST SUITE 4: WebSocket Real-Time Synchronization (Placeholder)
# ============================================================================


@pytest.mark.asyncio
class TestWebSocketRealTimeSynchronization:
    """Test real-time UI updates via WebSocket events (integration with frontend)"""

    async def test_websocket_event_triggers_ui_update(
        self, api_client: AsyncClient, integration_test_user, integration_test_user_token
    ):
        """
        Test that priority update triggers WebSocket event for real-time UI sync.

        Workflow:
        1. Frontend connects to WebSocket
        2. User updates priority via API
        3. WebSocket event "priority_config_updated" emitted
        4. Frontend receives event and updates UI without page reload

        Note: Full WebSocket client testing deferred to Phase 6 (E2E testing)
        This test verifies API update succeeds (WebSocket emission in Phase 4)
        """
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
            cookies={"access_token": integration_test_user_token},
        )

        assert response.status_code == 200
        # TODO: Phase 6 - Add WebSocket event assertion
        # Expected: WebSocket event emitted with event_type="priority_config_updated"
        # Payload: {user_id, tenant_key, timestamp, updated_priorities}
