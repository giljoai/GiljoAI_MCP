"""
Agent Job Lifecycle Endpoints - Handover 0124

Handles agent job lifecycle operations:
- POST /api/agent-jobs/spawn - Spawn new agent job
- POST /api/agent-jobs/{job_id}/acknowledge - Acknowledge job
- POST /api/agent-jobs/{job_id}/complete - Complete job
- POST /api/agent-jobs/{job_id}/error - Report job error

All operations use OrchestrationService (no direct DB access).
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status

from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency
from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService

from .dependencies import get_orchestration_service
from .models import (
    JobAcknowledgeResponse,
    JobCompleteRequest,
    JobCompleteResponse,
    JobErrorRequest,
    JobErrorResponse,
    SpawnAgentRequest,
    SpawnAgentResponse,
)


logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/spawn", response_model=SpawnAgentResponse, status_code=status.HTTP_201_CREATED)
async def spawn_agent_job(
    request: SpawnAgentRequest,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
) -> SpawnAgentResponse:
    """
    Spawn a new agent job.

    Uses OrchestrationService to create agent job with thin client architecture.
    Broadcasts WebSocket event for real-time UI updates.

    Args:
        request: Spawn request with agent details
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)
        ws_dep: WebSocket dependency for broadcasting (from dependency)

    Returns:
        SpawnAgentResponse with job ID and prompt

    Raises:
        HTTPException 403: User not authorized
        HTTPException 400: Invalid request or spawn failed
    """
    logger.debug(f"User {current_user.username} spawning agent job: {request.agent_display_name}")

    # Permission check - only admins can spawn agents
    if current_user.role != "admin":
        logger.warning(f"User {current_user.username} (role={current_user.role}) attempted to spawn agent")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to spawn agents"
        )

    # Spawn agent job via OrchestrationService
    result = await orchestration_service.spawn_agent_job(
        agent_display_name=request.agent_display_name,
        agent_name=request.agent_name or request.agent_display_name,
        mission=request.mission,
        project_id=request.project_id,
        tenant_key=current_user.tenant_key,
        parent_job_id=request.parent_job_id,
        context_chunks=request.context_chunks
    )

    # Check for errors
    if "error" in result:
        logger.error(f"Failed to spawn agent: {result['error']}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=result["error"]
        )

    # Broadcast WebSocket event for real-time UI
    try:
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="agent:created",
            data={
                "project_id": request.project_id,
                "job_id": result["job_id"],
                "agent_display_name": request.agent_display_name,
                "status": "waiting"
            }
        )
        logger.info(f"Agent spawn broadcasted: {result['job_id']}")
    except Exception:
        logger.exception("Failed to broadcast agent spawn event")
        # Non-critical - continue without broadcast

    logger.info(f"Spawned agent job {result['job_id']} for tenant {current_user.tenant_key}")

    return SpawnAgentResponse(
        success=True,
        job_id=result["job_id"],
        agent_prompt=result.get("agent_prompt", ""),
        mission_stored=result.get("mission_stored", True),
        thin_client=result.get("thin_client", True)
    )


@router.post("/{job_id}/acknowledge", response_model=JobAcknowledgeResponse)
async def acknowledge_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> JobAcknowledgeResponse:
    """
    Acknowledge a job (pending -> active).

    Sets mission_acknowledged_at, status=active, and started_at timestamp.
    Idempotent operation.

    Args:
        job_id: Job ID to acknowledge
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)

    Returns:
        JobAcknowledgeResponse with updated job status

    Raises:
        HTTPException 404: Job not found
        HTTPException 400: Invalid status transition
    """
    logger.debug(f"User {current_user.username} acknowledging job {job_id}")

    # Acknowledge job via OrchestrationService
    result = await orchestration_service.acknowledge_job(
        job_id=job_id,
        tenant_key=current_user.tenant_key
    )

    # Check for errors
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Acknowledged job {job_id} for tenant {current_user.tenant_key}")

    return JobAcknowledgeResponse(
        job_id=job_id,
        status=result.get("status", "active"),
        started_at=result.get("started_at"),
        message=result.get("message", "Job acknowledged successfully")
    )


@router.post("/{job_id}/complete", response_model=JobCompleteResponse)
async def complete_job(
    job_id: str,
    complete_request: JobCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> JobCompleteResponse:
    """
    Mark job as completed (active -> completed).

    Args:
        job_id: Job ID to complete
        complete_request: Completion request with optional result
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)

    Returns:
        JobCompleteResponse with completion details

    Raises:
        HTTPException 404: Job not found
        HTTPException 400: Invalid status transition
    """
    logger.debug(f"User {current_user.username} completing job {job_id}")

    # Complete job via OrchestrationService
    result = await orchestration_service.complete_job(
        job_id=job_id,
        tenant_key=current_user.tenant_key,
        result=complete_request.result
    )

    # Check for errors
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Completed job {job_id} for tenant {current_user.tenant_key}")

    return JobCompleteResponse(
        job_id=job_id,
        status=result.get("status", "completed"),
        completed_at=result.get("completed_at"),
        message=result.get("message", "Job completed successfully")
    )


@router.post("/{job_id}/error", response_model=JobErrorResponse)
async def report_job_error(
    job_id: str,
    error_request: JobErrorRequest,
    current_user: User = Depends(get_current_active_user),
    orchestration_service: OrchestrationService = Depends(get_orchestration_service),
) -> JobErrorResponse:
    """
    Report job error (pending/active -> failed).

    Args:
        job_id: Job ID to mark as failed
        error_request: Error request with error details
        current_user: Authenticated user (from dependency)
        orchestration_service: Service for job operations (from dependency)

    Returns:
        JobErrorResponse with failure details

    Raises:
        HTTPException 404: Job not found
        HTTPException 400: Invalid status transition
    """
    logger.debug(f"User {current_user.username} reporting error for job {job_id}")

    # Report error via OrchestrationService
    result = await orchestration_service.report_error(
        job_id=job_id,
        tenant_key=current_user.tenant_key,
        error_message=error_request.error
    )

    # Check for errors
    if "error" in result:
        error_msg = result["error"]
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg)
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=error_msg)

    logger.info(f"Reported error for job {job_id} for tenant {current_user.tenant_key}")

    return JobErrorResponse(
        job_id=job_id,
        status=result.get("status", "failed"),
        completed_at=result.get("completed_at"),
        message=result.get("message", "Job error reported")
    )
