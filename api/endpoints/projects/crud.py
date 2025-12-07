"""
Project CRUD Endpoints - Handover 0125

Handles project CRUD operations:
- POST   / - Create project
- GET    / - List projects
- GET    /{project_id} - Get project details
- PATCH  /{project_id} - Update project

All operations use ProjectService (no direct DB access where possible).
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.project_service import ProjectService

from .dependencies import get_project_service
from .models import ProjectCreate, ProjectResponse, ProjectUpdate


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Create a new project.

    Uses ProjectService for all database operations.

    Args:
        project: Project creation request
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with created project details

    Raises:
        HTTPException 400: Project creation failed
        HTTPException 403: User not authorized
    """
    logger.debug(f"User {current_user.username} creating project: {project.name}")

    # Create project via ProjectService
    result = await project_service.create_project(
        name=project.name,
        mission=project.mission,
        description=project.description or "",
        product_id=project.product_id,
        tenant_key=current_user.tenant_key,
        status=project.status,
        context_budget=project.context_budget,
    )

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to create project")
        logger.error(f"Project creation failed: {error_msg}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Created project {result['project_id']} for tenant {current_user.tenant_key}")

    # Build response
    return ProjectResponse(
        id=result["project_id"],
        alias=result.get("alias", ""),
        name=result["name"],
        description=result.get("description"),
        mission=result.get("mission", ""),
        status=result["status"],
        staging_status=None,  # New projects start with null staging_status
        product_id=project.product_id,
        created_at=result.get("created_at"),
        updated_at=result.get("updated_at"),
        completed_at=None,
        context_budget=project.context_budget,
        context_used=0,
        agent_count=0,
        message_count=0,
        agents=[],
        execution_mode=result.get("execution_mode", "multi_terminal"),  # Handover 0260
    )


@router.get("/", response_model=List[ProjectResponse])
async def list_projects(
    status_filter: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> List[ProjectResponse]:
    """
    List all projects for current tenant.

    Args:
        status_filter: Optional status filter
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        List of ProjectResponse objects
    """
    logger.debug(f"User {current_user.username} listing projects (status={status_filter})")

    # List projects via ProjectService
    result = await project_service.list_projects(
        status=status_filter,
        tenant_key=current_user.tenant_key
    )

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to list projects")
        logger.error(f"Project listing failed: {error_msg}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    projects = result.get("projects", [])
    logger.info(f"Found {len(projects)} projects for tenant {current_user.tenant_key}")

    # Convert to response models
    # Note: ProjectService returns dict format, convert to ProjectResponse
    return [
        ProjectResponse(
            id=proj.get("id"),
            alias=proj.get("alias", ""),
            name=proj.get("name"),
            description=proj.get("description"),
            mission=proj.get("mission", ""),
            status=proj.get("status"),
            staging_status=proj.get("staging_status"),
            product_id=proj.get("product_id"),
            created_at=proj.get("created_at"),
            updated_at=proj.get("updated_at"),
            completed_at=proj.get("completed_at"),
            context_budget=proj.get("context_budget", 150000),
            context_used=proj.get("context_used", 0),
            agent_count=proj.get("agent_count", 0),
            message_count=proj.get("message_count", 0),
            agents=[],
            execution_mode=proj.get("execution_mode", "multi_terminal"),  # Handover 0260
        )
        for proj in projects
    ]


@router.get("/deleted", response_model=List[ProjectResponse])
async def get_deleted_projects(
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> List[ProjectResponse]:
    """
    Get soft-deleted projects for recovery (Handover 0070).

    Returns projects with status='deleted' and deleted_at timestamp set.
    These projects can be recovered within 10 days of deletion.

    Args:
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        List of ProjectResponse for deleted projects

    Raises:
        HTTPException 500: Failed to list deleted projects
    """
    logger.debug(f"User {current_user.username} listing deleted projects")

    # List deleted projects via ProjectService
    result = await project_service.list_projects(status="deleted")

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to list deleted projects")
        logger.error(f"Deleted project listing failed: {error_msg}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    projects = result.get("projects", [])
    logger.info(f"Found {len(projects)} deleted projects for tenant {current_user.tenant_key}")

    # Convert to response models
    return [
        ProjectResponse(
            id=proj.get("id"),
            alias=proj.get("alias", ""),
            name=proj.get("name"),
            description=proj.get("description"),
            mission=proj.get("mission", ""),
            status=proj.get("status"),
            staging_status=proj.get("staging_status"),
            product_id=proj.get("product_id"),
            created_at=proj.get("created_at"),
            updated_at=proj.get("updated_at"),
            completed_at=proj.get("completed_at"),
            deleted_at=proj.get("deleted_at"),
            context_budget=proj.get("context_budget", 150000),
            context_used=proj.get("context_used", 0),
            agent_count=proj.get("agent_count", 0),
            message_count=proj.get("message_count", 0),
            execution_mode=proj.get("execution_mode", "multi_terminal"),  # Handover 0260
            agents=[]
        )
        for proj in projects
    ]


@router.get("/active", response_model=Optional[ProjectResponse])
async def get_active_project(
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> Optional[ProjectResponse]:
    """
    Get the currently active project for the user's tenant.

    Returns the active project (status='active') or None if no project is active.

    Follows Single Active Project architecture (Handover 0050b):
    - Only ONE project can be active per product at any time
    - Database enforces this via partial unique index

    Args:
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with active project details, or None if no active project
    """
    logger.debug(f"User {current_user.username} fetching active project")

    # Get active project via ProjectService
    result = await project_service.get_active_project()

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Failed to get active project")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    proj = result.get("project")

    # No active project is OK - return None
    if not proj:
        logger.info(f"No active project found for tenant {current_user.tenant_key}")
        return None

    logger.info(f"Retrieved active project {proj.get('name')} for tenant {current_user.tenant_key}")

    return ProjectResponse(
        id=proj.get("id"),
        alias=proj.get("alias", ""),
        name=proj.get("name"),
        description=proj.get("description"),
        mission=proj.get("mission", ""),
        status=proj.get("status"),
        staging_status=proj.get("staging_status"),
        product_id=proj.get("product_id"),
        created_at=proj.get("created_at"),
        updated_at=proj.get("updated_at"),
        completed_at=proj.get("completed_at"),
        deleted_at=proj.get("deleted_at"),
        context_budget=proj.get("context_budget", 150000),
        context_used=proj.get("context_used", 0),
        agent_count=proj.get("agent_count", 0),
        message_count=proj.get("message_count", 0),
        execution_mode=proj.get("execution_mode", "multi_terminal"),  # Handover 0260
    )


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Get project details by ID.

    Args:
        project_id: Project UUID or alias
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with project details

    Raises:
        HTTPException 404: Project not found
    """
    logger.debug(f"User {current_user.username} getting project {project_id}")

    # Get project via ProjectService
    result = await project_service.get_project(project_id=project_id)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Project not found")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    proj = result.get("project", {})
    logger.info(f"Retrieved project {project_id} for tenant {current_user.tenant_key}")

    # Production-grade: Use agents from service response (not hardcoded empty array)
    agents_from_service = proj.get("agents", [])

    return ProjectResponse(
        id=proj.get("id"),
        alias=proj.get("alias", ""),
        name=proj.get("name"),
        description=proj.get("description"),
        mission=proj.get("mission", ""),
        status=proj.get("status"),
        staging_status=proj.get("staging_status"),
        product_id=proj.get("product_id"),
        created_at=proj.get("created_at"),
        updated_at=proj.get("updated_at"),
        completed_at=proj.get("completed_at"),
        context_budget=proj.get("context_budget", 150000),
        context_used=proj.get("context_used", 0),
        agent_count=proj.get("agent_count", len(agents_from_service)),
        message_count=proj.get("message_count", 0),
        execution_mode=proj.get("execution_mode", "multi_terminal"),  # Handover 0260
        agents=agents_from_service  # Fixed: Use agents from ProjectService, not hardcoded []
    )


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    updates: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse:
    """
    Update project fields (Handover 0504).

    Supports updating: name, description, mission, status.
    Only provided fields are updated (partial updates supported).

    Args:
        project_id: Project UUID
        updates: Fields to update
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectResponse with updated project

    Raises:
        HTTPException 404: Project not found
        HTTPException 400: Update failed
    """
    logger.debug(f"User {current_user.username} updating project {project_id}")

    # Convert updates to dict, excluding unset fields
    update_dict = updates.dict(exclude_unset=True)

    if not update_dict:
        # No fields to update, just return current project
        result = await project_service.get_project(project_id=project_id)
        if not result.get("success"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
        proj = result.get("project", {})
    else:
        # Update via ProjectService
        result = await project_service.update_project(
            project_id=project_id,
            updates=update_dict
        )

        if not result.get("success"):
            error_msg = result.get("error", "Failed to update project")
            if "not found" in error_msg.lower():
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
            else:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

        proj = result.get("data", {})

    logger.info(f"Updated project {project_id}")

    return ProjectResponse(
        id=proj.get("id"),
        alias=proj.get("alias", ""),
        name=proj.get("name"),
        description=proj.get("description"),
        mission=proj.get("mission", ""),
        status=proj.get("status"),
        staging_status=proj.get("staging_status"),
        product_id=proj.get("product_id"),
        created_at=proj.get("created_at"),
        updated_at=proj.get("updated_at"),
        completed_at=proj.get("completed_at"),
        context_budget=proj.get("context_budget", 150000),
        context_used=proj.get("context_used", 0),
        agent_count=proj.get("agent_count", 0),
        message_count=proj.get("message_count", 0),
        execution_mode=proj.get("execution_mode", "multi_terminal"),  # Handover 0260
        agents=[]
    )
