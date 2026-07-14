# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Service-layer regression tests for BE6004C-3 (RC-2).

Bug class: dashboard services (e.g. ``ProjectSummaryService``) opened a BARE
``get_session_async()`` and resolved their tenant from
``TenantManager.get_current_tenant()``. That ambient ContextVar is unreliable
across the request -> threadpool/dependency boundary (RC-1/RC-3), so on the live
products/projects dashboard the fail-closed tenant guard saw no tenant on the
session and raised -> HTTP 500 on the confirmed ``{Project, AgentJob,
AgentExecution}`` model-set.

The fix threads an explicit ``tenant_key`` into each service ``_get_session``,
binding the session via ``tenant_session_context`` so the guard resolves tenant
from ``session.info["tenant_key"]`` instead of the ContextVar.

These tests exercise the FAILING layer -- the service, against a REAL database
session so the ``do_orm_execute`` tenant guard actually fires -- with **NO
ambient ContextVar set**. The reads succeed ONLY because the explicit key is
threaded into ``session.info``; that is the ContextVar-independence proof
(CLAUDE.md failing-layer rule).

Parallel-safe: each test runs inside ``TransactionalTestContext`` (rolled back
at teardown) and seeds a unique ``tk_...`` tenant; no module-level mutable
state; no ordering dependency. The ambient ContextVar is hard-cleared and
restored per test so a sibling xdist worker's context can never leak in.

Project: BE6004C-3 (RC-2).
"""

from __future__ import annotations

import contextlib
import logging
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models import Product, Project
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.services.agent_job_manager import AgentJobManager
from giljo_mcp.services.project_summary_service import ProjectSummaryService
from giljo_mcp.tenant import TenantManager, current_tenant


@contextlib.contextmanager
def _no_ambient_tenant():
    """Force the tenant ContextVar to None for the duration, then restore it.

    This is the crux of the RC-2 regression: the service must succeed with NO
    caller-set tenant context. We capture and restore via token so a concurrent
    xdist worker's context is never clobbered.
    """
    token = current_tenant.set(None)
    try:
        assert TenantManager.get_current_tenant() is None
        yield
    finally:
        current_tenant.reset(token)


async def _seed_project_with_agents(session: AsyncSession, tenant_key: str) -> tuple[str, str]:
    """Seed Product + Project + AgentJob + AgentExecution for one tenant.

    Touches the exact ``{Project, AgentJob, AgentExecution, Product}`` model-set
    the live dashboard 500 hit. Returns (project_id, product_id).
    """
    suffix = uuid.uuid4().hex[:8]
    product = Product(
        id=str(uuid.uuid4()),
        name=f"BE6004C-3 Product {suffix}",
        description="RC-2 regression product.",
        tenant_key=tenant_key,
        is_active=True,
        product_memory={},
    )
    session.add(product)

    project = Project(
        id=str(uuid.uuid4()),
        name=f"BE6004C-3 Project {suffix}",
        description="RC-2 regression project.",
        mission="Prove service reads are ContextVar-independent.",
        status="active",
        tenant_key=tenant_key,
        product_id=product.id,
        series_number=1,
        created_at=datetime.now(UTC),
    )
    session.add(project)

    job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        job_type="worker",
        mission="seed job",
        status="active",
        created_at=datetime.now(UTC),
        job_metadata={},
    )
    session.add(job)

    execution = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=job.job_id,
        tenant_key=tenant_key,
        agent_display_name="worker",
        agent_name="Seed Worker",
        status="complete",
        progress=100,
        tool_type="universal",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
    )
    session.add(execution)

    # Stamp tenant so the guard authorizes this SEED write; the assertion under
    # test is the SERVICE read below, which must work with no ambient context.
    session.info["tenant_key"] = tenant_key
    await session.flush()
    return project.id, product.id


@pytest.mark.asyncio
async def test_get_project_summary_succeeds_without_ambient_contextvar(db_session: AsyncSession) -> None:
    """RC-2: ProjectSummaryService.get_project_summary works with NO ambient ContextVar.

    The service is given the test session and an EXPLICIT tenant_key. Because the
    fix threads that key through ``_get_session`` -> ``tenant_session_context`` ->
    ``session.info``, the guard authorizes the {Project, AgentJob, AgentExecution,
    Product} reads without any caller-set tenant context. Pre-fix this raised
    TenantIsolationError (the live dashboard 500).
    """
    tenant_key = TenantManager.generate_tenant_key()
    project_id, _product_id = await _seed_project_with_agents(db_session, tenant_key)

    # Tenant_manager is intentionally a no-op: if the service still leaned on the
    # ambient ContextVar it would resolve to None and the guard would raise.
    tenant_manager = TenantManager()
    service = ProjectSummaryService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    with _no_ambient_tenant():
        result = await service.get_project_summary(project_id=project_id, tenant_key=tenant_key)

        # Guard never raised AND the right rows were aggregated -> proves the read
        # was authorized by session.info, not by a caller-set ContextVar.
        assert result.id == project_id
        assert result.total_jobs == 1
        assert result.completed_jobs == 1
        assert result.completion_percentage == 100.0
        assert result.product_name.startswith("BE6004C-3 Product")
        # Ambient context is still clean (no leak introduced by the read).
        assert TenantManager.get_current_tenant() is None


@pytest.mark.asyncio
async def test_list_team_agents_succeeds_without_ambient_contextvar(db_session: AsyncSession) -> None:
    """RC-2 (second touched service): AgentJobManager.list_team_agents is ContextVar-independent.

    list_team_agents is a SELECT over {AgentExecution, AgentJob}. With the explicit
    tenant threaded through ``_get_session(tenant_key)`` it succeeds with no ambient
    context; pre-fix the bare session would have left the guard contextless.
    """
    tenant_key = TenantManager.generate_tenant_key()
    project_id, _product_id = await _seed_project_with_agents(db_session, tenant_key)

    job_id = (
        (await db_session.execute(AgentJob.__table__.select().where(AgentJob.project_id == project_id))).first().job_id
    )

    manager = AgentJobManager(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        test_session=db_session,
    )

    # include_inactive=True so the seeded 'complete' execution is returned; the
    # point under test is that the guard authorizes the read from session.info,
    # not the status filter.
    with _no_ambient_tenant():
        members = await manager.list_team_agents(job_id=job_id, tenant_key=tenant_key, include_inactive=True)

    assert len(members) == 1
    assert members[0]["job_id"] == job_id
    assert members[0]["tenant_key"] == tenant_key


@pytest.mark.asyncio
async def test_get_project_summary_falls_back_to_ambient_when_key_omitted(db_session: AsyncSession) -> None:
    """Backward compatibility: omitting tenant_key falls back to the ambient context.

    Existing callers (and unit tests) that do not pass an explicit key must keep
    working via ``tenant_manager.get_current_tenant()``. This guards the optional
    parameter against becoming a silent breaking change.
    """
    tenant_key = TenantManager.generate_tenant_key()
    project_id, _product_id = await _seed_project_with_agents(db_session, tenant_key)

    class _AmbientManager(TenantManager):
        def get_current_tenant(self):  # type: ignore[override]
            return tenant_key

    service = ProjectSummaryService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=_AmbientManager(),
        test_session=db_session,
    )

    # No explicit key -> service resolves it from the (mocked) tenant manager.
    logging.getLogger(__name__).debug("fallback path: tenant from manager")
    result = await service.get_project_summary(project_id=project_id)
    assert result.id == project_id
    assert result.total_jobs == 1
