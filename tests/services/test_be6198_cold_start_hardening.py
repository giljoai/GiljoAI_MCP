# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6198 (90E6PQ) — chain cold-start hardening.

Two cold-start correctness gaps in the project-less chain conductor / sub-orchestrator
flow, both "authoritative chain chapter is right, contradicting solo prose is louder":

FIX #1 — DOUBLE-SPAWN (fork). The conductor eager-mints each member's sub-orchestrator
at staging, then CH_CHAIN_DRIVE STEP A tells it to "spawn" that sub-orch at drive time.
spawn_job had NO dedup -> a literal conductor minted a SECOND orchestrator = fork.
Fix #1A makes spawn_job idempotent for a chain sub-orch (orchestrator-role AND existing
non-terminal orchestrator AND active chain member); everything else mints fresh.

FIX #2 — SUB-ORCH DEADLOCK PROSE (hang). Three staging-end surfaces told a chain
sub-orch "a human presses Implement" — but the CONDUCTOR opens its gate in software, so
it must POLL get_job_mission. The sub-orch (project-bound chain member) now gets the
poll wording; the project-less CONDUCTOR and solo projects keep the original message.

Pinned here:
  1A spawn idempotency (service test, real spawn_job path):
     - reuse: same job_id, NO second orchestrator row, launch prompt present
     - negative (a) non-orchestrator (implementer) still mints fresh
     - negative (b) orchestrator-spawn with NO existing orchestrator still mints fresh
     - negative (c) non-chain (no active run) is unaffected (solo AlreadyExistsError)
  2/S2 _phase_response staging_end: chain member -> poll wording, no "Implement";
       solo + conductor -> original wording.
  2/S1 _staging_directive_for: chain member -> poll message; solo -> schema default.
  2/S3 _check_staging_redirect: chain member -> poll redirect; solo -> click-Implement.
     + _is_chain_member_suborch (DB) detects an active-run member vs a solo project.
  1B CH_CHAIN_DRIVE prose: STEP A references reuse/idempotent, not a bare spawn.

Parallel-safe: DB-touching tests use db_session (TransactionalTestContext). No
module-level mutable state. Edition Scope: CE.
"""

from __future__ import annotations

import random
import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.exceptions import AlreadyExistsError
from giljo_mcp.models import AgentTemplate, Product, Project
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.schemas.responses.orchestration import StagingDirective
from giljo_mcp.services.job_completion_service import (
    _CHAIN_SUBORCH_STAGING_END_ACTION,
    _CHAIN_SUBORCH_STAGING_END_NEXT_ACTION,
    _CHAIN_SUBORCH_STAGING_END_NEXT_STEP,
    _CONDUCTOR_STAGING_END_NEXT_ACTION,
    _CONDUCTOR_STAGING_END_NEXT_STEP,
    JobCompletionService,
)
from giljo_mcp.services.mission_orchestration_service import MissionOrchestrationService
from giljo_mcp.services.protocol_sections.chapters_chain import _build_ch_chain_drive
from giljo_mcp.services.sequence_run_service import SequenceRunService
from giljo_mcp.tenant import TenantManager


# ---------------------------------------------------------------------------
# Seeding helpers
# ---------------------------------------------------------------------------


async def _seed_project(session: AsyncSession, tenant_key: str, *, launched: bool = False) -> str:
    product = Product(
        id=str(uuid.uuid4()),
        name=f"BE-6198 Product {uuid.uuid4().hex[:6]}",
        description="Chain product.",
        tenant_key=tenant_key,
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(product)
    await session.flush()
    project = Project(
        id=str(uuid.uuid4()),
        name=f"BE-6198 {uuid.uuid4().hex[:6]}",
        description="Chain member.",
        mission="Be a chain member.",
        status="active",
        tenant_key=tenant_key,
        product_id=product.id,
        series_number=random.randint(1, 9000),
        execution_mode="claude_code_cli",
        implementation_launched_at=datetime.now(UTC) if launched else None,
        created_at=datetime.now(UTC),
    )
    session.add(project)
    session.info["tenant_key"] = tenant_key
    await session.flush()
    return project.id


async def _seed_orchestrator(session: AsyncSession, tenant_key: str, project_id: str) -> AgentJob:
    """Hand-mint a project-bound, non-decommissioned orchestrator (job + execution)."""
    job_id = str(uuid.uuid4())
    job = AgentJob(
        job_id=job_id,
        tenant_key=tenant_key,
        project_id=project_id,
        mission="orchestrate this project",
        job_type="orchestrator",
        status="active",
        job_metadata={},
    )
    session.add(job)
    session.add(
        AgentExecution(
            agent_id=str(uuid.uuid4()),
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            agent_name="SubOrch",
            status="waiting",
            health_status="unknown",
            project_phase="staging",
            started_at=datetime.now(UTC),
        )
    )
    session.info["tenant_key"] = tenant_key
    await session.flush()
    return job


async def _seed_template(session: AsyncSession, tenant_key: str, name: str = "implementer") -> None:
    session.add(
        AgentTemplate(
            tenant_key=tenant_key,
            name=name,
            role=name,
            description=f"Test {name}",
            system_instructions=f"# {name}\nTest agent.",
            is_active=True,
        )
    )
    await session.flush()


def _run_svc(session: AsyncSession) -> SequenceRunService:
    return SequenceRunService(db_manager=None, tenant_manager=TenantManager(), session=session)


async def _orchestrator_count(session: AsyncSession, tenant_key: str, project_id: str) -> int:
    stmt = (
        select(func.count())
        .select_from(AgentExecution)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            AgentJob.project_id == project_id,
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.agent_display_name == "orchestrator",
        )
    )
    return int((await session.execute(stmt)).scalar_one())


def _job_lifecycle_svc(db_manager, session: AsyncSession):
    from giljo_mcp.services.job_lifecycle_service import JobLifecycleService

    return JobLifecycleService(db_manager=db_manager, tenant_manager=TenantManager(), test_session=session)


# ===========================================================================
# FIX #1A — spawn_job idempotency for a chain sub-orchestrator
# ===========================================================================


@pytest.mark.asyncio
async def test_chain_orchestrator_respawn_reuses_existing_job(db_session, db_manager):
    """Re-spawning an orchestrator for an active-chain member returns the SAME job and
    creates NO duplicate (the cold-start double-spawn guarantee)."""
    tenant = TenantManager.generate_tenant_key()
    p1 = await _seed_project(db_session, tenant)
    p2 = await _seed_project(db_session, tenant)
    await _run_svc(db_session).create(
        project_ids=[p1, p2], resolved_order=[p1, p2], execution_mode="claude_code_cli", tenant_key=tenant
    )
    existing = await _seed_orchestrator(db_session, tenant, p1)

    svc = _job_lifecycle_svc(db_manager, db_session)
    result = await svc.spawn_job(
        agent_display_name="orchestrator",
        agent_name="orchestrator",
        project_id=p1,
        tenant_key=tenant,
    )

    assert result.job_id == existing.job_id, "the idempotent path must return the already-minted orchestrator job"
    assert result.agent_prompt, "the reuse path must still return a launch/bootstrap prompt to open the sub-orch"
    assert await _orchestrator_count(db_session, tenant, p1) == 1, "NO second orchestrator may be minted"


@pytest.mark.asyncio
async def test_non_orchestrator_spawn_still_mints_fresh_in_chain(db_session, db_manager):
    """Negative (a): an implementer spawn for the same chain member is NOT orchestrator-role,
    so it skips the guard and mints fresh."""
    tenant = TenantManager.generate_tenant_key()
    p1 = await _seed_project(db_session, tenant, launched=True)
    p2 = await _seed_project(db_session, tenant)
    await _run_svc(db_session).create(
        project_ids=[p1, p2], resolved_order=[p1, p2], execution_mode="claude_code_cli", tenant_key=tenant
    )
    await _seed_orchestrator(db_session, tenant, p1)
    await _seed_template(db_session, tenant, "implementer")

    svc = _job_lifecycle_svc(db_manager, db_session)
    result = await svc.spawn_job(
        agent_display_name="implementer",
        agent_name="implementer",
        mission="Implement the thing.",
        project_id=p1,
        tenant_key=tenant,
    )

    assert result.job_id != "", "an implementer must mint a brand-new job"
    # The orchestrator count is untouched; a new (implementer) execution exists separately.
    assert await _orchestrator_count(db_session, tenant, p1) == 1


@pytest.mark.asyncio
async def test_orchestrator_spawn_with_no_existing_mints_fresh(db_session, db_manager):
    """Negative (b): a chain member with NO existing orchestrator (true cold respawn)
    mints fresh — the guard only reuses when one already exists."""
    tenant = TenantManager.generate_tenant_key()
    p1 = await _seed_project(db_session, tenant)
    p2 = await _seed_project(db_session, tenant)
    await _run_svc(db_session).create(
        project_ids=[p1, p2], resolved_order=[p1, p2], execution_mode="claude_code_cli", tenant_key=tenant
    )

    svc = _job_lifecycle_svc(db_manager, db_session)
    result = await svc.spawn_job(
        agent_display_name="orchestrator",
        agent_name="orchestrator",
        project_id=p1,
        tenant_key=tenant,
    )

    assert result.job_id, "a cold respawn must mint a fresh orchestrator"
    assert await _orchestrator_count(db_session, tenant, p1) == 1


@pytest.mark.asyncio
async def test_solo_duplicate_orchestrator_unaffected(db_session, db_manager):
    """Negative (c): a SOLO project (no active run) with an existing orchestrator keeps the
    byte-identical pre-existing behavior — duplicate-orchestrator AlreadyExistsError."""
    tenant = TenantManager.generate_tenant_key()
    p1 = await _seed_project(db_session, tenant)  # no run created -> solo
    await _seed_orchestrator(db_session, tenant, p1)

    svc = _job_lifecycle_svc(db_manager, db_session)
    with pytest.raises(AlreadyExistsError):
        await svc.spawn_job(
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            project_id=p1,
            tenant_key=tenant,
        )
    assert await _orchestrator_count(db_session, tenant, p1) == 1


# ===========================================================================
# FIX #2 / S2 — _phase_response staging-end wording
# ===========================================================================


def test_phase_response_chain_member_staging_end_polls():
    phase, _msg, next_action = JobCompletionService._phase_response(
        is_staging_end=True, is_closeout_phase=False, is_chain_member_suborch=True
    )
    assert phase == "staging_end"
    why = next_action["why"]
    assert "click Implement" not in why and "presses Implement" not in why
    assert "opens your implementation gate automatically" in why
    assert next_action["tool"] == "get_job_mission"


def test_phase_response_solo_staging_end_unchanged():
    _phase, _msg, next_action = JobCompletionService._phase_response(
        is_staging_end=True, is_closeout_phase=False, is_chain_member_suborch=False
    )
    assert next_action["tool"] is None
    assert next_action["why"] == (
        "Stop this session now. A human presses Implement in the dashboard to start the "
        "implementation session with a fresh orchestrator execution. Do NOT write the "
        "project closeout from the staging session."
    )


def test_phase_response_conductor_staging_end_awaits_go():
    """BE-6221e: the project-less conductor (is_chain_member_suborch False, is_conductor
    True) must HALT after staging and wait for the user's EXPLICIT GO — NOT auto-drive.
    Its staging-end next_action carries the await-GO wording, not the sub-orch poll
    wording and not a bare 'press Implement once and drive'."""
    phase, _msg, next_action = JobCompletionService._phase_response(
        is_staging_end=True, is_closeout_phase=False, is_conductor=True, is_chain_member_suborch=False
    )
    assert phase == "staging_end"
    assert next_action["tool"] is None
    assert next_action["why"] == _CONDUCTOR_STAGING_END_NEXT_ACTION
    low = next_action["why"].lower()
    assert "explicit go" in low, "the conductor must be told to wait for the user's explicit GO"
    assert "do not re-call get_job_mission" in low, "the conductor must not self-drive via get_job_mission"
    assert "implement chain" in low, "the dashboard GO equivalent must be named"
    # It must NOT carry the sub-orch CONTINUE/poll wording.
    assert "opens your implementation gate automatically" not in next_action["why"]


# ===========================================================================
# FIX #2 / S1 — StagingDirective message override
# ===========================================================================


def test_staging_directive_chain_member_overrides_message():
    directive = JobCompletionService._staging_directive_for(True)
    assert directive.message == _CHAIN_SUBORCH_STAGING_END_NEXT_ACTION
    assert "Implement" not in directive.message


def test_staging_directive_solo_keeps_schema_default():
    directive = JobCompletionService._staging_directive_for(False)
    assert "click 'Implement'" in directive.message, "solo keeps the schema-default human-gate message"


def test_staging_directive_chain_member_action_and_next_step_say_continue():
    """BE-6220: the chain sub-orch directive must NOT contradict its own chain-aware
    message. The schema-default ``action='STOP'`` / ``next_action`` (why='Report staging
    complete to user and stop.') would strand the chain for a literal-following sub-orch.
    action, message and next_action must all agree on CONTINUE."""
    directive = JobCompletionService._staging_directive_for(True)
    default = StagingDirective()
    assert directive.action == "CONTINUE", "chain sub-orch must not be told to STOP"
    assert directive.next_action != default.next_action, (
        "chain sub-orch must not keep the solo 'Report staging complete to user and stop.' next_action"
    )
    assert directive.next_action["tool"] == "get_job_mission", (
        "next_action.tool must point the chain sub-orch at get_job_mission"
    )
    low = directive.next_action["why"].lower()
    assert "continue" in low, "next_action.why must tell the chain sub-orch to continue into implementation"


def test_staging_directive_solo_keeps_action_and_next_step_byte_identical():
    """SOLO IS SACRED: solo keeps the byte-identical schema defaults."""
    directive = JobCompletionService._staging_directive_for(False)
    default = StagingDirective()
    assert directive.action == default.action == "STOP"
    assert directive.next_action == default.next_action


# ===========================================================================
# BE-6221e — conductor HALT-after-staging directive (await the user's GO)
# ===========================================================================


def test_staging_directive_conductor_awaits_go_action_stays_stop():
    """BE-6221e: the project-less chain conductor's staging-end directive keeps
    action='STOP' (it must NOT auto-continue like a sub-orch) and firms the prose to
    'report the staged plan and wait for the user's EXPLICIT GO'."""
    directive = JobCompletionService._staging_directive_for(False, is_conductor=True)
    assert directive.action == "STOP", "conductor await-GO directive must keep action=STOP"
    assert directive.message == _CONDUCTOR_STAGING_END_NEXT_ACTION
    assert directive.next_action["why"] == _CONDUCTOR_STAGING_END_NEXT_STEP
    low = (directive.message + " " + directive.next_action["why"]).lower()
    assert "explicit go" in low, "must tell the conductor to wait for the user's explicit GO"
    assert "do not re-call get_job_mission" in low, "must forbid self-driving via get_job_mission"
    assert "implement chain" in low, "must name the dashboard GO equivalent"


def test_staging_directive_conductor_differs_from_solo_default():
    """BE-6221e: the conductor directive is distinct from the solo schema default
    (firmer wording) while BOTH keep action='STOP'."""
    conductor = JobCompletionService._staging_directive_for(False, is_conductor=True)
    solo = StagingDirective()
    assert conductor.action == solo.action == "STOP"
    assert conductor.message != solo.message
    assert conductor.next_action != solo.next_action


def test_be6221e_solo_and_suborch_staging_directives_byte_identical():
    """BE-6221e regression: adding the conductor await-GO branch changes ONLY the
    conductor. The SOLO directive stays the schema default and the SUB-ORCH directive
    stays the BE-6220 CONTINUE override — both BYTE-IDENTICAL to before BE-6221e."""
    default = StagingDirective()

    solo = JobCompletionService._staging_directive_for(False)
    assert solo.action == default.action
    assert solo.message == default.message
    assert solo.next_action == default.next_action

    sub = JobCompletionService._staging_directive_for(True)
    assert sub.action == _CHAIN_SUBORCH_STAGING_END_ACTION
    assert sub.message == _CHAIN_SUBORCH_STAGING_END_NEXT_ACTION
    assert sub.next_action["why"] == _CHAIN_SUBORCH_STAGING_END_NEXT_STEP


def test_chain_suborch_staging_end_leads_with_immediate_call_before_sleep():
    """BE-6208d: the staging-end poll prose must lead with the immediate
    get_job_mission call (the gate is already OPEN) and frame the ~30s sleep as
    a fallback only — not the first instruction."""
    msg = _CHAIN_SUBORCH_STAGING_END_NEXT_ACTION
    low = msg.lower()

    once_idx = low.find("get_job_mission once")
    sleep_idx = low.find("sleep")
    assert once_idx != -1, "must instruct an immediate get_job_mission call"
    assert sleep_idx != -1, "must still describe the fallback sleep"
    assert once_idx < sleep_idx, "the immediate call must precede the sleep instruction"
    # The sleep is a conditional fallback, not the default action.
    assert "only if" in low, "the sleep/retry must be framed as a fallback ('ONLY if')"


# ===========================================================================
# FIX #2 / S3 — get_staging_instructions redirect wording
# ===========================================================================


def test_check_staging_redirect_chain_member_polls():
    project = Project(
        id=str(uuid.uuid4()),
        name="P",
        description="d",
        mission="m",
        status="active",
        tenant_key="tk",
        staging_status="staging_complete",
        implementation_launched_at=None,
    )
    out = MissionOrchestrationService._check_staging_redirect(project, "job-1", is_chain_member=True)
    assert out is not None
    assert out["redirect"] == "get_job_mission"
    assert "do NOT wait for a human" in out["message"]
    assert "click Implement" not in out["message"]


def test_check_staging_redirect_solo_clicks_implement():
    project = Project(
        id=str(uuid.uuid4()),
        name="P",
        description="d",
        mission="m",
        status="active",
        tenant_key="tk",
        staging_status="staging_complete",
        implementation_launched_at=None,
    )
    out = MissionOrchestrationService._check_staging_redirect(project, "job-1", is_chain_member=False)
    assert out is not None
    assert out["redirect"] is None
    assert "Return to the dashboard and click Implement" in out["message"]


# ===========================================================================
# FIX #2 — _is_chain_member_suborch DB detection
# ===========================================================================


@pytest.mark.asyncio
async def test_is_chain_member_suborch_true_for_active_run(db_session):
    tenant = TenantManager.generate_tenant_key()
    p1 = await _seed_project(db_session, tenant)
    p2 = await _seed_project(db_session, tenant)
    await _run_svc(db_session).create(
        project_ids=[p1, p2], resolved_order=[p1, p2], execution_mode="claude_code_cli", tenant_key=tenant
    )
    svc = JobCompletionService(db_manager=None, tenant_manager=TenantManager(), test_session=db_session)
    assert await svc._is_chain_member_suborch(db_session, p1, tenant) is True


@pytest.mark.asyncio
async def test_is_chain_member_suborch_false_for_solo(db_session):
    tenant = TenantManager.generate_tenant_key()
    p1 = await _seed_project(db_session, tenant)  # no run
    svc = JobCompletionService(db_manager=None, tenant_manager=TenantManager(), test_session=db_session)
    assert await svc._is_chain_member_suborch(db_session, p1, tenant) is False


# ===========================================================================
# FIX #1B — CH_CHAIN_DRIVE STEP A prose references reuse/idempotency
# ===========================================================================


def test_chain_drive_step_a_references_idempotent_reuse():
    chapter = _build_ch_chain_drive(
        run_id="r1",
        resolved_order=["p1", "p2"],
        current_index=0,
        execution_mode="claude_code_cli",
        conductor_agent_id="conductor-1",
        job_id="job-1",
    )
    low = chapter.lower()
    assert "idempotent" in low, "STEP A must state spawn_job for a sub-orch is idempotent"
    assert "already minted" in low or "already-minted" in low, "STEP A must say the sub-orch was minted at staging"
    assert "get_workflow_status" in chapter, "STEP A must resolve the existing orchestrator via get_workflow_status"
    assert "never mints a duplicate" in low or "never a duplicate" in low
