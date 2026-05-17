# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression tests for project_helpers.spawn_implementation_orchestrator (CE-0028c).

Covers:
  a. Spawn when staging exec is complete + no impl exec exists yet.
  b. Idempotent: second call returns existing impl exec, does NOT spawn another.
  c. No-op (returns None) when the project has no orchestrator at all.
  d. Returns existing latest exec when staging hasn't reached complete yet
     (defensive — shouldn't be reachable from the UI flow but the helper is
     safe to call regardless).
  e. Tenant isolation: helper does not touch other tenants' executions.

Helper contract:
  - Only flushes (does not commit) so callers can batch with their own writes.
  - Returns the impl AgentExecution (existing or new), or None.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.services.project_helpers import spawn_implementation_orchestrator


# ============================================================================
# Fixtures + seed helpers
# ============================================================================


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="CE-0028c Helper Test Product",
        description="Product for CE-0028c helper tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


async def _seed_project(
    db_session: AsyncSession,
    tenant_key: str,
    product_id: str,
    *,
    staging_status: str | None = "staging_complete",
) -> Project:
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product_id,
        name="CE-0028c Helper Project",
        description="Project for CE-0028c helper tests",
        mission="Staging-end spawn test",
        status="active",
        staging_status=staging_status,
        created_at=datetime.now(UTC),
        series_number=random.randint(1, 999_999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


async def _seed_orchestrator(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: str,
    *,
    exec_status: str = "complete",
    project_phase: str = "staging",
) -> tuple[AgentJob, AgentExecution]:
    job_id = str(uuid4())
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        job_type="orchestrator",
        mission="CE-0028c helper test orchestrator",
        status="active",
    )
    db_session.add(job)

    now = datetime.now(UTC)
    execution = AgentExecution(
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        status=exec_status,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=now - timedelta(minutes=5),
        completed_at=now if exec_status == "complete" else None,
        project_phase=project_phase,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)
    return job, execution


async def _count_impl_execs(db_session: AsyncSession, tenant_key: str, job_id: str) -> int:
    stmt = select(AgentExecution).where(
        AgentExecution.tenant_key == tenant_key,
        AgentExecution.job_id == job_id,
        AgentExecution.project_phase == "implementation",
    )
    return len(list((await db_session.execute(stmt)).scalars().all()))


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_spawn_when_staging_complete_and_no_impl_exec(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
):
    """(a) The canonical happy path: staging exec is 'complete' and no
    impl exec exists. Helper spawns a fresh impl exec attached to the same
    job, returns it. The caller must commit (helper only flushes).
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    job, _ = await _seed_orchestrator(
        db_session, test_tenant_key, project.id, exec_status="complete", project_phase="staging"
    )

    impl = await spawn_implementation_orchestrator(db_session, project.id, test_tenant_key)
    await db_session.commit()

    assert impl is not None, "helper must return the newly-spawned impl exec"
    assert impl.project_phase == "implementation"
    assert impl.status == "waiting"
    assert impl.job_id == job.job_id, "impl exec must attach to the same AgentJob"
    assert impl.agent_display_name == "orchestrator"

    count = await _count_impl_execs(db_session, test_tenant_key, job.job_id)
    assert count == 1, f"expected exactly 1 impl exec after first spawn, got {count}"


@pytest.mark.asyncio
async def test_idempotent_second_call_returns_same_exec(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
):
    """(b) Helper is idempotent. Calling it twice returns the same impl exec
    and does NOT spawn a second one. Critical for the launch_implementation
    endpoint's already-launched code path which calls the helper to re-assert
    spawn (in case a prior call set the timestamp but the spawn didn't land).
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    job, _ = await _seed_orchestrator(
        db_session, test_tenant_key, project.id, exec_status="complete", project_phase="staging"
    )

    first = await spawn_implementation_orchestrator(db_session, project.id, test_tenant_key)
    await db_session.commit()

    second = await spawn_implementation_orchestrator(db_session, project.id, test_tenant_key)
    await db_session.commit()

    assert first is not None
    assert second is not None
    assert first.agent_id == second.agent_id, "idempotent: must return the same impl exec on second call"

    count = await _count_impl_execs(db_session, test_tenant_key, job.job_id)
    assert count == 1, f"idempotent: must not spawn a second impl exec; got {count}"


@pytest.mark.asyncio
async def test_no_orchestrator_returns_none(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
):
    """(c) Defensive: if the project has no orchestrator job at all, the
    helper returns None and writes nothing. Caller treats as a hard error.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    # No orchestrator seeded.

    impl = await spawn_implementation_orchestrator(db_session, project.id, test_tenant_key)
    await db_session.commit()

    assert impl is None, "no orchestrator -> helper returns None"


@pytest.mark.asyncio
async def test_staging_still_working_returns_existing_exec(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
):
    """(d) Defensive: if the staging exec is still 'working' (no complete
    staging exec exists), the helper returns the existing exec rather than
    spawning. The Implement-button flow shouldn't be reachable in this state
    but the helper stays safe to call.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, working_exec = await _seed_orchestrator(
        db_session, test_tenant_key, project.id, exec_status="working", project_phase="staging"
    )

    result = await spawn_implementation_orchestrator(db_session, project.id, test_tenant_key)
    await db_session.commit()

    assert result is not None
    assert result.agent_id == working_exec.agent_id, "should return the existing working exec, not spawn a new one"

    count = await _count_impl_execs(db_session, test_tenant_key, job.job_id)
    assert count == 0, "no impl exec should be spawned when staging is still in flight"


@pytest.mark.asyncio
async def test_tenant_isolation(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
):
    """(e) Tenant isolation: a project that belongs to a different tenant
    is invisible to the helper. Returns None, no cross-tenant exec touched.
    """
    other_tenant = "tk_other_tenant_for_isolation_test"

    other_product = Product(
        id=str(uuid4()),
        tenant_key=other_tenant,
        name="other tenant product",
        description="other",
        product_memory={},
    )
    db_session.add(other_product)
    await db_session.commit()

    project = await _seed_project(db_session, other_tenant, other_product.id, staging_status="staging_complete")
    await _seed_orchestrator(db_session, other_tenant, project.id, exec_status="complete", project_phase="staging")

    # Call with the wrong tenant_key — helper should not find the orchestrator.
    impl = await spawn_implementation_orchestrator(db_session, project.id, test_tenant_key)
    await db_session.commit()

    assert impl is None, "cross-tenant lookup must return None"
