"""
Test suite for TaskService Exception Handling - Handover 0480c

This test suite covers exception-based error handling migration from dict returns.
Tests all error paths for ResourceNotFoundError, ValidationError, and BaseGiljoError.

Target: All 27 error return statements converted to exception raises.
"""

from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from passlib.hash import bcrypt

from src.giljo_mcp.exceptions import (
    AuthorizationError,
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Task
from src.giljo_mcp.services.task_service import TaskService


# Use existing fixtures from base_fixtures


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture
async def test_tenant_key():
    """Generate unique tenant key for test isolation"""
    return f"test_tenant_{uuid4().hex[:8]}"


@pytest_asyncio.fixture
async def test_product(db_session, test_tenant_key):
    """Create test product in database"""
    product = Product(
        id=str(uuid4()),
        name=f"Test Product {uuid4().hex[:6]}",
        description="Test product for task service exception tests",
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
    user = User(
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
        created_by_user_id=test_user.id,
        title="Test Task",
        description="Test task description",
        status="pending",
        priority="medium",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)
    return task


@pytest_asyncio.fixture
async def tenant_manager(test_tenant_key):
    """Mock tenant manager"""
    manager = MagicMock()
    manager.get_current_tenant.return_value = test_tenant_key
    return manager


@pytest_asyncio.fixture
async def task_service(db_manager, tenant_manager, db_session):
    """Create TaskService instance with mocked dependencies"""
    service = TaskService(db_manager=db_manager, tenant_manager=tenant_manager, session=db_session)
    return service


# ============================================================================
# EXCEPTION TESTS - log_task & _log_task_impl
# ============================================================================


@pytest.mark.asyncio
async def test_log_task_raises_exception_on_database_error(task_service, tenant_manager):
    """Test log_task raises BaseGiljoError on database errors"""
    # Simulate database error
    with patch.object(task_service, "_log_task_impl", side_effect=Exception("Database connection failed")):
        with pytest.raises(BaseGiljoError) as exc_info:
            await task_service.log_task(content="Test task")

        assert "Database connection failed" in str(exc_info.value)
        assert exc_info.value.context.get("operation") == "log_task"


@pytest.mark.asyncio
async def test_log_task_impl_raises_not_found_on_nonexistent_project(task_service, test_tenant_key, test_product):
    """Test _log_task_impl raises ResourceNotFoundError when project_id not found"""
    nonexistent_project_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.log_task(
            content="Test task",
            project_id=nonexistent_project_id,
            product_id=test_product.id,
            tenant_key=test_tenant_key,
        )

    assert f"Project {nonexistent_project_id} not found" in str(exc_info.value)


# ============================================================================
# EXCEPTION TESTS - list_tasks
# ============================================================================


@pytest.mark.asyncio
async def test_list_tasks_raises_validation_error_no_tenant_context(db_manager):
    """Test list_tasks raises ValidationError when no tenant context"""
    # Create tenant manager that returns None
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = None

    service = TaskService(db_manager=db_manager, tenant_manager=tenant_manager)

    with pytest.raises(ValidationError) as exc_info:
        await service.list_tasks()

    assert "No tenant context available" in str(exc_info.value)
    assert exc_info.value.context.get("operation") == "list_tasks"


@pytest.mark.asyncio
async def test_list_tasks_raises_exception_on_database_error(task_service):
    """Test list_tasks raises BaseGiljoError on database errors"""
    with patch.object(task_service.db_manager, "get_session_async", side_effect=Exception("DB error")):
        with pytest.raises(BaseGiljoError) as exc_info:
            await task_service.list_tasks()

        assert "DB error" in str(exc_info.value)


# ============================================================================
# EXCEPTION TESTS - update_task
# ============================================================================


@pytest.mark.asyncio
async def test_update_task_raises_not_found_on_nonexistent_task(task_service):
    """Test update_task raises ResourceNotFoundError when task not found"""
    nonexistent_task_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.update_task(task_id=nonexistent_task_id, status="completed")

    assert f"Task {nonexistent_task_id} not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_update_task_raises_exception_on_database_error(task_service):
    """Test update_task raises BaseGiljoError on database errors"""
    with patch.object(task_service.db_manager, "get_session_async", side_effect=Exception("DB error")):
        with pytest.raises(BaseGiljoError) as exc_info:
            await task_service.update_task(task_id=str(uuid4()), status="completed")

        assert "DB error" in str(exc_info.value)


# ============================================================================
# EXCEPTION TESTS - get_task & _get_task_impl
# ============================================================================


@pytest.mark.asyncio
async def test_get_task_raises_validation_error_no_tenant_context(db_manager, db_session):
    """Test get_task raises ValidationError when no tenant context"""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = None

    service = TaskService(db_manager=db_manager, tenant_manager=tenant_manager, session=db_session)

    with pytest.raises(ValidationError) as exc_info:
        await service.get_task(task_id=str(uuid4()))

    assert "No tenant context available" in str(exc_info.value)
    assert exc_info.value.context.get("operation") == "get_task"


@pytest.mark.asyncio
async def test_get_task_raises_not_found_on_nonexistent_task(task_service):
    """Test get_task raises ResourceNotFoundError when task not found"""
    nonexistent_task_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.get_task(task_id=nonexistent_task_id)

    assert "Task not found" in str(exc_info.value)
    assert exc_info.value.context.get("task_id") == nonexistent_task_id


@pytest.mark.asyncio
async def test_get_task_raises_exception_on_database_error(task_service):
    """Test get_task raises BaseGiljoError on database errors"""
    with patch.object(task_service, "_get_task_impl", side_effect=Exception("DB error")):
        with pytest.raises(BaseGiljoError) as exc_info:
            await task_service.get_task(task_id=str(uuid4()))

        assert "DB error" in str(exc_info.value)


# ============================================================================
# EXCEPTION TESTS - delete_task & _delete_task_impl
# ============================================================================


@pytest.mark.asyncio
async def test_delete_task_raises_validation_error_no_tenant_context(db_manager, db_session):
    """Test delete_task raises ValidationError when no tenant context"""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = None

    service = TaskService(db_manager=db_manager, tenant_manager=tenant_manager, session=db_session)

    with pytest.raises(ValidationError) as exc_info:
        await service.delete_task(task_id=str(uuid4()), user_id=str(uuid4()))

    assert "No tenant context available" in str(exc_info.value)
    assert exc_info.value.context.get("operation") == "delete_task"


@pytest.mark.asyncio
async def test_delete_task_raises_not_found_on_nonexistent_task(task_service, test_user):
    """Test delete_task raises ResourceNotFoundError when task not found"""
    nonexistent_task_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.delete_task(task_id=nonexistent_task_id, user_id=test_user.id)

    assert "Task not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_task_raises_not_found_on_nonexistent_user(task_service, test_task):
    """Test delete_task raises ResourceNotFoundError when user not found"""
    nonexistent_user_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.delete_task(task_id=test_task.id, user_id=nonexistent_user_id)

    assert "User not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_task_raises_authorization_error_insufficient_permissions(
    task_service, test_task, db_session, test_tenant_key
):
    """Test delete_task raises AuthorizationError when user lacks permission"""
    # Create another user who didn't create the task
    other_user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("OtherPassword123"),
        full_name="Other User",
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    with pytest.raises(AuthorizationError) as exc_info:
        await task_service.delete_task(task_id=test_task.id, user_id=other_user.id)

    assert "Not authorized to delete this task" in str(exc_info.value)


@pytest.mark.asyncio
async def test_delete_task_raises_exception_on_database_error(task_service):
    """Test delete_task raises BaseGiljoError on database errors"""
    with patch.object(task_service, "_delete_task_impl", side_effect=Exception("DB error")):
        with pytest.raises(BaseGiljoError) as exc_info:
            await task_service.delete_task(task_id=str(uuid4()), user_id=str(uuid4()))

        assert "DB error" in str(exc_info.value)


# ============================================================================
# EXCEPTION TESTS - convert_to_project & _convert_to_project_impl
# ============================================================================


@pytest.mark.asyncio
async def test_convert_to_project_raises_validation_error_no_tenant_context(db_manager, db_session):
    """Test convert_to_project raises ValidationError when no tenant context"""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = None

    service = TaskService(db_manager=db_manager, tenant_manager=tenant_manager, session=db_session)

    with pytest.raises(ValidationError) as exc_info:
        await service.convert_to_project(
            task_id=str(uuid4()),
            project_name="Test Project",
            strategy="create_new",
            include_subtasks=False,
            user_id=str(uuid4()),
        )

    assert "No tenant context available" in str(exc_info.value)
    assert exc_info.value.context.get("operation") == "convert_to_project"


@pytest.mark.asyncio
async def test_convert_to_project_raises_not_found_on_nonexistent_task(task_service, test_user):
    """Test convert_to_project raises ResourceNotFoundError when task not found"""
    nonexistent_task_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.convert_to_project(
            task_id=nonexistent_task_id,
            project_name="Test Project",
            strategy="create_new",
            include_subtasks=False,
            user_id=test_user.id,
        )

    assert "Task not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_convert_to_project_raises_validation_error_already_converted(
    task_service, test_task, test_user, db_session, test_product, test_tenant_key
):
    """Test convert_to_project raises ValidationError when task already converted"""
    # Create a project to reference (to satisfy foreign key constraint)
    converted_project = Project(
        id=str(uuid4()),
        name=f"Converted Project {uuid4().hex[:6]}",
        description="Previously converted project",
        mission="Test mission",
        product_id=test_product.id,
        tenant_key=test_tenant_key,
        status="inactive",
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(converted_project)
    await db_session.flush()

    # Mark task as already converted
    test_task.converted_to_project_id = converted_project.id
    await db_session.flush()

    with pytest.raises(ValidationError) as exc_info:
        await task_service.convert_to_project(
            task_id=test_task.id,
            project_name="Test Project",
            strategy="create_new",
            include_subtasks=False,
            user_id=test_user.id,
        )

    assert f"Task already converted to project {test_task.converted_to_project_id}" in str(exc_info.value)


@pytest.mark.asyncio
async def test_convert_to_project_raises_not_found_on_nonexistent_user(task_service, test_task):
    """Test convert_to_project raises ResourceNotFoundError when user not found"""
    nonexistent_user_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.convert_to_project(
            task_id=test_task.id,
            project_name="Test Project",
            strategy="create_new",
            include_subtasks=False,
            user_id=nonexistent_user_id,
        )

    assert "User not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_convert_to_project_raises_authorization_error_insufficient_permissions(
    task_service, test_task, db_session, test_tenant_key
):
    """Test convert_to_project raises AuthorizationError when user lacks permission"""
    # Create another user who didn't create the task
    other_user = User(
        id=str(uuid4()),
        username=f"otheruser_{uuid4().hex[:6]}",
        email=f"other_{uuid4().hex[:6]}@example.com",
        password_hash=bcrypt.hash("OtherPassword123"),
        full_name="Other User",
        role="developer",
        tenant_key=test_tenant_key,
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    with pytest.raises(AuthorizationError) as exc_info:
        await task_service.convert_to_project(
            task_id=test_task.id,
            project_name="Test Project",
            strategy="create_new",
            include_subtasks=False,
            user_id=other_user.id,
        )

    assert "Not authorized to convert this task" in str(exc_info.value)


@pytest.mark.asyncio
async def test_convert_to_project_raises_validation_error_no_active_product(
    task_service, test_task, test_user, test_product
):
    """Test convert_to_project raises ValidationError when no active product"""
    # Deactivate the product
    test_product.is_active = False

    with pytest.raises(ValidationError) as exc_info:
        await task_service.convert_to_project(
            task_id=test_task.id,
            project_name="Test Project",
            strategy="create_new",
            include_subtasks=False,
            user_id=test_user.id,
        )

    assert "No active product" in str(exc_info.value)


@pytest.mark.asyncio
async def test_convert_to_project_raises_exception_on_database_error(task_service):
    """Test convert_to_project raises BaseGiljoError on database errors"""
    with patch.object(task_service, "_convert_to_project_impl", side_effect=Exception("DB error")):
        with pytest.raises(BaseGiljoError) as exc_info:
            await task_service.convert_to_project(
                task_id=str(uuid4()),
                project_name="Test",
                strategy="create_new",
                include_subtasks=False,
                user_id=str(uuid4()),
            )

        assert "DB error" in str(exc_info.value)


# ============================================================================
# EXCEPTION TESTS - change_status & _change_status_impl
# ============================================================================


@pytest.mark.asyncio
async def test_change_status_raises_validation_error_no_tenant_context(db_manager, db_session):
    """Test change_status raises ValidationError when no tenant context"""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = None

    service = TaskService(db_manager=db_manager, tenant_manager=tenant_manager, session=db_session)

    with pytest.raises(ValidationError) as exc_info:
        await service.change_status(task_id=str(uuid4()), new_status="completed")

    assert "No tenant context available" in str(exc_info.value)
    assert exc_info.value.context.get("operation") == "change_status"


@pytest.mark.asyncio
async def test_change_status_raises_not_found_on_nonexistent_task(task_service):
    """Test change_status raises ResourceNotFoundError when task not found"""
    nonexistent_task_id = str(uuid4())

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await task_service.change_status(task_id=nonexistent_task_id, new_status="completed")

    assert "Task not found" in str(exc_info.value)
    assert exc_info.value.context.get("task_id") == nonexistent_task_id


@pytest.mark.asyncio
async def test_change_status_raises_exception_on_database_error(task_service):
    """Test change_status raises BaseGiljoError on database errors"""
    with patch.object(task_service, "_change_status_impl", side_effect=Exception("DB error")):
        with pytest.raises(BaseGiljoError) as exc_info:
            await task_service.change_status(task_id=str(uuid4()), new_status="completed")

        assert "DB error" in str(exc_info.value)


# ============================================================================
# EXCEPTION TESTS - get_summary & _get_summary_impl
# ============================================================================


@pytest.mark.asyncio
async def test_get_summary_raises_validation_error_no_tenant_context(db_manager, db_session):
    """Test get_summary raises ValidationError when no tenant context"""
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = None

    service = TaskService(db_manager=db_manager, tenant_manager=tenant_manager, session=db_session)

    with pytest.raises(ValidationError) as exc_info:
        await service.get_summary()

    assert "No tenant context available" in str(exc_info.value)
    assert exc_info.value.context.get("operation") == "get_summary"


@pytest.mark.asyncio
async def test_get_summary_raises_exception_on_database_error(task_service):
    """Test get_summary raises BaseGiljoError on database errors"""
    with patch.object(task_service, "_get_summary_impl", side_effect=Exception("DB error")):
        with pytest.raises(BaseGiljoError) as exc_info:
            await task_service.get_summary()

        assert "DB error" in str(exc_info.value)
