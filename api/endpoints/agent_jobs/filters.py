"""
Quick filters endpoint for status board UI - Handover 0226

Provides available filter options based on current project jobs.

Features:
- Distinct value aggregation for all filterable fields
- Multi-tenant isolation
- Sorted results for consistent UI display
- Unread messages detection
"""

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from src.giljo_mcp.auth.dependencies import get_current_user
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class FilterOptions(BaseModel):
    """Available filter options for status board"""

    statuses: list[str]
    agent_display_names: list[str]
    health_statuses: list[str]
    tool_types: list[str]
    has_unread_jobs: bool


# ============================================================================
# ENDPOINT
# ============================================================================

@router.get("/filter-options", response_model=FilterOptions)
async def get_filter_options(
    project_id: str = Query(..., description="Project ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get available filter options for current project.

    Returns lists of unique values for:
    - Status (waiting, working, blocked, complete, etc.)
    - Agent display names (orchestrator, analyzer, implementer, etc.)
    - Health statuses (healthy, warning, critical, timeout)
    - Tool types (claude-code, codex, gemini, universal)
    - Has unread jobs (boolean)

    All lists are sorted alphabetically for consistent UI display.
    Multi-tenant isolation ensures users only see options from their own jobs.
    """

    # Base query with tenant isolation (query AgentExecution joined to AgentJob)
    base_conditions = and_(
        AgentExecution.tenant_key == current_user.tenant_key,
    )

    # Get distinct statuses
    status_query = (
        select(AgentExecution.status)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(base_conditions)
        .where(AgentJob.project_id == project_id)
        .where(AgentExecution.status.is_not(None))
        .distinct()
    )
    status_result = await db.execute(status_query)
    statuses = sorted([s for s in status_result.scalars().all() if s])

    # Get distinct agent display names
    agent_display_name_query = (
        select(AgentExecution.agent_type)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(base_conditions)
        .where(AgentJob.project_id == project_id)
        .where(AgentExecution.agent_type.is_not(None))
        .distinct()
    )
    agent_display_name_result = await db.execute(agent_display_name_query)
    agent_display_names = sorted([a for a in agent_display_name_result.scalars().all() if a])

    # Get distinct health statuses
    health_query = (
        select(AgentExecution.health_status)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(base_conditions)
        .where(AgentJob.project_id == project_id)
        .where(AgentExecution.health_status.is_not(None))
        .distinct()
    )
    health_result = await db.execute(health_query)
    health_statuses = sorted([h for h in health_result.scalars().all() if h])

    # Get distinct tool types
    tool_query = (
        select(AgentExecution.tool_type)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(base_conditions)
        .where(AgentJob.project_id == project_id)
        .where(AgentExecution.tool_type.is_not(None))
        .distinct()
    )
    tool_result = await db.execute(tool_query)
    tool_types = sorted([t for t in tool_result.scalars().all() if t])

    # Check if any jobs have unread messages
    unread_query = (
        select(AgentExecution.agent_id)
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(base_conditions)
        .where(AgentJob.project_id == project_id)
        .where(
            func.jsonb_path_exists(
                AgentExecution.messages,
                '$[*] ? (@.status == "pending")'
            )
        )
        .limit(1)
    )
    unread_result = await db.execute(unread_query)
    has_unread_jobs = unread_result.scalar() is not None

    return FilterOptions(
        statuses=statuses,
        agent_display_names=agent_display_names,
        health_statuses=health_statuses,
        tool_types=tool_types,
        has_unread_jobs=has_unread_jobs,
    )
