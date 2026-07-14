# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tenant isolation regression tests for TaskService (Security Fix).

Verifies that cross-tenant data leaks are prevented for:
- _update_task_impl() UPDATE query (CRITICAL: reads tenant from TenantManager)
- get_task() (CRITICAL: filters by tenant_key)

Test Strategy:
- Create entities in two tenants (A and B)
- Set TenantManager.set_current_tenant() to tenant A
- Attempt cross-tenant operations from tenant A against tenant B's tasks
- Verify all cross-tenant attempts are blocked

Follows patterns from: test_project_tenant_isolation_regression.py
"""

import uuid

import pytest
import pytest_asyncio

from giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from giljo_mcp.models import Product, Task
from giljo_mcp.models.auth import User
from giljo_mcp.services.task_service import TaskService
from giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture(scope="function")
async def two_tenant_tasks(db_session, db_manager):
    """
    Create tasks in two separate tenants for isolation testing.

    Tenant A: product_a, task_a (status="pending")
    Tenant B: product_b, task_b (status="pending")
    """
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    # Create products (required FK for tasks)
    product_a = Product(
        id=str(uuid.uuid4()),
        name="Tenant A Product",
        description="Product for tenant A",
        tenant_key=tenant_a,
        is_active=True,
    )
    product_b = Product(
        id=str(uuid.uuid4()),
        name="Tenant B Product",
        description="Product for tenant B",
        tenant_key=tenant_b,
        is_active=True,
    )
    db_session.add(product_a)
    db_session.add(product_b)
    await db_session.commit()

    # Create tasks
    task_a = Task(
        id=str(uuid.uuid4()),
        title="Tenant A Task",
        description="Task belonging to tenant A",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="pending",
    )
    task_b = Task(
        id=str(uuid.uuid4()),
        title="Tenant B Task",
        description="Task belonging to tenant B",
        tenant_key=tenant_b,
        product_id=product_b.id,
        status="pending",
    )

    db_session.add_all([task_a, task_b])
    await db_session.commit()

    for obj in [task_a, task_b]:
        await db_session.refresh(obj)

    # Create TaskService using test session
    tenant_manager = TenantManager()
    service = TaskService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        session=db_session,
    )

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "task_a": task_a,
        "task_b": task_b,
        "product_a": product_a,
        "product_b": product_b,
        "service": service,
        "tenant_manager": tenant_manager,
    }


# ============================================================================
# _update_task_impl() --- Cross-Tenant Modification Test
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_update_task_blocks_cross_tenant(db_session, two_tenant_tasks):
    """
    REGRESSION: _update_task_impl() must filter by tenant_key from TenantManager.

    Bug: _update_task_impl() previously did not enforce tenant isolation,
    allowing any tenant to update any other tenant's task if they knew the task_id.
    """
    tenant_a = two_tenant_tasks["tenant_a"]
    task_b = two_tenant_tasks["task_b"]
    service = two_tenant_tasks["service"]

    # Set current tenant to A
    TenantManager.set_current_tenant(tenant_a)

    # Tenant A tries to update tenant B's task
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.update_task(
            task_id=task_b.id,
            status="in_progress",
        )

    assert "not found" in exc_info.value.message.lower() or "access denied" in exc_info.value.message.lower()

    # Verify the task was NOT modified (status unchanged)
    await db_session.refresh(task_b)
    assert task_b.status == "pending", "Cross-tenant update modified another tenant's task!"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_update_task_same_tenant_succeeds(db_session, two_tenant_tasks):
    """
    Verify that same-tenant task update still works correctly.
    """
    tenant_a = two_tenant_tasks["tenant_a"]
    task_a = two_tenant_tasks["task_a"]
    service = two_tenant_tasks["service"]

    # Set current tenant to A
    TenantManager.set_current_tenant(tenant_a)

    # Tenant A updates their own task
    result = await service.update_task(
        task_id=task_a.id,
        status="in_progress",
    )

    assert task_a.id == result.task_id
    assert "status" in result.updated_fields

    # Verify task was actually updated
    await db_session.refresh(task_a)
    assert task_a.status == "in_progress"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_update_task_no_tenant_context_raises_validation_error(db_session, two_tenant_tasks):
    """
    update_task() with no tenant context must raise ValidationError,
    not silently proceed without filtering.
    """
    task_b = two_tenant_tasks["task_b"]
    service = two_tenant_tasks["service"]

    # Clear tenant context
    TenantManager.clear_current_tenant()

    with pytest.raises(ValidationError):
        await service.update_task(
            task_id=task_b.id,
            status="in_progress",
        )


# ============================================================================
# assign_task() --- Inherits Tenant Protection from update_task()
# ============================================================================


# ============================================================================
# get_task() --- Cross-Tenant Read Test
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_task_blocks_cross_tenant(db_session, two_tenant_tasks):
    """
    get_task() must filter by tenant_key from TenantManager.
    Tenant A must not be able to read tenant B's task.
    """
    tenant_a = two_tenant_tasks["tenant_a"]
    task_b = two_tenant_tasks["task_b"]
    service = two_tenant_tasks["service"]

    # Set current tenant to A
    TenantManager.set_current_tenant(tenant_a)

    with pytest.raises(ResourceNotFoundError):
        await service.get_task(task_id=task_b.id)


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_task_same_tenant_succeeds(db_session, two_tenant_tasks):
    """
    Verify that same-tenant get_task still works correctly.
    """
    tenant_a = two_tenant_tasks["tenant_a"]
    task_a = two_tenant_tasks["task_a"]
    service = two_tenant_tasks["service"]

    # Set current tenant to A
    TenantManager.set_current_tenant(tenant_a)

    task = await service.get_task(task_id=task_a.id)

    assert task.id == task_a.id
    assert task.title == "Tenant A Task"
    assert task.tenant_key == tenant_a


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_delete_task_treats_foreign_tenant_admin_as_not_found(db_session, two_tenant_tasks):
    """delete_task permission lookup must not load a foreign-tenant admin user."""
    tenant_a = two_tenant_tasks["tenant_a"]
    task_a = two_tenant_tasks["task_a"]
    service = two_tenant_tasks["service"]
    foreign_admin = User(
        id=str(uuid.uuid4()),
        username=f"foreign_admin_{uuid.uuid4().hex[:8]}",
        email=f"foreign_admin_{uuid.uuid4().hex[:8]}@example.com",
        tenant_key=two_tenant_tasks["tenant_b"],
        role="admin",
        is_active=True,
    )
    db_session.add(foreign_admin)
    await db_session.commit()

    TenantManager.set_current_tenant(tenant_a)

    with pytest.raises(ResourceNotFoundError):
        await service.delete_task(task_id=task_a.id, user_id=foreign_admin.id)

    assert await db_session.get(Task, task_a.id) is not None


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_delete_task_same_tenant_admin_succeeds(db_session, two_tenant_tasks):
    """Same-tenant admin users can still delete tasks."""
    tenant_a = two_tenant_tasks["tenant_a"]
    task_a = two_tenant_tasks["task_a"]
    service = two_tenant_tasks["service"]
    admin = User(
        id=str(uuid.uuid4()),
        username=f"tenant_admin_{uuid.uuid4().hex[:8]}",
        email=f"tenant_admin_{uuid.uuid4().hex[:8]}@example.com",
        tenant_key=tenant_a,
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    TenantManager.set_current_tenant(tenant_a)

    await service.delete_task(task_id=task_a.id, user_id=admin.id)

    # BE-6130b: soft delete — the row persists with deleted_at stamped, but it
    # drops out of every live read (get_task filters deleted_at IS NULL).
    soft_deleted = await db_session.get(Task, task_a.id)
    assert soft_deleted is not None
    assert soft_deleted.deleted_at is not None
    with pytest.raises(ResourceNotFoundError):
        await service.get_task(task_a.id)


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_convert_task_treats_foreign_tenant_admin_as_not_found(db_session, two_tenant_tasks):
    """Task conversion must not authorize a foreign-tenant admin user."""
    tenant_a = two_tenant_tasks["tenant_a"]
    task_a = two_tenant_tasks["task_a"]
    service = two_tenant_tasks["service"]
    foreign_admin = User(
        id=str(uuid.uuid4()),
        username=f"foreign_convert_admin_{uuid.uuid4().hex[:8]}",
        email=f"foreign_convert_admin_{uuid.uuid4().hex[:8]}@example.com",
        tenant_key=two_tenant_tasks["tenant_b"],
        role="admin",
        is_active=True,
    )
    db_session.add(foreign_admin)
    await db_session.commit()

    TenantManager.set_current_tenant(tenant_a)

    with pytest.raises(ResourceNotFoundError):
        await service.convert_to_project(
            task_id=task_a.id,
            project_name="Converted by foreign admin",
            strategy="create_new",
            include_subtasks=False,
            user_id=foreign_admin.id,
        )

    assert await db_session.get(Task, task_a.id) is not None


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_convert_task_same_tenant_admin_succeeds(db_session, two_tenant_tasks):
    """Same-tenant admin users can still convert tasks to projects."""
    tenant_a = two_tenant_tasks["tenant_a"]
    task_a = two_tenant_tasks["task_a"]
    service = two_tenant_tasks["service"]
    admin = User(
        id=str(uuid.uuid4()),
        username=f"tenant_convert_admin_{uuid.uuid4().hex[:8]}",
        email=f"tenant_convert_admin_{uuid.uuid4().hex[:8]}@example.com",
        tenant_key=tenant_a,
        role="admin",
        is_active=True,
    )
    db_session.add(admin)
    await db_session.commit()

    TenantManager.set_current_tenant(tenant_a)

    result = await service.convert_to_project(
        task_id=task_a.id,
        project_name="Converted by tenant admin",
        strategy="create_new",
        include_subtasks=False,
        user_id=admin.id,
    )

    assert result.project_name == "Converted by tenant admin"
    assert await db_session.get(Task, task_a.id) is None


# ============================================================================
# Combined --- Full Cross-Tenant Audit
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_task_service_cross_tenant_audit(db_session, two_tenant_tasks):
    """
    Integration test: Attempt every cross-tenant task operation from tenant A
    against tenant B's data. All must be blocked.
    """
    tenant_a = two_tenant_tasks["tenant_a"]
    task_b = two_tenant_tasks["task_b"]
    service = two_tenant_tasks["service"]

    violations = []

    # Set current tenant to A for all operations
    TenantManager.set_current_tenant(tenant_a)

    # 1. Update cross-tenant -- should raise
    try:
        await service.update_task(task_id=task_b.id, status="in_progress")
        violations.append("update_task() allowed cross-tenant update")
    except (ResourceNotFoundError, ValidationError):
        pass

    # 2. Get cross-tenant -- should raise
    try:
        await service.get_task(task_id=task_b.id)
        violations.append("get_task() allowed cross-tenant read")
    except (ResourceNotFoundError, ValidationError):
        pass

    assert len(violations) == 0, "CRITICAL: Tenant isolation violated!\nViolations:\n" + "\n".join(
        f"- {v}" for v in violations
    )

    # Verify task B was never modified by any operation
    await db_session.refresh(task_b)
    assert task_b.status == "pending", "CRITICAL: Task B status was modified by cross-tenant operations!"
