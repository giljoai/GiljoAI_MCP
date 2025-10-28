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
    status: str = Field(default="inactive", description="Project status (Handover 0050b: defaults to inactive)")
    context_budget: int = Field(default=150000, description="Token budget for the project")


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
            name=project.name,
            mission=project.mission,
            product_id=project.product_id,
            tenant_key=current_user.tenant_key,
            status=project.status,  # Pass status from request (Handover 0050b)
            context_budget=project.context_budget
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
    """
    List all projects (filtered by user's tenant).

    Handover 0070: Excludes deleted projects (status='deleted' OR deleted_at IS NOT NULL).
    Use GET /deleted to see deleted projects.
    """
    from api.app import state
    from src.giljo_mcp.models import Project
    from sqlalchemy import select, or_
    import logging
    logger = logging.getLogger(__name__)

    # DIAGNOSTIC: Log authentication success
    logger.info(f"[PROJECTS] Authentication successful - User: {current_user.username}, Tenant: {current_user.tenant_key}, Role: {current_user.role}")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # TENANT ISOLATION + HANDOVER 0070: Filter deleted projects
            stmt = select(Project).where(
                Project.tenant_key == current_user.tenant_key,
                # Exclude deleted projects
                or_(
                    Project.status != "deleted",
                    Project.deleted_at.is_(None)
                )
            )

            # Apply status filter if provided
            if status:
                stmt = stmt.where(Project.status == status)

            # Apply pagination
            stmt = stmt.offset(offset).limit(limit)

            result = await session.execute(stmt)
            db_projects = result.scalars().all()

            projects = []
            for proj in db_projects:
                # Get agent and message counts
                from src.giljo_mcp.models import Agent, Message

                agent_stmt = select(Agent).where(Agent.project_id == proj.id)
                agent_result = await session.execute(agent_stmt)
                agent_count = len(agent_result.scalars().all())

                message_stmt = select(Message).where(Message.project_id == proj.id)
                message_result = await session.execute(message_stmt)
                message_count = len(message_result.scalars().all())

                projects.append(
                    ProjectResponse(
                        id=proj.id,
                        alias=proj.alias,
                        name=proj.name,
                        mission=proj.mission,
                        status=proj.status,
                        product_id=proj.product_id,
                        created_at=proj.created_at,
                        updated_at=proj.updated_at or proj.created_at,
                        context_budget=proj.context_budget,
                        context_used=proj.context_used,
                        agent_count=agent_count,
                        message_count=message_count,
                    )
                )

            return projects

    except Exception as e:
        logger.error(f"Failed to list projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-alias/{alias}", response_model=ProjectResponse)
async def get_project_by_alias(alias: str):
    """
    Get project details by short alias.

    Handover 0070: Excludes deleted projects.
    """
    from api.app import state
    from src.giljo_mcp.models import Project
    from sqlalchemy import select, or_

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Query project by alias (Handover 0070: Exclude deleted projects)
            stmt = select(Project).where(
                Project.alias == alias.upper(),
                # Exclude deleted projects
                or_(
                    Project.status != "deleted",
                    Project.deleted_at.is_(None)
                )
            )
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
async def delete_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Soft delete a project (Handover 0070).

    Sets status='deleted' and deleted_at=NOW(). Project will be purged after 10 days.
    Recovery available via: Settings -> Database -> Deleted Projects
    """
    from api.app import state
    from src.giljo_mcp.models import Project
    from sqlalchemy import select
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Fetch project and verify tenant ownership
            stmt = select(Project).where(
                Project.id == project_id,
                Project.tenant_key == current_user.tenant_key
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Check if already deleted
            if project.status == "deleted" and project.deleted_at is not None:
                raise HTTPException(status_code=400, detail="Project already deleted")

            # Soft delete: Set status and deleted_at timestamp
            project.status = "deleted"
            project.deleted_at = datetime.now(timezone.utc)
            project.updated_at = datetime.now(timezone.utc)

            await session.flush()

            logger.info(f"[Handover 0070] Project '{project.name}' (id: {project_id}) soft deleted by {current_user.username}")

        # Broadcast project deletion
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type="deleted",
                project_data={
                    "status": "deleted",
                    "deleted_at": project.deleted_at.isoformat(),
                    "message": "Project will be permanently purged in 10 days"
                }
            )

        return {
            "success": True,
            "message": "Project deleted from view. Will be permanently purged in 10 days.",
            "recovery_info": "To recover: Settings → Database → Deleted Projects"
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


class DeletedProjectResponse(BaseModel):
    id: str
    alias: str
    name: str
    product_id: Optional[str] = None
    product_name: Optional[str] = None
    deleted_at: datetime
    days_until_purge: int
    purge_date: datetime


@router.get("/deleted", response_model=list[DeletedProjectResponse])
async def list_deleted_projects(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    List all deleted projects for the current tenant (Handover 0070).

    Returns projects with status='deleted' and calculated purge countdown.
    Projects are purged 10 days after deletion.
    """
    from api.app import state
    from src.giljo_mcp.models import Project, Product
    from sqlalchemy import select
    from datetime import timedelta
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Query deleted projects for this tenant
            stmt = select(Project, Product).outerjoin(
                Product, Project.product_id == Product.id
            ).where(
                Project.tenant_key == current_user.tenant_key,
                Project.deleted_at.isnot(None)
            ).order_by(Project.deleted_at.desc())

            result = await session.execute(stmt)
            rows = result.all()

            deleted_projects = []
            now = datetime.now(timezone.utc)

            for project, product in rows:
                # Calculate days until purge (10 days from deletion)
                purge_date = project.deleted_at + timedelta(days=10)
                days_until_purge = max(0, (purge_date - now).days)

                deleted_projects.append(
                    DeletedProjectResponse(
                        id=project.id,
                        alias=project.alias,
                        name=project.name,
                        product_id=project.product_id,
                        product_name=product.name if product else None,
                        deleted_at=project.deleted_at,
                        days_until_purge=days_until_purge,
                        purge_date=purge_date
                    )
                )

            logger.info(f"[Handover 0070] Retrieved {len(deleted_projects)} deleted projects for tenant {current_user.tenant_key}")
            return deleted_projects

    except Exception as e:
        logger.error(f"Failed to list deleted projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """
    Restore a soft-deleted project (Handover 0070).

    Sets status='inactive' (safe default) and clears deleted_at.
    User must manually activate project after restoration.
    """
    from api.app import state
    from src.giljo_mcp.models import Project, Agent, Message
    from sqlalchemy import select
    import logging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Fetch project and verify tenant ownership
            stmt = select(Project).where(
                Project.id == project_id,
                Project.tenant_key == current_user.tenant_key
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found or already purged")

            # Verify project is deleted
            if project.deleted_at is None:
                raise HTTPException(status_code=400, detail="Project is not deleted")

            # Restore project: Set to inactive (safe default)
            project.status = "inactive"
            project.deleted_at = None
            project.updated_at = datetime.now(timezone.utc)

            await session.flush()

            # Get agent and message counts
            agent_stmt = select(Agent).where(Agent.project_id == project.id)
            agent_result = await session.execute(agent_stmt)
            agent_count = len(agent_result.scalars().all())

            message_stmt = select(Message).where(Message.project_id == project.id)
            message_result = await session.execute(message_stmt)
            message_count = len(message_result.scalars().all())

            logger.info(f"[Handover 0070] Project '{project.name}' (id: {project_id}) restored by {current_user.username}")

        # Broadcast project restoration
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type="restored",
                project_data={
                    "status": "inactive",
                    "deleted_at": None,
                    "message": "Project restored successfully"
                }
            )

        # Return restored project
        return ProjectResponse(
            id=project.id,
            alias=project.alias,
            name=project.name,
            mission=project.mission,
            status=project.status,
            product_id=project.product_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            context_budget=project.context_budget,
            context_used=project.context_used,
            agent_count=agent_count,
            message_count=message_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to restore project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


async def purge_expired_deleted_projects(db_manager) -> dict:
    """
    Purge projects deleted more than 10 days ago (Handover 0070).

    This function performs cascade deletion:
    1. Deletes child agents
    2. Deletes child tasks
    3. Deletes child messages
    4. Deletes the project record

    Called from startup.py on server start.

    Args:
        db_manager: DatabaseManager instance

    Returns:
        dict: Purge results with count and details
    """
    from src.giljo_mcp.models import Project, Agent, Task, Message
    from sqlalchemy import select
    from datetime import timedelta
    import logging

    logger = logging.getLogger(__name__)

    if not db_manager:
        logger.error("[Handover 0070] Cannot purge - database manager not available")
        return {"success": False, "error": "Database not available"}

    try:
        async with db_manager.get_session_async() as session:
            # Find projects deleted more than 10 days ago
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=10)

            stmt = select(Project).where(
                Project.deleted_at.isnot(None),
                Project.deleted_at < cutoff_date
            )

            result = await session.execute(stmt)
            expired_projects = result.scalars().all()

            if not expired_projects:
                logger.info("[Handover 0070] No expired deleted projects to purge")
                return {"success": True, "purged_count": 0, "projects": []}

            purged_projects = []

            for project in expired_projects:
                project_info = {
                    "id": project.id,
                    "name": project.name,
                    "tenant_key": project.tenant_key,
                    "deleted_at": project.deleted_at.isoformat()
                }

                # Cascade delete: agents
                agent_stmt = select(Agent).where(Agent.project_id == project.id)
                agent_result = await session.execute(agent_stmt)
                agents = agent_result.scalars().all()
                for agent in agents:
                    await session.delete(agent)

                # Cascade delete: tasks
                task_stmt = select(Task).where(Task.project_id == project.id)
                task_result = await session.execute(task_stmt)
                tasks = task_result.scalars().all()
                for task in tasks:
                    await session.delete(task)

                # Cascade delete: messages
                message_stmt = select(Message).where(Message.project_id == project.id)
                message_result = await session.execute(message_stmt)
                messages = message_result.scalars().all()
                for message in messages:
                    await session.delete(message)

                # Delete project
                await session.delete(project)

                logger.info(
                    f"[Handover 0070] Purged project '{project.name}' (id: {project.id}, "
                    f"tenant: {project.tenant_key}, deleted: {project.deleted_at})"
                )

                purged_projects.append(project_info)

            await session.flush()

            logger.info(f"[Handover 0070] Successfully purged {len(purged_projects)} expired deleted projects")

            return {
                "success": True,
                "purged_count": len(purged_projects),
                "projects": purged_projects
            }

    except Exception as e:
        logger.error(f"[Handover 0070] Failed to purge expired deleted projects: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "purged_count": 0
        }
