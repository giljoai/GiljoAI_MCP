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

from fastapi import APIRouter, Depends, Query

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService

from .dependencies import get_orchestration_service
from .models import JobListResponse, JobMissionResponse, JobResponse, PendingJobsResponse, TodoItemResponse


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
    # Handover 0423: Convert todo_items to TodoItemResponse list
    todo_items_raw = job.get("todo_items", [])
    todo_items = [
        TodoItemResponse(content=item.get("content", ""), status=item.get("status", "pending"))
        for item in todo_items_raw
        if isinstance(item, dict)
    ]

    return JobResponse(
        id=job.get("agent_id", job.get("id", "")),  # 0366: prefer agent_id (UUID)
        job_id=job["job_id"],
        agent_id=job.get("agent_id"),  # Handover 0401: Executor UUID for WebSocket event matching
        execution_id=job.get("execution_id"),  # UNIQUE per row - use as Map key
        tenant_key=job["tenant_key"],
        project_id=job.get("project_id"),
        agent_display_name=job["agent_display_name"],
        agent_name=job.get("agent_name"),
        mission=job["mission"],
        status=job["status"],
        progress=job.get("progress", 0),
        spawned_by=job.get("spawned_by"),
        tool_type=job.get("tool_type", "universal"),
        context_chunks=job.get("context_chunks", []),
        # Handover 0407: Counter fields for message tracking (used by frontend store)
        messages_sent_count=job.get("messages_sent_count", 0),
        messages_waiting_count=job.get("messages_waiting_count", 0),
        messages_read_count=job.get("messages_read_count", 0),
        started_at=job.get("started_at"),
        completed_at=job.get("completed_at"),
        created_at=job["created_at"],
        updated_at=job.get("updated_at"),
        steps=job.get("steps"),
        todo_items=todo_items,  # Handover 0423
        phase=job.get("phase"),  # Handover 0411a
        result=job.get("result"),  # Handover 0497e
    )


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(
        None, description="Filter by status (waiting, working, blocked, complete, silent, decommissioned)"
    ),
    agent_display_name: Optional[str] = Query(
        None, description="Filter by agent display name (orchestrator, implementer, etc.)"
    ),
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
        agent_display_name: Filter by agent display name (optional)
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
        f"(project={project_id}, status={status}, type={agent_display_name}, "
        f"limit={limit}, offset={offset})"
    )

    # Service raises OrchestrationError on failure, caught by global exception handler
    result = await orchestration_service.list_jobs(
        tenant_key=current_user.tenant_key,
        project_id=project_id,
        status_filter=status,
        agent_display_name=agent_display_name,
        limit=limit,
        offset=offset,
    )

    # 0731d: OrchestrationService returns JobListResult typed model
    logger.info(
        f"Found {len(result.jobs)} jobs for user {current_user.username} (total={result.total}, offset={offset})"
    )

    # Convert job dicts to JobResponse models
    job_responses = [job_to_response(job) for job in result.jobs]

    return JobListResponse(
        jobs=job_responses,
        total=result.total,
        limit=result.limit,
        offset=result.offset,
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

    # Service raises exceptions on failure, caught by global exception handler
    result = await orchestration_service.get_pending_jobs(tenant_key=current_user.tenant_key)

    # 0731d: OrchestrationService returns PendingJobsResult typed model
    jobs = result.jobs
    logger.info(f"Found {len(jobs)} pending jobs for tenant {current_user.tenant_key}")

    return PendingJobsResponse(jobs=[job_to_response(job) for job in jobs], count=len(jobs))


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

    result = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key=current_user.tenant_key)

    logger.info(f"Retrieved job {job_id} for tenant {current_user.tenant_key}")

    # 0731d: OrchestrationService returns MissionResponse typed model
    # Convert to JobResponse via dict bridge (MissionResponse has different field set)
    return job_to_response(
        {
            "agent_id": result.agent_id or "",  # 0366: use agent_id
            "job_id": result.job_id,
            "tenant_key": current_user.tenant_key,
            "agent_display_name": result.agent_display_name or "unknown",
            "mission": result.mission or "",
            "status": result.status or "unknown",
            "spawned_by": result.parent_job_id,
            "context_chunks": [],
            "started_at": result.started_at,
            "completed_at": None,
            "created_at": result.created_at,
        }
    )


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

    result = await orchestration_service.get_agent_mission(job_id=job_id, tenant_key=current_user.tenant_key)

    logger.info(f"Retrieved mission for job {job_id} for tenant {current_user.tenant_key}")

    # 0731d: OrchestrationService returns MissionResponse typed model
    return JobMissionResponse(
        job_id=result.job_id,
        mission=result.mission or "",
        context_chunks=[],
        status=result.status or "unknown",
    )
