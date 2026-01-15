"""
Statistics and monitoring API endpoints

Handover 1011 Phase 1: Migrated to use StatisticsRepository pattern for all queries.
Original direct SQLAlchemy queries preserved as comments for rollback reference.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from sqlalchemy import and_, func, select
from src.giljo_mcp.colored_logger import get_colored_logger
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
    average_context_usage: float
    peak_context_usage: int
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
    context_used: int
    context_budget: int
    context_usage_percent: float
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
    average_response_time_seconds: float
    last_activity: datetime


class MessageStatsResponse(BaseModel):
    total_messages: int
    pending_messages: int
    acknowledged_messages: int
    completed_messages: int
    failed_messages: int
    average_processing_time_seconds: float
    messages_per_hour: float
    peak_hour_messages: int


class PerformanceMetricsResponse(BaseModel):
    api_response_time_ms: float
    database_query_time_ms: float
    websocket_connections: int
    active_sessions: int
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_usage_percent: float
    error_rate_percent: float


class TimeSeriesDataPoint(BaseModel):
    timestamp: datetime
    value: float
    label: Optional[str] = None


class TimeSeriesResponse(BaseModel):
    metric: str
    period: str
    data_points: list[TimeSeriesDataPoint]


class CallCountsResponse(BaseModel):
    total_api_calls: int
    total_mcp_calls: int


# Store startup time
startup_time = datetime.now(timezone.utc)


@router.get("/call-counts", response_model=CallCountsResponse)
async def get_call_counts(request: Request):
    """Get total API and MCP call counts."""
    from api.app import state

    tenant_key = getattr(request.state, "tenant_key", "default")
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    db_api_calls = 0
    db_mcp_calls = 0

    if state.db_manager:
        stats_repo = StatisticsRepository(state.db_manager)
        async with state.db_manager.get_session_async() as session:
            # ORIGINAL: stmt = select(ApiMetrics).where(ApiMetrics.tenant_key == tenant_key)
            # ORIGINAL: result = await session.execute(stmt)
            # ORIGINAL: metrics = result.scalar_one_or_none()
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
async def get_system_statistics(request: Request):
    """Get overall system statistics"""
    from api.app import state

    tenant_key = getattr(request.state, "tenant_key", None)
    logger.info(f"[STATS DEBUG] tenant_key from request: {tenant_key}")
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        stats_repo = StatisticsRepository(state.db_manager)
        async with state.db_manager.get_session_async() as session:
            # Get project stats
            # ORIGINAL: total_projects = await session.scalar(select(func.count(Project.id)).where(Project.tenant_key == tenant_key))
            total_projects = await stats_repo.count_total_projects(session, tenant_key)
            logger.info(f"[STATS DEBUG] total_projects: {total_projects}")

            # ORIGINAL: active_projects = await session.scalar(select(func.count(Project.id)).where(Project.tenant_key == tenant_key, Project.status == "active"))
            active_projects = await stats_repo.count_projects_by_status(session, tenant_key, "active")
            logger.info(f"[STATS DEBUG] active_projects: {active_projects}")

            # ORIGINAL: completed_projects = await session.scalar(select(func.count(Project.id)).where(Project.tenant_key == tenant_key, Project.status == "completed"))
            completed_projects = await stats_repo.count_projects_by_status(session, tenant_key, "completed")
            logger.info(f"[STATS DEBUG] completed_projects: {completed_projects}")

            # Get agent stats (using AgentExecution)
            # ORIGINAL: total_agents = await session.scalar(select(func.count(AgentExecution.agent_id)).where(AgentExecution.tenant_key == tenant_key))
            total_agents = await stats_repo.count_total_agents(session, tenant_key)
            logger.info(f"[STATS DEBUG] total_agents: {total_agents}")

            # ORIGINAL: active_agents = await session.scalar(select(func.count(AgentExecution.agent_id)).where(AgentExecution.tenant_key == tenant_key, AgentExecution.status.in_(["waiting", "working"])))
            active_agents = await stats_repo.count_active_agents(session, tenant_key)
            logger.info(f"[STATS DEBUG] active_agents: {active_agents}")

            # Get message stats
            # ORIGINAL: total_messages = await session.scalar(select(func.count(Message.id)).where(Message.tenant_key == tenant_key))
            total_messages = await stats_repo.count_total_messages(session, tenant_key)
            logger.info(f"[STATS DEBUG] total_messages: {total_messages}")

            # ORIGINAL: pending_messages = await session.scalar(select(func.count(Message.id)).where(Message.tenant_key == tenant_key, Message.status == "pending"))
            pending_messages = await stats_repo.count_messages_by_status(session, tenant_key, "pending")
            logger.info(f"[STATS DEBUG] pending_messages: {pending_messages}")

            # Get task stats
            # ORIGINAL: total_tasks = await session.scalar(select(func.count(Task.id)).where(Task.tenant_key == tenant_key))
            total_tasks = await stats_repo.count_total_tasks(session, tenant_key)
            logger.info(f"[STATS DEBUG] total_tasks: {total_tasks}")

            # ORIGINAL: completed_tasks = await session.scalar(select(func.count(Task.id)).where(Task.tenant_key == tenant_key, Task.status == "completed"))
            completed_tasks = await stats_repo.count_completed_tasks(session, tenant_key)
            logger.info(f"[STATS DEBUG] completed_tasks: {completed_tasks}")

            # Get context usage stats
            # ORIGINAL: avg_context = await session.scalar(select(func.avg(Project.context_used)).where(Project.tenant_key == tenant_key)) or 0
            # ORIGINAL: peak_context = await session.scalar(select(func.max(Project.context_used)).where(Project.tenant_key == tenant_key)) or 0
            avg_context, peak_context = await stats_repo.get_project_context_stats(session, tenant_key)

            # Get database size (approximate)
            db_size = 0

            # Calculate uptime
            uptime = (datetime.now(timezone.utc) - startup_time).total_seconds()

            # New metrics (using AgentExecution)
            # ORIGINAL: total_agents_spawned = await session.scalar(select(func.count(AgentExecution.agent_id)).where(AgentExecution.tenant_key == tenant_key))
            total_agents_spawned = await stats_repo.count_total_agents(session, tenant_key)

            # ORIGINAL: total_jobs_completed = await session.scalar(select(func.count(AgentExecution.agent_id)).where(AgentExecution.tenant_key == tenant_key, AgentExecution.status == "complete"))
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
                average_context_usage=avg_context,
                peak_context_usage=peak_context,
                database_size_mb=db_size,
                uptime_seconds=uptime,
                total_agents_spawned=total_agents_spawned,
                total_jobs_completed=total_jobs_completed,
            )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=list[ProjectStatsResponse])
async def get_project_statistics(
    request: Request,
    status: Optional[str] = Query(None, description="Filter by project status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
):
    """Get statistics for all projects"""
    from api.app import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        stats_repo = StatisticsRepository(state.db_manager)
        async with state.db_manager.get_session_async() as session:
            # Build query with tenant filtering
            # ORIGINAL: query = select(Project)
            # ORIGINAL: if status: query = query.where(Project.status == status)
            # ORIGINAL: query = query.offset(offset).limit(limit)
            # ORIGINAL: result = await session.execute(query)
            # ORIGINAL: projects = result.scalars().all()
            projects = await stats_repo.get_projects_with_pagination(
                session, tenant_key, status=status, limit=limit, offset=offset
            )

            stats = []
            for project in projects:
                # Get related counts (using AgentExecution joined to AgentJob)
                # ORIGINAL: agent_count = await session.scalar(select(func.count(AgentExecution.agent_id)).join(AgentJob, ...).where(...))
                agent_count = await stats_repo.count_agents_for_project(session, tenant_key, project.id)

                # ORIGINAL: message_count = await session.scalar(select(func.count(Message.id)).where(Message.project_id == project.id))
                message_count = await stats_repo.count_messages_for_project(session, tenant_key, project.id)

                # ORIGINAL: task_count = await session.scalar(select(func.count(Task.id)).where(Task.project_id == project.id))
                task_count = await stats_repo.count_tasks_for_project(session, tenant_key, project.id)

                # ORIGINAL: completed_task_count = await session.scalar(select(func.count(Task.id)).where(and_(Task.project_id == project.id, Task.status == "completed")))
                completed_task_count = await stats_repo.count_completed_tasks_for_project(session, tenant_key, project.id)

                # Get last activity
                # ORIGINAL: last_message = await session.scalar(select(func.max(Message.created_at)).where(Message.project_id == project.id))
                last_message = await stats_repo.get_last_activity_for_project(session, tenant_key, project.id)

                # Calculate duration
                end_time = project.updated_at if project.status == "completed" else datetime.now(timezone.utc)
                duration = (end_time - project.created_at).total_seconds()

                # Calculate context usage
                context_percent = (
                    (project.context_used / project.context_budget * 100) if project.context_budget > 0 else 0
                )

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
                        context_used=project.context_used,
                        context_budget=project.context_budget,
                        context_usage_percent=context_percent,
                        last_activity=last_message or project.updated_at,
                    )
                )

            return stats

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/project/{project_id}", response_model=ProjectStatsResponse)
async def get_project_statistics_by_id(request: Request, project_id: str):
    """Get statistics for a specific project"""
    # CRITICAL: Add tenant_key for security (MISSING IN ORIGINAL!)
    # ORIGINAL: Called get_project_statistics without passing request - security vulnerability!
    stats = await get_project_statistics(request, limit=1)
    for stat in stats:
        if stat.project_id == project_id:
            return stat
    raise HTTPException(status_code=404, detail="Project not found")


@router.get("/agents", response_model=list[AgentStatsResponse])
async def get_agent_statistics(
    request: Request,
    project_id: Optional[str] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by agent status"),
    limit: int = Query(100, description="Maximum number of results"),
):
    """Get statistics for all agents"""
    from api.app import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        stats_repo = StatisticsRepository(state.db_manager)
        async with state.db_manager.get_session_async() as session:
            # Build query (using AgentExecution)
            # ORIGINAL: query = select(AgentExecution)
            # ORIGINAL: if project_id: query = query.join(AgentJob, ...).where(...)
            # ORIGINAL: if status: query = query.where(...)
            # ORIGINAL: query = query.limit(limit)
            # ORIGINAL: result = await session.execute(query)
            # ORIGINAL: agent_executions = result.scalars().all()
            agent_executions = await stats_repo.get_agent_executions_with_filters(
                session, tenant_key, project_id=project_id, status=status, limit=limit
            )

            stats = []
            for agent_execution in agent_executions:
                # Get message counts (using agent_name from AgentExecution)
                # ORIGINAL: sent_count = await session.scalar(select(func.count(Message.id)).where(Message.from_agent == agent_execution.agent_name))
                sent_count = await stats_repo.count_messages_sent_by_agent(
                    session, tenant_key, agent_execution.agent_name
                )

                # ORIGINAL: received_count = await session.scalar(select(func.count(Message.id)).where(Message.to_agents.contains([agent_execution.agent_name])))
                received_count = await stats_repo.count_messages_received_by_agent(
                    session, tenant_key, agent_execution.agent_name
                )

                # Get task counts from messages array
                task_count = 0
                completed_count = 0
                if agent_execution.messages and isinstance(agent_execution.messages, list):
                    tasks = agent_execution.messages
                    if isinstance(tasks, list):
                        task_count = len(tasks)
                        completed_count = sum(1 for t in tasks if isinstance(t, dict) and t.get("status") == "completed")

                # Calculate average response time (simplified)
                avg_response_time = 30.0  # Default 30 seconds

                # Get last activity
                # ORIGINAL: last_sent = await session.scalar(select(func.max(Message.created_at)).where(Message.from_agent == agent_execution.agent_name))
                last_sent = await stats_repo.get_last_message_sent_by_agent(
                    session, tenant_key, agent_execution.agent_name
                )

                # Get project_id by joining to AgentJob
                # ORIGINAL: agent_job = await session.scalar(select(AgentJob).where(AgentJob.job_id == agent_execution.job_id))
                agent_job = await stats_repo.get_agent_job_by_job_id(
                    session, tenant_key, agent_execution.job_id
                )

                created_ts = agent_execution.started_at or (agent_execution.job.created_at if agent_job else agent_execution.started_at)

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/messages", response_model=MessageStatsResponse)
async def get_message_statistics(
    request: Request,
    project_id: Optional[str] = Query(None, description="Filter by project"),
    time_range: Optional[str] = Query("24h", description="Time range (1h, 24h, 7d, 30d)"),
):
    """Get message statistics"""
    from api.app import state

    # CRITICAL: Get tenant_key for security (MISSING IN ORIGINAL!)
    tenant_key = getattr(request.state, "tenant_key", None)
    if not tenant_key:
        raise HTTPException(status_code=400, detail="Tenant key not found in request state")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        stats_repo = StatisticsRepository(state.db_manager)
        async with state.db_manager.get_session_async() as session:
            # Calculate time filter
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

            # Build base query
            # ORIGINAL: base_query = select(Message)
            # ORIGINAL: if project_id: base_query = base_query.where(Message.project_id == project_id)
            # ORIGINAL: if since: base_query = base_query.where(Message.created_at >= since)
            # ORIGINAL: total = await session.scalar(select(func.count(Message.id)).select_from(base_query.subquery()))
            total = await stats_repo.count_messages_with_filters(
                session, tenant_key, project_id=project_id, since=since
            )

            # Get counts by status
            # ORIGINAL: pending = await session.scalar(select(func.count(Message.id)).select_from(base_query.subquery()).where(Message.status == "pending"))
            pending = await stats_repo.count_messages_by_status_with_filters(
                session, tenant_key, status="pending", project_id=project_id, since=since
            )

            # ORIGINAL: acknowledged = await session.scalar(select(func.count(Message.id)).select_from(base_query.subquery()).where(Message.status == "acknowledged"))
            acknowledged = await stats_repo.count_messages_by_status_with_filters(
                session, tenant_key, status="acknowledged", project_id=project_id, since=since
            )

            # ORIGINAL: completed = await session.scalar(select(func.count(Message.id)).select_from(base_query.subquery()).where(Message.status == "completed"))
            completed = await stats_repo.count_messages_by_status_with_filters(
                session, tenant_key, status="completed", project_id=project_id, since=since
            )

            # ORIGINAL: failed = await session.scalar(select(func.count(Message.id)).select_from(base_query.subquery()).where(Message.status == "failed"))
            failed = await stats_repo.count_messages_by_status_with_filters(
                session, tenant_key, status="failed", project_id=project_id, since=since
            )

            # Calculate processing time (simplified)
            avg_processing_time = 45.0  # Default 45 seconds

            # Calculate messages per hour
            hours_in_range = max((now - since).total_seconds() / 3600, 1) if since else 24
            messages_per_hour = total / hours_in_range

            # Find peak hour (simplified)
            peak_hour_messages = int(messages_per_hour * 1.5)  # Estimate

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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance", response_model=PerformanceMetricsResponse)
async def get_performance_metrics():
    """Get real-time performance metrics"""
    import time

    import psutil

    from api.app import state

    try:
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

        # Count active sessions (simplified)
        active_sessions = 1  # Current session

        # Calculate error rate (simplified)
        error_rate = 0.1  # 0.1% error rate

        # Measure database query time
        db_query_time = 0
        if state.db_manager:
            stats_repo = StatisticsRepository(state.db_manager)
            db_start = time.time()
            try:
                async with state.db_manager.get_session_async() as session:
                    # ORIGINAL: await session.execute(select(1))
                    await stats_repo.execute_health_check(session)
                db_query_time = (time.time() - db_start) * 1000
            except Exception:
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

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/timeseries/{metric}", response_model=TimeSeriesResponse)
async def get_timeseries_data(
    metric: str,
    period: str = Query("1h", description="Time period (1h, 24h, 7d)"),
    project_id: Optional[str] = Query(None, description="Filter by project"),
):
    """Get time series data for specific metrics"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    valid_metrics = ["messages", "agents", "tasks", "context_usage", "errors"]
    if metric not in valid_metrics:
        raise HTTPException(status_code=400, detail=f"Invalid metric. Choose from: {valid_metrics}")

    try:
        # Generate sample time series data
        now = datetime.now(timezone.utc)
        data_points = []

        if period == "1h":
            points = 12  # 5-minute intervals
            interval = timedelta(minutes=5)
        elif period == "24h":
            points = 24  # Hourly
            interval = timedelta(hours=1)
        elif period == "7d":
            points = 7  # Daily
            interval = timedelta(days=1)
        else:
            points = 24
            interval = timedelta(hours=1)

        # Generate data points (simplified - in production, query actual data)
        import random

        for i in range(points):
            timestamp = now - (interval * (points - i - 1))

            if metric == "messages":
                value = random.randint(10, 100)  # nosec B311
            elif metric == "agents":
                value = random.randint(1, 10)  # nosec B311
            elif metric == "tasks":
                value = random.randint(5, 50)  # nosec B311
            elif metric == "context_usage":
                value = random.randint(1000, 150000)  # nosec B311
            else:  # errors
                value = random.randint(0, 5)  # nosec B311

            data_points.append(TimeSeriesDataPoint(timestamp=timestamp, value=float(value)))

        return TimeSeriesResponse(metric=metric, period=period, data_points=data_points)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health/detailed")
async def get_detailed_health():
    """Get detailed health status of all system components"""
    from api.app import state

    health = {"overall": "healthy", "components": {}, "checks_passed": 0, "checks_failed": 0}

    # Check API
    health["components"]["api"] = {
        "status": "healthy",
        "uptime_seconds": (datetime.now(timezone.utc) - startup_time).total_seconds(),
    }
    health["checks_passed"] += 1

    # Check database
    if state.db_manager:
        stats_repo = StatisticsRepository(state.db_manager)
        try:
            async with state.db_manager.get_session_async() as session:
                # ORIGINAL: await session.execute(select(1))
                await stats_repo.execute_health_check(session)
            health["components"]["database"] = {"status": "healthy"}
            health["checks_passed"] += 1
        except Exception as e:
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
