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
from src.giljo_mcp.exceptions import (
    AuthorizationError,
    ResourceNotFoundError,
    ValidationError,
)
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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required to spawn agents")

    try:
        result = await orchestration_service.spawn_agent_job(
            agent_display_name=request.agent_display_name,
            agent_name=request.agent_name or request.agent_display_name,
            mission=request.mission,
            project_id=request.project_id,
            tenant_key=current_user.tenant_key,
            parent_job_id=request.parent_job_id,
            context_chunks=request.context_chunks,
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error spawning agent: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e

    # Broadcast WebSocket event for real-time UI
    # NOTE: OrchestrationService already broadcasts agent:created, but we broadcast again
    # to ensure the endpoint's caller gets the event even if the service broadcast failed.
    # Handover 0457: Include execution_id for frontend Map key consistency
    try:
        await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="agent:created",
            data={
                "project_id": request.project_id,
                "execution_id": result.get("execution_id"),  # Handover 0457: Unique row ID for frontend Map key
                "agent_id": result.get("agent_id"),  # Handover 0457: Executor UUID
                "job_id": result["job_id"],
                "agent_display_name": request.agent_display_name,
                "agent_name": request.agent_name or request.agent_display_name,
                "status": "waiting",
                "mission": request.mission,  # Handover 0464: Include mission for UI display
            },
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
        thin_client=result.get("thin_client", True),
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

    try:
        result = await orchestration_service.acknowledge_job(job_id=job_id, tenant_key=current_user.tenant_key)

        logger.info(f"Acknowledged job {job_id} for tenant {current_user.tenant_key}")

        # Service returns {"job": {...}, "next_instructions": ...}
        job_data = result.get("job", {})
        return JobAcknowledgeResponse(
            job_id=job_id,
            status=job_data.get("status", "active"),
            started_at=job_data.get("started_at"),
            message=result.get("next_instructions", "Job acknowledged successfully"),
        )
    except (ResourceNotFoundError, ValidationError, AuthorizationError):
        # Let domain exceptions propagate to global exception handler
        raise
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error acknowledging job: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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

    try:
        # Service expects result as dict, wrap string result for compatibility
        result_dict = {"summary": complete_request.result} if complete_request.result else {"summary": "Job completed"}
        result = await orchestration_service.complete_job(
            job_id=job_id, tenant_key=current_user.tenant_key, result=result_dict
        )

        logger.info(f"Completed job {job_id} for tenant {current_user.tenant_key}")

        # Service returns {"status": "success", "job_id": ..., "message": ...}
        # Response model expects execution status, not result status
        return JobCompleteResponse(
            job_id=job_id,
            status="completed",  # Fixed: execution status, not result status
            completed_at=None,  # Not returned by service
            message=result.get("message", "Job completed successfully"),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error completing job: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e


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

    try:
        result = await orchestration_service.report_error(
            job_id=job_id, tenant_key=current_user.tenant_key, error=error_request.error
        )

        logger.info(f"Reported error for job {job_id} for tenant {current_user.tenant_key}")

        # Service returns {"status": "success", "job_id": ..., "message": ...}
        # Response model expects execution status (blocked), not result status
        return JobErrorResponse(
            job_id=job_id,
            status="blocked",  # Fixed: execution status, not result status
            completed_at=None,  # Not returned by service
            message=result.get("message", "Job error reported"),
        )
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except AuthorizationError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Unexpected error reporting job error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error") from e
