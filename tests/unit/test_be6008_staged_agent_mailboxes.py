# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6008 service/protocol/messaging regression tests: staged-agent mailboxes.

Three of the four BE-6008 regressions live here (one per failing layer); the
fourth — the MCP-BOUNDARY spawn-without-mission test — lives in
``tests/integration/test_be6008_spawn_boundary.py`` because it needs the FastMCP
``mcp`` transport (a CI dependency not present in every local venv).

(a) SERVICE — two-phase spawn through ``JobLifecycleService.spawn_job`` creates a
    'staged' execution with a NULL job mission; ``MissionService.update_agent_mission``
    performs the Phase-2 write and transitions the execution 'staged' -> 'waiting'.

(c) PROTOCOL-INJECTION — a multi_terminal SPECIALIST mission carries the live
    roster (CH_TEAM) + authority (CH_MESSAGING) chapters; a CLI mode
    (claude_code_cli) carries NEITHER.

(d) MESSAGING — a Hub post to a 'staged' agent persists in message_recipients
    and is delivered by get_thread_history (staged agents are messageable).
    BE-9012d: retargeted from the retired bus (send_message/receive_messages).

Parallel-safe: every DB-touching test runs inside ``TransactionalTestContext``
(via the ``db_session`` fixture, rolled back at teardown), seeds a unique
``tk_...`` tenant, holds no module-level mutable state, and has no ordering
dependency. Runs clean under ``pytest -n auto``.

Project: BE-6008.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import tenant_session_context
from giljo_mcp.models import Project
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.products import Product
from giljo_mcp.models.templates import AgentTemplate
from giljo_mcp.services.comm_thread_service import CommThreadService
from giljo_mcp.services.job_lifecycle_service import JobLifecycleService
from giljo_mcp.services.mission_service import MissionService
from giljo_mcp.services.taxonomy_ops import ensure_default_types_seeded
from giljo_mcp.tenant import TenantManager


pytestmark = pytest.mark.asyncio


async def _seed_product(session: AsyncSession, tenant_key: str) -> str:
    """TSK-8005: seed a real Product instead of relying on projects.product_id=NULL
    (production enforces NOT NULL via ce_0004; NULL also risks a
    uq_project_taxonomy_active NULLS-NOT-DISTINCT collision within a tenant)."""
    product_id = str(uuid.uuid4())
    session.add(Product(id=product_id, tenant_key=tenant_key, name=f"BE-6008 Product {uuid.uuid4().hex[:8]}"))
    session.info["tenant_key"] = tenant_key
    await session.flush()
    return product_id


async def _seed_project(
    session: AsyncSession,
    tenant_key: str,
    execution_mode: str = "multi_terminal",
    *,
    implementation_launched: bool = False,
) -> str:
    """Seed one Project for the given tenant and return its id.

    ``implementation_launched=True`` stamps ``implementation_launched_at`` so
    ``get_agent_mission`` clears the implementation-phase gate and returns a real
    full_protocol (required by the protocol-injection tests).
    """
    suffix = uuid.uuid4().hex[:8]
    product_id = await _seed_product(session, tenant_key)
    project = Project(
        id=str(uuid.uuid4()),
        product_id=product_id,
        name=f"BE-6008 Project {suffix}",
        description="Two-phase spawn regression project.",
        mission="Stage agents, then write missions.",
        status="active",
        tenant_key=tenant_key,
        series_number=1,
        execution_mode=execution_mode,
        created_at=datetime.now(UTC),
        implementation_launched_at=datetime.now(UTC) if implementation_launched else None,
    )
    session.add(project)
    session.info["tenant_key"] = tenant_key
    await session.flush()
    return project.id


async def _seed_template(session: AsyncSession, tenant_key: str, name: str = "implementer") -> None:
    """Seed an active AgentTemplate so spawn_job's agent_name validation passes."""
    session.add(
        AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name=name,
            is_active=True,
        )
    )
    session.info["tenant_key"] = tenant_key
    await session.flush()


async def _get_execution(session: AsyncSession, tenant_key: str, job_id: str) -> AgentExecution:
    row = await session.execute(
        select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.job_id == job_id,
        )
    )
    return row.scalar_one()


async def _get_job(session: AsyncSession, tenant_key: str, job_id: str) -> AgentJob:
    row = await session.execute(select(AgentJob).where(AgentJob.tenant_key == tenant_key, AgentJob.job_id == job_id))
    return row.scalar_one()


# ---------------------------------------------------------------------------
# (a) SERVICE — two-phase spawn + staged->waiting transition
# ---------------------------------------------------------------------------


async def test_two_phase_spawn_then_mission_write_transitions_staged_to_waiting(
    db_session: AsyncSession,
) -> None:
    """Phase-1 mission-less spawn -> 'staged' + NULL mission; Phase-2 write -> 'waiting'."""
    tenant_key = TenantManager.generate_tenant_key()
    project_id = await _seed_project(db_session, tenant_key)
    await _seed_template(db_session, tenant_key, "implementer")

    lifecycle = JobLifecycleService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        test_session=db_session,
    )

    # Phase 1: spawn WITHOUT a mission.
    result = await lifecycle.spawn_job(
        agent_display_name="implementer",
        agent_name="implementer",
        project_id=project_id,
        tenant_key=tenant_key,
    )
    job_id = result.job_id

    execution = await _get_execution(db_session, tenant_key, job_id)
    job = await _get_job(db_session, tenant_key, job_id)
    assert execution.status == "staged", "mission-less spawn must create a 'staged' execution"
    assert job.mission is None, "a staged job's mission must be NULL until Phase-2"

    # Phase 2: author the mission -> staged unlocks to waiting.
    mission_service = MissionService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        test_session=db_session,
    )
    await mission_service.update_agent_mission(
        job_id=job_id, tenant_key=tenant_key, mission="Implement BE-6008 unit X."
    )

    execution_after = await _get_execution(db_session, tenant_key, job_id)
    job_after = await _get_job(db_session, tenant_key, job_id)
    assert execution_after.status == "waiting", "Phase-2 write must transition staged -> waiting"
    assert job_after.mission == "Implement BE-6008 unit X."


async def test_spawn_with_mission_is_waiting_not_staged(db_session: AsyncSession) -> None:
    """A normal mission-bearing spawn stays 'waiting' (no regression to the default path)."""
    tenant_key = TenantManager.generate_tenant_key()
    project_id = await _seed_project(db_session, tenant_key)
    await _seed_template(db_session, tenant_key, "implementer")

    lifecycle = JobLifecycleService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        test_session=db_session,
    )
    result = await lifecycle.spawn_job(
        agent_display_name="implementer",
        agent_name="implementer",
        project_id=project_id,
        tenant_key=tenant_key,
        mission="Do the work now.",
    )

    execution = await _get_execution(db_session, tenant_key, result.job_id)
    assert execution.status == "waiting"


# ---------------------------------------------------------------------------
# (c) PROTOCOL-INJECTION — multi_terminal specialist gets roster+authority; CLI does not
# ---------------------------------------------------------------------------


async def _spawn_and_fetch_mission(db_session: AsyncSession, tenant_key: str, execution_mode: str):
    project_id = await _seed_project(
        db_session, tenant_key, execution_mode=execution_mode, implementation_launched=True
    )
    await _seed_template(db_session, tenant_key, "implementer")

    lifecycle = JobLifecycleService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        test_session=db_session,
    )
    result = await lifecycle.spawn_job(
        agent_display_name="implementer",
        agent_name="implementer",
        project_id=project_id,
        tenant_key=tenant_key,
        mission="Implement the feature.",
    )

    mission_service = MissionService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        test_session=db_session,
    )
    return await mission_service.get_agent_mission(job_id=result.job_id, tenant_key=tenant_key)


async def test_multi_terminal_specialist_mission_has_roster_and_authority_chapters(
    db_session: AsyncSession,
) -> None:
    """A multi_terminal specialist's full_protocol carries CH_TEAM + CH_MESSAGING."""
    tenant_key = TenantManager.generate_tenant_key()
    response = await _spawn_and_fetch_mission(db_session, tenant_key, "multi_terminal")

    protocol = response.full_protocol
    assert "CH_TEAM: LIVE PROJECT ROSTER" in protocol, "multi_terminal specialist must get the live roster chapter"
    assert "CH_MESSAGING: WHO AUTHORS WORK" in protocol, "multi_terminal specialist must get the authority chapter"

    # BE-6008 de-dupe: the LIVE CH_TEAM roster supersedes the static `## YOUR TEAM`
    # table for a multi_terminal specialist — the mission body must NOT carry the
    # static roster too (no double roster).
    assert "## YOUR TEAM" not in response.mission, (
        "multi_terminal specialist mission body must NOT carry the static roster (live CH_TEAM supersedes it)"
    )


async def test_cli_mode_specialist_mission_omits_roster_and_authority_chapters(
    db_session: AsyncSession,
) -> None:
    """A claude_code_cli specialist's full_protocol carries NEITHER chapter."""
    tenant_key = TenantManager.generate_tenant_key()
    response = await _spawn_and_fetch_mission(db_session, tenant_key, "claude_code_cli")

    protocol = response.full_protocol
    assert "CH_TEAM: LIVE PROJECT ROSTER" not in protocol, "CLI mode must NOT inject the live roster chapter"
    assert "CH_MESSAGING: WHO AUTHORS WORK" not in protocol, "CLI mode must NOT inject the authority chapter"

    # BE-6008 de-dupe is multi_terminal-only: a CLI specialist still gets the
    # static `## YOUR TEAM` roster in its mission body (it has no live CH_TEAM).
    assert "## YOUR TEAM" in response.mission, (
        "CLI mode specialist must still carry the static roster in its mission body"
    )


# ---------------------------------------------------------------------------
# (d) MESSAGING — a message to a 'staged' agent persists and is delivered
# ---------------------------------------------------------------------------


async def test_message_to_staged_agent_is_persisted_and_delivered(db_session: AsyncSession) -> None:
    """A staged agent is messageable: a Hub post persists a recipient row and is
    delivered via get_thread_history.

    BE-9012d: retargeted from the retired bus (send_message/receive_messages) onto
    the Hub (post_to_thread/get_thread_history) — the CH_MESSAGING chapter's live
    peer-messaging path for a multi_terminal specialist.
    """
    tenant_key = TenantManager.generate_tenant_key()
    project_id = await _seed_project(db_session, tenant_key)
    await _seed_template(db_session, tenant_key, "implementer")

    # Phase-1 spawn a staged (mission-less) agent.
    lifecycle = JobLifecycleService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        test_session=db_session,
    )
    staged = await lifecycle.spawn_job(
        agent_display_name="implementer",
        agent_name="implementer",
        project_id=project_id,
        tenant_key=tenant_key,
    )
    staged_agent_id = staged.agent_id

    # A second (sender) agent on the same project.
    sender = await lifecycle.spawn_job(
        agent_display_name="orchestrator",
        agent_name="orchestrator",
        project_id=project_id,
        tenant_key=tenant_key,
        mission="Coordinate.",
    )

    execution = await _get_execution_for_agent(db_session, tenant_key, staged_agent_id)
    assert execution.status == "staged", "precondition: target agent is staged"

    # The Hub's CHT taxonomy type must exist for the tenant before create_thread
    # (normally seeded at real tenant/product creation; this test mints a bare
    # tenant_key, so seed it explicitly).
    with tenant_session_context(db_session, tenant_key):
        await ensure_default_types_seeded(db_session, tenant_key)

    comm = CommThreadService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        session=db_session,
    )
    thread = await comm.resolve_or_create_bound_thread(project_id=project_id, tenant_key=tenant_key)
    post_result = await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="INFO: schema is ready for you.",
        from_agent=sender.agent_id,
        to_participant=staged_agent_id,
        tenant_key=tenant_key,
    )
    assert post_result["recipients"] == [staged_agent_id], "the staged agent must be an accepted recipient"

    history = await comm.get_thread_history(
        thread_id=thread["thread_id"],
        as_participant=staged_agent_id,
        tenant_key=tenant_key,
    )
    contents = [m.get("content") for m in history["messages"]]
    assert any("schema is ready for you" in (c or "") for c in contents), (
        "a staged agent must receive Hub posts addressed to it"
    )


async def _get_execution_for_agent(session: AsyncSession, tenant_key: str, agent_id: str) -> AgentExecution:
    row = await session.execute(
        select(AgentExecution).where(
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.agent_id == agent_id,
        )
    )
    return row.scalar_one()
