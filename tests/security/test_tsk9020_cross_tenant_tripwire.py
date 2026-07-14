# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
TSK-9020 -- permanent cross-tenant isolation CI tripwire.

From the 2026-07-02 security posture decision (operator-internal,
P1): "no cross-tenant read/write path, ENFORCED BY PERMANENT CI TESTS (not a one-off audit)."

Seeds two tenants (A, B) with rows on every major surface (projects, tasks,
memory, products), then has tenant A attempt to READ and UPDATE
tenant B's rows via the REAL service/repository path (the same code the API
and MCP tools call in production -- no raw SQL, no mocking). Every attempt
must fail (ResourceNotFoundError / ValidationError, or an empty result --
service-level "not found" is indistinguishable from cross-tenant here by
design, see individual service docstrings).

This suite is intentionally standalone/additive (no shared fixtures pulled
from tests/services/conftest.py) so it keeps working as a tripwire even if
those per-domain regression suites are ever reorganized.

Messaging surface note: the agent message bus (MessageService) was retired in
BE-9012d (folded into the Hub / comm_threads). Its cross-tenant isolation is
now covered by tests/api/test_comm_threads_endpoints.py
(test_tenant_isolation_get_thread / _post_to_thread / _delete_thread), so this
tripwire no longer exercises the removed MessageService surface.

Memory (ProductMemoryService) note: entries are append-only -- there is no
update_entry operation to attack, so only the read surface (search_memory)
is exercised here (test_cross_tenant_read_blocked_across_all_surfaces). Its
sibling write path, create_entry() (TSK-9022), is exercised separately by
test_create_entry_rejects_product_tenant_mismatch below: it now cross-checks
that the DTO's product_id is owned by the DTO's tenant_key before writing,
instead of trusting the caller-supplied tenant_key alone.
"""

import random
import uuid
from datetime import UTC, datetime

import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.database import TenantIsolationError
from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.models import Product, Project, Task
from giljo_mcp.services.dto import MemoryEntryCreateParams
from giljo_mcp.services.product_memory_service import ProductMemoryService
from giljo_mcp.services.product_service import ProductService
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.services.task_service import TaskService
from giljo_mcp.tenant import TenantManager


@pytest_asyncio.fixture(scope="function")
async def two_tenants_full_surface(db_session, db_manager):
    """
    Seed tenant A and tenant B each with one row on every major surface:
    product, project, task, and a 360-memory entry. (The message-bus surface
    was retired in BE-9012d; the Hub replacement has its own cross-tenant
    isolation tests -- see the module docstring.)
    """
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    product_a = Product(
        id=str(uuid.uuid4()),
        name="TSK-9020 Tenant A Product",
        description="Tripwire product for tenant A",
        tenant_key=tenant_a,
        is_active=True,
    )
    product_b = Product(
        id=str(uuid.uuid4()),
        name="TSK-9020 Tenant B Product",
        description="Tripwire product for tenant B -- must never be reachable from tenant A",
        tenant_key=tenant_b,
        is_active=True,
    )
    db_session.add_all([product_a, product_b])
    await db_session.commit()

    project_a = Project(
        id=str(uuid.uuid4()),
        name="TSK-9020 Tenant A Project",
        description="Tripwire project A",
        mission="Tripwire mission A",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="active",
        series_number=random.randint(1, 900_000),
    )
    project_b = Project(
        id=str(uuid.uuid4()),
        name="TSK-9020 Tenant B Project",
        description="Tripwire project B -- must never be reachable from tenant A",
        mission="Tripwire mission B",
        tenant_key=tenant_b,
        product_id=product_b.id,
        status="active",
        series_number=random.randint(1, 900_000),
    )
    db_session.add_all([project_a, project_b])
    await db_session.commit()

    task_a = Task(
        id=str(uuid.uuid4()),
        title="TSK-9020 Tenant A Task",
        description="Tripwire task A",
        tenant_key=tenant_a,
        product_id=product_a.id,
        project_id=project_a.id,
        status="pending",
    )
    task_b = Task(
        id=str(uuid.uuid4()),
        title="TSK-9020 Tenant B Task",
        description="Tripwire task B -- must never be reachable from tenant A",
        tenant_key=tenant_b,
        product_id=product_b.id,
        project_id=project_b.id,
        status="pending",
    )
    db_session.add_all([task_a, task_b])
    await db_session.commit()

    for obj in (product_a, product_b, project_a, project_b, task_a, task_b):
        await db_session.refresh(obj)

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "product_a": product_a,
        "product_b": product_b,
        "project_a": project_a,
        "project_b": project_b,
        "task_a": task_a,
        "task_b": task_b,
    }


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_cross_tenant_read_blocked_across_all_surfaces(db_session, db_manager, two_tenants_full_surface):
    """
    Tenant A attempts to READ tenant B's row on every surface via the real
    service path. Every attempt must fail (not-found error, or an empty
    result for surfaces whose contract returns empty rather than raising).
    """
    data = two_tenants_full_surface
    tenant_a = data["tenant_a"]

    TenantManager.set_current_tenant(tenant_a)
    try:
        violations: list[str] = []

        project_service = ProjectService(db_manager=db_manager, tenant_manager=TenantManager(), test_session=db_session)
        try:
            await project_service.get_project(project_id=data["project_b"].id, tenant_key=tenant_a)
            violations.append("ProjectService.get_project() returned tenant B's project")
        except ResourceNotFoundError:
            pass

        task_service = TaskService(db_manager=db_manager, tenant_manager=TenantManager(), session=db_session)
        try:
            await task_service.get_task(task_id=data["task_b"].id)
            violations.append("TaskService.get_task() returned tenant B's task")
        except ResourceNotFoundError:
            pass

        # Messaging surface retired in BE-9012d (bus -> Hub). Cross-tenant Hub
        # isolation is covered by tests/api/test_comm_threads_endpoints.py
        # (test_tenant_isolation_get_thread / _post_to_thread / _delete_thread).

        product_service = ProductService(db_manager=db_manager, tenant_key=tenant_a, test_session=db_session)
        try:
            await product_service.get_product(product_id=data["product_b"].id)
            violations.append("ProductService.get_product() returned tenant B's product")
        except ResourceNotFoundError:
            pass

        memory_service = ProductMemoryService(db_manager=db_manager, tenant_key=tenant_a, test_session=db_session)
        try:
            await memory_service.search_memory(product_id=data["product_b"].id, query="tripwire")
            violations.append("ProductMemoryService.search_memory() searched tenant B's product")
        except ResourceNotFoundError:
            pass

        assert not violations, "CRITICAL: cross-tenant READ leak(s):\n" + "\n".join(f"- {v}" for v in violations)
    finally:
        TenantManager.clear_current_tenant()


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_cross_tenant_update_blocked_across_all_surfaces(db_session, db_manager, two_tenants_full_surface):
    """
    Tenant A attempts to UPDATE tenant B's row on every surface that supports
    an update via the real service path. Every attempt must fail, AND tenant
    B's row must be verifiably unchanged afterward (a raised exception alone
    does not prove the write never landed).
    """
    data = two_tenants_full_surface
    tenant_a = data["tenant_a"]

    TenantManager.set_current_tenant(tenant_a)
    try:
        violations: list[str] = []

        project_service = ProjectService(db_manager=db_manager, tenant_manager=TenantManager(), test_session=db_session)
        try:
            await project_service.update_project(project_id=data["project_b"].id, updates={"name": "pwned"})
            violations.append("ProjectService.update_project() updated tenant B's project")
        except ResourceNotFoundError:
            pass

        task_service = TaskService(db_manager=db_manager, tenant_manager=TenantManager(), session=db_session)
        try:
            await task_service.update_task(task_id=data["task_b"].id, status="in_progress")
            violations.append("TaskService.update_task() updated tenant B's task")
        except ResourceNotFoundError:
            pass

        # Messaging surface retired in BE-9012d (bus -> Hub); Hub cross-tenant
        # update isolation is covered in tests/api/test_comm_threads_endpoints.py.

        product_service = ProductService(db_manager=db_manager, tenant_key=tenant_a, test_session=db_session)
        try:
            await product_service.update_product(product_id=data["product_b"].id, name="pwned")
            violations.append("ProductService.update_product() updated tenant B's product")
        except ResourceNotFoundError:
            pass

        assert not violations, "CRITICAL: cross-tenant UPDATE leak(s):\n" + "\n".join(f"- {v}" for v in violations)

        # Prove the writes truly never landed, not just that an exception was raised.
        await db_session.refresh(data["project_b"])
        await db_session.refresh(data["task_b"])
        await db_session.refresh(data["product_b"])
        assert data["project_b"].name == "TSK-9020 Tenant B Project"
        assert data["task_b"].status == "pending"
        assert data["product_b"].name == "TSK-9020 Tenant B Product"
    finally:
        TenantManager.clear_current_tenant()


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_negative_control_unscoped_query_raises(db_session, two_tenants_full_surface):
    """
    Negative control: proves the tripwire can never silently pass.

    A deliberately-unscoped ORM SELECT against a tenant-scoped model, issued
    with NO active tenant context, MUST raise TenantIsolationError. If this
    assertion ever fails, the underlying session-level guard has been
    weakened or removed -- which would mean the READ/UPDATE assertions above
    could start silently passing for the wrong reason (nothing found because
    an exception fired) instead of by real tenant filtering. This is the
    same DB-session guard the whole suite implicitly relies on.
    """
    data = two_tenants_full_surface
    db_session.info.pop("tenant_key", None)
    db_session.info.pop("tenant_key_source", None)
    previous_tenant = TenantManager.get_current_tenant()
    TenantManager.clear_current_tenant()

    try:
        with pytest.raises(TenantIsolationError):
            await db_session.execute(select(Product).where(Product.id == data["product_b"].id))

        with pytest.raises(TenantIsolationError):
            await db_session.execute(select(Task).where(Task.id == data["task_b"].id))
    finally:
        if previous_tenant:
            TenantManager.set_current_tenant(previous_tenant)


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_create_entry_rejects_product_tenant_mismatch(db_session, db_manager, two_tenants_full_surface):
    """
    TSK-9022: ProductMemoryService.create_entry() must not trust a
    caller-supplied ``tenant_key`` that does not actually own the referenced
    product. Builds a DTO claiming tenant B's product_id under tenant A's
    tenant_key -- the write must be rejected, and no row must land.
    """
    data = two_tenants_full_surface
    tenant_a = data["tenant_a"]
    tenant_b = data["tenant_b"]
    product_b = data["product_b"]

    memory_service = ProductMemoryService(db_manager=db_manager, tenant_key=tenant_a, test_session=db_session)
    mismatched_params = MemoryEntryCreateParams(
        tenant_key=tenant_a,
        product_id=product_b.id,
        sequence=1,
        entry_type="project_completion",
        source="tsk9022_tripwire",
        timestamp=datetime.now(tz=UTC),
        summary="cross-tenant write attempt",
    )

    with pytest.raises(ResourceNotFoundError):
        await memory_service.create_entry(params=mismatched_params, session=db_session)

    # sanity: product_b itself must be untouched (refresh bypasses the ORM
    # tenant guard's statement-level check, same as the UPDATE tripwire above).
    await db_session.refresh(product_b)
    assert product_b.name == "TSK-9020 Tenant B Product"

    from giljo_mcp.models.product_memory_entry import ProductMemoryEntry

    # Proving no row landed for product_b requires an active tenant_b context
    # for the ORM guard to permit the SELECT at all.
    TenantManager.set_current_tenant(tenant_b)
    try:
        leaked = await db_session.execute(
            select(ProductMemoryEntry).where(ProductMemoryEntry.product_id == product_b.id)
        )
        assert leaked.scalars().all() == [], "CRITICAL: cross-tenant memory entry write landed"
    finally:
        TenantManager.clear_current_tenant()
