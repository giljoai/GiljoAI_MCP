"""
Agent Job Messages Endpoint - Handover 0387g

Provides message content for MessageAuditModal.
Fetches messages where the agent is sender or recipient.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import JSONB

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Message, User
from src.giljo_mcp.models.agent_identity import AgentExecution


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{job_id}/messages")
async def get_job_messages(
    job_id: str,
    limit: int = Query(50, ge=1, le=200, description="Maximum messages to retrieve (default 50, max 200)"),
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get messages for an agent job (for MessageAuditModal).

    Returns messages where the agent is sender or recipient.
    All messages are filtered by tenant_key for multi-tenant isolation.

    Args:
        job_id: Agent job ID to retrieve messages for
        limit: Maximum messages to retrieve (default 50, max 200)
        current_user: Authenticated user (from dependency)
        session: Database session (from dependency)

    Returns:
        Dictionary with job_id, agent_id, and messages list

    Raises:
        HTTPException 404: Job not found or access denied
        HTTPException 500: Failed to retrieve messages

    Example:
        GET /api/agent-jobs/{job_id}/messages?limit=100
    """
    logger.debug(f"User {current_user.username} retrieving messages for job {job_id} (limit={limit})")

    try:
        # Get execution to verify tenant access and get agent_id
        exec_stmt = select(AgentExecution).where(
            AgentExecution.job_id == job_id,
            AgentExecution.tenant_key == current_user.tenant_key,
        )
        execution = (await session.execute(exec_stmt)).scalar_one_or_none()

        if not execution:
            logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
            raise HTTPException(
                status_code=http_status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )

        # Query messages where agent is sender or recipient
        # Note: to_agents is TEXT[] in database, use PostgreSQL array containment
        msg_stmt = (
            select(Message)
            .where(
                Message.tenant_key == current_user.tenant_key,
                or_(
                    Message.from_agent == execution.agent_id,
                    Message.to_agents.contains([execution.agent_id])  # PostgreSQL array containment
                )
            )
            .order_by(Message.created_at.desc())
            .limit(limit)
        )
        messages = (await session.execute(msg_stmt)).scalars().all()

        logger.info(
            f"Retrieved {len(messages)} messages for job {job_id} "
            f"(agent_id={execution.agent_id}, tenant={current_user.tenant_key})"
        )

        return {
            "job_id": job_id,
            "agent_id": execution.agent_id,
            "messages": [
                {
                    "id": str(m.id),
                    "from_agent": m.from_agent,
                    "to_agents": m.to_agents,
                    "content": m.content[:500] if m.content else "",  # Truncate for preview
                    "status": m.status,
                    "created_at": m.created_at.isoformat(),
                    "direction": "outbound" if m.from_agent == execution.agent_id else "inbound",
                }
                for m in messages
            ],
        }

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        logger.error(f"Failed to retrieve messages for job {job_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve messages: {str(e)}"
        )
