# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Agent Job Operations Endpoints - Handovers 0107, 0244b

Handles agent job operational controls:
- GET /api/jobs/{job_id}/health - Get job health metrics
- PATCH /api/jobs/{job_id}/mission - Update agent mission (Handover 0244b)

Sprint 003c: Mission update routed through MissionService (no direct session.commit).
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.models import User
from giljo_mcp.services.job_query_service import JobQueryService
from giljo_mcp.services.orchestration_service import OrchestrationService
from giljo_mcp.utils.log_sanitizer import sanitize

from .dependencies import get_job_query_service, get_orchestration_service
from .models import (
    JobHealthResponse,
    UpdateMissionRequest,
    UpdateMissionResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{job_id}/health", response_model=JobHealthResponse)
async def get_job_health(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
    job_query_service: JobQueryService = Depends(get_job_query_service),
) -> JobHealthResponse:
    """
    Get health metrics for an agent job (Handover 0107).

    Returns health information including status, progress, timestamps,
    and staleness detection.

    Args:
        job_id: Job ID to check health
        current_user: Authenticated user (from dependency)

    Returns:
        JobHealthResponse with health metrics

    Raises:
        HTTPException 404: Job not found
        HTTPException 403: User not authorized (tenant mismatch)
    """
    logger.debug("User %s checking health of job %s", sanitize(current_user.username), sanitize(job_id))

    # Get execution with tenant isolation (job_id could be agent_id or job_id)
    # Try agent_id first (new model)
    execution = await job_query_service.get_execution_by_agent_id(
        tenant_key=current_user.tenant_key,
        agent_id=job_id,
        session=session,
    )

    # Fallback to job_id if not found by agent_id
    if not execution:
        execution = await job_query_service.get_execution_by_job_id(
            tenant_key=current_user.tenant_key,
            job_id=job_id,
            session=session,
        )

    if not execution:
        raise ResourceNotFoundError(f"Job {job_id} not found")
    minutes_since_progress: float | None = None
    is_stale = False

    if execution.last_progress_at:
        time_delta = datetime.now(UTC) - execution.last_progress_at
        minutes_since_progress = time_delta.total_seconds() / 60.0

        # Job is stale if no progress in 10+ minutes and not in terminal state
        is_stale = minutes_since_progress >= 10.0 and execution.status not in (
            "complete",
            "silent",
            "decommissioned",
        )

    # Return health metrics
    return JobHealthResponse(
        job_id=execution.job_id,
        status=execution.status,
        last_progress_at=execution.last_progress_at,
        last_message_check_at=execution.last_message_check_at,
        minutes_since_progress=minutes_since_progress,
        is_stale=is_stale,
    )


@router.patch("/{job_id}/mission")
async def update_agent_mission(
    job_id: str,
    request: UpdateMissionRequest,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
    session: AsyncSession = Depends(get_db_session),
    job_query_service: JobQueryService = Depends(get_job_query_service),
) -> UpdateMissionResponse:
    """
    Update agent mission with validation and WebSocket broadcast (Handover 0244b).

    Sprint 003c: Write routed through MissionService (no direct session.commit).

    Args:
        job_id: Job ID to update
        request: Update request with new mission text
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for mission updates
        session: Database session (read-only, for WebSocket context)

    Returns:
        UpdateMissionResponse with success status and updated mission

    Raises:
        ResourceNotFoundError: Job not found
        HTTPException 422: Validation error (empty or too long)
    """
    logger.debug("User %s updating mission for job %s", sanitize(current_user.username), sanitize(job_id))

    # Route write through OrchestrationService facade (handles commit + WebSocket)
    result = await orchestration_service.update_agent_mission(
        job_id=job_id,
        tenant_key=current_user.tenant_key,
        mission=request.mission,
    )

    logger.info(
        "Mission updated for job %s by user %s. New length: %d chars",
        sanitize(job_id),
        sanitize(current_user.username),
        result.mission_length,
    )

    # Emit detailed WebSocket event for frontend (agent display name + full mission)
    job = await job_query_service.get_agent_job_by_job_id(
        tenant_key=current_user.tenant_key,
        job_id=job_id,
        session=session,
    )
    current_execution = await job_query_service.get_latest_execution_for_job(
        tenant_key=current_user.tenant_key,
        job_id=job_id,
        session=session,
    )

    from api.websocket_manager import manager as websocket_manager

    await websocket_manager.emit_to_tenant(
        current_user.tenant_key,
        "agent:mission_updated",
        {
            "job_id": job_id,
            "agent_display_name": current_execution.agent_display_name
            if current_execution
            else (job.job_type if job else "unknown"),
            "agent_name": current_execution.agent_name if current_execution else None,
            "mission": request.mission,
            "project_id": str(job.project_id) if job and job.project_id else None,
        },
    )

    return UpdateMissionResponse(
        success=True,
        job_id=job_id,
        mission=request.mission,
    )
