# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Implementation-launch gate helpers for MissionService (BE-9073).

Verbatim split from ``mission_service.py`` to keep that module under the shrink-only
size budget. ``check_implementation_gate`` and ``is_chain_member`` take an explicit
``logger`` (mirrors the ``mission_assembly.py`` idiom) plus the already-fetched
``session``/``job`` objects and the service's ``repo``/``db_manager``/``tenant_manager``
handles — no new sessions are opened here. ``MissionService`` keeps thin back-compat
shims of unchanged name/signature that delegate here. Pure move, no behavior change.
Edition Scope: CE.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models import AgentJob
from giljo_mcp.schemas.service_responses import MissionResponse
from giljo_mcp.services.execution_mode_gate import (
    EXECUTION_MODE_NOT_SELECTED_MESSAGE,
    execution_mode_selected,
)


async def check_implementation_gate(
    logger: Any,
    session: AsyncSession,
    job: AgentJob,
    job_id: str,
    tenant_key: str,
    *,
    repo: Any,
    db_manager: Any,
    tenant_manager: Any,
) -> tuple[Any, MissionResponse | None]:
    """Check implementation phase gate.

    Returns:
        Tuple of (project, gate_response). gate_response is non-None if blocked.
    """
    # BE-6221c: the block message is the module constant owned by mission_service.py
    # (imported here, not defined here, so `from giljo_mcp.services.mission_service
    # import _CHAIN_WORKER_STAGING_BLOCK_MESSAGE` keeps resolving for existing
    # importers). Deferred import: mission_service.py imports this module at load
    # time, so a module-level import here would be circular.
    from giljo_mcp.services.mission_service import _CHAIN_WORKER_STAGING_BLOCK_MESSAGE

    project = await repo.get_project_by_id(session, tenant_key, job.project_id)

    # NULL-state gate: no mission until an execution mode is chosen. Backstop
    # for out-of-band / legacy rows (normal flow sets the mode at staging).
    # Fires before the implementation-launch gate and before any protocol is
    # rendered, so a NULL never reaches the HO1020 render fail-safes.
    if project is not None and not execution_mode_selected(project):
        return project, MissionResponse(
            job_id=job_id,
            blocked=True,
            mission=None,
            full_protocol=None,
            error="BLOCKED: No execution mode selected",
            user_instruction=EXECUTION_MODE_NOT_SELECTED_MESSAGE,
        )

    if project and project.implementation_launched_at is None:
        if job.job_type == "orchestrator":
            # §14 deadlock-breaker (CHAIN_ARCHITECTURE.md): a released chain
            # sub-orchestrator is NEVER gated. The conductor's spawn IS the start —
            # there is no per-project "wait for a go" step on either side. Fall
            # through (return None) so get_agent_mission renders this sub-orch's
            # COMBINED CH_SUB_ORCHESTRATOR protocol immediately and it starts working
            # (the prior BLOCKED response hid the mission behind a gate the
            # orchestrator could never open, while the conductor waited for a
            # staging_complete it could never produce). Strictly chain-gated: a solo
            # project (no active run) keeps the original human-gate message below
            # byte-identical (Deletion Test on the SOLO gate holds).
            chain_member = await is_chain_member(
                logger, session, job.project_id, tenant_key, db_manager=db_manager, tenant_manager=tenant_manager
            )
            # BE-9069 (Defect A): the chain exemption releases a sub-orchestrator DURING
            # its OWN staging. A chain member reaches staging_status='staging_complete'
            # and implementation_launched_at ATOMICALLY at its staging-end (job_completion_
            # service.py:1042 mark_staging_complete + 1068-1071 stamp, one complete_job txn;
            # pinned by test_be6206 test 3), so a chain member is NEVER 'staging_complete'
            # while launch is NULL. That exact state (staging_complete + launch NULL) is
            # UNIQUELY a SOLO project parked at the human Implement gate; mere enrollment in
            # a freshly minted (pending, zero-conductor-activity) run must NOT un-gate it
            # (BE-6115a: a spawned/staging agent cannot self-unlock implementation). A
            # genuinely released member (staging_status still 'staged'/NULL) still crosses.
            if chain_member and project.staging_status != "staging_complete":
                return project, None
            return project, MissionResponse(
                job_id=job_id,
                blocked=True,
                mission=None,
                full_protocol=None,
                error="BLOCKED: Implementation phase not launched",
                user_instruction=(
                    "Staging is complete but implementation has not been launched. "
                    "Return to the dashboard and click Implement, then start (or paste) your "
                    "orchestrator prompt in your agent session (terminal, desktop, or web tab)."
                ),
            )
        # BE-6213 P1: a WORKER spawned during a chain sub-orch's staging is
        # inert until that sub-orch's staging-end stamps implementation_launched_at.
        # The chain has no human Implement button, so reuse is_chain_member (the
        # same predicate the orchestrator branch uses above) to hand it a
        # chain-worded message instead of the dead-end "click Implement" wording.
        # Solo workers (chain_member False) keep the legacy message byte-identical.
        chain_member = await is_chain_member(
            logger, session, job.project_id, tenant_key, db_manager=db_manager, tenant_manager=tenant_manager
        )
        if chain_member:
            return project, MissionResponse(
                job_id=job_id,
                blocked=True,
                mission=None,
                full_protocol=None,
                error="BLOCKED: Chain orchestrator still staging",
                user_instruction=_CHAIN_WORKER_STAGING_BLOCK_MESSAGE,
            )
        return project, MissionResponse(
            job_id=job_id,
            blocked=True,
            mission=None,
            full_protocol=None,
            error="BLOCKED: Implementation phase not started by user",
            user_instruction=(
                "Your mission is blocked. The user must click the 'Implement' "
                "button in the GiljoAI dashboard before you can receive your mission. "
                "Please inform your user of this requirement and wait."
            ),
        )

    return project, None


async def is_chain_member(
    logger: Any,
    session: AsyncSession,
    project_id: Any,
    tenant_key: str,
    *,
    db_manager: Any,
    tenant_manager: Any,
) -> bool:
    """Return True if this project belongs to an ACTIVE sequential chain (BE-6196).

    Used by the implementation gate to pick the chain-aware blocked message (the
    conductor crosses the gate automatically) over the solo "click Implement" one.
    Best-effort: a resolution failure returns False so the gate falls back to the
    solo message and mission delivery is NEVER broken by chain lookup.
    """
    try:
        from giljo_mcp.services.sequence_run_service import SequenceRunService

        svc = SequenceRunService(
            db_manager=db_manager,
            tenant_manager=tenant_manager,
            session=session,
        )
        run = await svc.find_active_run_for_project(project_id=str(project_id), tenant_key=tenant_key)
        return run is not None
    except Exception:  # noqa: BLE001 - best-effort chain detection; never block the gate
        logger.warning("[BE-6196] chain-member check failed (non-fatal); falling back to solo gate")
        return False
