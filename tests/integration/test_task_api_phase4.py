"""
Integration tests for Phase 4 Task API endpoints.

Tests the following endpoints:
- PATCH /api/v1/tasks/{task_id} - Update task
- DELETE /api/v1/tasks/{task_id} - Delete task
- POST /api/v1/tasks/{task_id}/convert - Convert task to project
- GET /api/v1/tasks - Enhanced with user filtering

Follows TDD approach: tests written before implementation.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.models import Product, Project, Task, User


@pytest.fixture
async def test_user(db_session: AsyncSession):
    """Create a test user for authentication"""
    user = User(
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        password_hash="hashed_password",
        role="developer",
        tenant_key="test_tenant",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Generate JWT token
    token = JWTManager.create_access_token(
        user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
    )
    user.token = token

    return user


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin user for testing admin permissions"""
    user = User(
        username="adminuser",
        email="admin@example.com",
        full_name="Admin User",
        password_hash="hashed_password",
        role="admin",
        tenant_key="test_tenant",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Generate JWT token
    token = JWTManager.create_access_token(
        user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
    )
    user.token = token

    return user


@pytest.fixture
async def other_user(db_session: AsyncSession):
    """Create another user in the same tenant"""
    user = User(
        username="otheruser",
        email="other@example.com",
        full_name="Other User",
        password_hash="hashed_password",
        role="developer",
        tenant_key="test_tenant",
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Generate JWT token
    token = JWTManager.create_access_token(
        user_id=user.id, username=user.username, role=user.role, tenant_key=user.tenant_key
    )
    user.token = token

    return user


@pytest.fixture
async def test_product(db_session: AsyncSession):
    """Create a test product"""
    product = Product(name="Test Product", description="Test product for tasks", tenant_key="test_tenant")
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
async def test_project(db_session: AsyncSession, test_product: Product):
    """Create a test project"""
    project = Project(
        name="Test Project",
        mission="Test mission",
        product_id=test_product.id,
        tenant_key="test_tenant",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_task(db_session: AsyncSession, test_project: Project, test_user: User, test_product: Product):
    """Create a test task owned by test_user"""
    task = Task(
        title="Test Task",
        description="Test task description",
        project_id=test_project.id,
        product_id=test_product.id,
        tenant_key="test_tenant",
        status="waiting",
        priority="medium",
        created_by_user_id=test_user.id,
        assigned_to_user_id=test_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest.fixture
async def other_user_task(db_session: AsyncSession, test_project: Project, other_user: User, test_product: Product):
    """Create a task owned by other_user"""
    task = Task(
        title="Other User's Task",
        description="Task created by other user",
        project_id=test_project.id,
        product_id=test_product.id,
        tenant_key="test_tenant",
        status="waiting",
        priority="high",
        created_by_user_id=other_user.id,
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


# PATCH /api/v1/tasks/{task_id} Tests


@pytest.mark.asyncio
async def test_update_task_success(async_client: AsyncClient, test_user: User, test_task: Task):
    """Test updating a task successfully"""
    response = await async_client.patch(
        f"/api/v1/tasks/{test_task.id}",
        json={"status": "in_progress", "priority": "high"},
        cookies={"access_token": test_user.token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"
    assert data["priority"] == "high"
    assert data["id"] == test_task.id


@pytest.mark.asyncio
async def test_update_task_assigned_to_me(
    async_client: AsyncClient, test_user: User, other_user_task: Task, db_session: AsyncSession
):
    """Test that user can update tasks assigned to them"""
    # Assign other_user's task to test_user
    other_user_task.assigned_to_user_id = test_user.id
    await db_session.commit()

    response = await async_client.patch(
        f"/api/v1/tasks/{other_user_task.id}", json={"status": "in_progress"}, cookies={"access_token": test_user.token}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "in_progress"


@pytest.mark.asyncio
async def test_update_task_permission_denied(async_client: AsyncClient, test_user: User, other_user_task: Task):
    """Test that users can't update others' tasks"""
    response = await async_client.patch(
        f"/api/v1/tasks/{other_user_task.id}", json={"status": "in_progress"}, cookies={"access_token": test_user.token}
    )

    assert response.status_code == 403
    assert "Not authorized" in response.json()["detail"]


@pytest.mark.asyncio
async def test_update_task_admin_can_update_any(async_client: AsyncClient, admin_user: User, other_user_task: Task):
    """Test that admins can update any task in their tenant"""
    response = await async_client.patch(
        f"/api/v1/tasks/{other_user_task.id}",
        json={"status": "database_initialized"},
        cookies={"access_token": admin_user.token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "database_initialized"


@pytest.mark.asyncio
async def test_update_task_not_found(async_client: AsyncClient, test_user: User):
    """Test updating non-existent task returns 404"""
    response = await async_client.patch(
        "/api/v1/tasks/nonexistent-id", json={"status": "in_progress"}, cookies={"access_token": test_user.token}
    )

    assert response.status_code == 404


# DELETE /api/v1/tasks/{task_id} Tests


@pytest.mark.asyncio
async def test_delete_task_success(async_client: AsyncClient, test_user: User, test_task: Task):
    """Test deleting a task successfully"""
    response = await async_client.delete(f"/api/v1/tasks/{test_task.id}", cookies={"access_token": test_user.token})

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_task_permission_denied(async_client: AsyncClient, test_user: User, other_user_task: Task):
    """Test that users can't delete others' tasks"""
    response = await async_client.delete(
        f"/api/v1/tasks/{other_user_task.id}", cookies={"access_token": test_user.token}
    )

    assert response.status_code == 403
    assert "Only task creator or admin can delete" in response.json()["detail"]


@pytest.mark.asyncio
async def test_delete_task_admin_can_delete_any(async_client: AsyncClient, admin_user: User, other_user_task: Task):
    """Test that admins can delete any task in their tenant"""
    response = await async_client.delete(
        f"/api/v1/tasks/{other_user_task.id}", cookies={"access_token": admin_user.token}
    )

    assert response.status_code == 204


@pytest.mark.asyncio
async def test_delete_task_not_found(async_client: AsyncClient, test_user: User):
    """Test deleting non-existent task returns 404"""
    response = await async_client.delete("/api/v1/tasks/nonexistent-id", cookies={"access_token": test_user.token})

    assert response.status_code == 404


# POST /api/v1/tasks/{task_id}/convert Tests


@pytest.mark.asyncio
async def test_convert_task_to_project_success(async_client: AsyncClient, test_user: User, test_task: Task):
    """Test task-to-project conversion successfully"""
    response = await async_client.post(
        f"/api/v1/tasks/{test_task.id}/convert",
        json={"project_name": "Converted Project", "strategy": "single", "include_subtasks": True},
        cookies={"access_token": test_user.token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "Converted Project"
    assert data["original_task_id"] == test_task.id
    assert data["conversion_strategy"] == "single"
    assert "project_id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_convert_task_default_project_name(async_client: AsyncClient, test_user: User, test_task: Task):
    """Test conversion uses task title as default project name"""
    response = await async_client.post(
        f"/api/v1/tasks/{test_task.id}/convert",
        json={"strategy": "single", "include_subtasks": True},
        cookies={"access_token": test_user.token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == test_task.title


@pytest.mark.asyncio
async def test_convert_task_already_converted(
    async_client: AsyncClient, test_user: User, test_task: Task, test_project: Project, db_session: AsyncSession
):
    """Test that already-converted tasks cannot be converted again"""
    # Mark task as converted
    test_task.status = "converted"
    test_task.converted_to_project_id = test_project.id
    await db_session.commit()

    response = await async_client.post(
        f"/api/v1/tasks/{test_task.id}/convert", json={"strategy": "single"}, cookies={"access_token": test_user.token}
    )

    assert response.status_code == 400
    assert "already converted" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_convert_task_permission_denied(async_client: AsyncClient, test_user: User, other_user_task: Task):
    """Test that only creator or admin can convert tasks"""
    response = await async_client.post(
        f"/api/v1/tasks/{other_user_task.id}/convert",
        json={"strategy": "single"},
        cookies={"access_token": test_user.token},
    )

    assert response.status_code == 403
    assert "Only task creator or admin can convert" in response.json()["detail"]


@pytest.mark.asyncio
async def test_convert_task_admin_can_convert_any(async_client: AsyncClient, admin_user: User, other_user_task: Task):
    """Test that admins can convert any task in their tenant"""
    response = await async_client.post(
        f"/api/v1/tasks/{other_user_task.id}/convert",
        json={"project_name": "Admin Converted Project", "strategy": "single"},
        cookies={"access_token": admin_user.token},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["project_name"] == "Admin Converted Project"


# GET /api/v1/tasks with user filtering Tests


@pytest.mark.asyncio
async def test_list_tasks_my_tasks_filter(
    async_client: AsyncClient, test_user: User, test_task: Task, other_user_task: Task
):
    """Test 'my tasks' filtering shows only user's tasks"""
    response = await async_client.get("/api/v1/tasks?filter_type=my_tasks", cookies={"access_token": test_user.token})

    assert response.status_code == 200
    tasks = response.json()

    # Should only see tasks created by or assigned to test_user
    task_ids = [task["id"] for task in tasks]
    assert test_task.id in task_ids
    assert other_user_task.id not in task_ids


@pytest.mark.asyncio
async def test_list_tasks_assigned_to_me_filter(
    async_client: AsyncClient, test_user: User, test_task: Task, other_user_task: Task, db_session: AsyncSession
):
    """Test filtering tasks assigned to current user"""
    # Assign other_user's task to test_user
    other_user_task.assigned_to_user_id = test_user.id
    await db_session.commit()

    response = await async_client.get("/api/v1/tasks?assigned_to_me=true", cookies={"access_token": test_user.token})

    assert response.status_code == 200
    tasks = response.json()

    # Should see both tasks now (both assigned to test_user)
    task_ids = [task["id"] for task in tasks]
    assert test_task.id in task_ids
    assert other_user_task.id in task_ids


@pytest.mark.asyncio
async def test_list_tasks_created_by_me_filter(
    async_client: AsyncClient, test_user: User, test_task: Task, other_user_task: Task
):
    """Test filtering tasks created by current user"""
    response = await async_client.get("/api/v1/tasks?created_by_me=true", cookies={"access_token": test_user.token})

    assert response.status_code == 200
    tasks = response.json()

    # Should only see tasks created by test_user
    task_ids = [task["id"] for task in tasks]
    assert test_task.id in task_ids
    assert other_user_task.id not in task_ids


@pytest.mark.asyncio
async def test_list_tasks_admin_sees_all_by_default(
    async_client: AsyncClient, admin_user: User, test_task: Task, other_user_task: Task
):
    """Test that admins see all tasks in their tenant by default"""
    response = await async_client.get("/api/v1/tasks", cookies={"access_token": admin_user.token})

    assert response.status_code == 200
    tasks = response.json()

    # Admin should see all tasks in tenant
    task_ids = [task["id"] for task in tasks]
    assert test_task.id in task_ids
    assert other_user_task.id in task_ids


@pytest.mark.asyncio
async def test_list_tasks_regular_user_sees_own_by_default(
    async_client: AsyncClient, test_user: User, test_task: Task, other_user_task: Task
):
    """Test that regular users see only their tasks by default"""
    response = await async_client.get("/api/v1/tasks", cookies={"access_token": test_user.token})

    assert response.status_code == 200
    tasks = response.json()

    # Regular user should only see their own tasks by default
    task_ids = [task["id"] for task in tasks]
    assert test_task.id in task_ids
    assert other_user_task.id not in task_ids


@pytest.mark.asyncio
async def test_list_tasks_status_filter(
    async_client: AsyncClient, test_user: User, db_session: AsyncSession, test_project: Project, test_product: Product
):
    """Test filtering tasks by status"""
    # Create tasks with different statuses
    pending_task = Task(
        title="Pending Task",
        project_id=test_project.id,
        product_id=test_product.id,
        tenant_key="test_tenant",
        status="waiting",
        created_by_user_id=test_user.id,
    )
    completed_task = Task(
        title="Completed Task",
        project_id=test_project.id,
        product_id=test_product.id,
        tenant_key="test_tenant",
        status="database_initialized",
        created_by_user_id=test_user.id,
    )
    db_session.add_all([pending_task, completed_task])
    await db_session.commit()

    response = await async_client.get("/api/v1/tasks?status=pending", cookies={"access_token": test_user.token})

    assert response.status_code == 200
    tasks = response.json()

    # Should only see pending tasks
    for task in tasks:
        assert task["status"] == "pending"


@pytest.mark.asyncio
async def test_list_tasks_tenant_isolation(
    async_client: AsyncClient, db_session: AsyncSession, test_project: Project, test_product: Product
):
    """Test that users only see tasks in their tenant"""
    # Create user in different tenant
    other_tenant_user = User(
        username="othertenant",
        email="othertenant@example.com",
        password_hash="hashed_password",
        role="admin",
        tenant_key="other_tenant",
        is_active=True,
    )
    db_session.add(other_tenant_user)
    await db_session.commit()

    # Create task in other tenant
    other_tenant_task = Task(
        title="Other Tenant Task",
        project_id=test_project.id,
        product_id=test_product.id,
        tenant_key="other_tenant",
        status="waiting",
        created_by_user_id=other_tenant_user.id,
    )
    db_session.add(other_tenant_task)
    await db_session.commit()

    # Generate token for other tenant user
    other_token = JWTManager.create_access_token(
        user_id=other_tenant_user.id,
        username=other_tenant_user.username,
        role=other_tenant_user.role,
        tenant_key=other_tenant_user.tenant_key,
    )

    response = await async_client.get("/api/v1/tasks", cookies={"access_token": other_token})

    assert response.status_code == 200
    tasks = response.json()

    # All tasks should belong to other_tenant
    for task in tasks:
        # We can't check tenant_key directly from response, but we can verify
        # the task ID is the one we created in other_tenant
        assert task["id"] == other_tenant_task.id
