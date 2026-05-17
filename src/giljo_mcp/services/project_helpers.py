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


# CE-0032: spawn_implementation_orchestrator removed. Under the single-
# orchestrator-entity model the same AgentExecution row carries the
# orchestrator across the staging→implementation boundary; there is never a
# second exec to spawn. job_completion_service.complete_job leaves the row at
# status='waiting' at staging-end (see _apply_completion_status), and the
# orch's first get_agent_mission call in the impl session flips it back to
# 'working' via existing logic in mission_service.py:174.
