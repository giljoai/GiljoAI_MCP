"""
Orchestration API Endpoints - Mission Regeneration & Project Launch

Handover 0086B Task 3.3 - Mission Regeneration
Handover 0109 Agent 1 - Project Launch Endpoint
Created: 2025-11-02
Updated: 2025-01-06
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import MCPAgentJob, Product, Project, User


logger = logging.getLogger(__name__)
router = APIRouter(tags=["orchestration"])


class RegenerateMissionRequest(BaseModel):
    project_id: UUID
    override_field_priorities: Optional[dict[str, int]] = None
    override_serena_enabled: Optional[bool] = None


class RegenerateMissionResponse(BaseModel):
    mission: str
    token_estimate: int
    user_config_applied: bool
    serena_enabled: bool
    field_priorities_used: dict[str, int]


class LaunchProjectRequest(BaseModel):
    """Request model for launching a project."""

    project_id: UUID


class AgentInfo(BaseModel):
    """Agent information for launch response."""

    agent_id: str
    job_id: str
    agent_type: str
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


async def _get_user_config_with_overrides(
    user_id: UUID,
    db: AsyncSession,
    override_priorities: Optional[dict[str, int]],
    override_serena: Optional[bool],
) -> dict:
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
):
    logger.info(f"Mission regeneration requested for project {request.project_id}")

    result = await db.execute(select(Project).filter_by(id=request.project_id, tenant_key=current_user.tenant_key))
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    result = await db.execute(select(Product).filter_by(id=project.product_id, tenant_key=current_user.tenant_key))
    product = result.scalar_one_or_none()

    if not product:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    user_config = await _get_user_config_with_overrides(
        user_id=current_user.id,
        db=db,
        override_priorities=request.override_field_priorities,
        override_serena=request.override_serena_enabled,
    )

    mission_text = f"Mission for {project.name}: {project.mission}"
    token_estimate = len(mission_text) // 4

    try:
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="project:mission_updated",
            data={
                "project_id": str(request.project_id),
                "tenant_key": current_user.tenant_key,
                "mission": mission_text,
                "token_estimate": token_estimate,
                "generated_by": "user",
                "user_config_applied": True,
                "field_priorities": user_config["field_priorities"],
            },
        )
    except Exception:
        logger.exception("Failed to broadcast WebSocket event")

    return RegenerateMissionResponse(
        mission=mission_text,
        token_estimate=token_estimate,
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
):
    """
    Launch a staged project - transition from staging to execution phase.

    This endpoint is called when user clicks "Launch Jobs" button after staging completes.
    It validates that the project has a mission and spawned agents, then transitions
    the project to 'launching' status and broadcasts WebSocket event for UI updates.

    Handover 0109 Agent 1 - Project Launch Endpoint

    Args:
        request: LaunchProjectRequest containing project_id
        current_user: Authenticated user (auto-injected by JWT middleware)
        db: Database session (auto-injected)
        ws_dep: WebSocket dependency for broadcasting (auto-injected)

    Returns:
        LaunchProjectResponse with agent data and updated status

    Raises:
        HTTPException 404: Project not found or tenant mismatch
        HTTPException 400: Project missing mission or no agents spawned
    """
    project_id_str = str(request.project_id)
    logger.info(f"Launch project requested for project {project_id_str} by user {current_user.username}")

    # Step 1: Fetch project with multi-tenant isolation
    stmt = select(Project).where(
        Project.id == project_id_str,
        Project.tenant_key == current_user.tenant_key,
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        logger.warning(f"Project {project_id_str} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Step 2: Validate project is not soft-deleted
    if project.deleted_at is not None:
        logger.warning(f"Attempted to launch soft-deleted project {project_id_str}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Step 3: Validate mission exists (created during staging)
    if not project.mission or project.mission.strip() == "":
        logger.error(f"Project {project_id_str} has no mission - staging incomplete")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project mission has not been created. Please complete staging first.",
        )

    # Step 4: Fetch spawned agents with multi-tenant isolation
    agent_stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == project_id_str,
        MCPAgentJob.tenant_key == current_user.tenant_key,
    )
    agent_result = await db.execute(agent_stmt)
    agents = agent_result.scalars().all()

    if not agents or len(agents) == 0:
        logger.error(f"Project {project_id_str} has no spawned agents")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No agents have been spawned for this project. Please complete staging first.",
        )

    # Step 5: Update project staging_status to 'launching'
    old_status = project.staging_status
    project.staging_status = "launching"
    project.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        await db.refresh(project)
        logger.info(
            f"Project {project_id_str} status updated: {old_status} -> launching "
            f"({len(agents)} agents ready)"
        )
    except Exception as e:
        await db.rollback()
        logger.exception("Failed to update project status")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to launch project due to database error",
        ) from e

    # Step 6: Build agent info response
    agent_info_list = [
        AgentInfo(
            agent_id=str(agent.id),
            job_id=agent.job_id,
            agent_type=agent.agent_type,
            agent_name=agent.agent_name,
            status=agent.status,
            mission=agent.mission,
            tool_type=agent.tool_type,
            progress=agent.progress,
        )
        for agent in agents
    ]

    # Step 7: Broadcast WebSocket event for UI updates
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
        logger.info(f"WebSocket event 'project:launched' broadcasted for project {project_id_str}")
    except Exception:
        # Non-fatal: log but don't fail the request
        logger.exception("Failed to broadcast WebSocket event")

    # Step 8: Return success response
    return LaunchProjectResponse(
        success=True,
        project_id=project_id_str,
        staging_status=project.staging_status,
        agent_count=len(agents),
        agents=agent_info_list,
        message=f"Project launched successfully with {len(agents)} agents",
    )
