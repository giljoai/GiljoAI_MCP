"""
Agent Job Messages Endpoint - Handover 0387g

Provides message content for MessageAuditModal.
Fetches messages where the agent is sender or recipient.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi import status as http_status
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import Message, User
from src.giljo_mcp.models.agent_identity import AgentExecution


logger = logging.getLogger(__name__)
router = APIRouter()


def _resolve_sender_display_name(from_agent: str, agent_lookup: dict[str, str]) -> str:
    """
    Resolve from_agent to a human-readable display name.

    Args:
        from_agent: Raw from_agent value (could be 'user', 'orchestrator', agent_id UUID, or display name)
        agent_lookup: Dict mapping agent_id -> display name (e.g., "Orchestrator #1", "Implementer #2")

    Returns:
        Resolved display name
    """
    if not from_agent:
        return "Unknown"

    # Special cases
    if from_agent == "user":
        return "User"
    if from_agent == "system":
        return "System"

    # Check if it's an agent_id UUID - resolve to display name
    if from_agent in agent_lookup:
        return agent_lookup[from_agent]

    # Check if it looks like a display name already (e.g., "orchestrator", "implementer")
    # Capitalize first letter for display
    if from_agent.lower() in ["orchestrator", "implementer", "analyzer", "tester", "reviewer", "documenter"]:
        return from_agent.capitalize()

    # Return as-is (might be an agent_name like "impl-alpha")
    return from_agent


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

    # Get execution to verify tenant access and get agent_id
    exec_stmt = select(AgentExecution).where(
        AgentExecution.job_id == job_id,
        AgentExecution.tenant_key == current_user.tenant_key,
    )
    execution = (await session.execute(exec_stmt)).scalar_one_or_none()

    if not execution:
        logger.warning(f"Job {job_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=http_status.HTTP_404_NOT_FOUND, detail="Job not found")

    # Build agent_id -> display name lookup for sender resolution
    # Fetch all agents in this tenant for name resolution
    agents_stmt = select(AgentExecution).where(AgentExecution.tenant_key == current_user.tenant_key)
    agents_result = await session.execute(agents_stmt)
    agents = agents_result.scalars().all()

    # Build lookup: agent_id -> "DisplayName" (e.g., "Orchestrator")
    agent_lookup = {}
    for agent in agents:
        display_name = agent.agent_display_name.capitalize() if agent.agent_display_name else "Agent"
        agent_lookup[agent.agent_id] = display_name
        # Also add agent_name for resolution (e.g., "impl-alpha" -> "Implementer")
        if agent.agent_name:
            agent_lookup[agent.agent_name] = display_name

    # Query messages where agent is sender or recipient
    # Note: from_agent is stored in meta_data["_from_agent"], not as a column
    # Note: to_agents is JSONB array, use PostgreSQL array containment
    msg_stmt = (
        select(Message)
        .where(
            Message.tenant_key == current_user.tenant_key,
            or_(
                Message.meta_data.op("->>")("_from_agent") == execution.agent_id,
                Message.to_agents.contains([execution.agent_id]),  # PostgreSQL array containment
            ),
        )
        .order_by(Message.created_at.desc())
        .limit(limit)
    )
    messages = (await session.execute(msg_stmt)).scalars().all()

    logger.info(
        f"Retrieved {len(messages)} messages for job {job_id} "
        f"(agent_id={execution.agent_id}, tenant={current_user.tenant_key})"
    )

    # Build response with resolved sender names
    message_list = []
    for m in messages:
        raw_from_agent = m.meta_data.get("_from_agent", "unknown") if m.meta_data else "unknown"
        resolved_from = _resolve_sender_display_name(raw_from_agent, agent_lookup)
        is_outbound = raw_from_agent == execution.agent_id

        message_list.append(
            {
                "id": str(m.id),
                "from": resolved_from,  # Human-readable display name
                "from_agent": raw_from_agent,  # Raw value for backward compat
                "from_agent_id": raw_from_agent if raw_from_agent in agent_lookup else None,  # UUID if it's an agent
                "to_agents": m.to_agents,
                "content": m.content[:500] if m.content else "",  # Truncate for preview
                "status": m.status,
                "created_at": m.created_at.isoformat(),
                "direction": "outbound" if is_outbound else "inbound",
                "message_type": m.message_type,
            }
        )

    return {
        "job_id": job_id,
        "agent_id": execution.agent_id,
        "messages": message_list,
    }
