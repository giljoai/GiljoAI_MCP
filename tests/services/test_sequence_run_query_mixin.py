# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SequenceRunQueryMixin — the read/query methods extracted from SequenceRunService.

BE-6203 split the four read methods (``find_active_run_for_project``,
``find_active_run_for_conductor``, ``list_active``, ``get``) into
``SequenceRunQueryMixin`` to keep ``sequence_run_service.py`` under the 800-line
file-size guardrail. This is a PURE MOVE. This test pins that the extracted
methods still RESOLVE on ``SequenceRunService`` via inheritance and read correctly:
``get`` returns a run by id and is tenant-scoped (a wrong-tenant read raises).
The active-run filters (``list_active`` / ``find_active_run_for_project`` /
``find_active_run_for_conductor``) keep their own dedicated coverage in
test_be6200_list_active_live_members.py and test_be6184_dedicated_conductor.py.

Parallel-safety: DB-touching; uses the db_session fixture (TransactionalTestContext).
SequenceRunService.create COMMITs through the injected session, so a function-scoped
collector wipes only the tenant_keys this test created — no module-level mutable state.
"""

from __future__ import annotations

import random
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.models.sequence_runs import SequenceRun
from giljo_mcp.services.sequence_run_service import SequenceRunService
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio

_MODE = "claude_code_cli"


@pytest_asyncio.fixture
async def cleanup_tenants(db_manager):
    """Collect tenant_keys created by a test; delete their rows at teardown
    (create COMMITs through the injected session, so rows outlive the txn)."""
    tenants: list[str] = []
    yield tenants
    for tk in tenants:
        async with db_manager.get_session_async(tenant_key=tk) as session:
            await session.execute(delete(AgentExecution).where(AgentExecution.tenant_key == tk))
            await session.execute(delete(AgentJob).where(AgentJob.tenant_key == tk))
            await session.execute(delete(SequenceRun).where(SequenceRun.tenant_key == tk))
            await session.execute(delete(Project).where(Project.tenant_key == tk))
            await session.execute(delete(Product).where(Product.tenant_key == tk))
            await session.commit()


def _seq_svc(session: AsyncSession) -> SequenceRunService:
    return SequenceRunService(db_manager=None, tenant_manager=None, session=session)


async def _create_product(session: AsyncSession, tenant_key: str) -> str:
    product_id = str(uuid.uuid4())
    session.add(Product(id=product_id, tenant_key=tenant_key, name="Query Mixin Test Product"))
    await session.commit()
    return product_id


async def _create_project(session: AsyncSession, tenant_key: str, product_id: str) -> str:
    project_id = str(uuid.uuid4())
    session.add(
        Project(
            id=project_id,
            product_id=product_id,
            name="Query Mixin Test Project",
            description="query mixin regression",
            mission="query mixin regression mission",
            status="completed",
            tenant_key=tenant_key,
            execution_mode="multi_terminal",
            series_number=random.randint(1, 9000),
        )
    )
    await session.commit()
    return project_id


async def _create_run(session: AsyncSession, tenant_key: str, project_ids: list[str]) -> dict:
    return await _seq_svc(session).create(
        project_ids=project_ids,
        resolved_order=project_ids,
        execution_mode=_MODE,
        status="running",
        project_statuses=dict.fromkeys(project_ids, "completed"),
        tenant_key=tenant_key,
    )


async def test_get_resolves_via_mixin_and_is_tenant_scoped(
    db_session: AsyncSession, cleanup_tenants: list[str]
) -> None:
    """get() (extracted to SequenceRunQueryMixin) still resolves on SequenceRunService
    via inheritance, returns the run by id, and is tenant-scoped: a wrong-tenant read
    raises ResourceNotFoundError."""
    tenant = TenantManager.generate_tenant_key()
    cleanup_tenants.append(tenant)

    product_id = await _create_product(db_session, tenant)
    p1 = await _create_project(db_session, tenant, product_id)
    p2 = await _create_project(db_session, tenant, product_id)
    run = await _create_run(db_session, tenant, [p1, p2])
    run_id = run["id"]
    svc = _seq_svc(db_session)

    # Resolves for the owning tenant (the extracted method is reachable on the service).
    got = await svc.get(run_id=run_id, tenant_key=tenant)
    assert got["id"] == run_id

    # Tenant-scoped: another tenant cannot read the same run.
    other_tenant = TenantManager.generate_tenant_key()
    with pytest.raises(ResourceNotFoundError):
        await svc.get(run_id=run_id, tenant_key=other_tenant)


async def _set_run(session: AsyncSession, run_id: str, **values) -> None:
    """Directly patch a run row (test setup for terminal-status / review states)."""
    await session.execute(update(SequenceRun).where(SequenceRun.id == run_id).values(**values))
    await session.commit()


async def test_list_review_pending_surfaces_terminal_unreviewed_and_excludes_active(
    db_session: AsyncSession, cleanup_tenants: list[str]
) -> None:
    """FE-9104: list_review_pending returns TERMINAL runs with a completed-but-unreviewed
    member, excludes still-active runs, and is tenant-scoped."""
    tenant = TenantManager.generate_tenant_key()
    cleanup_tenants.append(tenant)

    product_id = await _create_product(db_session, tenant)
    p1 = await _create_project(db_session, tenant, product_id)
    p2 = await _create_project(db_session, tenant, product_id)

    # An active (running) run — must NOT appear in the review-pending listing.
    active = await _seq_svc(db_session).create(
        project_ids=[p1],
        resolved_order=[p1],
        execution_mode=_MODE,
        status="running",
        project_statuses={p1: "completed"},
        tenant_key=tenant,
    )
    # A terminal run whose members completed but were never reviewed.
    term = await _create_run(db_session, tenant, [p1, p2])
    await _set_run(db_session, term["id"], status="completed")

    svc = _seq_svc(db_session)
    pending = await svc.list_review_pending(tenant_key=tenant)
    ids = [r["id"] for r in pending]

    assert term["id"] in ids  # terminal + unreviewed → reachable
    assert active["id"] not in ids  # active runs are excluded (terminal-only source)

    # Tenant-scoped: another tenant sees none of these runs.
    other_tenant = TenantManager.generate_tenant_key()
    assert await svc.list_review_pending(tenant_key=other_tenant) == []


async def test_list_review_pending_drops_fully_reviewed_run(
    db_session: AsyncSession, cleanup_tenants: list[str]
) -> None:
    """FE-9104 release semantics: once every completed member is reviewed, the run no
    longer surfaces — the Jobs review link releases with no infinite bounce."""
    tenant = TenantManager.generate_tenant_key()
    cleanup_tenants.append(tenant)

    product_id = await _create_product(db_session, tenant)
    p1 = await _create_project(db_session, tenant, product_id)
    p2 = await _create_project(db_session, tenant, product_id)

    term = await _create_run(db_session, tenant, [p1, p2])
    svc = _seq_svc(db_session)

    # Terminal, no reviews yet → surfaces.
    await _set_run(db_session, term["id"], status="completed")
    assert [r["id"] for r in await svc.list_review_pending(tenant_key=tenant)] == [term["id"]]

    # All completed members reviewed → drops out (released).
    await _set_run(db_session, term["id"], reviewed_project_ids=[p1, p2])
    assert await svc.list_review_pending(tenant_key=tenant) == []
