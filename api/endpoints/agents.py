"""
Agent management API endpoints
"""

import time
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


router = APIRouter()


class AgentCreate(BaseModel):
    project_id: str = Field(..., description="Project ID")
    agent_name: str = Field(..., description="Agent name")
    mission: Optional[str] = Field(None, description="Agent mission")


class AgentResponse(BaseModel):
    id: str
    name: str
    project_id: str
    status: str
    mission: Optional[str]
    created_at: datetime
    health: dict


async def get_db_session():
    """Get database session dependency"""
    import os
    from src.giljo_mcp.database import DatabaseManager

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")

    db_manager = DatabaseManager(database_url=db_url, is_async=True)
    async with db_manager.get_session_async() as session:
        yield session


@router.post("/", response_model=AgentResponse)
async def create_agent(agent: AgentCreate):
    """Create or ensure an agent exists"""
    from api.app import state

    try:
        result = await state.tool_accessor.ensure_agent(
            project_id=agent.project_id, agent_name=agent.agent_name, mission=agent.mission
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create agent"))  # noqa: TRY301

        response = AgentResponse(
            id=result.get("agent_id", agent.agent_name),
            name=agent.agent_name,
            project_id=agent.project_id,
            status="active",
            mission=agent.mission,
            created_at=datetime.now(timezone.utc),
            health={"status": "healthy", "context_used": 0},
        )

        # Broadcast agent creation/update
        if state.websocket_manager and state.tenant_manager:
            tenant_key = state.tenant_manager.get_current_tenant()
            if tenant_key:
                await state.websocket_manager.broadcast_agent_update(
                    agent_id=result.get("agent_id", agent.agent_name),
                    agent_name=agent.agent_name,
                    project_id=agent.project_id,
                    tenant_key=tenant_key,
                    status="active",
                    context_usage=0,
                    meta_data={"health": response.health, "mission": agent.mission},
                )

        return response  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/", response_model=list[AgentResponse])
async def list_agents(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
):
    """List all agents with optional project filter"""
    from api.app import state

    # Check if database is available (not in setup mode)
    if not state.db_manager:
        # In setup mode, return empty list
        return []

    try:
        from src.giljo_mcp.models import Agent

        async with state.db_manager.get_session_async() as session:
            stmt = select(Agent)

            if project_id:
                stmt = stmt.where(Agent.project_id == project_id)

            stmt = stmt.order_by(Agent.created_at.desc())

            result = await session.execute(stmt)
            agents = result.scalars().all()

            return [
                AgentResponse(
                    id=agent.id,
                    name=agent.name,
                    project_id=agent.project_id,
                    status=agent.status,
                    mission=agent.mission,
                    created_at=agent.created_at,
                    health={
                        "status": agent.status,
                        "context_used": agent.context_used or 0,
                    },
                )
                for agent in agents
            ]

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{agent_name}/health", response_model=dict)
async def get_agent_health(agent_name: str):
    """Get agent health status"""
    from api.app import state

    try:
        result = await state.tool_accessor.agent_health(agent_name=agent_name)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Agent not found")  # noqa: TRY301

        return result.get("health", {})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{agent_name}/decommission")
async def decommission_agent(
    agent_name: str,
    project_id: str = Query(..., description="Project ID"),
    reason: str = Query("completed", description="Decommission reason"),
):
    """Decommission an agent"""
    from api.app import state

    try:
        result = await state.tool_accessor.decommission_agent(
            agent_name=agent_name, project_id=project_id, reason=reason
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to decommission agent"))

        # Broadcast agent decommission
        if state.websocket_manager and state.tenant_manager:
            tenant_key = state.tenant_manager.get_current_tenant()
            if tenant_key:
                await state.websocket_manager.broadcast_agent_update(
                    agent_id=agent_name,  # Use agent_name as ID for decommission
                    agent_name=agent_name,
                    project_id=project_id,
                    tenant_key=tenant_key,
                    status="decommissioned",
                    context_usage=0,
                    meta_data={"reason": reason},
                )

        return {"success": True, "message": f"Agent {agent_name} decommissioned"}  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Tree structure response models
class AgentNode(BaseModel):
    id: str
    name: str
    role: str
    status: str
    project_id: str
    parent_id: Optional[str] = None
    children: list["AgentNode"] = []
    mission: Optional[str] = None
    context_used: int = 0
    created_at: datetime
    last_active: datetime
    jobs_count: int = 0
    messages_sent: int = 0
    messages_received: int = 0


class AgentTreeResponse(BaseModel):
    project_id: str
    total_agents: int
    active_agents: int
    tree: list[AgentNode]
    response_time_ms: float


# Metrics response models
class AgentMetrics(BaseModel):
    total_agents: int
    active_agents: int
    decommissioned_agents: int
    avg_context_usage: float
    total_messages: int
    total_jobs: int
    avg_agent_duration_minutes: float
    agent_by_role: dict[str, int]
    agent_by_status: dict[str, int]
    hourly_activity: list[dict[str, Any]]
    token_usage_by_agent: list[dict[str, Any]]
    response_time_ms: float




@router.get("/tree", response_model=AgentTreeResponse)
async def get_agents_tree(
    project_id: str = Query(..., description="Project ID"),
    session: AsyncSession = Depends(get_db_session),  # noqa: B008
):
    """
    Get hierarchical tree structure of agents in a project.
    Returns parent-child relationships for visualization.
    """
    start_time = time.time()

    try:
        from src.giljo_mcp.models import Agent, Message

        # Query all agents for the project with relationships
        stmt = (
            select(Agent)
            .options(selectinload(Agent.jobs))
            .where(Agent.project_id == project_id)
            .order_by(Agent.created_at)
        )

        result = await session.execute(stmt)
        agents = result.scalars().all()

        # Count messages sent by each agent
        message_counts_stmt = (
            select(Message.from_agent_id, func.count(Message.id).label("sent_count"))
            .where(Message.project_id == project_id)
            .group_by(Message.from_agent_id)
        )

        msg_result = await session.execute(message_counts_stmt)
        message_counts = {row.from_agent_id: row.sent_count for row in msg_result}

        # Count messages received by each agent
        received_counts_stmt = (
            select(Message.to_agent_id, func.count(Message.id).label("received_count"))
            .where(Message.project_id == project_id)
            .group_by(Message.to_agent_id)
        )

        received_result = await session.execute(received_counts_stmt)
        received_counts = {row.to_agent_id: row.received_count for row in received_result}

        # Build tree structure
        agent_nodes = {}
        root_agents = []

        for agent in agents:
            node = AgentNode(
                id=agent.id,
                name=agent.name,
                role=agent.role,
                status=agent.status,
                project_id=agent.project_id,
                mission=agent.mission,
                context_used=agent.context_used or 0,
                created_at=agent.created_at,
                last_active=agent.last_active,
                jobs_count=len(agent.jobs) if agent.jobs else 0,
                messages_sent=message_counts.get(agent.id, 0),
                messages_received=received_counts.get(agent.id, 0),
                children=[],
            )

            agent_nodes[agent.id] = node

            # Orchestrator is always root
            if agent.role == "orchestrator":
                root_agents.append(node)
                node.parent_id = None
            else:
                # For now, all non-orchestrator agents are children of orchestrator
                # This can be enhanced to support more complex hierarchies
                orchestrator = next((a for a in agents if a.role == "orchestrator"), None)
                if orchestrator:
                    node.parent_id = orchestrator.id

        # Build parent-child relationships
        for node in agent_nodes.values():
            if node.parent_id and node.parent_id in agent_nodes:
                agent_nodes[node.parent_id].children.append(node)

        # If no orchestrator, all agents are root level
        if not root_agents:
            root_agents = list(agent_nodes.values())

        response_time = (time.time() - start_time) * 1000  # Convert to ms

        return AgentTreeResponse(
            project_id=project_id,
            total_agents=len(agents),
            active_agents=sum(1 for a in agents if a.status == "active"),
            tree=root_agents,
            response_time_ms=response_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/metrics", response_model=AgentMetrics)
async def get_agents_metrics(
    project_id: Optional[str] = Query(None, description="Project ID (optional for all projects)"),
    hours: int = Query(24, description="Number of hours for activity data"),
    session: AsyncSession = Depends(get_db_session),  # noqa: B008,
):
    """
    Get performance metrics and statistics for agents.
    Includes token usage, success rates, and activity patterns.
    """
    start_time = time.time()

    try:
        from src.giljo_mcp.models import Agent, Job, Message

        # Base query for agents
        agent_query = select(Agent)
        if project_id:
            agent_query = agent_query.where(Agent.project_id == project_id)

        result = await session.execute(agent_query)
        agents = result.scalars().all()

        # Calculate metrics
        total_agents = len(agents)
        active_agents = sum(1 for a in agents if a.status == "active")
        decommissioned_agents = sum(1 for a in agents if a.status == "decommissioned")

        # Average context usage
        context_usages = [a.context_used for a in agents if a.context_used]
        avg_context = sum(context_usages) / len(context_usages) if context_usages else 0

        # Agent counts by role and status
        agent_by_role = {}
        agent_by_status = {}

        for agent in agents:
            agent_by_role[agent.role] = agent_by_role.get(agent.role, 0) + 1
            agent_by_status[agent.status] = agent_by_status.get(agent.status, 0) + 1

        # Count total messages and jobs
        message_query = select(func.count(Message.id))
        job_query = select(func.count(Job.id))

        if project_id:
            message_query = message_query.where(Message.project_id == project_id)
            job_query = job_query.where(Job.agent_id.in_([a.id for a in agents]))

        msg_result = await session.execute(message_query)
        total_messages = msg_result.scalar() or 0

        job_result = await session.execute(job_query)
        total_jobs = job_result.scalar() or 0

        # Calculate average agent duration
        durations = []
        for agent in agents:
            if agent.decommissioned_at and agent.created_at:
                duration = (agent.decommissioned_at - agent.created_at).total_seconds() / 60
                durations.append(duration)

        avg_duration = sum(durations) / len(durations) if durations else 0

        # Hourly activity (last N hours)
        hourly_activity = []
        now = datetime.now(timezone.utc)

        for i in range(hours):
            hour_start = now - timedelta(hours=i + 1)
            hour_end = now - timedelta(hours=i)

            # Count agents active in this hour
            active_in_hour = sum(1 for a in agents if a.last_active and hour_start <= a.last_active < hour_end)

            hourly_activity.append(
                {"hour": hour_start.isoformat(), "active_agents": active_in_hour, "hour_label": f"{i+1}h ago"}
            )

        hourly_activity.reverse()  # Show oldest first

        # Token usage by agent (top 10)
        token_usage = [
            {"agent_name": a.name, "agent_role": a.role, "context_used": a.context_used or 0, "status": a.status}
            for a in sorted(agents, key=lambda x: x.context_used or 0, reverse=True)[:10]
        ]

        response_time = (time.time() - start_time) * 1000  # Convert to ms

        return AgentMetrics(
            total_agents=total_agents,
            active_agents=active_agents,
            decommissioned_agents=decommissioned_agents,
            avg_context_usage=round(avg_context, 2),
            total_messages=total_messages,
            total_jobs=total_jobs,
            avg_agent_duration_minutes=round(avg_duration, 2),
            agent_by_role=agent_by_role,
            agent_by_status=agent_by_status,
            hourly_activity=hourly_activity,
            token_usage_by_agent=token_usage,
            response_time_ms=response_time,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


# Fix forward reference for Pydantic models
AgentNode.model_rebuild()
# Force reload
# Force reload again
