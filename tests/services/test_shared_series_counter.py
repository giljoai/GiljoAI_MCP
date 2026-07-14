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

from datetime import UTC
from uuid import uuid4

import pytest
import pytest_asyncio

from giljo_mcp.exceptions import ValidationError
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
async def fe_taxonomy(db_session, test_tenant_key) -> TaxonomyType:
    tt = TaxonomyType(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        abbreviation="FE",
        label="Frontend",
        color="#a371f7",
        sort_order=2,
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

    @pytest.mark.asyncio
    async def test_soft_deleted_project_excluded_from_high_water_mark(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
        active_product: Product,
        be_taxonomy: TaxonomyType,
    ):
        """A soft-deleted project at 9999 must NOT inflate ``max+1`` to 10000.

        Regression for the prod minting bug: ``get_next_series_number_shared``
        computed ``max(series_number)+1`` over ALL projects, so a soft-deleted
        ``9999`` (e.g. ``SEC-9999``) pushed the next serial to ``10000`` —
        out of the 4-digit domain. Soft-deleted projects must be excluded from
        the active high-water mark (decision C).
        """
        from datetime import datetime

        from sqlalchemy import select

        from giljo_mcp.models.projects import Project

        # Project created and then soft-deleted at 9999 in the BE bucket.
        doomed = await project_service.create_project(
            name="Doomed-9999",
            mission="m",
            description="d",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )
        doomed_row = (await db_session.execute(select(Project).where(Project.id == doomed.id))).scalar_one()
        doomed_row.series_number = 9999
        doomed_row.deleted_at = datetime.now(UTC)
        await db_session.commit()

        # Next project in the same bucket must ignore the soft-deleted 9999.
        survivor = await project_service.create_project(
            name="Survivor",
            mission="m",
            description="d",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )

        assert survivor.series_number != 10000
        # Active pool is empty (only the soft-deleted 9999 exists) → first-free is 1.
        assert survivor.series_number == 1


class TestGlobalSerialCounter:
    """BE-6049b: ONE global serial line per product, shared across ALL tags.

    Widened from the BE-5065 per-``(tenant, product, type)`` bucket. The tag
    (FE/BE/...) is decoupled from the number — every project/task in a product
    draws from a single continue-upward ``max+1`` sequence.
    """

    @pytest.mark.asyncio
    async def test_counter_is_global_across_two_tags(
        self,
        task_service: TaskService,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
        active_product: Product,
        be_taxonomy: TaxonomyType,
        fe_taxonomy: TaxonomyType,
    ):
        """A BE project then an FE project then a BE task get 1, 2, 3 — one line for all tags.

        Pre-BE-6049b these would have been BE=1, FE=1, BE-task=2 (separate per-type
        buckets). The global counter makes the number continue upward regardless of tag.
        """
        from sqlalchemy import select

        from giljo_mcp.models import Task

        be_project = await project_service.create_project(
            name="BE-P",
            mission="m",
            description="d",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )
        fe_project = await project_service.create_project(
            name="FE-P",
            mission="m",
            description="d",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=fe_taxonomy.id,
        )
        task_result = await task_service.create_task_for_mcp(
            title="BE-T",
            description="t",
            task_type="BE",
            tenant_key=test_tenant_key,
        )
        task = (await db_session.execute(select(Task).where(Task.id == task_result["task_id"]))).scalar_one()

        assert be_project.series_number == 1
        assert fe_project.series_number == 2  # continues across tag, not a fresh FE=1
        assert task.series_number == 3  # task continues the same global line

    @pytest.mark.asyncio
    async def test_project_cap_rejected_above_9999(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
        active_product: Product,
        be_taxonomy: TaxonomyType,
    ):
        """Auto-assign must reject a serial > 9999 with a clear 'serial space exhausted' error."""
        from sqlalchemy import select

        from giljo_mcp.models.projects import Project

        seed = await project_service.create_project(
            name="Seed-9999",
            mission="m",
            description="d",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )
        seed_row = (await db_session.execute(select(Project).where(Project.id == seed.id))).scalar_one()
        seed_row.series_number = 9999  # active high-water mark at the cap
        await db_session.commit()

        with pytest.raises(ValidationError, match="exhausted"):
            await project_service.create_project(
                name="Overflow",
                mission="m",
                description="d",
                product_id=active_product.id,
                tenant_key=test_tenant_key,
                project_type_id=be_taxonomy.id,
            )

    @pytest.mark.asyncio
    async def test_task_cap_rejected_above_9999(
        self,
        task_service: TaskService,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
        active_product: Product,
        be_taxonomy: TaxonomyType,
    ):
        """Task auto-assign must also reject a serial > 9999 (shares the global counter)."""
        from sqlalchemy import select

        from giljo_mcp.models.projects import Project

        seed = await project_service.create_project(
            name="Seed-9999",
            mission="m",
            description="d",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )
        seed_row = (await db_session.execute(select(Project).where(Project.id == seed.id))).scalar_one()
        seed_row.series_number = 9999
        await db_session.commit()

        with pytest.raises(ValidationError, match="exhausted"):
            await task_service.create_task_for_mcp(
                title="Overflow task",
                description="t",
                task_type="BE",
                tenant_key=test_tenant_key,
            )

    @pytest.mark.asyncio
    async def test_soft_delete_frees_and_restore_reallocates_fresh(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
        active_product: Product,
        be_taxonomy: TaxonomyType,
    ):
        """Soft-delete frees the serial; restore assigns a FRESH continue-upward number (decision C)."""
        from sqlalchemy import select

        from giljo_mcp.models.projects import Project

        first = await project_service.create_project(
            name="First",
            mission="m",
            description="d",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )
        assert first.series_number == 1

        # Soft-delete frees serial 1 from the active high-water mark.
        await project_service.deletion.delete_project(first.id)

        # A new project reclaims the freed number (active pool empty again).
        second = await project_service.create_project(
            name="Second",
            mission="m",
            description="d",
            product_id=active_product.id,
            tenant_key=test_tenant_key,
            project_type_id=be_taxonomy.id,
        )
        assert second.series_number == 1

        # Restoring the first must NOT reuse 1 — it gets a fresh continue-upward number.
        await project_service.deletion.restore_project(first.id, tenant_key=test_tenant_key)
        restored = (await db_session.execute(select(Project).where(Project.id == first.id))).scalar_one()

        assert restored.deleted_at is None
        assert restored.series_number == 2  # max+1 over active pool {second=1}
        assert restored.series_number != second.series_number
