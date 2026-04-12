# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Agent Job Progress Endpoints - Handover 0124

Handles agent job progress reporting:
- POST /api/agent-jobs/{job_id}/progress - Report job progress

All operations use OrchestrationService (no direct DB access).
"""

import logging

from fastapi import APIRouter, Depends

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.utils.log_sanitizer import sanitize

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
        "User %s reporting progress for job %s: %s%%",
        sanitize(current_user.username),
        sanitize(job_id),
        progress_request.progress_percent,
    )

    # Build progress data dict for legacy format
    progress_data = {
        "percent": progress_request.progress_percent,  # Service expects "percent", not "progress_percent"
        "message": progress_request.status_message,
        "current_step": progress_request.current_task,
    }

    # Service raises ValidationError, ResourceNotFoundError, or OrchestrationError
    # Caught by global exception handler
    result = await orchestration_service.report_progress(
        job_id=job_id,
        tenant_key=current_user.tenant_key,
        progress=progress_data,  # Fixed: parameter name is "progress", not "progress_data"
    )

    logger.info(
        "Reported progress for job %s: %s%% for tenant %s",
        sanitize(job_id),
        progress_request.progress_percent,
        sanitize(current_user.tenant_key),
    )

    return ProgressReportResponse(
        job_id=job_id,
        progress_percent=progress_request.progress_percent,
        message=result.get("message", "Progress reported successfully"),
    )
