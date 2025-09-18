"""
Project management REST API endpoints
Exposes project MCP tools as HTTP endpoints
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# Request/Response models
class CreateProjectRequest(BaseModel):
    name: str
    mission: str
    agents: Optional[List[str]] = None

class UpdateProjectRequest(BaseModel):
    mission: Optional[str] = None
    status: Optional[str] = None

class ProjectResponse(BaseModel):
    success: bool
    project_id: Optional[str] = None
    name: Optional[str] = None
    mission: Optional[str] = None
    status: Optional[str] = None
    tenant_key: Optional[str] = None
    agent_count: Optional[int] = None
    context_usage: Optional[str] = None
    created_at: Optional[str] = None
    error: Optional[str] = None


@router.post("/", response_model=ProjectResponse)
async def create_project(request: CreateProjectRequest):
    """Create a new project"""
    try:
        # Properly implement the project creation functionality
        from datetime import datetime, timezone
        from uuid import uuid4

        from src.giljo_mcp.models import Agent, Project, Session

        # Initialize database manager with proper async support
        db_manager = DatabaseManager(is_async=True)
        tenant_manager = TenantManager()

        # Ensure tables exist
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Generate unique tenant key
            tenant_key = f"tk_{uuid4().hex}"

            # Create project
            project = Project(
                name=request.name,
                mission=request.mission,
                tenant_key=tenant_key,
                status="active",
                context_budget=150000,
                context_used=0,
                created_at=datetime.now(timezone.utc),
            )

            session.add(project)
            await session.flush()

            # Create initial session
            initial_session = Session(
                tenant_key=tenant_key,
                project_id=project.id,
                session_number=1,
                title=f"Initial session for {request.name}",
                objectives="Project initialization",
                started_at=datetime.now(timezone.utc)
            )
            session.add(initial_session)

            # Create agents if specified
            agents_created = []
            if request.agents:
                for agent_name in request.agents:
                    agent = Agent(
                        tenant_key=tenant_key,
                        project_id=project.id,
                        name=agent_name,
                        role=agent_name,
                        status="pending",
                        created_at=datetime.now(timezone.utc),
                    )
                    session.add(agent)
                    agents_created.append(agent_name)

            await session.commit()

            # Set as current project in tenant manager
            tenant_manager.set_current_tenant(tenant_key)

            logger.info(f"Created project '{request.name}' with ID {project.id}")

            result = {
                "success": True,
                "project_id": str(project.id),
                "name": request.name,
                "tenant_key": tenant_key,
                "agents_created": agents_created,
                "session_id": str(initial_session.id),
            }

        if result.get("success"):
            return ProjectResponse(
                success=True,
                project_id=result.get("project_id"),
                name=result.get("name"),
                tenant_key=result.get("tenant_key"),
                agent_count=len(result.get("agents_created", [])),
                created_at=result.get("created_at")
            )
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to create project"))

    except Exception as e:
        logger.exception(f"Failed to create project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=List[Dict[str, Any]])
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by project status"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of projects to return"),
    offset: int = Query(0, ge=0, description="Number of projects to skip")
):
    """List all projects with optional filtering"""
    try:
        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Project

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Build query with optional status filter
            query = select(Project)
            if status:
                query = query.where(Project.status == status)

            result = await session.execute(query)
            projects = result.scalars().all()

            project_list = []
            for project in projects:
                # Get agent count for each project
                agent_query = select(Agent).where(Agent.project_id == project.id)
                agent_result = await session.execute(agent_query)
                agents = agent_result.scalars().all()

                project_list.append({
                    "id": str(project.id),
                    "name": project.name,
                    "status": project.status,
                    "tenant_key": project.tenant_key,
                    "agent_count": len(agents),
                    "context_usage": f"{project.context_used}/{project.context_budget}",
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                })

            # Apply pagination
            paginated_projects = project_list[offset:offset + limit]
            return paginated_projects

    except Exception as e:
        logger.exception(f"Failed to list projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get a specific project by ID"""
    try:
        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Project

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Find project by ID
            query = select(Project).where(Project.id == project_id)
            result = await session.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Get agent count
            agent_query = select(Agent).where(Agent.project_id == project.id)
            agent_result = await session.execute(agent_query)
            agents = agent_result.scalars().all()

            return ProjectResponse(
                success=True,
                project_id=str(project.id),
                name=project.name,
                mission=project.mission,
                status=project.status,
                tenant_key=project.tenant_key,
                agent_count=len(agents),
                context_usage=f"{project.context_used}/{project.context_budget}",
                created_at=project.created_at.isoformat() if project.created_at else None
            )

    except Exception as e:
        logger.exception(f"Failed to get project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, request: UpdateProjectRequest):
    """Update a project"""
    try:
        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Project

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Find project
            query = select(Project).where(Project.id == project_id)
            result = await session.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Update mission if provided
            if request.mission:
                project.mission = request.mission

            # Update status if provided
            if request.status:
                project.status = request.status

            await session.commit()

            # Get agent count
            agent_query = select(Agent).where(Agent.project_id == project.id)
            agent_result = await session.execute(agent_query)
            agents = agent_result.scalars().all()

            return ProjectResponse(
                success=True,
                project_id=str(project.id),
                name=project.name,
                mission=project.mission,
                status=project.status,
                tenant_key=project.tenant_key,
                agent_count=len(agents),
                context_usage=f"{project.context_used}/{project.context_budget}"
            )

    except Exception as e:
        logger.exception(f"Failed to update project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}", response_model=ProjectResponse)
async def close_project(
    project_id: str,
    summary: str = Query(..., description="Summary of project completion")
):
    """Close a project"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select, update

        from src.giljo_mcp.models import Agent, Project, Session

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Find project
            query = select(Project).where(Project.id == project_id)
            result = await session.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            if project.status != "active":
                raise HTTPException(status_code=400, detail=f"Project is not active (status: {project.status})")

            # Update project status
            project.status = "completed"
            project.summary = summary
            project.completed_at = datetime.now(timezone.utc)

            # Close all active sessions (sessions without ended_at)
            session_update = (
                update(Session)
                .where(Session.project_id == project.id, Session.ended_at.is_(None))
                .values(ended_at=datetime.now(timezone.utc))
            )
            await session.execute(session_update)

            # Decommission all agents
            agent_update = (
                update(Agent)
                .where(Agent.project_id == project.id, Agent.status.in_(["active", "idle"]))
                .values(status="decommissioned")
            )
            await session.execute(agent_update)

            await session.commit()

            return ProjectResponse(
                success=True,
                project_id=str(project.id),
                name=project.name,
                status="completed"
            )

    except Exception as e:
        logger.exception(f"Failed to close project: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/switch", response_model=ProjectResponse)
async def switch_to_project(project_id: str):
    """Switch to a different project (set as current tenant)"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import Project, Session

        db_manager = DatabaseManager(is_async=True)
        tenant_manager = TenantManager()
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Find project
            query = select(Project).where(Project.id == project_id)
            result = await session.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Set tenant context
            tenant_manager.set_current_tenant(project.tenant_key)

            # Create new session if needed (check for active sessions using ended_at)
            session_query = select(Session).where(Session.project_id == project.id, Session.ended_at.is_(None))
            session_result = await session.execute(session_query)
            active_session = session_result.scalar_one_or_none()

            if not active_session:
                # Get next session number
                next_session_query = select(Session).where(Session.project_id == project.id).order_by(Session.session_number.desc())
                next_session_result = await session.execute(next_session_query)
                last_session = next_session_result.scalar_one_or_none()
                next_number = (last_session.session_number + 1) if last_session else 1

                active_session = Session(
                    tenant_key=project.tenant_key,
                    project_id=project.id,
                    session_number=next_number,
                    title=f"Switched session for {project.name}",
                    objectives="Project switching",
                    started_at=datetime.now(timezone.utc)
                )
                session.add(active_session)
                await session.commit()

            return ProjectResponse(
                success=True,
                project_id=str(project.id),
                name=project.name,
                mission=project.mission,
                tenant_key=project.tenant_key,
                context_usage=f"{project.context_used}/{project.context_budget}"
            )

    except Exception as e:
        logger.exception(f"Failed to switch project: {e}")
        raise HTTPException(status_code=500, detail=str(e))
