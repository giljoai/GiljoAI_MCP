"""
Agent management REST API endpoints
Exposes agent MCP tools as HTTP endpoints
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/agents", tags=["agents"])

# Request/Response models
class CreateAgentRequest(BaseModel):
    project_id: str
    agent_name: str
    mission: Optional[str] = None

class AssignJobRequest(BaseModel):
    agent_name: str
    job_type: str
    project_id: str
    tasks: Optional[List[str]] = None
    scope_boundary: Optional[str] = None
    vision_alignment: Optional[str] = None

class HandoffRequest(BaseModel):
    from_agent: str
    to_agent: str
    project_id: str
    context: Dict[str, Any]

class AgentResponse(BaseModel):
    success: bool
    agent: Optional[str] = None
    agent_id: Optional[str] = None
    status: Optional[str] = None
    job_id: Optional[str] = None
    message: Optional[str] = None
    error: Optional[str] = None


@router.post("/", response_model=AgentResponse)
async def create_agent(request: CreateAgentRequest):
    """Create or ensure an agent exists"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Project

        db_manager = DatabaseManager(is_async=True)
        tenant_manager = TenantManager()
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Verify project exists
            project_query = select(Project).where(Project.id == request.project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Check if agent already exists
            agent_query = select(Agent).where(
                Agent.project_id == request.project_id,
                Agent.name == request.agent_name
            )
            agent_result = await session.execute(agent_query)
            existing_agent = agent_result.scalar_one_or_none()

            if existing_agent:
                # Update existing agent
                if request.mission:
                    existing_agent.mission = request.mission
                await session.commit()

                return AgentResponse(
                    success=True,
                    agent_name=existing_agent.name,
                    status=existing_agent.status,
                    project_id=str(existing_agent.project_id)
                )
            # Create new agent
            new_agent = Agent(
                tenant_key=project.tenant_key,
                project_id=request.project_id,
                name=request.agent_name,
                role=request.agent_name,
                mission=request.mission or f"Agent {request.agent_name}",
                status="pending",
                created_at=datetime.now(timezone.utc)
            )
            session.add(new_agent)
            await session.commit()

            return AgentResponse(
                success=True,
                agent_name=new_agent.name,
                status=new_agent.status,
                project_id=str(new_agent.project_id)
            )

    except Exception as e:
        logger.exception(f"Failed to create agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/activate", response_model=AgentResponse)
async def activate_agent(request: CreateAgentRequest):
    """Activate an agent (starts working immediately)"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Project

        db_manager = DatabaseManager(is_async=True)
        tenant_manager = TenantManager()
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Verify project exists
            project_query = select(Project).where(Project.id == request.project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Check if agent already exists
            agent_query = select(Agent).where(
                Agent.project_id == request.project_id,
                Agent.name == request.agent_name
            )
            agent_result = await session.execute(agent_query)
            existing_agent = agent_result.scalar_one_or_none()

            if existing_agent:
                # Update existing agent to active status
                existing_agent.status = "active"
                existing_agent.last_active = datetime.now(timezone.utc)
                if request.mission:
                    existing_agent.mission = request.mission
                await session.commit()

                return AgentResponse(
                    success=True,
                    agent=existing_agent.name,
                    agent_id=str(existing_agent.id),
                    status=existing_agent.status,
                    message=f"Activated existing agent {existing_agent.name}"
                )
            # Create new agent
            new_agent = Agent(
                tenant_key=project.tenant_key,
                project_id=request.project_id,
                name=request.agent_name,
                role=request.agent_name,
                mission=request.mission or f"Agent {request.agent_name}",
                status="active",
                created_at=datetime.now(timezone.utc),
                last_active=datetime.now(timezone.utc)
            )
            session.add(new_agent)
            await session.commit()

            return AgentResponse(
                success=True,
                agent=new_agent.name,
                agent_id=str(new_agent.id),
                status=new_agent.status,
                message=f"Created and activated agent {new_agent.name}"
            )

    except Exception as e:
        logger.exception(f"Failed to activate agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/assign-job", response_model=AgentResponse)
async def assign_job_to_agent(request: AssignJobRequest):
    """Assign a job to an agent"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Job

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Find agent
            agent_query = select(Agent).where(
                Agent.project_id == request.project_id,
                Agent.name == request.agent_name
            )
            agent_result = await session.execute(agent_query)
            agent = agent_result.scalar_one_or_none()

            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            # Update or create active job
            active_job_query = select(Job).where(
                Job.agent_id == agent.id,
                Job.status == "active"
            )
            job_result = await session.execute(active_job_query)
            existing_job = job_result.scalar_one_or_none()

            if existing_job:
                # Update existing job
                existing_job.job_type = request.job_type
                existing_job.tasks = request.tasks or []
                existing_job.scope_boundary = request.scope_boundary
                existing_job.vision_alignment = request.vision_alignment
                job = existing_job
            else:
                # Create new job
                job = Job(
                    tenant_key=agent.tenant_key,
                    agent_id=agent.id,
                    job_type=request.job_type,
                    tasks=request.tasks or [],
                    scope_boundary=request.scope_boundary,
                    vision_alignment=request.vision_alignment,
                    status="active",
                    created_at=datetime.now(timezone.utc)
                )
                session.add(job)

            # Update agent status
            agent.status = "working"
            agent.last_active = datetime.now(timezone.utc)

            await session.commit()

            return AgentResponse(
                success=True,
                agent=agent.name,
                job_id=str(job.id),
                message=f"Assigned {request.job_type} job with {len(request.tasks or [])} tasks"
            )

    except Exception as e:
        logger.exception(f"Failed to assign job: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{agent_name}/health")
async def get_agent_health(
    agent_name: Optional[str] = None,
    project_id: Optional[str] = Query(None, description="Project ID for context")
):
    """Get agent health and status"""
    try:
        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Job, Project

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            if agent_name:
                # Get specific agent
                agent_query = select(Agent)
                if project_id:
                    agent_query = agent_query.where(
                        Agent.name == agent_name,
                        Agent.project_id == project_id
                    )
                else:
                    agent_query = agent_query.where(Agent.name == agent_name)

                agent_result = await session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    raise HTTPException(status_code=404, detail="Agent not found")

                # Get agent's active job
                job_query = select(Job).where(
                    Job.agent_id == agent.id,
                    Job.status == "active"
                )
                job_result = await session.execute(job_query)
                active_job = job_result.scalar_one_or_none()

                # Get project context usage
                project_query = select(Project).where(Project.id == agent.project_id)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                agents = [{
                    "name": agent.name,
                    "status": agent.status,
                    "role": agent.role,
                    "context_used": agent.context_used,
                    "last_active": agent.last_active.isoformat() if agent.last_active else None,
                    "active_job": {
                        "id": str(active_job.id),
                        "job_type": active_job.job_type,
                        "tasks_count": len(active_job.tasks) if active_job.tasks else 0
                    } if active_job else None
                }]

                return {
                    "success": True,
                    "project_context_usage": f"{project.context_used}/{project.context_budget}" if project else "Unknown",
                    "agents": agents
                }
            # Get all agents for project or system
            agent_query = select(Agent)
            if project_id:
                agent_query = agent_query.where(Agent.project_id == project_id)

            agent_result = await session.execute(agent_query)
            agents_list = agent_result.scalars().all()

            agents = []
            for agent in agents_list:
                # Get active job for each agent
                job_query = select(Job).where(
                    Job.agent_id == agent.id,
                    Job.status == "active"
                )
                job_result = await session.execute(job_query)
                active_job = job_result.scalar_one_or_none()

                agents.append({
                    "name": agent.name,
                    "status": agent.status,
                    "role": agent.role,
                    "context_used": agent.context_used,
                    "last_active": agent.last_active.isoformat() if agent.last_active else None,
                    "active_job": {
                        "id": str(active_job.id),
                        "job_type": active_job.job_type,
                        "tasks_count": len(active_job.tasks) if active_job.tasks else 0
                    } if active_job else None
                })

            return {
                "success": True,
                "project_context_usage": "Multiple projects" if not project_id else "Unknown",
                "agents": agents
            }

    except Exception as e:
        logger.exception(f"Failed to get agent health: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/handoff", response_model=Dict[str, Any])
async def handoff_work(request: HandoffRequest):
    """Transfer work from one agent to another"""
    try:
        import json
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Job, Message, Project

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Verify project exists
            project_query = select(Project).where(Project.id == request.project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Get from_agent
            from_agent_query = select(Agent).where(
                Agent.project_id == request.project_id,
                Agent.name == request.from_agent
            )
            from_agent_result = await session.execute(from_agent_query)
            from_agent = from_agent_result.scalar_one_or_none()

            if not from_agent:
                raise HTTPException(status_code=404, detail=f"From agent '{request.from_agent}' not found")

            # Get to_agent
            to_agent_query = select(Agent).where(
                Agent.project_id == request.project_id,
                Agent.name == request.to_agent
            )
            to_agent_result = await session.execute(to_agent_query)
            to_agent = to_agent_result.scalar_one_or_none()

            if not to_agent:
                raise HTTPException(status_code=404, detail=f"To agent '{request.to_agent}' not found")

            # Transfer active job from from_agent to to_agent
            active_job_query = select(Job).where(
                Job.agent_id == from_agent.id,
                Job.status == "active"
            )
            job_result = await session.execute(active_job_query)
            active_job = job_result.scalar_one_or_none()

            if active_job:
                # Close current job
                active_job.status = "completed"
                active_job.completed_at = datetime.now(timezone.utc)

                # Create new job for to_agent
                new_job = Job(
                    tenant_key=project.tenant_key,
                    agent_id=to_agent.id,
                    job_type=active_job.job_type,
                    tasks=active_job.tasks,
                    scope_boundary=active_job.scope_boundary,
                    vision_alignment=active_job.vision_alignment,
                    status="active",
                    created_at=datetime.now(timezone.utc),
                    meta_data={
                        "handoff_from": request.from_agent,
                        "original_job_id": str(active_job.id),
                        "handoff_context": request.context
                    }
                )
                session.add(new_job)

            # Create handoff message
            handoff_message = Message(
                tenant_key=project.tenant_key,
                project_id=request.project_id,
                from_agent_id=from_agent.id,
                to_agents=[request.to_agent],
                message_type="handoff",
                subject=f"Work handoff from {request.from_agent}",
                content=f"Work has been transferred from {request.from_agent}. Context: {json.dumps(request.context)}",
                priority="high",
                status="pending",
                created_at=datetime.now(timezone.utc),
                meta_data={
                    "handoff_context": request.context,
                    "transferred_job_id": str(new_job.id) if active_job else None
                }
            )
            session.add(handoff_message)

            # Update agent statuses
            from_agent.status = "idle"
            to_agent.status = "working"
            to_agent.last_active = datetime.now(timezone.utc)

            await session.commit()

            return {
                "success": True,
                "from_agent": request.from_agent,
                "to_agent": request.to_agent,
                "message_id": str(handoff_message.id),
                "context_transferred": request.context,
                "job_transferred": str(new_job.id) if active_job else None
            }

    except Exception as e:
        logger.exception(f"Failed to perform handoff: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{agent_name}")
async def decommission_agent(
    agent_name: str,
    project_id: str = Query(..., description="Project ID"),
    reason: str = Query("completed", description="Reason for decommissioning")
):
    """Decommission an agent"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select, update

        from src.giljo_mcp.models import Agent, Job

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Find the agent
            agent_query = select(Agent).where(
                Agent.project_id == project_id,
                Agent.name == agent_name
            )
            agent_result = await session.execute(agent_query)
            agent = agent_result.scalar_one_or_none()

            if not agent:
                raise HTTPException(status_code=404, detail="Agent not found")

            # Cannot decommission already decommissioned agents
            if agent.status == "decommissioned":
                raise HTTPException(status_code=400, detail="Agent already decommissioned")

            # Complete all active jobs
            active_jobs_update = (
                update(Job)
                .where(Job.agent_id == agent.id, Job.status == "active")
                .values(
                    status="completed",
                    completed_at=datetime.now(timezone.utc),
                    meta_data=Job.meta_data.op("||")({"decommission_reason": reason})
                )
            )
            await session.execute(active_jobs_update)

            # Store context usage before decommissioning
            context_used = agent.context_used

            # Update agent status
            agent.status = "decommissioned"
            agent.decommissioned_at = datetime.now(timezone.utc)
            agent.meta_data = {
                **(agent.meta_data or {}),
                "decommission_reason": reason,
                "decommission_timestamp": datetime.now(timezone.utc).isoformat()
            }

            await session.commit()

            return {
                "success": True,
                "agent": agent_name,
                "status": "decommissioned",
                "reason": reason,
                "context_used": context_used,
                "decommissioned_at": agent.decommissioned_at.isoformat()
            }

    except Exception as e:
        logger.exception(f"Failed to decommission agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_agents(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    status: Optional[str] = Query(None, description="Filter by agent status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of agents to return")
):
    """List agents with optional filtering"""
    try:
        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Job

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Build query with filters
            agent_query = select(Agent)
            if project_id:
                agent_query = agent_query.where(Agent.project_id == project_id)
            if status:
                agent_query = agent_query.where(Agent.status == status)

            # Order by last_active descending
            agent_query = agent_query.order_by(Agent.last_active.desc())

            agent_result = await session.execute(agent_query)
            agents_list = agent_result.scalars().all()

            agents = []
            for agent in agents_list[:limit]:
                # Get active job for each agent
                job_query = select(Job).where(
                    Job.agent_id == agent.id,
                    Job.status == "active"
                )
                job_result = await session.execute(job_query)
                active_job = job_result.scalar_one_or_none()

                agents.append({
                    "id": str(agent.id),
                    "name": agent.name,
                    "status": agent.status,
                    "role": agent.role,
                    "project_id": str(agent.project_id),
                    "context_used": agent.context_used,
                    "last_active": agent.last_active.isoformat() if agent.last_active else None,
                    "created_at": agent.created_at.isoformat() if agent.created_at else None,
                    "decommissioned_at": agent.decommissioned_at.isoformat() if agent.decommissioned_at else None,
                    "active_job": {
                        "id": str(active_job.id),
                        "job_type": active_job.job_type,
                        "tasks_count": len(active_job.tasks) if active_job.tasks else 0,
                        "created_at": active_job.created_at.isoformat() if active_job.created_at else None
                    } if active_job else None
                })

            return agents

    except Exception as e:
        logger.exception(f"Failed to list agents: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_name}/sub-agent/spawn")
async def spawn_sub_agent(
    agent_name: str,
    project_id: str = Query(..., description="Project ID"),
    sub_agent_name: str = Query(..., description="Sub-agent name"),
    mission: str = Query(..., description="Sub-agent mission"),
    meta_data: Optional[Dict[str, Any]] = None
):
    """Log spawning of a sub-agent"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, AgentInteraction, Project

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Verify project exists
            project_query = select(Project).where(Project.id == project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Find parent agent
            parent_agent_query = select(Agent).where(
                Agent.project_id == project_id,
                Agent.name == agent_name
            )
            parent_agent_result = await session.execute(parent_agent_query)
            parent_agent = parent_agent_result.scalar_one_or_none()

            if not parent_agent:
                raise HTTPException(status_code=404, detail=f"Parent agent '{agent_name}' not found")

            # Create interaction record for spawning
            interaction = AgentInteraction(
                tenant_key=project.tenant_key,
                project_id=project_id,
                parent_agent_id=parent_agent.id,
                sub_agent_name=sub_agent_name,
                interaction_type="SPAWN",
                mission=mission,
                start_time=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                meta_data=meta_data or {}
            )
            session.add(interaction)

            # Update parent agent activity
            parent_agent.last_active = datetime.now(timezone.utc)

            await session.commit()

            return {
                "success": True,
                "interaction_id": str(interaction.id),
                "parent_agent": agent_name,
                "sub_agent": sub_agent_name,
                "mission": mission,
                "start_time": interaction.start_time.isoformat()
            }

    except Exception as e:
        logger.exception(f"Failed to spawn sub-agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sub-agent/{interaction_id}/complete")
async def complete_sub_agent(
    interaction_id: str,
    result: Optional[str] = None,
    tokens_used: Optional[int] = None,
    error_message: Optional[str] = None,
    meta_data: Optional[Dict[str, Any]] = None
):
    """Log completion of a sub-agent task"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import AgentInteraction

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Find the interaction record
            interaction_query = select(AgentInteraction).where(
                AgentInteraction.id == interaction_id
            )
            interaction_result = await session.execute(interaction_query)
            interaction = interaction_result.scalar_one_or_none()

            if not interaction:
                raise HTTPException(status_code=404, detail="Interaction not found")

            if interaction.end_time is not None:
                raise HTTPException(status_code=400, detail="Interaction already completed")

            # Calculate duration
            end_time = datetime.now(timezone.utc)
            duration_seconds = int((end_time - interaction.start_time).total_seconds())

            # Update interaction with completion data
            interaction.end_time = end_time
            interaction.duration_seconds = duration_seconds
            interaction.tokens_used = tokens_used
            interaction.result = result
            interaction.error_message = error_message

            # Set interaction type based on outcome
            if error_message:
                interaction.interaction_type = "ERROR"
            else:
                interaction.interaction_type = "COMPLETE"

            # Merge metadata
            if meta_data:
                interaction.meta_data = {
                    **(interaction.meta_data or {}),
                    **meta_data
                }

            await session.commit()

            return {
                "success": True,
                "interaction_id": str(interaction.id),
                "sub_agent": interaction.sub_agent_name,
                "status": interaction.interaction_type.lower(),
                "duration_seconds": duration_seconds,
                "tokens_used": tokens_used,
                "start_time": interaction.start_time.isoformat(),
                "end_time": end_time.isoformat()
            }

    except Exception as e:
        logger.exception(f"Failed to complete sub-agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))
