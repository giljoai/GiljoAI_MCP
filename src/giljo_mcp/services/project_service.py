"""
ProjectService - Dedicated service for project domain logic

This service extracts all project-related operations from ToolAccessor
as part of Phase 1 of the god object refactoring (Handover 0121).

Responsibilities:
- CRUD operations for projects
- Project lifecycle management (complete, cancel, restore)
- Project state and status tracking
- Project metrics and statistics

Design Principles:
- Single Responsibility: Only project domain logic
- Dependency Injection: Accepts DatabaseManager and TenantManager
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager

# Import Pattern: Use modular imports from models package (Post-0128a)
# See models/__init__.py for migration guidance
from giljo_mcp.models.agents import MCPAgentJob
from giljo_mcp.models.tasks import Message
from giljo_mcp.models.projects import Project
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ProjectService:
    """
    Service for managing project lifecycle and operations.

    This service handles all project-related operations including:
    - Creating, reading, updating projects
    - Project status transitions (complete, cancel, restore)
    - Project metrics and status reporting
    - Mission updates with WebSocket integration

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        """
        Initialize ProjectService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support (provides global context access)

        Note:
            This service uses TenantManager.get_current_tenant() to retrieve tenant context.
            The tenant context is set by the get_tenant_key() dependency in the auth flow.
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # CRUD Operations
    # ============================================================================

    async def create_project(
        self,
        name: str,
        mission: str,
        description: str = "",
        product_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        status: str = "inactive",
        context_budget: int = 150000,
    ) -> dict[str, Any]:
        """
        Create a new project.

        Args:
            name: Project name (required)
            mission: AI-generated mission statement (required)
            description: Human-written project description (default: "")
            product_id: Parent product ID if project belongs to a product
            tenant_key: Tenant key for multi-tenancy (auto-generated if not provided)
            status: Initial project status (default: "inactive")
            context_budget: Token budget for context usage (default: 150000)

        Returns:
            Dict with success status and project details or error

        Example:
            >>> result = await service.create_project(
            ...     name="Build API",
            ...     mission="Create RESTful API with FastAPI",
            ...     description="User management API"
            ... )
            >>> print(result["project_id"])
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Generate tenant key if not provided
                if not tenant_key:
                    tenant_key = f"tk_{uuid4().hex}"

                # Create project entity
                project = Project(
                    name=name,
                    mission=mission,
                    description=description,
                    tenant_key=tenant_key,
                    product_id=product_id,
                    status=status,
                    context_budget=context_budget,
                    context_used=0,
                )

                session.add(project)
                await session.commit()

                project_id = str(project.id)

                self._logger.info(
                    f"Created project {project_id} with status '{status}' "
                    f"and tenant key {tenant_key}"
                )

                return {
                    "success": True,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "product_id": product_id,
                    "name": name,
                    "status": status,
                }

        except Exception as e:
            self._logger.exception(f"Failed to create project: {e}")
            return {"success": False, "error": str(e)}

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """
        Get a specific project by ID with associated agent jobs.

        Args:
            project_id: Project UUID

        Returns:
            Dict with success status and project details (including agents) or error

        Example:
            >>> result = await service.get_project("abc-123")
            >>> if result["success"]:
            ...     print(result["project"]["name"])
            ...     print(f"Agents: {len(result['project']['agents'])}")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Get project
                query = select(Project).where(Project.id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found"
                    }

                # Get agent jobs for this project (following get_active_project pattern)
                from src.giljo_mcp.models import MCPAgentJob
                agent_query = select(MCPAgentJob).where(
                    MCPAgentJob.project_id == project_id
                ).order_by(MCPAgentJob.created_at)
                agent_result = await session.execute(agent_query)
                agents = agent_result.scalars().all()

                # Convert agents to simple dicts (matching AgentSimple schema)
                agent_dicts = [
                    {
                        "id": agent.job_id,
                        "job_id": agent.job_id,
                        "agent_type": agent.agent_type,
                        "agent_name": agent.agent_name,
                        "status": agent.status,
                        "thin_client": True,
                    }
                    for agent in agents
                ]

                self._logger.info(
                    f"Retrieved project {project.name} with {len(agent_dicts)} agents"
                )

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "description": project.description,
                        "status": project.status,
                        "staging_status": project.staging_status,
                        "product_id": project.product_id,
                        "tenant_key": project.tenant_key,
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                        "created_at": project.created_at.isoformat() if project.created_at else None,
                        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
                        "agents": agent_dicts,  # Production-grade: Include agents in response
                        "agent_count": len(agent_dicts),
                    },
                }

        except Exception as e:
            self._logger.exception(f"Failed to get project: {e}")
            return {"success": False, "error": str(e)}

    async def get_active_project(self) -> dict[str, Any]:
        """
        Get the currently active project for the current tenant.

        Returns the active project (status='active') or None if no project is active.

        Follows Single Active Project architecture (Handover 0050b):
        - Only ONE project can be active per product at any time
        - Database enforces this via partial unique index

        Returns:
            Dict with success status and project details (or None if no active project)

        Example:
            >>> result = await service.get_active_project()
            >>> if result["success"] and result["project"]:
            ...     print(f"Active project: {result['project']['name']}")
        """
        try:
            # Get current tenant from context
            tenant_key = self.tenant_manager.get_current_tenant()

            # DEBUG: Log tenant context retrieval
            self._logger.debug(f"[get_active_project] Retrieved tenant_key from context: {tenant_key}")

            if not tenant_key:
                self._logger.error("[get_active_project] No tenant context available!")
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self.db_manager.get_session_async() as session:
                # Query for active project (tenant-isolated)
                from src.giljo_mcp.models import MCPAgentJob, Message

                stmt = (
                    select(Project)
                    .where(
                        and_(
                            Project.tenant_key == tenant_key,
                            Project.status == "active"
                        )
                    )
                    .limit(1)
                )

                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if not project:
                    self._logger.info(f"No active project found for tenant {tenant_key}")
                    return {
                        "success": True,
                        "project": None
                    }

                # Get agent job and message counts
                agent_job_stmt = select(func.count(MCPAgentJob.id)).where(
                    MCPAgentJob.project_id == project.id
                )
                agent_count_result = await session.execute(agent_job_stmt)
                agent_count = agent_count_result.scalar() or 0

                message_stmt = select(func.count(Message.id)).where(
                    Message.project_id == project.id
                )
                message_count_result = await session.execute(message_stmt)
                message_count = message_count_result.scalar() or 0

                self._logger.info(f"Found active project: {project.name} (ID: {project.id})")

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "alias": project.alias or "",
                        "name": project.name,
                        "mission": project.mission or "",
                        "description": project.description,
                        "status": project.status,
                        "product_id": project.product_id,
                        "created_at": project.created_at.isoformat() if project.created_at else None,
                        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
                        "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
                        "context_budget": project.context_budget or 150000,
                        "context_used": project.context_used or 0,
                        "agent_count": agent_count,
                        "message_count": message_count,
                    },
                }

        except Exception as e:
            self._logger.exception(f"Failed to get active project: {e}")
            return {"success": False, "error": str(e)}

    async def list_projects(
        self,
        status: Optional[str] = None,
        tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        List all projects with optional filters.

        Args:
            status: Filter by project status (optional)
            tenant_key: Tenant key for filtering (uses current tenant if not provided)

        Returns:
            Dict with success status and list of projects or error

        Example:
            >>> result = await service.list_projects(status="active")
            >>> for project in result["projects"]:
            ...     print(project["name"])
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {
                    "success": False,
                    "error": "No tenant context available"
                }

            async with self.db_manager.get_tenant_session_async(tenant_key) as session:
                # TENANT ISOLATION: Only return projects for the specified tenant
                query = select(Project).where(Project.tenant_key == tenant_key)
                if status:
                    query = query.where(Project.status == status)

                result = await session.execute(query)
                projects = result.scalars().all()

                project_list = []
                for project in projects:
                    # For list view, we include basic metrics
                    # (agent_count and message_count would require additional queries)
                    project_list.append({
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "description": project.description,
                        "status": project.status,
                        "staging_status": project.staging_status,
                        "tenant_key": project.tenant_key,
                        "product_id": project.product_id,
                        "created_at": project.created_at.isoformat(),
                        "updated_at": (
                            project.updated_at.isoformat()
                            if project.updated_at
                            else project.created_at.isoformat()
                        ),
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                    })

                return {
                    "success": True,
                    "projects": project_list
                }

        except Exception as e:
            self._logger.exception(f"Failed to list projects: {e}")
            return {"success": False, "error": str(e)}

    async def update_project_mission(
        self,
        project_id: str,
        mission: str
    ) -> dict[str, Any]:
        """
        Update the mission field after orchestrator analysis.

        This method also broadcasts the mission update via WebSocket HTTP bridge
        for real-time UI updates.

        Args:
            project_id: Project UUID
            mission: Updated mission statement

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.update_project_mission(
            ...     "abc-123",
            ...     "Build comprehensive REST API with authentication"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(mission=mission, updated_at=datetime.utcnow())
                )

                if result.rowcount == 0:
                    return {
                        "success": False,
                        "error": "Project not found"
                    }

                # Get project for tenant_key
                project_result = await session.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = project_result.scalar_one_or_none()

                await session.commit()

                # Broadcast mission update via WebSocket HTTP bridge
                if project:
                    await self._broadcast_mission_update(project_id, mission, project.tenant_key)

                return {
                    "success": True,
                    "message": "Mission updated successfully"
                }

        except Exception as e:
            self._logger.exception(f"Failed to update mission: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Lifecycle Management
    # ============================================================================

    async def complete_project(
        self,
        project_id: str,
        summary: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Mark a project as completed with completed_at timestamp.

        Args:
            project_id: Project UUID
            summary: Optional completion summary to store in metadata

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.complete_project(
            ...     "abc-123",
            ...     summary="Successfully implemented all features"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Build update values
                update_values = {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

                # Add summary to meta_data if provided
                if summary:
                    update_values["meta_data"] = {"summary": summary}

                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(**update_values)
                )

                if result.rowcount == 0:
                    return {
                        "success": False,
                        "error": "Project not found"
                    }

                await session.commit()

                self._logger.info(f"Completed project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} completed successfully",
                }

        except Exception as e:
            self._logger.exception(f"Failed to complete project: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_project(
        self,
        project_id: str,
        reason: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Cancel a project with completed_at timestamp.

        Args:
            project_id: Project UUID
            reason: Optional cancellation reason to store in metadata

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.cancel_project(
            ...     "abc-123",
            ...     reason="Requirements changed"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Build update values
                update_values = {
                    "status": "cancelled",
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

                # Add reason to meta_data if provided
                if reason:
                    update_values["meta_data"] = {"cancellation_reason": reason}

                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(**update_values)
                )

                if result.rowcount == 0:
                    return {
                        "success": False,
                        "error": "Project not found"
                    }

                await session.commit()

                self._logger.info(f"Cancelled project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} cancelled successfully",
                }

        except Exception as e:
            self._logger.exception(f"Failed to cancel project: {e}")
            return {"success": False, "error": str(e)}

    async def activate_project(
        self,
        project_id: str,
        force: bool = False,
        websocket_manager: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Activate a staged or paused project.

        State Transitions:
        - staging → active (initial launch)
        - paused → active (resume)

        Enforces Single Active Project constraint: automatically deactivates
        any existing active project in the same product before activating the new one.

        Args:
            project_id: Project UUID
            force: If True, skip validation checks (default: False)
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Dict with success status, message, and project data

        Raises:
            Exception: If project not found or invalid state transition

        Example:
            >>> result = await service.activate_project("abc-123")
            >>> # Returns: {"success": True, "data": {...}}
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Fetch project
                result = await session.execute(
                    select(Project)
                    .where(
                        and_(
                            Project.id == project_id,
                            Project.tenant_key == self.tenant_manager.get_current_tenant()
                        )
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Validate state transition
                if project.status not in ["staging", "paused"] and not force:
                    return {
                        "success": False,
                        "error": f"Cannot activate project from status '{project.status}'"
                    }

                # Check for existing active project in same product (Single Active Project constraint)
                if project.product_id:
                    existing_active_result = await session.execute(
                        select(Project).where(
                            and_(
                                Project.product_id == project.product_id,
                                Project.status == "active",
                                Project.id != project_id,
                                Project.tenant_key == self.tenant_manager.get_current_tenant()
                            )
                        )
                    )
                    existing_active = existing_active_result.scalar_one_or_none()

                    if existing_active:
                        # Auto-deactivate existing active project
                        existing_active.status = "paused"
                        existing_active.paused_at = datetime.utcnow()
                        existing_active.updated_at = datetime.utcnow()
                        self._logger.info(
                            f"Auto-deactivated project {existing_active.id} due to Single Active Project constraint"
                        )

                # Activate project
                project.status = "active"
                project.updated_at = datetime.utcnow()

                # Set activated_at only on first activation
                if not project.activated_at:
                    project.activated_at = datetime.utcnow()

                await session.commit()
                await session.refresh(project)

                self._logger.info(f"Activated project {project_id}")

                # Broadcast WebSocket event if manager provided
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast_project_update(
                            project_id=project.id,
                            update_type="status_changed",
                            project_data={
                                "name": project.name,
                                "status": project.status,
                                "mission": project.mission,
                            }
                        )
                    except Exception as ws_error:
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

                # Build response using ProjectResponse schema structure
                return {
                    "success": True,
                    "data": {
                        "id": project.id,
                        "name": project.name,
                        "status": project.status,
                        "mission": project.mission,
                        "description": project.description,
                        "config_data": project.config_data or {},
                        "meta_data": project.meta_data or {},
                        "created_at": project.created_at,
                        "updated_at": project.updated_at,
                        "activated_at": project.activated_at,
                        "completed_at": project.completed_at,
                        "product_id": project.product_id,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to activate project: {e}")
            return {"success": False, "error": str(e)}

    async def deactivate_project(
        self,
        project_id: str,
        reason: Optional[str] = None,
        websocket_manager: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Deactivate (pause) an active project.

        State Transition: active → paused

        Args:
            project_id: Project UUID
            reason: Optional reason for deactivation (stored in config_data)
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Dict with success status, message, and project data

        Example:
            >>> result = await service.deactivate_project(
            ...     "abc-123",
            ...     reason="Taking a break"
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Fetch project
                result = await session.execute(
                    select(Project)
                    .where(
                        and_(
                            Project.id == project_id,
                            Project.tenant_key == self.tenant_manager.get_current_tenant()
                        )
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Validate state
                if project.status != "active":
                    return {
                        "success": False,
                        "error": f"Cannot deactivate project with status '{project.status}'"
                    }

                # Deactivate project
                project.status = "paused"
                project.paused_at = datetime.utcnow()
                project.updated_at = datetime.utcnow()

                # Store reason if provided
                if reason:
                    if not project.config_data:
                        project.config_data = {}
                    project.config_data["deactivation_reason"] = reason

                await session.commit()
                await session.refresh(project)

                self._logger.info(f"Deactivated project {project_id}")

                # Broadcast WebSocket event
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast_project_update(
                            project_id=project.id,
                            update_type="status_changed",
                            project_data={
                                "name": project.name,
                                "status": project.status,
                                "mission": project.mission,
                            }
                        )
                    except Exception as ws_error:
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

                return {
                    "success": True,
                    "data": {
                        "id": project.id,
                        "name": project.name,
                        "status": project.status,
                        "mission": project.mission,
                        "description": project.description,
                        "config_data": project.config_data or {},
                        "meta_data": project.meta_data or {},
                        "created_at": project.created_at,
                        "updated_at": project.updated_at,
                        "activated_at": project.activated_at,
                        "completed_at": project.completed_at,
                        "product_id": project.product_id,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to deactivate project: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_staging(
        self,
        project_id: str,
        websocket_manager: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Cancel a project in staging state.

        State Transition: staging → cancelled

        Similar to cancel_project() but specifically for staging state.
        Cleans up any pending orchestrator jobs.

        Args:
            project_id: Project UUID
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Dict with success status, message, and project data

        Example:
            >>> result = await service.cancel_staging("abc-123")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Fetch project
                result = await session.execute(
                    select(Project)
                    .where(
                        and_(
                            Project.id == project_id,
                            Project.tenant_key == self.tenant_manager.get_current_tenant()
                        )
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Validate state
                if project.status != "staging":
                    return {
                        "success": False,
                        "error": f"Cannot cancel staging for project with status '{project.status}'"
                    }

                # Cancel project
                project.status = "cancelled"
                project.completed_at = datetime.utcnow()  # Using completed_at for cancelled_at
                project.updated_at = datetime.utcnow()

                await session.commit()
                await session.refresh(project)

                self._logger.info(f"Cancelled staging for project {project_id}")

                # Broadcast WebSocket event
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast_project_update(
                            project_id=project.id,
                            update_type="cancelled",
                            project_data={
                                "name": project.name,
                                "status": project.status,
                                "mission": project.mission,
                            }
                        )
                    except Exception as ws_error:
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

                return {
                    "success": True,
                    "data": {
                        "id": project.id,
                        "name": project.name,
                        "status": project.status,
                        "mission": project.mission,
                        "description": project.description,
                        "config_data": project.config_data or {},
                        "meta_data": project.meta_data or {},
                        "created_at": project.created_at,
                        "updated_at": project.updated_at,
                        "activated_at": project.activated_at,
                        "completed_at": project.completed_at,
                        "product_id": project.product_id,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to cancel staging: {e}")
            return {"success": False, "error": str(e)}

    async def get_project_summary(
        self,
        project_id: str
    ) -> dict[str, Any]:
        """
        Generate project summary with metrics and status.

        Returns comprehensive project overview including job statistics,
        completion metrics, and activity timestamps for dashboard display.

        Args:
            project_id: Project UUID

        Returns:
            Dict with success status and ProjectSummaryResponse data:
            - Basic project info (id, name, status, mission)
            - Agent job counts (pending/active/completed/failed)
            - Mission completion percentage
            - Timestamps (created, activated, last activity)
            - Product context (id, name)

        Example:
            >>> result = await service.get_project_summary("abc-123")
            >>> print(result["data"]["completion_percentage"])  # 75.0
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Fetch project with product eager loading
                result = await session.execute(
                    select(Project)
                    .where(
                        and_(
                            Project.id == project_id,
                            Project.tenant_key == self.tenant_manager.get_current_tenant()
                        )
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Get job counts by status
                job_counts_result = await session.execute(
                    select(
                        MCPAgentJob.status,
                        func.count(MCPAgentJob.id).label("count")
                    )
                    .where(
                        and_(
                            MCPAgentJob.project_id == project_id,
                            MCPAgentJob.tenant_key == self.tenant_manager.get_current_tenant()
                        )
                    )
                    .group_by(MCPAgentJob.status)
                )
                job_counts_raw = job_counts_result.all()

                # Build job counts dict
                job_counts = {status: count for status, count in job_counts_raw}
                
                total_jobs = sum(job_counts.values())
                completed_jobs = job_counts.get("completed", 0)
                failed_jobs = job_counts.get("failed", 0)
                active_jobs = job_counts.get("active", 0)
                pending_jobs = job_counts.get("pending", 0)

                # Calculate completion percentage
                completion_percentage = 0.0
                if total_jobs > 0:
                    completion_percentage = (completed_jobs / total_jobs) * 100.0

                # Get last activity timestamp
                last_activity_result = await session.execute(
                    select(func.max(MCPAgentJob.updated_at))
                    .where(
                        and_(
                            MCPAgentJob.project_id == project_id,
                            MCPAgentJob.tenant_key == self.tenant_manager.get_current_tenant()
                        )
                    )
                )
                last_activity_at = last_activity_result.scalar()

                # Get product info
                product_name = ""
                if project.product_id:
                    from giljo_mcp.models.products import Product
                    product_result = await session.execute(
                        select(Product).where(Product.id == project.product_id)
                    )
                    product = product_result.scalar_one_or_none()
                    if product:
                        product_name = product.name

                # Build summary response
                summary_data = {
                    "id": project.id,
                    "name": project.name,
                    "status": project.status,
                    "mission": project.mission,
                    "total_jobs": total_jobs,
                    "completed_jobs": completed_jobs,
                    "failed_jobs": failed_jobs,
                    "active_jobs": active_jobs,
                    "pending_jobs": pending_jobs,
                    "completion_percentage": completion_percentage,
                    "created_at": project.created_at,
                    "activated_at": project.activated_at,
                    "last_activity_at": last_activity_at,
                    "product_id": project.product_id or "",
                    "product_name": product_name,
                }

                return {"success": True, "data": summary_data}

        except Exception as e:
            self._logger.exception(f"Failed to get project summary: {e}")
            return {"success": False, "error": str(e)}

    async def update_project(
        self,
        project_id: str,
        updates: dict[str, Any],
        websocket_manager: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Update project fields.

        Updates all provided fields (name, description, mission, config_data).
        This is the fixed version that handles multiple fields, not just mission.

        Args:
            project_id: Project UUID
            updates: Dict of field updates (allowed: name, description, mission, config_data)
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Dict with success status and updated project data

        Example:
            >>> result = await service.update_project(
            ...     "abc-123",
            ...     {
            ...         "name": "New Name",
            ...         "description": "New Description",
            ...         "mission": "New Mission"
            ...     }
            ... )
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Fetch project
                result = await session.execute(
                    select(Project)
                    .where(
                        and_(
                            Project.id == project_id,
                            Project.tenant_key == self.tenant_manager.get_current_tenant()
                        )
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Update allowed fields
                allowed_fields = {"name", "description", "mission", "config_data"}
                for field, value in updates.items():
                    if field in allowed_fields:
                        setattr(project, field, value)

                project.updated_at = datetime.utcnow()

                await session.commit()
                await session.refresh(project)

                self._logger.info(f"Updated project {project_id}")

                # Broadcast WebSocket event
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast_project_update(
                            project_id=project.id,
                            update_type="updated",
                            project_data={
                                "name": project.name,
                                "status": project.status,
                                "mission": project.mission,
                            }
                        )
                    except Exception as ws_error:
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

                return {
                    "success": True,
                    "data": {
                        "id": project.id,
                        "name": project.name,
                        "status": project.status,
                        "mission": project.mission,
                        "description": project.description,
                        "config_data": project.config_data or {},
                        "meta_data": project.meta_data or {},
                        "created_at": project.created_at,
                        "updated_at": project.updated_at,
                        "activated_at": project.activated_at,
                        "completed_at": project.completed_at,
                        "product_id": project.product_id,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to update project: {e}")
            return {"success": False, "error": str(e)}

    async def launch_project(
        self,
        project_id: str,
        launch_config: Optional[dict[str, Any]] = None,
        websocket_manager: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Launch project orchestrator.

        Creates orchestrator agent job and generates thin-client launch prompt.
        Activates the project if not already active.

        Args:
            project_id: Project UUID
            launch_config: Optional launch configuration
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Dict with success status and ProjectLaunchResponse data:
            - project_id: Project UUID
            - orchestrator_job_id: Created orchestrator job UUID
            - launch_prompt: Thin-client prompt for starting orchestrator
            - status: Project status after launch

        Example:
            >>> result = await service.launch_project("abc-123")
            >>> print(result["data"]["orchestrator_job_id"])
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Fetch project
                result = await session.execute(
                    select(Project)
                    .where(
                        and_(
                            Project.id == project_id,
                            Project.tenant_key == self.tenant_manager.get_current_tenant()
                        )
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Activate project if not already active
                if project.status != "active":
                    activate_result = await self.activate_project(
                        project_id,
                        websocket_manager=websocket_manager
                    )
                    if not activate_result.get("success"):
                        return activate_result

                # Create orchestrator agent job
                from giljo_mcp.agent_job_manager import AgentJobManager
                
                job_manager = AgentJobManager(session, self.tenant_manager.get_current_tenant())
                
                orchestrator_job = await job_manager.create_job(
                    agent_type="orchestrator",
                    project_id=project_id,
                    config_data=launch_config or {}
                )

                # Generate thin-client launch prompt
                launch_prompt = f"""Launch orchestrator for project: {project.name}

Project ID: {project.id}
Mission: {project.mission}
Orchestrator Job ID: {orchestrator_job.id}

This is a thin-client launch. Use the get_orchestrator_instructions() MCP tool to fetch full mission details.
"""

                await session.commit()

                self._logger.info(f"Launched project {project_id} with orchestrator job {orchestrator_job.id}")

                # Broadcast WebSocket event
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast_project_update(
                            project_id=project.id,
                            update_type="launched",
                            project_data={
                                "name": project.name,
                                "status": project.status,
                                "orchestrator_job_id": orchestrator_job.id,
                            }
                        )
                    except Exception as ws_error:
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

                return {
                    "success": True,
                    "data": {
                        "project_id": project.id,
                        "orchestrator_job_id": orchestrator_job.id,
                        "launch_prompt": launch_prompt,
                        "status": project.status,
                    }
                }

        except Exception as e:
            self._logger.exception(f"Failed to launch project: {e}")
            return {"success": False, "error": str(e)}

    async def restore_project(self, project_id: str) -> dict[str, Any]:
        """
        Restore a completed or cancelled project to inactive status.

        Args:
            project_id: Project UUID

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.restore_project("abc-123")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Update project to inactive and clear completed_at
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(
                        status="inactive",
                        completed_at=None,
                        updated_at=datetime.utcnow(),
                    )
                )

                if result.rowcount == 0:
                    return {
                        "success": False,
                        "error": "Project not found"
                    }

                await session.commit()

                self._logger.info(f"Restored project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} restored successfully",
                }

        except Exception as e:
            self._logger.exception(f"Failed to restore project: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # State & Metrics
    # ============================================================================

    async def get_project_status(
        self,
        project_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Get comprehensive project status including agents and messages.

        If project_id is not provided, returns the first active project.

        Args:
            project_id: Project UUID (optional, defaults to active project)

        Returns:
            Dict with project details, agents list, and message counts

        Example:
            >>> result = await service.get_project_status("abc-123")
            >>> print(f"Active agents: {len(result['agents'])}")
            >>> print(f"Pending messages: {result['pending_messages']}")
        """
        try:
            async with self.db_manager.get_session_async() as session:
                # Get project
                query = select(Project)
                if project_id:
                    query = query.where(Project.id == project_id)
                else:
                    query = query.where(Project.status == "active").limit(1)

                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": "Project not found"
                    }

                # Get agent jobs (migrated from Agent to MCPAgentJob - Handover 0116)
                agent_job_result = await session.execute(
                    select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)
                )
                agent_jobs = agent_job_result.scalars().all()

                # Get pending messages
                message_result = await session.execute(
                    select(Message).where(
                        Message.project_id == project.id,
                        Message.status == "pending"
                    )
                )
                pending_messages = len(message_result.scalars().all())

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "status": project.status,
                        "staging_status": project.staging_status,
                        "tenant_key": project.tenant_key,
                        "product_id": project.product_id,
                        "created_at": project.created_at.isoformat(),
                        "completed_at": (
                            project.completed_at.isoformat()
                            if project.completed_at
                            else None
                        ),
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                    },
                    "agents": [
                        {
                            "name": job.agent_type,
                            "status": job.status,
                            "role": job.agent_type
                        }
                        for job in agent_jobs
                    ],
                    "pending_messages": pending_messages,
                }

        except Exception as e:
            self._logger.exception(f"Failed to get project status: {e}")
            return {"success": False, "error": str(e)}

    async def switch_project(self, project_id: str) -> dict[str, Any]:
        """
        Switch to a different project context.

        This updates the tenant context and creates/activates a session
        for the target project.

        Args:
            project_id: Project UUID to switch to

        Returns:
            Dict with success status and project details or error

        Example:
            >>> result = await service.switch_project("abc-123")
            >>> print(f"Switched to: {result['name']}")
        """
        try:
            async with self.db_manager.get_session_async() as db_session:
                from giljo_mcp.models import Session as SessionModel
                from giljo_mcp.tenant import current_tenant

                # Find project
                query = select(Project).where(Project.id == project_id)
                result = await db_session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found"
                    }

                # Set tenant context
                self.tenant_manager.set_current_tenant(project.tenant_key)
                current_tenant.set(project.tenant_key)

                # Create new session if needed
                session_query = select(SessionModel).where(
                    SessionModel.project_id == project.id,
                    SessionModel.status == "active"
                )
                session_result = await db_session.execute(session_query)
                active_session = session_result.scalar_one_or_none()

                if not active_session:
                    active_session = SessionModel(
                        project_id=project.id,
                        started_at=datetime.now(),
                        status="active",
                    )
                    db_session.add(active_session)
                    await db_session.commit()

                self._logger.info(
                    f"Switched to project '{project.name}' (ID: {project_id})"
                )

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "name": project.name,
                    "mission": project.mission,
                    "tenant_key": project.tenant_key,
                    "session_id": str(active_session.id),
                    "context_usage": f"{project.context_used}/{project.context_budget}",
                }

        except Exception as e:
            self._logger.exception(f"Failed to switch project: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Maintenance & Cleanup Methods
    # ============================================================================

    async def purge_expired_deleted_projects(self, days_before_purge: int = 10) -> dict[str, Any]:
        """
        Purge projects deleted more than specified days ago (Handover 0070).

        This function performs cascade deletion:
        1. Deletes child agents (MCPAgentJob)
        2. Deletes child tasks
        3. Deletes child messages
        4. Deletes the project record

        Called from startup.py on server start for automatic cleanup.

        Args:
            days_before_purge: Number of days before permanent deletion (default: 10)

        Returns:
            dict: Purge results with count and details
                - success: bool - Operation success status
                - purged_count: int - Number of projects purged
                - projects: list - Details of purged projects
                - error: str - Error message if failed

        Example:
            >>> result = await service.purge_expired_deleted_projects()
            >>> print(f"Purged {result['purged_count']} projects")
        """
        from datetime import timedelta, timezone

        from sqlalchemy import select

        from giljo_mcp.models import MCPAgentJob, Message, Task

        if not self.db_manager:
            self._logger.error("[Handover 0070] Cannot purge - database manager not available")
            return {"success": False, "error": "Database not available"}

        try:
            async with self.db_manager.get_session_async() as session:
                # Find projects deleted more than specified days ago
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_before_purge)

                stmt = select(Project).where(
                    Project.deleted_at.isnot(None),
                    Project.deleted_at < cutoff_date
                )

                result = await session.execute(stmt)
                expired_projects = result.scalars().all()

                if not expired_projects:
                    self._logger.info(
                        f"[Handover 0070] No expired deleted projects to purge "
                        f"(cutoff: {days_before_purge} days)"
                    )
                    return {"success": True, "purged_count": 0, "projects": []}

                purged_projects = []

                for project in expired_projects:
                    project_info = {
                        "id": project.id,
                        "name": project.name,
                        "tenant_key": project.tenant_key,
                        "deleted_at": project.deleted_at.isoformat(),
                    }

                    # Cascade delete: agent jobs
                    agent_job_stmt = select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)
                    agent_job_result = await session.execute(agent_job_stmt)
                    agent_jobs = agent_job_result.scalars().all()
                    for job in agent_jobs:
                        await session.delete(job)

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

                    self._logger.info(
                        f"[Handover 0070] Purged project '{project.name}' (id: {project.id}, "
                        f"tenant: {project.tenant_key}, deleted: {project.deleted_at})"
                    )

                    purged_projects.append(project_info)

                await session.flush()

                self._logger.info(
                    f"[Handover 0070] Successfully purged {len(purged_projects)} expired deleted projects"
                )

                return {
                    "success": True,
                    "purged_count": len(purged_projects),
                    "projects": purged_projects
                }

        except Exception as e:
            self._logger.exception(f"[Handover 0070] Failed to purge expired deleted projects: {e}")
            return {"success": False, "error": str(e), "purged_count": 0}

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _broadcast_mission_update(
        self,
        project_id: str,
        mission: str,
        tenant_key: str
    ) -> None:
        """
        Broadcast mission update via WebSocket HTTP bridge.

        This method uses the HTTP bridge to emit WebSocket events since
        MCP runs in a separate process from the main application.

        Args:
            project_id: Project UUID
            mission: Updated mission text
            tenant_key: Tenant key for routing
        """
        self._logger.info(
            f"[WEBSOCKET DEBUG] About to broadcast mission_updated "
            f"for project {project_id}"
        )

        try:
            import httpx

            self._logger.info(
                "[WEBSOCKET DEBUG] httpx imported, creating client for HTTP bridge"
            )

            # Use HTTP bridge to emit WebSocket event
            async with httpx.AsyncClient() as client:
                bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                self._logger.info(f"[WEBSOCKET DEBUG] Sending POST to {bridge_url}")

                response = await client.post(
                    bridge_url,
                    json={
                        "event_type": "project:mission_updated",
                        "tenant_key": tenant_key,
                        "data": {
                            "project_id": project_id,
                            "mission": mission,
                            "token_estimate": len(mission) // 4,
                            "user_config_applied": False,
                            "generated_by": "orchestrator",
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    },
                    timeout=5.0,
                )

                self._logger.info(
                    f"[WEBSOCKET DEBUG] HTTP bridge response: {response.status_code}"
                )
                self._logger.info(
                    f"[WEBSOCKET] Broadcasted mission_updated for project "
                    f"{project_id} via HTTP bridge"
                )

        except Exception as ws_error:
            self._logger.error(
                f"[WEBSOCKET ERROR] Failed to broadcast mission_updated "
                f"via HTTP bridge: {ws_error}",
                exc_info=True
            )
