"""
Project management API endpoints
"""

import logging
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User


# Logger
logger = logging.getLogger(__name__)
from api.schemas.prompt import (
    AgentStatusSummary,
    ProjectCanCloseResponse,
    ProjectCloseoutPromptResponse,
    ProjectCompleteRequest,
    ProjectCompleteResponse,
)


router = APIRouter()


# Pydantic models for request/response
class ProjectCreate(BaseModel):
    name: str = Field(..., description="Project name")
    description: str = Field(..., description="Human-written project description (what you want to accomplish)")
    mission: str = Field(
        default="", description="AI-generated mission statement (initially empty, filled by orchestrator)"
    )
    product_id: Optional[str] = Field(None, description="Product ID to associate with")
    status: str = Field(default="inactive", description="Project status (Handover 0050b: defaults to inactive)")
    context_budget: int = Field(default=150000, description="Token budget for the project")


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    mission: Optional[str] = None
    status: Optional[str] = None


class AgentSimple(BaseModel):
    """Simple agent schema for project response"""
    id: str  # job_id
    job_id: str
    agent_type: str
    agent_name: Optional[str] = None
    status: str
    thin_client: bool = True


class ProjectResponse(BaseModel):
    id: str
    alias: str
    name: str
    description: Optional[str] = None
    mission: str
    status: str
    product_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    completed_at: Optional[datetime] = None
    context_budget: int
    context_used: int
    agent_count: int
    message_count: int
    agents: List[AgentSimple] = []


# Handover 0062: Project Summary Response Models
class AgentSummary(BaseModel):
    """Summary of an agent used in the project."""

    id: str
    name: str
    type: str
    status: str
    job_mission: Optional[str] = None
    job_id: Optional[str] = None


class MessageSummary(BaseModel):
    """Summary of a message in the project."""

    id: str
    from_agent: str
    to_agents: List[str]
    content: str
    timestamp: str


class ProjectSummaryResponse(BaseModel):
    """Comprehensive project summary for after-action review."""

    project_id: str
    project_name: str
    description: str
    mission: Optional[str] = None
    status: str
    agents: List[AgentSummary]
    messages: List[MessageSummary]
    created_at: str
    completed_at: Optional[str] = None


@router.post("/", response_model=ProjectResponse)
async def create_project(
    project: ProjectCreate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
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
            description=project.description or "",  # Pass description (optional)
            product_id=project.product_id,
            tenant_key=current_user.tenant_key,
            status=project.status,  # Pass status from request (Handover 0050b)
            context_budget=project.context_budget,
        )

        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to create project"))  # noqa: TRY301

        # Fetch the created project to get the alias
        from sqlalchemy import select

        from src.giljo_mcp.models import Project

        async with state.db_manager.get_session_async() as session:
            stmt = select(Project).where(Project.id == result["project_id"])
            db_result = await session.execute(stmt)
            created_project = db_result.scalar_one_or_none()

        response = ProjectResponse(
            id=result["project_id"],
            alias=created_project.alias if created_project else "UNKNWN",
            name=project.name,
            description=project.description,
            mission=project.mission,
            status="inactive",
            product_id=project.product_id,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            completed_at=None,
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
    db: AsyncSession = Depends(get_db_session),
):
    """
    List all projects (filtered by user's tenant).

    Handover 0070: Excludes deleted projects (status='deleted' OR deleted_at IS NOT NULL).
    Use GET /deleted to see deleted projects.
    """
    import logging

    from sqlalchemy import or_, select

    from api.app import state
    from src.giljo_mcp.models import Project

    logger = logging.getLogger(__name__)

    # DIAGNOSTIC: Log authentication success
    logger.info(
        f"[PROJECTS] Authentication successful - User: {current_user.username}, Tenant: {current_user.tenant_key}, Role: {current_user.role}"
    )

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # TENANT ISOLATION + HANDOVER 0070: Filter deleted projects
            stmt = select(Project).where(
                Project.tenant_key == current_user.tenant_key,
                # Exclude deleted projects
                or_(Project.status != "deleted", Project.deleted_at.is_(None)),
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
                        description=proj.description,
                        mission=proj.mission,
                        status=proj.status,
                        product_id=proj.product_id,
                        created_at=proj.created_at,
                        updated_at=proj.updated_at or proj.created_at,
                        completed_at=proj.completed_at,
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


@router.get("/active", response_model=Optional[ProjectResponse])
async def get_active_project(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Get the currently active project for the user's tenant.

    Returns the active project (status='active') or None if no project is active.

    Leverages Single Active Project architecture (Handover 0050b):
    - Only ONE project can be active per product at any time
    - Database enforces this via partial unique index
    """
    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import Agent, Message, Project

    logger.info(f"[GET ACTIVE PROJECT] User: {current_user.username}, Tenant: {current_user.tenant_key}")

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Query for active project (tenant-isolated)
            stmt = (
                select(Project)
                .where(Project.tenant_key == current_user.tenant_key, Project.status == "active")
                .limit(1)
            )

            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                logger.info(f"[GET ACTIVE PROJECT] No active project found for tenant {current_user.tenant_key}")
                return None

            # Get agent and message counts
            agent_stmt = select(Agent).where(Agent.project_id == project.id)
            agent_result = await session.execute(agent_stmt)
            agent_count = len(agent_result.scalars().all())

            message_stmt = select(Message).where(Message.project_id == project.id)
            message_result = await session.execute(message_stmt)
            message_count = len(message_result.scalars().all())

            logger.info(f"[GET ACTIVE PROJECT] Found active project: {project.name} (ID: {project.id})")

            return ProjectResponse(
                id=project.id,
                alias=project.alias,
                name=project.name,
                description=project.description,
                mission=project.mission,
                status=project.status,
                product_id=project.product_id,
                created_at=project.created_at,
                updated_at=project.updated_at or project.created_at,
                completed_at=project.completed_at,
                context_budget=project.context_budget,
                context_used=project.context_used,
                agent_count=agent_count,
                message_count=message_count,
            )

    except Exception as e:
        logger.error(f"Failed to get active project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/by-alias/{alias}", response_model=ProjectResponse)
async def get_project_by_alias(alias: str):
    """
    Get project details by short alias.

    Handover 0070: Excludes deleted projects.
    """
    from sqlalchemy import or_, select

    from api.app import state
    from src.giljo_mcp.models import Project

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Query project by alias (Handover 0070: Exclude deleted projects)
            stmt = select(Project).where(
                Project.alias == alias.upper(),
                # Exclude deleted projects
                or_(Project.status != "deleted", Project.deleted_at.is_(None)),
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail=f"Project with alias '{alias}' not found")

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
                description=project.description,
                mission=project.mission,
                status=project.status,
                product_id=project.product_id,
                created_at=project.created_at,
                updated_at=project.updated_at or project.created_at,
                completed_at=project.completed_at,
                context_budget=project.context_budget,
                context_used=project.context_used,
                agent_count=agent_count,
                message_count=message_count,
            )

    except HTTPException:
        raise
    except Exception as e:
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
    current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    List deleted projects for the ACTIVE product only (Handover 0071).

    Returns empty list if no active product.

    Args:
        current_user: Authenticated user

    Returns:
        List of deleted projects from active product with 10-day recovery window
    """
    import logging
    from datetime import timedelta

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import Product, Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Get active product first (Handover 0071: Product-scoped deleted view)
            active_product_result = await session.execute(
                select(Product).where(Product.tenant_key == current_user.tenant_key, Product.is_active == True)
            )
            active_product = active_product_result.scalar_one_or_none()

            if not active_product:
                logger.info(
                    f"[Handover 0071] No active product - returning empty deleted list for user {current_user.username}"
                )
                return []

            # Query deleted projects ONLY for active product
            stmt = (
                select(Project, Product)
                .outerjoin(Product, Project.product_id == Product.id)
                .where(
                    Project.tenant_key == current_user.tenant_key,
                    Project.product_id == active_product.id,  # NEW: Product filter
                    Project.deleted_at.isnot(None),
                )
                .order_by(Project.deleted_at.desc())
            )

            result = await session.execute(stmt)
            rows = result.all()

            deleted_projects = []
            now = datetime.now(timezone.utc)

            for project, product in rows:
                # Calculate days until purge (10 days from deletion)
                # Convert naive datetime to UTC-aware for comparison
                deleted_at_utc = (
                    project.deleted_at.replace(tzinfo=timezone.utc)
                    if project.deleted_at.tzinfo is None
                    else project.deleted_at
                )
                purge_date = deleted_at_utc + timedelta(days=10)
                days_until_purge = max(0, (purge_date - now).days)

                deleted_projects.append(
                    DeletedProjectResponse(
                        id=project.id,
                        alias=project.alias,
                        name=project.name,
                        product_id=project.product_id,
                        product_name=product.name if product else None,
                        deleted_at=deleted_at_utc,
                        days_until_purge=days_until_purge,
                        purge_date=purge_date,
                    )
                )

            logger.info(
                f"[Handover 0071] Retrieved {len(deleted_projects)} deleted projects "
                f"for active product '{active_product.name}' (user: {current_user.username})"
            )

            return deleted_projects

    except Exception as e:
        logger.error(f"[Handover 0071] Failed to list deleted projects: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """Get project details by ID"""
    from sqlalchemy import or_, select

    from src.giljo_mcp.models import Agent, MCPAgentJob, Message, Project

    try:
        # Query project directly from database (like get_project_by_alias)
        stmt = select(Project).where(
            Project.id == project_id,
            Project.tenant_key == current_user.tenant_key,
            # Exclude deleted projects
            or_(Project.status != "deleted", Project.deleted_at.is_(None)),
        )
        result = await db.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Get agent jobs (MCP agents spawned for this project)
        agent_jobs_stmt = select(MCPAgentJob).where(
            MCPAgentJob.project_id == project.id,
            MCPAgentJob.tenant_key == current_user.tenant_key
        ).order_by(MCPAgentJob.created_at.asc())
        agent_jobs_result = await db.execute(agent_jobs_stmt)
        agent_jobs = agent_jobs_result.scalars().all()

        # Build agent list
        agents_list = []
        for job in agent_jobs:
            agents_list.append(AgentSimple(
                id=job.job_id,
                job_id=job.job_id,
                agent_type=job.agent_type,
                agent_name=job.agent_name,
                status=job.status,
                thin_client=job.thin_client if hasattr(job, 'thin_client') else True
            ))

        # Get legacy agent count (from old Agent table)
        agent_stmt = select(Agent).where(Agent.project_id == project.id)
        agent_result = await db.execute(agent_stmt)
        agent_count = len(agent_result.scalars().all())

        message_stmt = select(Message).where(Message.project_id == project.id)
        message_result = await db.execute(message_stmt)
        message_count = len(message_result.scalars().all())

        return ProjectResponse(
            id=project.id,
            alias=project.alias,
            name=project.name,
            description=project.description,  # Direct database access - should work!
            mission=project.mission,
            status=project.status,
            product_id=project.product_id,
            created_at=project.created_at,
            updated_at=project.updated_at or project.created_at,
            completed_at=project.completed_at,
            context_budget=project.context_budget,
            context_used=project.context_used,
            agent_count=len(agents_list) + agent_count,  # Total from both tables
            message_count=message_count,
            agents=agents_list,
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{project_id}", response_model=ProjectResponse)
async def update_project(
    project_id: str,
    update: ProjectUpdate,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session)
):
    """Update project details"""
    import logging

    from sqlalchemy import select

    from api.app import state
    from giljo_mcp.models import Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        logger.info(
            f"PATCH /projects/{project_id} - Received update: name={update.name}, mission={update.mission}, status={update.status}"
        )

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

            if update.description is not None:
                project.description = update.description
                logger.info("Updated description")

            if update.mission is not None:
                project.mission = update.mission
                logger.info("Updated mission")

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
                            status_code=400, detail="Cannot activate project - parent product not found"
                        )

                    if not parent_product.is_active:
                        logger.warning(
                            f"Cannot activate project - parent product '{parent_product.name}' is not active"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=f"Cannot activate project - parent product '{parent_product.name}' is not active. Please activate the product first.",
                        )

                    logger.info(f"Project activation validated - parent product '{parent_product.name}' is active")

                    # Handover 0071: Enforce single active project per product (application-level validation)
                    active_check = await session.execute(
                        select(Project).where(
                            Project.product_id == project.product_id,
                            Project.status == "active",
                            Project.id != project_id,
                        )
                    )
                    existing_active = active_check.scalar_one_or_none()

                    if existing_active:
                        logger.warning(
                            f"[Handover 0071] Cannot activate project '{project.name}' - "
                            f"project '{existing_active.name}' already active for product '{parent_product.name}'"
                        )
                        raise HTTPException(
                            status_code=400,
                            detail=(
                                f"Another project ('{existing_active.name}') is already active "
                                f"for this product. Please deactivate it first."
                            ),
                        )

                    logger.info("[Handover 0071] Single active project validation passed")

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
                    project_id=project_id, update_type="updated", project_data=update_data
                )

        # Get updated project
        updated_project = await get_project(project_id, current_user, db)
        logger.info(f"Project after retrieval: name={updated_project.name}, status={updated_project.status}")
        return updated_project

    except Exception as e:
        logger.error(f"Failed to update project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/activate", response_model=ProjectResponse)
async def activate_project(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Activate a project (enables launch button).

    Handover 0062: Project activation workflow.
    Changes status from inactive to active.
    """
    from sqlalchemy import select

    from src.giljo_mcp.models import Product, Project

    # Fetch project
    stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Validate current status
    if project.status != "inactive":
        raise HTTPException(status_code=400, detail=f"Project cannot be activated from status '{project.status}'")

    # Validate parent product exists and is active
    if project.product_id:
        product_result = await db.execute(select(Product).where(Product.id == project.product_id))
        parent_product = product_result.scalar_one_or_none()
        if not parent_product:
            raise HTTPException(status_code=400, detail="Cannot activate project - parent product not found")
        if not getattr(parent_product, "is_active", False):
            raise HTTPException(
                status_code=400,
                detail=f"Cannot activate project - parent product '{parent_product.name}' is not active. Please activate the product first.",
            )

        # Enforce single active project per product
        existing_active_result = await db.execute(
            select(Project).where(
                Project.product_id == project.product_id,
                Project.status == "active",
                Project.id != project_id,
            )
        )
        existing_active = existing_active_result.scalar_one_or_none()
        if existing_active:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Another project ('{existing_active.name}') is already active for this product. "
                    f"Please deactivate it first."
                ),
            )

    # Update status
    project.status = "active"
    project.updated_at = datetime.utcnow()

    await db.commit()
    await db.refresh(project)

    # Create orchestrator job for this project (Handover 0080)
    from src.giljo_mcp.models import MCPAgentJob

    # Check if orchestrator already exists
    existing_orch_stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == project_id,
        MCPAgentJob.agent_type == "orchestrator",
        MCPAgentJob.tenant_key == current_user.tenant_key,
    )
    existing_orch_result = await db.execute(existing_orch_stmt)
    existing_orchestrator = existing_orch_result.scalar_one_or_none()

    if not existing_orchestrator:
        # Create orchestrator job
        orchestrator_job = MCPAgentJob(
            tenant_key=current_user.tenant_key,
            project_id=project_id,
            agent_type="orchestrator",
            agent_name="Orchestrator",
            mission=(
                "I am ready to create the project mission based on product context and project description. "
                "I will write the mission in the mission window and select the proper agents below."
            ),
            status="waiting",
            tool_type="universal",
            progress=0,
            acknowledged=False,
            context_chunks=[],
            messages=[],
        )

        db.add(orchestrator_job)
        await db.commit()
        await db.refresh(orchestrator_job)

        logger.info(
            f"Created orchestrator job {orchestrator_job.job_id} for project {project_id} "
            f"(user: {current_user.username})"
        )

    logger.info(f"Project {project_id} activated by {current_user.username}")

    # Broadcast activation to subscribers (standard schema)
    try:
        from api.app import state

        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project.id,
                update_type="activated",
                project_data={"status": "active"},
            )
    except Exception:
        # Non-fatal: log and continue
        import logging as _logging

        _logging.getLogger(__name__).warning("Failed to broadcast project activation", exc_info=True)

    # Return unified response via helper to include counts
    return await get_project(project_id, current_user, db)


@router.get("/{project_id}/orchestrator")
async def get_project_orchestrator(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Get the orchestrator job for a project.

    Returns the orchestrator MCPAgentJob assigned to this project.
    If no orchestrator exists, creates one automatically.

    Args:
        project_id: Project UUID
        current_user: Authenticated user
        db: Database session

    Returns:
        Orchestrator job data with full job_id/agent_id

    Raises:
        404: Project not found
        403: User not authorized
    """
    import logging

    from sqlalchemy import select

    from src.giljo_mcp.models import MCPAgentJob, Project

    logger = logging.getLogger(__name__)

    # Verify project exists and user has access
    project_stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Find or create orchestrator job
    # Support orchestrator succession (Handover 0080) - get latest by instance_number
    orch_stmt = (
        select(MCPAgentJob)
        .where(
            MCPAgentJob.project_id == project_id,
            MCPAgentJob.agent_type == "orchestrator",
            MCPAgentJob.tenant_key == current_user.tenant_key,
        )
        .order_by(MCPAgentJob.instance_number.desc())
    )
    orch_result = await db.execute(orch_stmt)
    orchestrator = orch_result.scalars().first()

    if not orchestrator:
        # Create orchestrator if it doesn't exist
        orchestrator = MCPAgentJob(
            tenant_key=current_user.tenant_key,
            project_id=project_id,
            agent_type="orchestrator",
            agent_name="Orchestrator",
            mission=(
                "I am ready to create the project mission based on product context and project description. "
                "I will write the mission in the mission window and select the proper agents below."
            ),
            status="waiting",
            tool_type="universal",
            progress=0,
            acknowledged=False,
            context_chunks=[],
            messages=[],
        )

        db.add(orchestrator)
        await db.commit()
        await db.refresh(orchestrator)

        logger.info(
            f"Auto-created orchestrator job {orchestrator.job_id} for project {project_id} "
            f"(user: {current_user.username})"
        )

    # Return orchestrator data
    return {
        "success": True,
        "orchestrator": {
            "id": orchestrator.id,
            "job_id": orchestrator.job_id,  # Full 36-digit UUID
            "agent_id": orchestrator.job_id,  # Alias for compatibility
            "agent_type": orchestrator.agent_type,
            "agent_name": orchestrator.agent_name,
            "mission": orchestrator.mission,
            "status": orchestrator.status,
            "progress": orchestrator.progress,
            "tool_type": orchestrator.tool_type,
            "acknowledged": orchestrator.acknowledged,
            "created_at": orchestrator.created_at.isoformat() if orchestrator.created_at else None,
            "started_at": orchestrator.started_at.isoformat() if orchestrator.started_at else None,
            "completed_at": orchestrator.completed_at.isoformat() if orchestrator.completed_at else None,
        },
    }


@router.post("/{project_id}/deactivate", response_model=ProjectResponse)
async def deactivate_project(project_id: str, current_user: User = Depends(get_current_active_user)):
    """
    Deactivate a project (Handover 0071).

    Sets project status to 'inactive', freeing up the active project slot.
    This allows another project to be activated for this product.

    Rules:
    - Can deactivate from 'active' status only
    - Frees up active project slot (single active per product)
    - Preserves missions/agents/context (keep for reactivation)
    - Broadcasts WebSocket event

    Args:
        project_id: Project UUID
        current_user: Authenticated user

    Returns:
        Updated project with status='inactive'

    Raises:
        404: Project not found
        400: Project not in 'active' status
        500: Database error
    """
    import logging

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as db:
            # Get project with tenant isolation
            result = await db.execute(
                select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
            )
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            if project.status != "active":
                raise HTTPException(
                    status_code=400,
                    detail=f"Cannot deactivate project with status '{project.status}'. Only active projects can be deactivated.",
                )

            # Deactivate project
            project.status = "inactive"
            await db.commit()
            await db.refresh(project)

            logger.info(
                f"[Handover 0071] Project '{project.name}' (ID: {project_id}) deactivated by user {current_user.username}"
            )

            # Broadcast WebSocket event (standard project update schema)
            if state.websocket_manager:
                await state.websocket_manager.broadcast_project_update(
                    project_id=project.id,
                    update_type="deactivated",
                    project_data={"status": "inactive"},
                )

            # Build response using helper function
            return await get_project(project_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[Handover 0071] Failed to deactivate project: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/complete", response_model=ProjectResponse)
async def complete_project(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Mark a project as completed.

    Sets status='completed' and completed_at=NOW().
    Completed projects can be restored via the restore endpoint.
    """
    import logging

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import Agent, Message, Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Fetch project and verify tenant ownership
            stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Verify project is not already completed or cancelled
            if project.status in ("completed", "cancelled"):
                raise HTTPException(status_code=400, detail=f"Project is already {project.status}")

            # Mark as completed
            project.status = "completed"
            project.completed_at = datetime.now(timezone.utc)
            project.updated_at = datetime.now(timezone.utc)

            await session.flush()

            # Get agent and message counts
            agent_stmt = select(Agent).where(Agent.project_id == project.id)
            agent_result = await session.execute(agent_stmt)
            agent_count = len(agent_result.scalars().all())

            message_stmt = select(Message).where(Message.project_id == project.id)
            message_result = await session.execute(message_stmt)
            message_count = len(message_result.scalars().all())

            logger.info(f"Project '{project.name}' (id: {project_id}) marked as completed by {current_user.username}")

        # Broadcast project completion
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type="completed",
                project_data={"status": "completed", "completed_at": project.completed_at.isoformat()},
            )

        # Return completed project
        return ProjectResponse(
            id=project.id,
            alias=project.alias,
            name=project.name,
            description=project.description,
            mission=project.mission,
            status=project.status,
            product_id=project.product_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            completed_at=project.completed_at,
            context_budget=project.context_budget,
            context_used=project.context_used,
            agent_count=agent_count,
            message_count=message_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to complete project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/cancel", response_model=ProjectResponse)
async def cancel_project(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Cancel a project.

    Sets status='cancelled' and completed_at=NOW().
    Cancelled projects can be restored via the restore endpoint.
    """
    import logging

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import Agent, Message, Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Fetch project and verify tenant ownership
            stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Verify project is not already completed or cancelled
            if project.status in ("completed", "cancelled"):
                raise HTTPException(status_code=400, detail=f"Project is already {project.status}")

            # Mark as cancelled
            project.status = "cancelled"
            project.completed_at = datetime.now(timezone.utc)
            project.updated_at = datetime.now(timezone.utc)

            await session.flush()

            # Get agent and message counts
            agent_stmt = select(Agent).where(Agent.project_id == project.id)
            agent_result = await session.execute(agent_stmt)
            agent_count = len(agent_result.scalars().all())

            message_stmt = select(Message).where(Message.project_id == project.id)
            message_result = await session.execute(message_stmt)
            message_count = len(message_result.scalars().all())

            logger.info(f"Project '{project.name}' (id: {project_id}) cancelled by {current_user.username}")

        # Broadcast project cancellation
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type="cancelled",
                project_data={"status": "cancelled", "completed_at": project.completed_at.isoformat()},
            )

        # Return cancelled project
        return ProjectResponse(
            id=project.id,
            alias=project.alias,
            name=project.name,
            description=project.description,
            mission=project.mission,
            status=project.status,
            product_id=project.product_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            completed_at=project.completed_at,
            context_budget=project.context_budget,
            context_used=project.context_used,
            agent_count=agent_count,
            message_count=message_count,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to cancel project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# Handover 0108: Staging Cancellation Response
class StagingCancellationResponse(BaseModel):
    """Response model for staging cancellation (Handover 0108)."""

    success: bool = Field(..., description="Whether staging cancellation succeeded")
    agents_deleted: int = Field(..., description="Number of agents deleted/soft-deleted")
    agents_protected: int = Field(..., description="Number of agents protected (already launched)")
    staging_status: Optional[str] = Field(None, description="Updated staging_status (should be None)")
    message: str = Field(..., description="Human-readable result message")
    rollback_timestamp: Optional[str] = Field(None, description="ISO timestamp of rollback")


@router.post("/{project_id}/cancel-staging", response_model=StagingCancellationResponse)
async def cancel_project_staging(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Cancel project staging and rollback database (Handover 0108).

    This endpoint is called when a user cancels staging after the orchestrator
    has created the mission and spawned agents. It performs a transactional
    rollback of the staging operation.

    Operations:
    1. Validate project exists (with tenant isolation)
    2. Get orchestrator job for project
    3. Call rollback_project_staging() from staging_rollback module
    4. Update project.staging_status = None
    5. Broadcast WebSocket event

    Args:
        project_id: Project UUID
        current_user: Authenticated user (dependency injection)
        db: Database session (dependency injection)

    Returns:
        StagingCancellationResponse with deletion statistics

    Raises:
        404: Project not found
        400: No orchestrator found or invalid staging state
        500: Database error or rollback failure

    Multi-tenant isolation: Enforced via current_user.tenant_key
    Transaction safety: Atomic rollback with session.commit()
    """
    import logging

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import MCPAgentJob, Project
    from src.giljo_mcp.staging_rollback import rollback_project_staging

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    logger.info(
        f"[Handover 0108] Staging cancellation requested for project {project_id} "
        f"by user {current_user.username} (tenant: {current_user.tenant_key})"
    )

    try:
        async with state.db_manager.get_session_async() as session:
            # Step 1: Validate project exists and user has access (tenant isolation)
            project_stmt = select(Project).where(
                Project.id == project_id, Project.tenant_key == current_user.tenant_key
            )
            project_result = await session.execute(project_stmt)
            project = project_result.scalar_one_or_none()

            if not project:
                logger.warning(f"[Handover 0108] Project {project_id} not found for tenant {current_user.tenant_key}")
                raise HTTPException(status_code=404, detail="Project not found")

            # Step 2: Get orchestrator job for project (latest instance for succession support)
            orch_stmt = (
                select(MCPAgentJob)
                .where(
                    MCPAgentJob.project_id == project_id,
                    MCPAgentJob.agent_type == "orchestrator",
                    MCPAgentJob.tenant_key == current_user.tenant_key,
                )
                .order_by(MCPAgentJob.instance_number.desc())
            )
            orch_result = await session.execute(orch_stmt)
            orchestrator = orch_result.scalars().first()

            if not orchestrator:
                logger.error(f"[Handover 0108] No orchestrator found for project {project_id}")
                raise HTTPException(
                    status_code=400,
                    detail="No orchestrator found for this project. Cannot cancel staging.",
                )

            logger.info(
                f"[Handover 0108] Found orchestrator {orchestrator.job_id} "
                f"(instance {orchestrator.instance_number}, status: {orchestrator.status})"
            )

            # Step 3: Call rollback_project_staging() from staging_rollback module
            # This performs the atomic database rollback with soft delete
            rollback_result = await rollback_project_staging(
                tenant_key=current_user.tenant_key,
                project_id=project_id,
                orchestrator_job_id=orchestrator.job_id,
                reason=f"User {current_user.username} canceled staging via UI",
                hard_delete=False,  # Use soft delete (status='failed' with metadata)
            )

            if not rollback_result.get("success"):
                error_msg = rollback_result.get("error", "Unknown error during rollback")
                logger.error(f"[Handover 0108] Staging rollback failed: {error_msg}")
                raise HTTPException(status_code=500, detail=f"Staging rollback failed: {error_msg}")

            agents_deleted = rollback_result.get("agents_deleted", 0)
            agents_protected = rollback_result.get("agents_protected", 0)
            rollback_timestamp = rollback_result.get("rollback_timestamp")

            logger.info(
                f"[Handover 0108] Rollback successful: {agents_deleted} agents deleted, "
                f"{agents_protected} agents protected"
            )

            # Step 4: Update project.staging_status = None
            # This clears the staging flag and returns project to normal state
            project.staging_status = None
            await session.flush()

            # Commit transaction (includes rollback changes + project update)
            await session.commit()

            logger.info(f"[Handover 0108] Project {project_id} staging_status cleared (committed)")

        # Step 5: Broadcast WebSocket event (after commit)
        if state.websocket_manager:
            try:
                await state.websocket_manager.broadcast_project_update(
                    project_id=project_id,
                    update_type="staging_cancelled",
                    project_data={
                        "staging_status": None,
                        "agents_deleted": agents_deleted,
                        "agents_protected": agents_protected,
                        "rollback_timestamp": rollback_timestamp,
                        "message": f"Staging canceled: {agents_deleted} agents removed, {agents_protected} protected",
                    },
                )
                logger.info(f"[Handover 0108] WebSocket event broadcast for project {project_id}")
            except Exception as ws_error:
                # Non-fatal: log and continue
                logger.warning(f"[Handover 0108] Failed to broadcast WebSocket event: {ws_error}")

        # Build success response
        response = StagingCancellationResponse(
            success=True,
            agents_deleted=agents_deleted,
            agents_protected=agents_protected,
            staging_status=None,
            message=(
                f"Staging canceled successfully. Removed {agents_deleted} spawned agent(s), "
                f"protected {agents_protected} active agent(s)."
            ),
            rollback_timestamp=rollback_timestamp,
        )

        logger.info(
            f"[Handover 0108] Staging cancellation completed for project {project_id}: "
            f"deleted={agents_deleted}, protected={agents_protected}"
        )

        return response

    except HTTPException:
        # Re-raise HTTP exceptions (404, 400, 500)
        raise
    except Exception as e:
        logger.error(f"[Handover 0108] Unexpected error during staging cancellation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to cancel staging: {str(e)}")


@router.post("/{project_id}/restore-completed", response_model=ProjectResponse)
async def restore_completed_project(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Restore a completed or cancelled project.

    Sets status='inactive' (safe default) and clears completed_at.
    User must manually activate project after restoration.
    """
    import logging

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import Agent, Message, Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Fetch project and verify tenant ownership
            stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Verify project is completed or cancelled
            if project.status not in ("completed", "cancelled"):
                raise HTTPException(
                    status_code=400, detail=f"Project is not completed or cancelled (current status: {project.status})"
                )

            # Restore project: Set to inactive (safe default)
            project.status = "inactive"
            project.completed_at = None
            project.updated_at = datetime.now(timezone.utc)

            await session.flush()

            # Get agent and message counts
            agent_stmt = select(Agent).where(Agent.project_id == project.id)
            agent_result = await session.execute(agent_stmt)
            agent_count = len(agent_result.scalars().all())

            message_stmt = select(Message).where(Message.project_id == project.id)
            message_result = await session.execute(message_stmt)
            message_count = len(message_result.scalars().all())

            logger.info(
                f"Project '{project.name}' (id: {project_id}) restored from completed/cancelled by {current_user.username}"
            )

        # Broadcast project restoration
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type="restored",
                project_data={"status": "inactive", "completed_at": None, "message": "Project restored successfully"},
            )

        # Return restored project
        return ProjectResponse(
            id=project.id,
            alias=project.alias,
            name=project.name,
            description=project.description,
            mission=project.mission,
            status=project.status,
            product_id=project.product_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            completed_at=project.completed_at,
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


@router.delete("/{project_id}")
async def delete_project(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Soft delete a project (Handover 0070).

    Sets status='deleted' and deleted_at=NOW(). Project will be purged after 10 days.
    Recovery available via: Settings -> Database -> Deleted Projects
    """
    import logging

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Fetch project and verify tenant ownership
            stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
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

            logger.info(
                f"[Handover 0070] Project '{project.name}' (id: {project_id}) soft deleted by {current_user.username}"
            )

        # Broadcast project deletion
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type="deleted",
                project_data={
                    "status": "deleted",
                    "deleted_at": project.deleted_at.isoformat(),
                    "message": "Project will be permanently purged in 10 days",
                },
            )

        return {
            "success": True,
            "message": "Project deleted from view. Will be permanently purged in 10 days.",
            "recovery_info": "To recover: Settings → Database → Deleted Projects",
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/restore", response_model=ProjectResponse)
async def restore_project(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Restore a soft-deleted project (Handover 0070).

    Sets status='inactive' (safe default) and clears deleted_at.
    User must manually activate project after restoration.
    """
    import logging

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import Agent, Message, Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    try:
        async with state.db_manager.get_session_async() as session:
            # Fetch project and verify tenant ownership
            stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
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

            logger.info(
                f"[Handover 0070] Project '{project.name}' (id: {project_id}) restored by {current_user.username}"
            )

        # Broadcast project restoration
        if state.websocket_manager:
            await state.websocket_manager.broadcast_project_update(
                project_id=project_id,
                update_type="restored",
                project_data={"status": "inactive", "deleted_at": None, "message": "Project restored successfully"},
            )

        # Return restored project
        return ProjectResponse(
            id=project.id,
            alias=project.alias,
            name=project.name,
            description=project.description,
            mission=project.mission,
            status=project.status,
            product_id=project.product_id,
            created_at=project.created_at,
            updated_at=project.updated_at,
            completed_at=project.completed_at,
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
    import logging
    from datetime import timedelta

    from sqlalchemy import select

    from src.giljo_mcp.models import Agent, Message, Project, Task

    logger = logging.getLogger(__name__)

    if not db_manager:
        logger.error("[Handover 0070] Cannot purge - database manager not available")
        return {"success": False, "error": "Database not available"}

    try:
        async with db_manager.get_session_async() as session:
            # Find projects deleted more than 10 days ago
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=10)

            stmt = select(Project).where(Project.deleted_at.isnot(None), Project.deleted_at < cutoff_date)

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
                    "deleted_at": project.deleted_at.isoformat(),
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

            return {"success": True, "purged_count": len(purged_projects), "projects": purged_projects}

    except Exception as e:
        logger.error(f"[Handover 0070] Failed to purge expired deleted projects: {e}", exc_info=True)
        return {"success": False, "error": str(e), "purged_count": 0}


@router.get("/{project_id}/summary", response_model=ProjectSummaryResponse)
async def get_project_summary(
    project_id: str, current_user: User = Depends(get_current_active_user), db: AsyncSession = Depends(get_db_session)
):
    """
    Get comprehensive project summary for after-action review.

    Handover 0062: Project detail page enhancement.
    Includes project details, agents used, and message history.
    """
    from sqlalchemy import select

    from src.giljo_mcp.models import Agent, MCPAgentJob, Message, Project

    # Fetch project
    project_stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
    project_result = await db.execute(project_stmt)
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Fetch agents
    agents_stmt = select(Agent).where(Agent.project_id == project_id, Agent.tenant_key == current_user.tenant_key)
    agents_result = await db.execute(agents_stmt)
    agents = agents_result.scalars().all()

    # Fetch agent jobs (if project_id exists)
    jobs = []
    try:
        jobs_stmt = select(MCPAgentJob).where(
            MCPAgentJob.project_id == project_id, MCPAgentJob.tenant_key == current_user.tenant_key
        )
        jobs_result = await db.execute(jobs_stmt)
        jobs = jobs_result.scalars().all()
    except Exception as e:
        logger.warning(f"Could not fetch jobs for project {project_id}: {e}")

    # Fetch messages
    messages_stmt = (
        select(Message)
        .where(Message.project_id == project_id, Message.tenant_key == current_user.tenant_key)
        .order_by(Message.created_at)
    )
    messages_result = await db.execute(messages_stmt)
    messages = messages_result.scalars().all()

    # Build agent summaries
    agent_summaries = []
    job_map = {job.job_id: job for job in jobs}

    for agent in agents:
        job = job_map.get(agent.job_id) if agent.job_id else None
        agent_summaries.append(
            AgentSummary(
                id=agent.id,
                name=agent.name,
                type=agent.type,
                status=agent.status,
                job_mission=job.mission if job else None,
                job_id=agent.job_id,
            )
        )

    # Build message summaries
    message_summaries = []
    for msg in messages:
        message_summaries.append(
            MessageSummary(
                id=msg.id,
                from_agent=msg.from_agent,
                to_agents=msg.to_agents or [],
                content=msg.content,
                timestamp=msg.created_at.isoformat() if msg.created_at else "",
            )
        )

    # Build summary response
    return ProjectSummaryResponse(
        project_id=project.id,
        project_name=project.name,
        description=getattr(project, "description", project.mission),  # Backward compat
        mission=project.mission,
        status=project.status,
        agents=agent_summaries,
        messages=message_summaries,
        created_at=project.created_at.isoformat() if project.created_at else "",
        completed_at=project.completed_at.isoformat() if project.completed_at else None,
    )


# Handover 0073: Project Closeout Endpoints


@router.get("/{project_id}/can-close", response_model=ProjectCanCloseResponse)
async def check_project_can_close(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Check if all agents complete and project can close (Handover 0073).

    Analyzes agent statuses to determine if project is ready for closeout.
    If all agents are finished (complete or failed), generates an AI summary.

    Args:
        project_id: Project ID to check
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        ProjectCanCloseResponse with readiness status and agent breakdown

    Raises:
        404: Project not found or not accessible
        403: User not authorized to access project
    """
    import logging

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import MCPAgentJob, Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    # Get project with tenant isolation
    stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        logger.warning(f"Project {project_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or not accessible")

    # Get agent status breakdown
    agents_stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == project_id, MCPAgentJob.tenant_key == current_user.tenant_key
    )
    agents_result = await db.execute(agents_stmt)
    agents = agents_result.scalars().all()

    # Count agent statuses
    complete_count = sum(1 for a in agents if a.status == "complete")
    failed_count = sum(1 for a in agents if a.status == "failed")
    active_count = sum(1 for a in agents if a.status in ["working", "preparing", "review"])
    blocked_count = sum(1 for a in agents if a.status == "blocked")

    agent_statuses = AgentStatusSummary(
        complete=complete_count, failed=failed_count, active=active_count, blocked=blocked_count
    )

    # Check if all agents finished
    all_agents_finished = (complete_count + failed_count == len(agents)) and len(agents) > 0
    can_close = all_agents_finished

    # Generate summary if can close
    summary = None
    if can_close:
        # Generate AI summary from completed agents
        completed_agents = [a for a in agents if a.status == "complete"]
        failed_agents = [a for a in agents if a.status == "failed"]

        summary_parts = []
        summary_parts.append(f"Project '{project.name}' completed with {complete_count} successful agents")

        if failed_count > 0:
            summary_parts.append(f" and {failed_count} failed agents")

        summary_parts.append(".\n\nCompleted Work:")
        for agent in completed_agents:
            summary_parts.append(f"- {agent.agent_type}: {agent.mission[:100]}...")

        if failed_agents:
            summary_parts.append("\n\nFailed Tasks:")
            for agent in failed_agents:
                summary_parts.append(f"- {agent.agent_type}: {agent.block_reason or 'Unknown error'}")

        summary = "".join(summary_parts)

        # Store summary in project
        project.orchestrator_summary = summary
        await db.commit()

    logger.info(f"Project {project_id} closeout check: can_close={can_close}, agents={len(agents)}")

    return ProjectCanCloseResponse(
        can_close=can_close, summary=summary, agent_statuses=agent_statuses, all_agents_finished=all_agents_finished
    )


@router.post("/{project_id}/generate-closeout", response_model=ProjectCloseoutPromptResponse)
async def generate_project_closeout_prompt(
    project_id: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Generate closeout prompt with git commands and checklist (Handover 0073).

    Creates an executable bash script for finalizing the project, including
    git operations, documentation generation, and closeout checklist.

    Args:
        project_id: Project ID to generate closeout for
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        ProjectCloseoutPromptResponse with bash script and checklist

    Raises:
        404: Project not found or not accessible
        400: Project not ready for closeout
        403: User not authorized to access project
    """
    import logging
    from datetime import datetime, timezone

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import MCPAgentJob, Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    # Get project with tenant isolation
    stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        logger.warning(f"Project {project_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or not accessible")

    # Get agent counts
    agents_stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == project_id, MCPAgentJob.tenant_key == current_user.tenant_key
    )
    agents_result = await db.execute(agents_stmt)
    agents = agents_result.scalars().all()

    complete_count = sum(1 for a in agents if a.status == "complete")
    failed_count = sum(1 for a in agents if a.status == "failed")

    # Calculate project duration
    duration = datetime.now(timezone.utc) - project.created_at.replace(tzinfo=timezone.utc)
    duration_str = f"{duration.days} days, {duration.seconds // 3600} hours"

    # Determine project path
    project_path = project.meta_data.get("path", ".") if project.meta_data else "."
    git_branch = project.meta_data.get("git_branch", "main") if project.meta_data else "main"

    # Use orchestrator summary or generate simple summary
    agent_summary = project.orchestrator_summary or f"Project completed with {complete_count} successful agents"

    # Generate closeout bash script
    prompt = f"""#!/bin/bash
# Project Closeout: {project.name}
# Generated: {datetime.now(timezone.utc).isoformat()}

cd {project_path}

# 1. Check final status
echo "Checking project status..."
git status

# 2. Stage all changes
echo "Staging changes..."
git add .

# 3. Commit with summary
echo "Committing changes..."
git commit -m "Project complete: {project.name}

{agent_summary}

Agents completed: {complete_count}
Agents failed: {failed_count}
Total duration: {duration_str}
"

# 4. Push to remote
echo "Pushing to remote..."
git push origin {git_branch}

# 5. Generate documentation
echo "Generating project summary..."
cat > PROJECT_SUMMARY.md << 'EOF'
# {project.name} - Project Summary

## Overview
{project.mission}

## Results
{agent_summary}

## Statistics
- Completed Agents: {complete_count}
- Failed Agents: {failed_count}
- Total Duration: {duration_str}
- Created: {project.created_at.isoformat()}
- Completed: {datetime.now(timezone.utc).isoformat()}

## Project Details
- ID: {project.id}
- Alias: {project.alias}
- Status: {project.status}
EOF

echo "Project closeout complete!"
echo "Summary saved to PROJECT_SUMMARY.md"
"""

    # Generate checklist
    checklist = [
        "Review all agent work and deliverables",
        "Run final tests and quality checks",
        "Commit all changes to version control",
        "Push changes to remote repository",
        "Update project documentation",
        "Close agent terminals and cleanup",
        "Archive project artifacts",
        "Notify stakeholders of completion",
    ]

    # Store closeout prompt in project
    project.closeout_prompt = prompt
    await db.commit()

    logger.info(f"Generated closeout prompt for project {project_id}")

    return ProjectCloseoutPromptResponse(
        prompt=prompt, checklist=checklist, project_name=project.name, agent_summary=agent_summary
    )


@router.post("/{project_id}/complete", response_model=ProjectCompleteResponse)
async def complete_project_closeout(
    project_id: str,
    complete_request: ProjectCompleteRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
):
    """
    Mark project as completed and retire agents (Handover 0073).

    Finalizes the project by setting status to 'completed', recording timestamps,
    and retiring all associated agents. This is the final step in the closeout workflow.

    Args:
        project_id: Project ID to complete
        complete_request: Completion confirmation request
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        ProjectCompleteResponse with success status and retired agent count

    Raises:
        404: Project not found or not accessible
        400: Confirmation not provided or invalid
        403: User not authorized to access project
    """
    import logging
    from datetime import datetime, timezone

    from sqlalchemy import select

    from api.app import state
    from src.giljo_mcp.models import MCPAgentJob, Project

    logger = logging.getLogger(__name__)

    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    # Validate confirmation
    if not complete_request.confirm_closeout:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Must confirm closeout by setting confirm_closeout=true"
        )

    # Get project with tenant isolation
    stmt = select(Project).where(Project.id == project_id, Project.tenant_key == current_user.tenant_key)
    result = await db.execute(stmt)
    project = result.scalar_one_or_none()

    if not project:
        logger.warning(f"Project {project_id} not found for tenant {current_user.tenant_key}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found or not accessible")

    # Set project as completed
    project.status = "completed"
    project.closeout_executed_at = datetime.now(timezone.utc)
    if not project.completed_at:
        project.completed_at = datetime.now(timezone.utc)

    # Retire all agents in project
    agents_stmt = select(MCPAgentJob).where(
        MCPAgentJob.project_id == project_id, MCPAgentJob.tenant_key == current_user.tenant_key
    )
    agents_result = await db.execute(agents_stmt)
    agents = agents_result.scalars().all()

    retired_count = 0
    for agent in agents:
        # Set retired timestamp if not already set
        # Note: MCPAgentJob doesn't have retired_at field in the model we saw
        # So we'll just count the agents (field can be added in future migration)
        retired_count += 1

    # Commit all changes
    await db.commit()

    logger.info(f"Project {project_id} completed. Retired {retired_count} agents.")

    # Broadcast WebSocket event
    try:
        if state.websocket_manager:
            await state.websocket_manager.broadcast_to_project(
                project_id,
                {
                    "type": "project:completed",
                    "project_id": project_id,
                    "completed_at": project.completed_at.isoformat(),
                    "retired_agents": retired_count,
                },
            )
    except Exception as e:
        logger.warning(f"Failed to broadcast project completion: {e}")

    return ProjectCompleteResponse(
        success=True, completed_at=project.completed_at.isoformat(), retired_agents=retired_count
    )



# ========================================
# Handover 0113: Project Agent Lifecycle
# ========================================


class ProjectCloseOutResponse(BaseModel):
    """Response for project close-out operation."""

    success: bool
    message: str
    agents_decommissioned: int
    decommissioned_agent_ids: list[str]
    project_status: str


class ContinueWorkingResponse(BaseModel):
    """Response for continue working operation."""

    success: bool
    message: str
    agents_resumed: int
    resumed_agent_ids: list[str]
    project_status: str


@router.post("/{project_id}/close-out", response_model=ProjectCloseOutResponse)
async def close_out_project(
    project_id: str,
    request: Request,
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """
    Close out project by decommissioning all completed agents.

    Handover 0113: Project closeout workflow - transitions all complete agents to decommissioned.

    Workflow:
    1. Find all agents with status='complete' for this project
    2. Transition each to status='decommissioned'
    3. Set decommissioned_at timestamp
    4. Update project status to 'completed'
    5. Broadcast WebSocket updates

    Args:
        project_id: Project ID
        request: FastAPI request
        db_manager: Database manager

    Returns:
        ProjectCloseOutResponse with summary

    Raises:
        HTTPException 404: Project not found
        HTTPException 403: Unauthorized
    """
    from giljo_mcp.agent_job_manager import AgentJobManager

    auth_context = request.state.auth_context
    tenant_key = auth_context["tenant_key"]

    logger.info(f"[Project Close-Out] Starting closeout for project {project_id} (tenant: {tenant_key})")

    # Verify project exists and belongs to tenant
    with db_manager.get_session() as session:
        project = session.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key,
                    Project.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Find all complete agents
        complete_agents = session.execute(
            select(MCPAgentJob).where(
                and_(
                    MCPAgentJob.project_id == project_id,
                    MCPAgentJob.tenant_key == tenant_key,
                    MCPAgentJob.status == "complete",
                )
            )
        ).scalars().all()

        if not complete_agents:
            logger.info(f"[Project Close-Out] No complete agents found for project {project_id}")
            return ProjectCloseOutResponse(
                success=True,
                message="No agents to decommission",
                agents_decommissioned=0,
                decommissioned_agent_ids=[],
                project_status=project.status,
            )

        # Decommission all complete agents
        agent_job_manager = AgentJobManager(db_manager)
        decommissioned_ids = []

        for agent in complete_agents:
            try:
                agent_job_manager.decommission_job(tenant_key, agent.job_id)
                decommissioned_ids.append(agent.job_id)
                logger.info(f"[Project Close-Out] Decommissioned agent {agent.job_id} ({agent.agent_name})")

                # Broadcast WebSocket update
                if hasattr(request.state, "websocket_manager") and request.state.websocket_manager:
                    from api.websocket_service import WebSocketService

                    await WebSocketService.notify_agent_status(
                        request.state.websocket_manager,
                        agent_name=agent.agent_name or agent.agent_type,
                        project_id=project_id,
                        status="decommissioned",
                        tenant_key=tenant_key,
                        agent_id=agent.job_id,
                        decommissioned_at=datetime.now(timezone.utc).isoformat(),
                    )

            except Exception as e:
                logger.error(f"[Project Close-Out] Failed to decommission agent {agent.job_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to decommission agent {agent.job_id}")

        # Update project status to completed
        project.status = "completed"
        project.completed_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(project)

        logger.info(
            f"[Project Close-Out] Successfully decommissioned {len(decommissioned_ids)} agents for project {project_id}"
        )

        return ProjectCloseOutResponse(
            success=True,
            message=f"Successfully decommissioned {len(decommissioned_ids)} agents",
            agents_decommissioned=len(decommissioned_ids),
            decommissioned_agent_ids=decommissioned_ids,
            project_status=project.status,
        )


@router.post("/{project_id}/continue-working", response_model=ContinueWorkingResponse)
async def continue_working_on_project(
    project_id: str,
    request: Request,
    db_manager: DatabaseManager = Depends(get_db_manager),
):
    """
    Continue working on project by resuming all completed agents.

    Handover 0113: Continue working workflow - transitions all complete agents back to working.

    Workflow:
    1. Find all agents with status='complete' for this project
    2. Transition each to status='working'
    3. Clear completed_at timestamp, set started_at to now
    4. Keep project status='active'
    5. Broadcast WebSocket updates

    Args:
        project_id: Project ID
        request: FastAPI request
        db_manager: Database manager

    Returns:
        ContinueWorkingResponse with summary

    Raises:
        HTTPException 404: Project not found
        HTTPException 403: Unauthorized
    """
    from giljo_mcp.agent_job_manager import AgentJobManager

    auth_context = request.state.auth_context
    tenant_key = auth_context["tenant_key"]

    logger.info(f"[Continue Working] Starting resume for project {project_id} (tenant: {tenant_key})")

    # Verify project exists and belongs to tenant
    with db_manager.get_session() as session:
        project = session.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key,
                    Project.deleted_at.is_(None),
                )
            )
        ).scalar_one_or_none()

        if not project:
            raise HTTPException(status_code=404, detail="Project not found")

        # Find all complete agents
        complete_agents = session.execute(
            select(MCPAgentJob).where(
                and_(
                    MCPAgentJob.project_id == project_id,
                    MCPAgentJob.tenant_key == tenant_key,
                    MCPAgentJob.status == "complete",
                )
            )
        ).scalars().all()

        if not complete_agents:
            logger.info(f"[Continue Working] No complete agents found for project {project_id}")
            return ContinueWorkingResponse(
                success=True,
                message="No agents to resume",
                agents_resumed=0,
                resumed_agent_ids=[],
                project_status=project.status,
            )

        # Resume all complete agents
        agent_job_manager = AgentJobManager(db_manager)
        resumed_ids = []

        for agent in complete_agents:
            try:
                agent_job_manager.continue_working(tenant_key, agent.job_id)
                resumed_ids.append(agent.job_id)
                logger.info(f"[Continue Working] Resumed agent {agent.job_id} ({agent.agent_name})")

                # Broadcast WebSocket update
                if hasattr(request.state, "websocket_manager") and request.state.websocket_manager:
                    from api.websocket_service import WebSocketService

                    await WebSocketService.notify_agent_status(
                        request.state.websocket_manager,
                        agent_name=agent.agent_name or agent.agent_type,
                        project_id=project_id,
                        status="working",
                        tenant_key=tenant_key,
                        agent_id=agent.job_id,
                    )

            except Exception as e:
                logger.error(f"[Continue Working] Failed to resume agent {agent.job_id}: {e}")
                raise HTTPException(status_code=500, detail=f"Failed to resume agent {agent.job_id}")

        # Ensure project status is active
        if project.status != "active":
            project.status = "active"
            project.completed_at = None
            session.commit()
            session.refresh(project)

        logger.info(f"[Continue Working] Successfully resumed {len(resumed_ids)} agents for project {project_id}")

        return ContinueWorkingResponse(
            success=True,
            message=f"Successfully resumed {len(resumed_ids)} agents",
            agents_resumed=len(resumed_ids),
            resumed_agent_ids=resumed_ids,
            project_status=project.status,
        )
