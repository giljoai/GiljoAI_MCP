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

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager

# Import Pattern: Use modular imports from models package (Post-0128a)
# See models/__init__.py for migration guidance
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Message, Task
from src.giljo_mcp.tenant import TenantManager


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
        websocket_manager: Optional[Any] = None,
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
        self._websocket_manager = websocket_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.

        Returns:
            Context manager for database session
        """
        if self._test_session is not None:
            # For test sessions, wrap in a context manager that doesn't close
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        # Return the context manager directly (no double-wrapping)
        return self.db_manager.get_session_async()

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

    async def get_project(self, project_id: str, tenant_key: Optional[str] = None) -> dict[str, Any]:
        """
        Get a specific project by ID with associated agent jobs.

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for multi-tenant isolation (required for security)

        Returns:
            Dict with success status and project details (including agents) or error

        Example:
            >>> result = await service.get_project("abc-123", tenant_key="tenant-abc")
            >>> if result["success"]:
            ...     print(result["project"]["name"])
            ...     print(f"Agents: {len(result['project']['agents'])}")
        """
        try:
            async with self._get_session() as session:
                # Get project with tenant isolation filter (Handover 0325)
                if tenant_key:
                    result = await session.execute(
                        select(Project).where(Project.tenant_key == tenant_key, Project.id == project_id)
                    )
                else:
                    # Fallback for backward compatibility - will be deprecated
                    result = await session.execute(select(Project).where(Project.id == project_id))
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found or access denied"}

                # Get agent jobs for this project (migrated to AgentJob + AgentExecution - Handover 0367a)
                agent_query = (
                    select(AgentJob, AgentExecution)
                    .join(AgentExecution, AgentJob.job_id == AgentExecution.job_id)
                    .where(AgentJob.project_id == project_id)
                    .order_by(AgentJob.created_at)
                )
                agent_result = await session.execute(agent_query)
                agent_pairs = agent_result.all()

                # Convert agents to simple dicts (matching AgentSimple schema)
                # Include messages for JobsTab WebSocket refresh fix (Handover 0358)
                agent_dicts = [
                    {
                        "id": job.job_id,
                        "job_id": job.job_id,
                        "agent_display_name": job.job_type,
                        "agent_name": execution.agent_name,
                        "status": execution.status,
                        "messages_sent_count": execution.messages_sent_count,
                        "messages_waiting_count": execution.messages_waiting_count,
                        "messages_read_count": execution.messages_read_count,
                        "thin_client": True,
                    }
                    for job, execution in agent_pairs
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
                        "execution_mode": project.execution_mode,  # Handover 0260
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
                stmt = (
                    select(Project).where(and_(Project.tenant_key == tenant_key, Project.status == "active")).limit(1)
                )

                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if not project:
                    self._logger.info(f"No active project found for tenant {tenant_key}")
                    return {"success": True, "project": None}

                # Get agent job and message counts (migrated to AgentJob - Handover 0367a)
                agent_job_stmt = select(func.count(AgentJob.job_id)).where(AgentJob.project_id == project.id)
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

    async def update_project_mission(
        self, project_id: str, mission: str, tenant_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Update the mission field after orchestrator analysis.

        This method also broadcasts the mission update via WebSocket HTTP bridge
        for real-time UI updates.

        Args:
            project_id: Project UUID
            mission: Updated mission statement
            tenant_key: Tenant key for multi-tenant isolation (required for security)

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.update_project_mission(
            ...     "abc-123",
            ...     "Build comprehensive REST API with authentication",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            async with self._get_session() as session:
                # Update project with tenant isolation filter (Handover 0325)
                if tenant_key:
                    result = await session.execute(
                        update(Project)
                        .where(Project.tenant_key == tenant_key, Project.id == project_id)
                        .values(mission=mission, updated_at=datetime.utcnow())
                    )
                else:
                    # Fallback for backward compatibility - will be deprecated
                    result = await session.execute(
                        update(Project)
                        .where(Project.id == project_id)
                        .values(mission=mission, updated_at=datetime.utcnow())
                    )

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found or access denied"}

                # Get project for tenant_key (with tenant filter if provided)
                if tenant_key:
                    project_result = await session.execute(
                        select(Project).where(Project.tenant_key == tenant_key, Project.id == project_id)
                    )
                else:
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

                # Decommission associated agents (migrated to AgentExecution - Handover 0367a)
                # Query AgentExecution records via join with AgentJob
                agent_result = await session.execute(
                    select(AgentExecution)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentJob.tenant_key == tenant_key,
                            AgentExecution.status.notin_(["complete", "failed", "cancelled"]),
                        )
                    )
                )
                executions_to_decommission = agent_result.scalars().all()
                decommissioned_ids = []

                for execution in executions_to_decommission:
                    execution.status = "decommissioned"
                    execution.updated_at = datetime.utcnow()
                    decommissioned_ids.append(execution.job_id)

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

                # Resume decommissioned agents (migrated to AgentExecution - Handover 0367a)
                agent_result = await session.execute(
                    select(AgentExecution)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentJob.tenant_key == tenant_key,
                            AgentExecution.status == "decommissioned",
                        )
                    )
                )
                executions_to_resume = agent_result.scalars().all()
                resumed_ids = []

                for execution in executions_to_resume:
                    execution.status = "waiting"
                    execution.updated_at = datetime.utcnow()
                    resumed_ids.append(execution.job_id)

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
                    if not project.meta_data:
                        project.meta_data = {}
                    project.meta_data["deactivation_reason"] = reason

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

                # Get job counts by status (migrated to AgentExecution - Handover 0367a)
                job_counts_result = await session.execute(
                    select(AgentExecution.status, func.count(AgentExecution.agent_id).label("count"))
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentJob.tenant_key == self.tenant_manager.get_current_tenant(),
                        )
                    )
                    .group_by(AgentExecution.status)
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

                # Get last activity timestamp (migrated to AgentExecution - Handover 0367a)
                last_activity_result = await session.execute(
                    select(
                        func.greatest(
                            func.max(AgentExecution.completed_at),
                            func.max(AgentExecution.started_at),
                            func.max(AgentExecution.last_progress_at),
                        )
                    )
                    .select_from(AgentExecution)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentJob.tenant_key == self.tenant_manager.get_current_tenant(),
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
                                Product.tenant_key == self.tenant_manager.get_current_tenant(),
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

        return {
            "success": True,
            "data": {
                "project_id": project_id,
                "project_name": project.name,
                "agent_count": total_agents,
                "completed_agents": completed_agents,
                "failed_agents": failed_agents,
                "all_agents_complete": all_agents_complete,
                "has_failed_agents": has_failed_agents,
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
            f'git commit -m "Project complete: {project.name}"\n'
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
        Aggregate agent status counts for closeout operations (migrated to AgentExecution - Handover 0367a).
        """
        job_counts_result = await session.execute(
            select(AgentExecution.status, func.count(AgentExecution.agent_id).label("count"))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
            .group_by(AgentExecution.status)
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

                # Handover 0343: Lock execution_mode after staging (mission exists)
                if "execution_mode" in updates:
                    if project.mission and project.mission.strip():
                        return {
                            "success": False,
                            "error": "Cannot change execution mode after staging. Mission has been generated.",
                        }

                # Update allowed fields (Handover 0260: Added execution_mode)
                # Handover 0412: Added status, completed_at for archive endpoint
                allowed_fields = {"name", "description", "mission", "execution_mode", "status", "completed_at"}
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
                        "execution_mode": project.execution_mode,  # Handover 0260
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
        self,
        project_id: str,
        user_id: Optional[str] = None,
        launch_config: Optional[dict[str, Any]] = None,
        websocket_manager: Optional[Any] = None,
    ) -> dict[str, Any]:
        """
        Launch project orchestrator.

        Creates orchestrator agent job and generates thin-client launch prompt.
        Activates the project if not already active.
        Fetches user field_priority_config and depth_config to pass to orchestrator.

        Args:
            project_id: Project UUID
            user_id: Optional user ID for fetching field priorities and depth config
            launch_config: Optional launch configuration
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Dict with success status and ProjectLaunchResponse data:
            - project_id: Project UUID
            - orchestrator_job_id: Created orchestrator job UUID
            - launch_prompt: Thin-client prompt for starting orchestrator
            - status: Project status after launch

        Example:
            >>> result = await service.launch_project("abc-123", user_id="user-456")
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

                # Fetch user field_priority_config and depth_config if user_id provided
                field_priorities = {}
                depth_config = None

                if user_id:
                    from giljo_mcp.models import User

                    user_stmt = select(User).where(
                        and_(User.id == user_id, User.tenant_key == self.tenant_manager.get_current_tenant())
                    )
                    user_result = await session.execute(user_stmt)
                    user = user_result.scalar_one_or_none()

                    if user:
                        # Extract field_priorities from v2.0 structure
                        if user.field_priority_config:
                            field_priorities = user.field_priority_config.get("priorities", {})

                        # Get depth_config
                        if user.depth_config:
                            depth_config = user.depth_config

                # Apply defaults for depth_config if not set
                if not depth_config:
                    depth_config = {
                        "vision_documents": "medium",
                        "memory_last_n_projects": 3,
                        "git_commits": 25,
                        "agent_templates": "type_only",
                        "tech_stack_sections": "all",
                        "architecture_depth": "overview",
                    }

                # Calculate next instance number for orchestrator (migrated to AgentExecution - Handover 0367a)
                tenant_key = self.tenant_manager.get_current_tenant()

                instance_stmt = (
                    select(func.coalesce(func.max(AgentExecution.instance_number), 0))
                    .select_from(AgentExecution)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        and_(
                            AgentExecution.tenant_key == tenant_key,
                            AgentJob.project_id == project_id,
                            AgentExecution.agent_display_name == "orchestrator",
                        )
                    )
                )
                instance_result = await session.execute(instance_stmt)
                instance_number = (instance_result.scalar() or 0) + 1

                # Create AgentJob (work order) - stores mission ONCE (Handover 0358a)
                orchestrator_job_id = str(uuid4())
                agent_job = AgentJob(
                    job_id=orchestrator_job_id,
                    tenant_key=tenant_key,
                    project_id=project_id,
                    mission=project.mission or f"Orchestrator mission for project: {project.name}",
                    job_type="orchestrator",
                    status="active",
                    job_metadata={
                        "field_priorities": field_priorities,
                        "depth_config": depth_config,
                        "user_id": user_id,
                        "created_via": "project_service_launch",
                    },
                )
                session.add(agent_job)

                # Create AgentExecution (executor) - first instance (Handover 0358a)
                agent_execution = AgentExecution(
                    agent_id=str(uuid4()),
                    job_id=orchestrator_job_id,
                    tenant_key=tenant_key,
                    agent_display_name="orchestrator",  # Lowercase for frontend compatibility
                    agent_name="orchestrator",  # Type key for color lookup
                    instance_number=instance_number,
                    status="waiting",
                    context_budget=project.context_budget or 150000,
                    context_used=0,
                    progress=0,
                    health_status="unknown",
                )
                session.add(agent_execution)

                # Set staging_status to 'staged' when orchestrator is launched
                project.staging_status = "staged"
                project.updated_at = datetime.utcnow()

                await session.flush()  # Get the IDs without committing

                # Generate thin-client launch prompt
                launch_prompt = f"""Launch orchestrator for project: {project.name}

Project ID: {project.id}
Mission: {project.mission}
Orchestrator Job ID: {orchestrator_job_id}

This is a thin-client launch. Use the get_orchestrator_instructions() MCP tool to fetch full mission details.
"""

                await session.commit()

                self._logger.info(f"Launched project {project_id} with orchestrator job {orchestrator_job_id}")

                # Broadcast WebSocket event
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast_project_update(
                            project_id=project.id,
                            update_type="launched",
                            project_data={
                                "name": project.name,
                                "status": project.status,
                                "staging_status": project.staging_status,
                                "orchestrator_job_id": orchestrator_job_id,
                            },
                        )
                    except Exception as ws_error:
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

                return {
                    "success": True,
                    "data": {
                        "project_id": project.id,
                        "orchestrator_job_id": orchestrator_job_id,
                        "launch_prompt": launch_prompt,
                        "status": project.status,
                        "staging_status": project.staging_status,
                    },
                }

        except Exception as e:
            self._logger.exception(f"Failed to launch project: {e}")
            return {"success": False, "error": str(e)}

    async def restore_project(self, project_id: str) -> dict[str, Any]:
        """
        Restore a completed, cancelled, or soft-deleted project to inactive status.

        Args:
            project_id: Project UUID

        Returns:
            Dict with success status or error

        Example:
            >>> result = await service.restore_project("abc-123")
        """
        try:
            async with self._get_session() as session:
                # Update project to inactive and clear completed_at and deleted_at
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(
                        status="inactive",
                        completed_at=None,
                        deleted_at=None,
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

                # Get agent jobs (migrated to AgentJob + AgentExecution - Handover 0367a)
                agent_job_result = await session.execute(
                    select(AgentJob, AgentExecution)
                    .join(AgentExecution, AgentJob.job_id == AgentExecution.job_id)
                    .where(AgentJob.project_id == project.id)
                )
                agent_pairs = agent_job_result.all()

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
                        {"name": job.job_type, "status": execution.status, "role": job.job_type}
                        for job, execution in agent_pairs
                    ],
                    "pending_messages": pending_messages,
                }

        except Exception as e:
            self._logger.exception(f"Failed to get project status: {e}")
            return {"success": False, "error": str(e)}

    async def switch_project(self, project_id: str, tenant_key: Optional[str] = None) -> dict[str, Any]:
        """
        Switch to a different project context.

        This updates the tenant context and creates/activates a session
        for the target project.

        Args:
            project_id: Project UUID to switch to
            tenant_key: Tenant key for multi-tenant isolation (required for security)

        Returns:
            Dict with success status and project details or error

        Example:
            >>> result = await service.switch_project("abc-123", tenant_key="tenant-abc")
            >>> print(f"Switched to: {result['name']}")
        """
        try:
            async with self._get_session() as db_session:
                from giljo_mcp.models import Session as SessionModel
                from giljo_mcp.tenant import current_tenant

                # Find project with tenant isolation filter (Handover 0325)
                if tenant_key:
                    result = await db_session.execute(
                        select(Project).where(Project.tenant_key == tenant_key, Project.id == project_id)
                    )
                else:
                    # Fallback for backward compatibility - will be deprecated
                    result = await db_session.execute(select(Project).where(Project.id == project_id))
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found or access denied"}

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

    async def nuclear_delete_project(self, project_id: str, websocket_manager: Optional[Any] = None) -> dict[str, Any]:
        """
        Immediately and permanently delete a project and ALL related data (nuclear delete).

        This method performs complete cascade deletion of:
        - Agent jobs (AgentJob + AgentExecution)
        - Tasks
        - Messages
        - Context indexes (ContextIndex)
        - Large document indexes (LargeDocumentIndex)
        - Sessions
        - Vision documents
        - The project itself

        Special handling:
        - Deactivates project if it's currently active
        - Broadcasts WebSocket events for real-time UI cleanup
        - Ensures multi-tenant isolation (only deletes for current tenant)
        - Fully transactional (rollback on error)

        Args:
            project_id: Project UUID
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Dict with success status and deletion details:
            - success: bool
            - message: str
            - deleted_counts: dict with counts of each deleted entity type
            - project_name: str (name of deleted project)

        Example:
            >>> result = await service.nuclear_delete_project("abc-123")
            >>> print(result["deleted_counts"])
            {"agents": 5, "tasks": 12, "messages": 48, ...}
        """
        try:
            # Get current tenant from context
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            async with self._get_session() as session:
                # Fetch project with tenant validation
                stmt = select(Project).where(
                    and_(
                        Project.id == project_id,
                        Project.tenant_key == tenant_key,
                    )
                )
                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found or access denied"}

                project_name = project.name

                # Deactivate project if it's active (to avoid constraint issues)
                if project.status == "active":
                    project.status = "inactive"
                    project.updated_at = datetime.utcnow()
                    await session.flush()  # Flush deactivation before deleting
                    self._logger.info(f"Deactivated project {project_id} before nuclear delete")

                # Initialize deletion counters
                deleted_counts = {
                    "agent_jobs": 0,
                    "tasks": 0,
                    "messages": 0,
                    "context_indexes": 0,
                    "document_indexes": 0,
                    "sessions": 0,
                    "visions": 0,
                }

                # Import additional models needed for deletion
                from giljo_mcp.models.context import ContextIndex, LargeDocumentIndex
                from giljo_mcp.models.products import Vision
                from giljo_mcp.models.projects import Session as ProjectSession

                # Delete agent jobs (migrated to AgentJob - Handover 0367a)
                # Note: AgentExecution records will cascade delete via FK relationship
                agent_job_stmt = select(AgentJob).where(
                    and_(
                        AgentJob.project_id == project_id,
                        AgentJob.tenant_key == tenant_key,
                    )
                )
                agent_jobs = (await session.execute(agent_job_stmt)).scalars().all()
                for job in agent_jobs:
                    await session.delete(job)
                deleted_counts["agent_jobs"] = len(agent_jobs)

                # Delete tasks
                task_stmt = select(Task).where(
                    and_(
                        Task.project_id == project_id,
                        Task.tenant_key == tenant_key,
                    )
                )
                tasks = (await session.execute(task_stmt)).scalars().all()
                for task in tasks:
                    await session.delete(task)
                deleted_counts["tasks"] = len(tasks)

                # Delete messages
                message_stmt = select(Message).where(
                    and_(
                        Message.project_id == project_id,
                        Message.tenant_key == tenant_key,
                    )
                )
                messages = (await session.execute(message_stmt)).scalars().all()
                for message in messages:
                    await session.delete(message)
                deleted_counts["messages"] = len(messages)

                # Delete context indexes
                context_index_stmt = select(ContextIndex).where(
                    and_(
                        ContextIndex.project_id == project_id,
                        ContextIndex.tenant_key == tenant_key,
                    )
                )
                context_indexes = (await session.execute(context_index_stmt)).scalars().all()
                for ctx_index in context_indexes:
                    await session.delete(ctx_index)
                deleted_counts["context_indexes"] = len(context_indexes)

                # Delete large document indexes
                doc_index_stmt = select(LargeDocumentIndex).where(
                    and_(
                        LargeDocumentIndex.project_id == project_id,
                        LargeDocumentIndex.tenant_key == tenant_key,
                    )
                )
                doc_indexes = (await session.execute(doc_index_stmt)).scalars().all()
                for doc_index in doc_indexes:
                    await session.delete(doc_index)
                deleted_counts["document_indexes"] = len(doc_indexes)

                # Delete sessions
                session_stmt = select(ProjectSession).where(
                    and_(
                        ProjectSession.project_id == project_id,
                        ProjectSession.tenant_key == tenant_key,
                    )
                )
                sessions = (await session.execute(session_stmt)).scalars().all()
                for proj_session in sessions:
                    await session.delete(proj_session)
                deleted_counts["sessions"] = len(sessions)

                # Delete vision documents
                vision_stmt = select(Vision).where(
                    and_(
                        Vision.project_id == project_id,
                        Vision.tenant_key == tenant_key,
                    )
                )
                visions = (await session.execute(vision_stmt)).scalars().all()
                for vision in visions:
                    await session.delete(vision)
                deleted_counts["visions"] = len(visions)

                # Mark 360 memory entries as deleted by user (preserve historical reference)
                # Handover 0390b: Use repository instead of JSONB mutation
                memory_entries_marked = 0
                if project.product_id:
                    from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

                    repo = ProductMemoryRepository()
                    memory_entries_marked = await repo.mark_entries_deleted(
                        session=session,
                        project_id=project_id,
                        tenant_key=tenant_key,
                    )

                    if memory_entries_marked > 0:
                        self._logger.info(
                            f"Marked {memory_entries_marked} 360 memory entries as deleted for project {project_id}"
                        )

                deleted_counts["memory_entries_marked"] = memory_entries_marked

                # Finally, delete the project itself
                await session.delete(project)

                # Commit transaction
                await session.commit()

                self._logger.info(
                    f"Nuclear delete completed for project {project_id} ({project_name}): "
                    f"{deleted_counts['agent_jobs']} agents, "
                    f"{deleted_counts['tasks']} tasks, "
                    f"{deleted_counts['messages']} messages, "
                    f"{deleted_counts['context_indexes']} context indexes, "
                    f"{deleted_counts['document_indexes']} document indexes, "
                    f"{deleted_counts['sessions']} sessions, "
                    f"{deleted_counts['visions']} visions, "
                    f"{deleted_counts['memory_entries_marked']} 360 memory entries marked"
                )

                # Broadcast WebSocket event for real-time UI cleanup
                if websocket_manager:
                    try:
                        await websocket_manager.broadcast_project_update(
                            project_id=project_id,
                            update_type="deleted",
                            project_data={
                                "name": project_name,
                                "deleted_counts": deleted_counts,
                            },
                        )
                    except Exception as ws_error:
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

                return {
                    "success": True,
                    "message": f"Project '{project_name}' permanently deleted",
                    "deleted_counts": deleted_counts,
                    "project_name": project_name,
                }

        except Exception as e:
            self._logger.exception(f"Failed to nuclear delete project: {e}")
            return {"success": False, "error": str(e)}

    async def _purge_project_records(self, session: AsyncSession, project: Project) -> dict[str, Any]:
        """Cascade delete a soft-deleted project and its child records."""
        project_info = {
            "id": project.id,
            "name": project.name,
            "tenant_key": project.tenant_key,
            "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
        }

        # Mark 360 memory entries as deleted by user (preserve historical reference)
        if project.product_id:
            from sqlalchemy.orm.attributes import flag_modified
            from src.giljo_mcp.models.products import Product

            product_stmt = select(Product).where(
                and_(
                    Product.id == project.product_id,
                    Product.tenant_key == project.tenant_key,
                )
            )
            product_result = await session.execute(product_stmt)
            parent_product = product_result.scalar_one_or_none()

            if parent_product and parent_product.product_memory:
                product_memory = parent_product.product_memory
                sequential_history = product_memory.get("sequential_history", [])

                for entry in sequential_history:
                    if isinstance(entry, dict) and entry.get("project_id") == project.id:
                        entry["deleted_by_user"] = True
                        entry["user_deleted_at"] = datetime.utcnow().isoformat()

                parent_product.product_memory = product_memory
                flag_modified(parent_product, "product_memory")

        # Delete agent jobs (migrated to AgentJob - Handover 0367a)
        agent_job_stmt = select(AgentJob).where(AgentJob.project_id == project.id)
        agent_jobs = (await session.execute(agent_job_stmt)).scalars().all()
        for job in agent_jobs:
            await session.delete(job)

        task_stmt = select(Task).where(Task.project_id == project.id)
        tasks = (await session.execute(task_stmt)).scalars().all()
        for task in tasks:
            await session.delete(task)

        message_stmt = select(Message).where(Message.project_id == project.id)
        messages = (await session.execute(message_stmt)).scalars().all()
        for message in messages:
            await session.delete(message)

        await session.delete(project)
        return project_info

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

                # Cascade soft delete to agent jobs - cancel all executions for this project (migrated to AgentExecution - Handover 0367a)
                executions_stmt = (
                    select(AgentExecution)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentJob.tenant_key == tenant_key,
                            AgentExecution.status.notin_(["completed", "failed", "cancelled"]),
                        )
                    )
                )
                executions_result = await session.execute(executions_stmt)
                executions = executions_result.scalars().all()

                cancelled_jobs_count = 0
                for execution in executions:
                    execution.status = "cancelled"
                    execution.decommissioned_at = now
                    execution.completed_at = now
                    cancelled_jobs_count += 1

                await session.commit()

                self._logger.info(
                    f"Soft deleted project {project_id} for tenant {tenant_key} "
                    f"at {project.deleted_at.isoformat() if project.deleted_at else 'unknown time'}. "
                    f"Cancelled {cancelled_jobs_count} agent jobs."
                )

                return {
                    "success": True,
                    "message": "Project deleted successfully",
                    "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
                    "cancelled_jobs": cancelled_jobs_count,
                }

        except Exception as e:
            self._logger.exception(f"Failed to delete project: {e}")
            return {"success": False, "error": str(e)}

    async def purge_deleted_project(self, project_id: str) -> dict[str, Any]:
        """
        Nuclear delete a specific soft-deleted project for the current tenant.

        Called when user clicks trash icon next to a deleted project.
        Uses nuclear_delete_project for complete immediate removal.
        """
        # Simply delegate to nuclear_delete_project which handles everything
        result = await self.nuclear_delete_project(project_id)

        if result.get("success"):
            # Format response to match expected purge response structure
            project_info = {
                "id": project_id,
                "name": result.get("project_name", "Unknown"),
                "tenant_key": result.get("tenant_key", ""),
                "deleted_at": datetime.now(timezone.utc).isoformat(),
            }

            self._logger.info("[Nuclear Purge] Manually purged project %s via trash icon", project_id)

            return {"success": True, "purged_count": 1, "projects": [project_info]}
        else:
            return {"success": False, "error": result.get("error", "Failed to purge project"), "purged_count": 0}

    async def purge_all_deleted_projects(self) -> dict[str, Any]:
        """
        Nuclear delete all soft-deleted projects for the current tenant.

        Uses nuclear_delete_project for each project to ensure complete removal.
        Called when user clicks "Delete All" button in deleted projects modal.
        """
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available", "purged_count": 0}

            async with self._get_session() as session:
                stmt = select(Project).where(
                    and_(Project.tenant_key == tenant_key, Project.status == "deleted", Project.deleted_at.isnot(None))
                )
                result = await session.execute(stmt)
                deleted_projects = result.scalars().all()

                if not deleted_projects:
                    return {"success": True, "purged_count": 0, "projects": []}

            # Use nuclear delete for each project
            purged_projects = []
            for project in deleted_projects:
                result = await self.nuclear_delete_project(project.id)
                if result.get("success"):
                    purged_projects.append(
                        {
                            "id": project.id,
                            "name": project.name,
                            "tenant_key": project.tenant_key,
                            "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
                        }
                    )
                else:
                    self._logger.error(f"Failed to nuclear delete project {project.id}: {result.get('error')}")

            self._logger.info(
                "[Nuclear Purge] Permanently deleted %s project(s) for tenant %s",
                len(purged_projects),
                tenant_key,
            )

            return {"success": True, "purged_count": len(purged_projects), "projects": purged_projects}

        except Exception as e:
            self._logger.exception(f"Failed to nuclear purge all deleted projects: {e}")
            return {"success": False, "error": str(e), "purged_count": 0}

    async def purge_expired_deleted_projects(self, days_before_purge: int = 10) -> dict[str, Any]:
        """
        Nuclear delete projects deleted more than specified days ago.

        Uses nuclear_delete_project to ensure complete removal of expired projects.
        This function performs COMPLETE cascade deletion:
        1. Deactivates if active
        2. Deletes ALL child agents (AgentJob + AgentExecution)
        3. Deletes ALL tasks
        4. Deletes ALL messages
        5. Deletes ALL context indexes
        6. Deletes ALL large document indexes
        7. Deletes ALL sessions
        8. Deletes ALL vision documents
        9. Deletes the project record

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
            >>> print(f"Nuclear purged {result['purged_count']} expired projects")
        """
        from datetime import timedelta, timezone

        if not self.db_manager:
            self._logger.error("[Nuclear Purge] Cannot purge - database manager not available")
            return {"success": False, "error": "Database not available"}

        try:
            async with self._get_session() as session:
                # Find projects deleted more than specified days ago
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_before_purge)

                stmt = select(Project).where(
                    Project.deleted_at.isnot(None),
                    Project.status == "deleted",
                    Project.deleted_at < cutoff_date,
                )

                result = await session.execute(stmt)
                expired_projects = result.scalars().all()

                if not expired_projects:
                    self._logger.info(
                        f"[Nuclear Purge] No expired deleted projects to purge (cutoff: {days_before_purge} days)"
                    )
                    return {"success": True, "purged_count": 0, "projects": []}

            # Use nuclear delete for each expired project
            purged_projects = []
            for project in expired_projects:
                result = await self.nuclear_delete_project(project.id)
                if result.get("success"):
                    purged_projects.append(
                        {
                            "id": project.id,
                            "name": project.name,
                            "tenant_key": project.tenant_key,
                            "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
                        }
                    )
                    self._logger.info(
                        f"[Nuclear Purge] Auto-purged expired project {project.id} "
                        f"(deleted {(datetime.now(timezone.utc) - project.deleted_at).days} days ago)"
                    )
                else:
                    self._logger.error(f"Failed to nuclear delete expired project {project.id}: {result.get('error')}")

            self._logger.info(f"[Nuclear Purge] Successfully purged {len(purged_projects)} expired deleted projects")

            return {"success": True, "purged_count": len(purged_projects), "projects": purged_projects}

        except Exception as e:
            self._logger.exception(f"[Nuclear Purge] Failed to purge expired deleted projects: {e}")
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
        """Broadcast memory update via WebSocketManager (in-process)."""
        self._logger.info(
            f"[WEBSOCKET DEBUG] Broadcasting memory update for project {project_id} (sequence: {sequence_number})"
        )

        if not self._websocket_manager:
            self._logger.debug("[WEBSOCKET] No WebSocket manager available for project:memory_updated")
            return

        summary_preview = (summary[:200] + "...") if len(summary) > 200 else summary

        try:
            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=tenant_key,
                event_type="project:memory_updated",
                data={
                    "project_id": project_id,
                    "project_name": project_name,
                    "sequence_number": sequence_number,
                    "summary_preview": summary_preview,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )
        except Exception as ws_error:
            self._logger.error(
                f"[WEBSOCKET ERROR] Failed to broadcast project:memory_updated: {ws_error}",
                exc_info=True,
            )

    async def _broadcast_mission_update(self, project_id: str, mission: str, tenant_key: str) -> None:
        """
        Broadcast mission update via WebSocketManager (in-process).

        Args:
            project_id: Project UUID
            mission: Updated mission text
            tenant_key: Tenant key for routing
        """
        self._logger.info(f"[WEBSOCKET DEBUG] About to broadcast mission_updated " f"for project {project_id}")

        if not self._websocket_manager:
            self._logger.debug("[WEBSOCKET] No WebSocket manager available for project:mission_updated")
            return

        try:
            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=tenant_key,
                event_type="project:mission_updated",
                data={
                    "project_id": project_id,
                    "mission": mission,
                    "token_estimate": len(mission) // 4,
                    "user_config_applied": False,
                    "generated_by": "orchestrator",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                },
            )

        except Exception as ws_error:
            self._logger.error(
                f"[WEBSOCKET ERROR] Failed to broadcast project:mission_updated: {ws_error}",
                exc_info=True,
            )
