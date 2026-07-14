# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6211e — execution-mode bleed: own-worker wait gated on is_subagent_render +
conductor event-wake on a chain member closeout.

Part 1 (pure-string, the failing layer = the rendered wake block):
  In a CLI subagent mode the orchestrator's spawn call (Task / spawn_agent / @agent)
  BLOCKS and returns the worker result inline, so the wake block must tell it to call
  get_agent_result immediately and NEVER sleep-poll its OWN workers — while keeping a
  cross-terminal receive_messages note. The multi_terminal generic wake block is
  unchanged (byte-identical), and an unregistered subagent CLI fails safe to the
  subagent-generic block (never the multi_terminal one).

Part 2 (DB, the failing layer = the member-status writer):
  mark_chain_member_status, after the terminal "completed" write, best-effort
  event-wakes the run's conductor by REUSING reactivate_job (additive to the
  wake_in_minutes poll). A blocked conductor resumes; a sleeping/absent conductor is a
  swallowed no-op that never fails the closeout; an in-flight ("implementing") status
  never fires the wake.

DB tests use the db_session fixture (TransactionalTestContext). No module-level mutable
state, no ordering deps. Parallel-safe under xdist. Edition Scope: CE.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.sequence_runs import SequenceRun
from giljo_mcp.services.project_helpers import mark_chain_member_status
from giljo_mcp.services.protocol_sections.agent_lifecycle import _build_wake_pattern
from giljo_mcp.tenant import TenantManager


# --------------------------------------------------------------------------------------
# Part 1 — own-worker wait block branches on is_subagent_render (pure string)
# --------------------------------------------------------------------------------------

_SUBAGENT_TOOLS = ("claude-code", "codex", "gemini", "antigravity")


def _wake(execution_mode: str) -> str:
    return _build_wake_pattern(execution_mode, executor_id="EXEC-1", tenant_key="TK-1")


def test_subagent_wake_blocks_use_inline_get_agent_result_not_sleep_poll() -> None:
    """Every registered subagent wake block tells the orchestrator its spawn BLOCKS and
    returns inline → call get_agent_result, never sleep-poll its own workers."""
    for mode in _SUBAGENT_TOOLS:
        block = _wake(mode)
        assert "get_agent_result" in block, f"{mode}: must point at get_agent_result for own workers"
        assert "BLOCKS" in block, f"{mode}: must state the spawn call BLOCKS / returns inline"
        assert "do NOT" in block and "sleep" in block, f"{mode}: must forbid sleep-polling own workers"
        # The old wrong prose ("Sleep-and-check pattern (when waiting for agents)") is gone.
        assert "Sleep-and-check pattern (when waiting for agents)" not in block


def test_subagent_wake_blocks_keep_cross_terminal_receive_messages_note() -> None:
    """Own workers return inline, but cross-terminal peers still reach the orchestrator by
    message — every subagent block keeps the cross-terminal drain note.

    BE-9012d: the bus (receive_messages) is retired in favor of the Hub
    (get_thread_history on the orchestrator's coordination thread)."""
    for mode in _SUBAGENT_TOOLS:
        block = _wake(mode)
        assert "get_thread_history" in block, f"{mode}: must keep the cross-terminal get_thread_history note"


def test_multi_terminal_wake_block_is_unchanged_and_carries_no_own_worker_inline_prose() -> None:
    """The multi_terminal generic block stays human-mediated: no get_agent_result own-worker
    inline prose leaks into it (byte-identical render is locked by test_be6209f's golden)."""
    block = _wake("multi_terminal")
    assert "CONSTELLATION: MULTI-TERMINAL" in block
    assert "get_agent_result" not in block
    assert "The user mediates between sessions." in block


def test_unregistered_subagent_cli_fails_safe_to_subagent_generic_not_multi_terminal() -> None:
    """An unknown future subagent CLI gets the subagent-generic inline block,
    NEVER the multi_terminal human-mediated block (HO1020 fail-safe)."""
    for mode in ("some_future_cli",):
        block = _wake(mode)
        assert "get_agent_result" in block, f"{mode}: unknown subagent must get the inline-return contract"
        assert "CONSTELLATION: MULTI-TERMINAL" not in block, f"{mode}: must NOT leak the multi_terminal block"
        assert "The user mediates between sessions." not in block


def test_antigravity_has_dedicated_wake_block() -> None:
    """TSK-6210: antigravity now has its own CH3 dispatch block, not the generic fallback."""
    block = _wake("antigravity")
    assert "CONSTELLATION: ANTIGRAVITY CLI" in block
    assert "get_agent_result" in block
    assert "BLOCKS" in block
    assert "do NOT" in block and "sleep" in block
    assert "get_thread_history" in block  # BE-9012d: bus retired, Hub replaces it
    assert "CONSTELLATION: MULTI-TERMINAL" not in block
    assert "The user mediates between sessions." not in block


# --------------------------------------------------------------------------------------
# Part 2 — conductor event-wake on a member closeout (DB)
# --------------------------------------------------------------------------------------

pytestmark = pytest.mark.asyncio


async def _seed_run(
    session: AsyncSession,
    tenant_key: str,
    *,
    resolved_order: list[str],
    conductor_agent_id: str | None,
    project_statuses: dict[str, str] | None = None,
) -> str:
    run_id = str(uuid.uuid4())
    run = SequenceRun(
        id=run_id,
        tenant_key=tenant_key,
        project_ids=resolved_order,
        resolved_order=resolved_order,
        current_index=0,
        execution_mode="claude_code_cli",
        status="running",
        review_policy="per_card",
        project_statuses=project_statuses or {},
        conductor_agent_id=conductor_agent_id,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    session.add(run)
    session.info["tenant_key"] = tenant_key
    await session.flush()
    return run_id


async def _seed_blocked_conductor(session: AsyncSession, tenant_key: str, conductor_agent_id: str) -> str:
    """Mint a project-less conductor whose execution is BLOCKED (reactivatable)."""
    job_id = str(uuid.uuid4())
    session.add(
        AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=None,  # project-less conductor
            mission="drive the chain",
            job_type="orchestrator",
            status="completed",
            job_metadata={},
        )
    )
    session.add(
        AgentExecution(
            agent_id=conductor_agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="conductor",
            agent_name="orchestrator",
            status="blocked",
            health_status="unknown",
            project_phase="implementation",
            started_at=datetime.now(UTC),
            completed_at=datetime.now(UTC),
        )
    )
    await session.flush()
    return job_id


async def _get_execution(session: AsyncSession, tenant_key: str, agent_id: str) -> AgentExecution:
    from giljo_mcp.repositories.agent_job_repository import AgentJobRepository

    repo = AgentJobRepository(None)
    execution = await repo.get_execution_by_agent_id(session, tenant_key, agent_id)
    assert execution is not None
    return execution


async def test_member_completed_event_wakes_blocked_conductor(db_session: AsyncSession) -> None:
    """A member closeout (status="completed") reactivates a blocked conductor:
    execution blocked→working, job completed→active. AND the member status is written."""
    tenant = TenantManager.generate_tenant_key()
    p0, p1 = str(uuid.uuid4()), str(uuid.uuid4())
    conductor_agent_id = str(uuid.uuid4())
    await _seed_run(
        db_session,
        tenant,
        resolved_order=[p0, p1],
        conductor_agent_id=conductor_agent_id,
        project_statuses={p0: "running"},
    )
    job_id = await _seed_blocked_conductor(db_session, tenant, conductor_agent_id)

    wrote = await mark_chain_member_status(
        db_manager=None,
        tenant_manager=TenantManager(),
        project_id=p0,
        tenant_key=tenant,
        status="completed",
        test_session=db_session,
    )
    assert wrote is True

    execution = await _get_execution(db_session, tenant, conductor_agent_id)
    assert execution.status == "working", "blocked conductor must be reactivated on the member closeout"

    from giljo_mcp.repositories.agent_job_repository import AgentJobRepository

    job = await AgentJobRepository(None).get_agent_job_by_job_id(db_session, tenant, job_id)
    assert job is not None and job.status == "active", "conductor job completed→active on reactivation"


async def test_member_completed_with_absent_conductor_is_non_fatal(db_session: AsyncSession) -> None:
    """A run whose conductor has no execution (or is not blocked) still writes the member
    status and returns True — the event-wake is a swallowed no-op, never failing closeout."""
    tenant = TenantManager.generate_tenant_key()
    p0 = str(uuid.uuid4())
    # conductor_agent_id present on the run, but NO matching execution seeded.
    await _seed_run(
        db_session,
        tenant,
        resolved_order=[p0],
        conductor_agent_id=str(uuid.uuid4()),
        project_statuses={p0: "running"},
    )

    wrote = await mark_chain_member_status(
        db_manager=None,
        tenant_manager=TenantManager(),
        project_id=p0,
        tenant_key=tenant,
        status="completed",
        test_session=db_session,
    )
    assert wrote is True  # closeout side-effect succeeded despite the no-op wake


async def test_in_flight_status_does_not_event_wake_conductor(db_session: AsyncSession) -> None:
    """A non-terminal member status ("implementing") must NOT fire the event-wake: a
    blocked conductor stays blocked (only a CLOSEOUT wakes it)."""
    tenant = TenantManager.generate_tenant_key()
    p0 = str(uuid.uuid4())
    conductor_agent_id = str(uuid.uuid4())
    await _seed_run(
        db_session,
        tenant,
        resolved_order=[p0],
        conductor_agent_id=conductor_agent_id,
        project_statuses={p0: "running"},
    )
    await _seed_blocked_conductor(db_session, tenant, conductor_agent_id)

    wrote = await mark_chain_member_status(
        db_manager=None,
        tenant_manager=TenantManager(),
        project_id=p0,
        tenant_key=tenant,
        status="implementing",
        test_session=db_session,
    )
    assert wrote is True

    execution = await _get_execution(db_session, tenant, conductor_agent_id)
    assert execution.status == "blocked", "in-flight status must not reactivate the conductor"
