"""
API Integration Tests for Project execution_mode - Handover 0260 Phase 2 (TDD RED)

Tests cover:
- GET /api/v1/projects/{id} returns execution_mode
- PATCH /api/v1/projects/{id} updates execution_mode
- POST /api/v1/projects/ creates with execution_mode
- Invalid execution_mode values return 400
- Multi-tenant isolation for execution_mode
- Default value handling
- Response schema validation

These tests should FAIL initially until:
1. Project model has execution_mode column
2. ProjectResponse schema includes execution_mode
3. ProjectUpdate schema includes execution_mode
4. ProjectCreate schema includes execution_mode
5. API endpoints handle execution_mode
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


# ============================================================================
# FIXTURES (reuse from test_projects_api.py)
# ============================================================================

@pytest.fixture
async def api_client(db_manager):
    """
    Create AsyncClient for API testing with proper app state setup.

    Sets up db_manager in app.state for endpoints that need it (like auth/login).
    """
    from httpx import AsyncClient as HTTPXAsyncClient, ASGITransport
    from unittest.mock import MagicMock

    try:
        from api.app import app, state
        from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
        from src.giljo_mcp.auth import AuthManager
        from src.giljo_mcp.tenant import TenantManager

        async def mock_get_db_session():
            async with db_manager.get_session_async() as session:
                yield session

        # Override database session dependency
        app.dependency_overrides[get_db_session] = mock_get_db_session

        # Set up global state with db_manager for services that need it
        state.db_manager = db_manager
        app.state.db_manager = db_manager
        if state.tenant_manager is None:
            state.tenant_manager = TenantManager()

        # Set up tool_accessor for endpoints that need it
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor
        state.tool_accessor = ToolAccessor(db_manager=db_manager, tenant_manager=state.tenant_manager)
        app.state.tool_accessor = state.tool_accessor

        # Create mock config for AuthManager
        mock_config = MagicMock()
        mock_config.jwt.secret_key = "test_secret_key"
        mock_config.jwt.algorithm = "HS256"
        mock_config.jwt.expiration_minutes = 30
        mock_config.get = MagicMock(side_effect=lambda key, default=None: {
            "security.auth_enabled": True,
            "security.api_keys_required": False,
        }.get(key, default))

        state.config = mock_config
        app.state.config = mock_config
        app.state.auth = AuthManager(mock_config, db=None)
        state.auth = app.state.auth

        async with HTTPXAsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            cookies=None,
            follow_redirects=True
        ) as client:
            client.cookies.clear()
            yield client
            client.cookies.clear()

        app.dependency_overrides.clear()

    except ImportError:
        pytest.skip("API application not available for testing")


@pytest.fixture
async def tenant_a_user(db_manager):
    """Create Tenant A user for multi-tenant isolation testing."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_a_exec_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("password_a"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "password_a"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_a_token(api_client: AsyncClient, tenant_a_user):
    """Get JWT token for Tenant A user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_a_user._test_username, "password": tenant_a_user._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_a_product(api_client: AsyncClient, tenant_a_token: str):
    """Create a test product for Tenant A."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": "Tenant A Exec Mode Product",
            "description": "Test product for execution mode tests",
            "project_path": "/path/to/tenant_a/exec_product"
        },
        cookies={"access_token": tenant_a_token}
    )
    assert response.status_code == 200
    return response.json()


# ============================================================================
# CREATE PROJECT WITH EXECUTION_MODE TESTS
# ============================================================================

class TestProjectCreateWithExecutionMode:
    """Test POST /api/v1/projects/ with execution_mode field."""

    @pytest.mark.asyncio
    async def test_create_project_defaults_to_multi_terminal(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Project creation should default to 'multi_terminal' execution mode."""
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Default Execution Mode Project",
                "description": "Test default execution mode",
                "product_id": tenant_a_product["id"]
            },
            cookies={"access_token": tenant_a_token}
        )

        # EXPECTED TO FAIL: execution_mode not in response schema yet
        assert response.status_code == 201, f"Unexpected status: {response.status_code}"
        data = response.json()

        assert "execution_mode" in data, \
            "Response missing execution_mode field (schema not updated yet)"
        assert data["execution_mode"] == "multi_terminal", \
            f"Expected default 'multi_terminal', got {data.get('execution_mode')}"

    @pytest.mark.asyncio
    async def test_create_project_with_claude_code_cli_mode(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Project can be created with 'claude_code_cli' execution mode."""
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "CLI Mode Project",
                "description": "Test CLI execution mode",
                "product_id": tenant_a_product["id"],
                "execution_mode": "claude_code_cli"
            },
            cookies={"access_token": tenant_a_token}
        )

        # EXPECTED TO FAIL: execution_mode not in request/response schemas yet
        assert response.status_code == 201, f"Unexpected status: {response.status_code}"
        data = response.json()

        assert "execution_mode" in data, \
            "Response missing execution_mode field (schema not updated yet)"
        assert data["execution_mode"] == "claude_code_cli", \
            f"Expected 'claude_code_cli', got {data.get('execution_mode')}"

    @pytest.mark.asyncio
    async def test_create_project_with_multi_terminal_explicit(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Project can be explicitly created with 'multi_terminal' execution mode."""
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Explicit Multi-Terminal Project",
                "description": "Test explicit multi-terminal mode",
                "product_id": tenant_a_product["id"],
                "execution_mode": "multi_terminal"
            },
            cookies={"access_token": tenant_a_token}
        )

        # EXPECTED TO FAIL: execution_mode not in schemas yet
        assert response.status_code == 201, f"Unexpected status: {response.status_code}"
        data = response.json()

        assert "execution_mode" in data, \
            "Response missing execution_mode field (schema not updated yet)"
        assert data["execution_mode"] == "multi_terminal", \
            f"Expected 'multi_terminal', got {data.get('execution_mode')}"

    @pytest.mark.asyncio
    async def test_create_project_with_invalid_execution_mode(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Creating project with invalid execution_mode should return 400."""
        invalid_modes = ["invalid_mode", "cli_only", "terminal", "", "CLAUDE_CODE_CLI"]

        for invalid_mode in invalid_modes:
            response = await api_client.post(
                "/api/v1/projects/",
                json={
                    "name": f"Invalid Mode Project {invalid_mode}",
                    "description": "Should fail validation",
                    "product_id": tenant_a_product["id"],
                    "execution_mode": invalid_mode
                },
                cookies={"access_token": tenant_a_token}
            )

            # EXPECTED TO FAIL: validation not implemented yet
            assert response.status_code == 400, \
                f"Expected 400 for invalid mode '{invalid_mode}', got {response.status_code} " \
                f"(validation not implemented yet)"

            # When validation is implemented, error should mention execution_mode
            if response.status_code == 400:
                error_detail = response.json().get("message", "")
                assert "execution_mode" in str(error_detail).lower(), \
                    f"Error should mention execution_mode field for mode '{invalid_mode}'"


# ============================================================================
# GET PROJECT WITH EXECUTION_MODE TESTS
# ============================================================================

class TestProjectGetWithExecutionMode:
    """Test GET /api/v1/projects/{id} includes execution_mode."""

    @pytest.mark.asyncio
    async def test_get_project_includes_execution_mode(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """GET /api/v1/projects/{id} should include execution_mode in response."""
        # Create project first
        create_response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Get Test Project",
                "description": "Test GET includes execution_mode",
                "product_id": tenant_a_product["id"],
                "execution_mode": "claude_code_cli"
            },
            cookies={"access_token": tenant_a_token}
        )
        assert create_response.status_code == 201
        project = create_response.json()

        # Get project details
        get_response = await api_client.get(
            f"/api/v1/projects/{project['id']}",
            cookies={"access_token": tenant_a_token}
        )

        # EXPECTED TO FAIL: execution_mode not in response schema yet
        assert get_response.status_code == 200
        data = get_response.json()

        assert "execution_mode" in data, \
            "GET response missing execution_mode field (schema not updated yet)"
        assert data["execution_mode"] == "claude_code_cli", \
            f"Expected 'claude_code_cli', got {data.get('execution_mode')}"

    @pytest.mark.asyncio
    async def test_list_projects_includes_execution_mode(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """GET /api/v1/projects/ should include execution_mode for all projects."""
        # Create projects with different execution modes
        await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "List Test CLI Project",
                "description": "Test list includes execution_mode",
                "product_id": tenant_a_product["id"],
                "execution_mode": "claude_code_cli"
            },
            cookies={"access_token": tenant_a_token}
        )

        await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "List Test Multi-Terminal Project",
                "description": "Test list includes execution_mode",
                "product_id": tenant_a_product["id"],
                "execution_mode": "multi_terminal"
            },
            cookies={"access_token": tenant_a_token}
        )

        # List all projects
        list_response = await api_client.get(
            "/api/v1/projects/",
            cookies={"access_token": tenant_a_token}
        )

        # EXPECTED TO FAIL: execution_mode not in response schema yet
        assert list_response.status_code == 200
        projects = list_response.json()

        assert len(projects) >= 2, "Should have at least 2 test projects"

        for project in projects:
            assert "execution_mode" in project, \
                f"Project {project.get('name')} missing execution_mode field"
            assert project["execution_mode"] in ["claude_code_cli", "multi_terminal"], \
                f"Invalid execution_mode: {project.get('execution_mode')}"


# ============================================================================
# UPDATE PROJECT EXECUTION_MODE TESTS
# ============================================================================

class TestProjectUpdateExecutionMode:
    """Test PATCH /api/v1/projects/{id} updates execution_mode."""

    @pytest.mark.asyncio
    async def test_patch_project_updates_execution_mode_to_cli(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """PATCH /api/v1/projects/{id} should update execution_mode to claude_code_cli."""
        # Create project with default mode
        create_response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Patch CLI Test Project",
                "description": "Test updating to CLI mode",
                "product_id": tenant_a_product["id"]
            },
            cookies={"access_token": tenant_a_token}
        )
        assert create_response.status_code == 201
        project = create_response.json()

        # Update to claude_code_cli
        patch_response = await api_client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"execution_mode": "claude_code_cli"},
            cookies={"access_token": tenant_a_token}
        )

        # EXPECTED TO FAIL: execution_mode not in update schema yet
        assert patch_response.status_code == 200, \
            f"PATCH failed with status {patch_response.status_code}"
        data = patch_response.json()

        assert "execution_mode" in data, \
            "PATCH response missing execution_mode field (schema not updated yet)"
        assert data["execution_mode"] == "claude_code_cli", \
            f"Expected 'claude_code_cli' after PATCH, got {data.get('execution_mode')}"

    @pytest.mark.asyncio
    async def test_patch_project_updates_execution_mode_to_multi_terminal(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """PATCH /api/v1/projects/{id} should update execution_mode to multi_terminal."""
        # Create project with CLI mode
        create_response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Patch Multi-Terminal Test Project",
                "description": "Test updating to multi-terminal mode",
                "product_id": tenant_a_product["id"],
                "execution_mode": "claude_code_cli"
            },
            cookies={"access_token": tenant_a_token}
        )
        assert create_response.status_code == 201
        project = create_response.json()

        # Update back to multi_terminal
        patch_response = await api_client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"execution_mode": "multi_terminal"},
            cookies={"access_token": tenant_a_token}
        )

        # EXPECTED TO FAIL: execution_mode not in update schema yet
        assert patch_response.status_code == 200, \
            f"PATCH failed with status {patch_response.status_code}"
        data = patch_response.json()

        assert "execution_mode" in data, \
            "PATCH response missing execution_mode field (schema not updated yet)"
        assert data["execution_mode"] == "multi_terminal", \
            f"Expected 'multi_terminal' after PATCH, got {data.get('execution_mode')}"

    @pytest.mark.asyncio
    async def test_patch_project_invalid_execution_mode_rejected(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """PATCH with invalid execution_mode should return 400."""
        # Create project
        create_response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Invalid Patch Test Project",
                "description": "Test invalid PATCH rejection",
                "product_id": tenant_a_product["id"]
            },
            cookies={"access_token": tenant_a_token}
        )
        assert create_response.status_code == 201
        project = create_response.json()

        # Try to update with invalid mode
        invalid_modes = ["invalid_mode", "cli_only", "terminal", "", "CLAUDE_CODE_CLI"]

        for invalid_mode in invalid_modes:
            patch_response = await api_client.patch(
                f"/api/v1/projects/{project['id']}",
                json={"execution_mode": invalid_mode},
                cookies={"access_token": tenant_a_token}
            )

            # EXPECTED TO FAIL: validation not implemented yet
            assert patch_response.status_code == 400, \
                f"Expected 400 for invalid mode '{invalid_mode}', got {patch_response.status_code} " \
                f"(validation not implemented yet)"

            # Error should mention execution_mode
            if patch_response.status_code == 400:
                error_detail = patch_response.json().get("message", "")
                assert "execution_mode" in str(error_detail).lower(), \
                    f"Error should mention execution_mode field for mode '{invalid_mode}'"

    @pytest.mark.asyncio
    async def test_patch_project_partial_update_preserves_execution_mode(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """PATCH with other fields should not change execution_mode."""
        # Create project with CLI mode
        create_response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Preserve Mode Test Project",
                "description": "Test execution_mode preservation",
                "product_id": tenant_a_product["id"],
                "execution_mode": "claude_code_cli"
            },
            cookies={"access_token": tenant_a_token}
        )
        assert create_response.status_code == 201
        project = create_response.json()

        # Update name only (not execution_mode)
        patch_response = await api_client.patch(
            f"/api/v1/projects/{project['id']}",
            json={"name": "Updated Name"},
            cookies={"access_token": tenant_a_token}
        )

        # EXPECTED TO FAIL: execution_mode not in schemas yet
        assert patch_response.status_code == 200
        data = patch_response.json()

        assert data["name"] == "Updated Name"
        assert "execution_mode" in data, \
            "PATCH response missing execution_mode field"
        assert data["execution_mode"] == "claude_code_cli", \
            f"execution_mode should remain 'claude_code_cli', got {data.get('execution_mode')}"


# ============================================================================
# MULTI-TENANT ISOLATION TESTS
# ============================================================================

class TestExecutionModeMultiTenantIsolation:
    """Test multi-tenant isolation for execution_mode."""

    @pytest.mark.asyncio
    async def test_different_tenants_different_execution_modes(
        self, api_client: AsyncClient, db_manager
    ):
        """Different tenants can have projects with different execution modes."""
        from passlib.hash import bcrypt
        from src.giljo_mcp.models import User
        from src.giljo_mcp.tenant import TenantManager

        # Create two separate tenants
        tenant_a_key = TenantManager.generate_tenant_key("exec_tenant_a")
        tenant_b_key = TenantManager.generate_tenant_key("exec_tenant_b")

        async with db_manager.get_session_async() as session:
            user_a = User(
                username=f"exec_user_a_{uuid4().hex[:6]}",
                password_hash=bcrypt.hash("password_a"),
                email="exec_a@test.com",
                role="developer",
                tenant_key=tenant_a_key,
                is_active=True,
            )
            user_b = User(
                username=f"exec_user_b_{uuid4().hex[:6]}",
                password_hash=bcrypt.hash("password_b"),
                email="exec_b@test.com",
                role="developer",
                tenant_key=tenant_b_key,
                is_active=True,
            )
            session.add(user_a)
            session.add(user_b)
            await session.commit()

        # Login both users
        login_a = await api_client.post(
            "/api/auth/login",
            json={"username": user_a.username, "password": "password_a"}
        )
        token_a = login_a.cookies.get("access_token")

        login_b = await api_client.post(
            "/api/auth/login",
            json={"username": user_b.username, "password": "password_b"}
        )
        token_b = login_b.cookies.get("access_token")

        # Create products for both tenants
        product_a = await api_client.post(
            "/api/v1/products/",
            json={
                "name": "Exec Tenant A Product",
                "description": "Tenant A product",
                "project_path": "/path/a"
            },
            cookies={"access_token": token_a}
        )
        product_a_id = product_a.json()["id"]

        product_b = await api_client.post(
            "/api/v1/products/",
            json={
                "name": "Exec Tenant B Product",
                "description": "Tenant B product",
                "project_path": "/path/b"
            },
            cookies={"access_token": token_b}
        )
        product_b_id = product_b.json()["id"]

        # Tenant A creates project with multi_terminal
        project_a = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Tenant A Exec Project",
                "description": "Tenant A uses multi_terminal",
                "product_id": product_a_id,
                "execution_mode": "multi_terminal"
            },
            cookies={"access_token": token_a}
        )
        assert project_a.status_code == 201

        # Tenant B creates project with claude_code_cli
        project_b = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Tenant B Exec Project",
                "description": "Tenant B uses CLI",
                "product_id": product_b_id,
                "execution_mode": "claude_code_cli"
            },
            cookies={"access_token": token_b}
        )
        assert project_b.status_code == 201

        # EXPECTED TO FAIL: execution_mode not in schemas yet
        project_a_data = project_a.json()
        project_b_data = project_b.json()

        assert "execution_mode" in project_a_data
        assert "execution_mode" in project_b_data

        assert project_a_data["execution_mode"] == "multi_terminal"
        assert project_b_data["execution_mode"] == "claude_code_cli"

        # Verify isolation - Tenant A cannot see Tenant B's project
        get_b_as_a = await api_client.get(
            f"/api/v1/projects/{project_b_data['id']}",
            cookies={"access_token": token_a}
        )
        assert get_b_as_a.status_code == 404, "Tenant isolation violated"

    @pytest.mark.asyncio
    async def test_cross_tenant_execution_mode_update_blocked(
        self, api_client: AsyncClient, db_manager
    ):
        """Tenant A cannot update Tenant B's project execution_mode."""
        from passlib.hash import bcrypt
        from src.giljo_mcp.models import User
        from src.giljo_mcp.tenant import TenantManager

        # Create two tenants
        tenant_a_key = TenantManager.generate_tenant_key("exec_cross_a")
        tenant_b_key = TenantManager.generate_tenant_key("exec_cross_b")

        async with db_manager.get_session_async() as session:
            user_a = User(
                username=f"exec_cross_a_{uuid4().hex[:6]}",
                password_hash=bcrypt.hash("password_a"),
                email="cross_a@test.com",
                role="developer",
                tenant_key=tenant_a_key,
                is_active=True,
            )
            user_b = User(
                username=f"exec_cross_b_{uuid4().hex[:6]}",
                password_hash=bcrypt.hash("password_b"),
                email="cross_b@test.com",
                role="developer",
                tenant_key=tenant_b_key,
                is_active=True,
            )
            session.add(user_a)
            session.add(user_b)
            await session.commit()

        # Login both
        login_a = await api_client.post(
            "/api/auth/login",
            json={"username": user_a.username, "password": "password_a"}
        )
        token_a = login_a.cookies.get("access_token")

        login_b = await api_client.post(
            "/api/auth/login",
            json={"username": user_b.username, "password": "password_b"}
        )
        token_b = login_b.cookies.get("access_token")

        # Tenant B creates product and project
        product_b = await api_client.post(
            "/api/v1/products/",
            json={
                "name": "Exec Cross Tenant B Product",
                "description": "Tenant B product",
                "project_path": "/path/cross_b"
            },
            cookies={"access_token": token_b}
        )
        product_b_id = product_b.json()["id"]

        project_b = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Tenant B Cross Project",
                "description": "Tenant B project",
                "product_id": product_b_id,
                "execution_mode": "multi_terminal"
            },
            cookies={"access_token": token_b}
        )
        assert project_b.status_code == 201
        project_b_data = project_b.json()

        # Tenant A tries to update Tenant B's execution_mode
        patch_response = await api_client.patch(
            f"/api/v1/projects/{project_b_data['id']}",
            json={"execution_mode": "claude_code_cli"},
            cookies={"access_token": token_a}
        )

        # Should be blocked (404 to prevent info leakage)
        assert patch_response.status_code == 404, \
            f"Cross-tenant PATCH should be blocked, got {patch_response.status_code}"

        # Verify Tenant B's execution_mode is unchanged
        verify_response = await api_client.get(
            f"/api/v1/projects/{project_b_data['id']}",
            cookies={"access_token": token_b}
        )
        assert verify_response.status_code == 200
        verify_data = verify_response.json()

        # EXPECTED TO FAIL: execution_mode not in schemas yet
        if "execution_mode" in verify_data:
            assert verify_data["execution_mode"] == "multi_terminal", \
                "Tenant B's execution_mode should remain unchanged"


# ============================================================================
# RESPONSE SCHEMA VALIDATION
# ============================================================================

class TestExecutionModeSchemaValidation:
    """Test response schema includes execution_mode correctly."""

    @pytest.mark.asyncio
    async def test_project_response_schema_includes_execution_mode(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """ProjectResponse schema should include execution_mode field."""
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Schema Test Project",
                "description": "Test schema validation",
                "product_id": tenant_a_product["id"],
                "execution_mode": "claude_code_cli"
            },
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 201
        data = response.json()

        # EXPECTED TO FAIL: execution_mode not in ProjectResponse schema yet
        required_fields = [
            "id", "alias", "name", "description", "mission", "status",
            "created_at", "updated_at", "context_budget", "context_used",
            "agent_count", "message_count", "execution_mode"  # NEW FIELD
        ]

        for field in required_fields:
            assert field in data, f"ProjectResponse missing required field: {field}"

        # Validate execution_mode type and value
        assert isinstance(data["execution_mode"], str), \
            f"execution_mode should be string, got {type(data['execution_mode'])}"
        assert data["execution_mode"] in ["claude_code_cli", "multi_terminal"], \
            f"Invalid execution_mode value: {data['execution_mode']}"
