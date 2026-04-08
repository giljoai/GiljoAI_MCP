# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Execution endpoints for agent jobs.

Handover 0366d-1: Frontend Core Agent Display
Handover 0491: Clear-silent endpoint
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

from .models import AgentExecutionResponse, ClearSilentResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{job_id}/executions", response_model=list[AgentExecutionResponse])
async def get_job_executions(
    job_id: str, db: AsyncSession = Depends(get_db_session), current_user: User = Depends(get_current_active_user)
) -> list[AgentExecutionResponse]:
    """
    Get all agent execution instances for a specific job.

    Returns list of AgentExecution records sorted by created_at ascending.
    Used by frontend to display execution history.

    Handover 0366d-1: Frontend Core Agent Display
    """
    # Verify job exists and user has access (tenant isolation)
    result = await db.execute(
        select(AgentJob).where(AgentJob.job_id == job_id, AgentJob.tenant_key == current_user.tenant_key)
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Fetch all executions for this job (defense-in-depth: tenant_key filter)
    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.job_id == job_id, AgentExecution.tenant_key == current_user.tenant_key)
        .order_by(AgentExecution.started_at.asc())
    )
    executions = result.scalars().all()

    return [
        AgentExecutionResponse(
            agent_id=str(execution.agent_id),
            job_id=str(execution.job_id),
            status=execution.status,
            progress=execution.progress,
            spawned_by=str(execution.spawned_by) if execution.spawned_by else None,
            created_at=execution.created_at,
            updated_at=execution.updated_at,
        )
        for execution in executions
    ]


@router.post("/{agent_id}/clear-silent", response_model=ClearSilentResponse)
async def clear_silent(
    agent_id: str,
    request: Request,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user),
) -> ClearSilentResponse:
    """
    Clear silent status for an agent execution (Handover 0491).

    When an agent is marked as 'silent' (no MCP activity past threshold),
    this endpoint allows users to manually clear the status back to 'working'
    by clicking the Silent badge in the dashboard.

    Args:
        agent_id: Agent execution ID
        request: FastAPI request (for accessing app state)
        db: Database session
        current_user: Authenticated user

    Returns:
        ClearSilentResponse with updated agent info

    Raises:
        HTTPException 404: Agent not found or not in silent status
    """
    from src.giljo_mcp.services.silence_detector import clear_silent_status

    # Get WebSocket manager from app state
    ws_manager = getattr(request.app.state, "websocket_manager", None)

    result = await clear_silent_status(
        session=db,
        agent_id=agent_id,
        tenant_key=current_user.tenant_key,
        ws_manager=ws_manager,
    )

    if result is None:
        raise HTTPException(
            status_code=404,
            detail="Agent not found or not currently in silent status",
        )

    logger.info(
        "User %s cleared silent status for agent %s",
        current_user.username,
        agent_id,
    )

    return ClearSilentResponse(**result)
