# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE-6085 regression — Deactivate conditionally resets a NEVER-RUN orchestrator.

Edition Scope: Both (CE core project lifecycle).

A project wedges when an orchestrator fixture is created (Stage clicked) but the
orchestrator session never runs: the Stage button is disabled (an orchestrator
already exists) and no Unstage shows (not 'staged'), so there is no UI recovery
path. The fix makes the EXISTING Deactivate action the recovery -- but ONLY when
the orchestrator never ran. A real run is never touched (load-bearing ELSE).

Detection (all three) -- "the orchestrator never ran":
  1. a non-decommissioned orchestrator execution exists in 'waiting'/'staged',
  2. EVERY such execution has working_started_at IS NULL (never entered 'working'
     -- the BE-5107 listener anchors it on the first 'working' transition), and
  3. zero non-orchestrator (subagent) executions.

These tests are exercised at the SERVICE layer (the layer the bug occurred) on a
real DB via TransactionalTestContext, tenant-scoped, parallel-safe.

Cases:
  (a) WEDGED ('waiting', working_started_at NULL, 0 subagents, WITH a placeholder
      mission) -> RESET. Proves the new detection fires exactly where the old
      mission-NULL check was dead code.
  (a2) same but orchestrator parked in 'staged' -> RESET (covers the status tuple).
  (b) RAN (working_started_at SET) -> NOT reset.
  (c) SUBAGENTS (>=1 non-orch child) -> NOT reset.
  (d) COMPLETED-STAGING (staging_status='staging_complete') -> NOT reset.
  (e) after reset + reactivate -> project re-stageable (fresh orchestrator fixture,
      decommissioned one excluded).
"""

import uuid
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest
from sqlalchemy import and_, select

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.models import Product, Project, Task
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.services.project_lifecycle_service import ProjectLifecycleService
from tests.fixtures.base_fixtures import TestData


_PLACEHOLDER_MISSION = "Orchestrator for project: Wedged"


def _tenant_manager(tenant_key: str) -> MagicMock:
    tm = MagicMock()
    tm.get_current_tenant = MagicMock(return_value=tenant_key)
    return tm


async def _setup_project(
    db_session,
    tenant_key: str,
    *,
    staging_status: str | None = "staging",
    orch_status: str = "waiting",
    orch_working_started_at: datetime | None = None,
    orch_mission: str | None = _PLACEHOLDER_MISSION,
    with_subagent: bool = False,
    implementation_launched: bool = False,
    add_task: bool = True,
) -> tuple[Project, AgentExecution, Task | None]:
    """Build a product + ACTIVE project + orchestrator job/execution (+ optional
    subagent + project task) and commit. Returns (project, orch_execution, task)."""
    product = Product(
        id=str(uuid.uuid4()),
        name="Wedged Product",
        description="desc",
        tenant_key=tenant_key,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product)
    await db_session.flush()

    project = Project(
        id=str(uuid.uuid4()),
        name="Wedged Project",
        description="Human-written requirements that MUST survive deactivate.",
        mission="orchestrator-authored mission text",
        status=ProjectStatus.ACTIVE,
        staging_status=staging_status,
        product_id=product.id,
        tenant_key=tenant_key,
        series_number=1,
        implementation_launched_at=datetime.now(UTC) if implementation_launched else None,
    )
    db_session.add(project)
    await db_session.flush()

    task: Task | None = None
    if add_task:
        task = Task(
            id=str(uuid.uuid4()),
            title="Preserve me",
            description="task desc",
            tenant_key=tenant_key,
            product_id=product.id,
            project_id=project.id,
            status="pending",
            priority="medium",
        )
        db_session.add(task)

    orch_job = AgentJob(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_key,
        project_id=project.id,
        mission=orch_mission,
        job_type="orchestrator",
        status="active",
    )
    db_session.add(orch_job)
    orch_exec = AgentExecution(
        agent_id=str(uuid.uuid4()),
        job_id=orch_job.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        agent_name="orchestrator",
        status=orch_status,
        working_started_at=orch_working_started_at,
        started_at=datetime.now(UTC),
        project_phase="staging",
    )
    db_session.add(orch_exec)

    if with_subagent:
        sub_job = AgentJob(
            job_id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            project_id=project.id,
            mission="implement feature X",
            job_type="implementer",
            status="active",
        )
        db_session.add(sub_job)
        db_session.add(
            AgentExecution(
                agent_id=str(uuid.uuid4()),
                job_id=sub_job.job_id,
                tenant_key=tenant_key,
                agent_display_name="implementer",
                agent_name="implementer",
                status="waiting",
                started_at=datetime.now(UTC),
            )
        )

    await db_session.commit()
    return project, orch_exec, task


def _service(db_manager, db_session, tenant_key: str) -> ProjectLifecycleService:
    return ProjectLifecycleService(
        db_manager=db_manager,
        tenant_manager=_tenant_manager(tenant_key),
        test_session=db_session,
    )


async def _orch_execution_exists(db_session, execution_id: str) -> bool:
    """True if an AgentExecution row with this id still exists (query, no refresh)."""
    row = (
        await db_session.execute(select(AgentExecution).where(AgentExecution.id == execution_id))
    ).scalar_one_or_none()
    return row is not None


async def _orch_job_exists(db_session, job_id: str) -> bool:
    """True if an AgentJob row with this job_id still exists (query, no refresh)."""
    row = (await db_session.execute(select(AgentJob).where(AgentJob.job_id == job_id))).scalar_one_or_none()
    return row is not None


async def _count_orchestrator_executions(db_session, project_id: str, tenant_key: str) -> int:
    """Count ALL orchestrator executions for a project (any status) -- the
    accumulation check: post-deactivate this must be 0 (no decommissioned
    tombstones left behind)."""
    rows = (
        (
            await db_session.execute(
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentJob.project_id == project_id,
                        AgentExecution.agent_display_name == "orchestrator",
                        AgentExecution.tenant_key == tenant_key,
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    return len(rows)


# ---------------------------------------------------------------------------
# (a) RESET path — the wedge the fix exists for
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deactivate_resets_never_run_orchestrator(db_session, db_manager):
    """WEDGED: orchestrator 'waiting', working_started_at NULL, 0 subagents, WITH a
    placeholder mission -> deactivate HARD-DELETES the orchestrator fixture
    (execution + job, BE-6123), resets staging_status to None, and PRESERVES
    title/description/project/tasks."""
    tenant_key = TestData.generate_tenant_key()
    project, orch_exec, task = await _setup_project(db_session, tenant_key)
    orig_title, orig_desc = project.name, project.description
    # Capture identifiers BEFORE deletion -- the ORM object must NOT be refreshed
    # afterwards (its row is gone). Query for absence instead.
    orch_exec_id, orch_job_id = orch_exec.id, orch_exec.job_id

    service = _service(db_manager, db_session, tenant_key)
    result = await service.deactivate_project(project.id, tenant_key=tenant_key)

    await db_session.refresh(project)
    await db_session.refresh(task)

    # Status flipped (the always-true half of deactivate).
    assert result.status == ProjectStatus.INACTIVE
    # BE-6123: the never-run orchestrator fixture is DELETED (no tombstone).
    assert await _orch_execution_exists(db_session, orch_exec_id) is False
    assert await _orch_job_exists(db_session, orch_job_id) is False
    # Clean pre-staging state (un-wedge preserved).
    assert project.staging_status is None
    assert project.mission == ""
    assert project.implementation_launched_at is None
    # Preserved: title, description, the project row, the task.
    assert project.name == orig_title
    assert project.description == orig_desc
    assert task.title == "Preserve me"


@pytest.mark.asyncio
async def test_deactivate_resets_staged_never_run_orchestrator(db_session, db_manager):
    """(a2) Same wedge but the orchestrator is parked in 'staged' -> still DELETED
    (covers the full ('waiting','staged') status tuple)."""
    tenant_key = TestData.generate_tenant_key()
    project, orch_exec, _ = await _setup_project(db_session, tenant_key, orch_status="staged", orch_mission=None)
    orch_exec_id, orch_job_id = orch_exec.id, orch_exec.job_id

    service = _service(db_manager, db_session, tenant_key)
    await service.deactivate_project(project.id, tenant_key=tenant_key)

    await db_session.refresh(project)
    assert await _orch_execution_exists(db_session, orch_exec_id) is False
    assert await _orch_job_exists(db_session, orch_job_id) is False
    assert project.staging_status is None


# ---------------------------------------------------------------------------
# (b)(c)(d) NO-RESET path — load-bearing: a real run is never touched
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_deactivate_preserves_orchestrator_that_ran(db_session, db_manager):
    """(b) RAN: working_started_at SET (orchestrator entered 'working' at least once,
    then parked at 'waiting' per CE-0032) -> deactivate must NOT touch agent state."""
    tenant_key = TestData.generate_tenant_key()
    project, orch_exec, _ = await _setup_project(db_session, tenant_key, orch_working_started_at=datetime.now(UTC))

    service = _service(db_manager, db_session, tenant_key)
    await service.deactivate_project(project.id, tenant_key=tenant_key)

    await db_session.refresh(project)
    await db_session.refresh(orch_exec)
    assert project.status == ProjectStatus.INACTIVE  # only the status changed
    assert orch_exec.status == "waiting"  # untouched
    assert project.staging_status == "staging"  # untouched
    assert project.mission == "orchestrator-authored mission text"  # untouched


@pytest.mark.asyncio
async def test_deactivate_preserves_orchestrator_with_subagents(db_session, db_manager):
    """(c) SUBAGENTS: >=1 non-orchestrator child execution -> NOT reset, even though
    the orchestrator itself never entered 'working'."""
    tenant_key = TestData.generate_tenant_key()
    project, orch_exec, _ = await _setup_project(db_session, tenant_key, with_subagent=True)

    service = _service(db_manager, db_session, tenant_key)
    await service.deactivate_project(project.id, tenant_key=tenant_key)

    await db_session.refresh(project)
    await db_session.refresh(orch_exec)
    assert project.status == ProjectStatus.INACTIVE
    assert orch_exec.status == "waiting"  # untouched
    assert project.staging_status == "staging"  # untouched


@pytest.mark.asyncio
async def test_deactivate_preserves_completed_staging(db_session, db_manager):
    """(d) COMPLETED-STAGING: staging_status='staging_complete' (staging finished,
    Implement not yet clicked) -> NOT reset. The orchestrator ran."""
    tenant_key = TestData.generate_tenant_key()
    project, orch_exec, _ = await _setup_project(
        db_session,
        tenant_key,
        staging_status="staging_complete",
        orch_working_started_at=datetime.now(UTC),
    )

    service = _service(db_manager, db_session, tenant_key)
    await service.deactivate_project(project.id, tenant_key=tenant_key)

    await db_session.refresh(project)
    await db_session.refresh(orch_exec)
    assert project.status == ProjectStatus.INACTIVE
    assert orch_exec.status == "waiting"  # untouched
    assert project.staging_status == "staging_complete"  # untouched


# ---------------------------------------------------------------------------
# (e) End-to-end recovery — reset then reactivate yields a re-stageable project
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_reset_then_reactivate_is_restageable(db_session, db_manager):
    """(e) After deactivate (delete) + reactivate, the project is re-stageable: the
    old orchestrator fixture is DELETED (BE-6123, not tombstoned) and reactivation
    builds a FRESH orchestrator fixture; staging_status is clean (None)."""
    tenant_key = TestData.generate_tenant_key()
    project, old_orch, _ = await _setup_project(db_session, tenant_key)
    old_orch_id, old_orch_job_id, old_agent_id = old_orch.id, old_orch.job_id, old_orch.agent_id

    service = _service(db_manager, db_session, tenant_key)
    await service.deactivate_project(project.id, tenant_key=tenant_key)
    # BE-6123: the never-run fixture is GONE, not decommissioned (no refresh of a
    # deleted ORM object).
    assert await _orch_execution_exists(db_session, old_orch_id) is False
    assert await _orch_job_exists(db_session, old_orch_job_id) is False

    # Reactivate -> _ensure_orchestrator_fixture creates a fresh orchestrator.
    await service.activate_project(project.id, tenant_key=tenant_key)
    await db_session.refresh(project)

    assert project.status == ProjectStatus.ACTIVE
    assert project.staging_status is None  # clean: Stage button works again

    live_orchestrators = (
        (
            await db_session.execute(
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentJob.project_id == project.id,
                        AgentExecution.agent_display_name == "orchestrator",
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status != "decommissioned",
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(live_orchestrators) == 1
    assert live_orchestrators[0].agent_id != old_agent_id  # a FRESH fixture


# ---------------------------------------------------------------------------
# (f) BE-6123 — repeated activate/deactivate does NOT accumulate tombstones,
#     and once an orchestrator RUNS the cycle stops deleting it.
# ---------------------------------------------------------------------------


async def _live_orchestrator(db_session, project_id: str, tenant_key: str) -> AgentExecution:
    """Return the single non-decommissioned orchestrator execution (asserts exactly one)."""
    rows = (
        (
            await db_session.execute(
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentJob.project_id == project_id,
                        AgentExecution.agent_display_name == "orchestrator",
                        AgentExecution.tenant_key == tenant_key,
                        AgentExecution.status != "decommissioned",
                    )
                )
            )
        )
        .scalars()
        .all()
    )
    assert len(rows) == 1, f"expected exactly 1 live orchestrator, found {len(rows)}"
    return rows[0]


@pytest.mark.asyncio
async def test_activate_deactivate_cycle_no_accumulation_and_ran_survives(db_session, db_manager):
    """(f) BE-6123 regression: activate->deactivate->activate->deactivate on ONE
    project leaves NO accumulation (0 orchestrator rows, no decommissioned
    tombstones; <=1 live at any point). Then, once an orchestrator actually RUNS
    (working_started_at SET), deactivate must STOP deleting it -- it survives as
    audit history."""
    tenant_key = TestData.generate_tenant_key()

    product = Product(
        id=str(uuid.uuid4()),
        name="Cycle Product",
        description="desc",
        tenant_key=tenant_key,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product)
    await db_session.flush()
    project = Project(
        id=str(uuid.uuid4()),
        name="Cycle Project",
        description="requirements that survive every cycle",
        mission="",
        status=ProjectStatus.INACTIVE,
        staging_status=None,
        product_id=product.id,
        tenant_key=tenant_key,
        series_number=1,
    )
    db_session.add(project)
    await db_session.commit()

    service = _service(db_manager, db_session, tenant_key)

    # Cycle 1: activate creates a fresh fixture; deactivate deletes it.
    await service.activate_project(project.id, tenant_key=tenant_key)
    agent_id_1 = (await _live_orchestrator(db_session, project.id, tenant_key)).agent_id
    await service.deactivate_project(project.id, tenant_key=tenant_key)
    assert await _count_orchestrator_executions(db_session, project.id, tenant_key) == 0

    # Cycle 2: a NEW fixture (different agent_id), then deleted again -> still 0.
    await service.activate_project(project.id, tenant_key=tenant_key)
    agent_id_2 = (await _live_orchestrator(db_session, project.id, tenant_key)).agent_id
    assert agent_id_2 != agent_id_1
    await service.deactivate_project(project.id, tenant_key=tenant_key)
    # No accumulation: zero orchestrator rows of ANY status remain for the project.
    assert await _count_orchestrator_executions(db_session, project.id, tenant_key) == 0

    # Now simulate the orchestrator ACTUALLY RUNNING this cycle.
    await service.activate_project(project.id, tenant_key=tenant_key)
    ran = await _live_orchestrator(db_session, project.id, tenant_key)
    ran_id, ran_agent_id = ran.id, ran.agent_id
    ran.working_started_at = datetime.now(UTC)
    await db_session.commit()

    # Deactivate must NOT touch a ran orchestrator -> it survives.
    await service.deactivate_project(project.id, tenant_key=tenant_key)
    assert await _orch_execution_exists(db_session, ran_id) is True
    survivor = await _live_orchestrator(db_session, project.id, tenant_key)
    assert survivor.agent_id == ran_agent_id
    assert survivor.status != "decommissioned"
