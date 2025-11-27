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
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

import httpx
from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager

# Import Pattern: Use modular imports from models package (Post-0128a)
# See models/__init__.py for migration guidance
from giljo_mcp.models.agents import MCPAgentJob
from giljo_mcp.models.projects import Project
from giljo_mcp.models.tasks import Message
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

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: Optional[AsyncSession] = None,
    ):
        """
        Initialize ProjectService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support (provides global context access)
            test_session: Optional AsyncSession for tests to share the same transaction

        Note:
            This service uses TenantManager.get_current_tenant() to retrieve tenant context.
            The tenant context is set by the get_tenant_key() dependency in the auth flow.
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    @asynccontextmanager
    async def _get_session(self):
        """
        Yield a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.
        """
        if self._test_session is not None:
            yield self._test_session
            return

        async with self.db_manager.get_session_async() as session:
            yield session

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
            async with self._get_session() as session:
                # Generate tenant key if not provided
                if not tenant_key:
                    tenant_key = f"tk_{uuid4().hex}"

                # Create project entity
                now = datetime.utcnow()
                project = Project(
                    name=name,
                    mission=mission,
                    description=description,
                    tenant_key=tenant_key,
                    product_id=product_id,
                    status=status,
                    context_budget=context_budget,
                    context_used=0,
                    updated_at=now,  # Explicitly set since DB schema may not have DEFAULT
                )

                session.add(project)
                await session.commit()
                await session.refresh(project)  # Load DB-generated fields (created_at, updated_at)

                project_id = str(project.id)

                self._logger.info(
                    f"Created project {project_id} with status '{status}' " f"and tenant key {tenant_key}"
                )

                return {
                    "success": True,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "product_id": product_id,
                    "name": name,
                    "description": description,
                    "mission": mission,
                    "status": status,
                    "created_at": project.created_at.isoformat() if project.created_at else None,
                    "updated_at": project.updated_at.isoformat() if project.updated_at else None,
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
            async with self._get_session() as session:
                # Get project
                query = select(Project).where(Project.id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}

                # Get agent jobs for this project (following get_active_project pattern)
                from src.giljo_mcp.models import MCPAgentJob

                agent_query = (
                    select(MCPAgentJob).where(MCPAgentJob.project_id == project_id).order_by(MCPAgentJob.created_at)
                )
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

                self._logger.info(f"Retrieved project {project.name} with {len(agent_dicts)} agents")

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
                return {"success": False, "error": "No tenant context available"}

            async with self._get_session() as session:
                # Query for active project (tenant-isolated)
                from src.giljo_mcp.models import MCPAgentJob, Message

                stmt = (
                    select(Project).where(and_(Project.tenant_key == tenant_key, Project.status == "active")).limit(1)
                )

                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if not project:
                    self._logger.info(f"No active project found for tenant {tenant_key}")
                    return {"success": True, "project": None}

                # Get agent job and message counts
                agent_job_stmt = select(func.count(MCPAgentJob.id)).where(MCPAgentJob.project_id == project.id)
                agent_count_result = await session.execute(agent_job_stmt)
                agent_count = agent_count_result.scalar() or 0

                message_stmt = select(func.count(Message.id)).where(Message.project_id == project.id)
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

    async def list_projects(self, status: Optional[str] = None, tenant_key: Optional[str] = None) -> dict[str, Any]:
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
                return {"success": False, "error": "No tenant context available"}

            async with self.db_manager.get_tenant_session_async(tenant_key) as session:
                # TENANT ISOLATION: Only return projects for the specified tenant
                query = select(Project).where(Project.tenant_key == tenant_key)

                if status:
                    # Explicit status filter, including deleted if requested
                    query = query.where(Project.status == status)
                    if status == "deleted":
                        query = query.where(Project.deleted_at.isnot(None))
                else:
                    # Default listing excludes soft-deleted projects
                    query = query.where(Project.deleted_at.is_(None))

                result = await session.execute(query)
                projects = result.scalars().all()

                project_list = []
                for project in projects:
                    # For list view, we include basic metrics
                    # (agent_count and message_count would require additional queries)
                    project_list.append(
                        {
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
                                project.updated_at.isoformat() if project.updated_at else project.created_at.isoformat()
                            ),
                            "context_budget": project.context_budget,
                            "context_used": project.context_used,
                        }
                    )

                return {"success": True, "projects": project_list}

        except Exception as e:
            self._logger.exception(f"Failed to list projects: {e}")
            return {"success": False, "error": str(e)}

    async def update_project_mission(self, project_id: str, mission: str) -> dict[str, Any]:
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
            async with self._get_session() as session:
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(mission=mission, updated_at=datetime.utcnow())
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                # Get project for tenant_key
                project_result = await session.execute(select(Project).where(Project.id == project_id))
                project = project_result.scalar_one_or_none()

                await session.commit()

                # Broadcast mission update via WebSocket HTTP bridge
                if project:
                    await self._broadcast_mission_update(project_id, mission, project.tenant_key)

                return {"success": True, "message": "Mission updated successfully"}

        except Exception as e:
            self._logger.exception(f"Failed to update mission: {e}")
            return {"success": False, "error": str(e)}

    # ============================================================================
    # Lifecycle Management
    # ============================================================================

    async def complete_project(
        self,
        project_id: str,
        summary: str,
        key_outcomes: list[str],
        decisions_made: list[str],
        tenant_key: Optional[str] = None,
        db_session: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Mark a project as completed and trigger 360 memory update.

        Args:
            project_id: Project UUID
            summary: Completion summary (required)
            key_outcomes: List of key outcomes/deliverables
            decisions_made: List of decisions captured during project
            db_session: Optional database session (for transaction management)

        Returns:
            Dict with success status and memory update metadata
        """
        try:
            resolved_tenant = tenant_key or self.tenant_manager.get_current_tenant()
            if not resolved_tenant:
                return {"success": False, "error": "Tenant not set"}

            if not summary or not summary.strip():
                return {"success": False, "error": "Summary is required"}

            owns_session = db_session is None

            if owns_session:
                async with self._get_session() as session:
                    return await self._complete_project_transaction(
                        session=session,
                        project_id=project_id,
                        tenant_key=resolved_tenant,
                        summary=summary,
                        key_outcomes=key_outcomes,
                        decisions_made=decisions_made,
                        commit=owns_session,
                    )

            return await self._complete_project_transaction(
                session=db_session,
                project_id=project_id,
                tenant_key=resolved_tenant,
                summary=summary,
                key_outcomes=key_outcomes,
                decisions_made=decisions_made,
                commit=False,
            )

        except Exception as e:
            self._logger.exception(f"Failed to complete project: {e}")
            return {"success": False, "error": str(e)}

    async def _complete_project_transaction(
        self,
        session: AsyncSession,
        project_id: str,
        tenant_key: str,
        summary: str,
        key_outcomes: list[str],
        decisions_made: list[str],
        commit: bool,
    ) -> dict[str, Any]:
        """Complete project within provided session context."""
        now = datetime.utcnow()

        result = await session.execute(
            select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key,
                )
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            return {"success": False, "error": "Project not found or access denied"}

        project.status = "completed"
        project.completed_at = now
        project.updated_at = now
        project.closeout_executed_at = now
        project.orchestrator_summary = summary

        # Store closeout metadata for audit trail
        project.meta_data = project.meta_data or {}
        project.meta_data["closeout"] = {
            "summary": summary,
            "key_outcomes": key_outcomes or [],
            "decisions_made": decisions_made or [],
            "completed_at": now.isoformat(),
        }

        # Invoke MCP tool to write 360 Memory entry
        from giljo_mcp.tools.project_closeout import close_project_and_update_memory

        mcp_result = await close_project_and_update_memory(
            project_id=project_id,
            summary=summary,
            key_outcomes=key_outcomes or [],
            decisions_made=decisions_made or [],
            tenant_key=tenant_key,
            db_manager=self.db_manager,
            session=session,
        )

        if not mcp_result.get("success"):
            self._logger.error(f"MCP tool call failed: {mcp_result.get('error')}")

        memory_updated = bool(mcp_result.get("success"))
        sequence_number = mcp_result.get("sequence_number", 0)
        git_commits_count = mcp_result.get("git_commits_count", 0)

        if commit:
            await session.commit()

        await self._broadcast_memory_update(
            project_id=project_id,
            project_name=project.name,
            sequence_number=sequence_number,
            summary=summary,
            tenant_key=tenant_key,
        )

        return {
            "success": True,
            "message": f"Project {project_id} completed successfully",
            "memory_updated": memory_updated,
            "sequence_number": sequence_number,
            "git_commits_count": git_commits_count,
        }

    async def cancel_project(self, project_id: str, reason: Optional[str] = None) -> dict[str, Any]:
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
            async with self._get_session() as session:
                # Build update values
                update_values = {
                    "status": "cancelled",
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

                # Add reason to meta_data if provided
                if reason:
                    update_values["meta_data"] = {"cancellation_reason": reason}

                result = await session.execute(update(Project).where(Project.id == project_id).values(**update_values))

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                await session.commit()

                self._logger.info(f"Cancelled project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} cancelled successfully",
                }

        except Exception as e:
            self._logger.exception(f"Failed to cancel project: {e}")
            return {"success": False, "error": str(e)}

    async def close_out_project(self, project_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Close out project and decommission agents (Handover 0113).

        Marks project as completed with timestamp and optionally decommissions
        associated agents if agent jobs are tracked.

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict with success status, message, and decommissioned agent details

        Raises:
            Returns error dict if project not found or tenant access denied

        Example:
            >>> result = await service.close_out_project(
            ...     "abc-123",
            ...     "tenant-key-456"
            ... )
            >>> # Returns: {
            ...     "success": True,
            ...     "message": "Project closed out successfully",
            ...     "agents_decommissioned": 5,
            ...     "decommissioned_agent_ids": ["job-1", "job-2", ...]
            ... }
        """
        try:
            async with self._get_session() as session:
                # Fetch project with tenant validation
                result = await session.execute(
                    select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found or access denied"}

                # Mark project as completed
                project.status = "completed"
                project.completed_at = datetime.utcnow()
                project.updated_at = datetime.utcnow()
                project.closeout_executed_at = datetime.utcnow()

                # Decommission associated agents
                agent_result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.project_id == project_id,
                            MCPAgentJob.tenant_key == tenant_key,
                            MCPAgentJob.status.notin_(["complete", "failed", "cancelled"]),
                        )
                    )
                )
                agents_to_decommission = agent_result.scalars().all()
                decommissioned_ids = []

                for agent in agents_to_decommission:
                    agent.status = "decommissioned"
                    agent.updated_at = datetime.utcnow()
                    decommissioned_ids.append(agent.job_id)

                await session.commit()

                self._logger.info(
                    f"Closed out project {project_id} with {len(decommissioned_ids)} agents decommissioned"
                )

                return {
                    "success": True,
                    "message": "Project closed out successfully",
                    "agents_decommissioned": len(decommissioned_ids),
                    "decommissioned_agent_ids": decommissioned_ids,
                    "project_status": "completed",
                }

        except Exception as e:
            self._logger.exception(f"Failed to close out project: {e}")
            return {"success": False, "error": str(e)}

    async def continue_working(self, project_id: str, tenant_key: str) -> dict[str, Any]:
        """
        Resume work on a completed project (Handover 0113).

        Reopens a completed project by changing status to active and clearing
        completed_at timestamp. Validates project is in completed state.

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict with success status, message, and resumed agent details

        Raises:
            Returns error dict if:
            - Project not found or tenant access denied
            - Project not in completed state (invalid state transition)

        Example:
            >>> result = await service.continue_working(
            ...     "abc-123",
            ...     "tenant-key-456"
            ... )
            >>> # Returns: {
            ...     "success": True,
            ...     "message": "Project resumed successfully",
            ...     "agents_resumed": 3,
            ...     "resumed_agent_ids": ["job-1", "job-2", "job-3"]
            ... }
        """
        try:
            async with self._get_session() as session:
                # Fetch project with tenant validation
                result = await session.execute(
                    select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found or access denied"}

                # Validate project is in completed state
                if project.status != "completed":
                    return {
                        "success": False,
                        "error": f"Cannot resume project from status '{project.status}'. Project must be completed.",
                    }

                # Reopen project in inactive state.
                # This avoids violating the Single Active Project per product constraint.
                project.status = "inactive"
                project.completed_at = None
                project.updated_at = datetime.utcnow()

                # Resume decommissioned agents
                agent_result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.project_id == project_id,
                            MCPAgentJob.tenant_key == tenant_key,
                            MCPAgentJob.status == "decommissioned",
                        )
                    )
                )
                agents_to_resume = agent_result.scalars().all()
                resumed_ids = []

                for agent in agents_to_resume:
                    agent.status = "waiting"
                    agent.updated_at = datetime.utcnow()
                    resumed_ids.append(agent.job_id)

                await session.commit()

                self._logger.info(f"Resumed project {project_id} with {len(resumed_ids)} agents resumed")

                return {
                    "success": True,
                    "message": "Project resumed successfully",
                    "agents_resumed": len(resumed_ids),
                    "resumed_agent_ids": resumed_ids,
                    "project_status": "inactive",
                }

        except Exception as e:
            self._logger.exception(f"Failed to resume project: {e}")
            return {"success": False, "error": str(e)}

    async def activate_project(
        self, project_id: str, force: bool = False, websocket_manager: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Activate a project.

        State Transitions:
        - staging → active (initial launch)
        - inactive → active (activate/resume)

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
            async with self._get_session() as session:
                # Fetch project
                result = await session.execute(
                    select(Project).where(
                        and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Validate state transition
                if project.status not in ["staging", "inactive"] and not force:
                    return {"success": False, "error": f"Cannot activate project from status '{project.status}'"}

                # Check for existing active project in same product (Single Active Project constraint)
                if project.product_id:
                    existing_active_result = await session.execute(
                        select(Project).where(
                            and_(
                                Project.product_id == project.product_id,
                                Project.status == "active",
                                Project.id != project_id,
                                Project.tenant_key == self.tenant_manager.get_current_tenant(),
                            )
                        )
                    )
                    existing_active = existing_active_result.scalar_one_or_none()

                    if existing_active:
                        # Auto-deactivate existing active project
                        existing_active.status = "inactive"
                        existing_active.updated_at = datetime.utcnow()
                        self._logger.info(
                            f"Auto-deactivated project {existing_active.id} due to Single Active Project constraint"
                        )

                        # IMPORTANT: Flush deactivation before activating the new project to
                        # satisfy the unique index idx_project_single_active_per_product.
                        # Otherwise Postgres may see two active projects for the same product
                        # in a single flush and raise a unique violation.
                        await session.flush()

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
                            },
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
                    },
                }

        except Exception as e:
            self._logger.exception(f"Failed to activate project: {e}")
            return {"success": False, "error": str(e)}

    async def deactivate_project(
        self, project_id: str, reason: Optional[str] = None, websocket_manager: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Deactivate an active project.

        State Transition: active → inactive

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
            async with self._get_session() as session:
                # Fetch project
                result = await session.execute(
                    select(Project).where(
                        and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Validate state
                if project.status != "active":
                    return {"success": False, "error": f"Cannot deactivate project with status '{project.status}'"}

                # Deactivate project
                project.status = "inactive"
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
                            },
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
                    },
                }

        except Exception as e:
            self._logger.exception(f"Failed to deactivate project: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_staging(self, project_id: str, websocket_manager: Optional[Any] = None) -> dict[str, Any]:
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
            async with self._get_session() as session:
                # Fetch project
                result = await session.execute(
                    select(Project).where(
                        and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Validate state
                if project.status != "staging":
                    return {
                        "success": False,
                        "error": f"Cannot cancel staging for project with status '{project.status}'",
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
                            },
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
                    },
                }

        except Exception as e:
            self._logger.exception(f"Failed to cancel staging: {e}")
            return {"success": False, "error": str(e)}

    async def get_project_summary(self, project_id: str) -> dict[str, Any]:
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
            async with self._get_session() as session:
                # Fetch project with product eager loading
                result = await session.execute(
                    select(Project).where(
                        and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Get job counts by status
                job_counts_result = await session.execute(
                    select(MCPAgentJob.status, func.count(MCPAgentJob.id).label("count"))
                    .where(
                        and_(
                            MCPAgentJob.project_id == project_id,
                            MCPAgentJob.tenant_key == self.tenant_manager.get_current_tenant(),
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

                # Get last activity timestamp (most recent of completed_at, started_at, or last_progress_at)
                last_activity_result = await session.execute(
                    select(
                        func.greatest(
                            func.max(MCPAgentJob.completed_at),
                            func.max(MCPAgentJob.started_at),
                            func.max(MCPAgentJob.last_progress_at),
                        )
                    ).where(
                        and_(
                            MCPAgentJob.project_id == project_id,
                            MCPAgentJob.tenant_key == self.tenant_manager.get_current_tenant(),
                        )
                    )
                )
                last_activity_at = last_activity_result.scalar()

                # Get product info
                product_name = ""
                if project.product_id:
                    from giljo_mcp.models.products import Product

                    product_result = await session.execute(
                        select(Product).where(
                            and_(
                                Product.id == project.product_id,
                                Product.tenant_key == self.tenant_manager.get_current_tenant()
                            )
                        )
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

    async def get_closeout_data(self, project_id: str, db_session: Optional[Any] = None) -> dict[str, Any]:
        """
        Generate dynamic closeout checklist and prompt for project completion.

        Called by GET /api/projects/{project_id}/closeout.

        Returns:
            Dict with success flag and ProjectCloseoutDataResponse payload.
        """
        tenant_key = self.tenant_manager.get_current_tenant()

        try:
            if db_session:
                return await self._build_closeout_data(project_id, tenant_key, db_session)

            async with self._get_session() as session:
                return await self._build_closeout_data(project_id, tenant_key, session)

        except Exception as e:
            self._logger.exception(f"Failed to get closeout data: {e}")
            return {"success": False, "error": str(e)}

    async def can_close_project(
        self, project_id: str, tenant_key: Optional[str] = None, db_session: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Determine whether a project can be closed based on agent status.
        """
        tenant_key = tenant_key or self.tenant_manager.get_current_tenant()

        if not tenant_key:
            return {"success": False, "error": "Tenant context missing"}

        try:
            if db_session:
                return await self._build_can_close_response(project_id, tenant_key, db_session)

            async with self._get_session() as session:
                return await self._build_can_close_response(project_id, tenant_key, session)

        except Exception as e:
            self._logger.exception(f"Failed to evaluate can-close for project {project_id}: {e}")
            return {"success": False, "error": str(e)}

    async def generate_closeout_prompt(
        self, project_id: str, tenant_key: Optional[str] = None, db_session: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Generate closeout prompt with checklist and agent summary.
        """
        tenant_key = tenant_key or self.tenant_manager.get_current_tenant()

        if not tenant_key:
            return {"success": False, "error": "Tenant context missing"}

        try:
            if db_session:
                return await self._build_closeout_prompt(project_id, tenant_key, db_session)

            async with self._get_session() as session:
                return await self._build_closeout_prompt(project_id, tenant_key, session)

        except Exception as e:
            self._logger.exception(f"Failed to generate closeout prompt for project {project_id}: {e}")
            return {"success": False, "error": str(e)}

    async def _build_closeout_data(self, project_id: str, tenant_key: str, session: Any) -> dict[str, Any]:
        """
        Internal helper to build closeout data using provided session.
        """
        project = await self._get_project_for_tenant(project_id, tenant_key, session)

        if not project:
            return {"success": False, "error": "Project not found or access denied"}

        status_counts = await self._aggregate_agent_statuses(project_id, tenant_key, session)
        total_agents = status_counts["total"]
        completed_agents = status_counts["completed"]
        failed_agents = status_counts["failed"]
        active_agents = status_counts["active"]

        all_agents_complete = total_agents > 0 and completed_agents == total_agents and active_agents == 0
        has_failed_agents = failed_agents > 0
        has_git_commits = False

        if project.product_id:
            from giljo_mcp.models.products import Product

            product_result = await session.execute(
                select(Product).where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
            )
            product = product_result.scalar_one_or_none()

            if product and product.product_memory:
                git_config = product.product_memory.get("git_integration", {}) or {}
                github_config = product.product_memory.get("github", {}) or {}
                repo_name = git_config.get("repo_name") or github_config.get("repo_name")
                integration_enabled = git_config.get("enabled") or github_config.get("enabled")
                has_git_commits = bool(integration_enabled and repo_name)

        checklist: list[str] = []

        if all_agents_complete:
            checklist.append("[PASS] All agents completed successfully")
        else:
            checklist.append(f"[WARN] {completed_agents}/{total_agents} agents completed")

        if not has_failed_agents:
            checklist.append("[PASS] No failed agents")
        else:
            checklist.append(f"[FAIL] {failed_agents} agent(s) failed")

        if total_agents > 0:
            checklist.append(f"[PASS] Project has meaningful work ({total_agents} agents)")
        else:
            checklist.append("[INFO] No agents in project (empty project)")

        if has_git_commits:
            checklist.append("[PASS] Git commits will be included in 360 Memory")
        else:
            checklist.append("[INFO] No Git integration (manual summary will be used)")

        mission_preview = project.mission or ""
        if len(mission_preview) > 200:
            mission_preview = f"{mission_preview[:200]}..."

        tenant_for_prompt = tenant_key or ""
        closeout_prompt = (
            f"# Project Closeout: {project.name}\n\n"
            "## Project Summary\n"
            f"Project ID: {project_id}\n"
            f"Mission: {mission_preview}\n"
            f"Agents: {total_agents} total ({completed_agents} completed, {failed_agents} failed)\n\n"
            "## MCP Command Template\n\n"
            "Use this command to close out the project and update 360 Memory:\n\n"
            "close_project_and_update_memory(\n"
            f'    project_id=\"{project_id}\",\n'
            "    summary=\"\"\"\n"
            "    Provide a concise 2-3 paragraph summary of the project delivery.\n"
            "    Focus on outcomes, decisions, and next steps for the product team.\n"
            "    \"\"\",\n"
            "    key_outcomes=[\n"
            '        \"Outcome 1: Describe key deliverable\",\n'
            '        \"Outcome 2: Describe key deliverable\",\n'
            '        \"Outcome 3: Describe key deliverable\",\n'
            "    ],\n"
            "    decisions_made=[\n"
            '        \"Decision 1: Document architectural or technical choice\",\n'
            '        \"Decision 2: Document architectural or technical choice\",\n'
            "    ],\n"
            f'    tenant_key=\"{tenant_for_prompt}\"\n'
            ")\n\n"
            "## Guidance\n"
            "- Summaries should explain what changed and why it matters.\n"
            "- List measurable outcomes when possible (performance, reliability, coverage).\n"
            "- Capture decisions that affect future work or context loading.\n"
        )

        return {
            "success": True,
            "data": {
                "checklist": checklist,
                "closeout_prompt": closeout_prompt,
                "project_name": project.name,
                "project_id": project_id,
                "agent_count": total_agents,
                "all_agents_complete": all_agents_complete,
                "has_failed_agents": has_failed_agents,
                "has_git_commits": has_git_commits,
            },
        }

    async def _build_can_close_response(self, project_id: str, tenant_key: str, session: Any) -> dict[str, Any]:
        """
        Build readiness response for can-close endpoint.
        """
        project = await self._get_project_for_tenant(project_id, tenant_key, session)

        if not project:
            return {"success": False, "error": "Project not found or access denied"}

        status_counts = await self._aggregate_agent_statuses(project_id, tenant_key, session)
        all_agents_finished = status_counts["total"] > 0 and status_counts["active"] == 0

        summary = None
        if all_agents_finished:
            summary_parts = [f"{status_counts['completed']} successful agents"]
            summary_parts.append(f"{status_counts['failed']} failed agents")
            summary_parts.append(f"{status_counts['blocked']} blocked agents")
            summary = ", ".join(summary_parts)

        return {
            "success": True,
            "data": {
                "can_close": all_agents_finished,
                "summary": summary,
                "all_agents_finished": all_agents_finished,
                "agent_statuses": {
                    "complete": status_counts["completed"],
                    "failed": status_counts["failed"],
                    "active": status_counts["active"],
                    "blocked": status_counts["blocked"],
                },
            },
        }

    async def _build_closeout_prompt(self, project_id: str, tenant_key: str, session: Any) -> dict[str, Any]:
        """
        Build a bash closeout prompt and checklist for the project.
        """
        project = await self._get_project_for_tenant(project_id, tenant_key, session)

        if not project:
            return {"success": False, "error": "Project not found or access denied"}

        status_counts = await self._aggregate_agent_statuses(project_id, tenant_key, session)
        agent_summary = (
            f"{status_counts['completed']} completed, "
            f"{status_counts['failed']} failed, "
            f"{status_counts['active']} active, "
            f"{status_counts['blocked']} blocked"
        )

        repo_path = "."
        branch = "main"
        if project.meta_data:
            repo_path = project.meta_data.get("path", ".") or "."
            branch = project.meta_data.get("git_branch", branch) or branch

        prompt = (
            "#!/bin/bash\n"
            "set -euo pipefail\n\n"
            f"cd {repo_path}\n"
            "git status\n"
            "git add .\n"
            f"git commit -m \"Project complete: {project.name}\"\n"
            f"git push origin {branch}\n\n"
            "cat > PROJECT_SUMMARY.md <<'EOF'\n"
            f"Project: {project.name}\n"
            f"Mission: {project.mission or ''}\n"
            f"Agent Summary: {agent_summary}\n"
            "Key Outcomes:\n"
            "- Fill in final deliverables here\n"
            "Decisions Made:\n"
            "- Record architecture or workflow decisions here\n"
            "EOF\n"
        )

        checklist = [
            "Review all agent outputs and ensure artifacts are saved.",
            "Commit final changes to the repository.",
            f"Push branch {branch} to remote.",
            "Update PROJECT_SUMMARY.md with outcomes and decisions.",
            "Run close_project_and_update_memory() to refresh 360 Memory.",
        ]

        project.closeout_prompt = prompt
        await session.commit()

        return {
            "success": True,
            "data": {
                "prompt": prompt,
                "checklist": checklist,
                "project_name": project.name,
                "agent_summary": agent_summary,
            },
        }

    async def _aggregate_agent_statuses(self, project_id: str, tenant_key: str, session: Any) -> dict[str, Any]:
        """
        Aggregate agent status counts for closeout operations.
        """
        job_counts_result = await session.execute(
            select(MCPAgentJob.status, func.count(MCPAgentJob.id).label("count"))
            .where(
                and_(
                    MCPAgentJob.project_id == project_id,
                    MCPAgentJob.tenant_key == tenant_key,
                )
            )
            .group_by(MCPAgentJob.status)
        )
        job_counts = {status: count for status, count in job_counts_result.all()}

        total_agents = sum(job_counts.values())
        completed_agents = job_counts.get("complete", 0) + job_counts.get("completed", 0)
        failed_agents = job_counts.get("failed", 0)
        blocked_agents = job_counts.get("blocked", 0)
        active_statuses = {
            "working",
            "active",
            "waiting",
            "pending",
            "preparing",
            "running",
            "queued",
            "paused",
            "review",
            "planning",
            "blocked",
        }
        active_agents = sum(job_counts.get(status, 0) for status in active_statuses)

        return {
            "job_counts": job_counts,
            "total": total_agents,
            "completed": completed_agents,
            "failed": failed_agents,
            "blocked": blocked_agents,
            "active": active_agents,
        }

    async def _get_project_for_tenant(self, project_id: str, tenant_key: str, session: Any) -> Optional[Project]:
        """
        Fetch a project scoped to tenant for closeout operations.
        """
        result = await session.execute(
            select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
        )
        return result.scalar_one_or_none()

    async def update_project(
        self, project_id: str, updates: dict[str, Any], websocket_manager: Optional[Any] = None
    ) -> dict[str, Any]:
        """
        Update project fields.

        Updates all provided fields (name, description, mission).
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
            async with self._get_session() as session:
                # Fetch project
                result = await session.execute(
                    select(Project).where(
                        and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Update allowed fields
                allowed_fields = {"name", "description", "mission"}
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
                            },
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
                        "meta_data": project.meta_data or {},
                        "created_at": project.created_at,
                        "updated_at": project.updated_at,
                        "activated_at": project.activated_at,
                        "completed_at": project.completed_at,
                        "product_id": project.product_id,
                    },
                }

        except Exception as e:
            self._logger.exception(f"Failed to update project: {e}")
            return {"success": False, "error": str(e)}

    async def launch_project(
        self, project_id: str, launch_config: Optional[dict[str, Any]] = None, websocket_manager: Optional[Any] = None
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
            async with self._get_session() as session:
                # Fetch project
                result = await session.execute(
                    select(Project).where(
                        and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Activate project if not already active
                if project.status != "active":
                    activate_result = await self.activate_project(project_id, websocket_manager=websocket_manager)
                    if not activate_result.get("success"):
                        return activate_result

                # Create orchestrator agent job
                from giljo_mcp.agent_job_manager import AgentJobManager

                job_manager = AgentJobManager(session, self.tenant_manager.get_current_tenant())

                orchestrator_job = await job_manager.create_job(
                    agent_type="orchestrator", project_id=project_id, config_data=launch_config or {}
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
                            },
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
                    },
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
            async with self._get_session() as session:
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
                    return {"success": False, "error": "Project not found"}

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

    async def get_project_status(self, project_id: Optional[str] = None) -> dict[str, Any]:
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
            async with self._get_session() as session:
                # Get project
                query = select(Project)
                if project_id:
                    query = query.where(Project.id == project_id)
                else:
                    query = query.where(Project.status == "active").limit(1)

                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Get agent jobs (migrated from Agent to MCPAgentJob - Handover 0116)
                agent_job_result = await session.execute(
                    select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)
                )
                agent_jobs = agent_job_result.scalars().all()

                # Get pending messages
                message_result = await session.execute(
                    select(Message).where(Message.project_id == project.id, Message.status == "pending")
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
                        "completed_at": (project.completed_at.isoformat() if project.completed_at else None),
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                    },
                    "agents": [
                        {"name": job.agent_type, "status": job.status, "role": job.agent_type} for job in agent_jobs
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
            async with self._get_session() as db_session:
                from giljo_mcp.models import Session as SessionModel
                from giljo_mcp.tenant import current_tenant

                # Find project
                query = select(Project).where(Project.id == project_id)
                result = await db_session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}

                # Set tenant context
                self.tenant_manager.set_current_tenant(project.tenant_key)
                current_tenant.set(project.tenant_key)

                # Create new session if needed (active = not ended)
                session_query = select(SessionModel).where(
                    SessionModel.project_id == project.id, SessionModel.ended_at.is_(None)
                )
                session_result = await db_session.execute(session_query)
                active_session = session_result.scalar_one_or_none()

                if not active_session:
                    active_session = SessionModel(
                        project_id=project.id, started_at=datetime.now(), tenant_key=project.tenant_key
                    )
                    db_session.add(active_session)
                    await db_session.commit()

                self._logger.info(f"Switched to project '{project.name}' (ID: {project_id})")

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

    async def delete_project(self, project_id: str) -> dict[str, Any]:
        """
        Soft delete a project.

        Sets status='deleted' and deleted_at timestamp for the current tenant's project.
        Actual purge is handled separately by purge_expired_deleted_projects().

        Args:
            project_id: Project UUID

        Returns:
            Dict with success status, message, and deleted_at timestamp or error.
        """
        try:
            # Get current tenant from context
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            async with self._get_session() as session:
                stmt = select(Project).where(
                    and_(
                        Project.id == project_id,
                        Project.tenant_key == tenant_key,
                        Project.deleted_at.is_(None),
                    )
                )
                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found or already deleted"}

                now = datetime.now(timezone.utc)
                project.status = "deleted"
                project.deleted_at = now
                project.updated_at = now

                await session.commit()

                self._logger.info(
                    f"Soft deleted project {project_id} for tenant {tenant_key} "
                    f"at {project.deleted_at.isoformat() if project.deleted_at else 'unknown time'}"
                )

                return {
                    "success": True,
                    "message": "Project deleted successfully",
                    "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
                }

        except Exception as e:
            self._logger.exception(f"Failed to delete project: {e}")
            return {"success": False, "error": str(e)}

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
            async with self._get_session() as session:
                # Find projects deleted more than specified days ago
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_before_purge)

                stmt = select(Project).where(Project.deleted_at.isnot(None), Project.deleted_at < cutoff_date)

                result = await session.execute(stmt)
                expired_projects = result.scalars().all()

                if not expired_projects:
                    self._logger.info(
                        f"[Handover 0070] No expired deleted projects to purge " f"(cutoff: {days_before_purge} days)"
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

                return {"success": True, "purged_count": len(purged_projects), "projects": purged_projects}

        except Exception as e:
            self._logger.exception(f"[Handover 0070] Failed to purge expired deleted projects: {e}")
            return {"success": False, "error": str(e), "purged_count": 0}

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _broadcast_memory_update(
        self,
        project_id: str,
        project_name: str,
        sequence_number: int,
        summary: str,
        tenant_key: str,
    ) -> None:
        """Broadcast memory update via WebSocket HTTP bridge."""
        self._logger.info(
            f"[WEBSOCKET DEBUG] Broadcasting memory update for project {project_id} (sequence: {sequence_number})"
        )

        try:
            async with httpx.AsyncClient() as client:
                bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                summary_preview = (summary[:200] + "...") if len(summary) > 200 else summary

                response = await client.post(
                    bridge_url,
                    json={
                        "event_type": "project:memory_updated",
                        "tenant_key": tenant_key,
                        "data": {
                            "project_id": project_id,
                            "project_name": project_name,
                            "sequence_number": sequence_number,
                            "summary_preview": summary_preview,
                            "timestamp": datetime.utcnow().isoformat(),
                        },
                    },
                    timeout=5.0,
                )

                self._logger.info(
                    f"[WEBSOCKET] Broadcasted memory_updated for project {project_id} (response: {response.status_code})"
                )

        except Exception as ws_error:
            self._logger.error(
                f"[WEBSOCKET ERROR] Failed to broadcast memory_updated via HTTP bridge: {ws_error}",
                exc_info=True,
            )

    async def _broadcast_mission_update(self, project_id: str, mission: str, tenant_key: str) -> None:
        """
        Broadcast mission update via WebSocket HTTP bridge.

        This method uses the HTTP bridge to emit WebSocket events since
        MCP runs in a separate process from the main application.

        Args:
            project_id: Project UUID
            mission: Updated mission text
            tenant_key: Tenant key for routing
        """
        self._logger.info(f"[WEBSOCKET DEBUG] About to broadcast mission_updated " f"for project {project_id}")

        try:
            self._logger.info("[WEBSOCKET DEBUG] httpx imported, creating client for HTTP bridge")

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

                self._logger.info(f"[WEBSOCKET DEBUG] HTTP bridge response: {response.status_code}")
                self._logger.info(
                    f"[WEBSOCKET] Broadcasted mission_updated for project " f"{project_id} via HTTP bridge"
                )

        except Exception as ws_error:
            self._logger.error(
                f"[WEBSOCKET ERROR] Failed to broadcast mission_updated " f"via HTTP bridge: {ws_error}", exc_info=True
            )
