"""
Project Lifecycle Endpoints - Handover 0125

Handles project lifecycle operations:
- POST /{project_id}/activate - Activate project
- POST /{project_id}/cancel - Cancel project
- POST /{project_id}/restore - Restore cancelled project
- POST /{project_id}/cancel-staging - Cancel staging phase

All operations use ProjectService.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.project_service import ProjectService

from .dependencies import get_project_service
from .models import ProjectResponse, StagingCancellationResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{project_id}/activate", response_model=ProjectResponse)
async def activate_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Activate a project (sets status to active).

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with activated project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Activation failed
    """
    logger.info(f"User {current_user.username} activating project {project_id}")

    # TODO: Add activate_project to ProjectService
    # For now, return error indicating service method needed
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="ProjectService.activate_project not yet implemented"
    )


@router.post("/{project_id}/cancel", response_model=ProjectResponse)
async def cancel_project(
    project_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Cancel a project.

    Args:
        project_id: Project UUID
        reason: Optional cancellation reason
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with cancelled project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Cancellation failed
    """
    logger.info(f"User {current_user.username} cancelling project {project_id}")

    # Cancel via ProjectService
    result = await project_service.cancel_project(
        project_id=project_id,
        reason=reason
    )

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to cancel project")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Cancelled project {project_id}")

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
        agents=[]
    )


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Restore a cancelled project.

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with restored project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Restore failed
    """
    logger.info(f"User {current_user.username} restoring project {project_id}")

    # Restore via ProjectService
    result = await project_service.restore_project(project_id=project_id)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to restore project")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Restored project {project_id}")

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
        agents=[]
    )


@router.post("/{project_id}/cancel-staging", response_model=StagingCancellationResponse)
async def cancel_project_staging(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> StagingCancellationResponse:
    """
    Cancel project staging and rollback (Handover 0108).

    This endpoint cancels staging after orchestrator has spawned agents.
    Performs transactional rollback of staging changes.

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        StagingCancellationResponse with rollback details

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Cancellation failed
    """
    logger.info(f"User {current_user.username} cancelling staging for project {project_id}")

    # TODO: Add cancel_staging to ProjectService
    # For now, return error indicating service method needed
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="ProjectService.cancel_staging not yet implemented - complex operation requiring direct DB access"
    )
