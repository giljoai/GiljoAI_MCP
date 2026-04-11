# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test suite for TaskService CRUD operations - split from test_task_service_enhanced.py

Covers:
- get_task (single task retrieval by ID)
- delete_task (soft/hard delete with permission checks)
- list_tasks (returns list[Task])
- update_task (returns TaskUpdateResult)
- create_task (returns str task_id)
"""

import random
from datetime import datetime, timezone
from uuid import uuid4

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.exceptions import AuthorizationError, ResourceNotFoundError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Task
from src.giljo_mcp.schemas.service_responses import TaskUpdateResult


# ============================================================================
# LOCAL FIXTURES (override conftest test_project which lacks product_id)
# ============================================================================


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
        password_hash=bcrypt.hashpw("Password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
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
    result = await task_service.update_task(task_id=str(test_task.id), status="in_progress", priority="high")

    # 0731c: update_task now returns TaskUpdateResult
    assert isinstance(result, TaskUpdateResult)
    assert result.task_id == str(test_task.id)
    assert "status" in result.updated_fields
    assert "priority" in result.updated_fields


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
