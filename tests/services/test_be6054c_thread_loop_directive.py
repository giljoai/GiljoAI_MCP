# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6054c — thread loop/sleep coordination regression at the failing layer.

The mechanism: a user arms a loop on a comm thread (post_to_thread
loop_directive=True). An addressed agent then gets the "loop/sleep until this
thread is resolved/closed" directive composed into its NEXT get_agent_mission.
The loop provably TERMINATES because the directive disappears once the thread
reaches a terminal status.

Covered here:
- has_active_loop_directive: True when armed on a non-terminal thread, False
  when the thread is closed, False when nothing is armed (the termination proof
  at the service/query layer).
- mission composition: the directive text appears in full_protocol when armed +
  non-terminal, and is ABSENT when not armed and after the thread is closed.

Real DB (rollback-isolated db_session). Reuses BE-6008's spawn/seed helpers.
"""

from __future__ import annotations

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.services.comm_thread_service import CommThreadService
from giljo_mcp.services.job_lifecycle_service import JobLifecycleService
from giljo_mcp.services.mission_service import MissionService
from giljo_mcp.services.taxonomy_ops import ensure_default_types_seeded
from giljo_mcp.tenant import TenantManager

# Reuse the proven spawn/seed machinery from the BE-6008 mission tests.
from tests.unit.test_be6008_staged_agent_mailboxes import (
    _get_execution,
    _seed_project,
    _seed_template,
)


pytestmark = pytest.mark.asyncio

_DIRECTIVE_MARKER = "LOOP / SLEEP DIRECTIVE"


def _comm(db_session) -> CommThreadService:
    return CommThreadService(db_manager=None, tenant_manager=TenantManager(), session=db_session)


async def _seed_cht(db_session, tenant_key: str) -> None:
    from giljo_mcp.database import tenant_session_context

    with tenant_session_context(db_session, tenant_key):
        await ensure_default_types_seeded(db_session, tenant_key)


async def _spawn_agent(db_session: AsyncSession, tenant_key: str) -> tuple[str, str]:
    """Spawn a multi_terminal specialist; return (job_id, agent_id)."""
    project_id = await _seed_project(
        db_session, tenant_key, execution_mode="multi_terminal", implementation_launched=True
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
    execution = await _get_execution(db_session, tenant_key, result.job_id)
    return result.job_id, str(execution.agent_id)


async def _fetch_protocol(db_session: AsyncSession, tenant_key: str, job_id: str) -> str:
    mission_service = MissionService(
        db_manager=None,  # type: ignore[arg-type]
        tenant_manager=TenantManager(),
        test_session=db_session,
    )
    response = await mission_service.get_agent_mission(job_id=job_id, tenant_key=tenant_key)
    return response.full_protocol or ""


# ---------------------------------------------------------------------------
# Query layer: the termination proof
# ---------------------------------------------------------------------------


async def test_has_active_loop_directive_true_when_armed(db_session):
    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="loop me", creator_id="agent-x", tenant_key=tenant)
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="please loop until resolved",
        to_participant="agent-x",
        loop_directive=True,
        user_id=None,
        from_agent="orchestrator",
        tenant_key=tenant,
    )
    assert await comm.has_active_loop_directive(agent_id="agent-x", tenant_key=tenant) is True


async def test_has_active_loop_directive_false_after_thread_closed(db_session):
    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="loop me", creator_id="agent-x", tenant_key=tenant)
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="loop",
        to_participant="agent-x",
        loop_directive=True,
        from_agent="orchestrator",
        tenant_key=tenant,
    )
    assert await comm.has_active_loop_directive(agent_id="agent-x", tenant_key=tenant) is True

    # Close the thread -> the loop must terminate (directive goes silent).
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="done",
        from_agent="orchestrator",
        set_status="closed",
        tenant_key=tenant,
    )
    assert await comm.has_active_loop_directive(agent_id="agent-x", tenant_key=tenant) is False


async def test_has_active_loop_directive_false_when_not_armed(db_session):
    tenant = TenantManager.generate_tenant_key()
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="quiet", creator_id="agent-x", tenant_key=tenant)
    # A normal (non-loop) post must NOT arm the directive.
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="hi",
        to_participant="agent-x",
        from_agent="orchestrator",
        tenant_key=tenant,
    )
    assert await comm.has_active_loop_directive(agent_id="agent-x", tenant_key=tenant) is False


# ---------------------------------------------------------------------------
# Mission composition: directive injected ONLY when armed + non-terminal
# ---------------------------------------------------------------------------


async def test_directive_injected_into_mission_when_armed(db_session):
    tenant = TenantManager.generate_tenant_key()
    job_id, agent_id = await _spawn_agent(db_session, tenant)
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="loop", creator_id="orchestrator", tenant_key=tenant)
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="loop until resolved",
        to_participant=agent_id,
        loop_directive=True,
        from_agent="orchestrator",
        tenant_key=tenant,
    )
    protocol = await _fetch_protocol(db_session, tenant, job_id)
    assert _DIRECTIVE_MARKER in protocol


async def test_directive_absent_when_not_armed(db_session):
    tenant = TenantManager.generate_tenant_key()
    job_id, _agent_id = await _spawn_agent(db_session, tenant)
    protocol = await _fetch_protocol(db_session, tenant, job_id)
    assert _DIRECTIVE_MARKER not in protocol


async def test_directive_absent_after_thread_closed(db_session):
    tenant = TenantManager.generate_tenant_key()
    job_id, agent_id = await _spawn_agent(db_session, tenant)
    await _seed_cht(db_session, tenant)
    comm = _comm(db_session)
    thread = await comm.create_thread(subject="loop", creator_id="orchestrator", tenant_key=tenant)
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="loop",
        to_participant=agent_id,
        loop_directive=True,
        from_agent="orchestrator",
        tenant_key=tenant,
    )
    assert _DIRECTIVE_MARKER in await _fetch_protocol(db_session, tenant, job_id)

    # Close the thread -> the directive must disappear from the next mission.
    await comm.post_to_thread(
        thread_id=thread["thread_id"],
        content="resolved",
        from_agent="orchestrator",
        set_status="closed",
        tenant_key=tenant,
    )
    assert _DIRECTIVE_MARKER not in await _fetch_protocol(db_session, tenant, job_id)
