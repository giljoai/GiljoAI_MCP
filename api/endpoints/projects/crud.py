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

from fastapi import APIRouter, Depends, Query, status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.project_service import ProjectService

from .dependencies import get_project_service
from .models import (
    AvailableSeriesResponse,
    NextSeriesResponse,
    ProjectCreate,
    ProjectResponse,
    ProjectUpdate,
    SeriesCheckResponse,
    UsedSubseriesResponse,
)


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

    # Create project via ProjectService (raises exceptions on error - Handover 0730b)
    created_project = await project_service.create_project(
        name=project.name,
        mission=project.mission,
        description=project.description or "",
        product_id=project.product_id,
        tenant_key=current_user.tenant_key,
        status=project.status,
        # Handover 0440a: Pass taxonomy fields
        project_type_id=project.project_type_id,
        series_number=project.series_number,
        subseries=project.subseries,
    )

    logger.info(f"Created project {created_project.id} for tenant {current_user.tenant_key}")

    # Build response
    return ProjectResponse(
        id=str(created_project.id),
        alias=created_project.alias or "",
        name=created_project.name,
        description=created_project.description,
        mission=created_project.mission or "",
        status=created_project.status,
        staging_status=created_project.staging_status,
        product_id=created_project.product_id,
        created_at=created_project.created_at.isoformat() if created_project.created_at else None,
        updated_at=created_project.updated_at.isoformat() if created_project.updated_at else None,
        completed_at=created_project.completed_at.isoformat() if created_project.completed_at else None,
        agent_count=0,
        message_count=0,
        agents=[],
        execution_mode=created_project.execution_mode or "multi_terminal",  # Handover 0260
        # Handover 0440a: Taxonomy fields
        project_type_id=created_project.project_type_id,
        project_type=created_project.project_type,  # Handover 0440c: Nested type info
        series_number=created_project.series_number,
        subseries=created_project.subseries,
        taxonomy_alias=created_project.taxonomy_alias,
    )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    status_filter: str | None = None,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
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

    # List projects via ProjectService (raises exceptions on error)
    projects = await project_service.list_projects(status=status_filter, tenant_key=current_user.tenant_key)

    logger.info(f"Found {len(projects)} projects for tenant {current_user.tenant_key}")

    # Convert to response models (0731d: ProjectService returns list[ProjectListItem] typed models)
    return [
        ProjectResponse(
            id=proj.id,
            alias="",
            name=proj.name,
            description=proj.description,
            mission=proj.mission or "",
            status=proj.status,
            staging_status=proj.staging_status,
            product_id=proj.product_id,
            created_at=proj.created_at,
            updated_at=proj.updated_at,
            completed_at=None,
            agent_count=0,
            message_count=0,
            agents=[],
            execution_mode="multi_terminal",  # Handover 0260
            # Handover 0440a: Taxonomy fields
            project_type_id=proj.project_type_id,
            project_type=proj.project_type,  # Handover 0440c: Nested type info
            series_number=proj.series_number,
            subseries=proj.subseries,
            taxonomy_alias=proj.taxonomy_alias,
        )
        for proj in projects
    ]


@router.get("/deleted", response_model=list[ProjectResponse])
async def get_deleted_projects(
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> list[ProjectResponse]:
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

    # List deleted projects via ProjectService (raises exceptions on error)
    # SECURITY: Explicit tenant_key prevents cross-tenant data leak
    projects = await project_service.list_projects(status="deleted", tenant_key=current_user.tenant_key)

    logger.info(f"Found {len(projects)} deleted projects for tenant {current_user.tenant_key}")

    # Convert to response models (0731d: ProjectService returns list[ProjectListItem] typed models)
    return [
        ProjectResponse(
            id=proj.id,
            alias="",
            name=proj.name,
            description=proj.description,
            mission=proj.mission or "",
            status=proj.status,
            staging_status=proj.staging_status,
            product_id=proj.product_id,
            created_at=proj.created_at,
            updated_at=proj.updated_at,
            completed_at=None,
            deleted_at=None,
            agent_count=0,
            message_count=0,
            execution_mode="multi_terminal",  # Handover 0260
            agents=[],
            # Handover 0440a: Taxonomy fields
            project_type_id=proj.project_type_id,
            project_type=proj.project_type,  # Handover 0440c: Nested type info
            series_number=proj.series_number,
            subseries=proj.subseries,
            taxonomy_alias=proj.taxonomy_alias,
        )
        for proj in projects
    ]


@router.get("/active", response_model=ProjectResponse | None)
async def get_active_project(
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectResponse | None:
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

    # Get active project via ProjectService (raises exceptions on error, returns None if no active project)
    proj = await project_service.get_active_project()

    # No active project is OK - return None
    if not proj:
        logger.info(f"No active project found for tenant {current_user.tenant_key}")
        return None

    logger.info(f"Retrieved active project {proj.name} for tenant {current_user.tenant_key}")

    return ProjectResponse(
        id=proj.id,
        alias=proj.alias,
        name=proj.name,
        description=proj.description,
        mission=proj.mission or "",
        status=proj.status,
        product_id=proj.product_id,
        created_at=proj.created_at,
        updated_at=proj.updated_at,
        completed_at=proj.completed_at,
        deleted_at=proj.deleted_at,
        agent_count=proj.agent_count,
        message_count=proj.message_count,
        execution_mode="multi_terminal",  # Handover 0260
        # Handover 0440a: Taxonomy fields
        project_type_id=proj.project_type_id,
        project_type=proj.project_type,  # Handover 0440c: Nested type info
        series_number=proj.series_number,
        subseries=proj.subseries,
        taxonomy_alias=proj.taxonomy_alias,
    )


@router.get("/next-series", response_model=NextSeriesResponse)
async def next_series_number(
    type_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Get the next available series number for a project type.

    Handover 0440a: Taxonomy series number helper.
    """

    from api.endpoints.project_types.crud_ops import get_next_series_number

    async with project_service.db_manager.get_session_async() as session:
        next_num = await get_next_series_number(session, current_user.tenant_key, type_id)
    return {"next_series_number": next_num}


@router.get("/available-series", response_model=AvailableSeriesResponse)
async def available_series_numbers(
    type_id: str,
    limit: int = 5,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Get available series numbers (gaps + next) for a project type.

    Handover 0440a: Taxonomy series number helper.
    """
    from api.endpoints.project_types.crud_ops import get_available_series_numbers

    async with project_service.db_manager.get_session_async() as session:
        available = await get_available_series_numbers(session, current_user.tenant_key, type_id, limit)
    return {"available_series_numbers": available}


@router.get("/check-series", response_model=SeriesCheckResponse)
async def check_series_number(
    type_id: str | None = None,
    series_number: int = Query(ge=1, le=9999),
    subseries: str | None = Query(default=None, pattern=r"^[a-z]$"),
    exclude_project_id: str | None = None,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Check if a specific series number is available for a project type.

    Handover 0440c: Real-time series validation for inline taxonomy input.
    """
    from api.endpoints.project_types.crud_ops import check_series_available

    async with project_service.db_manager.get_session_async() as session:
        result = await check_series_available(
            session,
            current_user.tenant_key,
            type_id,
            series_number,
            subseries,
            exclude_project_id,
        )
    return result


@router.get("/used-subseries", response_model=UsedSubseriesResponse)
async def used_subseries(
    type_id: str | None = None,
    series_number: int = Query(ge=1, le=9999),
    exclude_project_id: str | None = None,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
):
    """Get subseries letters already used for a type + series_number.

    Handover 0440c: Smart suffix dropdown filtering.
    """
    from api.endpoints.project_types.crud_ops import get_used_subseries

    async with project_service.db_manager.get_session_async() as session:
        result = await get_used_subseries(
            session,
            current_user.tenant_key,
            type_id,
            series_number,
            exclude_project_id,
        )
    return result


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

    # Get project via ProjectService (raises exceptions on error)
    proj = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)

    logger.info(f"Retrieved project {project_id} for tenant {current_user.tenant_key}")

    # Production-grade: Use agents from service response (not hardcoded empty array)
    agents_from_service = proj.agents

    return ProjectResponse(
        id=proj.id,
        alias=proj.alias or "",
        name=proj.name,
        description=proj.description,
        mission=proj.mission or "",
        status=proj.status,
        staging_status=proj.staging_status,
        product_id=proj.product_id,
        created_at=proj.created_at,
        updated_at=proj.updated_at,
        completed_at=proj.completed_at,
        agent_count=proj.agent_count or len(agents_from_service),
        message_count=proj.message_count,
        execution_mode=proj.execution_mode or "multi_terminal",  # Handover 0260
        agents=agents_from_service,  # Fixed: Use agents from ProjectService, not hardcoded []
        # Handover 0440a: Taxonomy fields
        project_type_id=proj.project_type_id,
        project_type=proj.project_type,  # Handover 0440c: Nested type info
        series_number=proj.series_number,
        subseries=proj.subseries,
        taxonomy_alias=proj.taxonomy_alias,
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
        # No fields to update, just return current project (raises exceptions on error)
        detail = await project_service.get_project(project_id=project_id, tenant_key=current_user.tenant_key)
        proj_id = detail.id
        proj_alias = detail.alias or ""
        proj_name = detail.name
        proj_desc = detail.description
        proj_mission = detail.mission or ""
        proj_status = detail.status
        proj_staging = detail.staging_status
        proj_product = detail.product_id
        proj_created = detail.created_at
        proj_updated = detail.updated_at
        proj_completed = detail.completed_at
        proj_agents = detail.agent_count
        proj_messages = detail.message_count
        proj_mode = detail.execution_mode or "multi_terminal"
        # Handover 0440a: Taxonomy fields from ProjectDetail
        proj_type_id = detail.project_type_id
        proj_type = detail.project_type  # Handover 0440c: Nested type info
        proj_series = detail.series_number
        proj_subseries = detail.subseries
        proj_tax_alias = detail.taxonomy_alias
    else:
        # Update via ProjectService (raises exceptions on error, returns ProjectData)
        proj = await project_service.update_project(project_id=project_id, updates=update_dict)
        proj_id = proj.id
        proj_alias = ""
        proj_name = proj.name
        proj_desc = proj.description
        proj_mission = proj.mission or ""
        proj_status = proj.status
        proj_staging = None
        proj_product = proj.product_id
        proj_created = proj.created_at
        proj_updated = proj.updated_at
        proj_completed = proj.completed_at
        proj_agents = 0
        proj_messages = 0
        proj_mode = proj.execution_mode or "multi_terminal"
        # Handover 0440a: Taxonomy fields from ProjectData
        proj_type_id = proj.project_type_id
        proj_type = proj.project_type  # Handover 0440c: Nested type info
        proj_series = proj.series_number
        proj_subseries = proj.subseries
        proj_tax_alias = proj.taxonomy_alias

    logger.info(f"Updated project {project_id}")

    return ProjectResponse(
        id=proj_id,
        alias=proj_alias,
        name=proj_name,
        description=proj_desc,
        mission=proj_mission,
        status=proj_status,
        staging_status=proj_staging,
        product_id=proj_product,
        created_at=proj_created,
        updated_at=proj_updated,
        completed_at=proj_completed,
        agent_count=proj_agents,
        message_count=proj_messages,
        execution_mode=proj_mode,
        agents=[],
        # Handover 0440a: Taxonomy fields
        project_type_id=proj_type_id,
        project_type=proj_type,  # Handover 0440c: Nested type info
        series_number=proj_series,
        subseries=proj_subseries,
        taxonomy_alias=proj_tax_alias,
    )
