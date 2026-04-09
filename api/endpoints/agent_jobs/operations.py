# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Agent Job Operations Endpoints - Handovers 0107, 0244b

Handles agent job operational controls:
- GET /api/jobs/{job_id}/health - Get job health metrics
- PATCH /api/jobs/{job_id}/mission - Update agent mission (Handover 0244b)

Operations use standalone functions from agent_job_manager module or direct database access.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models import User
from src.giljo_mcp.repositories.agent_job_repository import AgentJobRepository

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
    logger.debug(f"User {current_user.username} checking health of job {job_id}")

    # Initialize repository
    repo = AgentJobRepository(None)  # Repository doesn't use db_manager for queries

    # Get execution with tenant isolation (job_id could be agent_id or job_id)
    # Try agent_id first (new model)
    execution = await repo.get_execution_by_agent_id(
        session=session,
        tenant_key=current_user.tenant_key,
        agent_id=job_id,
    )

    # Fallback to job_id if not found by agent_id
    if not execution:
        execution = await repo.get_execution_by_job_id(
            session=session,
            tenant_key=current_user.tenant_key,
            job_id=job_id,
        )

    if not execution:
        raise ResourceNotFoundError(f"Job {job_id} not found")
    minutes_since_progress: Optional[float] = None
    is_stale = False

    if execution.last_progress_at:
        time_delta = datetime.now(timezone.utc) - execution.last_progress_at
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
    session: AsyncSession = Depends(get_db_session),
) -> UpdateMissionResponse:
    """
    Update agent mission with validation and WebSocket broadcast (Handover 0244b).

    Allows users to modify the mission/instructions for an agent job.
    The mission is the task instructions created by the orchestrator.

    Args:
        job_id: Job ID to update
        request: Update request with new mission text
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        UpdateMissionResponse with success status and updated mission

    Raises:
        HTTPException 404: Job not found
        HTTPException 403: User not authorized (tenant mismatch)
        HTTPException 422: Validation error (empty or too long)
        HTTPException 500: Internal server error
    """
    logger.debug(f"User {current_user.username} updating mission for job {job_id}")

    # Initialize repository
    repo = AgentJobRepository(None)

    # Get AgentJob with tenant isolation (mission is stored on job, not execution)
    job = await repo.get_agent_job_by_job_id(
        session=session,
        tenant_key=current_user.tenant_key,
        job_id=job_id,
    )

    if not job:
        raise ResourceNotFoundError(f"Agent job {job_id} not found")
    job.mission = request.mission

    await session.commit()
    await session.refresh(job)

    logger.info(
        f"Mission updated for job {job_id} by user {current_user.username}. New length: {len(request.mission)} chars"
    )

    # Get current execution for WebSocket event
    current_execution = await repo.get_latest_execution_for_job(
        session=session,
        tenant_key=current_user.tenant_key,
        job_id=job_id,
    )

    # Emit WebSocket event for real-time updates
    from api.websocket_manager import manager as websocket_manager

    await websocket_manager.emit_to_tenant(
        current_user.tenant_key,
        "agent:mission_updated",
        {
            "job_id": job_id,
            "agent_display_name": current_execution.agent_display_name if current_execution else job.job_type,
            "agent_name": current_execution.agent_name if current_execution else None,
            "mission": job.mission,
            "project_id": job.project_id,
        },
    )

    # Return success response
    return UpdateMissionResponse(
        success=True,
        job_id=job_id,
        mission=job.mission,
    )
