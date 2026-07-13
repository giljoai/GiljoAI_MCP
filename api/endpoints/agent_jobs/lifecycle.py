# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Agent Job Lifecycle Endpoints - Handover 0124

Handles agent job lifecycle operations:
- POST /api/agent-jobs/spawn - Spawn new agent job

All operations use OrchestrationService (no direct DB access).

BE-9143: the registered-but-dead /{job_id}/complete and /{job_id}/error routes
were retired (no remaining caller — agents complete/error via the MCP tools that
dispatch in-process, never through these REST mirrors).
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency
from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.models import User
from giljo_mcp.services.orchestration_service import OrchestrationService
from giljo_mcp.utils.log_sanitizer import sanitize

from .dependencies import get_orchestration_service
from .models import (
    SpawnAgentRequest,
    SpawnAgentResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/spawn", response_model=SpawnAgentResponse, status_code=status.HTTP_201_CREATED)
async def spawn_job(
    request: SpawnAgentRequest,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
) -> SpawnAgentResponse:
    """
    Spawn a new agent job.

    Uses OrchestrationService to create agent job with thin client architecture.
    Broadcasts WebSocket event for real-time UI updates.

    Args:
        request: Spawn request with agent details
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)
        ws_dep: WebSocket dependency for broadcasting (from dependency)

    Returns:
        SpawnAgentResponse with job ID and prompt

    Raises:
        HTTPException 403: User not authorized
        HTTPException 400: Invalid request or spawn failed
    """
    logger.debug(
        "User %s spawning agent job: %s", sanitize(current_user.username), sanitize(request.agent_display_name)
    )

    # Permission check - only admins can spawn agents
    if current_user.role != "admin":
        logger.warning(
            "User %s (role=%s) attempted to spawn agent", sanitize(current_user.username), sanitize(current_user.role)
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required to spawn agents")

    result = await orchestration_service.spawn_job(
        agent_display_name=request.agent_display_name,
        agent_name=request.agent_name or request.agent_display_name,
        mission=request.mission,
        project_id=request.project_id,
        tenant_key=current_user.tenant_key,
        parent_job_id=request.parent_job_id,
        context_chunks=request.context_chunks,
    )

    # Broadcast WebSocket event for real-time UI
    # NOTE: OrchestrationService already broadcasts agent:created, but we broadcast again
    # to ensure the endpoint's caller gets the event even if the service broadcast failed.
    # Handover 0457: Include execution_id for frontend Map key consistency
    # 0731d: OrchestrationService returns SpawnResult typed model
    try:
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="agent:created",
            data={
                "project_id": request.project_id,
                "execution_id": result.execution_id,  # Handover 0457: Unique row ID for frontend Map key
                "agent_id": result.agent_id,  # Handover 0457: Executor UUID
                "job_id": result.job_id,
                "agent_display_name": request.agent_display_name,
                "agent_name": request.agent_name or request.agent_display_name,
                "status": "waiting",
                "mission": request.mission,  # Handover 0464: Include mission for UI display
            },
        )
        logger.info("Agent spawn broadcasted: %s", sanitize(str(result.job_id)))
    except Exception as _exc:  # Broad catch: API boundary, converts to HTTP error
        logger.exception("Failed to broadcast agent spawn event")
        # Non-critical - continue without broadcast

    logger.info("Spawned agent job %s for tenant %s", sanitize(str(result.job_id)), sanitize(current_user.tenant_key))

    return SpawnAgentResponse(
        success=True,
        job_id=result.job_id,
        agent_prompt=result.agent_prompt,
        mission_stored=result.mission_stored,
        thin_client=result.thin_client,
    )
