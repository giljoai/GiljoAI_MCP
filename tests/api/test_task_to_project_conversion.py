"""
Integration tests for task-to-project conversion functionality.

Tests the convert_task_to_project endpoint with focus on:
1. Single active project constraint (idx_project_single_active_per_product)
2. Proper project status transitions (active -> paused)
3. Task deletion after successful conversion
4. Multi-tenant isolation
5. Error handling and edge cases

Backend Integration Tester Agent - TDD Approach
Phase: TEST (write failing tests first)
"""

import uuid
import pytest
from httpx import AsyncClient
from passlib.hash import bcrypt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Product, Project, Task, User


@pytest.mark.asyncio
async def test_convert_task_to_project_with_existing_active_project(
    api_client: AsyncClient,
    db_manager,
):
    """
    Test task conversion when there's already an active project for the product.

    This is the CRITICAL test for the bug fix.

    Expected behavior:
    1. Existing active project should be set to 'paused'
    2. New project should be created with 'active' status
    3. Task should be deleted after successful conversion
    4. No IntegrityError should occur (idx_project_single_active_per_product)
    """
    # Setup: Create test user and authenticate
    async with db_manager.get_session_async() as session:
        # Create test user with unique username/email
        test_id = uuid.uuid4().hex[:8]
        user = User(
            username=f"converter_user_{test_id}",
            email=f"converter_{test_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=f"test_tenant_{test_id}",
            role="developer",
        )
        session.add(user)
        await session.flush()

        # Create an active product
        product = Product(
            name="Test Product",
            description="Product for testing",
            tenant_key=user.tenant_key,
            is_active=True,
        )
        session.add(product)
        await session.flush()

        # Create an existing active project (THIS IS THE KEY SETUP)
        existing_project = Project(
            name="Existing Active Project",
            description="This should be paused",
            mission="Original mission",
            product_id=product.id,
            tenant_key=user.tenant_key,
            status="active",  # Already active!
        )
        session.add(existing_project)
        await session.flush()

        # Create a task to convert
        task = Task(
            title="Task to Convert",
            description="This task will become a project",
            product_id=product.id,
            tenant_key=user.tenant_key,
            created_by_user_id=user.id,
            status="pending",
            priority="high",
        )
        session.add(task)
        await session.commit()

        task_id = str(task.id)
        existing_project_id = str(existing_project.id)

        # Generate auth token
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key,
        )

    # Action: Convert task to project
    response = await api_client.post(
        f"/api/v1/tasks/{task_id}/convert",
        json={
            "project_name": "New Project from Task",
            "strategy": "new_project",
            "include_subtasks": False,
        },
        cookies={"access_token": token},
    )

    # Assertions
    assert response.status_code == 200, f"Conversion failed: {response.status_code} - {response.text}"

    data = response.json()
    assert data["project_name"] == "New Project from Task"
    assert data["original_task_id"] == task_id
    assert "project_id" in data
    new_project_id = data["project_id"]

    # Verify database state
    async with db_manager.get_session_async() as session:
        # Verify existing project was paused
        existing_proj_stmt = select(Project).where(Project.id == existing_project_id)
        existing_proj_result = await session.execute(existing_proj_stmt)
        existing_proj = existing_proj_result.scalar_one_or_none()

        assert existing_proj is not None, "Existing project should still exist"
        assert existing_proj.status == "paused", f"Existing active project should be paused, got: {existing_proj.status}"

        # Verify new project is active
        new_proj_stmt = select(Project).where(Project.id == new_project_id)
        new_proj_result = await session.execute(new_proj_stmt)
        new_proj = new_proj_result.scalar_one_or_none()

        assert new_proj is not None, "New project should exist"
        assert new_proj.status == "active", f"New project should be active, got: {new_proj.status}"
        assert new_proj.name == "New Project from Task"

        # Verify task was deleted
        task_stmt = select(Task).where(Task.id == task_id)
        task_result = await session.execute(task_stmt)
        deleted_task = task_result.scalar_one_or_none()

        assert deleted_task is None, "Task should be deleted after conversion"

        # Verify only one active project per product (database constraint validation)
        active_projects_stmt = select(Project).where(
            Project.product_id == product.id,
            Project.status == "active"
        )
        active_projects_result = await session.execute(active_projects_stmt)
        active_projects = active_projects_result.scalars().all()

        assert len(active_projects) == 1, f"Should have exactly one active project per product, got {len(active_projects)}"
        assert str(active_projects[0].id) == new_project_id


@pytest.mark.asyncio
async def test_convert_task_to_project_no_existing_active_project(
    api_client: AsyncClient,
    db_manager,
):
    """
    Test task conversion when there's NO existing active project.

    Expected behavior:
    1. New project should be created with 'active' status
    2. Task should be deleted after successful conversion
    3. No errors should occur
    """
    async with db_manager.get_session_async() as session:
        # Create test user with unique username/email
        test_id = uuid.uuid4().hex[:8]
        user = User(
            username=f"converter_user2_{test_id}",
            email=f"converter2_{test_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=f"test_tenant2_{test_id}",
            role="developer",
        )
        session.add(user)
        await session.flush()

        # Create an active product
        product = Product(
            name="Test Product No Active",
            description="Product for testing",
            tenant_key=user.tenant_key,
            is_active=True,
        )
        session.add(product)
        await session.flush()

        # Create a task to convert (no existing active project)
        task = Task(
            title="Task to Convert No Active",
            description="This task will become a project",
            product_id=product.id,
            tenant_key=user.tenant_key,
            created_by_user_id=user.id,
            status="pending",
        )
        session.add(task)
        await session.commit()

        task_id = str(task.id)

        # Generate auth token
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key,
        )

    # Action: Convert task to project
    response = await api_client.post(
        f"/api/v1/tasks/{task_id}/convert",
        json={
            "project_name": "New Project from Task",
            "strategy": "new_project",
            "include_subtasks": False,
        },
        cookies={"access_token": token},
    )

    # Assertions
    assert response.status_code == 200

    data = response.json()
    new_project_id = data["project_id"]

    # Verify database state
    async with db_manager.get_session_async() as session:
        # Verify new project is active
        new_proj_stmt = select(Project).where(Project.id == new_project_id)
        new_proj_result = await session.execute(new_proj_stmt)
        new_proj = new_proj_result.scalar_one_or_none()

        assert new_proj is not None
        assert new_proj.status == "active"

        # Verify task was deleted
        task_stmt = select(Task).where(Task.id == task_id)
        task_result = await session.execute(task_stmt)
        deleted_task = task_result.scalar_one_or_none()

        assert deleted_task is None, "Task should be deleted after conversion"


@pytest.mark.asyncio
async def test_convert_task_with_paused_project(
    api_client: AsyncClient,
    db_manager,
):
    """
    Test task conversion when there's a paused project (not active).

    Expected behavior:
    1. Paused project should remain paused
    2. New project should be created with 'active' status
    3. Task should be deleted
    """
    async with db_manager.get_session_async() as session:
        # Create test user with unique username/email
        test_id = uuid.uuid4().hex[:8]
        user = User(
            username=f"converter_user3_{test_id}",
            email=f"converter3_{test_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=f"test_tenant3_{test_id}",
            role="developer",
        )
        session.add(user)
        await session.flush()

        # Create an active product
        product = Product(
            name="Test Product Paused",
            description="Product for testing",
            tenant_key=user.tenant_key,
            is_active=True,
        )
        session.add(product)
        await session.flush()

        # Create a paused project (NOT active)
        paused_project = Project(
            name="Paused Project",
            description="This should stay paused",
            mission="Paused mission",
            product_id=product.id,
            tenant_key=user.tenant_key,
            status="paused",
        )
        session.add(paused_project)
        await session.flush()

        # Create a task to convert
        task = Task(
            title="Task to Convert Paused",
            description="This task will become a project",
            product_id=product.id,
            tenant_key=user.tenant_key,
            created_by_user_id=user.id,
            status="pending",
        )
        session.add(task)
        await session.commit()

        task_id = str(task.id)
        paused_project_id = str(paused_project.id)

        # Generate auth token
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key,
        )

    # Action: Convert task to project
    response = await api_client.post(
        f"/api/v1/tasks/{task_id}/convert",
        json={
            "project_name": "New Project from Task",
            "strategy": "new_project",
            "include_subtasks": False,
        },
        cookies={"access_token": token},
    )

    # Assertions
    assert response.status_code == 200

    # Verify database state
    async with db_manager.get_session_async() as session:
        # Verify paused project is still paused
        paused_proj_stmt = select(Project).where(Project.id == paused_project_id)
        paused_proj_result = await session.execute(paused_proj_stmt)
        paused_proj = paused_proj_result.scalar_one_or_none()

        assert paused_proj is not None
        assert paused_proj.status == "paused", "Paused project should remain paused"

        # Verify new project is active
        data = response.json()
        new_proj_stmt = select(Project).where(Project.id == data["project_id"])
        new_proj_result = await session.execute(new_proj_stmt)
        new_proj = new_proj_result.scalar_one_or_none()

        assert new_proj is not None
        assert new_proj.status == "active"

        # Verify task was deleted
        task_stmt = select(Task).where(Task.id == task_id)
        task_result = await session.execute(task_stmt)
        deleted_task = task_result.scalar_one_or_none()

        assert deleted_task is None


@pytest.mark.asyncio
async def test_convert_already_converted_task(
    api_client: AsyncClient,
    db_manager,
):
    """
    Test that already-converted tasks cannot be converted again.

    Expected behavior:
    1. Should get 400 Bad Request
    2. Task should remain in converted state
    """
    async with db_manager.get_session_async() as session:
        # Create test user with unique username/email
        test_id = uuid.uuid4().hex[:8]
        user = User(
            username=f"converter_user4_{test_id}",
            email=f"converter4_{test_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=f"test_tenant4_{test_id}",
            role="developer",
        )
        session.add(user)
        await session.flush()

        # Create product and project
        product = Product(
            name="Test Product Already",
            tenant_key=user.tenant_key,
            is_active=True,
        )
        session.add(product)
        await session.flush()

        original_project = Project(
            name="Original Project",
            description="Original project description",
            mission="Original mission",
            product_id=product.id,
            tenant_key=user.tenant_key,
            status="active",
        )
        session.add(original_project)
        await session.flush()

        # Create already-converted task
        task = Task(
            title="Already Converted Task",
            product_id=product.id,
            tenant_key=user.tenant_key,
            created_by_user_id=user.id,
            status="completed",
            converted_to_project_id=original_project.id,  # Already converted!
        )
        session.add(task)
        await session.commit()

        task_id = str(task.id)

        # Generate auth token
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key,
        )

    # Action: Try to convert again
    response = await api_client.post(
        f"/api/v1/tasks/{task_id}/convert",
        json={
            "project_name": "Another Conversion",
            "strategy": "new_project",
            "include_subtasks": False,
        },
        cookies={"access_token": token},
    )

    # Assertions
    assert response.status_code == 400, "Already converted task should return 400"
    assert "already converted" in response.text.lower()


@pytest.mark.asyncio
async def test_convert_task_no_active_product(
    api_client: AsyncClient,
    db_manager,
):
    """
    Test task conversion fails when no active product exists.

    Expected behavior:
    1. Should get 400 Bad Request
    2. Task should not be converted
    """
    async with db_manager.get_session_async() as session:
        # Create test user with unique username/email
        test_id = uuid.uuid4().hex[:8]
        user = User(
            username=f"converter_user5_{test_id}",
            email=f"converter5_{test_id}@test.com",
            password_hash=bcrypt.hash("test_password"),
            tenant_key=f"test_tenant5_{test_id}",
            role="developer",
        )
        session.add(user)
        await session.flush()

        # Create inactive product
        product = Product(
            name="Inactive Product",
            tenant_key=user.tenant_key,
            is_active=False,  # Not active!
        )
        session.add(product)
        await session.flush()

        # Create task
        task = Task(
            title="Task to Convert No Active Product",
            product_id=product.id,
            tenant_key=user.tenant_key,
            created_by_user_id=user.id,
            status="pending",
        )
        session.add(task)
        await session.commit()

        task_id = str(task.id)

        # Generate auth token
        from src.giljo_mcp.auth.jwt_manager import JWTManager
        token = JWTManager.create_access_token(
            user_id=user.id,
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key,
        )

    # Action: Try to convert without active product
    response = await api_client.post(
        f"/api/v1/tasks/{task_id}/convert",
        json={
            "project_name": "Should Fail",
            "strategy": "new_project",
            "include_subtasks": False,
        },
        cookies={"access_token": token},
    )

    # Assertions
    assert response.status_code == 400
    assert "no active product" in response.text.lower()

    # Verify task still exists and is not converted
    async with db_manager.get_session_async() as session:
        task_stmt = select(Task).where(Task.id == task_id)
        task_result = await session.execute(task_stmt)
        task_after = task_result.scalar_one_or_none()

        assert task_after is not None
        assert task_after.converted_to_project_id is None
