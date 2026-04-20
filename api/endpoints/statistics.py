# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Statistics and monitoring API endpoints

Handover 1011 Phase 1: Migrated to use StatisticsRepository pattern for all queries.
Original direct SQLAlchemy queries preserved as comments for rollback reference.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.models import User
from giljo_mcp.services.statistics_service import StatisticsService


logger = logging.getLogger(__name__)


router = APIRouter()


# Pydantic models for response
class SystemStatsResponse(BaseModel):
    total_projects: int
    active_projects: int
    completed_projects: int
    total_agents: int
    active_agents: int
    total_messages: int
    pending_messages: int
    total_tasks: int
    completed_tasks: int
    database_size_mb: float
    uptime_seconds: float
    total_agents_spawned: int
    total_jobs_completed: int
    projects_finished: int
    projects_staged: int
    projects_cancelled: int


class ProjectStatsResponse(BaseModel):
    project_id: str
    name: str
    status: str
    duration_seconds: float
    agent_count: int
    message_count: int
    task_count: int
    completed_tasks: int
    last_activity: datetime


class AgentStatsResponse(BaseModel):
    agent_id: str
    name: str
    role: str
    status: str
    project_id: str
    created_at: datetime
    messages_sent: int
    messages_received: int
    tasks_assigned: int
    tasks_completed: int
    average_response_time_seconds: Optional[float] = None
    last_activity: datetime


class MessageStatsResponse(BaseModel):
    total_messages: int
    pending_messages: int
    acknowledged_messages: int
    completed_messages: int
    failed_messages: int
    average_processing_time_seconds: Optional[float] = None
    messages_per_hour: float
    peak_hour_messages: Optional[int] = None


class PerformanceMetricsResponse(BaseModel):
    api_response_time_ms: float
    database_query_time_ms: float
    websocket_connections: int
    active_sessions: Optional[int] = None
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_usage_percent: float
    error_rate_percent: Optional[float] = None


class CallCountsResponse(BaseModel):
    total_api_calls: int
    total_mcp_calls: int


class DetailedHealthResponse(BaseModel):
    overall: str
    components: dict[str, Any]
    checks_passed: int
    checks_failed: int


# Store startup time
startup_time = datetime.now(timezone.utc)


class AgentRoleDistItem(BaseModel):
    """Single entry in the agent role distribution chart."""

    label: str
    count: int
    color: str
    is_active: bool


class DashboardStatsResponse(BaseModel):
    """Response model for the consolidated dashboard analytics endpoint (Handover 0839)."""

    project_status_dist: dict[str, int]
    taxonomy_dist: list[dict]
    agent_role_dist: list[AgentRoleDistItem]
    recent_projects: list[dict]
    recent_memories: list[dict]
    task_status_dist: dict[str, int]
    execution_mode_dist: dict[str, int]
    products: list[dict]


@router.get("/dashboard", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    request: Request,
    product_id: Optional[str] = Query(None, description="Filter by product (None = all products)"),
    current_user: User = Depends(get_current_active_user),
):
    """
    Consolidated dashboard analytics endpoint (Handover 0839).

    Returns project status distribution, taxonomy distribution, agent role
    distribution, recent projects, recent 360 memories, task status distribution,
    and per-product project counts -- all in a single request.

    All data is filtered by tenant_key for isolation. Optional product_id
    narrows results to a specific product.
    """
    from api.app_state import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_service = StatisticsService(state.db_manager)
    data = await stats_service.get_dashboard_stats(tenant_key, product_id=product_id)

    return DashboardStatsResponse(**data)


@router.get("/call-counts", response_model=CallCountsResponse)
async def get_call_counts(request: Request, current_user: User = Depends(get_current_active_user)):
    """Get total API and MCP call counts."""
    from api.app_state import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    db_api_calls = 0
    db_mcp_calls = 0

    if state.db_manager:
        stats_service = StatisticsService(state.db_manager)
        metrics = await stats_service.get_api_metrics(tenant_key)
        if metrics:
            db_api_calls = metrics.total_api_calls
            db_mcp_calls = metrics.total_mcp_calls

    in_memory_api_calls = state.api_call_count.get(tenant_key, 0)
    in_memory_mcp_calls = state.mcp_call_count.get(tenant_key, 0)

    return CallCountsResponse(
        total_api_calls=db_api_calls + in_memory_api_calls,
        total_mcp_calls=db_mcp_calls + in_memory_mcp_calls,
    )


@router.get("/system", response_model=SystemStatsResponse)
async def get_system_statistics(request: Request, current_user: User = Depends(get_current_active_user)):
    """Get overall system statistics"""
    from api.app_state import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_service = StatisticsService(state.db_manager)
    data = await stats_service.get_system_stats(tenant_key)

    uptime = (datetime.now(timezone.utc) - startup_time).total_seconds()

    return SystemStatsResponse(
        total_projects=data["total_projects"],
        active_projects=data["active_projects"],
        completed_projects=data["completed_projects"],
        projects_finished=data["completed_projects"],
        projects_staged=data["projects_staged"],
        projects_cancelled=data["projects_cancelled"],
        total_agents=data["total_agents"],
        active_agents=data["active_agents"],
        total_messages=data["total_messages"],
        pending_messages=data["pending_messages"],
        total_tasks=data["total_tasks"],
        completed_tasks=data["completed_tasks"],
        database_size_mb=0,
        uptime_seconds=uptime,
        total_agents_spawned=data["total_agents_spawned"],
        total_jobs_completed=data["total_jobs_completed"],
    )


@router.get("/projects", response_model=list[ProjectStatsResponse])
async def get_project_statistics(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by project status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),
):
    """Get statistics for all projects"""
    from api.app_state import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_service = StatisticsService(state.db_manager)
    projects = await stats_service.get_project_stats(tenant_key, status=status, limit=limit, offset=offset)

    stats = []
    for project in projects:
        agent_count = await stats_service.count_agents_for_project(tenant_key, project.id)
        message_count = await stats_service.count_messages_for_project(tenant_key, project.id)
        task_count = await stats_service.count_tasks_for_project(tenant_key, project.id)
        completed_task_count = await stats_service.count_completed_tasks_for_project(tenant_key, project.id)
        last_message = await stats_service.get_last_activity_for_project(tenant_key, project.id)

        # Calculate duration
        end_time = project.updated_at if project.status == "completed" else datetime.now(timezone.utc)
        duration = (end_time - project.created_at).total_seconds()

        stats.append(
            ProjectStatsResponse(
                project_id=str(project.id),
                name=project.name,
                status=project.status,
                duration_seconds=duration,
                agent_count=agent_count,
                message_count=message_count,
                task_count=task_count,
                completed_tasks=completed_task_count,
                last_activity=last_message or project.updated_at,
            )
        )

    return stats


@router.get("/project/{project_id}", response_model=ProjectStatsResponse)
async def get_project_statistics_by_id(
    request: Request, project_id: str, current_user: User = Depends(get_current_active_user)
):
    """Get statistics for a specific project"""
    from api.app_state import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_service = StatisticsService(state.db_manager)
    # Direct single-project query instead of fetching all projects (N+1 fix)
    project = await stats_service.get_project_by_id(tenant_key, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    agent_count = await stats_service.count_agents_for_project(tenant_key, project.id)
    message_count = await stats_service.count_messages_for_project(tenant_key, project.id)
    task_count = await stats_service.count_tasks_for_project(tenant_key, project.id)
    completed_task_count = await stats_service.count_completed_tasks_for_project(tenant_key, project.id)
    last_message = await stats_service.get_last_activity_for_project(tenant_key, project.id)

    end_time = project.updated_at if project.status == "completed" else datetime.now(timezone.utc)
    duration = (end_time - project.created_at).total_seconds()

    return ProjectStatsResponse(
        project_id=str(project.id),
        name=project.name,
        status=project.status,
        duration_seconds=duration,
        agent_count=agent_count,
        message_count=message_count,
        task_count=task_count,
        completed_tasks=completed_task_count,
        last_activity=last_message or project.updated_at,
    )


@router.get("/agents", response_model=list[AgentStatsResponse])
async def get_agent_statistics(
    request: Request,
    project_id: Optional[str] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by agent status"),
    limit: int = Query(100, description="Maximum number of results"),
    current_user: User = Depends(get_current_active_user),
):
    """Get statistics for all agents"""
    from api.app_state import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_service = StatisticsService(state.db_manager)
    agent_executions = await stats_service.get_agent_executions_with_filters(
        tenant_key, project_id=project_id, status=status, limit=limit
    )

    stats = []
    for agent_execution in agent_executions:
        sent_count = await stats_service.count_messages_sent_by_agent(tenant_key, agent_execution.agent_name)
        received_count = await stats_service.count_messages_received_by_agent(tenant_key, agent_execution.agent_name)

        task_count = agent_execution.messages_sent_count
        completed_count = agent_execution.messages_read_count

        avg_response_time = None  # No real metric available yet

        last_sent = await stats_service.get_last_message_sent_by_agent(tenant_key, agent_execution.agent_name)
        agent_job = await stats_service.get_agent_job_by_job_id(tenant_key, agent_execution.job_id)

        created_ts = agent_execution.started_at or (
            agent_execution.job.created_at if agent_job else agent_execution.started_at
        )

        stats.append(
            AgentStatsResponse(
                agent_id=str(agent_execution.agent_id),
                name=agent_execution.agent_name,
                role=agent_execution.agent_display_name,
                status=agent_execution.status,
                project_id=str(agent_job.project_id) if agent_job else "unknown",
                created_at=created_ts,
                messages_sent=sent_count,
                messages_received=received_count,
                tasks_assigned=task_count,
                tasks_completed=completed_count,
                average_response_time_seconds=avg_response_time,
                last_activity=last_sent or created_ts,
            )
        )

    return stats


@router.get("/messages", response_model=MessageStatsResponse)
async def get_message_statistics(
    request: Request,
    project_id: Optional[str] = Query(None, description="Filter by project"),
    time_range: Optional[str] = Query("24h", description="Time range (1h, 24h, 7d, 30d)"),
    current_user: User = Depends(get_current_active_user),
):
    """Get message statistics"""
    from api.app_state import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    now = datetime.now(timezone.utc)
    if time_range == "1h":
        since = now - timedelta(hours=1)
    elif time_range == "24h":
        since = now - timedelta(days=1)
    elif time_range == "7d":
        since = now - timedelta(days=7)
    elif time_range == "30d":
        since = now - timedelta(days=30)
    else:
        since = None

    stats_service = StatisticsService(state.db_manager)
    data = await stats_service.get_message_stats(tenant_key, project_id=project_id, since=since)

    hours_in_range = max((now - since).total_seconds() / 3600, 1) if since else 24
    messages_per_hour = data["total"] / hours_in_range

    return MessageStatsResponse(
        total_messages=data["total"],
        pending_messages=data["pending"],
        acknowledged_messages=data["acknowledged"],
        completed_messages=data["completed"],
        failed_messages=data["failed"],
        average_processing_time_seconds=None,
        messages_per_hour=messages_per_hour,
        peak_hour_messages=None,
    )


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(current_user: User = Depends(get_current_active_user)):
    """Get real-time performance metrics"""
    import time

    import psutil

    from api.app_state import state

    # Measure API response time
    start_time = time.time()

    # Get memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)

    # Get CPU usage
    cpu_percent = psutil.cpu_percent(interval=0.1)

    # Get disk usage
    disk_usage = psutil.disk_usage("/")
    disk_percent = disk_usage.percent

    # Count WebSocket connections
    websocket_connections = len(state.connections) if state.connections else 0

    # Active sessions: no real tracking available yet
    active_sessions = None

    # Error rate: no real tracking available yet
    error_rate = None

    db_query_time = 0
    if state.db_manager:
        stats_service = StatisticsService(state.db_manager)
        db_start = time.time()
        try:
            await stats_service.execute_health_check()
            db_query_time = (time.time() - db_start) * 1000
        except (SQLAlchemyError, OSError):
            logger.exception("Database health check failed")
            db_query_time = -1

    # Calculate API response time
    api_response_time = (time.time() - start_time) * 1000

    return PerformanceMetricsResponse(
        api_response_time_ms=api_response_time,
        database_query_time_ms=db_query_time,
        websocket_connections=websocket_connections,
        active_sessions=active_sessions,
        memory_usage_mb=memory_mb,
        cpu_usage_percent=cpu_percent,
        disk_usage_percent=disk_percent,
        error_rate_percent=error_rate,
    )


@router.get("/health/detailed", response_model=DetailedHealthResponse)
async def get_detailed_health(current_user: User = Depends(get_current_active_user)):
    """Get detailed health status of all system components"""
    from api.app_state import state

    health = {"overall": "healthy", "components": {}, "checks_passed": 0, "checks_failed": 0}

    # Check API
    health["components"]["api"] = {
        "status": "healthy",
        "uptime_seconds": (datetime.now(timezone.utc) - startup_time).total_seconds(),
    }
    health["checks_passed"] += 1

    if state.db_manager:
        stats_service = StatisticsService(state.db_manager)
        try:
            await stats_service.execute_health_check()
            health["components"]["database"] = {"status": "healthy"}
            health["checks_passed"] += 1
        except (RuntimeError, OSError) as e:
            health["components"]["database"] = {"status": "unhealthy", "error": str(e)}
            health["checks_failed"] += 1
            health["overall"] = "degraded"
    else:
        health["components"]["database"] = {"status": "not_configured"}
        health["checks_failed"] += 1

    # Check WebSocket
    if state.websocket_manager:
        health["components"]["websocket"] = {
            "status": "healthy",
            "active_connections": len(state.connections) if state.connections else 0,
        }
        health["checks_passed"] += 1
    else:
        health["components"]["websocket"] = {"status": "not_configured"}

    # Check configuration
    if state.config:
        health["components"]["configuration"] = {"status": "healthy"}
        health["checks_passed"] += 1
    else:
        health["components"]["configuration"] = {"status": "not_loaded"}
        health["checks_failed"] += 1

    # Check authentication
    if state.auth:
        health["components"]["authentication"] = {
            "status": "healthy",
            "auth_enabled": state.config.get("security.auth_enabled", False),
        }
        health["checks_passed"] += 1
    else:
        health["components"]["authentication"] = {"status": "not_configured"}

    # Determine overall health
    if health["checks_failed"] > 0:
        if health["checks_failed"] > health["checks_passed"]:
            health["overall"] = "unhealthy"
        else:
            health["overall"] = "degraded"

    return health
