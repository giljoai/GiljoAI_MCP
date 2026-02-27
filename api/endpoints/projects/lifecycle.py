"""
Project Lifecycle Endpoints - Handover 0125 & 0504

Handles project lifecycle operations:
- POST /{project_id}/activate - Activate project (Handover 0504)
- POST /{project_id}/deactivate - Deactivate project (Handover 0504)
- POST /{project_id}/cancel - Cancel project
- POST /{project_id}/restore - Restore cancelled project
- POST /{project_id}/cancel-staging - Cancel staging phase (Handover 0504)
- POST /{project_id}/launch - Launch orchestrator (Handover 0504)
- POST /{project_id}/archive - Archive completed project (Handover 0412)
- DELETE /{project_id} - Soft delete project
- DELETE /deleted - Purge all deleted projects
- DELETE /{project_id}/purge - Nuclear purge single deleted project

All operations use ProjectService.
"""

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.models.schemas import ProjectLaunchResponse
from src.giljo_mcp.services.project_service import ProjectService

from .dependencies import get_project_service
from .models import (
    ProjectDeleteResponse,
    ProjectPurgeResponse,
    ProjectResponse,
    PurgedProject,
)


logger = logging.getLogger(__name__)
router = APIRouter()


def _build_project_response(proj, agents=None) -> ProjectResponse:
    """Build a ProjectResponse from a ProjectDetail DTO.

    Centralises the ProjectDetail-to-ProjectResponse mapping used by every
    lifecycle endpoint so the field list is maintained in exactly one place.

    Args:
        proj: ProjectDetail DTO returned by ProjectService.get_project().
        agents: Optional list of agent dicts. Defaults to an empty list.

    Returns:
        A fully populated ProjectResponse.
    """
    if agents is None:
        agents = []
    return ProjectResponse(
        id=proj.id,
        alias=proj.alias or "",
        name=proj.name,
        description=proj.description,
        mission=proj.mission or "",
        status=proj.status,
        product_id=proj.product_id,
        created_at=proj.created_at,
        updated_at=proj.updated_at,
        completed_at=proj.completed_at,
        agent_count=proj.agent_count,
        message_count=proj.message_count,
        agents=agents,
    )


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

    # Activate via ProjectService (raises exceptions on error - Handover 0730b)
    await project_service.activate_project(project_id=project_id, force=force, tenant_key=current_user.tenant_key)

    logger.info(f"Activated project {project_id}")

    # Get full project details with agents (raises exceptions on error)
    proj = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)

    return _build_project_response(proj)


@router.post("/{project_id}/deactivate", response_model=ProjectResponse)
async def deactivate_project(
    project_id: str,
    reason: str | None = None,
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

    # Deactivate via ProjectService (raises exceptions on error - Handover 0730b)
    await project_service.deactivate_project(project_id=project_id, tenant_key=current_user.tenant_key, reason=reason)

    logger.info(f"Deactivated project {project_id}")

    # Get updated project with agents (raises exceptions on error)
    proj = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)

    return _build_project_response(proj)


@router.post("/{project_id}/cancel", response_model=ProjectResponse)
async def cancel_project(
    project_id: str,
    reason: str | None = None,
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

    # Cancel via ProjectService (raises exceptions on error)
    await project_service.cancel_project(project_id=project_id, tenant_key=current_user.tenant_key, reason=reason)

    logger.info(f"Cancelled project {project_id}")

    # Get updated project (raises exceptions on error)
    proj = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)

    return _build_project_response(proj)


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

    # Restore via ProjectService (raises exceptions on error)
    # SECURITY: Explicit tenant_key prevents cross-tenant project restoration
    await project_service.restore_project(project_id=project_id, tenant_key=current_user.tenant_key)

    logger.info(f"Restored project {project_id}")

    # Get updated project (raises exceptions on error)
    proj = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)

    return _build_project_response(proj)


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

    # Cancel staging via ProjectService (raises exceptions on error)
    await project_service.cancel_staging(project_id=project_id)

    logger.info(f"Cancelled staging for project {project_id}")

    # Get updated project (raises exceptions on error)
    proj = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)

    return _build_project_response(proj)


@router.delete("/deleted", response_model=ProjectPurgeResponse)
async def purge_all_deleted_projects(
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectPurgeResponse:
    """
    Permanently delete all soft-deleted projects for the current tenant.
    """
    logger.info("User %s purging all deleted projects", current_user.username)

    # Service raises exceptions on error
    result = await project_service.purge_all_deleted_projects()

    # 0731d: ProjectService returns ProjectPurgeResult typed model
    projects = [PurgedProject(**proj) for proj in result.projects]
    return ProjectPurgeResponse(
        success=True,
        purged_count=result.purged_count,
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
    Immediately perform nuclear delete on a specific soft-deleted project.

    This is triggered when user clicks the trash icon next to a deleted project.
    Performs complete removal of project and ALL associated data immediately.
    """
    logger.info("User %s performing NUCLEAR PURGE on deleted project %s", current_user.username, project_id)

    # Use nuclear delete for immediate permanent deletion (raises exceptions on error)
    result = await project_service.nuclear_delete_project(project_id)

    # 0731d: ProjectService returns NuclearDeleteResult typed model
    project_info = {
        "id": project_id,
        "name": result.project_name,
        "tenant_key": "",
        "deleted_at": datetime.now(timezone.utc).isoformat(),
    }

    return ProjectPurgeResponse(
        success=True,
        purged_count=1,
        projects=[PurgedProject(**project_info)],
        message=f"Project permanently deleted. Removed: {result.deleted_counts}",
    )


@router.post("/{project_id}/archive", response_model=ProjectResponse)
async def archive_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Archive a completed project (Handover 0412).

    Marks project as 'completed' and sets completed_at timestamp.
    This is used when the user confirms project closeout and wants to archive it
    without continuing work.

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with archived project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Archive failed
    """
    logger.info(f"User {current_user.username} archiving project {project_id}")

    # Get project first to validate (raises exceptions on error)
    proj = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)
    current_status = proj.status

    # Only deactivate if not already inactive/completed
    if current_status not in ("inactive", "completed", "archived", "terminated"):
        await project_service.deactivate_project(project_id=project_id, reason="User archived project after completion")

    # Check early_termination flag to determine target status (Handover 0498)
    meta = proj.meta_data or {}
    target_status = "terminated" if meta.get("early_termination") else "completed"

    # Set completed_at timestamp to mark as archived (raises exceptions on error)
    await project_service.update_project(
        project_id=project_id, updates={"status": target_status, "completed_at": datetime.now(timezone.utc)}
    )

    logger.info(f"Archived project {project_id}")

    # Get updated project (raises exceptions on error)
    proj = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)

    return _build_project_response(proj)


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

    # Service raises exceptions on error
    result = await project_service.delete_project(project_id)

    # 0731d: ProjectService returns SoftDeleteResult typed model
    return ProjectDeleteResponse(
        success=True,
        message=result.message,
        deleted_at=result.deleted_at,
    )


@router.post("/{project_id}/launch", response_model=ProjectLaunchResponse)
async def launch_project(
    project_id: str,
    launch_config: dict[str, Any | None] = None,
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

    # Launch via ProjectService (raises exceptions on error)
    launch_data = await project_service.launch_project(
        project_id=project_id, user_id=str(current_user.id), launch_config=launch_config
    )

    logger.info(f"Launched project {project_id}")

    # 0731d: ProjectService returns ProjectLaunchResult typed model
    return ProjectLaunchResponse(
        project_id=launch_data.project_id,
        orchestrator_job_id=launch_data.orchestrator_job_id,
        launch_prompt=launch_data.launch_prompt,
        status=launch_data.status,
    )
