"""
Table view endpoint for status board UI - Handover 0226

Provides optimized column data for table display with minimal payload size.

Features:
- Minimal payload (only table columns, ~50% smaller than full JobResponse)
- Advanced filtering (status, health, unread messages, agent type)
- Flexible sorting (last_progress, created_at, status, agent_type)
- Pagination support
- Multi-tenant isolation
- Message count aggregation
- Performance optimized with database indexes (Handover 0225)
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from src.giljo_mcp.auth.dependencies import get_current_user
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agents import MCPAgentJob

router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================

class TableRowData(BaseModel):
    """Optimized data for single table row"""

    job_id: str
    agent_type: str
    agent_name: Optional[str] = None
    tool_type: str  # claude-code, codex, gemini, universal
    status: str  # waiting, working, blocked, complete, failed, cancelled, decommissioned
    progress: int  # 0-100
    current_task: Optional[str] = None

    # Message tracking
    unread_count: int
    acknowledged_count: int
    total_messages: int

    # Health monitoring
    health_status: str  # unknown, healthy, warning, critical, timeout
    last_progress_at: Optional[datetime] = None
    minutes_since_progress: Optional[int] = None
    is_stale: bool

    # Timestamps
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Mission tracking (Handover 0233)
    mission_read_at: Optional[datetime] = None
    mission_acknowledged_at: Optional[datetime] = None

    # Instance tracking (orchestrator succession)
    instance_number: int
    is_orchestrator: bool


class TableViewResponse(BaseModel):
    """Response for table view endpoint"""

    rows: list[TableRowData]
    total: int
    limit: int
    offset: int
    project_id: str
    filters_applied: dict


# ============================================================================
# ENDPOINT
# ============================================================================

@router.get("/table-view", response_model=TableViewResponse)
async def get_agent_jobs_table_view(
    project_id: str = Query(..., description="Project ID to fetch jobs for"),
    status: Optional[list[str]] = Query(None, description="Filter by status (can specify multiple)"),
    health_status: Optional[list[str]] = Query(None, description="Filter by health status"),
    has_unread: Optional[bool] = Query(None, description="Filter jobs with unread messages"),
    agent_type: Optional[list[str]] = Query(None, description="Filter by agent type"),
    sort_by: Literal["last_progress", "created_at", "status", "agent_type"] = Query(
        "last_progress", description="Sort column"
    ),
    sort_order: Literal["asc", "desc"] = Query("desc", description="Sort direction"),
    limit: int = Query(50, ge=1, le=500, description="Number of rows to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get optimized table view data for status board.

    Features:
    - Minimal payload size (only table columns)
    - Advanced filtering (status, health, unread messages, agent type)
    - Flexible sorting (last_progress, created_at, status, agent_type)
    - Pagination support
    - Multi-tenant isolation
    - Message count aggregation

    Performance:
    - Uses composite indexes from Handover 0225 for fast queries
    - Target response time: <100ms for 50 jobs
    - Payload size: ~300-500 bytes per row (vs ~1-2KB for full JobResponse)
    """

    # Build base query with tenant isolation
    query = select(MCPAgentJob).where(
        and_(
            MCPAgentJob.tenant_key == current_user.tenant_key,
            MCPAgentJob.project_id == project_id,
        )
    )

    # Apply filters
    filters_applied = {}

    if status:
        query = query.where(MCPAgentJob.status.in_(status))
        filters_applied["status"] = status

    if health_status:
        query = query.where(MCPAgentJob.health_status.in_(health_status))
        filters_applied["health_status"] = health_status

    if agent_type:
        query = query.where(MCPAgentJob.agent_type.in_(agent_type))
        filters_applied["agent_type"] = agent_type

    if has_unread is not None:
        if has_unread:
            # Filter jobs with messages containing status="pending"
            query = query.where(
                func.jsonb_path_exists(
                    MCPAgentJob.messages,
                    '$[*] ? (@.status == "pending")'
                )
            )
        filters_applied["has_unread"] = has_unread

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting
    if sort_by == "last_progress":
        sort_column = MCPAgentJob.last_progress_at
    elif sort_by == "created_at":
        sort_column = MCPAgentJob.created_at
    elif sort_by == "status":
        sort_column = MCPAgentJob.status
    elif sort_by == "agent_type":
        sort_column = MCPAgentJob.agent_type

    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nulls_last())
    else:
        query = query.order_by(sort_column.asc().nulls_last())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    jobs = result.scalars().all()

    # Build table rows with message count aggregation
    rows = []
    now = datetime.now(timezone.utc)

    for job in jobs:
        # Count messages by status
        unread_count = 0
        acknowledged_count = 0
        total_messages = len(job.messages) if job.messages else 0

        if job.messages:
            for msg in job.messages:
                if msg.get("status") == "pending":
                    unread_count += 1
                elif msg.get("status") == "acknowledged":
                    acknowledged_count += 1

        # Calculate staleness
        minutes_since_progress = None
        is_stale = False

        if job.last_progress_at:
            delta = now - job.last_progress_at
            minutes_since_progress = int(delta.total_seconds() / 60)

            # Job is stale if >10 minutes since progress and not in terminal state
            terminal_states = {"complete", "failed", "cancelled", "decommissioned"}
            if minutes_since_progress > 10 and job.status not in terminal_states:
                is_stale = True

        # Determine instance number (orchestrator succession)
        instance_number = job.instance_number if hasattr(job, "instance_number") else 1

        rows.append(
            TableRowData(
                job_id=job.job_id,
                agent_type=job.agent_type,
                agent_name=job.agent_name,
                tool_type=job.tool_type,
                status=job.status,
                progress=job.progress,
                current_task=job.current_task,
                unread_count=unread_count,
                acknowledged_count=acknowledged_count,
                total_messages=total_messages,
                health_status=job.health_status,
                last_progress_at=job.last_progress_at,
                minutes_since_progress=minutes_since_progress,
                is_stale=is_stale,
                created_at=job.created_at,
                started_at=job.started_at,
                completed_at=job.completed_at,
                mission_read_at=job.mission_read_at,  # Handover 0233
                mission_acknowledged_at=job.mission_acknowledged_at,  # Handover 0233
                instance_number=instance_number,
                is_orchestrator=(job.agent_type == "orchestrator"),
            )
        )

    return TableViewResponse(
        rows=rows,
        total=total,
        limit=limit,
        offset=offset,
        project_id=project_id,
        filters_applied=filters_applied,
    )
