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
from giljo_mcp.services.project_helpers import spawn_implementation_orchestrator


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


@pytest.mark.asyncio
async def test_staging_orchestrator_complete_job_leaves_job_status_active(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0028 (h): the staging→implementation transition must preserve
    ``AgentJob.status='active'``.

    The orchestrator AgentJob is long-lived across both phases — the
    implementation execution re-attaches to the same job_id (CE-0026
    ``_spawn_implementation_execution``). Flipping job.status='completed' at
    staging-end made the UI treat the project as fully done (CloseoutModal +
    360-memory poll) and blocked the Implement (play) button flow.

    The staging-phase AgentExecution itself still marks complete (it IS
    finished as a session); only the parent job status is preserved.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="staging")

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Staging end — should NOT flip job.status"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success"
    assert result.staging_directive is not None and result.staging_directive.action == "STOP"

    refreshed_job = (await db_session.execute(select(AgentJob).where(AgentJob.job_id == job.job_id))).scalar_one()
    assert refreshed_job.status == "active", (
        f"CE-0028: staging-end must leave job.status='active', got {refreshed_job.status!r}"
    )
    assert refreshed_job.completed_at is None, (
        f"CE-0028: staging-end must leave job.completed_at unset, got {refreshed_job.completed_at!r}"
    )

    # CE-0029 Item 2: there are now TWO execs on this job — the historical
    # staging exec (complete) and the newly pre-spawned impl exec (waiting).
    # Filter by phase to assert each independently.
    refreshed_execs = list(
        (await db_session.execute(select(AgentExecution).where(AgentExecution.job_id == job.job_id))).scalars().all()
    )
    by_phase = {e.project_phase: e for e in refreshed_execs}
    assert by_phase["staging"].status == "complete", (
        "Staging execution must still mark itself complete — only the parent job is preserved"
    )
    assert by_phase["implementation"].status == "waiting", (
        "CE-0029 Item 2: pre-spawned impl exec must be 'waiting' immediately at staging-end"
    )


# ============================================================================
# CE-0029 Item 2 regression tests — pre-spawn impl exec at staging-end
# ============================================================================


@pytest.mark.asyncio
async def test_staging_end_prespawns_impl_exec(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0029 Item 2: after a successful staging-end complete_job, exactly
    one waiting impl-phase orchestrator execution exists alongside the
    now-complete staging execution.

    Both execs attach to the same AgentJob (orchestrator job survives the
    phase boundary, per CE-0028 ``job.status='active'`` preservation).
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="staging")

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Staging end — pre-spawn impl exec"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success"
    assert result.staging_directive is not None
    assert result.staging_directive.action == "STOP"

    # Two executions on the same job: the historical staging exec (complete)
    # and the freshly-spawned impl exec (waiting).
    execs = list(
        (
            await db_session.execute(
                select(AgentExecution).where(
                    AgentExecution.job_id == job.job_id,
                    AgentExecution.tenant_key == test_tenant_key,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(execs) == 2, f"Expected 2 execs on job {job.job_id}, got {len(execs)}: {[e.status for e in execs]}"

    by_phase = {e.project_phase: e for e in execs}
    assert "staging" in by_phase and "implementation" in by_phase, (
        f"Expected one staging + one implementation exec, got phases: {[e.project_phase for e in execs]}"
    )
    assert by_phase["staging"].status == "complete", (
        f"Staging exec must be 'complete', got {by_phase['staging'].status!r}"
    )
    assert by_phase["implementation"].status == "waiting", (
        f"Impl exec must be 'waiting', got {by_phase['implementation'].status!r}"
    )
    # Both share the AgentJob.
    assert by_phase["implementation"].job_id == job.job_id
    assert by_phase["staging"].job_id == job.job_id


@pytest.mark.asyncio
async def test_staging_end_prespawn_is_idempotent(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0029 Item 2: a second staging-end complete_job (defensive — should
    not happen in practice) does NOT create a second impl exec. The helper's
    Branch 1 detects the existing waiting impl exec and returns it.

    The second call also exits the staging-end branch via the
    ``project.implementation_launched_at`` safeguard if the test set it; we
    don't set that here — the second call lands in _handle_staging_end again
    and the helper's idempotency carries the test.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="staging")

    # First staging-end call — spawns the impl exec.
    await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "First staging-end"},
        tenant_key=test_tenant_key,
    )

    impl_after_first = list(
        (
            await db_session.execute(
                select(AgentExecution).where(
                    AgentExecution.job_id == job.job_id,
                    AgentExecution.tenant_key == test_tenant_key,
                    AgentExecution.project_phase == "implementation",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(impl_after_first) == 1, f"After first staging-end, expected 1 impl exec, got {len(impl_after_first)}"

    # Re-fire the helper directly (the second complete_job would 404 because
    # the staging exec is now terminal). Call spawn directly to assert
    # idempotency in the same way _handle_staging_end would call it.
    second = await spawn_implementation_orchestrator(db_session, str(project.id), test_tenant_key)
    await db_session.commit()

    # Existing waiting impl exec returned, no second spawn.
    assert second is not None
    assert second.agent_id == impl_after_first[0].agent_id

    impl_after_second = list(
        (
            await db_session.execute(
                select(AgentExecution).where(
                    AgentExecution.job_id == job.job_id,
                    AgentExecution.tenant_key == test_tenant_key,
                    AgentExecution.project_phase == "implementation",
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(impl_after_second) == 1, (
        f"After idempotent re-spawn, expected still 1 impl exec, got {len(impl_after_second)}"
    )


@pytest.mark.asyncio
async def test_implementation_end_does_not_prespawn(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0029 Item 2 negative case: an impl-phase orchestrator's complete_job
    must NOT spawn another orchestrator execution. The pre-spawn fires only
    at the staging-end branch.

    Seeds two execs on the same job (matching the post-CE-0029-Item-2 state):
    staging (complete) + implementation (working). Completing the impl exec
    must leave the count at 2 — no third orch exec.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    # Mark the project as having launched implementation so the
    # _is_staging_end_orchestrator_call safeguard treats the impl exec as
    # impl-phase regardless of the project_phase column.
    project.implementation_launched_at = datetime.now(UTC)
    await db_session.commit()
    await db_session.refresh(project)

    # Historical staging exec (complete) on the orchestrator job.
    staging_job_id = str(uuid4())
    staging_job = AgentJob(
        job_id=staging_job_id,
        tenant_key=test_tenant_key,
        project_id=project.id,
        job_type="orchestrator",
        mission="CE-0029 staging history",
        status="active",
    )
    db_session.add(staging_job)
    staging_exec = AgentExecution(
        job_id=staging_job_id,
        tenant_key=test_tenant_key,
        agent_display_name="orchestrator",
        status="complete",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=datetime.now(UTC) - timedelta(minutes=10),
        completed_at=datetime.now(UTC) - timedelta(minutes=5),
        project_phase="staging",
    )
    db_session.add(staging_exec)

    # Active impl exec on the SAME job.
    impl_exec = AgentExecution(
        job_id=staging_job_id,
        tenant_key=test_tenant_key,
        agent_display_name="orchestrator",
        status="working",
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
        started_at=datetime.now(UTC) - timedelta(minutes=2),
        project_phase="implementation",
    )
    db_session.add(impl_exec)
    await db_session.commit()

    result = await completion_service.complete_job(
        job_id=staging_job_id,
        result={"summary": "Impl-phase close — must not spawn another orch"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success"
    assert result.staging_directive is None, "Impl-phase complete_job must NOT return a staging_directive"

    # Still exactly 2 execs on the job: no extra spawn.
    execs = list(
        (
            await db_session.execute(
                select(AgentExecution).where(
                    AgentExecution.job_id == staging_job_id,
                    AgentExecution.tenant_key == test_tenant_key,
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(execs) == 2, (
        f"Impl-phase close must NOT create a new orch exec — expected 2, got {len(execs)} "
        f"(statuses: {[e.status for e in execs]}, phases: {[e.project_phase for e in execs]})"
    )


@pytest.mark.asyncio
async def test_implementation_orchestrator_complete_job_marks_job_completed(
    db_session: AsyncSession,
    completion_service: JobCompletionService,
    test_tenant_key: str,
    test_product: Product,
):
    """CE-0028 negative case: implementation-phase orchestrator completion
    MUST still flip ``AgentJob.status='completed'``. The CE-0028 bypass is
    scoped tightly to the staging→implementation transition; impl-phase
    closeout is the real project-completion event.
    """
    project = await _seed_project(db_session, test_tenant_key, test_product.id, staging_status="staging_complete")
    job, _ = await _seed_orchestrator_job(db_session, test_tenant_key, project.id, project_phase="implementation")

    result = await completion_service.complete_job(
        job_id=job.job_id,
        result={"summary": "Impl close — should flip job.status='completed'"},
        tenant_key=test_tenant_key,
    )

    assert result.status == "success"
    assert result.staging_directive is None

    refreshed_job = (await db_session.execute(select(AgentJob).where(AgentJob.job_id == job.job_id))).scalar_one()
    assert refreshed_job.status == "completed", (
        f"CE-0028 regression guard: impl-phase orch completion MUST flip job.status='completed', "
        f"got {refreshed_job.status!r}"
    )
    assert refreshed_job.completed_at is not None, "Impl-phase completion must set job.completed_at"
