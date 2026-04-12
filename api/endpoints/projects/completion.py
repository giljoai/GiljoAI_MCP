# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Project Completion Endpoints - Handover 0125

Handles project completion operations:
- GET /{project_id}/can-close - Evaluate closeout readiness
- POST /{project_id}/generate-closeout - Generate closeout prompt/checklist
- POST /{project_id}/complete - Complete project
- POST /{project_id}/close-out - Close out project (decommission agents)
- POST /{project_id}/continue-working - Resume work on project

All operations use ProjectService.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas.prompt import (
    ProjectCanCloseResponse,
    ProjectCloseoutDataResponse,
    ProjectCloseoutPromptResponse,
    ProjectCompleteRequest,
    ProjectCompleteResponse,
)
from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.utils.log_sanitizer import sanitize

from .dependencies import get_project_service
from .models import ContinueWorkingResponse, ProjectCloseOutResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get(
    "/{project_id}/can-close",
    response_model=ProjectCanCloseResponse,
    summary="Check whether a project can be closed",
    tags=["Projects"],
)
async def can_close_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectCanCloseResponse:
    """
    Evaluate whether a project is ready for closeout based on agent status.
    """
    logger.info("User %s checking can-close for project %s", sanitize(current_user.username), sanitize(project_id))

    # Service raises exceptions on error, returns CanCloseResult typed model
    result = await project_service.can_close_project(project_id=project_id, tenant_key=current_user.tenant_key)

    return ProjectCanCloseResponse(
        can_close=result.can_close,
        summary=result.summary,
        all_agents_finished=result.all_agents_finished,
        agent_statuses=result.agent_statuses,
    )


@router.post(
    "/{project_id}/generate-closeout",
    response_model=ProjectCloseoutPromptResponse,
    summary="Generate closeout prompt and checklist",
    tags=["Projects"],
)
async def generate_closeout_prompt(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectCloseoutPromptResponse:
    """
    Generate closeout prompt and checklist for project completion.
    """
    logger.info(
        "User %s generating closeout prompt for project %s", sanitize(current_user.username), sanitize(project_id)
    )

    # Service raises exceptions on error, returns CloseoutPromptResult typed model
    result = await project_service.generate_closeout_prompt(project_id=project_id, tenant_key=current_user.tenant_key)

    return ProjectCloseoutPromptResponse(
        prompt=result.prompt,
        checklist=result.checklist,
        project_name=result.project_name,
        agent_summary=result.agent_summary,
    )


@router.post(
    "/{project_id}/complete",
    response_model=ProjectCompleteResponse,
    summary="Complete project and update 360 Memory",
    tags=["Projects"],
)
async def complete_project(
    project_id: str,
    request: ProjectCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectCompleteResponse:
    """
    Complete project and update product's 360 Memory with learnings.
    """
    logger.info("User %s completing project %s", sanitize(current_user.username), sanitize(project_id))

    if not request.confirm_closeout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must confirm closeout (confirm_closeout=True)",
        )

    # Service raises exceptions on error
    result = await project_service.complete_project(
        project_id=project_id,
        summary=request.summary,
        key_outcomes=request.key_outcomes,
        decisions_made=request.decisions_made,
        tenant_key=current_user.tenant_key,
    )

    return ProjectCompleteResponse(
        success=True,
        completed_at=datetime.now(timezone.utc).isoformat(),
        memory_updated=result.memory_updated,
        sequence_number=result.sequence_number,
        git_commits_count=result.git_commits_count,
    )


@router.get(
    "/{project_id}/closeout",
    response_model=ProjectCloseoutDataResponse,
    summary="Get project closeout data (checklist + prompt)",
)
async def get_project_closeout_data(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectCloseoutDataResponse:
    """
    Get dynamic closeout checklist and prompt for project completion.

    Called by CloseoutModal.vue when the user initiates project closeout.
    """
    logger.info("User %s fetching closeout data for project %s", sanitize(current_user.username), sanitize(project_id))

    # Service raises exceptions on error, returns CloseoutData typed model
    result = await project_service.get_closeout_data(project_id=project_id)

    return ProjectCloseoutDataResponse(
        project_id=result.project_id,
        project_name=result.project_name,
        agent_count=result.agent_count,
        completed_agents=result.completed_agents,
        blocked_agents=result.blocked_agents,
        silent_agents=result.silent_agents,
        all_agents_complete=result.all_agents_complete,
        has_blocked_agents=result.has_blocked_agents,
    )


@router.post("/{project_id}/close-out", response_model=ProjectCloseOutResponse)
async def close_out_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectCloseOutResponse:
    """
    Close out project and decommission agents (Handover 0113).

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectCloseOutResponse with decommission details

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Close-out failed
    """
    logger.info("User %s closing out project %s", sanitize(current_user.username), sanitize(project_id))

    # Close out project via ProjectService (raises exceptions on error)
    result = await project_service.close_out_project(project_id=project_id, tenant_key=current_user.tenant_key)

    logger.info("Closed out project %s", sanitize(project_id))

    return ProjectCloseOutResponse(
        success=True,
        message=result.message,
        agents_decommissioned=result.agents_decommissioned,
        decommissioned_agent_ids=result.decommissioned_agent_ids,
        project_status=result.project_status,
    )


@router.post("/{project_id}/continue-working", response_model=ContinueWorkingResponse)
async def continue_working(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ContinueWorkingResponse:
    """
    Resume work on project (Handover 0113).

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ContinueWorkingResponse with resume details

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Invalid state transition
    """
    logger.info("User %s resuming work on project %s", sanitize(current_user.username), sanitize(project_id))

    # Resume work via ProjectService (raises exceptions on error)
    result = await project_service.continue_working(project_id=project_id, tenant_key=current_user.tenant_key)

    logger.info("Resumed work on project %s", sanitize(project_id))

    return ContinueWorkingResponse(
        success=True,
        message=result.message,
        agents_resumed=result.agents_resumed,
        resumed_agent_ids=result.resumed_agent_ids,
        project_status=result.project_status,
    )
