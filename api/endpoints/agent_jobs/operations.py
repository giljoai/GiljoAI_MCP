"""
Agent Job Operations Endpoints - Handovers 0107, 0244b

Handles agent job operational controls:
- POST /api/jobs/{job_id}/cancel - Cancel agent job
- POST /api/jobs/{job_id}/force-fail - Force-fail agent job
- GET /api/jobs/{job_id}/health - Get job health metrics
- PATCH /api/jobs/{job_id}/mission - Update agent mission (Handover 0244b)

Operations use standalone functions from agent_job_manager module or direct database access.
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi import status as http_status

from src.giljo_mcp.agent_job_manager import force_fail_job, request_job_cancellation
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.repositories.agent_job_repository import AgentJobRepository
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .dependencies import get_db_manager
from .models import (
    CancelJobRequest,
    CancelJobResponse,
    ForceFailJobRequest,
    ForceFailJobResponse,
    JobHealthResponse,
    UpdateMissionRequest,
    UpdateMissionResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{job_id}/cancel", response_model=CancelJobResponse)
async def cancel_job(
    job_id: str,
    request: CancelJobRequest,
    current_user: User = Depends(get_current_active_user),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> CancelJobResponse:
    """
    Request graceful cancellation of an agent job (Handover 0107).

    Sets job status to "cancelling" and sends a high-priority cancel message
    to the agent, allowing it to clean up gracefully.

    Args:
        job_id: Job ID to cancel
        request: Cancel request with reason
        current_user: Authenticated user (from dependency)

    Returns:
        CancelJobResponse with success status and updated job details

    Raises:
        HTTPException 404: Job not found
        HTTPException 403: User not authorized (tenant mismatch)
        HTTPException 409: Job in invalid state for cancellation
        HTTPException 400: Invalid request
    """
    logger.debug(f"User {current_user.username} requesting cancellation of job {job_id}")

    try:
        # Call business logic function
        result = await request_job_cancellation(
            tenant_key=current_user.tenant_key,
            job_id=job_id,
            reason=request.reason,
            db_manager=db_manager,
        )

        # Return success response
        return CancelJobResponse(
            success=result["success"],
            job_id=result["job_id"],
            status=result["status"],
            message=result["message"],
        )

    except ValueError as e:
        error_msg = str(e)

        # Handle not found
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        # Handle terminal state (cannot cancel)
        if "cannot cancel" in error_msg.lower() or "terminal state" in error_msg.lower():
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_msg
            )

        # General validation error
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    except Exception as e:
        logger.error(f"Unexpected error canceling job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel job: {str(e)}"
        )


@router.post("/{job_id}/force-fail", response_model=ForceFailJobResponse)
async def force_fail_job_endpoint(
    job_id: str,
    request: ForceFailJobRequest,
    current_user: User = Depends(get_current_active_user),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> ForceFailJobResponse:
    """
    Force-fail an agent job without waiting for graceful shutdown (Handover 0107).

    Immediately marks job as failed. Use this when agent is unresponsive
    or cancellation request has timed out.

    Args:
        job_id: Job ID to force-fail
        request: Force-fail request with reason
        current_user: Authenticated user (from dependency)

    Returns:
        ForceFailJobResponse with success status and updated job details

    Raises:
        HTTPException 404: Job not found
        HTTPException 403: User not authorized (tenant mismatch)
        HTTPException 409: Job already failed
        HTTPException 400: Invalid request
    """
    logger.debug(f"User {current_user.username} force-failing job {job_id}")

    try:
        # Call business logic function
        result = await force_fail_job(
            tenant_key=current_user.tenant_key,
            job_id=job_id,
            reason=request.reason,
            db_manager=db_manager,
        )

        # Return success response
        return ForceFailJobResponse(
            success=result["success"],
            job_id=result["job_id"],
            status=result["status"],
            message=result["message"],
        )

    except ValueError as e:
        error_msg = str(e)

        # Handle not found
        if "not found" in error_msg.lower():
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=error_msg
            )

        # Handle already failed
        if "already failed" in error_msg.lower():
            raise HTTPException(
                status_code=http_status.HTTP_409_CONFLICT,
                detail=error_msg
            )

        # General validation error
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    except Exception as e:
        logger.error(f"Unexpected error force-failing job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to force-fail job: {str(e)}"
        )


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

    try:
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
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Job {job_id} not found"
            )

        # ORIGINAL QUERY (kept for reference):
        # stmt = select(AgentExecution).where(
        #     AgentExecution.tenant_key == current_user.tenant_key,
        #     AgentExecution.agent_id == job_id,
        # )
        # result = await session.execute(stmt)
        # execution = result.scalar_one_or_none()
        #
        # # Fallback to job_id if not found by agent_id
        # if not execution:
        #     stmt = select(AgentExecution).where(
        #         AgentExecution.tenant_key == current_user.tenant_key,
        #         AgentExecution.job_id == job_id,
        #     )
        #     result = await session.execute(stmt)
        #     execution = result.scalar_one_or_none()

        # Calculate minutes since last progress
        minutes_since_progress: Optional[float] = None
        is_stale = False

        if execution.last_progress_at:
            time_delta = datetime.now(timezone.utc) - execution.last_progress_at
            minutes_since_progress = time_delta.total_seconds() / 60.0

            # Job is stale if no progress in 10+ minutes and not in terminal state
            is_stale = (
                minutes_since_progress >= 10.0
                and execution.status not in ("complete", "failed", "cancelled", "decommissioned")
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

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Unexpected error getting health for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get job health: {str(e)}"
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

    try:
        # Initialize repository
        repo = AgentJobRepository(None)

        # Get AgentJob with tenant isolation (mission is stored on job, not execution)
        job = await repo.get_agent_job_by_job_id(
            session=session,
            tenant_key=current_user.tenant_key,
            job_id=job_id,
        )

        if not job:
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail=f"Agent job {job_id} not found"
            )

        # ORIGINAL QUERY (kept for reference):
        # stmt = select(AgentJob).where(
        #     AgentJob.tenant_key == current_user.tenant_key,
        #     AgentJob.job_id == job_id,
        # )
        # result = await session.execute(stmt)
        # job = result.scalar_one_or_none()

        # Update mission (stored on AgentJob, not AgentExecution)
        job.mission = request.mission

        await session.commit()
        await session.refresh(job)

        logger.info(
            f"Mission updated for job {job_id} by user {current_user.username}. "
            f"New length: {len(request.mission)} chars"
        )

        # Get current execution for WebSocket event
        current_execution = await repo.get_latest_execution_for_job(
            session=session,
            tenant_key=current_user.tenant_key,
            job_id=job_id,
        )

        # ORIGINAL QUERY (kept for reference):
        # exec_stmt = select(AgentExecution).where(
        #     AgentExecution.job_id == job_id,
        #     AgentExecution.tenant_key == current_user.tenant_key,
        # ).order_by(AgentExecution.instance_number.desc())
        # exec_result = await session.execute(exec_stmt)
        # current_execution = exec_result.scalar_one_or_none()

        # Emit WebSocket event for real-time updates
        from api.websocket_manager import manager as websocket_manager

        await websocket_manager.emit_to_tenant(
            current_user.tenant_key,
            "agent:mission_updated",
            {
                "job_id": job_id,
                "agent_type": current_execution.agent_type if current_execution else job.job_type,
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

    except HTTPException:
        # Re-raise HTTP exceptions
        raise

    except Exception as e:
        logger.error(f"Unexpected error updating mission for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update mission: {str(e)}"
        )
