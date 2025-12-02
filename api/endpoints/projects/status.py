"""
Project Status Endpoints - Handover 0125

Handles project status and query operations:
- GET /{project_id}/status - Get project status
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


@router.get("/{project_id}/status")
async def get_project_status(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    project_service: ProjectService = Depends(get_project_service),
) -> dict:
    """
    Get project status with metrics.

    Args:
        project_id: Project UUID
        current_user: Authenticated user (from dependency)
        project_service: Project service (from dependency)

    Returns:
        Dict with project status and metrics

    Raises:
        HTTPException 404: Project not found
    """
    logger.debug(f"User {current_user.username} getting status for project {project_id}")

    # Get status via ProjectService
    result = await project_service.get_project_status(project_id=project_id)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Project not found")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    logger.info(f"Retrieved status for project {project_id}")
    return result


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

    # Get summary via ProjectService
    result = await project_service.get_project_summary(project_id=project_id)

    # Check for errors
    if not result.get("success"):
        error_msg = result.get("error", "Project not found")
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    logger.info(f"Retrieved summary for project {project_id}")

    # Return data as ProjectSummaryResponse
    summary_data = result.get("data", {})
    return ProjectSummaryResponse(**summary_data)


@router.get("/{project_id}/orchestrator", response_model=OrchestratorResponse)
async def get_project_orchestrator(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrchestratorResponse:
    """
    Get the orchestrator job for a project.

    Returns the orchestrator MCPAgentJob assigned to this project.
    Supports orchestrator succession (Handover 0080) - returns latest instance.
    If no orchestrator exists, creates one automatically.

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
        This endpoint auto-creates orchestrators for backward compatibility.
        The orchestrator is essential for project launch flow.
    """
    from sqlalchemy import select
    from src.giljo_mcp.models import MCPAgentJob, Project

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
    orch_stmt = (
        select(MCPAgentJob)
        .where(
            MCPAgentJob.project_id == project_id,
            MCPAgentJob.agent_type == "orchestrator",
            MCPAgentJob.tenant_key == current_user.tenant_key,
            MCPAgentJob.status.in_(["waiting", "working", "blocked"]),  # Only active statuses
        )
        .order_by(MCPAgentJob.instance_number.desc())
    )
    orch_result = await db.execute(orch_stmt)
    orchestrator = orch_result.scalars().first()

    if not orchestrator:
        # Auto-create orchestrator if missing (backward compatibility)
        orchestrator = MCPAgentJob(
            tenant_key=current_user.tenant_key,
            project_id=project_id,
            agent_type="orchestrator",
            agent_name="Orchestrator",
            mission=(
                "I am ready to create the project mission based on product context "
                "and project description. I will write the mission in the mission window "
                "and select the proper agents below."
            ),
            status="waiting",
            tool_type="universal",
            progress=0,
            acknowledged=False,
            context_chunks=[],
            messages=[],
        )

        db.add(orchestrator)
        await db.commit()
        await db.refresh(orchestrator)

        logger.info(
            f"Auto-created orchestrator {orchestrator.job_id} for project {project_id} "
            f"(user: {current_user.username})"
        )

    logger.info(f"Retrieved orchestrator {orchestrator.job_id} for project {project_id}")

    # Return orchestrator data
    from .models import OrchestratorJobResponse

    return OrchestratorResponse(
        success=True,
        orchestrator=OrchestratorJobResponse(
            id=orchestrator.id,
            job_id=orchestrator.job_id,
            agent_id=orchestrator.job_id,  # Alias for backward compatibility
            agent_type=orchestrator.agent_type,
            agent_name=orchestrator.agent_name,
            mission=orchestrator.mission,
            status=orchestrator.status,
            progress=orchestrator.progress,
            tool_type=orchestrator.tool_type,
            acknowledged=orchestrator.acknowledged,
            created_at=orchestrator.created_at,
            started_at=orchestrator.started_at,
            completed_at=orchestrator.completed_at,
            instance_number=orchestrator.instance_number or 1,
        ),
    )
