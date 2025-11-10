"""
Agent Job Progress Endpoints - Handover 0124

Handles agent job progress reporting:
- POST /api/agent-jobs/{job_id}/progress - Report job progress

All operations use OrchestrationService (no direct DB access).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService

from .dependencies import get_orchestration_service
from .models import ProgressReportRequest, ProgressReportResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{job_id}/progress", response_model=ProgressReportResponse)
async def report_progress(
    job_id: str,
    progress_request: ProgressReportRequest,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> ProgressReportResponse:
    """
    Report job progress.

    Updates job progress percentage and status message.
    Useful for long-running agents to report incremental progress.

    Args:
        job_id: Job ID to report progress for
        progress_request: Progress details (percent, message, current task)
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)

    Returns:
        ProgressReportResponse with updated progress

    Raises:
        HTTPException 404: Job not found
        HTTPException 400: Invalid progress data
    """
    logger.debug(
        f"User {current_user.username} reporting progress for job {job_id}: "
        f"{progress_request.progress_percent}%"
    )

    # Build progress data
    progress_data = {
        "progress_percent": progress_request.progress_percent,
        "status_message": progress_request.status_message,
        "current_task": progress_request.current_task
    }

    # Report progress via OrchestrationService
    result = await orchestration_service.report_progress(
        job_id=job_id,
        tenant_key=current_user.tenant_key,
        progress_data=progress_data
    )

    # Check for errors
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(
        f"Reported progress for job {job_id}: {progress_request.progress_percent}% "
        f"for tenant {current_user.tenant_key}"
    )

    return ProgressReportResponse(
        job_id=job_id,
        progress_percent=progress_request.progress_percent,
        message=result.get("message", "Progress reported successfully")
    )
