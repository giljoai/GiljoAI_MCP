# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Shared helpers for the project service family.

Extracted from project_service.py (Sprint 002e) to eliminate cross-import
coupling where project_lifecycle_service and project_launch_service
imported ``_build_ws_project_data`` directly from project_service.
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob


logger = logging.getLogger(__name__)


def _build_ws_project_data(project) -> dict:
    """Build standardized project data dict for WebSocket broadcasts.

    Single source of truth for project data sent to frontend via
    WebSocket ``broadcast_project_update`` events. All project broadcast
    sites should use this helper to ensure a consistent field structure.

    Args:
        project: Project model instance (SQLAlchemy).

    Returns:
        Dict with the fields extracted by
        ``WebSocketManager.broadcast_project_update``.
    """
    return {
        "name": project.name,
        "description": project.description,
        "status": project.status,
        "mission": project.mission,
    }


async def mark_staging_complete(
    session,
    project,
    *,
    source: str,
    websocket_manager: Any | None = None,
    agent_count: int | None = None,
) -> bool:
    """Flip ``project.staging_status`` to ``'staging_complete'`` and emit WS event.

    Idempotent — single canonical implementation of the staging→implementation
    flag transition. Three call sites converge here:

    - ``mission_service.update_agent_mission`` (auto-flip when orchestrator
      persists a mission and sub-agents have been spawned).
    - ``job_completion_service.complete_job`` (orchestrator explicitly closes
      its staging session via ``complete_job``).
    - Historically ``message_routing_service`` (the broadcast magic — removed
      in this change).

    Args:
        session: Active SQLAlchemy AsyncSession. Caller is responsible for
            committing after this returns (we ``flush`` only, not ``commit``,
            so callers can batch the flip with their own writes).
        project: Project model instance (already loaded in ``session``).
        source: Free-text identifier of the caller (logged on flip and on
            idempotent no-op). Examples: ``"mission_service"``,
            ``"complete_job:staging_end"``.
        websocket_manager: Optional WebSocket manager. When provided AND the
            flag actually flipped, emits a ``project:staging_complete`` event
            to the tenant.
        agent_count: Optional sub-agent count to include in the WS payload
            (purely informational; the UI doesn't depend on it).

    Returns:
        True if the flag was flipped by this call. False if the project was
        already in ``staging_complete`` (idempotent no-op).
    """
    if project.staging_status == "staging_complete":
        logger.debug(
            "[STAGING_COMPLETE:%s] project=%s already complete — no-op",
            source,
            project.id,
        )
        return False

    project.staging_status = "staging_complete"
    project.updated_at = datetime.now(UTC)
    await session.flush()

    logger.info(
        "[STAGING_COMPLETE:%s] project=%s flag flipped",
        source,
        project.id,
    )

    if websocket_manager is not None:
        payload = {
            "project_id": str(project.id),
            "staging_status": "staging_complete",
        }
        if agent_count is not None:
            payload["agent_count"] = agent_count
        try:
            await websocket_manager.broadcast_to_tenant(
                tenant_key=project.tenant_key,
                event_type="project:staging_complete",
                data=payload,
            )
        except Exception as ws_error:  # noqa: BLE001 - WS resilience
            logger.warning(
                "[STAGING_COMPLETE:%s] WS broadcast failed: %s",
                source,
                ws_error,
            )

    return True


async def spawn_implementation_orchestrator(
    session,
    project_id: str,
    tenant_key: str,
) -> AgentExecution | None:
    """Find-or-spawn an impl-phase orchestrator execution (CE-0028c).

    Idempotent — safe to call multiple times. Three branches:

    1. An impl-phase execution already exists with ``status`` in
       ``('waiting', 'working')`` → return it. No write.
    2. The staging-phase execution is ``status='complete'`` and no impl
       execution exists yet → spawn a fresh ``project_phase='implementation'``,
       ``status='waiting'`` execution attached to the same ``AgentJob``,
       flush, return it.
    3. No orchestrator job exists for this project → return ``None``.
       Caller treats as a hard error (the project has no orchestrator).

    Why this exists: the Implement-button UI flow calls
    ``PATCH /api/agent-jobs/projects/{id}/launch-implementation`` (sets
    ``project.implementation_launched_at``) and then
    ``GET /api/v1/prompts/implementation/{id}`` (fetches the orch's launch
    prompt). The prompt endpoint filters orchestrator executions by
    ``status NOT IN ('complete', 'closed', 'decommissioned', 'failed')``.
    Post-CE-0026 the staging execution is ``'complete'`` at that point —
    if no impl execution exists, the prompt endpoint returns 404 and the
    play button silently fails. The CE-0026 spawn was wired only to the
    initial-launch endpoint (``POST /api/v1/projects/{id}/launch``), which
    the play button doesn't call. CE-0028c wires the spawn to the actual
    Implement-button path.

    Future direction (queued for CE-0029): pre-spawn the impl execution at
    staging-end inside ``_handle_staging_end`` instead of lazily here. The
    helper stays useful for idempotency on the endpoint, but the lazy-spawn
    branch becomes a fallback rather than the primary path.

    Args:
        session: Active SQLAlchemy AsyncSession. Caller commits; this helper
            only flushes so it can be batched into the caller's transaction
            (e.g., the endpoint commits timestamp + spawn together).
        project_id: Project UUID (string).
        tenant_key: Tenant key for isolation.

    Returns:
        The impl-phase ``AgentExecution`` (existing or newly created), or
        ``None`` if the project has no orchestrator job at all.
    """
    stmt = (
        select(AgentExecution)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            AgentJob.project_id == project_id,
            AgentExecution.tenant_key == tenant_key,
            AgentExecution.agent_display_name == "orchestrator",
            ~AgentExecution.status.in_(["decommissioned"]),
        )
    )
    execs = list((await session.execute(stmt)).scalars().all())

    if not execs:
        logger.warning(
            "[CE-0028c] spawn_implementation_orchestrator: no orchestrator job found for project %s",
            project_id,
        )
        return None

    # Branch 1: idempotent — any existing non-terminal orch exec is the
    # "current" orchestrator and serves the prompt endpoint's needs.
    # Includes both impl-phase (the canonical case) and staging-phase
    # (the orch is still in-flight; Implement-button shouldn't have been
    # clickable, but the helper stays safe to call).
    active = next(
        (e for e in execs if e.status in ("waiting", "working")),
        None,
    )
    if active:
        logger.debug(
            "[CE-0028c] spawn_implementation_orchestrator: active orch exec %s (status=%s, phase=%s) "
            "already exists for project %s",
            active.agent_id,
            active.status,
            getattr(active, "project_phase", None),
            project_id,
        )
        return active

    # Branch 2: anchor spawn to ANY complete orch exec. CE-0027 explicitly
    # tolerates a mislabeled project_phase column (legacy rows had the buggy
    # default 'implementation' on what was really a staging session). The
    # SPAWN trigger is status='complete', not phase='staging'. Matches the
    # CE-0027 simplification in project_launch_service.launch_project.
    complete_orch = next((e for e in execs if e.status == "complete"), None)
    if complete_orch is None:
        # No complete orch and no active orch — execs all in some odd state
        # (e.g., 'failed', 'closed'). Return the most-recent for the caller
        # to inspect; spawn would be invalid.
        logger.info(
            "[CE-0028c] spawn_implementation_orchestrator: no complete or active orch exec for project %s; "
            "returning latest (%s, status=%s)",
            project_id,
            execs[0].agent_id,
            execs[0].status,
        )
        return execs[0]

    impl_exec = AgentExecution(
        agent_id=str(uuid4()),
        job_id=complete_orch.job_id,
        tenant_key=tenant_key,
        agent_display_name="orchestrator",
        agent_name="orchestrator",
        status="waiting",
        progress=0,
        health_status="unknown",
        project_phase="implementation",
    )
    session.add(impl_exec)
    await session.flush()
    logger.info(
        "[CE-0028c] spawned implementation orchestrator execution %s for project %s (job %s)",
        impl_exec.agent_id,
        project_id,
        complete_orch.job_id,
    )
    return impl_exec
