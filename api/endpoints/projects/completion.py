"""
Project Completion Endpoints - Handover 0125

Handles project completion operations:
- POST /{project_id}/complete - Complete project
- POST /{project_id}/close-out - Close out project (decommission agents)
- POST /{project_id}/continue-working - Resume work on project

All operations use ProjectService.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas.prompt import ProjectCloseoutDataResponse
from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.project_service import ProjectService

from .dependencies import get_project_service
from .models import ContinueWorkingResponse, ProjectCloseOutResponse, ProjectResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{project_id}/complete", response_model=ProjectResponse)
async def complete_project(
    project_id: str,
    summary: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Mark project as completed.

    Args:
        project_id: Project UUID
        summary: Optional completion summary
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with completed project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Completion failed
    """
    logger.info(f"User {current_user.username} completing project {project_id}")

    # Complete via ProjectService
    result = await project_service.complete_project(project_id=project_id, summary=summary)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to complete project")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Completed project {project_id}")

    # Get updated project
    get_result = await project_service.get_project(project_id=project_id)
    proj = get_result.get("project", {})

    return ProjectResponse(
        id=proj.get("id"),
        alias=proj.get("alias", ""),
        name=proj.get("name"),
        description=proj.get("description"),
        mission=proj.get("mission", ""),
        status=proj.get("status"),
        product_id=proj.get("product_id"),
        created_at=proj.get("created_at"),
        updated_at=proj.get("updated_at"),
        completed_at=proj.get("completed_at"),
        context_budget=proj.get("context_budget", 150000),
        context_used=proj.get("context_used", 0),
        agent_count=proj.get("agent_count", 0),
        message_count=proj.get("message_count", 0),
        agents=[],
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
    logger.info(f"User {current_user.username} fetching closeout data for project {project_id}")

    result = await project_service.get_closeout_data(project_id=project_id)

    if not result.get("success"):
        error_msg = result.get("error", "Project not found")
        status_code = (
            status.HTTP_404_NOT_FOUND
            if "not found" in error_msg.lower() or "access denied" in error_msg.lower()
            else status.HTTP_500_INTERNAL_SERVER_ERROR
        )
        raise HTTPException(status_code=status_code, detail=error_msg)

    return ProjectCloseoutDataResponse(**result["data"])


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
    logger.info(f"User {current_user.username} closing out project {project_id}")

    # Close out project via ProjectService
    result = await project_service.close_out_project(project_id=project_id, tenant_key=current_user.tenant_key)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to close out project")
        if "not found" in error_msg.lower() or "access denied" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Closed out project {project_id}")

    return ProjectCloseOutResponse(
        success=result["success"],
        message=result["message"],
        agents_decommissioned=result["agents_decommissioned"],
        decommissioned_agent_ids=result["decommissioned_agent_ids"],
        project_status=result["project_status"],
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
    logger.info(f"User {current_user.username} resuming work on project {project_id}")

    # Resume work via ProjectService
    result = await project_service.continue_working(project_id=project_id, tenant_key=current_user.tenant_key)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to resume project")
        if "not found" in error_msg.lower() or "access denied" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Resumed work on project {project_id}")

    return ContinueWorkingResponse(
        success=result["success"],
        message=result["message"],
        agents_resumed=result["agents_resumed"],
        resumed_agent_ids=result["resumed_agent_ids"],
        project_status=result["project_status"],
    )
