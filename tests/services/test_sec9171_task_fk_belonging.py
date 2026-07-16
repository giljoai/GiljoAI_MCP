# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-9171 (#15) regression: cross-tenant FK belonging checks on task writes.

Edition Scope: Both (task_service is CE-shared code).

Before the fix, ``_log_task_impl`` passed ``parent_task_id`` to the ORM
unchecked and ``_update_task_impl`` applied ``parent_task_id`` / ``project_id``
via the field allowlist with no ownership re-check — the allowlist gates field
NAMES, not row OWNERSHIP. A tenant-A caller could reference a tenant-B UUID and
persist a cross-tenant FK on its own row (integrity break, not a disclosure:
reads stay tenant-scoped).

The guard mirrors the EXISTING ``project_id`` belonging check on create: a
tenant-scoped repo lookup that raises ``ResourceNotFoundError`` when the row is
not owned. Same layer as the bug (service), real DB, no mocks; parallel-safe —
each test mints its own tenants/products, no module-level mutable state.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.database import tenant_session_context
from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.models import Product, Project, Task
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


@pytest_asyncio.fixture
async def product_a(db_session, test_tenant_key) -> Product:
    product = Product(
        id=str(uuid4()),
        name=f"SEC9171 Product A {uuid4().hex[:6]}",
        description="task FK belonging tests (tenant A)",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    return product


@pytest_asyncio.fixture
async def tenant_b() -> str:
    return TenantManager.generate_tenant_key()


@pytest_asyncio.fixture
async def foreign_rows(db_session, tenant_b) -> dict:
    """A product + task + project owned by tenant B (the victim tenant)."""
    with tenant_session_context(db_session, tenant_b):
        product = Product(
            id=str(uuid4()),
            name=f"SEC9171 Product B {uuid4().hex[:6]}",
            description="task FK belonging tests (tenant B)",
            tenant_key=tenant_b,
            is_active=True,
        )
        db_session.add(product)
        await db_session.flush()
        task = Task(
            id=str(uuid4()),
            tenant_key=tenant_b,
            product_id=product.id,
            title="tenant B task",
            description="victim parent candidate",
            status="pending",
            priority="medium",
        )
        project = Project(
            id=str(uuid4()),
            tenant_key=tenant_b,
            product_id=product.id,
            name="tenant B project",
            description="victim project candidate",
            mission="sec9171",
            status="active",
        )
        db_session.add_all([task, project])
        await db_session.commit()
    return {"product_id": product.id, "task_id": task.id, "project_id": project.id}


async def _make_task_a(task_service, product_a, test_tenant_key, *, parent_task_id: str | None = None) -> str:
    return await task_service.log_task(
        content=f"tenant A task {uuid4().hex[:6]}",
        product_id=product_a.id,
        tenant_key=test_tenant_key,
        parent_task_id=parent_task_id,
    )


# ---------------------------------------------------------------------------
# Create path
# ---------------------------------------------------------------------------


async def test_create_rejects_cross_tenant_parent_task(
    task_service, db_session, test_tenant_key, product_a, foreign_rows
):
    with pytest.raises(ResourceNotFoundError):
        await _make_task_a(task_service, product_a, test_tenant_key, parent_task_id=foreign_rows["task_id"])

    # Nothing persisted pointing at the foreign parent.
    with tenant_session_context(db_session, test_tenant_key):
        rows = (
            await db_session.execute(
                select(Task.id).where(
                    Task.tenant_key == test_tenant_key, Task.parent_task_id == foreign_rows["task_id"]
                )
            )
        ).all()
    assert rows == []


async def test_create_accepts_same_tenant_parent_task(task_service, db_session, test_tenant_key, product_a):
    parent_id = await _make_task_a(task_service, product_a, test_tenant_key)
    child_id = await _make_task_a(task_service, product_a, test_tenant_key, parent_task_id=parent_id)

    with tenant_session_context(db_session, test_tenant_key):
        child = (await db_session.execute(select(Task).where(Task.id == child_id))).scalar_one()
    assert child.parent_task_id == parent_id


# ---------------------------------------------------------------------------
# Update path
# ---------------------------------------------------------------------------


async def test_update_rejects_cross_tenant_parent_task(
    task_service, db_session, test_tenant_key, product_a, foreign_rows
):
    task_id = await _make_task_a(task_service, product_a, test_tenant_key)

    with pytest.raises(ResourceNotFoundError):
        await task_service.update_task(task_id, parent_task_id=foreign_rows["task_id"])

    with tenant_session_context(db_session, test_tenant_key):
        row = (await db_session.execute(select(Task).where(Task.id == task_id))).scalar_one()
    assert row.parent_task_id is None


async def test_update_rejects_cross_tenant_project(task_service, db_session, test_tenant_key, product_a, foreign_rows):
    task_id = await _make_task_a(task_service, product_a, test_tenant_key)

    with pytest.raises(ResourceNotFoundError):
        await task_service.update_task(task_id, project_id=foreign_rows["project_id"])

    with tenant_session_context(db_session, test_tenant_key):
        row = (await db_session.execute(select(Task).where(Task.id == task_id))).scalar_one()
    assert row.project_id is None


async def test_update_accepts_same_tenant_parent_and_unset(task_service, db_session, test_tenant_key, product_a):
    parent_id = await _make_task_a(task_service, product_a, test_tenant_key)
    task_id = await _make_task_a(task_service, product_a, test_tenant_key)

    result = await task_service.update_task(task_id, parent_task_id=parent_id)
    assert "parent_task_id" in result.updated_fields

    # Unsetting (None) stays allowed — belonging applies to non-null refs only.
    result = await task_service.update_task(task_id, parent_task_id=None)
    assert "parent_task_id" in result.updated_fields

    with tenant_session_context(db_session, test_tenant_key):
        row = (await db_session.execute(select(Task).where(Task.id == task_id))).scalar_one()
    assert row.parent_task_id is None


async def test_update_accepts_same_tenant_project(task_service, db_session, test_tenant_key, product_a):
    task_id = await _make_task_a(task_service, product_a, test_tenant_key)
    with tenant_session_context(db_session, test_tenant_key):
        project = Project(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=product_a.id,
            name="tenant A project",
            description="same-tenant project",
            mission="sec9171",
            status="active",
        )
        db_session.add(project)
        await db_session.commit()

    result = await task_service.update_task(task_id, project_id=project.id)
    assert "project_id" in result.updated_fields

    with tenant_session_context(db_session, test_tenant_key):
        row = (await db_session.execute(select(Task).where(Task.id == task_id))).scalar_one()
    assert row.project_id == project.id
