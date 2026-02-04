"""
Execution endpoints for agent jobs.

Handover 0366d-1: Frontend Core Agent Display
"""
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution

from .models import AgentExecutionResponse

router = APIRouter()


@router.get("/{job_id}/executions", response_model=List[AgentExecutionResponse])
async def get_job_executions(
    job_id: str,
    db: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_active_user)
) -> List[AgentExecutionResponse]:
    """
    Get all agent execution instances for a specific job.

    Returns list of AgentExecution records sorted by instance_number ascending.
    Used by frontend to display execution history and succession timeline.

    Handover 0366d-1: Frontend Core Agent Display
    """
    # Verify job exists and user has access (tenant isolation)
    result = await db.execute(
        select(AgentJob).where(
            AgentJob.job_id == job_id,
            AgentJob.tenant_key == current_user.tenant_key
        )
    )
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    # Fetch all executions for this job
    result = await db.execute(
        select(AgentExecution)
        .where(AgentExecution.job_id == job_id)
        .order_by(AgentExecution.instance_number.asc())
    )
    executions = result.scalars().all()

    return [
        AgentExecutionResponse(
            agent_id=str(exec.agent_id),
            job_id=str(exec.job_id),
            instance_number=exec.instance_number,
            status=exec.status,
            progress=exec.progress,
            spawned_by=str(exec.spawned_by) if exec.spawned_by else None,
            created_at=exec.created_at,
            updated_at=exec.updated_at
        )
        for exec in executions
    ]
