"""
Test suite for TaskService permission helpers - split from test_task_service_enhanced.py

Covers:
- can_delete_task (permission helper)
"""

import random
from datetime import datetime, timezone
from uuid import uuid4

import pytest
import pytest_asyncio
import bcrypt

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Task


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
# TEST: Permission Helpers (unchanged - already return bool)
# ============================================================================


@pytest.mark.asyncio
async def test_can_delete_task_as_creator(task_service, test_task, test_user):
    """Test creator can delete their own task"""
    can_delete = task_service._conversion.can_delete_task(test_task, test_user)
    assert can_delete is True


@pytest.mark.asyncio
async def test_can_delete_task_as_admin(task_service, test_task, admin_user):
    """Test admin can delete any task in tenant"""
    can_delete = task_service._conversion.can_delete_task(test_task, admin_user)
    assert can_delete is True


@pytest.mark.asyncio
async def test_can_delete_task_denied(task_service, test_task, db_session, test_tenant_key):
    """Test other developer cannot delete task they didn't create"""
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

    can_delete = task_service._conversion.can_delete_task(test_task, other_user)
    assert can_delete is False
