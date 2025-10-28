"""
Project management API endpoints
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User

router = APIRouter()


# Pydantic models for request/response
class ProjectCreate(BaseModel):
    name: str = Field(..., description="Project name")
    mission: str = Field(..., description="Project mission statement")
    product_id: Optional[str] = Field(None, description="Product ID to associate with")


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    mission: Optional[str] = None
    status: Optional[str] = None


class ProjectResponse(BaseModel):
    id: str
    alias: str
    name: str
    mission: str
    status: str
    product_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    context_budget: int
    context_used: int
    agent_count: int
    message_count: int


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Create a new project"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:

        # Create project in database
        str(uuid.uuid4())

        # Use the tool accessor, passing the tenant_key from the authenticated user
        result = await state.tool_accessor.create_project(
            name=project.name, mission=project.mission, product_id=project.product_id, tenant_key=current_user.tenant_key
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create project"))  # noqa: TRY301

        # Fetch the created project to get the alias
        from src.giljo_mcp.models import Project
        from sqlalchemy import select

        async with state.db_manager.get_session_async() as session:
            stmt = select(Project).where(Project.id == result["project_id"])
            db_result = await session.execute(stmt)
            created_project = db_result.scalar_one_or_none()
        
        response = ProjectResponse(
            id=result["project_id"],
            alias=created_project.alias if created_project else "UNKNWN",
            name=project.name,
            mission=project.mission,
            status="inactive",
            product_id=project.product_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            context_budget=150000,
            context_used=0,
            agent_count=0,
            message_count=0,
        )

        # Broadcast project creation
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=result["project_id"],
                update_type="created",
                project_data={
                    "name": project.name,
                    "mission": project.mission,
                    "status": "inactive",
                    "context_budget": 150000,
                    "context_used": 0,
                },
            )

        return response  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, description="Maximum number of results"),
    offset: int = Query(0, description="Number of results to skip"),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """List all projects (filtered by user's tenant)"""
    from api.app import state
    import logging
    logger = logging.getLogger(__name__)

    # DIAGNOSTIC: Log authentication success
    logger.info(f"[PROJECTS] Authentication successful - User: {current_user.username}, Tenant: {current_user.tenant_key}, Role: {current_user.role}")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:

        # TENANT ISOLATION: Only return projects for user's tenant
        result = await state.tool_accessor.list_projects(status=status, tenant_key=current_user.tenant_key)
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to list projects"))  # noqa: TRY301

        projects = []
        for proj in result.get("projects", [])[offset : offset + limit]:
            projects.append(
                ProjectResponse(
                    id=proj["id"],
                    alias=proj.get("alias", "UNKNWN"),
                    name=proj["name"],
                    mission=proj["mission"],
                    status=proj["status"],
                    product_id=proj.get("product_id"),
                    created_at=datetime.fromisoformat(proj["created_at"]),
                    updated_at=datetime.fromisoformat(proj.get("updated_at", proj["created_at"])),
                    context_budget=proj.get("context_budget", 150000),
                    context_used=proj.get("context_used", 0),
                    agent_count=proj.get("agent_count", 0),
                    message_count=proj.get("message_count", 0),
                )
            )

        return projects  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-alias/{alias}", response_model=ProjectResponse)
async def get_project_by_alias(alias: str):
    """Get project details by short alias"""
    from api.app import state
    from src.giljo_mcp.models import Project
    from sqlalchemy import select

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Query project by alias
            stmt = select(Project).where(Project.alias == alias.upper())
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(
                    status_code=404,
                    detail=f"Project with alias '{alias}' not found"
                )

            # Get agent and message counts
            from src.giljo_mcp.models import Agent, Message
            
            agent_stmt = select(Agent).where(Agent.project_id == project.id)
            agent_result = await session.execute(agent_stmt)
            agent_count = len(agent_result.scalars().all())
            
            message_stmt = select(Message).where(Message.project_id == project.id)
            message_result = await session.execute(message_stmt)
            message_count = len(message_result.scalars().all())

            return ProjectResponse(
                id=project.id,
                alias=project.alias,
                name=project.name,
                mission=project.mission,
                status=project.status,
                product_id=project.product_id,
                created_at=project.created_at,
                updated_at=project.updated_at or project.created_at,
                context_budget=project.context_budget,
                context_used=project.context_used,
                agent_count=agent_count,
                message_count=message_count,
            )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str):
    """Get project details"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        result = await state.tool_accessor.project_status(project_id=project_id)

        if not result.get("success"):
            raise HTTPException(status_code=404, detail="Project not found")  # noqa: TRY301

        proj = result["project"]
        return ProjectResponse(
            id=proj["id"],
            alias=proj.get("alias", "UNKNWN"),
            name=proj["name"],
            mission=proj["mission"],
            status=proj["status"],
            product_id=proj.get("product_id"),
            created_at=datetime.fromisoformat(proj["created_at"]),
            updated_at=datetime.fromisoformat(proj.get("updated_at", proj["created_at"])),
            context_budget=proj.get("context_budget", 150000),
            context_used=proj.get("context_used", 0),
            agent_count=len(result.get("agents", [])),
            message_count=result.get("pending_messages", 0),
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(project_id: str, update: ProjectUpdate):
    """Update project details"""
    from api.app import state
    from sqlalchemy import select
    from giljo_mcp.models import Project
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        logger.info(f"PATCH /projects/{project_id} - Received update: name={update.name}, mission={update.mission}, status={update.status}")

        # Use a single session for all updates
        async with state.db_manager.get_session_async() as session:
            query = select(Project).where(Project.id == project_id)
            result = await session.execute(query)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            logger.info(f"Project before update: name={project.name}, status={project.status}")

            # Update fields if provided
            if update.name is not None:
                project.name = update.name
                logger.info(f"Updated name to: {project.name}")

            if update.mission is not None:
                project.mission = update.mission
                logger.info(f"Updated mission")

            if update.status is not None:
                logger.info(f"Updating status from '{project.status}' to '{update.status}'")
                
                # Handover 0050 Phase 4: Validate parent product is active when activating project
                if update.status == "active" and project.product_id:
                    from giljo_mcp.models import Product
                    
                    # Fetch parent product
                    product_query = select(Product).where(Product.id == project.product_id)
                    product_result = await session.execute(product_query)
                    parent_product = product_result.scalar_one_or_none()
                    
                    if not parent_product:
                        logger.error(f"Cannot activate project - parent product not found: {project.product_id}")
                        raise HTTPException(
                            status_code=400,
                            detail="Cannot activate project - parent product not found"
                        )
                    
                    if not parent_product.is_active:
                        logger.warning(f"Cannot activate project - parent product '{parent_product.name}' is not active")
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot activate project - parent product '{parent_product.name}' is not active. Please activate the product first."
                        )
                    
                    logger.info(f"Project activation validated - parent product '{parent_product.name}' is active")
                
                project.status = update.status
                logger.info(f"Project status after assignment: {project.status}")

            # Flush changes to database (commit happens automatically on context exit)
            await session.flush()
            logger.info(f"Project status after flush: {project.status}")

            # Broadcast updates
            if state.websocket_manager:
                update_data = {}
                if update.name is not None:
                    update_data["name"] = update.name
                if update.mission is not None:
                    update_data["mission"] = update.mission
                if update.status is not None:
                    update_data["status"] = update.status

                await state.websocket_manager.broadcast_project_update(
                    project_id=project_id,
                    update_type="updated",
                    project_data=update_data
                )

        # Get updated project
        updated_project = await get_project(project_id)
        logger.info(f"Project after retrieval: name={updated_project.name}, status={updated_project.status}")
        return updated_project

    except Exception as e:
        logger.error(f"Failed to update project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{project_id}")
async def close_project(project_id: str, summary: str = Query(..., description="Closing summary")):
    """Close a project"""
    from api.app import state

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        result = await state.tool_accessor.close_project(project_id=project_id, summary=summary)

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to close project"))  # noqa: TRY301

        # Broadcast project closure
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project_id, update_type="closed", project_data={"status": "closed", "summary": summary}
            )

        return {"success": True, "message": "Project closed successfully"}  # noqa: TRY300

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
