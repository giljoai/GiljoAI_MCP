# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""IMP-6262: Task → Project conversion STRIPS the taxonomy type.

``TSK`` is task-exclusive: converting a task must NOT copy its type onto the new
project (that would mint a TSK-typed project and reopen the task/project alias
ambiguity). The converted project is born UNTYPED (``project_type_id IS NULL``),
keeping the task's title + serial as its identity; the user re-tags it later.

The task's ``series_number`` is preserved (the task row is hard-deleted on
conversion, freeing that product-unique number). A serial-less task still gets a
fresh number under the (tenant, product, NULL) bucket so the project satisfies
``uq_project_taxonomy_active`` (NULLS NOT DISTINCT).

(Supersedes BE-5065, which copied ``project_type_id`` + ``series_number`` across.)
"""

from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select

from giljo_mcp.models import Project, Task, User
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import TaxonomyType
from giljo_mcp.services.task_conversion_service import TaskConversionService


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
async def conversion_service(db_manager, db_session, test_tenant_key):
    from giljo_mcp.tenant import TenantManager

    tm = TenantManager()
    tm.set_current_tenant(test_tenant_key)
    return TaskConversionService(db_manager=db_manager, tenant_manager=tm, session=db_session)


async def _admin(db_session, tenant_key: str) -> User:
    u = User(
        id=str(uuid4()),
        tenant_key=tenant_key,
        username=f"u_{uuid4().hex[:8]}",
        email=f"{uuid4().hex[:8]}@test.local",
        role="admin",
    )
    db_session.add(u)
    await db_session.commit()
    await db_session.refresh(u)
    return u


async def _active_product(db_session, tenant_key: str) -> Product:
    p = Product(
        id=str(uuid4()),
        name=f"P {uuid4().hex[:6]}",
        description="conv test product",
        tenant_key=tenant_key,
        is_active=True,
    )
    db_session.add(p)
    await db_session.commit()
    await db_session.refresh(p)
    return p


class TestTaskConversionInheritance:
    @pytest.mark.asyncio
    async def test_typed_task_converts_to_untyped_project(
        self,
        conversion_service: TaskConversionService,
        db_session,
        test_tenant_key: str,
        be_taxonomy: TaxonomyType,
    ):
        """IMP-6262: a typed task converts to an UNTYPED project — the type is
        STRIPPED (not copied), the serial + title are kept. TSK is task-exclusive,
        so no conversion ever stamps a taxonomy onto the project; the user tags it
        later in the dashboard."""
        user = await _admin(db_session, test_tenant_key)
        product = await _active_product(db_session, test_tenant_key)

        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=product.id,
            title="BE-0017 task",
            description="typed task ready for conversion",
            status="pending",
            priority="medium",
            created_by_user_id=user.id,
            task_type_id=be_taxonomy.id,
            series_number=17,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = await conversion_service.convert_to_project(
            task_id=task.id,
            project_name=None,
            strategy="single",
            include_subtasks=False,
            user_id=user.id,
        )

        project = (await db_session.execute(select(Project).where(Project.id == result.project_id))).scalar_one()
        # Type is STRIPPED — NOT copied from the task's BE type.
        assert project.project_type_id is None
        # Serial + title are preserved as the untyped project's identity.
        assert project.series_number == 17
        assert project.name == "BE-0017 task"

    @pytest.mark.asyncio
    async def test_untyped_task_falls_back_to_fresh_number(
        self,
        conversion_service: TaskConversionService,
        db_session,
        test_tenant_key: str,
    ):
        user = await _admin(db_session, test_tenant_key)
        product = await _active_product(db_session, test_tenant_key)

        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=product.id,
            title="untyped",
            description="legacy task without task_type_id",
            status="pending",
            priority="medium",
            created_by_user_id=user.id,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = await conversion_service.convert_to_project(
            task_id=task.id,
            project_name=None,
            strategy="single",
            include_subtasks=False,
            user_id=user.id,
        )

        project = (await db_session.execute(select(Project).where(Project.id == result.project_id))).scalar_one()
        assert project.project_type_id is None
        assert project.series_number is not None
        assert project.series_number >= 1

    @pytest.mark.asyncio
    async def test_converted_project_has_null_execution_mode(
        self,
        conversion_service: TaskConversionService,
        db_session,
        test_tenant_key: str,
    ):
        """The ORIGINAL incident: a task converted to a project must be born with
        NO execution mode (NULL = not yet chosen), never silently stamped
        'multi_terminal'. The conversion path does not set execution_mode, and the
        column now has no default, so the user must pick a mode in the dashboard
        before staging."""
        user = await _admin(db_session, test_tenant_key)
        product = await _active_product(db_session, test_tenant_key)

        task = Task(
            id=str(uuid4()),
            tenant_key=test_tenant_key,
            product_id=product.id,
            title="mode-less task",
            description="task converted to a project should have no execution mode",
            status="pending",
            priority="medium",
            created_by_user_id=user.id,
        )
        db_session.add(task)
        await db_session.commit()
        await db_session.refresh(task)

        result = await conversion_service.convert_to_project(
            task_id=task.id,
            project_name=None,
            strategy="single",
            include_subtasks=False,
            user_id=user.id,
        )

        project = (await db_session.execute(select(Project).where(Project.id == result.project_id))).scalar_one()
        assert project.execution_mode is None, (
            "task->project conversion must NOT stamp an execution mode (this is the original silent-multi_terminal bug)"
        )
