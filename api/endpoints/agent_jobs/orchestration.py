# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Orchestration Endpoints - Handover 0124

Handles project orchestration operations:
- GET /api/agent-jobs/workflow/{project_id} - Get workflow status
- POST /api/agent-jobs/launch-project - Launch staged project
- PATCH /api/agent-jobs/projects/{project_id}/launch-implementation - Launch implementation phase

All operations use OrchestrationService (no direct DB access).

Note: regenerate-mission endpoint removed in Handover 0729 (never integrated with frontend).
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
from src.giljo_mcp.models import Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.services.orchestration_service import OrchestrationService
from src.giljo_mcp.utils.log_sanitizer import sanitize

from .dependencies import get_orchestration_service
from .models import WorkflowStatusResponse


logger = logging.getLogger(__name__)
router = APIRouter()


# ============================================================================
# Orchestration Models (from old orchestration.py)
# ============================================================================


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
    logger.debug(
        "User %s getting workflow status for project %s", sanitize(current_user.username), sanitize(project_id)
    )

    # Get workflow status via OrchestrationService
    result = await orchestration_service.get_workflow_status(project_id=project_id, tenant_key=current_user.tenant_key)

    logger.info("Retrieved workflow status for project %s", sanitize(project_id))

    # 0731d: OrchestrationService returns WorkflowStatus typed model
    return WorkflowStatusResponse(
        project_id=project_id,
        status=result.current_stage,
        agent_count=result.total_agents,
        completed_count=result.completed_agents,
        active_count=result.active_agents,
        blocked_count=result.blocked_agents,
        silent_count=result.silent_agents,
        decommissioned_count=result.decommissioned_agents,
        pending_count=result.pending_agents,
        progress_percent=int(result.progress_percent),
    )


# ============================================================================
# Launch Endpoints
# ============================================================================


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
    logger.info("Launch project requested for %s by %s", sanitize(project_id_str), sanitize(current_user.username))

    # Fetch project with multi-tenant isolation
    stmt = select(Project).where(
        Project.id == project_id_str,
        Project.tenant_key == current_user.tenant_key,
    )
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project or project.deleted_at is not None:
        logger.warning(
            "Project %s not found for tenant %s", sanitize(project_id_str), sanitize(current_user.tenant_key)
        )
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Validate mission exists
    if not project.mission or project.mission.strip() == "":
        logger.error("Project %s has no mission", sanitize(project_id_str))
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
        logger.error("Project %s has no spawned agents", sanitize(project_id_str))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No agents have been spawned for this project. Please complete staging first.",
        )

    # Update project timestamp (staging_status stays "staged" — implementation tracked by implementation_launched_at)
    project.updated_at = datetime.now(timezone.utc)

    try:
        await db.commit()
        await db.refresh(project)
        logger.info("Project %s launching implementation (%d agents)", sanitize(project_id_str), len(agents))
    except Exception as e:  # Broad catch: API boundary, converts to HTTP error
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
        logger.info("WebSocket event 'project:launched' broadcasted for %s", sanitize(project_id_str))
    except Exception:  # Broad catch: API boundary, converts to HTTP error
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
    logger.info(
        "Launch implementation requested for project %s by %s", sanitize(project_id), sanitize(current_user.username)
    )

    # Get project with tenant isolation (query-level filtering, not post-fetch check)
    project_result = await db.execute(
        select(Project).where(
            Project.id == project_id,
            Project.tenant_key == current_user.tenant_key,
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    # Check if already launched (idempotent)
    if project.implementation_launched_at is not None:
        logger.info("Project %s already launched at %s", sanitize(project_id), project.implementation_launched_at)
        return LaunchImplementationResponse(
            already_launched=True, launched_at=project.implementation_launched_at.isoformat()
        )

    # Set timestamp
    project.implementation_launched_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(project)

    logger.info(
        "Implementation launched for project %s at %s", sanitize(project_id), project.implementation_launched_at
    )

    return LaunchImplementationResponse(
        success=True, implementation_launched_at=project.implementation_launched_at.isoformat()
    )
