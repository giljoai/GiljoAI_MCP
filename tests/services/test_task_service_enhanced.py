"""
Test suite for TaskService Enhancement - TDD Handover 0322 Phase 3
Updated for typed returns (Handover 0731c).

This test suite covers the 5 new TaskService methods + 2 permission helpers:
- get_task (single task retrieval by ID)
- delete_task (soft/hard delete with permission checks)
- convert_to_project (task -> project conversion with subtask handling)
- change_status (status change with automatic timestamp updates)
- get_summary (task statistics aggregation)
- can_modify_task (permission helper)
- can_delete_task (permission helper)

Coverage Target: >80%
"""

import random
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
import pytest_asyncio
from passlib.hash import bcrypt
from sqlalchemy import select

from src.giljo_mcp.exceptions import AuthorizationError, ResourceNotFoundError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Task
from src.giljo_mcp.schemas.service_responses import ConversionResult, TaskUpdateResult
from src.giljo_mcp.services.task_service import TaskService



# Use existing fixtures from base_fixtures


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate unique tenant key for test isolation"""
    # Use simple format for tests (not the strict tk_ format)
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def other_tenant_key():
    """Generate another tenant key for cross-tenant testing"""
    return f"other_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def test_product(db_session, test_tenant_key):
    """Create test product in database"""
    product = Product(
        id=str(uuid4()),
        name=f"Test Product {uuid4().hex[:6]}",
        description="Test product for task service tests",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project(db_session, test_tenant_key, test_product):
    """Create test project in database"""
    project = Project(
        id=str(uuid4()),
        name=f"Test Project {uuid4().hex[:6]}",
        description="Test project for task tests",
        mission="Test mission",
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        status="active",
        created_at=datetime.now(timezone.utc),
        series_number=random.randint(1, 999999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_user(db_session, test_tenant_key):
    """Create test user (developer role)"""
    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:6]}",
        email=f"test_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("TestPassword123"),
        full_name="Test User",
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def admin_user(db_session, test_tenant_key):
    """Create admin user"""
    admin = User(
        id=str(uuid4()),
        username=f"admin_{uuid4().hex[:6]}",
        email=f"admin_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("AdminPassword123"),
        full_name="Admin User",
        role="admin",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(admin)
    await db_session.commit()
    await db_session.refresh(admin)
    return admin


@pytest_asyncio.fixture
async def other_tenant_user(db_session, other_tenant_key):
    """Create user in different tenant"""
    user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("OtherPassword123"),
        full_name="Other Tenant User",
        role="developer",
        tenant_key=other_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_task(db_session, test_tenant_key, test_product, test_project, test_user):
    """Create test task in database"""
    task = Task(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        project_id=test_project.id,
        title="Test Task",
        description="Test task description",
        category="feature",
        status="waiting",
        priority="medium",
        created_by_user_id=test_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def other_tenant_product(db_session, other_tenant_key):
    """Create product for other tenant"""
    product = Product(
        id=str(uuid4()),
        name=f"Other Product {uuid4().hex[:6]}",
        description="Product for other tenant",
        tenant_key=other_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def other_tenant_task(db_session, other_tenant_key, other_tenant_product, other_tenant_user):
    """Create task in different tenant with required product_id (0433)"""
    task = Task(
        id=str(uuid4()),
        tenant_key=other_tenant_key,
        product_id=other_tenant_product.id,  # Required per handover 0433
        title="Other Tenant Task",
        description="Task in different tenant",
        status="waiting",
        priority="medium",
        created_by_user_id=other_tenant_user.id,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def task_service(db_manager, db_session, test_tenant_key):
    """Create TaskService instance with TenantManager and shared session"""
    # Create a mock TenantManager that returns our test tenant key
    mock_tenant_manager = MagicMock()
    mock_tenant_manager.get_current_tenant.return_value = test_tenant_key

    return TaskService(
        db_manager=db_manager,
        tenant_manager=mock_tenant_manager,
        session=db_session,  # ADD THIS - Shared Session Pattern (Handover 0324)
    )


# ============================================================================
# TEST: get_task - Now returns Task ORM model directly (0731c)
# ============================================================================


@pytest.mark.asyncio
async def test_get_task_success(task_service, test_task):
    """Test successful single task retrieval by ID - returns Task ORM model"""
    result = await task_service.get_task(task_id=str(test_task.id))

    # 0731c: get_task now returns Task ORM model directly
    assert isinstance(result, Task)
    assert str(result.id) == str(test_task.id)
    assert result.title == "Test Task"
    assert result.status == "waiting"


@pytest.mark.asyncio
async def test_get_task_not_found(task_service):
    """Test get_task raises ResourceNotFoundError for missing task"""
    fake_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.get_task(task_id=fake_id)

    assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_get_task_tenant_isolation(task_service, other_tenant_task):
    """Test get_task respects tenant_key filtering (cannot access other tenant's tasks)"""
    # Try to access task from another tenant
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.get_task(task_id=str(other_tenant_task.id))

    assert "not found" in str(exc_info.value).lower()


# ============================================================================
# TEST: delete_task - Returns None (unchanged, already correct)
# ============================================================================


@pytest.mark.asyncio
async def test_delete_task_success_as_creator(task_service, test_task, test_user, db_session):
    """Test successful task deletion by creator"""
    result = await task_service.delete_task(task_id=str(test_task.id), user_id=str(test_user.id))
    assert result is None

    # Verify task is deleted from database
    stmt = select(Task).where(Task.id == test_task.id)
    db_result = await db_session.execute(stmt)
    deleted_task = db_result.scalar_one_or_none()
    assert deleted_task is None


@pytest.mark.asyncio
async def test_delete_task_success_as_admin(task_service, test_task, admin_user, db_session):
    """Test successful task deletion by admin"""
    result = await task_service.delete_task(task_id=str(test_task.id), user_id=str(admin_user.id))
    assert result is None

    # Verify task is deleted from database
    stmt = select(Task).where(Task.id == test_task.id)
    db_result = await db_session.execute(stmt)
    deleted_task = db_result.scalar_one_or_none()
    assert deleted_task is None


@pytest.mark.asyncio
async def test_delete_task_permission_denied(task_service, test_task, db_session, test_tenant_key):
    """Test delete_task raises AuthorizationError when user lacks permission"""
    # Create another developer user who didn't create the task
    other_user = User(
        id=str(uuid4()),
        username=f"otherdev_{uuid4().hex[:6]}",
        email=f"otherdev_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("Password123"),
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    with pytest.raises(AuthorizationError) as exc_info:
        await task_service.delete_task(task_id=str(test_task.id), user_id=str(other_user.id))

    assert "permission" in str(exc_info.value).lower() or "not authorized" in str(exc_info.value).lower()


# ============================================================================
# TEST: convert_to_project - Now returns ConversionResult (0731c)
# ============================================================================


@pytest.mark.asyncio
async def test_convert_to_project_basic(task_service, test_task, test_user, db_session, test_product):
    """Test basic task -> project conversion returns ConversionResult"""
    result = await task_service.convert_to_project(
        task_id=str(test_task.id),
        project_name="New Project from Task",
        strategy="create_new",
        include_subtasks=False,
        user_id=str(test_user.id),
    )

    # 0731c: convert_to_project now returns ConversionResult
    assert isinstance(result, ConversionResult)
    assert result.task_id == str(test_task.id)
    assert result.project_id is not None
    assert result.project_name == "New Project from Task"

    # Verify project was created
    stmt = select(Project).where(Project.id == result.project_id)
    db_result = await db_session.execute(stmt)
    new_project = db_result.scalar_one_or_none()

    assert new_project is not None
    assert new_project.name == "New Project from Task"
    assert new_project.product_id == test_product.id


@pytest.mark.asyncio
async def test_convert_to_project_with_subtasks(
    task_service, test_task, test_user, db_session, test_tenant_key, test_product, test_project
):
    """Test task -> project conversion with subtask handling returns ConversionResult"""
    # Create subtasks
    subtask1 = Task(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        project_id=test_project.id,
        parent_task_id=test_task.id,
        title="Subtask 1",
        description="First subtask",
        status="waiting",
        priority="low",
        created_by_user_id=test_user.id,
    )
    subtask2 = Task(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        project_id=test_project.id,
        parent_task_id=test_task.id,
        title="Subtask 2",
        description="Second subtask",
        status="waiting",
        priority="low",
        created_by_user_id=test_user.id,
    )
    db_session.add_all([subtask1, subtask2])
    await db_session.commit()

    result = await task_service.convert_to_project(
        task_id=str(test_task.id),
        project_name="Project with Subtasks",
        strategy="create_new",
        include_subtasks=True,
        user_id=str(test_user.id),
    )

    # 0731c: convert_to_project now returns ConversionResult
    assert isinstance(result, ConversionResult)
    assert result.project_id is not None
    assert result.project_name == "Project with Subtasks"


@pytest.mark.asyncio
async def test_convert_to_project_permission_denied(task_service, test_task, db_session, test_tenant_key):
    """Test convert_to_project raises AuthorizationError without permission"""
    # Create another user who didn't create the task
    other_user = User(
        id=str(uuid4()),
        username=f"unauthorized_{uuid4().hex[:6]}",
        email=f"unauth_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("Password123"),
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    with pytest.raises(AuthorizationError) as exc_info:
        await task_service.convert_to_project(
            task_id=str(test_task.id),
            project_name="Unauthorized Project",
            strategy="create_new",
            include_subtasks=False,
            user_id=str(other_user.id),
        )

    assert "permission" in str(exc_info.value).lower() or "not authorized" in str(exc_info.value).lower()


# ============================================================================
# TEST: change_status - Now returns Task ORM model directly (0731c)
# ============================================================================


@pytest.mark.asyncio
async def test_change_status_to_in_progress(task_service, test_task, db_session):
    """Test status change to 'in_progress' sets started_at - returns Task"""
    assert test_task.started_at is None  # Initially None

    result = await task_service.change_status(task_id=str(test_task.id), new_status="in_progress")

    # 0731c: change_status now returns Task ORM model directly
    assert isinstance(result, Task)
    assert result.status == "in_progress"

    # Verify started_at was set
    await db_session.refresh(test_task)
    assert test_task.started_at is not None


@pytest.mark.asyncio
async def test_change_status_to_completed(task_service, test_task, db_session):
    """Test status change to 'completed' sets completed_at - returns Task"""
    assert test_task.completed_at is None  # Initially None

    result = await task_service.change_status(task_id=str(test_task.id), new_status="completed")

    # 0731c: change_status now returns Task ORM model directly
    assert isinstance(result, Task)
    assert result.status == "completed"

    # Verify completed_at was set
    await db_session.refresh(test_task)
    assert test_task.completed_at is not None


@pytest.mark.asyncio
async def test_change_status_to_cancelled(task_service, test_task, db_session):
    """Test status change to 'cancelled' sets completed_at - returns Task"""
    assert test_task.completed_at is None

    result = await task_service.change_status(task_id=str(test_task.id), new_status="cancelled")

    # 0731c: change_status now returns Task ORM model directly
    assert isinstance(result, Task)
    assert result.status == "cancelled"

    # Verify completed_at was set
    await db_session.refresh(test_task)
    assert test_task.completed_at is not None


@pytest.mark.asyncio
async def test_change_status_invalid(task_service, test_task):
    """Test invalid status handling - returns Task with whatever status was set"""
    result = await task_service.change_status(task_id=str(test_task.id), new_status="invalid_status_xyz")

    # 0731c: change_status now returns Task ORM model directly
    assert isinstance(result, Task)
    assert result.status == "invalid_status_xyz"


# ============================================================================
# TEST: get_summary - Now returns dict (summary structure unchanged)
# ============================================================================


@pytest.mark.asyncio
async def test_get_summary_all_products(
    task_service, db_session, test_tenant_key, test_product, test_project, test_user
):
    """Test task summary aggregation across all products"""
    # Create tasks with different statuses
    tasks_data = [
        {"status": "pending", "priority": "high"},
        {"status": "in_progress", "priority": "medium"},
        {"status": "completed", "priority": "low"},
        {"status": "pending", "priority": "critical"},
    ]

    for task_data in tasks_data:
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=test_product.id,
            project_id=test_project.id,
            title=f"Task {task_data['status']}",
            description=f"Task with status {task_data['status']}",
            status=task_data["status"],
            priority=task_data["priority"],
            created_by_user_id=test_user.id,
        )
        db_session.add(task)

    await db_session.commit()

    summary = await task_service.get_summary(product_id=None)

    # get_summary still returns dict with summary structure
    assert summary is not None
    assert "summary" in summary
    assert "total_products" in summary
    assert "total_tasks" in summary


@pytest.mark.asyncio
async def test_get_summary_filtered_by_product(
    task_service, db_session, test_tenant_key, test_product, test_project, test_user
):
    """Test task summary filtered by specific product"""
    # Create tasks
    task1 = Task(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        product_id=test_product.id,
        project_id=test_project.id,
        title="Product Task",
        description="Task for specific product",
        status="waiting",
        priority="high",
        created_by_user_id=test_user.id,
    )
    db_session.add(task1)
    await db_session.commit()

    summary = await task_service.get_summary(product_id=str(test_product.id))

    # Verify summary was returned
    assert summary is not None
    assert "summary" in summary


# ============================================================================
# TEST: list_tasks - Now returns list[Task] directly (0731c)
# ============================================================================


@pytest.mark.asyncio
async def test_list_tasks_returns_task_list(task_service, test_task):
    """Test list_tasks returns list of Task ORM models"""
    result = await task_service.list_tasks()

    # 0731c: list_tasks now returns list[Task] directly
    assert isinstance(result, list)
    assert len(result) >= 1
    assert all(isinstance(t, Task) for t in result)

    # Verify our test task is in the list
    task_ids = [str(t.id) for t in result]
    assert str(test_task.id) in task_ids


@pytest.mark.asyncio
async def test_list_tasks_empty(task_service):
    """Test list_tasks returns empty list when no tasks exist"""
    result = await task_service.list_tasks()

    # 0731c: list_tasks now returns list[Task] directly
    assert isinstance(result, list)
    assert len(result) == 0


# ============================================================================
# TEST: update_task - Now returns TaskUpdateResult (0731c)
# ============================================================================


@pytest.mark.asyncio
async def test_update_task_returns_typed_result(task_service, test_task):
    """Test update_task returns TaskUpdateResult"""
    result = await task_service.update_task(
        task_id=str(test_task.id), status="in_progress", priority="high"
    )

    # 0731c: update_task now returns TaskUpdateResult
    assert isinstance(result, TaskUpdateResult)
    assert result.task_id == str(test_task.id)
    assert "status" in result.updated_fields
    assert "priority" in result.updated_fields


@pytest.mark.asyncio
async def test_assign_task_returns_typed_result(task_service, test_task):
    """Test assign_task returns TaskUpdateResult (delegates to update_task)"""
    result = await task_service.assign_task(task_id=str(test_task.id), agent_name="impl-1")

    # 0731c: assign_task delegates to update_task, returns TaskUpdateResult
    # Note: assigned_to field was removed in Handover 0076, only status gets updated
    assert isinstance(result, TaskUpdateResult)
    assert result.task_id == str(test_task.id)
    assert "status" in result.updated_fields


@pytest.mark.asyncio
async def test_complete_task_returns_typed_result(task_service, test_task):
    """Test complete_task returns TaskUpdateResult (delegates to update_task)"""
    result = await task_service.complete_task(task_id=str(test_task.id))

    # 0731c: complete_task delegates to update_task, returns TaskUpdateResult
    assert isinstance(result, TaskUpdateResult)
    assert result.task_id == str(test_task.id)
    assert "status" in result.updated_fields


# ============================================================================
# TEST: create_task - Now returns str (task_id) matching log_task (0731c)
# ============================================================================


@pytest.mark.asyncio
async def test_create_task_returns_task_id(task_service, test_product, test_tenant_key):
    """Test create_task returns task_id string (delegates to log_task)"""
    result = await task_service.create_task(
        title="New Task",
        description="A new task description",
        priority="high",
        product_id=test_product.id,
        tenant_key=test_tenant_key,
    )

    # 0731c: create_task delegates to log_task, returns str (task_id)
    assert isinstance(result, str)
    assert len(result) > 0


# ============================================================================
# TEST: Permission Helpers (unchanged - already return bool)
# ============================================================================


@pytest.mark.asyncio
async def test_can_modify_task_as_creator(task_service, test_task, test_user):
    """Test creator can modify their own task"""
    can_modify = task_service.can_modify_task(test_task, test_user)
    assert can_modify is True


@pytest.mark.asyncio
async def test_can_modify_task_as_admin(task_service, test_task, admin_user):
    """Test admin can modify any task in tenant"""
    can_modify = task_service.can_modify_task(test_task, admin_user)
    assert can_modify is True


@pytest.mark.asyncio
async def test_can_modify_task_denied(task_service, test_task, db_session, test_tenant_key):
    """Test other developer cannot modify task they didn't create"""
    other_user = User(
        id=str(uuid4()),
        username=f"otherdev_{uuid4().hex[:6]}",
        email=f"otherdev_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("Password123"),
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    can_modify = task_service.can_modify_task(test_task, other_user)
    assert can_modify is False


@pytest.mark.asyncio
async def test_can_delete_task_as_creator(task_service, test_task, test_user):
    """Test creator can delete their own task"""
    can_delete = task_service.can_delete_task(test_task, test_user)
    assert can_delete is True


@pytest.mark.asyncio
async def test_can_delete_task_as_admin(task_service, test_task, admin_user):
    """Test admin can delete any task in tenant"""
    can_delete = task_service.can_delete_task(test_task, admin_user)
    assert can_delete is True


@pytest.mark.asyncio
async def test_can_delete_task_denied(task_service, test_task, db_session, test_tenant_key):
    """Test other developer cannot delete task they didn't create"""
    other_user = User(
        id=str(uuid4()),
        username=f"otherdev_{uuid4().hex[:6]}",
        email=f"otherdev_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("Password123"),
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(other_user)
    await db_session.commit()

    can_delete = task_service.can_delete_task(test_task, other_user)
    assert can_delete is False
