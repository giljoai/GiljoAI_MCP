# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Test suite for TaskService conversion and status operations - split from test_task_service_enhanced.py

Covers:
- convert_to_project (task -> project conversion with subtask handling)
- change_status (status change with automatic timestamp updates)
- get_summary (task statistics aggregation)
"""

import random
from datetime import datetime, timezone
from uuid import uuid4

import bcrypt
import pytest
import pytest_asyncio
from sqlalchemy import select

from src.giljo_mcp.exceptions import AuthorizationError
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Task
from src.giljo_mcp.schemas.service_responses import ConversionResult


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
        password_hash=bcrypt.hashpw("Password123".encode("utf-8"), bcrypt.gensalt()).decode("utf-8"),
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
