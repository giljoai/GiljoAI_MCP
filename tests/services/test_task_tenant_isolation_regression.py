"""
Tenant isolation regression tests for TaskService (Security Fix).

Verifies that cross-tenant data leaks are prevented for:
- _update_task_impl() UPDATE query (CRITICAL: reads tenant from TenantManager)
- assign_task() and complete_task() (delegate to update_task)
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

from src.giljo_mcp.exceptions import ResourceNotFoundError, ValidationError
from src.giljo_mcp.models import Product, Task
from src.giljo_mcp.services.task_service import TaskService
from src.giljo_mcp.tenant import TenantManager


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
    tenant_manager = two_tenant_tasks["tenant_manager"]

    # Set current tenant to A
    TenantManager.set_current_tenant(tenant_a)

    # Tenant A tries to update tenant B's task
    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.update_task(
            task_id=task_b.id,
            status="in_progress",
        )

    assert (
        "not found" in exc_info.value.message.lower()
        or "access denied" in exc_info.value.message.lower()
    )

    # Verify the task was NOT modified (status unchanged)
    await db_session.refresh(task_b)
    assert task_b.status == "pending", (
        "Cross-tenant update modified another tenant's task!"
    )


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
async def test_update_task_no_tenant_context_raises_validation_error(
    db_session, two_tenant_tasks
):
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


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_assign_task_blocks_cross_tenant(db_session, two_tenant_tasks):
    """
    assign_task() delegates to update_task(), which must enforce tenant isolation.
    Tenant A must not be able to assign tenant B's task to an agent.
    """
    tenant_a = two_tenant_tasks["tenant_a"]
    task_b = two_tenant_tasks["task_b"]
    service = two_tenant_tasks["service"]

    # Set current tenant to A
    TenantManager.set_current_tenant(tenant_a)

    with pytest.raises(ResourceNotFoundError):
        await service.assign_task(
            task_id=task_b.id,
            agent_name="rogue-agent",
        )

    # Verify the task was NOT assigned
    await db_session.refresh(task_b)
    assert task_b.status == "pending", (
        "Cross-tenant assign_task modified another tenant's task!"
    )


# ============================================================================
# complete_task() --- Inherits Tenant Protection from update_task()
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_complete_task_blocks_cross_tenant(db_session, two_tenant_tasks):
    """
    complete_task() delegates to update_task(), which must enforce tenant isolation.
    Tenant A must not be able to complete tenant B's task.
    """
    tenant_a = two_tenant_tasks["tenant_a"]
    task_b = two_tenant_tasks["task_b"]
    service = two_tenant_tasks["service"]

    # Set current tenant to A
    TenantManager.set_current_tenant(tenant_a)

    with pytest.raises(ResourceNotFoundError):
        await service.complete_task(task_id=task_b.id)

    # Verify the task was NOT completed
    await db_session.refresh(task_b)
    assert task_b.status == "pending", (
        "Cross-tenant complete_task modified another tenant's task!"
    )


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

    # 2. Assign cross-tenant -- should raise
    try:
        await service.assign_task(task_id=task_b.id, agent_name="rogue-agent")
        violations.append("assign_task() allowed cross-tenant assignment")
    except (ResourceNotFoundError, ValidationError):
        pass

    # 3. Complete cross-tenant -- should raise
    try:
        await service.complete_task(task_id=task_b.id)
        violations.append("complete_task() allowed cross-tenant completion")
    except (ResourceNotFoundError, ValidationError):
        pass

    # 4. Get cross-tenant -- should raise
    try:
        await service.get_task(task_id=task_b.id)
        violations.append("get_task() allowed cross-tenant read")
    except (ResourceNotFoundError, ValidationError):
        pass

    assert len(violations) == 0, (
        "CRITICAL: Tenant isolation violated!\nViolations:\n"
        + "\n".join(f"- {v}" for v in violations)
    )

    # Verify task B was never modified by any operation
    await db_session.refresh(task_b)
    assert task_b.status == "pending", (
        "CRITICAL: Task B status was modified by cross-tenant operations!"
    )
