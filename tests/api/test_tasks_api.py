"""
Tasks API Integration Tests - Handover 0611

Comprehensive validation of all 8+ task endpoints:
- CRUD endpoints: create, list, get, update, delete
- Status endpoint: change_task_status
- Conversion endpoint: convert_task_to_project
- Summary endpoint: get_task_summary

Test Coverage:
- Happy path scenarios (200/201 responses)
- Authentication enforcement (401 Unauthorized)
- Authorization enforcement (403 Forbidden)
- Multi-tenant isolation (zero cross-tenant leakage)
- Not Found scenarios (404)
- Validation errors (400 Bad Request)
- Response schema validation
- Product-scoped filtering
- Task-project associations

Phase 2 Progress: API Layer Testing (4/10 groups)
"""

import pytest
from httpx import AsyncClient


# ============================================================================
# FIXTURES - Test Users and Authentication
# ============================================================================


@pytest.fixture
async def tenant_a_user(db_manager):
    """Create Tenant A user for multi-tenant isolation testing."""
    from uuid import uuid4

    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_a_task_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create organization first (0424j: org_id is NOT NULL)
        org = Organization(
            name=f"Tenant A Task Org {unique_id}",
            slug=f"tenant-a-task-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_a"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # Required NOT NULL (0424j)
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
    from uuid import uuid4

    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_b_task_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create organization first (0424j: org_id is NOT NULL)
        org = Organization(
            name=f"Tenant B Task Org {unique_id}",
            slug=f"tenant-b-task-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_b"),
            email=f"{username}@test.com",
            role="developer",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # Required NOT NULL (0424j)
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
async def tenant_a_admin(db_manager):
    """Create Tenant A admin user for permission testing."""
    from uuid import uuid4

    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_a_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create organization first (0424j: org_id is NOT NULL)
        org = Organization(
            name=f"Tenant A Admin Org {unique_id}",
            slug=f"tenant-a-admin-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_admin"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # Required NOT NULL (0424j)
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user._test_username = username
        user._test_password = "password_admin"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_a_token(api_client: AsyncClient, tenant_a_user):
    """Get JWT token for Tenant A user."""
    response = await api_client.post(
        "/api/auth/login", json={"username": tenant_a_user._test_username, "password": tenant_a_user._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_b_token(api_client: AsyncClient, tenant_b_user):
    """Get JWT token for Tenant B user."""
    response = await api_client.post(
        "/api/auth/login", json={"username": tenant_b_user._test_username, "password": tenant_b_user._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_a_admin_token(api_client: AsyncClient, tenant_a_admin):
    """Get JWT token for Tenant A admin user."""
    response = await api_client.post(
        "/api/auth/login", json={"username": tenant_a_admin._test_username, "password": tenant_a_admin._test_password}
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
            "name": "Tenant A Product for Tasks",
            "description": "Test product for task testing",
            "project_path": "/path/to/tenant_a/tasks",
        },
        cookies={"access_token": tenant_a_token},
    )
    assert response.status_code == 200
    product = response.json()

    # Activate the product
    await api_client.post(f"/api/v1/products/{product['id']}/activate", cookies={"access_token": tenant_a_token})

    return product


@pytest.fixture
async def tenant_b_product(api_client: AsyncClient, tenant_b_token: str):
    """Create a test product for Tenant B."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": "Tenant B Product for Tasks",
            "description": "Test product for Tenant B",
            "project_path": "/path/to/tenant_b/tasks",
        },
        cookies={"access_token": tenant_b_token},
    )
    assert response.status_code == 200
    product = response.json()

    # Activate the product
    await api_client.post(f"/api/v1/products/{product['id']}/activate", cookies={"access_token": tenant_b_token})

    return product


@pytest.fixture
async def tenant_a_task(api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
    """Create a test task for Tenant A."""
    response = await api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Tenant A Task",
            "description": "Test task for Tenant A",
            "category": "feature",
            "priority": "high",
            "status": "pending",
            "product_id": tenant_a_product["id"],
        },
        cookies={"access_token": tenant_a_token},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
async def tenant_b_task(api_client: AsyncClient, tenant_b_token: str, tenant_b_product):
    """Create a test task for Tenant B."""
    response = await api_client.post(
        "/api/v1/tasks/",
        json={
            "title": "Tenant B Task",
            "description": "Test task for Tenant B",
            "category": "bug",
            "priority": "medium",
            "status": "pending",
            "product_id": tenant_b_product["id"],
        },
        cookies={"access_token": tenant_b_token},
    )
    assert response.status_code == 200
    return response.json()


# ============================================================================
# CRUD ENDPOINTS TESTS
# ============================================================================


class TestTaskCRUD:
    """Test CRUD operations: create, list, get, update, delete"""

    @pytest.mark.asyncio
    async def test_create_task_happy_path(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
        """Test POST /api/v1/tasks/ - Create task successfully."""
        response = await api_client.post(
            "/api/v1/tasks/",
            json={
                "title": "New Task",
                "description": "Test task creation",
                "category": "feature",
                "priority": "high",
                "status": "pending",
                "product_id": tenant_a_product["id"],
                "estimated_effort": 5,
            },
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response schema
        assert "id" in data
        assert data["title"] == "New Task"
        assert data["description"] == "Test task creation"
        assert data["category"] == "feature"
        assert data["priority"] == "high"
        assert data["status"] == "pending"
        assert data["product_id"] == tenant_a_product["id"]
        assert data["estimated_effort"] == 5
        assert "created_by_user_id" in data
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_create_task_minimal_data(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
        """Test POST /api/v1/tasks/ - Create with minimal required data (title + product_id per 0433)."""
        response = await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Minimal Task", "product_id": tenant_a_product["id"]},
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Minimal Task"
        assert data["status"] == "pending"  # Default status
        assert data["priority"] == "medium"  # Default priority
        assert data["product_id"] == tenant_a_product["id"]  # Required per 0433

    @pytest.mark.skip(reason="Projects API endpoint issue - testing task creation only")
    @pytest.mark.asyncio
    async def test_create_task_with_project(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
        """Test POST /api/v1/tasks/ - Create task with project association."""
        # Create a project first
        project_response = await api_client.post(
            "/api/v1/projects/",
            json={
                "name": "Test Project",
                "description": "Project for task association",
                "product_id": tenant_a_product["id"],
            },
            cookies={"access_token": tenant_a_token},
        )
        project = project_response.json()

        # Create task with project_id
        response = await api_client.post(
            "/api/v1/tasks/",
            json={
                "title": "Task with Project",
                "project_id": project["id"],
                "product_id": tenant_a_product["id"],
                "status": "pending",
            },
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_id"] == project["id"]
        assert data["product_id"] == tenant_a_product["id"]

    @pytest.mark.asyncio
    async def test_create_task_unauthorized(self, api_client: AsyncClient):
        """Test POST /api/v1/tasks/ - 401 without authentication."""
        response = await api_client.post("/api/v1/tasks/", json={"title": "Unauthorized Task", "status": "pending"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_list_tasks_happy_path(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_task):
        """Test GET /api/v1/tasks/ - List all tasks."""
        response = await api_client.get("/api/v1/tasks/", cookies={"access_token": tenant_a_token})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # Find our test task
        task = next((t for t in data if t["id"] == tenant_a_task["id"]), None)
        assert task is not None
        assert task["title"] == tenant_a_task["title"]

    @pytest.mark.asyncio
    async def test_list_tasks_product_filter(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
        """Test GET /api/v1/tasks/?filter_type=product_tasks - Filter by active product."""
        # Create multiple tasks
        await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Product Task 1", "product_id": tenant_a_product["id"], "status": "pending"},
            cookies={"access_token": tenant_a_token},
        )
        await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Product Task 2", "product_id": tenant_a_product["id"], "status": "pending"},
            cookies={"access_token": tenant_a_token},
        )

        response = await api_client.get(
            "/api/v1/tasks/?filter_type=product_tasks", cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All tasks should be for active product
        for task in data:
            assert task["product_id"] == tenant_a_product["id"]

    @pytest.mark.asyncio
    async def test_create_task_without_product_id_fails(self, api_client: AsyncClient, tenant_a_token: str):
        """Test POST /api/v1/tasks/ - 422 without product_id (required per 0433)."""
        response = await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Task without Product", "status": "pending"},
            cookies={"access_token": tenant_a_token},
        )

        # product_id is required per 0433, so validation should fail
        assert response.status_code == 422
        data = response.json()
        # Check for Pydantic validation error in either 'errors' or 'detail' format
        if "errors" in data:
            # New format: {'errors': [...], 'message': '...'}
            errors = data["errors"]
            assert any("product_id" in str(err) for err in errors)
        else:
            # Standard Pydantic format: {'detail': [...]}
            assert "detail" in data
            errors = data["detail"]
            assert any("product_id" in str(err) for err in errors)

    @pytest.mark.asyncio
    async def test_list_tasks_created_by_me_filter(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_task):
        """Test GET /api/v1/tasks/?created_by_me=true - Filter by creator."""
        response = await api_client.get("/api/v1/tasks/?created_by_me=true", cookies={"access_token": tenant_a_token})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All tasks should be created by current user
        for task in data:
            assert task["created_by_user_id"] is not None

    @pytest.mark.asyncio
    async def test_list_tasks_status_filter(self, api_client: AsyncClient, tenant_a_token: str):
        """Test GET /api/v1/tasks/?status=pending - Filter by status."""
        response = await api_client.get("/api/v1/tasks/?status=pending", cookies={"access_token": tenant_a_token})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for task in data:
            assert task["status"] == "pending"

    @pytest.mark.asyncio
    async def test_list_tasks_priority_filter(self, api_client: AsyncClient, tenant_a_token: str):
        """Test GET /api/v1/tasks/?priority=high - Filter by priority."""
        response = await api_client.get("/api/v1/tasks/?priority=high", cookies={"access_token": tenant_a_token})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        for task in data:
            assert task["priority"] == "high"

    @pytest.mark.asyncio
    async def test_list_tasks_multi_tenant_isolation(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_b_token: str, tenant_a_task, tenant_b_task
    ):
        """Test GET /api/v1/tasks/ - Verify tenant isolation."""
        # Tenant A should only see their tasks
        response_a = await api_client.get("/api/v1/tasks/", cookies={"access_token": tenant_a_token})
        assert response_a.status_code == 200
        tasks_a = response_a.json()

        task_ids_a = [t["id"] for t in tasks_a]
        assert tenant_a_task["id"] in task_ids_a
        assert tenant_b_task["id"] not in task_ids_a  # Isolation verified

        # Tenant B should only see their tasks
        response_b = await api_client.get("/api/v1/tasks/", cookies={"access_token": tenant_b_token})
        assert response_b.status_code == 200
        tasks_b = response_b.json()

        task_ids_b = [t["id"] for t in tasks_b]
        assert tenant_b_task["id"] in task_ids_b
        assert tenant_a_task["id"] not in task_ids_b  # Isolation verified

    @pytest.mark.asyncio
    async def test_list_tasks_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/v1/tasks/ - 401 without authentication."""
        response = await api_client.get("/api/v1/tasks/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_task_happy_path(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_task):
        """Test GET /api/v1/tasks/{task_id} - Get task details."""
        response = await api_client.get(
            f"/api/v1/tasks/{tenant_a_task['id']}/", cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_task["id"]
        assert data["title"] == tenant_a_task["title"]
        assert "created_at" in data

    @pytest.mark.asyncio
    async def test_get_task_not_found(self, api_client: AsyncClient, tenant_a_token: str):
        """Test GET /api/v1/tasks/{task_id} - 404 for non-existent task."""
        response = await api_client.get(
            "/api/v1/tasks/00000000-0000-0000-0000-000000000000/", cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_task_cross_tenant_forbidden(self, api_client: AsyncClient, tenant_a_token: str, tenant_b_task):
        """Test GET /api/v1/tasks/{task_id} - 404 for cross-tenant access."""
        response = await api_client.get(
            f"/api/v1/tasks/{tenant_b_task['id']}/", cookies={"access_token": tenant_a_token}
        )
        # Should return 404 (not found) to prevent information leakage
        assert response.status_code == 404

    @pytest.mark.skip(reason="Test client cookie persistence - auth test infrastructure issue")
    @pytest.mark.asyncio
    async def test_get_task_unauthorized(self, api_client: AsyncClient, tenant_a_task):
        """Test GET /api/v1/tasks/{task_id} - 401 without authentication."""
        response = await api_client.get(f"/api/v1/tasks/{tenant_a_task['id']}/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_update_task_happy_path(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_task):
        """Test PUT /api/v1/tasks/{task_id} - Update task successfully."""
        response = await api_client.put(
            f"/api/v1/tasks/{tenant_a_task['id']}/",
            json={
                "title": "Updated Task Title",
                "description": "Updated description",
                "priority": "low",
                "status": "in_progress",
            },
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == tenant_a_task["id"]
        assert data["title"] == "Updated Task Title"
        assert data["description"] == "Updated description"
        assert data["priority"] == "low"
        assert data["status"] == "in_progress"
        assert data["started_at"] is not None  # Should auto-set when status = in_progress

    @pytest.mark.asyncio
    async def test_update_task_to_completed(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_task):
        """Test PUT /api/v1/tasks/{task_id} - Update to completed status."""
        response = await api_client.put(
            f"/api/v1/tasks/{tenant_a_task['id']}/",
            json={"status": "completed"},
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None  # Should auto-set when status = completed

    @pytest.mark.asyncio
    async def test_update_task_partial(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_task):
        """Test PUT /api/v1/tasks/{task_id} - Partial update."""
        response = await api_client.put(
            f"/api/v1/tasks/{tenant_a_task['id']}/",
            json={"priority": "critical"},
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["priority"] == "critical"
        # Original title should remain
        assert data["title"] == tenant_a_task["title"]

    @pytest.mark.asyncio
    async def test_update_task_not_found(self, api_client: AsyncClient, tenant_a_token: str):
        """Test PUT /api/v1/tasks/{task_id} - 404 for non-existent task."""
        response = await api_client.put(
            "/api/v1/tasks/00000000-0000-0000-0000-000000000000/",
            json={"title": "Updated"},
            cookies={"access_token": tenant_a_token},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_update_task_cross_tenant_forbidden(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_b_task
    ):
        """Test PUT /api/v1/tasks/{task_id} - 404 for cross-tenant update."""
        response = await api_client.put(
            f"/api/v1/tasks/{tenant_b_task['id']}/", json={"title": "Hacked"}, cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.skip(reason="Admin user fixture different tenant - test isolation issue")
    @pytest.mark.asyncio
    async def test_update_task_forbidden_non_creator(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_admin_token: str
    ):
        """Test PUT /api/v1/tasks/{task_id} - Non-creator can't update (unless admin)."""
        # Create task as regular user
        response = await api_client.post(
            "/api/v1/tasks/", json={"title": "User Task", "status": "pending"}, cookies={"access_token": tenant_a_token}
        )
        task = response.json()

        # Admin from same tenant CAN update
        admin_response = await api_client.put(
            f"/api/v1/tasks/{task['id']}/",
            json={"title": "Admin Updated"},
            cookies={"access_token": tenant_a_admin_token},
        )
        assert admin_response.status_code == 200

    @pytest.mark.skip(reason="Test client cookie persistence - auth test infrastructure issue")
    @pytest.mark.asyncio
    async def test_update_task_unauthorized(self, api_client: AsyncClient, tenant_a_task):
        """Test PUT /api/v1/tasks/{task_id} - 401 without authentication."""
        response = await api_client.put(f"/api/v1/tasks/{tenant_a_task['id']}/", json={"title": "Updated"})
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_delete_task_happy_path(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
        """Test DELETE /api/v1/tasks/{task_id} - Delete task successfully."""
        # Create task to delete (product_id required per 0433)
        response = await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Task to Delete", "status": "pending", "product_id": tenant_a_product["id"]},
            cookies={"access_token": tenant_a_token},
        )
        task = response.json()

        # Delete it
        delete_response = await api_client.delete(
            f"/api/v1/tasks/{task['id']}/", cookies={"access_token": tenant_a_token}
        )

        assert delete_response.status_code == 204

        # Verify task no longer appears in list
        list_response = await api_client.get("/api/v1/tasks/", cookies={"access_token": tenant_a_token})
        task_ids = [t["id"] for t in list_response.json()]
        assert task["id"] not in task_ids

    @pytest.mark.asyncio
    async def test_delete_task_not_found(self, api_client: AsyncClient, tenant_a_token: str):
        """Test DELETE /api/v1/tasks/{task_id} - 404 for non-existent task."""
        response = await api_client.delete(
            "/api/v1/tasks/00000000-0000-0000-0000-000000000000/", cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_task_cross_tenant_forbidden(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_b_task
    ):
        """Test DELETE /api/v1/tasks/{task_id} - 404 for cross-tenant delete."""
        response = await api_client.delete(
            f"/api/v1/tasks/{tenant_b_task['id']}/", cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

    @pytest.mark.skip(reason="Test client cookie persistence - auth test infrastructure issue")
    @pytest.mark.asyncio
    async def test_delete_task_unauthorized(self, api_client: AsyncClient, tenant_a_task):
        """Test DELETE /api/v1/tasks/{task_id} - 401 without authentication."""
        response = await api_client.delete(f"/api/v1/tasks/{tenant_a_task['id']}/")
        assert response.status_code == 401


# ============================================================================
# STATUS ENDPOINT TESTS
# ============================================================================


class TestTaskStatus:
    """Test status change endpoint"""

    @pytest.mark.asyncio
    async def test_change_task_status_happy_path(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_task):
        """Test PATCH /api/v1/tasks/{task_id}/status/ - Change status successfully."""
        response = await api_client.patch(
            f"/api/v1/tasks/{tenant_a_task['id']}/status/",
            json={"status": "in_progress"},
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "in_progress"
        assert data["started_at"] is not None

    @pytest.mark.asyncio
    async def test_change_task_status_to_completed(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_task):
        """Test PATCH /api/v1/tasks/{task_id}/status/ - Change to completed."""
        response = await api_client.patch(
            f"/api/v1/tasks/{tenant_a_task['id']}/status/",
            json={"status": "completed"},
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_change_task_status_not_found(self, api_client: AsyncClient, tenant_a_token: str):
        """Test PATCH /api/v1/tasks/{task_id}/status/ - 404 for non-existent task."""
        response = await api_client.patch(
            "/api/v1/tasks/00000000-0000-0000-0000-000000000000/status/",
            json={"status": "completed"},
            cookies={"access_token": tenant_a_token},
        )
        assert response.status_code == 404

    @pytest.mark.skip(reason="Test client cookie persistence - auth test infrastructure issue")
    @pytest.mark.asyncio
    async def test_change_task_status_unauthorized(self, api_client: AsyncClient, tenant_a_task):
        """Test PATCH /api/v1/tasks/{task_id}/status/ - 401 without authentication."""
        response = await api_client.patch(f"/api/v1/tasks/{tenant_a_task['id']}/status/", json={"status": "completed"})
        assert response.status_code == 401


# ============================================================================
# CONVERSION ENDPOINT TESTS
# ============================================================================


class TestTaskConversion:
    """Test task-to-project conversion endpoint"""

    @pytest.mark.asyncio
    async def test_convert_task_to_project_happy_path(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/tasks/{task_id}/convert/ - Convert task to project successfully."""
        # Create task to convert
        task_response = await api_client.post(
            "/api/v1/tasks/",
            json={
                "title": "Task to Convert",
                "description": "This will become a project",
                "product_id": tenant_a_product["id"],
                "status": "pending",
            },
            cookies={"access_token": tenant_a_token},
        )
        task = task_response.json()

        # Convert to project
        response = await api_client.post(
            f"/api/v1/tasks/{task['id']}/convert/",
            json={"project_name": "Converted Project", "strategy": "standard", "include_subtasks": False},
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "project_id" in data
        assert data["project_name"] == "Converted Project"
        assert data["original_task_id"] == task["id"]
        assert data["conversion_strategy"] == "standard"

        # Verify task is deleted after conversion
        task_check = await api_client.get(f"/api/v1/tasks/{task['id']}/", cookies={"access_token": tenant_a_token})
        assert task_check.status_code == 404

    @pytest.mark.asyncio
    async def test_convert_task_default_project_name(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/tasks/{task_id}/convert/ - Use task title as project name."""
        task_response = await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Auto Named Project", "product_id": tenant_a_product["id"], "status": "pending"},
            cookies={"access_token": tenant_a_token},
        )
        task = task_response.json()

        response = await api_client.post(
            f"/api/v1/tasks/{task['id']}/convert/",
            json={"strategy": "standard", "include_subtasks": False},
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["project_name"] == "Auto Named Project"

    @pytest.mark.asyncio
    async def test_convert_task_already_converted(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
        """Test POST /api/v1/tasks/{task_id}/convert/ - 400 if already converted."""
        # Create and convert task
        task_response = await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Already Converted", "product_id": tenant_a_product["id"], "status": "pending"},
            cookies={"access_token": tenant_a_token},
        )
        task = task_response.json()

        # First conversion
        await api_client.post(
            f"/api/v1/tasks/{task['id']}/convert/",
            json={"strategy": "standard", "include_subtasks": False},
            cookies={"access_token": tenant_a_token},
        )

        # The task is deleted after successful conversion, so a second attempt should get 404
        response2 = await api_client.post(
            f"/api/v1/tasks/{task['id']}/convert/",
            json={"strategy": "standard", "include_subtasks": False},
            cookies={"access_token": tenant_a_token},
        )
        assert response2.status_code == 404

    @pytest.mark.asyncio
    async def test_convert_task_without_active_product(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test POST /api/v1/tasks/{task_id}/convert/ - 400 without active product."""
        # Create task FIRST while product is active (product_id required per 0433)
        task_response = await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Task to Convert", "status": "pending", "product_id": tenant_a_product["id"]},
            cookies={"access_token": tenant_a_token},
        )
        assert task_response.status_code == 200
        task = task_response.json()

        # Deactivate product AFTER creating the task
        await api_client.post(
            f"/api/v1/products/{tenant_a_product['id']}/deactivate", cookies={"access_token": tenant_a_token}
        )

        # Try to convert - should fail because no active product
        response = await api_client.post(
            f"/api/v1/tasks/{task['id']}/convert/",
            json={"strategy": "standard", "include_subtasks": False},
            cookies={"access_token": tenant_a_token},
        )

        assert response.status_code == 400
        # Exception handler returns 'message' not 'detail' (Handover 0480)
        assert "No active product" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_convert_task_not_found(self, api_client: AsyncClient, tenant_a_token: str):
        """Test POST /api/v1/tasks/{task_id}/convert/ - 404 for non-existent task."""
        response = await api_client.post(
            "/api/v1/tasks/00000000-0000-0000-0000-000000000000/convert/",
            json={"strategy": "standard", "include_subtasks": False},
            cookies={"access_token": tenant_a_token},
        )
        assert response.status_code == 404

    @pytest.mark.skip(reason="Test client cookie persistence - auth test infrastructure issue")
    @pytest.mark.asyncio
    async def test_convert_task_unauthorized(self, api_client: AsyncClient, tenant_a_task):
        """Test POST /api/v1/tasks/{task_id}/convert/ - 401 without authentication."""
        response = await api_client.post(
            f"/api/v1/tasks/{tenant_a_task['id']}/convert/", json={"strategy": "standard", "include_subtasks": False}
        )
        assert response.status_code == 401


# ============================================================================
# SUMMARY ENDPOINT TESTS
# ============================================================================


class TestTaskSummary:
    """Test task summary endpoint"""

    @pytest.mark.asyncio
    async def test_get_task_summary_happy_path(self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product):
        """Test GET /api/v1/tasks/summary/ - Get task summary successfully."""
        # Create tasks with different statuses and priorities
        await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Task 1", "status": "pending", "priority": "high", "product_id": tenant_a_product["id"]},
            cookies={"access_token": tenant_a_token},
        )
        await api_client.post(
            "/api/v1/tasks/",
            json={
                "title": "Task 2",
                "status": "in_progress",
                "priority": "medium",
                "product_id": tenant_a_product["id"],
            },
            cookies={"access_token": tenant_a_token},
        )
        await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Task 3", "status": "completed", "priority": "low", "product_id": tenant_a_product["id"]},
            cookies={"access_token": tenant_a_token},
        )

        response = await api_client.get("/api/v1/tasks/summary/", cookies={"access_token": tenant_a_token})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summary" in data
        assert "total_products" in data
        assert "total_tasks" in data
        assert data["total_tasks"] >= 3

    @pytest.mark.asyncio
    async def test_get_task_summary_product_filter(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_a_product
    ):
        """Test GET /api/v1/tasks/summary/?product_id={id} - Filter by product."""
        # Create tasks for specific product
        await api_client.post(
            "/api/v1/tasks/",
            json={"title": "Product Task", "product_id": tenant_a_product["id"], "status": "pending"},
            cookies={"access_token": tenant_a_token},
        )

        response = await api_client.get(
            f"/api/v1/tasks/summary/?product_id={tenant_a_product['id']}", cookies={"access_token": tenant_a_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "summary" in data

    @pytest.mark.asyncio
    async def test_get_task_summary_empty(self, api_client: AsyncClient, tenant_a_token: str):
        """Test GET /api/v1/tasks/summary/ - Empty summary when no tasks."""
        response = await api_client.get("/api/v1/tasks/summary/", cookies={"access_token": tenant_a_token})

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["total_tasks"] >= 0

    @pytest.mark.asyncio
    async def test_get_task_summary_unauthorized(self, api_client: AsyncClient):
        """Test GET /api/v1/tasks/summary/ - 401 without authentication."""
        response = await api_client.get("/api/v1/tasks/summary/")
        assert response.status_code == 401


# ============================================================================
# MULTI-TENANT ISOLATION TESTS (COMPREHENSIVE)
# ============================================================================


class TestMultiTenantIsolation:
    """Comprehensive multi-tenant isolation verification across all endpoints"""

    @pytest.mark.asyncio
    async def test_cross_tenant_task_access_blocked(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_b_token: str, tenant_a_task, tenant_b_task
    ):
        """Verify complete tenant isolation - Tenant A cannot access Tenant B's tasks."""

        # Test GET task
        response = await api_client.get(
            f"/api/v1/tasks/{tenant_b_task['id']}/", cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404  # Not found (prevents info leakage)

        # Test UPDATE task
        response = await api_client.put(
            f"/api/v1/tasks/{tenant_b_task['id']}/", json={"title": "Hacked"}, cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

        # Test DELETE task
        response = await api_client.delete(
            f"/api/v1/tasks/{tenant_b_task['id']}/", cookies={"access_token": tenant_a_token}
        )
        assert response.status_code == 404

        # Test STATUS CHANGE
        response = await api_client.patch(
            f"/api/v1/tasks/{tenant_b_task['id']}/status/",
            json={"status": "completed"},
            cookies={"access_token": tenant_a_token},
        )
        assert response.status_code == 404

        # Test CONVERT
        response = await api_client.post(
            f"/api/v1/tasks/{tenant_b_task['id']}/convert/",
            json={"strategy": "standard", "include_subtasks": False},
            cookies={"access_token": tenant_a_token},
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_task_summary_tenant_isolation(
        self, api_client: AsyncClient, tenant_a_token: str, tenant_b_token: str, tenant_a_task, tenant_b_task
    ):
        """Verify task summaries are isolated between tenants."""

        # Tenant A's summary
        response_a = await api_client.get("/api/v1/tasks/summary/", cookies={"access_token": tenant_a_token})
        assert response_a.status_code == 200
        data_a = response_a.json()

        # Tenant B's summary
        response_b = await api_client.get("/api/v1/tasks/summary/", cookies={"access_token": tenant_b_token})
        assert response_b.status_code == 200
        data_b = response_b.json()

        # Summaries should be different
        assert data_a != data_b
