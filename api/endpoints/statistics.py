# ruff: noqa: A005
"""
Statistics and monitoring API endpoints

Handover 1011 Phase 1: Migrated to use StatisticsRepository pattern for all queries.
Original direct SQLAlchemy queries preserved as comments for rollback reference.
"""

from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.colored_logger import get_colored_logger
from src.giljo_mcp.models import User
from src.giljo_mcp.repositories.statistics_repository import StatisticsRepository


logger = get_colored_logger(__name__)


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
    peak_hour_messages: int


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


@router.get("/call-counts", response_model=CallCountsResponse)
async def get_call_counts(request: Request, current_user: User = Depends(get_current_active_user)):
    """Get total API and MCP call counts."""
    from api.app import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    db_api_calls = 0
    db_mcp_calls = 0

    if state.db_manager:
        stats_repo = StatisticsRepository(state.db_manager)
        async with state.db_manager.get_session_async() as session:
            metrics = await stats_repo.get_api_metrics(session, tenant_key)
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
    from api.app import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_repo = StatisticsRepository(state.db_manager)
    async with state.db_manager.get_session_async() as session:
        total_projects = await stats_repo.count_total_projects(session, tenant_key)
        active_projects = await stats_repo.count_projects_by_status(session, tenant_key, "active")
        completed_projects = await stats_repo.count_projects_by_status(session, tenant_key, "completed")
        total_agents = await stats_repo.count_total_agents(session, tenant_key)
        active_agents = await stats_repo.count_active_agents(session, tenant_key)
        total_messages = await stats_repo.count_total_messages(session, tenant_key)
        pending_messages = await stats_repo.count_messages_by_status(session, tenant_key, "pending")
        total_tasks = await stats_repo.count_total_tasks(session, tenant_key)
        completed_tasks = await stats_repo.count_completed_tasks(session, tenant_key)

        db_size = 0

        uptime = (datetime.now(timezone.utc) - startup_time).total_seconds()

        total_agents_spawned = await stats_repo.count_total_agents(session, tenant_key)

        total_jobs_completed = await stats_repo.count_completed_agents(session, tenant_key)

        return SystemStatsResponse(
            total_projects=total_projects,
            active_projects=active_projects,
            completed_projects=completed_projects,
            projects_finished=completed_projects,
            total_agents=total_agents,
            active_agents=active_agents,
            total_messages=total_messages,
            pending_messages=pending_messages,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            database_size_mb=db_size,
            uptime_seconds=uptime,
            total_agents_spawned=total_agents_spawned,
            total_jobs_completed=total_jobs_completed,
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
    from api.app import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_repo = StatisticsRepository(state.db_manager)
    async with state.db_manager.get_session_async() as session:
        projects = await stats_repo.get_projects_with_pagination(
            session, tenant_key, status=status, limit=limit, offset=offset
        )

        stats = []
        for project in projects:
            agent_count = await stats_repo.count_agents_for_project(session, tenant_key, project.id)

            message_count = await stats_repo.count_messages_for_project(session, tenant_key, project.id)

            task_count = await stats_repo.count_tasks_for_project(session, tenant_key, project.id)

            completed_task_count = await stats_repo.count_completed_tasks_for_project(session, tenant_key, project.id)

            last_message = await stats_repo.get_last_activity_for_project(session, tenant_key, project.id)

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
    from api.app import state

    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_repo = StatisticsRepository(state.db_manager)
    async with state.db_manager.get_session_async() as session:
        # Direct single-project query instead of fetching all projects (N+1 fix)
        project = await stats_repo.get_project_by_id(session, tenant_key, project_id)
        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        agent_count = await stats_repo.count_agents_for_project(session, tenant_key, project.id)
        message_count = await stats_repo.count_messages_for_project(session, tenant_key, project.id)
        task_count = await stats_repo.count_tasks_for_project(session, tenant_key, project.id)
        completed_task_count = await stats_repo.count_completed_tasks_for_project(session, tenant_key, project.id)
        last_message = await stats_repo.get_last_activity_for_project(session, tenant_key, project.id)

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
    from api.app import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_repo = StatisticsRepository(state.db_manager)
    async with state.db_manager.get_session_async() as session:
        agent_executions = await stats_repo.get_agent_executions_with_filters(
            session, tenant_key, project_id=project_id, status=status, limit=limit
        )

        stats = []
        for agent_execution in agent_executions:
            sent_count = await stats_repo.count_messages_sent_by_agent(session, tenant_key, agent_execution.agent_name)

            received_count = await stats_repo.count_messages_received_by_agent(
                session, tenant_key, agent_execution.agent_name
            )

            task_count = agent_execution.messages_sent_count
            completed_count = agent_execution.messages_read_count

            avg_response_time = None  # No real metric available yet

            last_sent = await stats_repo.get_last_message_sent_by_agent(session, tenant_key, agent_execution.agent_name)

            agent_job = await stats_repo.get_agent_job_by_job_id(session, tenant_key, agent_execution.job_id)

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
    from api.app import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    stats_repo = StatisticsRepository(state.db_manager)
    async with state.db_manager.get_session_async() as session:
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

        total = await stats_repo.count_messages_with_filters(session, tenant_key, project_id=project_id, since=since)

        pending = await stats_repo.count_messages_by_status_with_filters(
            session, tenant_key, status="pending", project_id=project_id, since=since
        )

        acknowledged = await stats_repo.count_messages_by_status_with_filters(
            session, tenant_key, status="acknowledged", project_id=project_id, since=since
        )

        completed = await stats_repo.count_messages_by_status_with_filters(
            session, tenant_key, status="completed", project_id=project_id, since=since
        )

        failed = await stats_repo.count_messages_by_status_with_filters(
            session, tenant_key, status="failed", project_id=project_id, since=since
        )

        avg_processing_time = None  # No real metric available yet

        hours_in_range = max((now - since).total_seconds() / 3600, 1) if since else 24
        messages_per_hour = total / hours_in_range

        peak_hour_messages = int(messages_per_hour * 1.5)

        return MessageStatsResponse(
            total_messages=total,
            pending_messages=pending,
            acknowledged_messages=acknowledged,
            completed_messages=completed,
            failed_messages=failed,
            average_processing_time_seconds=avg_processing_time,
            messages_per_hour=messages_per_hour,
            peak_hour_messages=peak_hour_messages,
        )


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics(current_user: User = Depends(get_current_active_user)):
    """Get real-time performance metrics"""
    import time

    import psutil

    from api.app import state

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
        stats_repo = StatisticsRepository(state.db_manager)
        db_start = time.time()
        try:
            async with state.db_manager.get_session_async() as session:
                await stats_repo.execute_health_check(session)
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
    from api.app import state

    health = {"overall": "healthy", "components": {}, "checks_passed": 0, "checks_failed": 0}

    # Check API
    health["components"]["api"] = {
        "status": "healthy",
        "uptime_seconds": (datetime.now(timezone.utc) - startup_time).total_seconds(),
    }
    health["checks_passed"] += 1

    if state.db_manager:
        stats_repo = StatisticsRepository(state.db_manager)
        try:
            async with state.db_manager.get_session_async() as session:
                await stats_repo.execute_health_check(session)
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
