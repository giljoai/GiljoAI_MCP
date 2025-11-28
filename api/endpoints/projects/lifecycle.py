"""
Project Lifecycle Endpoints - Handover 0125 & 0504

Handles project lifecycle operations:
- POST /{project_id}/activate - Activate project (Handover 0504)
- POST /{project_id}/deactivate - Deactivate project (Handover 0504)
- POST /{project_id}/cancel - Cancel project
- POST /{project_id}/restore - Restore cancelled project
- POST /{project_id}/cancel-staging - Cancel staging phase (Handover 0504)
- POST /{project_id}/launch - Launch orchestrator (Handover 0504)

All operations use ProjectService.
"""

import logging
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.models.schemas import ProjectLaunchResponse
from src.giljo_mcp.services.project_service import ProjectService

from .dependencies import get_project_service
from .models import (
    ProjectResponse,
    StagingCancellationResponse,
    ProjectDeleteResponse,
    ProjectPurgeResponse,
    PurgedProject,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{project_id}/activate", response_model=ProjectResponse)
async def activate_project(
    project_id: str,
    force: bool = False,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Activate a project (sets status to active).

    State Transitions:
    - staging → active (initial launch)
    - inactive → active (resume)

    Automatically deactivates other active projects in same product (Single Active Project constraint).

    Args:
        project_id: Project UUID
        force: Skip validation checks if True
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with activated project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Activation failed
    """
    logger.info(f"User {current_user.username} activating project {project_id} (force={force})")

    # Activate via ProjectService
    result = await project_service.activate_project(
        project_id=project_id,
        force=force
    )

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to activate project")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Activated project {project_id}")

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


@router.post("/{project_id}/deactivate", response_model=ProjectResponse)
async def deactivate_project(
    project_id: str,
    reason: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Deactivate an active project.

    State Transition: active → inactive

    Args:
        project_id: Project UUID
        reason: Optional reason for deactivation (stored in config_data)
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with inactive project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Deactivation failed
    """
    logger.info(f"User {current_user.username} deactivating project {project_id}")

    # Deactivate via ProjectService
    result = await project_service.deactivate_project(
        project_id=project_id,
        reason=reason
    )

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to deactivate project")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Deactivated project {project_id}")

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


@router.post("/{project_id}/cancel-staging", response_model=ProjectResponse)
async def cancel_project_staging(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Cancel project staging and rollback (Handover 0108).

    State Transition: staging → cancelled

    This endpoint cancels staging after orchestrator has spawned agents.
    Performs transactional rollback of staging changes.

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with cancelled project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Cancellation failed
    """
    logger.info(f"User {current_user.username} cancelling staging for project {project_id}")

    # Cancel staging via ProjectService
    result = await project_service.cancel_staging(project_id=project_id)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to cancel staging")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Cancelled staging for project {project_id}")

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


@router.delete("/deleted", response_model=ProjectPurgeResponse)
async def purge_all_deleted_projects(
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectPurgeResponse:
    """
    Permanently delete all soft-deleted projects for the current tenant.
    """
    logger.info("User %s purging all deleted projects", current_user.username)

    result = await project_service.purge_all_deleted_projects()
    if not result.get("success"):
        error_msg = result.get("error", "Failed to purge deleted projects")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    projects = [PurgedProject(**proj) for proj in result.get("projects", [])]
    return ProjectPurgeResponse(
        success=True,
        purged_count=result.get("purged_count", 0),
        projects=projects,
        message="Deleted projects purged successfully",
    )


@router.delete("/{project_id}/purge", response_model=ProjectPurgeResponse)
async def purge_deleted_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectPurgeResponse:
    """
    Permanently delete a specific soft-deleted project.
    """
    logger.info("User %s purging deleted project %s", current_user.username, project_id)

    result = await project_service.purge_deleted_project(project_id)

    if not result.get("success"):
        error_msg = result.get("error", "Failed to purge project")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    projects = [PurgedProject(**proj) for proj in result.get("projects", [])]
    return ProjectPurgeResponse(
        success=True,
        purged_count=result.get("purged_count", 0),
        projects=projects,
        message="Project purged successfully",
    )


@router.delete("/{project_id}", response_model=ProjectDeleteResponse)
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectDeleteResponse:
    """
    Soft delete a project.

    Marks the project as status='deleted' and sets deleted_at. Purging after 10 days
    is handled by ProjectService.purge_expired_deleted_projects().
    """
    logger.info(f"User {current_user.username} deleting project {project_id}")

    try:
        result = await project_service.delete_project(project_id)

        if not result.get("success"):
            error_msg = result.get("error", "Failed to delete project")
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

        return ProjectDeleteResponse(
            success=True,
            message=result.get("message", "Project deleted successfully"),
            deleted_at=result.get("deleted_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete project: {str(e)}",
        )


@router.post("/{project_id}/launch", response_model=ProjectLaunchResponse)
async def launch_project(
    project_id: str,
    launch_config: Optional[Dict[str, Any]] = None,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectLaunchResponse:
    """
    Launch project orchestrator (Handover 0504).

    Creates orchestrator agent job and generates thin-client launch prompt.
    Activates the project if not already active.

    Args:
        project_id: Project UUID
        launch_config: Optional launch configuration
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectLaunchResponse with orchestrator job ID and launch prompt

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Launch failed
    """
    logger.info(f"User {current_user.username} launching project {project_id}")

    # Launch via ProjectService
    result = await project_service.launch_project(
        project_id=project_id,
        launch_config=launch_config
    )

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to launch project")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Launched project {project_id}")

    # Return data as ProjectLaunchResponse
    launch_data = result.get("data", {})
    return ProjectLaunchResponse(**launch_data)
