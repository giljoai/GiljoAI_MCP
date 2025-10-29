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

Kanban Board API endpoints for Handover 0066: Agent Kanban Dashboard:
- GET /api/agent-jobs/kanban/{project_id} - Get Kanban board data
- GET /api/agent-jobs/{job_id}/message-thread - Get message thread
- POST /api/agent-jobs/{job_id}/send-message - Send developer message

All endpoints enforce role-based access control and multi-tenant isolation.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.agent_job import (
    ChildJobSpec,
    JobAcknowledgeResponse,
    JobCompleteRequest,
    JobCompleteResponse,
    JobCreateRequest,
    JobCreateResponse,
    JobFailRequest,
    JobFailResponse,
    JobHierarchyResponse,
    JobListResponse,
    JobResponse,
    JobSpawnRequest,
    JobSpawnResponse,
    JobUpdateRequest,
    KanbanBoardResponse,
    KanbanColumn,
    KanbanJobCard,
    MessageCounts,
    MessageResponse,
    MessageSendRequest,
    MessageThreadItem,
    MessageThreadResponse,
    SendMessageRequest,
    SendMessageResponse,
)
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import MCPAgentJob, Project, User

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
        created_at=job.created_at
    )


# Job CRUD Endpoints

@router.post("/", response_model=JobCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_job(
    job_request: JobCreateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required to create jobs"
        )

    # Create job
    job = MCPAgentJob(
        tenant_key=current_user.tenant_key,
        agent_type=job_request.agent_type,
        mission=job_request.mission,
        status="pending",
        spawned_by=job_request.spawned_by,
        context_chunks=job_request.context_chunks or [],
        messages=[],
        acknowledged=False
    )

    db.add(job)
    await db.commit()
    await db.refresh(job)

    logger.info(f"Created job {job.job_id} for tenant {current_user.tenant_key}")

    return JobCreateResponse(
        job_id=job.job_id,
        message="Job created successfully"
    )


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    status_filter: Optional[str] = Query(None, alias="status", description="Filter by status"),
    agent_type: Optional[str] = Query(None, description="Filter by agent type"),
    spawned_by: Optional[str] = Query(None, description="Filter by parent job_id"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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

    return JobListResponse(
        jobs=[job_to_response(job) for job in jobs],
        total=total
    )


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return job_to_response(job)


@router.patch("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: str,
    job_update: JobUpdateRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Permission check
    if not can_modify_job(job, current_user):
        logger.warning(f"User {current_user.username} not authorized to update job {job_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this job"
        )

    # Update status if provided
    update_data = job_update.dict(exclude_unset=True)
    if "status" in update_data:
        new_status = update_data["status"]

        # Validate status transition
        from src.giljo_mcp.agent_job_manager import AgentJobManager
        valid_transitions = AgentJobManager.VALID_TRANSITIONS.get(job.status, set())

        if new_status not in valid_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from '{job.status}' to '{new_status}'. "
                       f"Valid transitions: {valid_transitions or 'none (terminal state)'}"
            )

        job.status = new_status

    await db.commit()
    await db.refresh(job)

    logger.info(f"Updated job {job_id} by user {current_user.username}")

    return job_to_response(job)


@router.delete("/{job_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Permission check
    if not can_delete_job(job, current_user):
        logger.warning(f"User {current_user.username} not authorized to delete job {job_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete jobs"
        )

    await db.delete(job)
    await db.commit()

    logger.info(f"Deleted job {job_id} by user {current_user.username}")


# Job Status Management Endpoints

@router.post("/{job_id}/acknowledge", response_model=JobAcknowledgeResponse)
async def acknowledge_job(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # If already acknowledged, return as-is (idempotent)
    if job.acknowledged and job.status == "active":
        logger.info(f"Job {job_id} already acknowledged, returning current state")
        return JobAcknowledgeResponse(
            job_id=job.job_id,
            status=job.status,
            started_at=job.started_at,
            message="Job already acknowledged"
        )

    # Validate status transition
    if job.status != "pending":
        from src.giljo_mcp.agent_job_manager import AgentJobManager
        valid_transitions = AgentJobManager.VALID_TRANSITIONS.get(job.status, set())

        if "active" not in valid_transitions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid status transition from '{job.status}' to 'active'. "
                       f"Valid transitions: {valid_transitions or 'none (terminal state)'}"
            )

    # Update job
    from datetime import datetime, timezone
    job.acknowledged = True
    job.status = "active"
    job.started_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(job)

    logger.info(f"Acknowledged job {job_id} for tenant {current_user.tenant_key}")

    return JobAcknowledgeResponse(
        job_id=job.job_id,
        status=job.status,
        started_at=job.started_at,
        message="Job acknowledged successfully"
    )


@router.post("/{job_id}/complete", response_model=JobCompleteResponse)
async def complete_job(
    job_id: str,
    complete_request: JobCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Validate status transition
    from src.giljo_mcp.agent_job_manager import AgentJobManager
    valid_transitions = AgentJobManager.VALID_TRANSITIONS.get(job.status, set())

    if "completed" not in valid_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{job.status}' to 'completed'. "
                   f"Valid transitions: {valid_transitions or 'none (terminal state)'}"
        )

    # Update job
    from datetime import datetime, timezone
    job.status = "completed"
    job.completed_at = datetime.now(timezone.utc)

    # Add result as message
    if complete_request.result:
        result_msg = {
            "role": "system",
            "type": "completion",
            "content": complete_request.result,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        job.messages = job.messages + [result_msg]

    await db.commit()
    await db.refresh(job)

    logger.info(f"Completed job {job_id} for tenant {current_user.tenant_key}")

    return JobCompleteResponse(
        job_id=job.job_id,
        status=job.status,
        completed_at=job.completed_at,
        message="Job completed successfully"
    )


@router.post("/{job_id}/fail", response_model=JobFailResponse)
async def fail_job(
    job_id: str,
    fail_request: JobFailRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Validate status transition
    from src.giljo_mcp.agent_job_manager import AgentJobManager
    valid_transitions = AgentJobManager.VALID_TRANSITIONS.get(job.status, set())

    if "failed" not in valid_transitions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from '{job.status}' to 'failed'. "
                   f"Valid transitions: {valid_transitions or 'none (terminal state)'}"
        )

    # Update job
    from datetime import datetime, timezone
    job.status = "failed"
    job.completed_at = datetime.now(timezone.utc)

    # Add error as message
    if fail_request.error:
        error_msg = {
            "role": "system",
            "type": "error",
            "content": fail_request.error,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        job.messages = job.messages + [error_msg]

    await db.commit()
    await db.refresh(job)

    logger.info(f"Failed job {job_id} for tenant {current_user.tenant_key}")

    return JobFailResponse(
        job_id=job.job_id,
        status=job.status,
        completed_at=job.completed_at,
        message="Job failed"
    )


# Agent Communication Endpoints

@router.post("/{job_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    job_id: str,
    message_request: MessageSendRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Create message
    from datetime import datetime, timezone
    message = {
        "role": message_request.role,
        "type": message_request.type,
        "content": message_request.content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "acknowledged": False
    }

    # Add message to job
    job.messages = job.messages + [message]

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
        acknowledged=message["acknowledged"]
    )


@router.get("/{job_id}/messages")
async def get_messages(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Return messages with message_id (index)
    messages_with_ids = []
    for idx, msg in enumerate(job.messages or []):
        messages_with_ids.append({
            "message_id": str(idx),
            **msg
        })

    return {"messages": messages_with_ids}


@router.post("/{job_id}/messages/{message_id}/acknowledge", response_model=MessageResponse)
async def acknowledge_message(
    job_id: str,
    message_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Get message by index
    try:
        msg_idx = int(message_id)
        if msg_idx < 0 or msg_idx >= len(job.messages or []):
            raise IndexError
    except (ValueError, IndexError):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message not found"
        )

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
        acknowledged=True
    )


# Job Coordination Endpoints

@router.post("/{job_id}/spawn-children", response_model=JobSpawnResponse, status_code=status.HTTP_201_CREATED)
async def spawn_children(
    job_id: str,
    spawn_request: JobSpawnRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> JobSpawnResponse:
    """
    Spawn child jobs from a parent job.

    Args:
        job_id: Parent job ID
        spawn_request: Child job specifications
        current_user: Current authenticated user
        db: Database session

    Returns:
        Spawn response with created child job IDs

    Raises:
        HTTPException: 404 if parent job not found
    """
    logger.debug(f"User {current_user.username} spawning children for job {job_id}")

    # Query parent job with tenant isolation
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    parent_job = result.scalar_one_or_none()

    if not parent_job:
        logger.warning(f"Parent job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Create child jobs
    child_job_ids = []
    for child_spec in spawn_request.children:
        child_job = MCPAgentJob(
            tenant_key=current_user.tenant_key,
            agent_type=child_spec.agent_type,
            mission=child_spec.mission,
            status="pending",
            spawned_by=parent_job.job_id,
            context_chunks=child_spec.context_chunks or [],
            messages=[],
            acknowledged=False
        )

        db.add(child_job)
        await db.flush()  # Get job_id without committing
        child_job_ids.append(child_job.job_id)

    await db.commit()

    logger.info(f"Spawned {len(child_job_ids)} children for job {job_id}")

    return JobSpawnResponse(
        parent_job_id=parent_job.job_id,
        child_job_ids=child_job_ids,
        message=f"{len(child_job_ids)} child jobs spawned successfully"
    )


@router.get("/{job_id}/hierarchy", response_model=JobHierarchyResponse)
async def get_hierarchy(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> JobHierarchyResponse:
    """
    Get job hierarchy (parent + all children).

    Args:
        job_id: Parent job ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        Hierarchy response with parent and children

    Raises:
        HTTPException: 404 if parent job not found
    """
    logger.debug(f"User {current_user.username} getting hierarchy for job {job_id}")

    # Query parent job with tenant isolation
    parent_stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(parent_stmt)
    parent = result.scalar_one_or_none()

    if not parent:
        logger.warning(f"Parent job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Query children
    children_stmt = select(MCPAgentJob).where(
        MCPAgentJob.spawned_by == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    ).order_by(MCPAgentJob.created_at)

    result = await db.execute(children_stmt)
    children = result.scalars().all()

    logger.info(f"Retrieved hierarchy for job {job_id}: {len(children)} children")

    return JobHierarchyResponse(
        parent=job_to_response(parent),
        children=[job_to_response(child) for child in children],
        total_children=len(children)
    )


# Kanban Board Endpoints (Handover 0066)

@router.get("/kanban/{project_id}", response_model=KanbanBoardResponse)
async def get_kanban_board(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
) -> KanbanBoardResponse:
    """
    Get Kanban board data for Agent Kanban Dashboard.

    Returns jobs grouped by status (4 columns: pending, active, completed, blocked)
    with message counts for each job.

    Args:
        project_id: Project ID to get Kanban board for
        current_user: Current authenticated user
        db: Database session

    Returns:
        Kanban board data with 4 columns and message counts

    Raises:
        HTTPException: 404 if project not found (includes multi-tenant isolation)
    """
    logger.debug(f"User {current_user.username} getting Kanban board for project {project_id}")

    # Verify project exists and user has access (multi-tenant isolation)
    project_stmt = select(Project).where(
        Project.id == project_id,
        Project.tenant_key == current_user.tenant_key
    )
    result = await db.execute(project_stmt)
    project = result.scalar_one_or_none()

    if not project:
        logger.warning(f"Project {project_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Query all jobs for this project
    jobs_stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    ).order_by(MCPAgentJob.created_at.desc())

    result = await db.execute(jobs_stmt)
    jobs = result.scalars().all()

    # Helper function to calculate message counts
    def calculate_message_counts(job: MCPAgentJob) -> MessageCounts:
        """Calculate message counts for a job."""
        messages = job.messages or []

        unread_count = sum(1 for msg in messages if msg.get("status") == "pending")
        acknowledged_count = sum(1 for msg in messages if msg.get("status") == "acknowledged")
        sent_count = sum(1 for msg in messages if msg.get("from") in ["developer", "user"])

        return MessageCounts(
            unread_messages=unread_count,
            acknowledged_messages=acknowledged_count,
            sent_messages=sent_count
        )

    # Helper function to convert job to Kanban card
    def job_to_kanban_card(job: MCPAgentJob) -> KanbanJobCard:
        """Convert MCPAgentJob to KanbanJobCard."""
        return KanbanJobCard(
            job_id=job.job_id,
            agent_type=job.agent_type,
            mission=job.mission,
            status=job.status,
            acknowledged=job.acknowledged,
            started_at=job.started_at,
            completed_at=job.completed_at,
            created_at=job.created_at,
            message_counts=calculate_message_counts(job)
        )

    # Group jobs by status (4 columns)
    columns_data = {
        "pending": [],
        "active": [],
        "completed": [],
        "blocked": []
    }

    for job in jobs:
        if job.status in columns_data:
            columns_data[job.status].append(job_to_kanban_card(job))

    # Create column objects
    columns = [
        KanbanColumn(status="pending", jobs=columns_data["pending"]),
        KanbanColumn(status="active", jobs=columns_data["active"]),
        KanbanColumn(status="completed", jobs=columns_data["completed"]),
        KanbanColumn(status="blocked", jobs=columns_data["blocked"])
    ]

    logger.info(
        f"Retrieved Kanban board for project {project_id}: "
        f"pending={len(columns_data['pending'])}, active={len(columns_data['active'])}, "
        f"completed={len(columns_data['completed'])}, blocked={len(columns_data['blocked'])}"
    )

    return KanbanBoardResponse(
        project_id=project_id,
        columns=columns
    )


@router.get("/{job_id}/message-thread", response_model=MessageThreadResponse)
async def get_message_thread(
    job_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Convert messages to MessageThreadItem format
    messages = []
    for idx, msg in enumerate(job.messages or []):
        messages.append(
            MessageThreadItem(
                message_id=str(idx),
                from_=msg.get("from", "unknown"),
                content=msg.get("content", ""),
                timestamp=msg.get("timestamp", ""),
                status=msg.get("status", "pending")
            )
        )

    logger.info(f"Retrieved {len(messages)} messages for job {job_id}")

    return MessageThreadResponse(
        job_id=job.job_id,
        messages=messages
    )


@router.post("/{job_id}/send-message", response_model=SendMessageResponse, status_code=status.HTTP_201_CREATED)
async def send_developer_message(
    job_id: str,
    message_request: SendMessageRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
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
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Message content cannot be empty"
        )

    # Query job with tenant isolation
    stmt = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == current_user.tenant_key
    )
    result = await db.execute(stmt)
    job = result.scalar_one_or_none()

    if not job:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Create message
    from datetime import datetime, timezone
    message = {
        "from": "developer",
        "content": message_request.content,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "pending"
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
        status=message["status"]
    )
