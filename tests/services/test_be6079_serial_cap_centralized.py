# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6079: the >9999 serial-exhaustion cap lives in the ALLOCATOR.

Before BE-6079 the ``> 9999`` cap (decision D) was duplicated inline on only the
two primary create paths (project_service ``_mutation_mixin``, task_service
``_log_task_impl``); the REST ``POST /api/v1/tasks`` create and the
task->project conversion untyped-fallback both auto-assigned a serial WITHOUT a
cap. The check now lives in the single allocator every auto-assign path funnels
through — ``ProjectRepository.get_next_series_number_shared`` — so no path can
mint a 5-digit serial.

This module pins the new home of the cap:
- it raises directly at the repository layer (the layer the bug would occur),
- the task->project untyped-fallback conversion path is gated by it.

The project-create and task-create-for-mcp paths are pinned by the pre-existing
``TestGlobalSerialCounter.test_project_cap_rejected_above_9999`` /
``test_task_cap_rejected_above_9999`` in ``test_shared_series_counter.py``; the
REST ``POST /api/v1/tasks`` path by
``test_be6049c_rest_task_create_tsk.test_rest_create_task_gated_at_serial_cap``.
Together the four auto-assign paths + the allocator are all covered.
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.exceptions import ValidationError
from giljo_mcp.models import Project, Task, User
from giljo_mcp.models.products import Product
from giljo_mcp.repositories.project_repository import MAX_SERIES_NUMBER, ProjectRepository
from giljo_mcp.services.task_conversion_service import TaskConversionService


@pytest_asyncio.fixture
async def active_product(db_session, test_tenant_key) -> Product:
    product = Product(
        id=str(uuid4()),
        name=f"Cap Product {uuid4().hex[:6]}",
        description="Product for serial-cap tests",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


async def _seed_project_at(db_session, tenant_key: str, product_id: str, series_number: int) -> Project:
    """Insert an ACTIVE (non-deleted) project at ``series_number`` to set the watermark."""
    proj = Project(
        id=str(uuid4()),
        name=f"Watermark-{series_number}",
        description="watermark seed",
        mission="",
        tenant_key=tenant_key,
        product_id=product_id,
        status="inactive",
        series_number=series_number,
    )
    db_session.add(proj)
    await db_session.commit()
    await db_session.refresh(proj)
    return proj


class TestAllocatorCap:
    @pytest.mark.asyncio
    async def test_allocator_raises_at_cap(
        self,
        db_session,
        test_tenant_key: str,
        active_product: Product,
    ):
        """``get_next_series_number_shared`` itself raises when the next value > 9999."""
        await _seed_project_at(db_session, test_tenant_key, active_product.id, MAX_SERIES_NUMBER)

        repo = ProjectRepository()
        with pytest.raises(ValidationError, match="exhausted"):
            await repo.get_next_series_number_shared(db_session, test_tenant_key, active_product.id)

    @pytest.mark.asyncio
    async def test_allocator_allows_below_cap(
        self,
        db_session,
        test_tenant_key: str,
        active_product: Product,
    ):
        """One below the cap is fine and returns exactly MAX_SERIES_NUMBER (the last slot)."""
        await _seed_project_at(db_session, test_tenant_key, active_product.id, MAX_SERIES_NUMBER - 1)

        repo = ProjectRepository()
        nxt = await repo.get_next_series_number_shared(db_session, test_tenant_key, active_product.id)
        assert nxt == MAX_SERIES_NUMBER


class TestConversionFallbackCap:
    @pytest.mark.asyncio
    async def test_untyped_conversion_gated_at_cap(
        self,
        db_manager,
        db_session,
        test_tenant_key: str,
        active_product: Product,
    ):
        """The task->project untyped-fallback allocates a serial — it must be capped too.

        BE-6079: this path was previously UNCAPPED (it called the allocator with no
        inline guard). With the cap centralized in the allocator, converting an
        untyped task when the product is at the 9999 watermark must raise.
        """
        from giljo_mcp.tenant import TenantManager

        tm = TenantManager()
        tm.set_current_tenant(test_tenant_key)
        conversion_service = TaskConversionService(db_manager=db_manager, tenant_manager=tm, session=db_session)

        user = User(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            username=f"u_{uuid4().hex[:8]}",
            email=f"{uuid4().hex[:8]}@test.local",
            role="admin",
        )
        db_session.add(user)
        await _seed_project_at(db_session, test_tenant_key, active_product.id, MAX_SERIES_NUMBER)

        # Untyped task (task_type_id NULL) -> conversion takes the fresh-number fallback.
        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=active_product.id,
            title="untyped at cap",
            description="legacy untyped task to convert when serial space is exhausted",
            status="pending",
            priority="medium",
            created_by_user_id=user.id,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        with pytest.raises(ValidationError, match="exhausted"):
            await conversion_service.convert_to_project(
                task_id=task.id,
                project_name=None,
                strategy="single",
                include_subtasks=False,
                user_id=user.id,
            )

        # And the originating task must NOT have been marked converted on the failed attempt.
        refreshed = (await db_session.execute(select(Task).where(Task.id == task.id))).scalar_one()
        assert refreshed.converted_to_project_id is None
