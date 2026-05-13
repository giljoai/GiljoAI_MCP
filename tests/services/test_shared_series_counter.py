# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-5065: Shared series_number counter across tasks and projects.

Under the same ``(tenant_key, product_id, taxonomy_type_id)`` bucket, creating a
task assigned to type BE then a project of type BE (or vice versa) must produce
``BE-N`` and ``BE-N+1`` — never two ``BE-N``. The repository helpers
``lock_rows_for_series_shared`` + ``get_next_series_number_shared`` enforce this
by computing ``max(series_number)`` across both ``tasks`` and ``projects`` for
the bucket inside a row-locked transaction.
"""

from uuid import uuid4

import pytest
import pytest_asyncio

from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import TaxonomyType
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.services.task_service import TaskService


@pytest_asyncio.fixture
async def be_taxonomy(db_session, test_tenant_key) -> TaxonomyType:
    tt = TaxonomyType(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        abbreviation="BE",
        label="Backend",
        color="#1f6feb",
        sort_order=1,
    )
    db_session.add(tt)
    await db_session.commit()
    await db_session.refresh(tt)
    return tt


@pytest_asyncio.fixture
async def active_product(db_session, test_tenant_key) -> Product:
    product = Product(
        id=str(uuid4()),
        name=f"Shared Counter Product {uuid4().hex[:6]}",
        description="Product for shared-counter tests",
        tenant_key=test_tenant_key,
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def project_service(db_manager, db_session, test_tenant_key) -> ProjectService:
    from giljo_mcp.tenant import TenantManager

    tm = TenantManager()
    tm.set_current_tenant(test_tenant_key)
    return ProjectService(db_manager=db_manager, tenant_manager=tm, test_session=db_session)


class TestSharedSeriesCounter:
    @pytest.mark.asyncio
    async def test_project_then_task(
        self,
        task_service: TaskService,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
        active_product: Product,
        be_taxonomy: TaxonomyType,
    ):
        project = await project_service.create_project(
            name="P1",
            mission="m1",
            description="d1",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )
        task_result = await task_service.create_task_for_mcp(
            title="T1",
            description="t1",
            task_type="BE",
            tenant_key=test_tenant_key,
        )

        # Project should be N (probably 1), task should be N+1.
        from giljo_mcp.models import Task

        task = (
            await db_session.execute(__import__("sqlalchemy").select(Task).where(Task.id == task_result["task_id"]))
        ).scalar_one()
        assert project.series_number == 1
        assert task.series_number == 2

    @pytest.mark.asyncio
    async def test_task_then_project(
        self,
        task_service: TaskService,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
        active_product: Product,
        be_taxonomy: TaxonomyType,
    ):
        task_result = await task_service.create_task_for_mcp(
            title="T1",
            description="t1",
            task_type="BE",
            tenant_key=test_tenant_key,
        )
        project = await project_service.create_project(
            name="P1",
            mission="m1",
            description="d1",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )

        from sqlalchemy import select

        from giljo_mcp.models import Task

        task = (await db_session.execute(select(Task).where(Task.id == task_result["task_id"]))).scalar_one()
        assert task.series_number == 1
        assert project.series_number == 2
