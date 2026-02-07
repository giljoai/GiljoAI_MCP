"""
Table view endpoint for status board UI - Handover 0226

Provides optimized column data for table display with minimal payload size.

Features:
- Minimal payload (only table columns, ~50% smaller than full JobResponse)
- Advanced filtering (status, health, unread messages, agent type)
- Flexible sorting (last_progress, created_at, status, agent_display_name)
- Pagination support
- Multi-tenant isolation
- Message count aggregation
- Performance optimized with database indexes (Handover 0225)
"""

from datetime import datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.dependencies import get_db
from src.giljo_mcp.auth.dependencies import get_current_user
from src.giljo_mcp.models import User
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


router = APIRouter()


# ============================================================================
# RESPONSE MODELS
# ============================================================================


class TodoItemData(BaseModel):
    """Individual TODO item for Plan tab display - Handover 0423"""

    content: str
    status: str  # pending, in_progress, completed


class TableRowData(BaseModel):
    """Optimized data for single table row"""

    job_id: str
    agent_id: Optional[str] = None  # Handover 0401b: Executor UUID for WebSocket event matching
    agent_display_name: str
    agent_name: Optional[str] = None
    tool_type: str  # claude-code, codex, gemini, universal
    status: str  # waiting, working, blocked, complete, failed, cancelled, decommissioned
    progress: int  # 0-100
    current_task: Optional[str] = None
    mission: Optional[str] = None  # Job mission assigned by orchestrator

    # Message tracking (legacy field names for backward compatibility)
    unread_count: int
    acknowledged_count: int
    total_messages: int

    # Message counters (Handover 0407: Direct counter fields for frontend store)
    messages_sent_count: int = 0
    messages_waiting_count: int = 0
    messages_read_count: int = 0

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
    mission_acknowledged_at: Optional[datetime] = None

    # Agent role tracking
    is_orchestrator: bool

    # TODO-style steps summary for dashboard Steps column (Handover 0297)
    steps_total: Optional[int] = None
    steps_completed: Optional[int] = None

    # TODO items for Plan tab display - Handover 0423
    todo_items: list[TodoItemData] = []


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
    agent_display_name: Optional[list[str]] = Query(None, description="Filter by agent type"),
    sort_by: Literal["last_progress", "created_at", "status", "agent_display_name"] = Query(
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
    - Flexible sorting (last_progress, created_at, status, agent_display_name)
    - Pagination support
    - Multi-tenant isolation
    - Message count aggregation

    Performance:
    - Uses composite indexes from Handover 0225 for fast queries
    - Target response time: <100ms for 50 jobs
    - Payload size: ~300-500 bytes per row (vs ~1-2KB for full JobResponse)
    """

    # Build base query with tenant isolation (query AgentExecution joined to AgentJob)
    # Handover 0423: Load todo_items relationship for Plan tab display
    query = (
        select(AgentExecution)
        .options(joinedload(AgentExecution.job).selectinload(AgentJob.todo_items))
        .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
        .where(
            and_(
                AgentExecution.tenant_key == current_user.tenant_key,
                AgentJob.project_id == project_id,
            )
        )
    )

    # Apply filters
    filters_applied = {}

    if status:
        query = query.where(AgentExecution.status.in_(status))
        filters_applied["status"] = status

    if health_status:
        query = query.where(AgentExecution.health_status.in_(health_status))
        filters_applied["health_status"] = health_status

    if agent_display_name:
        query = query.where(AgentExecution.agent_display_name.in_(agent_display_name))
        filters_applied["agent_display_name"] = agent_display_name

    if has_unread is not None:
        if has_unread:
            # Filter jobs with unread messages (using counter field)
            query = query.where(AgentExecution.messages_waiting_count > 0)
        filters_applied["has_unread"] = has_unread

    # Get total count before pagination
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Apply sorting
    if sort_by == "last_progress":
        sort_column = AgentExecution.last_progress_at
    elif sort_by == "created_at":
        sort_column = AgentExecution.started_at
    elif sort_by == "status":
        sort_column = AgentExecution.status
    elif sort_by == "agent_display_name":
        sort_column = AgentExecution.agent_display_name

    if sort_order == "desc":
        query = query.order_by(sort_column.desc().nulls_last())
    else:
        query = query.order_by(sort_column.asc().nulls_last())

    # Apply pagination
    query = query.limit(limit).offset(offset)

    # Execute query
    result = await db.execute(query)
    executions = result.scalars().all()

    # Build table rows with message count aggregation
    rows = []
    now = datetime.now(timezone.utc)

    for execution in executions:
        # Use counter fields instead of iterating messages
        unread_count = execution.messages_waiting_count
        acknowledged_count = execution.messages_read_count
        total_messages = (
            execution.messages_sent_count + execution.messages_waiting_count + execution.messages_read_count
        )

        # Calculate staleness
        minutes_since_progress = None
        is_stale = False

        if execution.last_progress_at:
            delta = now - execution.last_progress_at
            minutes_since_progress = int(delta.total_seconds() / 60)

            # Job is stale if >10 minutes since progress and not in terminal state
            terminal_states = {"complete", "failed", "cancelled", "decommissioned"}
            if minutes_since_progress > 10 and execution.status not in terminal_states:
                is_stale = True

        # Derive steps summary from execution metadata (note: in new model, metadata is on job)
        steps_total = None
        steps_completed = None
        try:
            metadata = execution.job.job_metadata or {} if execution.job else {}
            todo_steps = metadata.get("todo_steps") or {}
            total_steps = todo_steps.get("total_steps")
            completed_steps = todo_steps.get("completed_steps")
            if (
                isinstance(total_steps, int)
                and total_steps > 0
                and isinstance(completed_steps, int)
                and 0 <= completed_steps <= total_steps
            ):
                steps_total = total_steps
                steps_completed = completed_steps
        except Exception:
            # Keep table view robust even if metadata is malformed
            steps_total = None
            steps_completed = None

        rows.append(
            TableRowData(
                job_id=execution.job_id,
                agent_id=execution.agent_id,  # Handover 0401b: WebSocket event matching
                agent_display_name=execution.agent_display_name,
                agent_name=execution.agent_name,
                tool_type=execution.tool_type,
                status=execution.status,
                progress=execution.progress,
                current_task=execution.current_task,
                mission=execution.job.mission if execution.job else None,  # Job mission from AgentJob
                unread_count=unread_count,
                acknowledged_count=acknowledged_count,
                total_messages=total_messages,
                # Handover 0407: Direct counter fields for frontend store
                messages_sent_count=execution.messages_sent_count,
                messages_waiting_count=execution.messages_waiting_count,
                messages_read_count=execution.messages_read_count,
                health_status=execution.health_status,
                last_progress_at=execution.last_progress_at,
                minutes_since_progress=minutes_since_progress,
                is_stale=is_stale,
                created_at=execution.started_at or execution.job.created_at if execution.job else execution.started_at,
                started_at=execution.started_at,
                completed_at=execution.completed_at,
                mission_acknowledged_at=execution.mission_acknowledged_at,  # Handover 0233
                is_orchestrator=(execution.agent_display_name == "orchestrator"),
                steps_total=steps_total,
                steps_completed=steps_completed,
                # Handover 0423: Include todo_items for Plan tab display
                todo_items=[
                    TodoItemData(content=item.content, status=item.status)
                    for item in sorted(execution.job.todo_items if execution.job else [], key=lambda x: x.sequence)
                ],
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
