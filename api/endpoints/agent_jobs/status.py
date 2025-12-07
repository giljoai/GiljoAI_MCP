"""
Agent Job Status Endpoints - Handover 0124

Handles agent job status and query operations:
- GET /api/agent-jobs/ - List all jobs with filtering (Handover 0135)
- GET /api/agent-jobs/pending - List pending jobs
- GET /api/agent-jobs/{job_id} - Get job details
- GET /api/agent-jobs/{job_id}/mission - Get job mission

All operations use OrchestrationService (no direct DB access).
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService

from .dependencies import get_orchestration_service
from .models import JobListResponse, JobMissionResponse, JobResponse, PendingJobsResponse


logger = logging.getLogger(__name__)
router = APIRouter()


def job_to_response(job: dict) -> JobResponse:
    """
    Convert job dict to JobResponse model.

    Args:
        job: Job dictionary from service

    Returns:
        JobResponse model
    """
    return JobResponse(
        id=job.get("id", 0),
        job_id=job["job_id"],
        tenant_key=job["tenant_key"],
        project_id=job.get("project_id"),
        agent_type=job["agent_type"],
        agent_name=job.get("agent_name"),
        mission=job["mission"],
        status=job["status"],
        progress=job.get("progress", 0),
        spawned_by=job.get("spawned_by"),
        tool_type=job.get("tool_type", "universal"),
        context_chunks=job.get("context_chunks", []),
        messages=job.get("messages", []),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        created_at=job["created_at"],
        updated_at=job.get("updated_at"),
        mission_acknowledged_at=job.get("mission_acknowledged_at"),  # Handover 0297
        steps=job.get("steps"),
    )


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by status (waiting, active, completed, failed)"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type (orchestrator, implementer, etc.)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results (default 100, max 500)"),
    offset: int = Query(0, ge=0, description="Pagination offset (default 0)"),
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> JobListResponse:
    """
    List agent jobs with flexible filtering.

    All jobs are automatically filtered by the authenticated user's tenant_key
    for multi-tenant isolation. Additional filters can be applied via query params.

    Supports pagination for large result sets. Use offset/limit for paging.

    Args:
        project_id: Filter by project UUID (optional)
        status: Filter by job status (optional)
        agent_type: Filter by agent type (optional)
        limit: Maximum results (default 100)
        offset: Pagination offset (default 0)
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)

    Returns:
        JobListResponse with jobs list and pagination metadata

    Raises:
        HTTPException 500: Failed to list jobs

    Example:
        GET /api/agent-jobs/?project_id=abc123&status=active&limit=50
    """
    logger.debug(
        f"User {current_user.username} listing jobs "
        f"(project={project_id}, status={status}, type={agent_type}, "
        f"limit={limit}, offset={offset})"
    )

    result = await orchestration_service.list_jobs(
        tenant_key=current_user.tenant_key,
        project_id=project_id,
        status_filter=status,
        agent_type=agent_type,
        limit=limit,
        offset=offset,
    )

    if "error" in result:
        logger.error(f"Failed to list jobs: {result['error']}")
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list jobs: {result['error']}"
        )

    logger.info(
        f"Found {len(result['jobs'])} jobs for user {current_user.username} "
        f"(total={result['total']}, offset={offset})"
    )

    # Convert job dicts to JobResponse models
    job_responses = [job_to_response(job) for job in result["jobs"]]

    return JobListResponse(
        jobs=job_responses,
        total=result["total"],
        limit=result["limit"],
        offset=result["offset"],
    )


@router.get("/pending", response_model=PendingJobsResponse)
async def list_pending_jobs(
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> PendingJobsResponse:
    """
    List pending jobs for current tenant.

    Returns all unacknowledged jobs in pending status.

    Args:
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)

    Returns:
        PendingJobsResponse with list of pending jobs
    """
    logger.debug(f"User {current_user.username} listing pending jobs")

    # Get pending jobs via OrchestrationService
    result = await orchestration_service.get_pending_jobs(
        tenant_key=current_user.tenant_key
    )

    # Check for errors
    if "error" in result:
        logger.error(f"Failed to get pending jobs: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=result["error"]
        )

    jobs = result.get("jobs", [])
    logger.info(f"Found {len(jobs)} pending jobs for tenant {current_user.tenant_key}")

    return PendingJobsResponse(
        jobs=[job_to_response(job) for job in jobs],
        count=len(jobs)
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> JobResponse:
    """
    Get job details by job_id.

    Args:
        job_id: Job ID to retrieve
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)

    Returns:
        JobResponse with job details

    Raises:
        HTTPException 404: Job not found (includes multi-tenant isolation)
    """
    logger.debug(f"User {current_user.username} getting job {job_id}")

    # Get job via OrchestrationService
    # Note: OrchestrationService doesn't have a get_job_by_id method yet
    # We'll need to use get_agent_mission which includes job details
    result = await orchestration_service.get_agent_mission(
        job_id=job_id,
        tenant_key=current_user.tenant_key
    )

    # Check for errors
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    logger.info(f"Retrieved job {job_id} for tenant {current_user.tenant_key}")

    # Convert result to JobResponse
    # The get_agent_mission returns: job_id, mission, context_chunks, status
    # We need to expand this or call a different service method
    # For now, return what we have (this may need enhancement)
    return job_to_response({
        "id": 0,  # Not available from get_agent_mission
        "job_id": result["job_id"],
        "tenant_key": current_user.tenant_key,
        "agent_type": result.get("agent_type", "unknown"),
        "mission": result["mission"],
        "status": result["status"],
        "spawned_by": result.get("spawned_by"),
        "context_chunks": result.get("context_chunks", []),
        "messages": result.get("messages", []),
        "acknowledged": result.get("acknowledged", False),
        "started_at": result.get("started_at"),
        "completed_at": result.get("completed_at"),
        "created_at": result.get("created_at")
    })


@router.get("/{job_id}/mission", response_model=JobMissionResponse)
async def get_job_mission(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> JobMissionResponse:
    """
    Get job mission by job_id.

    Returns mission text, context chunks, and current status.

    Args:
        job_id: Job ID to retrieve mission for
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)

    Returns:
        JobMissionResponse with mission details

    Raises:
        HTTPException 404: Job not found (includes multi-tenant isolation)
    """
    logger.debug(f"User {current_user.username} getting mission for job {job_id}")

    # Get mission via OrchestrationService
    result = await orchestration_service.get_agent_mission(
        job_id=job_id,
        tenant_key=current_user.tenant_key
    )

    # Check for errors
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_msg)

    logger.info(f"Retrieved mission for job {job_id} for tenant {current_user.tenant_key}")

    return JobMissionResponse(
        job_id=result["job_id"],
        mission=result["mission"],
        context_chunks=result.get("context_chunks", []),
        status=result["status"]
    )
