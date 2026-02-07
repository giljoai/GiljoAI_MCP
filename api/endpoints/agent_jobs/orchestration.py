"""
Orchestration Endpoints - Handover 0124

Handles project orchestration operations:
- POST /api/agent-jobs/orchestrate/{project_id} - Orchestrate project
- GET /api/agent-jobs/workflow/{project_id} - Get workflow status
- POST /api/agent-jobs/regenerate-mission - Regenerate project mission
- POST /api/agent-jobs/launch-project - Launch staged project

All operations use OrchestrationService (no direct DB access).
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.orchestration_service import OrchestrationService

from .dependencies import get_orchestration_service
from .models import WorkflowStatusResponse


logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Orchestration Models (from old orchestration.py)
# ============================================================================


class RegenerateMissionRequest(BaseModel):
    """Request model for mission regeneration."""

    project_id: UUID
    override_field_priorities: Optional[dict[str, int]] = None
    override_serena_enabled: Optional[bool] = None


class RegenerateMissionResponse(BaseModel):
    """Response model for mission regeneration."""

    mission: str
    user_config_applied: bool
    serena_enabled: bool
    field_priorities_used: dict[str, int]


class LaunchProjectRequest(BaseModel):
    """Request model for project launch."""

    project_id: UUID


class AgentInfo(BaseModel):
    """Agent information for launch response."""

    agent_id: str
    job_id: str
    agent_display_name: str
    agent_name: Optional[str]
    status: str
    mission: str
    tool_type: str
    progress: int


class LaunchProjectResponse(BaseModel):
    """Response model for project launch."""

    success: bool
    project_id: str
    staging_status: str
    agent_count: int
    agents: list[AgentInfo]
    message: Optional[str] = None


# ============================================================================
# Core Orchestration Endpoints (OrchestrationService)
# ============================================================================
# Note: orchestrate_project endpoint removed - use manual orchestration workflow


@router.get("/workflow/{project_id}", response_model=WorkflowStatusResponse)
async def get_workflow_status(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> WorkflowStatusResponse:
    """
    Get workflow status for project.

    Returns agent counts, completion status, and progress percentage.

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for orchestration operations (from dependency)

    Returns:
        WorkflowStatusResponse with workflow metrics

    Raises:
        HTTPException 404: Project not found
    """
    from src.giljo_mcp.exceptions import DatabaseError, ResourceNotFoundError

    logger.debug(f"User {current_user.username} getting workflow status for project {project_id}")

    try:
        # Get workflow status via OrchestrationService
        result = await orchestration_service.get_workflow_status(
            project_id=project_id, tenant_key=current_user.tenant_key
        )

        logger.info(f"Retrieved workflow status for project {project_id}")

        return WorkflowStatusResponse(
            project_id=project_id,
            status=result.get("current_stage", "unknown"),
            agent_count=result.get("total_agents", 0),
            completed_count=result.get("completed_agents", 0),
            failed_count=result.get("failed_agents", 0),
            active_count=result.get("active_agents", 0),
            progress_percent=int(result.get("progress_percent", 0)),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=e.message)
    except DatabaseError as e:
        logger.exception(f"Database error getting workflow status: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=e.message)


# ============================================================================
# Mission & Launch Endpoints (from old orchestration.py)
# ============================================================================


async def _get_user_config_with_overrides(
    user_id: UUID,
    db: AsyncSession,
    override_priorities: Optional[dict[str, int]],
    override_serena: Optional[bool],
) -> dict:
    """
    Get user field priority configuration with optional overrides.

    Args:
        user_id: User UUID
        db: Database session
        override_priorities: Optional priority overrides
        override_serena: Optional serena enabled override

    Returns:
        Dict with field_priorities, serena_enabled, token_budget
    """
    result = await db.execute(select(User).filter_by(id=user_id))
    user = result.scalar_one_or_none()

    base_config = {
        "field_priorities": {},
        "serena_enabled": False,
        "token_budget": 2000,
    }

    if user and user.field_priority_config:
        base_config["field_priorities"] = user.field_priority_config.get("field_priorities", {})
        base_config["serena_enabled"] = user.field_priority_config.get("serena_enabled", False)
        base_config["token_budget"] = user.field_priority_config.get("token_budget", 2000)

    if override_priorities is not None:
        base_config["field_priorities"] = {**base_config["field_priorities"], **override_priorities}
    if override_serena is not None:
        base_config["serena_enabled"] = override_serena

    return base_config


@router.post("/regenerate-mission", response_model=RegenerateMissionResponse)
async def regenerate_mission(
    request: RegenerateMissionRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
) -> RegenerateMissionResponse:
    """
    Regenerate project mission with optional user configuration overrides.

    Handover 0086B Task 3.3 - Mission Regeneration

    Args:
        request: Mission regeneration request with project_id and overrides
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)
        ws_dep: WebSocket dependency for broadcasting (from dependency)

    Returns:
        RegenerateMissionResponse with generated mission and config

    Raises:
        HTTPException 404: Project or product not found
    """
    logger.info(f"Mission regeneration requested for project {request.project_id}")

    # Get project with tenant isolation
    result = await db.execute(select(Project).filter_by(id=request.project_id, tenant_key=current_user.tenant_key))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Get product
    result = await db.execute(select(Product).filter_by(id=project.product_id, tenant_key=current_user.tenant_key))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    # Get user config with overrides
    user_config = await _get_user_config_with_overrides(
        user_id=current_user.id,
        db=db,
        override_priorities=request.override_field_priorities,
        override_serena=request.override_serena_enabled,
    )

    # Generate mission (simplified - real implementation would use mission planner)
    mission_text = f"Mission for {project.name}: {project.mission}"

    # Broadcast WebSocket event
    try:
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="project:mission_updated",
            data={
                "project_id": str(request.project_id),
                "tenant_key": current_user.tenant_key,
                "mission": mission_text,
                "generated_by": "user",
                "user_config_applied": True,
                "field_priorities": user_config["field_priorities"],
            },
        )
    except Exception:
        logger.exception("Failed to broadcast WebSocket event")

    return RegenerateMissionResponse(
        mission=mission_text,
        user_config_applied=True,
        serena_enabled=user_config["serena_enabled"],
        field_priorities_used=user_config["field_priorities"],
    )


@router.post("/launch-project", response_model=LaunchProjectResponse)
async def launch_project(
    request: LaunchProjectRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
) -> LaunchProjectResponse:
    """
    Launch a staged project - transition from staging to execution phase.

    Called when user clicks "Launch Jobs" button after staging completes.
    Validates project has mission and agents, then transitions to 'launching' status.

    Handover 0109 Agent 1 - Project Launch Endpoint

    Args:
        request: LaunchProjectRequest with project_id
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)
        ws_dep: WebSocket dependency for broadcasting (from dependency)

    Returns:
        LaunchProjectResponse with agent data and updated status

    Raises:
        HTTPException 404: Project not found or soft-deleted
        HTTPException 400: Project missing mission or no agents spawned
    """
    project_id_str = str(request.project_id)
    logger.info(f"Launch project requested for {project_id_str} by {current_user.username}")

    # Fetch project with multi-tenant isolation
    stmt = select(Project).where(
        Project.id == project_id_str,
        Project.tenant_key == current_user.tenant_key,
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project or project.deleted_at is not None:
        logger.warning(f"Project {project_id_str} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate mission exists
    if not project.mission or project.mission.strip() == "":
        logger.error(f"Project {project_id_str} has no mission")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project mission has not been created. Please complete staging first.",
        )

    # Fetch spawned agents (executions with job data)
    agent_stmt = (
        select(AgentExecution)
        .options(joinedload(AgentExecution.job))
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            AgentJob.project_id == project_id_str,
            AgentExecution.tenant_key == current_user.tenant_key,
        )
    )
    agent_result = await db.execute(agent_stmt)
    agents = agent_result.scalars().all()

    if not agents:
        logger.error(f"Project {project_id_str} has no spawned agents")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No agents have been spawned for this project. Please complete staging first.",
        )

    # Update project status
    old_status = project.staging_status
    project.staging_status = "launching"
    project.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        await db.refresh(project)
        logger.info(f"Project {project_id_str} status: {old_status} -> launching ({len(agents)} agents)")
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to update project status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to launch project due to database error"
        ) from e

    # Build agent info response
    agent_info_list = [
        AgentInfo(
            agent_id=str(agent.agent_id),
            job_id=agent.job_id,
            agent_display_name=agent.agent_display_name,
            agent_name=agent.agent_name,
            status=agent.status,
            mission=agent.job.mission,  # Mission is on the job, not execution
            tool_type=agent.tool_type,
            progress=agent.progress,
        )
        for agent in agents
    ]

    # Broadcast WebSocket event
    try:
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="project:launched",
            data={
                "project_id": project_id_str,
                "staging_status": project.staging_status,
                "agent_count": len(agents),
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "launched_by": current_user.username,
            },
        )
        logger.info(f"WebSocket event 'project:launched' broadcasted for {project_id_str}")
    except Exception:
        logger.exception("Failed to broadcast WebSocket event")

    return LaunchProjectResponse(
        success=True,
        project_id=project_id_str,
        staging_status=project.staging_status,
        agent_count=len(agents),
        agents=agent_info_list,
        message=f"Project launched successfully with {len(agents)} agents",
    )


# ============================================================================
# Implementation Phase Gate (Handover 0709)
# ============================================================================


class LaunchImplementationResponse(BaseModel):
    """Response model for launch implementation."""

    success: bool = True
    implementation_launched_at: Optional[str] = None
    already_launched: Optional[bool] = None
    launched_at: Optional[str] = None


@router.patch("/projects/{project_id}/launch-implementation", response_model=LaunchImplementationResponse)
async def launch_implementation(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> LaunchImplementationResponse:
    """
    Set implementation_launched_at timestamp (phase gate release).

    Called when user clicks 'Implement' button in the dashboard.
    Allows agents to receive their missions via get_agent_mission().

    Handover 0709: Implementation phase gate

    Args:
        project_id: Project ID to launch implementation for
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        LaunchImplementationResponse with timestamp

    Raises:
        HTTPException 404: Project not found or tenant isolation violation
    """
    logger.info(f"Launch implementation requested for project {project_id} by {current_user.username}")

    # Get project with tenant isolation
    project = await db.get(Project, project_id)

    if not project or project.tenant_key != current_user.tenant_key:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check if already launched (idempotent)
    if project.implementation_launched_at is not None:
        logger.info(f"Project {project_id} already launched at {project.implementation_launched_at}")
        return LaunchImplementationResponse(
            already_launched=True, launched_at=project.implementation_launched_at.isoformat()
        )

    # Set timestamp
    project.implementation_launched_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(project)

    logger.info(f"Implementation launched for project {project_id} at {project.implementation_launched_at}")

    return LaunchImplementationResponse(
        success=True, implementation_launched_at=project.implementation_launched_at.isoformat()
    )
