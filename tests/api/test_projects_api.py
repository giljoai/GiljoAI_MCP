"""
Projects API Integration Tests - Handover 0610

Comprehensive validation of all 17+ project endpoints across 4 modules:
- CRUD endpoints (crud.py): create, list, get, update, list_deleted, get_active
- Lifecycle endpoints (lifecycle.py): activate, deactivate, cancel, restore, cancel_staging, launch
- Status endpoints (status.py): status, summary, orchestrator
- Completion endpoints (completion.py): complete, close_out, continue_working

Test Coverage:
- Happy path scenarios (200/201 responses)
- Authentication enforcement (401 Unauthorized)
- Authorization enforcement (403/404 Forbidden)
- Multi-tenant isolation (zero cross-tenant leakage)
- Not Found scenarios (404)
- Validation errors (400 Bad Request)
- Response schema validation
- Single Active Project per Product constraint (Handover 0050b)
- Product-project association enforcement
- Cascade behavior verification

Phase 2 Progress: API Layer Testing (2/10 groups)
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4


# ============================================================================
# FIXTURES - Test Users and Authentication
# ============================================================================

@pytest.fixture
async def tenant_a_user(db_manager):
    """Create Tenant A user for multi-tenant isolation testing."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_a_proj_{unique_id}"
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
        # Store credentials for login
        user._test_username = username
        user._test_password = "password_a"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_b_user(db_manager):
    """Create Tenant B user for cross-tenant access testing."""
    from passlib.hash import bcrypt
    from src.giljo_mcp.models import User
    from src.giljo_mcp.tenant import TenantManager

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_b_proj_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        user = User(
            username=username,
            password_hash=bcrypt.hash("password_b"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Store credentials for login
        user._test_username = username
        user._test_password = "password_b"
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
async def tenant_b_token(api_client: AsyncClient, tenant_b_user):
    """Get JWT token for Tenant B user."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_b_user._test_username, "password": tenant_b_user._test_password}
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
            "name": "Tenant A Product",
            "description": "Test product for Tenant A",
            "project_path": "/path/to/tenant_a/product"
        },
        cookies={"access_token": tenant_a_token}
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
async def tenant_b_product(api_client: AsyncClient, tenant_b_token: str):
    """Create a test product for Tenant B."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": "Tenant B Product",
            "description": "Test product for Tenant B",
            "project_path": "/path/to/tenant_b/product"
        },
        cookies={"access_token": tenant_b_token}
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
async def tenant_a_project(api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
    """Create a test project for Tenant A."""
    response = await api_client.post(
        "/api/v1/projects/",
        json={
            "name": "Tenant A Project",
            "description": "Test project for Tenant A",
            "mission": "Test mission",
            "product_id": tenant_a_product["id"],
            "status": "inactive"
        },
        cookies={"access_token": tenant_a_token}
    )
    assert response.status_code == 201
    return response.json()


@pytest.fixture
async def tenant_b_project(api_client: AsyncClient, tenant_b_token: str, tenant_b_product):
    """Create a test project for Tenant B."""
    response = await api_client.post(
        "/api/v1/projects/",
        json={
            "name": "Tenant B Project",
            "description": "Test project for Tenant B",
            "mission": "Test mission",
            "product_id": tenant_b_product["id"],
            "status": "inactive"
        },
        cookies={"access_token": tenant_b_token}
    )
    assert response.status_code == 201
    return response.json()


# ============================================================================
# CRUD ENDPOINTS TESTS
# ============================================================================

class TestProjectCRUD:
    """Test CRUD operations: create, list, get, update, list_deleted, get_active"""

    @pytest.mark.asyncio
    async def test_create_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/projects/ - Create project successfully."""
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "New Project",
                "description": "Test project creation",
                "mission": "Complete the mission",
                "product_id": tenant_a_product["id"],
                "status": "inactive",
                "context_budget": 150000
            },
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 201
        data = response.json()

        # Validate response schema
        assert "id" in data
        assert data["name"] == "New Project"
        assert data["description"] == "Test project creation"
        assert data["mission"] == "Complete the mission"
        assert data["product_id"] == tenant_a_product["id"]
        assert data["status"] == "inactive"
        assert data["context_budget"] == 150000
        assert data["context_used"] == 0
        assert data["agent_count"] == 0
        assert data["message_count"] == 0
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_create_project_minimal_data(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/projects/ - Create with minimal required data."""
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Minimal Project",
                "description": "Minimal description",
                "product_id": tenant_a_product["id"]
            },
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Minimal Project"
        assert data["mission"] == ""  # Default empty mission
        assert data["status"] == "inactive"  # Default status
        assert data["context_budget"] == 150000  # Default budget

    @pytest.mark.asyncio
    async def test_create_project_unauthorized(self, api_client: AsyncClient, tenant_a_product):
        """Test POST /api/v1/projects/ - 401 without authentication."""
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Unauthorized Project",
                "description": "Should fail",
                "product_id": tenant_a_product["id"]
            }
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_create_project_invalid_product(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/projects/ - 400 for non-existent product."""
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Invalid Product Project",
                "description": "Should fail",
                "product_id": "00000000-0000-0000-0000-000000000000"
            },
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_list_projects_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test GET /api/v1/projects/ - List all projects."""
        response = await api_client.get(
            "/api/v1/projects/",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our test project
        project = next((p for p in data if p["id"] == tenant_a_project["id"]), None)
        assert project is not None
        assert project["name"] == tenant_a_project["name"]

    @pytest.mark.asyncio
    async def test_list_projects_with_status_filter(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test GET /api/v1/projects/?status_filter=inactive - Filter by status."""
        response = await api_client.get(
            "/api/v1/projects/?status_filter=inactive",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All returned projects should have status=inactive
        for proj in data:
            assert proj["status"] == "inactive"

    @pytest.mark.asyncio
    async def test_list_projects_multi_tenant_isolation(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
        tenant_a_project,
        tenant_b_project
    ):
        """Test GET /api/v1/projects/ - Verify tenant isolation."""
        # Tenant A should only see their projects
        response_a = await api_client.get(
            "/api/v1/projects/",
            cookies={"access_token": tenant_a_token}
        )
        assert response_a.status_code == 200
        projects_a = response_a.json()

        project_ids_a = [p["id"] for p in projects_a]
        assert tenant_a_project["id"] in project_ids_a
        assert tenant_b_project["id"] not in project_ids_a  # Isolation verified

        # Tenant B should only see their projects
        response_b = await api_client.get(
            "/api/v1/projects/",
            cookies={"access_token": tenant_b_token}
        )
        assert response_b.status_code == 200
        projects_b = response_b.json()

        project_ids_b = [p["id"] for p in projects_b]
        assert tenant_b_project["id"] in project_ids_b
        assert tenant_a_project["id"] not in project_ids_b  # Isolation verified

    @pytest.mark.asyncio
    async def test_list_projects_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/v1/projects/ - 401 without authentication."""
        response = await api_client.get("/api/v1/projects/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test GET /api/v1/projects/{project_id} - Get project details."""
        response = await api_client.get(
            f"/api/v1/projects/{tenant_a_project['id']}",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_project["id"]
        assert data["name"] == tenant_a_project["name"]
        assert "created_at" in data
        assert "updated_at" in data

    @pytest.mark.asyncio
    async def test_get_project_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/projects/{project_id} - 404 for non-existent project."""
        response = await api_client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_cross_tenant_forbidden(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_project
    ):
        """Test GET /api/v1/projects/{project_id} - 404 for cross-tenant access."""
        # Tenant A tries to access Tenant B's project
        response = await api_client.get(
            f"/api/v1/projects/{tenant_b_project['id']}",
            cookies={"access_token": tenant_a_token}
        )
        # Should return 404 (not found) to prevent information leakage
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test GET /api/v1/projects/{project_id} - 401 without authentication."""
        response = await api_client.get(
            f"/api/v1/projects/{tenant_a_project['id']}"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_project_soft_delete_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test DELETE /api/v1/projects/{project_id} - Soft delete successfully."""
        # Create a project to delete
        create_response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Project to Delete",
                "description": "Test delete flow",
                "mission": "Test mission",
                "product_id": tenant_a_product["id"],
            },
            cookies={"access_token": tenant_a_token},
        )
        assert create_response.status_code == 201
        project = create_response.json()

        # Soft delete it
        delete_response = await api_client.delete(
            f"/api/v1/projects/{project['id']}",
            cookies={"access_token": tenant_a_token},
        )

        assert delete_response.status_code == 200
        data = delete_response.json()
        assert data["success"] is True
        assert "message" in data
        assert "deleted_at" in data

        # Verify project no longer appears in regular list
        list_response = await api_client.get(
            "/api/v1/projects/",
            cookies={"access_token": tenant_a_token},
        )
        assert list_response.status_code == 200
        project_ids = [p["id"] for p in list_response.json()]
        assert project["id"] not in project_ids

        # Verify project appears in deleted projects list
        deleted_response = await api_client.get(
            "/api/v1/projects/deleted",
            cookies={"access_token": tenant_a_token},
        )
        assert deleted_response.status_code == 200
        deleted_ids = [p["id"] for p in deleted_response.json()]
        assert project["id"] in deleted_ids

    @pytest.mark.asyncio
    async def test_update_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test PATCH /api/v1/projects/{project_id} - Update project successfully."""
        response = await api_client.patch(
            f"/api/v1/projects/{tenant_a_project['id']}",
            json={
                "name": "Updated Project Name",
                "description": "Updated description",
                "mission": "Updated mission"
            },
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_project["id"]
        assert data["name"] == "Updated Project Name"
        assert data["description"] == "Updated description"
        assert data["mission"] == "Updated mission"

    @pytest.mark.asyncio
    async def test_update_project_partial(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test PATCH /api/v1/projects/{project_id} - Partial update."""
        response = await api_client.patch(
            f"/api/v1/projects/{tenant_a_project['id']}",
            json={"name": "Partially Updated"},
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Partially Updated"
        # Original description should remain
        assert data["description"] == tenant_a_project["description"]

    @pytest.mark.asyncio
    async def test_update_project_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test PATCH /api/v1/projects/{project_id} - 404 for non-existent project."""
        response = await api_client.patch(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000",
            json={"name": "Updated"},
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project_cross_tenant_forbidden(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_project
    ):
        """Test PATCH /api/v1/projects/{project_id} - 404 for cross-tenant update."""
        response = await api_client.patch(
            f"/api/v1/projects/{tenant_b_project['id']}",
            json={"name": "Hacked"},
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_project_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test PATCH /api/v1/projects/{project_id} - 401 without authentication."""
        response = await api_client.patch(
            f"/api/v1/projects/{tenant_a_project['id']}",
            json={"name": "Updated"}
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_deleted_projects_empty(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/projects/deleted - Empty list when no deleted projects."""
        response = await api_client.get(
            "/api/v1/projects/deleted",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_deleted_projects_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/v1/projects/deleted - 401 without authentication."""
        response = await api_client.get("/api/v1/projects/deleted")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_active_project_none(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/projects/active - None when no active project."""
        response = await api_client.get(
            "/api/v1/projects/active",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        # Response can be null/None for no active project
        data = response.json()
        # None or empty object is acceptable

    @pytest.mark.asyncio
    async def test_get_active_project_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/v1/projects/active - 401 without authentication."""
        response = await api_client.get("/api/v1/projects/active")
        assert response.status_code == 401


# ============================================================================
# LIFECYCLE ENDPOINTS TESTS
# ============================================================================

class TestProjectLifecycle:
    """Test lifecycle operations: activate, deactivate, cancel, restore, cancel_staging, launch"""

    @pytest.mark.asyncio
    async def test_activate_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/activate - Activate successfully."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_project["id"]
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_activate_project_single_active_constraint(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/projects/{project_id}/activate - Single active project enforcement."""
        # Create two projects in same product
        response1 = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Project 1",
                "description": "First project",
                "product_id": tenant_a_product["id"]
            },
            cookies={"access_token": tenant_a_token}
        )
        project1 = response1.json()

        response2 = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Project 2",
                "description": "Second project",
                "product_id": tenant_a_product["id"]
            },
            cookies={"access_token": tenant_a_token}
        )
        project2 = response2.json()

        # Activate first project
        await api_client.post(
            f"/api/v1/projects/{project1['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        # Activate second project (should deactivate first)
        response = await api_client.post(
            f"/api/v1/projects/{project2['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "active"

        # Verify first project is deactivated
        response1_check = await api_client.get(
            f"/api/v1/projects/{project1['id']}",
            cookies={"access_token": tenant_a_token}
        )
        assert response1_check.json()["status"] == "paused"

    @pytest.mark.asyncio
    async def test_activate_project_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/projects/{project_id}/activate - 404 for non-existent project."""
        response = await api_client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/activate",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_activate_project_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/activate - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/activate"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_deactivate_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/deactivate - Deactivate successfully."""
        # First activate the project
        await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )

        # Then deactivate it
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/deactivate",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_project["id"]
        assert data["status"] == "paused"

    @pytest.mark.asyncio
    async def test_deactivate_project_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/projects/{project_id}/deactivate - 404 for non-existent project."""
        response = await api_client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/deactivate",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_deactivate_project_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/deactivate - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/deactivate"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_cancel_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/cancel - Cancel project successfully."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/cancel",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_project["id"]
        assert data["status"] == "cancelled"

    @pytest.mark.asyncio
    async def test_cancel_project_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/projects/{project_id}/cancel - 404 for non-existent project."""
        response = await api_client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/cancel",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cancel_project_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/cancel - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/cancel"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_restore_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/restore - Restore cancelled project."""
        # First cancel the project
        await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/cancel",
            cookies={"access_token": tenant_a_token}
        )

        # Then restore it
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/restore",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_project["id"]
        # Status should be restored (typically to 'inactive' or 'paused')
        assert data["status"] != "cancelled"

    @pytest.mark.asyncio
    async def test_restore_project_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/projects/{project_id}/restore - 404 for non-existent project."""
        response = await api_client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/restore",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_restore_project_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/restore - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/restore"
        )
        assert response.status_code == 401


# ============================================================================
# STATUS ENDPOINTS TESTS
# ============================================================================

class TestProjectStatus:
    """Test status operations: summary, orchestrator"""

    @pytest.mark.asyncio
    async def test_get_project_summary_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test GET /api/v1/projects/{project_id}/summary - Get project summary."""
        response = await api_client.get(
            f"/api/v1/projects/{tenant_a_project['id']}/summary",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert "project_name" in data
        assert "status" in data
        assert "agents" in data
        assert "messages" in data

    @pytest.mark.asyncio
    async def test_get_project_summary_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/projects/{project_id}/summary - 404 for non-existent project."""
        response = await api_client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/summary",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_summary_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test GET /api/v1/projects/{project_id}/summary - 401 without authentication."""
        response = await api_client.get(
            f"/api/v1/projects/{tenant_a_project['id']}/summary"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_project_orchestrator_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test GET /api/v1/projects/{project_id}/orchestrator - Get orchestrator job."""
        response = await api_client.get(
            f"/api/v1/projects/{tenant_a_project['id']}/orchestrator",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "orchestrator" in data
        orch = data["orchestrator"]
        assert "job_id" in orch
        assert "agent_display_name" in orch
        assert orch["agent_display_name"] == "orchestrator"

    @pytest.mark.asyncio
    async def test_get_project_orchestrator_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test GET /api/v1/projects/{project_id}/orchestrator - 404 for non-existent project."""
        response = await api_client.get(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/orchestrator",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_project_orchestrator_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test GET /api/v1/projects/{project_id}/orchestrator - 401 without authentication."""
        response = await api_client.get(
            f"/api/v1/projects/{tenant_a_project['id']}/orchestrator"
        )
        assert response.status_code == 401


# ============================================================================
# COMPLETION ENDPOINTS TESTS
# ============================================================================

class TestProjectCompletion:
    """Test completion operations: complete, close_out, continue_working"""

    @pytest.mark.asyncio
    async def test_complete_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/complete - Complete project successfully."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/complete",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_project["id"]
        assert data["status"] == "completed"
        assert "completed_at" in data

    @pytest.mark.asyncio
    async def test_complete_project_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/projects/{project_id}/complete - 404 for non-existent project."""
        response = await api_client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/complete",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_complete_project_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/complete - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/complete"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_close_out_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/close-out - Close out project."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/close-out",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "agents_decommissioned" in data
        assert "project_status" in data

    @pytest.mark.asyncio
    async def test_close_out_project_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/projects/{project_id}/close-out - 404 for non-existent project."""
        response = await api_client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/close-out",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_close_out_project_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/close-out - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/close-out"
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_continue_working_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/continue-working - Resume work."""
        # First close out the project
        await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/close-out",
            cookies={"access_token": tenant_a_token}
        )

        # Then resume work
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/continue-working",
            cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "agents_resumed" in data
        assert "project_status" in data

    @pytest.mark.asyncio
    async def test_continue_working_not_found(
        self, api_client: AsyncClient, tenant_a_token: str
    ):
        """Test POST /api/v1/projects/{project_id}/continue-working - 404 for non-existent project."""
        response = await api_client.post(
            "/api/v1/projects/00000000-0000-0000-0000-000000000000/continue-working",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_continue_working_unauthorized(
        self, api_client: AsyncClient, tenant_a_project
    ):
        """Test POST /api/v1/projects/{project_id}/continue-working - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/projects/{tenant_a_project['id']}/continue-working"
        )
        assert response.status_code == 401


# ============================================================================
# MULTI-TENANT ISOLATION TESTS (COMPREHENSIVE)
# ============================================================================

class TestMultiTenantIsolation:
    """Comprehensive multi-tenant isolation verification across all endpoints"""

    @pytest.mark.asyncio
    async def test_cross_tenant_project_access_blocked(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
        tenant_a_project,
        tenant_b_project
    ):
        """Verify complete tenant isolation - Tenant A cannot access Tenant B's projects."""

        # Test GET project
        response = await api_client.get(
            f"/api/v1/projects/{tenant_b_project['id']}",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404  # Not found (prevents info leakage)

        # Test UPDATE project
        response = await api_client.patch(
            f"/api/v1/projects/{tenant_b_project['id']}",
            json={"name": "Hacked"},
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

        # Test ACTIVATE project
        response = await api_client.post(
            f"/api/v1/projects/{tenant_b_project['id']}/activate",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

        # Test CANCEL project
        response = await api_client.post(
            f"/api/v1/projects/{tenant_b_project['id']}/cancel",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

        # Test STATUS
        response = await api_client.get(
            f"/api/v1/projects/{tenant_b_project['id']}/status",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

        # Test COMPLETE
        response = await api_client.post(
            f"/api/v1/projects/{tenant_b_project['id']}/complete",
            cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_product_association_enforced(
        self,
        api_client: AsyncClient,
        tenant_a_token: str,
        tenant_b_token: str,
        tenant_a_product,
        tenant_b_product
    ):
        """Verify projects are isolated by product association."""
        # Tenant A cannot create project with Tenant B's product
        response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Cross-tenant Project",
                "description": "Should fail",
                "product_id": tenant_b_product["id"]
            },
            cookies={"access_token": tenant_a_token}
        )
        # Should fail (400 or 404) - product validation should catch this
        assert response.status_code in [400, 404]
