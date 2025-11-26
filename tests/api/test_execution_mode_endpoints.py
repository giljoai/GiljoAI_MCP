"""
API Integration Tests for Execution Mode Endpoints - Handover 0248c

Tests the following endpoints:
- GET /api/users/me/settings/execution_mode
- PUT /api/users/me/settings/execution_mode

Test Coverage:
- Default value (claude_code) for new users
- Valid updates (claude_code ↔ multi_terminal)
- Persistence after updates
- Invalid values (422 Pydantic validation error)
- Authentication required (401 Unauthorized)
- Cross-user isolation (each user has their own setting)

Phase: Test-First Development (TDD)
Status: Tests for existing implementation (execution_mode in depth_config JSONB)
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from passlib.hash import bcrypt


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
async def execution_mode_user(api_client: AsyncClient, db_manager):
    """
    Create a test user with valid tenant key for execution mode tests.
    Returns token for authentication.
    """
    from src.giljo_mcp.models import User
    from src.giljo_mcp.auth.jwt_manager import JWTManager
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"exec_mode_user_{unique_id}"

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("test_password"),
            email=f"{username}@test.com",
            tenant_key=TenantManager.generate_tenant_key(f"exec_mode_{unique_id}"),
            role="developer",
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key,
        )

        return token


# ============================================================================
# EXECUTION MODE TESTS - GET /users/me/settings/execution_mode
# ============================================================================

class TestGetExecutionMode:
    """Test GET /users/me/settings/execution_mode - Retrieve execution mode"""

    @pytest.mark.asyncio
    async def test_get_execution_mode_default_value(
        self, api_client: AsyncClient, execution_mode_user: str
    ):
        """Test GET /users/me/settings/execution_mode - New user defaults to claude_code."""
        response = await api_client.get(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user}
        )

        assert response.status_code == 200
        data = response.json()
        assert "execution_mode" in data
        assert data["execution_mode"] == "claude_code"

    @pytest.mark.asyncio
    async def test_get_execution_mode_requires_authentication(
        self, api_client: AsyncClient
    ):
        """Test GET /users/me/settings/execution_mode - 401 without authentication."""
        response = await api_client.get("/api/v1/users/me/settings/execution_mode")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_execution_mode_multi_user_isolation(
        self, api_client: AsyncClient, db_manager
    ):
        """Test GET /users/me/settings/execution_mode - Each user has independent setting."""
        from src.giljo_mcp.models import User
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        from passlib.hash import bcrypt
        from src.giljo_mcp.tenant import TenantManager

        # Create two separate users with different execution modes
        unique_id_1 = uuid4().hex[:8]
        unique_id_2 = uuid4().hex[:8]

        async with db_manager.get_session_async() as session:
            user1 = User(
                username=f"user1_{unique_id_1}",
                password_hash=bcrypt.hash("password1"),
                email=f"user1_{unique_id_1}@test.com",
                tenant_key=TenantManager.generate_tenant_key(f"tenant1_{unique_id_1}"),
                role="developer",
                is_active=True,
                depth_config={
                    "vision_chunking": "moderate",
                    "memory_last_n_projects": 3,
                    "git_commits": 25,
                    "agent_template_detail": "standard",
                    "tech_stack_sections": "all",
                    "architecture_depth": "overview",
                    "execution_mode": "claude_code",  # User 1 uses claude_code
                },
            )
            user2 = User(
                username=f"user2_{unique_id_2}",
                password_hash=bcrypt.hash("password2"),
                email=f"user2_{unique_id_2}@test.com",
                tenant_key=TenantManager.generate_tenant_key(f"tenant2_{unique_id_2}"),
                role="developer",
                is_active=True,
                depth_config={
                    "vision_chunking": "moderate",
                    "memory_last_n_projects": 3,
                    "git_commits": 25,
                    "agent_template_detail": "standard",
                    "tech_stack_sections": "all",
                    "architecture_depth": "overview",
                    "execution_mode": "multi_terminal",  # User 2 uses multi_terminal
                },
            )
            session.add_all([user1, user2])
            await session.commit()
            await session.refresh(user1)
            await session.refresh(user2)

            # Generate tokens for both users
            token1 = JWTManager.create_access_token(
                user_id=user1.id,
                username=user1.username,
                role=user1.role,
                tenant_key=user1.tenant_key,
            )
            token2 = JWTManager.create_access_token(
                user_id=user2.id,
                username=user2.username,
                role=user2.role,
                tenant_key=user2.tenant_key,
            )

        # User 1 sees their own setting (claude_code)
        response1 = await api_client.get(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": token1}
        )
        assert response1.status_code == 200
        assert response1.json()["execution_mode"] == "claude_code"

        # User 2 sees their own setting (multi_terminal)
        response2 = await api_client.get(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": token2}
        )
        assert response2.status_code == 200
        assert response2.json()["execution_mode"] == "multi_terminal"


# ============================================================================
# EXECUTION MODE TESTS - PUT /users/me/settings/execution_mode
# ============================================================================

class TestUpdateExecutionMode:
    """Test PUT /users/me/settings/execution_mode - Update execution mode"""

    @pytest.mark.asyncio
    async def test_update_execution_mode_to_multi_terminal(
        self, api_client: AsyncClient, execution_mode_user: str
    ):
        """Test PUT /users/me/settings/execution_mode - Update to multi_terminal succeeds."""
        response = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user},
            json={"execution_mode": "multi_terminal"}
        )

        assert response.status_code == 200
        data = response.json()
        assert "execution_mode" in data
        assert data["execution_mode"] == "multi_terminal"

    @pytest.mark.asyncio
    async def test_update_execution_mode_persistence(
        self, api_client: AsyncClient, execution_mode_user: str
    ):
        """Test PUT /users/me/settings/execution_mode - Update persists after GET."""
        # Update to multi_terminal
        update_response = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user},
            json={"execution_mode": "multi_terminal"}
        )
        assert update_response.status_code == 200

        # Verify persistence via GET
        get_response = await api_client.get(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user}
        )
        assert get_response.status_code == 200
        assert get_response.json()["execution_mode"] == "multi_terminal"

    @pytest.mark.asyncio
    async def test_update_execution_mode_switch_back_to_claude_code(
        self, api_client: AsyncClient, execution_mode_user: str
    ):
        """Test PUT /users/me/settings/execution_mode - Can switch back to claude_code."""
        # First change to multi_terminal
        await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user},
            json={"execution_mode": "multi_terminal"}
        )

        # Switch back to claude_code
        switch_response = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user},
            json={"execution_mode": "claude_code"}
        )
        assert switch_response.status_code == 200
        assert switch_response.json()["execution_mode"] == "claude_code"

        # Verify persistence
        get_response = await api_client.get(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user}
        )
        assert get_response.status_code == 200
        assert get_response.json()["execution_mode"] == "claude_code"

    @pytest.mark.asyncio
    async def test_update_execution_mode_invalid_value(
        self, api_client: AsyncClient, execution_mode_user: str
    ):
        """Test PUT /users/me/settings/execution_mode - 422 for invalid mode."""
        response = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user},
            json={"execution_mode": "invalid_mode"}
        )

        # Pydantic validation should return 422 Unprocessable Entity
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_execution_mode_missing_field(
        self, api_client: AsyncClient, execution_mode_user: str
    ):
        """Test PUT /users/me/settings/execution_mode - 422 for missing execution_mode field."""
        response = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user},
            json={}  # Missing execution_mode
        )

        # Pydantic validation should return 422
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_update_execution_mode_requires_authentication(
        self, api_client: AsyncClient
    ):
        """Test PUT /users/me/settings/execution_mode - 401 without authentication."""
        response = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            json={"execution_mode": "multi_terminal"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_execution_mode_idempotent(
        self, api_client: AsyncClient, execution_mode_user: str
    ):
        """Test PUT /users/me/settings/execution_mode - Idempotent (same value twice)."""
        # Set to multi_terminal
        response1 = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user},
            json={"execution_mode": "multi_terminal"}
        )
        assert response1.status_code == 200

        # Set to multi_terminal again
        response2 = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": execution_mode_user},
            json={"execution_mode": "multi_terminal"}
        )
        assert response2.status_code == 200
        assert response2.json()["execution_mode"] == "multi_terminal"


# ============================================================================
# CROSS-USER ISOLATION TESTS
# ============================================================================

class TestExecutionModeUserIsolation:
    """Test execution mode settings are isolated per user"""

    @pytest.mark.asyncio
    async def test_execution_mode_user_isolation(
        self, api_client: AsyncClient, db_manager
    ):
        """Test PUT /users/me/settings/execution_mode - Changes don't affect other users."""
        from src.giljo_mcp.models import User
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        from passlib.hash import bcrypt
        from src.giljo_mcp.tenant import TenantManager

        # Create two users with same initial execution mode
        unique_id_a = uuid4().hex[:8]
        unique_id_b = uuid4().hex[:8]

        async with db_manager.get_session_async() as session:
            user_a = User(
                username=f"user_a_{unique_id_a}",
                password_hash=bcrypt.hash("password_a"),
                email=f"user_a_{unique_id_a}@test.com",
                tenant_key=TenantManager.generate_tenant_key(f"tenant_a_{unique_id_a}"),
                role="developer",
                is_active=True,
                depth_config={
                    "vision_chunking": "moderate",
                    "memory_last_n_projects": 3,
                    "git_commits": 25,
                    "agent_template_detail": "standard",
                    "tech_stack_sections": "all",
                    "architecture_depth": "overview",
                    "execution_mode": "claude_code",
                },
            )
            user_b = User(
                username=f"user_b_{unique_id_b}",
                password_hash=bcrypt.hash("password_b"),
                email=f"user_b_{unique_id_b}@test.com",
                tenant_key=TenantManager.generate_tenant_key(f"tenant_b_{unique_id_b}"),
                role="developer",
                is_active=True,
                depth_config={
                    "vision_chunking": "moderate",
                    "memory_last_n_projects": 3,
                    "git_commits": 25,
                    "agent_template_detail": "standard",
                    "tech_stack_sections": "all",
                    "architecture_depth": "overview",
                    "execution_mode": "claude_code",
                },
            )
            session.add_all([user_a, user_b])
            await session.commit()
            await session.refresh(user_a)
            await session.refresh(user_b)

            token_a = JWTManager.create_access_token(
                user_id=user_a.id,
                username=user_a.username,
                role=user_a.role,
                tenant_key=user_a.tenant_key,
            )
            token_b = JWTManager.create_access_token(
                user_id=user_b.id,
                username=user_b.username,
                role=user_b.role,
                tenant_key=user_b.tenant_key,
            )

        # User A changes to multi_terminal
        response_a = await api_client.put(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": token_a},
            json={"execution_mode": "multi_terminal"}
        )
        assert response_a.status_code == 200

        # User B's setting should remain unchanged
        response_b = await api_client.get(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": token_b}
        )
        assert response_b.status_code == 200
        assert response_b.json()["execution_mode"] == "claude_code"  # Still default

        # Verify User A's change persisted
        response_a_verify = await api_client.get(
            "/api/v1/users/me/settings/execution_mode",
            cookies={"access_token": token_a}
        )
        assert response_a_verify.status_code == 200
        assert response_a_verify.json()["execution_mode"] == "multi_terminal"
