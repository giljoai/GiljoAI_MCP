"""
Project Status Endpoints - Handover 0125

Handles project status and query operations:
- GET /{project_id}/summary - Get project summary (Handover 0504)
- GET /{project_id}/orchestrator - Get orchestrator job

All operations use ProjectService where available.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.models.schemas import ProjectSummaryResponse
from src.giljo_mcp.services.project_service import ProjectService

from .dependencies import get_project_service
from .models import OrchestratorResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse)
async def get_project_summary(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> ProjectSummaryResponse:
    """
    Get comprehensive project summary with metrics (Handover 0504).

    Returns project overview including job statistics, completion metrics,
    and activity timestamps for dashboard display.

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        ProjectSummaryResponse with project metrics and status

    Raises:
        HTTPException 404: Project not found
        HTTPException 500: Internal server error
    """
    logger.debug(f"User {current_user.username} getting summary for project {project_id}")

    # Get summary via ProjectService (raises exceptions on error)
    summary_data = await project_service.get_project_summary(project_id=project_id)

    logger.info(f"Retrieved summary for project {project_id}")

    return ProjectSummaryResponse(**summary_data)


@router.get("/{project_id}/orchestrator", response_model=OrchestratorResponse)
async def get_project_orchestrator(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrchestratorResponse:
    """
    Get the orchestrator job for a project.

    Returns the orchestrator AgentExecution (executor) with AgentJob (work order) data.
    Supports orchestrator succession (Handover 0080) - returns latest instance.
    If no orchestrator exists, creates one automatically using the dual-model pattern.

    Migration (Handover 0367b):
    - Queries AgentExecution joined with AgentJob (legacy model removed)
    - Creates BOTH AgentJob (work order) + AgentExecution (executor instance)
    - Response maps from AgentExecution fields + AgentJob.mission

    Args:
        project_id: Project UUID or alias
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        Orchestrator job data with full job_id/agent_id

    Raises:
        HTTPException 404: Project not found
        HTTPException 500: Database error

    Note:
        Handover 0506: Removed auto-creation. Returns null orchestrator if none exists.
        Frontend shows "Re-launch Orchestrator" button when orchestrator is null.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from src.giljo_mcp.models import Project
    from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

    logger.debug(
        f"User {current_user.username} getting orchestrator for project {project_id}"
    )

    # Verify project exists and user has access
    project_stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == current_user.tenant_key
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project not found: {project_id}"
        )

    # Find orchestrator - support succession (get latest ACTIVE instance)
    # FIX: Filter by active statuses to avoid returning cancelled/failed orchestrators
    # Bug: Previously returned cancelled orchestrators causing "Project not ready to launch" error
    # MIGRATION: Query AgentExecution joined with AgentJob (Handover 0367b)
    orch_stmt = (
        select(AgentExecution)
        .options(joinedload(AgentExecution.job))
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            AgentJob.project_id == project_id,
            AgentExecution.agent_display_name == "orchestrator",
            AgentExecution.tenant_key == current_user.tenant_key,
            # Include complete/handed_over to show finished orchestrators (Handover 0506)
            # Previously excluded these, causing auto-spawn bug when viewing completed projects
            AgentExecution.status.in_(["waiting", "working", "blocked", "complete", "handed_over"]),
        )
        .order_by(AgentExecution.instance_number.desc())
    )
    orch_result = await db.execute(orch_stmt)
    orchestrator_execution = orch_result.scalars().first()

    if not orchestrator_execution:
        # Handover 0506: No auto-creation - return null orchestrator
        # Frontend shows "Re-launch Orchestrator" button when orchestrator is null
        logger.info(f"No orchestrator found for project {project_id} (user: {current_user.username})")
        return OrchestratorResponse(
            success=True,
            orchestrator=None
        )

    logger.info(
        f"Retrieved orchestrator execution {orchestrator_execution.agent_id} "
        f"(job: {orchestrator_execution.job_id}) for project {project_id}"
    )

    # Return orchestrator data - map from AgentExecution + AgentJob
    from .models import OrchestratorJobResponse

    return OrchestratorResponse(
        success=True,
        orchestrator=OrchestratorJobResponse(
            id=None,  # Deprecated field (Handover 0366a)
            job_id=orchestrator_execution.job_id,  # AgentJob.job_id
            agent_id=orchestrator_execution.agent_id,  # AgentExecution.agent_id (executor UUID)
            agent_display_name=orchestrator_execution.agent_display_name,  # From AgentExecution
            agent_name=orchestrator_execution.agent_name,  # From AgentExecution
            mission=orchestrator_execution.job.mission,  # From AgentJob
            status=orchestrator_execution.status,  # From AgentExecution
            progress=orchestrator_execution.progress,  # From AgentExecution
            tool_type=orchestrator_execution.tool_type,  # From AgentExecution
            created_at=orchestrator_execution.started_at or orchestrator_execution.job.created_at,
            started_at=orchestrator_execution.started_at,  # From AgentExecution
            completed_at=orchestrator_execution.completed_at,  # From AgentExecution
            instance_number=orchestrator_execution.instance_number or 1,  # From AgentExecution
        ),
    )
