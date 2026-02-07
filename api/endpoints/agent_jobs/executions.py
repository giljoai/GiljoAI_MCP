"""
Execution endpoints for agent jobs.

Handover 0366d-1: Frontend Core Agent Display
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

from .models import AgentExecutionResponse


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

    # Fetch all executions for this job
    result = await db.execute(
        select(AgentExecution).where(AgentExecution.job_id == job_id).order_by(AgentExecution.started_at.asc())
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
