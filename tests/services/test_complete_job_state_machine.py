# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Regression tests for CE-0026: JobCompletionService._handle_staging_end
state-machine branch.

Five focused behaviors:
  a. Staging-end orchestrator returns STOP directive and flips staging_status.
  b. Idempotent: already-flipped project still returns the directive.
  c. Implementation-phase orchestrator: no directive.
  d. Non-orchestrator job type: no directive even on staging-phase project.
  e. mark_staging_complete is called exactly once per staging-end complete_job.
"""

from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob, AgentTodoItem
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.services.job_completion_service import JobCompletionService


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
async def test_product(db_session: AsyncSession, test_tenant_key: str) -> Product:
    product = Product(
        id=str(uuid4()),
        tenant_key=test_tenant_key,
        name="CE-0026 State Machine Product",
        description="Product for CE-0026 state machine tests",
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest.fixture
def completion_service(db_session: AsyncSession, test_tenant_key: str) -> JobCompletionService:
    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    return JobCompletionService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )


async def _seed_orchestrator_job(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: str,
    *,
    project_phase: str = "staging",
) -> tuple[AgentJob, AgentExecution]:
    """Seed an orchestrator AgentJob + working AgentExecution."""
    job_id = str(uuid4())
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        job_type="orchestrator",
        mission="CE-0026 staging orchestrator",
        status="active",
    )
    db_session.add(job)

    now = datetime.now(UTC)
    execution = AgentExecution(
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=now - timedelta(minutes=5),
        project_phase=project_phase,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)
    return job, execution


async def _seed_deliverable_job(
    db_session: AsyncSession,
    tenant_key: str,
    project_id: str,
    *,
    job_type: str = "implementer",
    project_phase: str = "staging",
) -> tuple[AgentJob, AgentExecution]:
    """Seed a non-orchestrator AgentJob + working AgentExecution."""
    job_id = str(uuid4())
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        job_type=job_type,
        mission="CE-0026 deliverable agent",
        status="active",
    )
    db_session.add(job)

    now = datetime.now(UTC)
    execution = AgentExecution(
        job_id=job_id,
        tenant_key=tenant_key,
        agent_display_name=job_type,
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=now - timedelta(minutes=3),
        project_phase=project_phase,
    )
    db_session.add(execution)
    await db_session.commit()
    await db_session.refresh(job)
    await db_session.refresh(execution)
    return job, execution


async def _seed_project(
    db_session: AsyncSession,
    tenant_key: str,
    product_id: str,
    *,
    staging_status: str | None = "staging",
) -> Project:
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        product_id=product_id,
        name="CE-0026 Test Project",
        description="Project for CE-0026 state machine tests",
        mission="Staging state machine test",
        status="active",
        staging_status=staging_status,
        created_at=datetime.now(UTC),
        series_number=random.randint(1, 999_999),
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


# ============================================================================
# Tests
# ============================================================================


@pytest.mark.asyncio
async def test_staging_end_orchestrator_returns_stop_directive_and_flips_status(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """(a) Staging-phase orchestrator complete_job returns STOP directive and
    flips project.staging_status to 'staging_complete'.

    CE-0026: the _handle_staging_end branch triggers when:
      - job.job_type == 'orchestrator'
      - execution.project_phase == 'staging'
      - project.staging_status != 'staging_complete' (flip needed)
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="staging")

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Staging session complete"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success"
    assert result.staging_directive is not None, "CE-0026: staging-phase orchestrator must return a staging_directive"
    assert result.staging_directive.action == "STOP", f"Expected action=STOP, got {result.staging_directive.action!r}"
    assert result.staging_directive.status == "STAGING_SESSION_COMPLETE", (
        f"Expected status=STAGING_SESSION_COMPLETE, got {result.staging_directive.status!r}"
    )

    refreshed = (
        await db_session.execute(select(Project).where(Project.id == project.id, Project.tenant_key == test_tenant_key))
    ).scalar_one()
    assert refreshed.staging_status == "staging_complete", (
        f"CE-0026: staging_status must be flipped to 'staging_complete', got {refreshed.staging_status!r}"
    )


@pytest.mark.asyncio
async def test_staging_end_already_flipped_still_returns_directive(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """(b) Idempotent: if project.staging_status is already 'staging_complete',
    complete_job still returns the STOP directive (the orchestrator still needs
    the signal even though mark_staging_complete was a no-op).

    CE-0026: mark_staging_complete returns False when already complete, but
    _handle_staging_end still returns StagingDirective() regardless.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="staging")

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Staging already complete — idempotent path"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success"
    assert result.staging_directive is not None, "CE-0026: idempotent staging-end must still return a staging_directive"
    assert result.staging_directive.action == "STOP"

    # staging_status must remain unchanged (not re-flipped).
    refreshed = (
        await db_session.execute(select(Project).where(Project.id == project.id, Project.tenant_key == test_tenant_key))
    ).scalar_one()
    assert refreshed.staging_status == "staging_complete"


@pytest.mark.asyncio
async def test_implementation_phase_orchestrator_no_directive(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """(c) Implementation-phase orchestrator: complete_job returns no
    staging_directive and normal closeout_checklist behavior is unchanged.

    CE-0026: _handle_staging_end returns None when project_phase='implementation'.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="implementation")

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Implementation complete"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success"
    assert result.staging_directive is None, (
        "CE-0026: implementation-phase orchestrator must NOT return a staging_directive"
    )
    # Closeout checklist is still built for orchestrators (INF-5076 regression guard).
    assert result.closeout_checklist is not None, (
        "closeout_checklist must still be populated for orchestrator complete_job"
    )


@pytest.mark.asyncio
async def test_deliverable_agent_no_directive_even_on_staging_phase_project(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """(d) Non-orchestrator job type: complete_job returns no staging_directive
    regardless of the project's staging_status.

    CE-0026: _handle_staging_end returns None immediately when
    job.job_type != 'orchestrator'.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, _ = await _seed_deliverable_job(
        db_session,
        test_tenant_key,
        project.id,
        job_type="implementer",
        project_phase="staging",
    )

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Implementer done"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success"
    assert result.staging_directive is None, "CE-0026: non-orchestrator job must never return a staging_directive"
    # project staging_status must not have been touched by this non-orch complete.
    refreshed = (
        await db_session.execute(select(Project).where(Project.id == project.id, Project.tenant_key == test_tenant_key))
    ).scalar_one()
    assert refreshed.staging_status == "staging", "Non-orchestrator complete_job must not alter project.staging_status"


@pytest.mark.asyncio
async def test_mark_staging_complete_called_exactly_once_on_staging_end(
    db_session: AsyncSession,
    test_tenant_key: str,
    test_product: Product,
):
    """(e) mark_staging_complete is invoked exactly once, with
    source='complete_job:staging_end', during a staging-end complete_job.

    Uses unittest.mock.patch on the helper at the job_completion_service
    import site so the patched version is what the service calls.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="staging")

    db_manager = MagicMock()
    tenant_manager = MagicMock()
    tenant_manager.get_current_tenant.return_value = test_tenant_key
    svc = JobCompletionService(
        db_manager=db_manager,
        tenant_manager=tenant_manager,
        test_session=db_session,
    )

    with patch(
        "giljo_mcp.services.job_completion_service.mark_staging_complete",
        new_callable=AsyncMock,
        return_value=True,
    ) as mock_msc:
        await svc.complete_job(
            job_id=job.job_id,
            result={"summary": "Staging end — mock test"},
            tenant_key=test_tenant_key,
        )

    mock_msc.assert_called_once()
    _, kwargs = mock_msc.call_args
    assert kwargs.get("source") == "complete_job:staging_end", (
        f"CE-0026: mark_staging_complete must be called with source='complete_job:staging_end', "
        f"got source={kwargs.get('source')!r}"
    )


# ============================================================================
# CE-0027 regression tests — phase-aware gate + phase-aware closeout_checklist
# ============================================================================


async def _seed_incomplete_todos(
    db_session: AsyncSession,
    tenant_key: str,
    job_id: str,
    count: int = 3,
) -> list[AgentTodoItem]:
    """Seed `count` pending TODO items for a job — simulates deliverable plan."""
    todos: list[AgentTodoItem] = []
    for i in range(count):
        todo = AgentTodoItem(
            job_id=job_id,
            tenant_key=tenant_key,
            content=f"CE-0027 deliverable item {i + 1}",
            status="pending",
            sequence=i,
        )
        db_session.add(todo)
        todos.append(todo)
    await db_session.commit()
    return todos


@pytest.mark.asyncio
async def test_staging_orchestrator_complete_job_bypasses_incomplete_todos_gate(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0027 (f): staging-phase orchestrator's complete_job must NOT be
    blocked by incomplete TODOs.

    Reason: the orchestrator protocol instructs the staging orch to write
    deliverable-shaped TODOs (e.g., "Build PaddleService") that are meant to
    survive into implementation. The pre-CE-0027 gate blocked staging-close
    on these, forcing the agent to lie about completion status. CE-0027
    makes the gate phase-aware.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="staging")
    await _seed_incomplete_todos(db_session, test_tenant_key, job.job_id, count=3)

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Staging done; 3 deliverable TODOs survive into impl"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success", "CE-0027: staging orch must close successfully despite incomplete TODOs"
    assert result.staging_directive is not None, "CE-0027: staging close should still return STOP directive"
    assert result.staging_directive.action == "STOP"


@pytest.mark.asyncio
async def test_implementation_orchestrator_complete_job_still_blocks_on_incomplete_todos(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0027 (f) regression: implementation-phase orchestrator with
    incomplete TODOs MUST still be blocked (the gate's original purpose —
    preventing premature closure — still applies in impl phase).
    """
    from giljo_mcp.exceptions import ValidationError

    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="implementation")
    await _seed_incomplete_todos(db_session, test_tenant_key, job.job_id, count=2)

    with pytest.raises(ValidationError) as exc_info:
        await completion_service.complete_job(
            job_id=job.job_id,
            result={"summary": "Tried to close impl with incomplete TODOs"},
            tenant_key=test_tenant_key,
        )

    assert "COMPLETION_BLOCKED" in str(exc_info.value), (
        f"CE-0027 regression: impl orch with incomplete TODOs must still raise COMPLETION_BLOCKED, "
        f"got: {exc_info.value!r}"
    )


@pytest.mark.asyncio
async def test_deliverable_agent_still_blocks_on_incomplete_todos(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0027 (f) regression: non-orchestrator agents (implementer, tester,
    etc.) MUST still be blocked by incomplete TODOs regardless of phase.
    The phase-aware bypass applies only to orchestrators.
    """
    from giljo_mcp.exceptions import ValidationError

    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    job, _ = await _seed_deliverable_job(
        db_session, test_tenant_key, project.id, job_type="implementer", project_phase="staging"
    )
    await _seed_incomplete_todos(db_session, test_tenant_key, job.job_id, count=2)

    with pytest.raises(ValidationError) as exc_info:
        await completion_service.complete_job(
            job_id=job.job_id,
            result={"summary": "Implementer trying to close with pending work"},
            tenant_key=test_tenant_key,
        )

    assert "COMPLETION_BLOCKED" in str(exc_info.value), (
        "CE-0027 regression: implementer agent must still be blocked on incomplete TODOs"
    )


@pytest.mark.asyncio
async def test_staging_orchestrator_response_has_no_closeout_checklist(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0027 (g): staging-phase orchestrator's complete_job response must
    NOT include closeout_checklist. The checklist content (request_approval,
    deferred findings) is impl-phase guidance and confused the staging agent
    on the dogfood Paddle test.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="staging")

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Staging close — should not get impl-phase checklist"},
        tenant_key=test_tenant_key,
    )

    assert result.staging_directive is not None
    assert result.closeout_checklist is None, (
        f"CE-0027: staging orch response must not carry closeout_checklist, got {result.closeout_checklist!r}"
    )


@pytest.mark.asyncio
async def test_implementation_orchestrator_response_has_closeout_checklist(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0027 (g) regression: impl-phase orchestrator's response STILL
    includes closeout_checklist (impl-phase guidance is preserved for the
    audience it's actually for).
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="implementation")

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Impl close — should still get checklist"},
        tenant_key=test_tenant_key,
    )

    assert result.staging_directive is None, "Impl orch should not get staging_directive"
    assert result.closeout_checklist is not None, (
        "CE-0027 regression: impl orch response must still carry closeout_checklist"
    )
    assert "instruction" in result.closeout_checklist or "follow_up_items" in result.closeout_checklist
