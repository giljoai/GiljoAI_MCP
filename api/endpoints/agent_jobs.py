"""
Agent Job Management API endpoints for Handover 0019: Agent Job Management System.

Provides REST API for comprehensive agent job operations:
- POST /api/agent-jobs - Create job
- GET /api/agent-jobs - List jobs (with filtering)
- GET /api/agent-jobs/{job_id} - Get job details
- PATCH /api/agent-jobs/{job_id} - Update job
- DELETE /api/agent-jobs/{job_id} - Delete job (admins only)
- POST /api/agent-jobs/{job_id}/acknowledge - Acknowledge job
- POST /api/agent-jobs/{job_id}/complete - Complete job
- POST /api/agent-jobs/{job_id}/fail - Fail job
- POST /api/agent-jobs/{job_id}/messages - Send message
- GET /api/agent-jobs/{job_id}/messages - Get messages
- POST /api/agent-jobs/{job_id}/messages/{message_id}/acknowledge - Ack message
- POST /api/agent-jobs/{job_id}/spawn-children - Spawn children
- GET /api/agent-jobs/{job_id}/hierarchy - Get hierarchy

Job Cancellation & Health Monitoring endpoints for Handover 0107:
- POST /api/agent-jobs/{job_id}/cancel - Cancel job gracefully
- POST /api/agent-jobs/{job_id}/force-fail - Force fail unresponsive job
- GET /api/agent-jobs/{job_id}/health - Get job health metrics

All endpoints enforce role-based access control and multi-tenant isolation.
"""

import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Handover 0086B: Production-grade WebSocket dependency injection
from api.dependencies.websocket import WebSocketDependency, get_websocket_dependency

# Handover 0086B: Production-grade WebSocket dependency injection
from api.schemas.agent_job import (
    JobAcknowledgeResponse,
    JobCancellationRequest,
    JobCancellationResponse,
    JobCompleteRequest,
    JobCompleteResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobFailRequest,
    JobFailResponse,
    JobForceFailRequest,
    JobForceFailResponse,
    JobHealthResponse,
    JobListResponse,
    JobResponse,
    JobUpdateRequest,
    MessageResponse,
    MessageSendRequest,
    MessageThreadItem,
    MessageThreadResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from api.schemas.prompt import BroadcastMessageRequest, BroadcastMessageResponse
from src.giljo_mcp.agent_job_manager import AgentJobManager
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import MCPAgentJob, Project, User
from src.giljo_mcp.slash_commands.handover import handle_gil_handover


logger = logging.getLogger(__name__)
router = APIRouter()


# Helper Functions


def can_access_job(job: MCPAgentJob, user: User) -> bool:
    """
    Check if user can access a job.

    Args:
        job: Job to check
        user: User attempting access

    Returns:
        True if user can access job, False otherwise

    Authorization rules:
    - Jobs must be in same tenant
    """
    return job.tenant_key == user.tenant_key


def can_modify_job(job: MCPAgentJob, user: User) -> bool:
    """
    Check if user can modify a job.

    Args:
        job: Job to check
        user: User attempting modification

    Returns:
        True if user can modify job, False otherwise

    Authorization rules:
    - Admins can modify any job in their tenant
    - Regular users cannot modify jobs (admins only)
    """
    if user.role == "admin":
        return job.tenant_key == user.tenant_key

    return False


def can_delete_job(job: MCPAgentJob, user: User) -> bool:
    """
    Check if user can delete a job.

    Args:
        job: Job to check
        user: User attempting deletion

    Returns:
        True if user can delete job, False otherwise

    Authorization rules:
    - Only admins can delete jobs
    """
    return user.role == "admin" and job.tenant_key == user.tenant_key


def job_to_response(job: MCPAgentJob) -> JobResponse:
    """
    Convert MCPAgentJob model to JobResponse schema.

    Args:
        job: MCPAgentJob model instance

    Returns:
        JobResponse schema
    """
    return JobResponse(
        id=job.id,
        job_id=job.job_id,
        tenant_key=job.tenant_key,
        agent_type=job.agent_type,
        mission=job.mission,
        status=job.status,
        spawned_by=job.spawned_by,
        context_chunks=job.context_chunks or [],
        messages=job.messages or [],
        acknowledged=job.acknowledged,
        started_at=job.started_at,
        completed_at=job.completed_at,
        created_at=job.created_at,
    )


# Job CRUD Endpoints


@router.post("/", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_request: JobCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
    ws_dep: WebSocketDependency = Depends(get_websocket_dependency),
) -> JobCreateResponse:
    """
    Create a new agent job.

    Only admins can create jobs.

    Args:
        job_request: Job creation request
        current_user: Current authenticated user
        db: Database session

    Returns:
        Job creation response with job_id

    Raises:
        HTTPException: 403 if user is not admin
    """
    logger.debug(f"User {current_user.username} creating job")

    # Permission check - only admins can create jobs
    if current_user.role != "admin":
        logger.warning(f"User {current_user.username} (role={current_user.role}) attempted to create job")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required to create jobs")

    # Create job
    job = MCPAgentJob(
        tenant_key=current_user.tenant_key,
        agent_type=job_request.agent_type,
        mission=job_request.mission,
        status="pending",
        spawned_by=job_request.spawned_by,
        context_chunks=job_request.context_chunks or [],
        messages=[],
        acknowledged=False,
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    # Emit WebSocket event for real-time UI update (Handover 0086B Task 3.1)
    # Production-grade implementation with dependency injection
    try:
        # Serialize agent data
        agent_data = {
            "job_id": str(job.job_id),
            "agent_type": job.agent_type,
            "status": "waiting",
            "priority": 5,  # Default priority
            "created_at": job.created_at.isoformat() if job.created_at else datetime.now(timezone.utc).isoformat(),
        }

        # Get project_id if it exists
        project_id = getattr(job, "project_id", None)
        if project_id:
            project_id = str(project_id)

        # Broadcast via dependency injection (multi-tenant isolation enforced)
        sent_count = await ws_dep.broadcast_to_tenant(
            tenant_key=current_user.tenant_key,
            event_type="agent:created",
            data={
                "project_id": project_id,
                "tenant_key": current_user.tenant_key,
                "agent": agent_data,
            },
        )

        logger.info(
            f"Agent creation broadcasted to {sent_count} clients",
            extra={
                "job_id": str(job.job_id),
                "agent_type": job.agent_type,
                "tenant_key": current_user.tenant_key,
                "sent_count": sent_count,
            },
        )
    except Exception:
        logger.exception(
            "Failed to broadcast agent creation",
            extra={"job_id": str(job.job_id), "agent_type": job.agent_type, "tenant_key": current_user.tenant_key},
        )
        # Non-critical - continue without WebSocket broadcast

    logger.info(f"Created job {job.job_id} for tenant {current_user.tenant_key}")

    return JobCreateResponse(job_id=job.job_id, message="Job created successfully")


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    spawned_by: Optional[str] = Query(None, description="Filter by parent job_id"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> JobListResponse:
    """
    List jobs with flexible filtering.

    All jobs are filtered by user's tenant_key (multi-tenant isolation).

    Args:
        status_filter: Filter by job status
        agent_type: Filter by agent type
        spawned_by: Filter by parent job_id
        limit: Maximum number of results
        offset: Number of results to skip
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of jobs matching filters
    """
    logger.debug(f"User {current_user.username} listing jobs")

    # Start with tenant filter (multi-tenant isolation)
    query = select(MCPAgentJob).where(MCPAgentJob.tenant_key == current_user.tenant_key)

    # Apply filters
    if status_filter:
        query = query.where(MCPAgentJob.status == status_filter)

    if agent_type:
        query = query.where(MCPAgentJob.agent_type == agent_type)

    if spawned_by:
        query = query.where(MCPAgentJob.spawned_by == spawned_by)

    # Get total count (before pagination)
    count_query = select(MCPAgentJob).where(MCPAgentJob.tenant_key == current_user.tenant_key)
    if status_filter:
        count_query = count_query.where(MCPAgentJob.status == status_filter)
    if agent_type:
        count_query = count_query.where(MCPAgentJob.agent_type == agent_type)
    if spawned_by:
        count_query = count_query.where(MCPAgentJob.spawned_by == spawned_by)

    total_result = await db.execute(count_query)
    total = len(total_result.scalars().all())

    # Apply pagination
    query = query.order_by(MCPAgentJob.created_at.desc()).offset(offset).limit(limit)

    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

    logger.info(f"Found {len(jobs)} jobs for user {current_user.username} (total={total})")

    return JobListResponse(jobs=[job_to_response(job) for job in jobs], total=total)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> JobResponse:
    """
    Get job details by job_id.

    Args:
        job_id: Job ID to retrieve
        current_user: Current authenticated user
        db: Database session

    Returns:
        Job details

    Raises:
        HTTPException: 404 if job not found (includes multi-tenant isolation)
    """
    logger.debug(f"User {current_user.username} getting job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    return job_to_response(job)


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_update: JobUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> JobResponse:
    """
    Update a job.

    Only admins can update jobs.

    Args:
        job_id: Job ID to update
        job_update: Fields to update
        current_user: Current authenticated user
        db: Database session

    Returns:
        Updated job data

    Raises:
        HTTPException: 403 if user lacks permission
        HTTPException: 404 if job not found
        HTTPException: 400 if status transition invalid
    """
    logger.debug(f"User {current_user.username} updating job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Permission check
    if not can_modify_job(job, current_user):
        logger.warning(f"User {current_user.username} not authorized to update job {job_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this job")

    # Update status if provided
    update_data = job_update.dict(exclude_unset=True)
    if "status" in update_data:
        new_status = update_data["status"]

        # Validate status transition
        valid_transitions = AgentJobManager.VALID_TRANSITIONS.get(job.status, set())

        if new_status not in valid_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from '{job.status}' to '{new_status}'. "
                f"Valid transitions: {valid_transitions or 'none (terminal state)'}",
            )

        job.status = new_status

    await db.commit()
    await db.refresh(job)

    logger.info(f"Updated job {job_id} by user {current_user.username}")

    return job_to_response(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Delete a job.

    Only admins can delete jobs.

    Args:
        job_id: Job ID to delete
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: 403 if user lacks permission
        HTTPException: 404 if job not found
    """
    logger.debug(f"User {current_user.username} deleting job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Permission check
    if not can_delete_job(job, current_user):
        logger.warning(f"User {current_user.username} not authorized to delete job {job_id}")
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only admins can delete jobs")

    await db.delete(job)
    await db.commit()

    logger.info(f"Deleted job {job_id} by user {current_user.username}")


# Job Status Management Endpoints


@router.post("/{job_id}/acknowledge", response_model=JobAcknowledgeResponse)
async def acknowledge_job(
    job_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> JobAcknowledgeResponse:
    """
    Acknowledge a job (pending -> active).

    Sets acknowledged=True, status=active, and started_at timestamp.
    Idempotent operation.

    Args:
        job_id: Job ID to acknowledge
        current_user: Current authenticated user
        db: Database session

    Returns:
        Acknowledgment response

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 400 if status transition invalid
    """
    logger.debug(f"User {current_user.username} acknowledging job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # If already acknowledged, return as-is (idempotent)
    if job.acknowledged and job.status == "active":
        logger.info(f"Job {job_id} already acknowledged, returning current state")
        return JobAcknowledgeResponse(
            job_id=job.job_id, status=job.status, started_at=job.started_at, message="Job already acknowledged"
        )

    # Validate status transition
    if job.status != "pending":
        valid_transitions = AgentJobManager.VALID_TRANSITIONS.get(job.status, set())

        if "active" not in valid_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from '{job.status}' to 'active'. "
                f"Valid transitions: {valid_transitions or 'none (terminal state)'}",
            )

    # Update job
    job.acknowledged = True
    job.status = "active"
    job.started_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(job)

    logger.info(f"Acknowledged job {job_id} for tenant {current_user.tenant_key}")

    return JobAcknowledgeResponse(
        job_id=job.job_id, status=job.status, started_at=job.started_at, message="Job acknowledged successfully"
    )


@router.post("/{job_id}/complete", response_model=JobCompleteResponse)
async def complete_job(
    job_id: str,
    complete_request: JobCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> JobCompleteResponse:
    """
    Mark job as completed (active -> completed).

    Args:
        job_id: Job ID to complete
        complete_request: Completion request with optional result
        current_user: Current authenticated user
        db: Database session

    Returns:
        Completion response

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 400 if status transition invalid
    """
    logger.debug(f"User {current_user.username} completing job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Validate status transition
    valid_transitions = AgentJobManager.VALID_TRANSITIONS.get(job.status, set())

    if "completed" not in valid_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{job.status}' to 'completed'. "
            f"Valid transitions: {valid_transitions or 'none (terminal state)'}",
        )

    # Update job
    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)

    # Add result as message
    if complete_request.result:
        result_msg = {
            "role": "system",
            "type": "completion",
            "content": complete_request.result,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        job.messages = [*job.messages, result_msg]

    await db.commit()
    await db.refresh(job)

    logger.info(f"Completed job {job_id} for tenant {current_user.tenant_key}")

    return JobCompleteResponse(
        job_id=job.job_id, status=job.status, completed_at=job.completed_at, message="Job completed successfully"
    )


@router.post("/{job_id}/fail", response_model=JobFailResponse)
async def fail_job(
    job_id: str,
    fail_request: JobFailRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> JobFailResponse:
    """
    Mark job as failed (pending/active -> failed).

    Args:
        job_id: Job ID to fail
        fail_request: Fail request with optional error details
        current_user: Current authenticated user
        db: Database session

    Returns:
        Fail response

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 400 if status transition invalid
    """
    logger.debug(f"User {current_user.username} failing job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Validate status transition
    valid_transitions = AgentJobManager.VALID_TRANSITIONS.get(job.status, set())

    if "failed" not in valid_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{job.status}' to 'failed'. "
            f"Valid transitions: {valid_transitions or 'none (terminal state)'}",
        )

    # Update job
    job.status = "failed"
    job.completed_at = datetime.now(timezone.utc)

    # Add error as message
    if fail_request.error:
        error_msg = {
            "role": "system",
            "type": "error",
            "content": fail_request.error,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        job.messages = [*job.messages, error_msg]

    await db.commit()
    await db.refresh(job)

    logger.info(f"Failed job {job_id} for tenant {current_user.tenant_key}")

    return JobFailResponse(job_id=job.job_id, status=job.status, completed_at=job.completed_at, message="Job failed")


# Agent Communication Endpoints


@router.post("/{job_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    job_id: str,
    message_request: MessageSendRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Send a message to a job.

    Args:
        job_id: Job ID to send message to
        message_request: Message content
        current_user: Current authenticated user
        db: Database session

    Returns:
        Message response with message_id

    Raises:
        HTTPException: 404 if job not found
    """
    logger.debug(f"User {current_user.username} sending message to job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Create message

    message = {
        "role": message_request.role,
        "type": message_request.type,
        "content": message_request.content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "acknowledged": False,
    }

    # Add message to job
    job.messages = [*job.messages, message]

    await db.commit()
    await db.refresh(job)

    # Message ID is the index in the messages array
    message_id = str(len(job.messages) - 1)

    logger.info(f"Sent message to job {job_id}")

    return MessageResponse(
        message_id=message_id,
        timestamp=message["timestamp"],
        role=message["role"],
        type=message["type"],
        content=message["content"],
        acknowledged=message["acknowledged"],
    )


@router.get("/{job_id}/messages")
async def get_messages(
    job_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Get all messages for a job.

    Args:
        job_id: Job ID to get messages from
        current_user: Current authenticated user
        db: Database session

    Returns:
        List of messages

    Raises:
        HTTPException: 404 if job not found
    """
    logger.debug(f"User {current_user.username} getting messages from job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Return messages with message_id (index)
    messages_with_ids = []
    for idx, msg in enumerate(job.messages or []):
        messages_with_ids.append({"message_id": str(idx), **msg})

    return {"messages": messages_with_ids}


@router.post("/{job_id}/messages/{message_id}/acknowledge", response_model=MessageResponse)
async def acknowledge_message(
    job_id: str,
    message_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> MessageResponse:
    """
    Acknowledge a message.

    Args:
        job_id: Job ID containing the message
        message_id: Message index to acknowledge
        current_user: Current authenticated user
        db: Database session

    Returns:
        Acknowledged message

    Raises:
        HTTPException: 404 if job or message not found
    """
    logger.debug(f"User {current_user.username} acknowledging message {message_id} in job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Get message by index
    try:
        msg_idx = int(message_id)
        if msg_idx < 0 or msg_idx >= len(job.messages or []):
            raise IndexError
    except (ValueError, IndexError) as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found") from e

    # Update message acknowledged status
    messages = job.messages or []
    messages[msg_idx]["acknowledged"] = True
    job.messages = messages

    await db.commit()
    await db.refresh(job)

    logger.info(f"Acknowledged message {message_id} in job {job_id}")

    return MessageResponse(
        message_id=message_id,
        timestamp=messages[msg_idx]["timestamp"],
        role=messages[msg_idx]["role"],
        type=messages[msg_idx]["type"],
        content=messages[msg_idx]["content"],
        acknowledged=True,
    )


# Job Coordination Endpoints


@router.get("/{job_id}/message-thread", response_model=MessageThreadResponse)
async def get_message_thread(
    job_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> MessageThreadResponse:
    """
    Get message thread for a job (Slack-style conversation view).

    Returns messages in chronological order for display in the Kanban dashboard.

    Args:
        job_id: Job ID to get message thread for
        current_user: Current authenticated user
        db: Database session

    Returns:
        Message thread in chronological order

    Raises:
        HTTPException: 404 if job not found (includes multi-tenant isolation)
    """
    logger.debug(f"User {current_user.username} getting message thread for job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Convert messages to MessageThreadItem format
    messages = []
    for idx, msg in enumerate(job.messages or []):
        messages.append(
            MessageThreadItem(
                message_id=str(idx),
                from_=msg.get("from", "unknown"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", ""),
                status=msg.get("status", "pending"),
            )
        )

    logger.info(f"Retrieved {len(messages)} messages for job {job_id}")

    return MessageThreadResponse(job_id=job.job_id, messages=messages)


@router.post("/{job_id}/send-message", response_model=SendMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_developer_message(
    job_id: str,
    message_request: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> SendMessageResponse:
    """
    Send a message from developer to agent.

    Allows developers to communicate with agents working on jobs.
    Messages are added to the job's messages JSONB array.

    Args:
        job_id: Job ID to send message to
        message_request: Message content
        current_user: Current authenticated user
        db: Database session

    Returns:
        Sent message details

    Raises:
        HTTPException: 404 if job not found
        HTTPException: 400 if content is empty
    """
    logger.debug(f"User {current_user.username} sending message to job {job_id}")

    # Validate content
    if not message_request.content or not message_request.content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Create message
    message = {
        "from": "developer",
        "content": message_request.content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending",
    }

    # Add message to job
    job.messages = (job.messages or []) + [message]

    await db.commit()
    await db.refresh(job)

    # Message ID is the index in the messages array
    message_id = str(len(job.messages) - 1)

    logger.info(f"Sent developer message to job {job_id} (message_id={message_id})")

    return SendMessageResponse(
        message_id=message_id,
        from_="developer",
        content=message["content"],
        timestamp=message["timestamp"],
        status=message["status"],
    )


@router.post("/broadcast", response_model=BroadcastMessageResponse)
async def broadcast_message(
    message_request: BroadcastMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Send message to ALL agents in a project (Handover 0073).

    Broadcasts a message from the developer to every agent in the specified project.
    Each agent receives the message in their messages array with a shared broadcast_id
    for tracking purposes.

    Args:
        message_request: Broadcast request with project_id and content
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        BroadcastMessageResponse with broadcast_id, message_ids, and agent_count

    Raises:
        404: Project not found or not accessible
        400: Message content invalid or empty
        403: User not authorized to access project
    """
    logger.debug(f"User {current_user.username} broadcasting to project {message_request.project_id}")

    # Validate content
    if not message_request.content or not message_request.content.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Message content cannot be empty")

    if len(message_request.content) > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Message content exceeds maximum length of 10000 characters"
        )

    # Verify project exists and user has access (multi-tenant isolation)
    project_stmt = select(Project).where(
        Project.id == message_request.project_id, Project.tenant_key == current_user.tenant_key
    )
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        logger.warning(f"Project {message_request.project_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or not accessible")

    # Get all agents in project (multi-tenant isolation)
    agents_stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == message_request.project_id, MCPAgentJob.tenant_key == current_user.tenant_key
    )
    agents_result = await db.execute(agents_stmt)
    agents = agents_result.scalars().all()

    if not agents:
        logger.warning(f"No agents found in project {message_request.project_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="No agents found in project")

    # Generate broadcast ID for tracking
    broadcast_id = str(uuid4())
    timestamp = datetime.now(timezone.utc).isoformat()

    # Create broadcast message template
    broadcast_message = {
        "id": "",  # Will be set per-agent
        "broadcast_id": broadcast_id,
        "from": "developer",
        "to_agent": None,  # Broadcast to all
        "content": message_request.content,
        "timestamp": timestamp,
        "status": "pending",
        "type": "mcp_message",
        "is_broadcast": True,
    }

    # Broadcast to all agents
    message_ids = []
    for agent in agents:
        # Create unique message ID for this agent
        message_id = str(uuid4())
        agent_message = {**broadcast_message, "id": message_id}

        # Append to agent's messages array
        agent.messages = (agent.messages or []) + [agent_message]
        message_ids.append(message_id)

    # Commit all changes
    await db.commit()

    logger.info(f"Broadcast {broadcast_id} sent to {len(agents)} agents in project {message_request.project_id}")

    # Broadcast WebSocket event (if available)
    try:
        # Lazy import to avoid circular dependency
        from api.app import state

        if state.websocket_manager:
            await state.websocket_manager.broadcast_to_project(
                message_request.project_id,
                {
                    "type": "message:broadcast",
                    "broadcast_id": broadcast_id,
                    "project_id": message_request.project_id,
                    "agent_count": len(agents),
                    "content_preview": message_request.content[:100],
                    "timestamp": timestamp,
                },
            )
    except Exception:
        logger.warning("Failed to broadcast WebSocket event")
        # Don't fail the request if WebSocket broadcast fails

    return BroadcastMessageResponse(
        broadcast_id=broadcast_id, message_ids=message_ids, agent_count=len(agents), timestamp=timestamp
    )


# ============================================================================
# Orchestrator Succession Endpoints (Handover 0080a)
# ============================================================================


class SuccessionTriggerResponse(BaseModel):
    """Response model for succession trigger"""

    success: bool
    message: str
    successor_id: Optional[str] = None
    launch_prompt: Optional[str] = None
    handover_summary: Optional[dict] = None
    error: Optional[str] = None


@router.post("/{job_id}/trigger_succession", response_model=SuccessionTriggerResponse)
async def trigger_succession(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Trigger orchestrator succession (Handover 0080a).

    Creates a successor orchestrator instance and marks the current
    orchestrator as complete with handover. Only available for
    orchestrator agents.

    Args:
        job_id: Orchestrator job ID
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        SuccessionTriggerResponse with successor details and launch prompt

    Raises:
        404: Orchestrator job not found
        400: Job is not an orchestrator or already handed over
        403: User not authorized to access job
    """
    logger.debug(f"User {current_user.username} triggering succession for job {job_id}")

    # Execute succession handler (reuse slash command logic)
    result = await handle_gil_handover(
        db_session=db,
        tenant_key=current_user.tenant_key,
        orchestrator_job_id=job_id,
    )

    # Map result to response
    if not result.get("success"):
        # Determine appropriate HTTP status code based on error type
        error = result.get("error", "UNKNOWN")
        if error in ("NO_ORCHESTRATOR", "INVALID_ORCHESTRATOR"):
            status_code = status.HTTP_404_NOT_FOUND
        elif error in ("ALREADY_HANDED_OVER", "SUCCESSOR_EXISTS"):
            status_code = status.HTTP_409_CONFLICT
        else:
            status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

        raise HTTPException(status_code=status_code, detail=result.get("message"))

    return SuccessionTriggerResponse(**result)


# ============================================================================
# Job Cancellation & Health Monitoring Endpoints (Handover 0107)
# ============================================================================


@router.post("/{job_id}/cancel", response_model=JobCancellationResponse)
async def cancel_job(
    job_id: str,
    cancellation_request: JobCancellationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> JobCancellationResponse:
    """
    Cancel a job gracefully (Handover 0107).

    Sets job status to 'cancelled' and records cancellation reason.
    This is a graceful cancellation that allows agents to detect and respond.

    Args:
        job_id: Job ID to cancel
        cancellation_request: Cancellation request with reason
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        JobCancellationResponse with cancellation details

    Raises:
        404: Job not found
        400: Invalid status transition
        403: User not authorized to access job
    """
    logger.debug(f"User {current_user.username} cancelling job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Validate status - cannot cancel completed or failed jobs
    if job.status in ("complete", "failed"):
        logger.warning(f"Cannot cancel job {job_id} with status '{job.status}'")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=f"Cannot cancel job with status '{job.status}'"
        )

    # Update job status
    job.status = "blocked"  # Use 'blocked' as closest existing status for cancellation
    job.block_reason = f"Cancelled: {cancellation_request.reason}"
    cancelled_at = datetime.now(timezone.utc)

    # Add cancellation message
    cancellation_msg = {
        "role": "system",
        "type": "cancellation",
        "content": cancellation_request.reason,
        "timestamp": cancelled_at.isoformat(),
    }
    job.messages = (job.messages or []) + [cancellation_msg]

    await db.commit()
    await db.refresh(job)

    logger.info(f"Cancelled job {job_id} for tenant {current_user.tenant_key}, reason: {cancellation_request.reason}")

    return JobCancellationResponse(
        job_id=job.job_id, status=job.status, message="Job cancelled successfully", cancelled_at=cancelled_at
    )


@router.post("/{job_id}/force-fail", response_model=JobForceFailResponse)
async def force_fail_job(
    job_id: str,
    force_fail_request: JobForceFailRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> JobForceFailResponse:
    """
    Force fail a job (Handover 0107).

    Immediately transitions job to 'failed' status with reason.
    Use this for unresponsive agents or critical failures.

    Args:
        job_id: Job ID to force fail
        force_fail_request: Force fail request with reason
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        JobForceFailResponse with failure details and updated job

    Raises:
        404: Job not found
        403: User not authorized to access job
    """
    logger.debug(f"User {current_user.username} force failing job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Update job status to failed
    job.status = "failed"
    job.completed_at = datetime.now(timezone.utc)

    # Add force fail message
    force_fail_msg = {
        "role": "system",
        "type": "error",
        "content": f"Force failed: {force_fail_request.reason}",
        "timestamp": job.completed_at.isoformat(),
    }
    job.messages = (job.messages or []) + [force_fail_msg]

    await db.commit()
    await db.refresh(job)

    logger.warning(
        f"Force failed job {job_id} for tenant {current_user.tenant_key}, reason: {force_fail_request.reason}"
    )

    return JobForceFailResponse(
        job_id=job.job_id, status=job.status, message="Job force failed successfully", job=job_to_response(job)
    )


@router.get("/{job_id}/health", response_model=JobHealthResponse)
async def get_job_health(
    job_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
) -> JobHealthResponse:
    """
    Get job health metrics (Handover 0107).

    Returns health information including last progress time and staleness detection.
    A job is considered stale if no progress has been made in > 10 minutes.

    Args:
        job_id: Job ID to check health
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        JobHealthResponse with health metrics

    Raises:
        404: Job not found
        403: User not authorized to access job
    """
    logger.debug(f"User {current_user.username} checking health for job {job_id}")

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Calculate health metrics
    now = datetime.now(timezone.utc)

    # Determine last progress timestamp (most recent of started_at or last_health_check)
    last_progress_at = None
    if job.started_at:
        last_progress_at = job.started_at
    if job.last_health_check and (not last_progress_at or job.last_health_check > last_progress_at):
        last_progress_at = job.last_health_check

    # Calculate minutes since progress
    minutes_since_progress = None
    if last_progress_at:
        delta = now - last_progress_at
        minutes_since_progress = int(delta.total_seconds() / 60)

    # Determine if job is stale (> 10 minutes without progress)
    is_stale = False
    if minutes_since_progress is not None and minutes_since_progress > 10:
        is_stale = True

    # Format timestamps as ISO strings
    last_progress_str = last_progress_at.isoformat() if last_progress_at else None
    last_message_check_str = job.last_health_check.isoformat() if job.last_health_check else None

    logger.info(
        f"Health check for job {job_id}: status={job.status}, "
        f"minutes_since_progress={minutes_since_progress}, is_stale={is_stale}"
    )

    return JobHealthResponse(
        job_id=job.job_id,
        status=job.status,
        last_progress_at=last_progress_str,
        last_message_check_at=last_message_check_str,
        minutes_since_progress=minutes_since_progress,
        is_stale=is_stale,
    )
