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
        This endpoint auto-creates orchestrators for backward compatibility.
        The orchestrator is essential for project launch flow.
    """
    from sqlalchemy import select
    from sqlalchemy.orm import joinedload
    from uuid import uuid4
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
            AgentExecution.agent_type == "orchestrator",
            AgentExecution.tenant_key == current_user.tenant_key,
            AgentExecution.status.in_(["waiting", "working", "blocked"]),  # Only active statuses
        )
        .order_by(AgentExecution.instance_number.desc())
    )
    orch_result = await db.execute(orch_stmt)
    orchestrator_execution = orch_result.scalars().first()

    if not orchestrator_execution:
        # Auto-create orchestrator if missing (backward compatibility)
        # Following pattern from tool_accessor.py:1477-1510
        # Create both AgentJob (work order) and AgentExecution (executor instance)
        job_id = str(uuid4())
        agent_id = str(uuid4())

        # Step 1: Create AgentJob (work order)
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=current_user.tenant_key,
            project_id=project_id,
            mission=(
                "I am ready to create the project mission based on product context "
                "and project description. I will write the mission in the mission window "
                "and select the proper agents below."
            ),
            job_type="orchestrator",
            status="active",
        )
        db.add(agent_job)

        # Step 2: Create AgentExecution (executor instance)
        orchestrator_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,  # FK to AgentJob
            tenant_key=current_user.tenant_key,
            agent_type="orchestrator",
            agent_name="Orchestrator",
            instance_number=1,
            status="waiting",
            progress=0,
            tool_type="universal",
            messages=[],
        )
        db.add(orchestrator_execution)
        await db.commit()
        await db.refresh(orchestrator_execution)
        await db.refresh(agent_job)

        # Set the job relationship for response mapping
        orchestrator_execution.job = agent_job

        logger.info(
            f"Auto-created orchestrator {job_id} (agent_id: {agent_id}) for project {project_id} "
            f"(user: {current_user.username})"
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
            agent_type=orchestrator_execution.agent_type,  # From AgentExecution
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
