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
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    AlreadyExistsError,
    BaseGiljoError,
    ProjectStateError,
    ResourceNotFoundError,
    ValidationError,
)

# Import Pattern: Use modular imports from models package (Post-0128a)
# See models/__init__.py for migration guidance
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Message, Task
from src.giljo_mcp.schemas.service_responses import (
    ActiveProjectDetail,
    CanCloseResult,
    CloseoutData,
    CloseoutPromptResult,
    NuclearDeleteResult,
    OperationResult,
    ProjectCloseOutResult,
    ProjectCompleteResult,
    ProjectData,
    ProjectDetail,
    ProjectLaunchResult,
    ProjectListItem,
    ProjectMissionUpdateResult,
    ProjectPurgeResult,
    ProjectResumeResult,
    ProjectSummaryResult,
    ProjectSwitchResult,
    SoftDeleteResult,
)
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


def _build_ws_project_data(project) -> dict:
    """Build standardized project data dict for WebSocket broadcasts.

    Single source of truth for project data sent to frontend via
    WebSocket ``broadcast_project_update`` events. All project broadcast
    sites should use this helper to ensure a consistent field structure.

    Args:
        project: Project model instance (SQLAlchemy).

    Returns:
        Dict with the fields extracted by
        ``WebSocketManager.broadcast_project_update``.
    """
    return {
        "name": project.name,
        "status": project.status,
        "mission": project.mission,
    }


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
        test_session: AsyncSession | None = None,
        websocket_manager: Any | None = None,
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
        product_id: str | None = None,
        tenant_key: str | None = None,
        status: str = "inactive",
        project_type_id: str | None = None,
        series_number: int | None = None,
        subseries: str | None = None,
    ) -> Project:
        """
        Create a new project.

        Args:
            name: Project name (required)
            mission: AI-generated mission statement (required)
            description: Human-written project description (default: "")
            product_id: Parent product ID if project belongs to a product
            tenant_key: Tenant key for multi-tenancy (auto-generated if not provided)
            status: Initial project status (default: "inactive")
            project_type_id: Project type ID for taxonomy classification (Handover 0440a)
            series_number: Sequential number within a project type (Handover 0440a)
            subseries: Single-letter subseries suffix (Handover 0440a)

        Returns:
            Project: The created project instance

        Raises:
            BaseGiljoError: When project creation fails

        Example:
            >>> project = await service.create_project(
            ...     name="Build API",
            ...     mission="Create RESTful API with FastAPI",
            ...     description="User management API"
            ... )
            >>> print(project.id)
        """
        try:
            async with self._get_session() as session:
                # Generate tenant key if not provided
                if not tenant_key:
                    tenant_key = f"tk_{uuid4().hex}"

                # Application-level duplicate check before insert
                if series_number is not None:
                    dup_query = select(Project.id).where(
                        Project.tenant_key == tenant_key,
                        Project.series_number == series_number,
                        Project.deleted_at.is_(None),
                    )
                    if project_type_id:
                        dup_query = dup_query.where(Project.project_type_id == project_type_id)
                    else:
                        dup_query = dup_query.where(Project.project_type_id.is_(None))
                    if subseries is not None:
                        dup_query = dup_query.where(Project.subseries == subseries)
                    else:
                        dup_query = dup_query.where(Project.subseries.is_(None))
                    dup_result = await session.execute(dup_query)
                    if dup_result.scalar_one_or_none():
                        raise AlreadyExistsError(
                            message="Taxonomy combination already in use. Please choose a different series number or suffix.",
                            context={"name": name, "tenant_key": tenant_key},
                        )

                # Create project entity
                now = datetime.now(timezone.utc)
                project = Project(
                    name=name,
                    mission=mission,
                    description=description,
                    tenant_key=tenant_key,
                    product_id=product_id,
                    status=status,
                    project_type_id=project_type_id,
                    series_number=series_number,
                    subseries=subseries,
                    updated_at=now,  # Explicitly set since DB schema may not have DEFAULT
                )

                session.add(project)
                await session.commit()
                await session.refresh(project)  # Load DB-generated fields (created_at, updated_at)

                # Handover 0440a: Eagerly load project_type relationship for taxonomy_alias
                if project.project_type_id:
                    result = await session.execute(
                        select(Project).options(selectinload(Project.project_type)).where(Project.id == project.id)
                    )
                    project = result.scalar_one()

                self._logger.info(f"Created project {project.id} with status '{status}' and tenant key {tenant_key}")

                return project

        except IntegrityError as e:
            if "uq_project_taxonomy" in str(e):
                raise AlreadyExistsError(
                    message="Taxonomy combination already in use. Please choose a different series number or suffix.",
                    context={"name": name, "tenant_key": tenant_key},
                ) from e
            self._logger.exception("Failed to create project")
            raise BaseGiljoError(
                message=f"Failed to create project: {e!s}", context={"name": name, "tenant_key": tenant_key}
            ) from e
        except Exception as e:
            self._logger.exception("Failed to create project")
            raise BaseGiljoError(
                message=f"Failed to create project: {e!s}", context={"name": name, "tenant_key": tenant_key}
            ) from e

    async def get_project(self, project_id: str, tenant_key: str) -> ProjectDetail:
        """
        Get a specific project by ID with associated agent jobs.

        Args:
            project_id: Project UUID
            tenant_key: REQUIRED - Tenant key for multi-tenant isolation (Handover 0424 Phase 0)

        Returns:
            ProjectDetail: Typed project details (including agents)

        Raises:
            ValidationError: If tenant_key is None or empty (security requirement)
            ResourceNotFoundError: When project not found
            BaseGiljoError: When operation fails

        Example:
            >>> result = await service.get_project("abc-123", tenant_key="tenant-abc")
            >>> print(result.name)
            >>> print(f"Agents: {len(result.agents)}")
        """
        # SECURITY FIX: Require tenant_key (Handover 0424 Phase 0)
        if not tenant_key:
            raise ValidationError("tenant_key is required for security (Handover 0424 Phase 0)")

        try:
            async with self._get_session() as session:
                # Get project with mandatory tenant isolation filter (Handover 0424 Phase 0)
                # Handover 0440a: Eagerly load project_type for taxonomy_alias property
                result = await session.execute(
                    select(Project)
                    .options(selectinload(Project.project_type))
                    .where(Project.tenant_key == tenant_key, Project.id == project_id)
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise ResourceNotFoundError(
                        message="Project not found or access denied",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                # Get agent jobs for this project (defense-in-depth: tenant_key on join query)
                agent_query = (
                    select(AgentJob, AgentExecution)
                    .join(AgentExecution, AgentJob.job_id == AgentExecution.job_id)
                    .where(AgentJob.project_id == project_id, AgentJob.tenant_key == tenant_key)
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

                return ProjectDetail(
                    id=str(project.id),
                    alias=project.alias,
                    name=project.name,
                    mission=project.mission,
                    description=project.description,
                    status=project.status,
                    staging_status=project.staging_status,
                    product_id=project.product_id,
                    tenant_key=project.tenant_key,
                    execution_mode=project.execution_mode,
                    meta_data=project.meta_data or {},
                    created_at=project.created_at.isoformat() if project.created_at else None,
                    updated_at=project.updated_at.isoformat() if project.updated_at else None,
                    completed_at=project.completed_at.isoformat() if project.completed_at else None,
                    agents=agent_dicts,
                    agent_count=len(agent_dicts),
                    message_count=0,
                    # Handover 0440a: Taxonomy fields
                    project_type_id=project.project_type_id,
                    project_type=project.project_type,
                    series_number=project.series_number,
                    subseries=project.subseries,
                    taxonomy_alias=project.taxonomy_alias,
                )

        except (ValueError, ResourceNotFoundError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to get project")
            raise BaseGiljoError(
                message=f"Failed to get project: {e!s}", context={"project_id": project_id, "tenant_key": tenant_key}
            ) from e

    async def get_active_project(self) -> ActiveProjectDetail | None:
        """
        Get the currently active project for the current tenant.

        Returns the active project (status='active') or None if no project is active.

        Follows Single Active Project architecture (Handover 0050b):
        - Only ONE project can be active per product at any time
        - Database enforces this via partial unique index

        Returns:
            Dict with project details, or None if no active project

        Raises:
            ValidationError: When no tenant context is available
            BaseGiljoError: When operation fails

        Example:
            >>> result = await service.get_active_project()
            >>> if result:
            ...     print(f"Active project: {result['name']}")
        """
        try:
            # Get current tenant from context
            tenant_key = self.tenant_manager.get_current_tenant()

            # DEBUG: Log tenant context retrieval
            self._logger.debug(f"[get_active_project] Retrieved tenant_key from context: {tenant_key}")

            if not tenant_key:
                self._logger.error("[get_active_project] No tenant context available!")
                raise ValidationError(
                    message="No tenant context available", context={"operation": "get_active_project"}
                )

            async with self._get_session() as session:
                # Query for active project (tenant-isolated)
                # Handover 0440a: Eagerly load project_type for taxonomy_alias property
                stmt = (
                    select(Project)
                    .options(selectinload(Project.project_type))
                    .where(and_(Project.tenant_key == tenant_key, Project.status == "active"))
                    .limit(1)
                )

                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if not project:
                    self._logger.info(f"No active project found for tenant {tenant_key}")
                    return None

                # Get agent job and message counts (defense-in-depth: tenant_key on child queries)
                agent_job_stmt = select(func.count(AgentJob.job_id)).where(
                    AgentJob.project_id == project.id, AgentJob.tenant_key == tenant_key
                )
                agent_count_result = await session.execute(agent_job_stmt)
                agent_count = agent_count_result.scalar() or 0

                message_stmt = select(func.count(Message.id)).where(
                    Message.project_id == project.id, Message.tenant_key == tenant_key
                )
                message_count_result = await session.execute(message_stmt)
                message_count = message_count_result.scalar() or 0

                self._logger.info(f"Found active project: {project.name} (ID: {project.id})")

                return ActiveProjectDetail(
                    id=str(project.id),
                    alias=project.alias or "",
                    name=project.name,
                    mission=project.mission or "",
                    description=project.description,
                    status=project.status,
                    product_id=project.product_id,
                    created_at=project.created_at.isoformat() if project.created_at else None,
                    updated_at=project.updated_at.isoformat() if project.updated_at else None,
                    completed_at=project.completed_at.isoformat() if project.completed_at else None,
                    deleted_at=project.deleted_at.isoformat() if project.deleted_at else None,
                    agent_count=agent_count,
                    message_count=message_count,
                    # Handover 0440a: Taxonomy fields
                    project_type_id=project.project_type_id,
                    series_number=project.series_number,
                    subseries=project.subseries,
                    taxonomy_alias=project.taxonomy_alias,
                )

        except ValidationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to get active project")
            raise BaseGiljoError(message=f"Failed to get active project: {e!s}", context={}) from e

    async def list_projects(self, status: str | None = None, tenant_key: str | None = None) -> list[ProjectListItem]:
        """
        List all projects with optional filters.

        Args:
            status: Filter by project status (optional)
            tenant_key: Tenant key for filtering (uses current tenant if not provided)

        Returns:
            List of project dicts

        Raises:
            ValidationError: When no tenant context is available
            BaseGiljoError: When operation fails

        Example:
            >>> projects = await service.list_projects(status="active")
            >>> for project in projects:
            ...     print(project["name"])
        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "list_projects"})

            async with self.db_manager.get_tenant_session_async(tenant_key) as session:
                # TENANT ISOLATION: Only return projects for the specified tenant
                # Handover 0440a: Eagerly load project_type for taxonomy_alias property
                query = (
                    select(Project).options(selectinload(Project.project_type)).where(Project.tenant_key == tenant_key)
                )

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

                # For list view, we include basic metrics
                # (agent_count and message_count would require additional queries)
                project_list = [
                    ProjectListItem(
                        id=str(project.id),
                        name=project.name,
                        mission=project.mission,
                        description=project.description,
                        status=project.status,
                        staging_status=project.staging_status,
                        tenant_key=project.tenant_key,
                        product_id=project.product_id,
                        created_at=project.created_at.isoformat(),
                        updated_at=(
                            project.updated_at.isoformat() if project.updated_at else project.created_at.isoformat()
                        ),
                        # Handover 0440a: Taxonomy fields
                        project_type_id=project.project_type_id,
                        project_type=project.project_type,
                        series_number=project.series_number,
                        subseries=project.subseries,
                        taxonomy_alias=project.taxonomy_alias,
                    )
                    for project in projects
                ]

                return project_list

        except ValidationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to list projects")
            raise BaseGiljoError(message=f"Failed to list projects: {e!s}", context={"tenant_key": tenant_key}) from e

    async def update_project_mission(
        self, project_id: str, mission: str, tenant_key: str | None = None
    ) -> ProjectMissionUpdateResult:
        """
        Update the mission field after orchestrator analysis.

        This method also broadcasts the mission update via WebSocket HTTP bridge
        for real-time UI updates.

        Args:
            project_id: Project UUID
            mission: Updated mission statement
            tenant_key: Tenant key for multi-tenant isolation (uses context if not provided)

        Returns:
            Dict with success status

        Raises:
            ValidationError: No tenant context available
            ResourceNotFoundError: When project not found
            BaseGiljoError: When operation fails

        Example:
            >>> result = await service.update_project_mission(
            ...     "abc-123",
            ...     "Build comprehensive REST API with authentication",
            ...     tenant_key="tenant-abc"
            ... )
        """
        try:
            async with self._get_session() as session:
                # TENANT ISOLATION: Require tenant_key, fall back to context
                if not tenant_key:
                    tenant_key = self.tenant_manager.get_current_tenant()
                if not tenant_key:
                    raise ValidationError(
                        message="No tenant context available",
                        context={"operation": "update_project_mission", "project_id": project_id},
                    )

                # Handover 0425: Also set staging_status to 'staged' when mission is updated
                result = await session.execute(
                    update(Project)
                    .where(and_(Project.tenant_key == tenant_key, Project.id == project_id))
                    .values(mission=mission, staging_status="staged", updated_at=datetime.now(timezone.utc))
                )

                if result.rowcount == 0:
                    raise ResourceNotFoundError(
                        message="Project not found or access denied",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                # Get project for WebSocket broadcast
                project_result = await session.execute(
                    select(Project).where(and_(Project.tenant_key == tenant_key, Project.id == project_id))
                )
                project = project_result.scalar_one_or_none()

                await session.commit()

                # Broadcast mission update via WebSocket HTTP bridge
                if project:
                    await self._broadcast_mission_update(project_id, mission, project.tenant_key)

                return ProjectMissionUpdateResult(
                    message="Mission updated successfully",
                    project_id=project_id,
                )

        except (ResourceNotFoundError, ValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to update mission")
            raise BaseGiljoError(
                message=f"Failed to update mission: {e!s}", context={"project_id": project_id, "tenant_key": tenant_key}
            ) from e

    # ============================================================================
    # Lifecycle Management
    # ============================================================================

    async def complete_project(
        self,
        project_id: str,
        summary: str,
        key_outcomes: list[str],
        decisions_made: list[str],
        tenant_key: str | None = None,
        db_session: Any | None = None,
    ) -> ProjectCompleteResult:
        """
        Mark a project as completed and trigger 360 memory update.

        Args:
            project_id: Project UUID
            summary: Completion summary (required)
            key_outcomes: List of key outcomes/deliverables
            decisions_made: List of decisions captured during project
            db_session: Optional database session (for transaction management)

        Returns:
            ProjectCompleteResult: Completion result with memory update metadata

        Raises:
            ValidationError: When tenant not set or summary missing
            BaseGiljoError: When operation fails
        """
        try:
            resolved_tenant = tenant_key or self.tenant_manager.get_current_tenant()
            if not resolved_tenant:
                raise ValidationError(message="Tenant not set", context={"operation": "complete_project"})

            if not summary or not summary.strip():
                raise ValidationError(
                    message="Summary is required", context={"operation": "complete_project", "project_id": project_id}
                )

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

        except ValidationError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to complete project")
            raise BaseGiljoError(
                message=f"Failed to complete project: {e!s}",
                context={"project_id": project_id, "tenant_key": tenant_key},
            ) from e

    async def _complete_project_transaction(
        self,
        session: AsyncSession,
        project_id: str,
        tenant_key: str,
        summary: str,
        key_outcomes: list[str],
        decisions_made: list[str],
        commit: bool,
    ) -> ProjectCompleteResult:
        """
        Complete project within provided session context.

        Raises:
            ResourceNotFoundError: When project not found
        """
        now = datetime.now(timezone.utc)

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
            raise ResourceNotFoundError(
                message="Project not found or access denied",
                context={"project_id": project_id, "tenant_key": tenant_key},
            )

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

        try:
            mcp_result = await close_project_and_update_memory(
                project_id=project_id,
                summary=summary,
                key_outcomes=key_outcomes or [],
                decisions_made=decisions_made or [],
                tenant_key=tenant_key,
                db_manager=self.db_manager,
                session=session,
            )
            memory_updated = True
            sequence_number = mcp_result.get("sequence_number", 0)
            git_commits_count = mcp_result.get("git_commits_count", 0)
        except (ResourceNotFoundError, ValidationError, ProjectStateError, OSError):
            self._logger.exception("MCP tool call failed")
            memory_updated = False
            sequence_number = 0
            git_commits_count = 0

        if commit:
            await session.commit()

        await self._broadcast_memory_update(
            project_id=project_id,
            project_name=project.name,
            sequence_number=sequence_number,
            summary=summary,
            tenant_key=tenant_key,
        )

        return ProjectCompleteResult(
            message=f"Project {project_id} completed successfully",
            memory_updated=memory_updated,
            sequence_number=sequence_number,
            git_commits_count=git_commits_count,
        )

    async def cancel_project(self, project_id: str, tenant_key: str, reason: str | None = None) -> None:
        """
        Cancel a project with completed_at timestamp.

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for multi-tenant isolation
            reason: Optional cancellation reason to store in metadata

        Returns:
            None

        Raises:
            ResourceNotFoundError: When project not found
            BaseGiljoError: When operation fails

        Example:
            >>> await service.cancel_project(
            ...     "abc-123",
            ...     "tenant-key-456",
            ...     reason="Requirements changed"
            ... )
        """
        try:
            async with self._get_session() as session:
                # Build update values
                update_values = {
                    "status": "cancelled",
                    "completed_at": datetime.now(timezone.utc),
                    "updated_at": datetime.now(timezone.utc),
                }

                # Add reason to meta_data if provided
                if reason:
                    update_values["meta_data"] = {"cancellation_reason": reason}

                result = await session.execute(
                    update(Project)
                    .where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                    .values(**update_values)
                )

                if result.rowcount == 0:
                    raise ResourceNotFoundError(
                        message="Project not found or access denied",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                await session.commit()

                self._logger.info(f"Cancelled project {project_id}")

        except ResourceNotFoundError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to cancel project")
            raise BaseGiljoError(message=f"Failed to cancel project: {e!s}", context={"project_id": project_id}) from e

    async def close_out_project(self, project_id: str, tenant_key: str) -> ProjectCloseOutResult:
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
            ResourceNotFoundError: When project not found or access denied
            BaseGiljoError: When operation fails

        Example:
            >>> result = await service.close_out_project(
            ...     "abc-123",
            ...     "tenant-key-456"
            ... )
            >>> # Returns: {
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
                    raise ResourceNotFoundError(
                        message="Project not found or access denied",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                # Mark project as completed
                project.status = "completed"
                project.completed_at = datetime.now(timezone.utc)
                project.updated_at = datetime.now(timezone.utc)
                project.closeout_executed_at = datetime.now(timezone.utc)

                # Decommission associated agents with smart lifecycle drain (Handover 0498)
                # Query AgentExecution records via join with AgentJob
                agent_result = await session.execute(
                    select(AgentExecution)
                    .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                    .where(
                        and_(
                            AgentJob.project_id == project_id,
                            AgentJob.tenant_key == tenant_key,
                            AgentExecution.status.notin_(["complete", "decommissioned"]),
                        )
                    )
                )
                executions_to_decommission = agent_result.scalars().all()
                decommissioned_ids = []

                for execution in executions_to_decommission:
                    execution.status = "decommissioned"
                    execution.updated_at = datetime.now(timezone.utc)
                    decommissioned_ids.append(execution.job_id)

                await session.commit()

                self._logger.info(
                    f"Closed out project {project_id} with {len(decommissioned_ids)} agents decommissioned"
                )

                return ProjectCloseOutResult(
                    message="Project closed out successfully",
                    agents_decommissioned=len(decommissioned_ids),
                    decommissioned_agent_ids=decommissioned_ids,
                    project_status="completed",
                )

        except ResourceNotFoundError:
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to close out project")
            raise BaseGiljoError(
                message=f"Failed to close out project: {e!s}",
                context={"project_id": project_id, "tenant_key": tenant_key},
            ) from e

    async def continue_working(self, project_id: str, tenant_key: str) -> ProjectResumeResult:
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
            ResourceNotFoundError: When project not found or access denied
            ProjectStateError: When project not in completed state
            BaseGiljoError: When operation fails

        Example:
            >>> result = await service.continue_working(
            ...     "abc-123",
            ...     "tenant-key-456"
            ... )
            >>> # Returns: {
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
                    raise ResourceNotFoundError(
                        message="Project not found or access denied",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                # Validate project is in completed state
                if project.status != "completed":
                    raise ProjectStateError(
                        message=f"Cannot resume project from status '{project.status}'. Project must be completed.",
                        context={"project_id": project_id, "current_status": project.status},
                    )

                # Reopen project in inactive state.
                # This avoids violating the Single Active Project per product constraint.
                project.status = "inactive"
                project.completed_at = None
                project.updated_at = datetime.now(timezone.utc)

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
                    execution.updated_at = datetime.now(timezone.utc)
                    resumed_ids.append(execution.job_id)

                await session.commit()

                self._logger.info(f"Resumed project {project_id} with {len(resumed_ids)} agents resumed")

                return ProjectResumeResult(
                    message="Project resumed successfully",
                    agents_resumed=len(resumed_ids),
                    resumed_agent_ids=resumed_ids,
                    project_status="inactive",
                )

        except (ResourceNotFoundError, ProjectStateError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to resume project")
            raise BaseGiljoError(
                message=f"Failed to resume project: {e!s}", context={"project_id": project_id, "tenant_key": tenant_key}
            ) from e

    async def activate_project(
        self,
        project_id: str,
        force: bool = False,
        websocket_manager: Any | None = None,
        tenant_key: str | None = None,
    ) -> Project:
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
            tenant_key: Optional tenant key (uses current tenant if not provided)

        Returns:
            Project: The activated project instance

        Raises:
            ResourceNotFoundError: When project not found
            ProjectStateError: When invalid state transition
            BaseGiljoError: When operation fails

        Example:
            >>> project = await service.activate_project("abc-123")
            >>> assert project.status == "active"
        """
        try:
            resolved_tenant = tenant_key or self.tenant_manager.get_current_tenant()
            async with self._get_session() as session:
                # Fetch project
                result = await session.execute(
                    select(Project).where(and_(Project.id == project_id, Project.tenant_key == resolved_tenant))
                )
                project = result.scalar_one_or_none()

                if not project:
                    raise ResourceNotFoundError(
                        message="Project not found", context={"project_id": project_id, "tenant_key": resolved_tenant}
                    )

                # Validate state transition
                if project.status not in ["staging", "inactive"] and not force:
                    raise ProjectStateError(
                        message=f"Cannot activate project from status '{project.status}'",
                        context={"project_id": project_id, "current_status": project.status},
                    )

                # Check for existing active project in same product (Single Active Project constraint)
                if project.product_id:
                    existing_active_result = await session.execute(
                        select(Project).where(
                            and_(
                                Project.product_id == project.product_id,
                                Project.status == "active",
                                Project.id != project_id,
                                Project.tenant_key == resolved_tenant,
                            )
                        )
                    )
                    existing_active = existing_active_result.scalar_one_or_none()

                    if existing_active:
                        # Auto-deactivate existing active project
                        existing_active.status = "inactive"
                        existing_active.updated_at = datetime.now(timezone.utc)
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
                project.updated_at = datetime.now(timezone.utc)

                # Set activated_at only on first activation
                if not project.activated_at:
                    project.activated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(project)

                self._logger.info(f"Activated project {project_id}")

                # Broadcast WebSocket event if manager provided
                ws_mgr = websocket_manager or self._websocket_manager
                if ws_mgr:
                    try:
                        await ws_mgr.broadcast_project_update(
                            project_id=project.id,
                            update_type="status_changed",
                            project_data=_build_ws_project_data(project),
                        )
                    except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

                # Handover 0431: Create orchestrator fixture on project activation
                # This ensures orchestrator appears in UI before "Stage Project" is clicked
                await self._ensure_orchestrator_fixture(
                    session=session,
                    project=project,
                    websocket_manager=ws_mgr,
                )

                return project

        except (ResourceNotFoundError, ProjectStateError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:
            self._logger.exception("Failed to activate project")
            raise BaseGiljoError(
                message=f"Failed to activate project: {e!s}", context={"project_id": project_id}
            ) from e

    async def _ensure_orchestrator_fixture(
        self,
        session: AsyncSession,
        project: Project,
        websocket_manager: Any | None = None,
    ) -> dict[str, str] | None:
        """
        Ensure an orchestrator fixture exists for the activated project (Handover 0431).

        Creates orchestrator AgentJob + AgentExecution as a "fixture" that appears
        in the UI before the user clicks "Stage Project". This indicates to the user
        that an agent is ready to stage.

        The orchestrator is created with status='waiting' and no mission yet.
        When user clicks "Stage Project", the staging endpoint will reuse this
        existing orchestrator and generate the staging prompt.

        Args:
            session: Active database session
            project: The project being activated
            websocket_manager: Optional WebSocket manager for real-time UI updates

        Returns:
            Dict with orchestrator job_id and agent_id if created, None if already exists
        """
        tenant_key = self.tenant_manager.get_current_tenant()

        # Check if orchestrator already exists for this project
        # FIX 1 (Handover 0485): Use exclusion-based filter (finds: waiting, working, complete, blocked)
        existing_stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project.id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),  # Handover 0491: Simplified statuses
            )
        )
        existing_result = await session.execute(existing_stmt)
        existing = existing_result.scalar_one_or_none()

        if existing:
            self._logger.info(
                f"[ORCHESTRATOR FIXTURE] Orchestrator already exists for project {project.id}, "
                f"job_id={existing.job_id}, status={existing.status}"
            )
            return None

        # Generate IDs
        job_id = str(uuid4())
        agent_id = str(uuid4())

        # Create AgentJob (work order)
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission=f"Orchestrator for project: {project.name}",  # Placeholder
            job_type="orchestrator",
            status="active",
            job_metadata={
                "created_via": "project_activation_fixture",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
        )
        session.add(agent_job)

        # Create AgentExecution (executor)
        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="waiting",
            progress=0,
            health_status="unknown",
        )
        session.add(agent_execution)

        await session.commit()
        await session.refresh(agent_job)
        await session.refresh(agent_execution)

        self._logger.info(
            f"[ORCHESTRATOR FIXTURE] Created orchestrator fixture for project {project.id}: "
            f"job_id={job_id}, agent_id={agent_id}"
        )

        # Broadcast agent:created event for UI update
        if websocket_manager:
            try:
                await websocket_manager.broadcast_to_tenant(
                    tenant_key=tenant_key,
                    event_type="agent:created",
                    data={
                        "project_id": project.id,
                        "execution_id": agent_execution.id,  # Handover 0457: Unique row ID for frontend Map key
                        "agent_id": agent_id,
                        "job_id": job_id,
                        "agent_display_name": "orchestrator",
                        "agent_name": "orchestrator",
                        "status": "waiting",
                        "fixture": True,  # Indicates this is a fixture, not from staging
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    },
                )
                self._logger.info(f"[ORCHESTRATOR FIXTURE] Broadcast agent:created for {job_id}")
            except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                self._logger.warning(f"[ORCHESTRATOR FIXTURE] WebSocket broadcast failed: {ws_error}")

        return {
            "job_id": job_id,
            "agent_id": agent_id,
        }

    async def deactivate_project(
        self,
        project_id: str,
        tenant_key: str | None = None,
        reason: str | None = None,
        websocket_manager: Any | None = None,
    ) -> Project:
        """
        Deactivate an active project.

        State Transition: active → inactive

        Args:
            project_id: Project UUID
            tenant_key: Optional tenant key (uses current tenant if not provided)
            reason: Optional reason for deactivation (stored in meta_data)
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Project: The deactivated project instance

        Raises:
            ResourceNotFoundError: Project not found
            ProjectStateError: Cannot deactivate project with current status

        Example:
            >>> project = await service.deactivate_project(
            ...     "abc-123",
            ...     reason="Taking a break"
            ... )
            >>> assert project.status == "inactive"
        """
        resolved_tenant = tenant_key or self.tenant_manager.get_current_tenant()
        async with self._get_session() as session:
            # Fetch project
            result = await session.execute(
                select(Project).where(and_(Project.id == project_id, Project.tenant_key == resolved_tenant))
            )
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(
                    message="Project not found or access denied",
                    context={"project_id": project_id, "tenant_key": resolved_tenant},
                )

            # Validate state
            if project.status != "active":
                raise ProjectStateError(
                    message=f"Cannot deactivate project with status '{project.status}'",
                    context={"project_id": project_id, "current_status": project.status},
                )

            # Deactivate project
            project.status = "inactive"
            project.updated_at = datetime.now(timezone.utc)

            # Store reason if provided
            if reason:
                if not project.meta_data:
                    project.meta_data = {}
                project.meta_data["deactivation_reason"] = reason

            await session.commit()
            await session.refresh(project)

            self._logger.info(f"Deactivated project {project_id}")

            # Broadcast WebSocket event
            ws_mgr = websocket_manager or self._websocket_manager
            if ws_mgr:
                try:
                    await ws_mgr.broadcast_project_update(
                        project_id=project.id,
                        update_type="status_changed",
                        project_data=_build_ws_project_data(project),
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                    self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

            return project

    async def cancel_staging(self, project_id: str, websocket_manager: Any | None = None) -> ProjectData:
        """
        Cancel a project in staging state.

        State Transition: staging → cancelled

        Similar to cancel_project() but specifically for staging state.
        Cleans up any pending orchestrator jobs.

        Args:
            project_id: Project UUID
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Project data dictionary

        Raises:
            ResourceNotFoundError: Project not found
            ProjectStateError: Cannot cancel staging for project with current status

        Example:
            >>> result = await service.cancel_staging("abc-123")
        """
        async with self._get_session() as session:
            # Fetch project
            result = await session.execute(
                select(Project).where(
                    and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                )
            )
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(message="Project not found", context={"project_id": project_id})

            # Validate state
            if project.status != "staging":
                raise ProjectStateError(
                    message=f"Cannot cancel staging for project with status '{project.status}'",
                    context={"project_id": project_id, "current_status": project.status},
                )

            # Cancel project
            project.status = "cancelled"
            project.completed_at = datetime.now(timezone.utc)  # Using completed_at for cancelled_at
            project.updated_at = datetime.now(timezone.utc)

            await session.commit()
            await session.refresh(project)

            self._logger.info(f"Cancelled staging for project {project_id}")

            # Broadcast WebSocket event
            if websocket_manager:
                try:
                    await websocket_manager.broadcast_project_update(
                        project_id=project.id,
                        update_type="cancelled",
                        project_data=_build_ws_project_data(project),
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                    self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

            return ProjectData(
                id=project.id,
                name=project.name,
                status=project.status,
                mission=project.mission,
                description=project.description,
                meta_data=project.meta_data or {},
                created_at=project.created_at.isoformat() if project.created_at else None,
                updated_at=project.updated_at.isoformat() if project.updated_at else None,
                activated_at=project.activated_at.isoformat() if project.activated_at else None,
                completed_at=project.completed_at.isoformat() if project.completed_at else None,
                product_id=project.product_id,
            )

    async def get_project_summary(self, project_id: str) -> ProjectSummaryResult:
        """
        Generate project summary with metrics and status.

        Returns comprehensive project overview including job statistics,
        completion metrics, and activity timestamps for dashboard display.

        Args:
            project_id: Project UUID

        Returns:
            ProjectSummaryResponse data:
            - Basic project info (id, name, status, mission)
            - Agent job counts (pending/active/completed/failed)
            - Mission completion percentage
            - Timestamps (created, activated, last activity)
            - Product context (id, name)

        Raises:
            ResourceNotFoundError: Project not found

        Example:
            >>> result = await service.get_project_summary("abc-123")
            >>> print(result["completion_percentage"])  # 75.0
        """
        async with self._get_session() as session:
            # Fetch project with product eager loading
            result = await session.execute(
                select(Project).where(
                    and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                )
            )
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(message="Project not found", context={"project_id": project_id})

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
            job_counts = dict(job_counts_raw)

            total_jobs = sum(job_counts.values())
            completed_jobs = job_counts.get("complete", 0)
            blocked_jobs = job_counts.get("blocked", 0)
            active_jobs = job_counts.get("working", 0)
            pending_jobs = job_counts.get("waiting", 0)

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
            return ProjectSummaryResult(
                id=project.id,
                name=project.name,
                status=project.status,
                mission=project.mission,
                total_jobs=total_jobs,
                completed_jobs=completed_jobs,
                blocked_jobs=blocked_jobs,
                active_jobs=active_jobs,
                pending_jobs=pending_jobs,
                completion_percentage=completion_percentage,
                created_at=project.created_at.isoformat() if project.created_at else None,
                activated_at=project.activated_at.isoformat() if project.activated_at else None,
                last_activity_at=last_activity_at.isoformat() if last_activity_at else None,
                product_id=project.product_id or "",
                product_name=product_name,
            )

    async def get_closeout_data(self, project_id: str, db_session: Any | None = None) -> CloseoutData:
        """
        Generate dynamic closeout checklist and prompt for project completion.

        Called by GET /api/projects/{project_id}/closeout.

        Returns:
            ProjectCloseoutDataResponse payload.

        Raises:
            ResourceNotFoundError: Project not found or access denied
        """
        tenant_key = self.tenant_manager.get_current_tenant()

        if db_session:
            return await self._build_closeout_data(project_id, tenant_key, db_session)

        async with self._get_session() as session:
            return await self._build_closeout_data(project_id, tenant_key, session)

    async def can_close_project(
        self, project_id: str, tenant_key: str | None = None, db_session: Any | None = None
    ) -> CanCloseResult:
        """
        Determine whether a project can be closed based on agent status.

        Returns:
            Can-close response data

        Raises:
            ValidationError: Tenant context missing
            ResourceNotFoundError: Project not found or access denied
        """
        tenant_key = tenant_key or self.tenant_manager.get_current_tenant()

        if not tenant_key:
            raise ValidationError(message="Tenant context missing", context={"project_id": project_id})

        if db_session:
            return await self._build_can_close_response(project_id, tenant_key, db_session)

        async with self._get_session() as session:
            return await self._build_can_close_response(project_id, tenant_key, session)

    async def generate_closeout_prompt(
        self, project_id: str, tenant_key: str | None = None, db_session: Any | None = None
    ) -> CloseoutPromptResult:
        """
        Generate closeout prompt with checklist and agent summary.

        Returns:
            Closeout prompt data

        Raises:
            ValidationError: Tenant context missing
            ResourceNotFoundError: Project not found or access denied
        """
        tenant_key = tenant_key or self.tenant_manager.get_current_tenant()

        if not tenant_key:
            raise ValidationError(message="Tenant context missing", context={"project_id": project_id})

        if db_session:
            return await self._build_closeout_prompt(project_id, tenant_key, db_session)

        async with self._get_session() as session:
            return await self._build_closeout_prompt(project_id, tenant_key, session)

    async def _build_closeout_data(self, project_id: str, tenant_key: str, session: Any) -> CloseoutData:
        """
        Internal helper to build closeout data using provided session.

        Raises:
            ResourceNotFoundError: Project not found or access denied
        """
        project = await self._get_project_for_tenant(project_id, tenant_key, session)

        if not project:
            raise ResourceNotFoundError(
                message="Project not found or access denied",
                context={"project_id": project_id, "tenant_key": tenant_key},
            )

        status_counts = await self._aggregate_agent_statuses(project_id, tenant_key, session)
        total_agents = status_counts["total"]
        completed_agents = status_counts["completed"]
        blocked_agents = status_counts["blocked"]
        silent_agents = status_counts.get("silent", 0)
        active_agents = status_counts["active"]

        all_agents_complete = total_agents > 0 and completed_agents == total_agents and active_agents == 0
        has_blocked_agents = blocked_agents > 0

        return CloseoutData(
            project_id=project_id,
            project_name=project.name,
            agent_count=total_agents,
            completed_agents=completed_agents,
            blocked_agents=blocked_agents,
            silent_agents=silent_agents,
            all_agents_complete=all_agents_complete,
            has_blocked_agents=has_blocked_agents,
        )

    async def _build_can_close_response(self, project_id: str, tenant_key: str, session: Any) -> CanCloseResult:
        """
        Build readiness response for can-close endpoint.

        Raises:
            ResourceNotFoundError: Project not found or access denied
        """
        project = await self._get_project_for_tenant(project_id, tenant_key, session)

        if not project:
            raise ResourceNotFoundError(
                message="Project not found or access denied",
                context={"project_id": project_id, "tenant_key": tenant_key},
            )

        status_counts = await self._aggregate_agent_statuses(project_id, tenant_key, session)
        all_agents_finished = status_counts["total"] > 0 and status_counts["active"] == 0

        summary = None
        if all_agents_finished:
            summary_parts = [f"{status_counts['completed']} successful agents"]
            summary_parts.append(f"{status_counts['blocked']} blocked agents")
            summary_parts.append(f"{status_counts.get('silent', 0)} silent agents")
            summary = ", ".join(summary_parts)

        return CanCloseResult(
            can_close=all_agents_finished,
            summary=summary,
            all_agents_finished=all_agents_finished,
            agent_statuses={
                "complete": status_counts["completed"],
                "blocked": status_counts["blocked"],
                "silent": status_counts.get("silent", 0),
                "active": status_counts["active"],
            },
        )

    async def _build_closeout_prompt(self, project_id: str, tenant_key: str, session: Any) -> CloseoutPromptResult:
        """
        Build a bash closeout prompt and checklist for the project.

        Raises:
            ResourceNotFoundError: Project not found or access denied
        """
        project = await self._get_project_for_tenant(project_id, tenant_key, session)

        if not project:
            raise ResourceNotFoundError(
                message="Project not found or access denied",
                context={"project_id": project_id, "tenant_key": tenant_key},
            )

        status_counts = await self._aggregate_agent_statuses(project_id, tenant_key, session)
        agent_summary = (
            f"{status_counts['completed']} completed, "
            f"{status_counts['blocked']} blocked, "
            f"{status_counts.get('silent', 0)} silent, "
            f"{status_counts['active']} active"
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

        return CloseoutPromptResult(
            prompt=prompt,
            checklist=checklist,
            project_name=project.name,
            agent_summary=agent_summary,
        )

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
        job_counts = dict(job_counts_result.all())

        total_agents = sum(job_counts.values())
        completed_agents = job_counts.get("complete", 0)
        blocked_agents = job_counts.get("blocked", 0)
        silent_agents = job_counts.get("silent", 0)
        # Valid statuses after 0491: waiting, working, blocked, complete, silent, decommissioned
        active_statuses = {"working", "waiting", "blocked", "silent"}
        active_agents = sum(job_counts.get(status, 0) for status in active_statuses)

        return {
            "job_counts": job_counts,
            "total": total_agents,
            "completed": completed_agents,
            "blocked": blocked_agents,
            "silent": silent_agents,
            "active": active_agents,
        }

    async def _get_project_for_tenant(self, project_id: str, tenant_key: str, session: Any) -> Project | None:
        """
        Fetch a project scoped to tenant for closeout operations.
        """
        result = await session.execute(
            select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
        )
        return result.scalar_one_or_none()

    async def update_project(
        self, project_id: str, updates: dict[str, Any], websocket_manager: Any | None = None
    ) -> ProjectData:
        """
        Update project fields.

        Updates all provided fields (name, description, mission).
        This is the fixed version that handles multiple fields, not just mission.

        Args:
            project_id: Project UUID
            updates: Dict of field updates (allowed: name, description, mission, config_data)
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Updated project data dictionary

        Raises:
            ResourceNotFoundError: Project not found
            ProjectStateError: Cannot change execution mode after staging

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
        async with self._get_session() as session:
            # Fetch project
            # Handover 0440a: Eagerly load project_type for taxonomy_alias property
            result = await session.execute(
                select(Project)
                .options(selectinload(Project.project_type))
                .where(and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant()))
            )
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(message="Project not found", context={"project_id": project_id})

            # Handover 0343: Lock execution_mode after staging (mission exists)
            if "execution_mode" in updates and project.mission and project.mission.strip():
                raise ProjectStateError(
                    message="Cannot change execution mode after staging. Mission has been generated.",
                    context={"project_id": project_id},
                )

            # Update allowed fields (Handover 0260: Added execution_mode)
            # Handover 0412: Added status, completed_at for archive endpoint
            # Handover 0440a: Added project_type_id, series_number, subseries for taxonomy
            allowed_fields = {
                "name",
                "description",
                "mission",
                "execution_mode",
                "status",
                "completed_at",
                "project_type_id",
                "series_number",
                "subseries",
            }
            for field, value in updates.items():
                if field in allowed_fields:
                    setattr(project, field, value)

            project.updated_at = datetime.now(timezone.utc)

            try:
                await session.commit()
            except IntegrityError as e:
                if "uq_project_taxonomy" in str(e):
                    raise AlreadyExistsError(
                        message="Taxonomy combination already in use. Please choose a different series number or suffix.",
                        context={"project_id": project_id},
                    ) from e
                raise
            await session.refresh(project)

            # Reload project_type relationship (expired after commit)
            if project.project_type_id:
                result = await session.execute(
                    select(Project).options(selectinload(Project.project_type)).where(Project.id == project.id)
                )
                project = result.scalar_one()

            self._logger.info(f"Updated project {project_id}")

            # Broadcast WebSocket event
            if websocket_manager:
                try:
                    await websocket_manager.broadcast_project_update(
                        project_id=project.id,
                        update_type="updated",
                        project_data=_build_ws_project_data(project),
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                    self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

            return ProjectData(
                id=project.id,
                name=project.name,
                status=project.status,
                mission=project.mission,
                description=project.description,
                execution_mode=project.execution_mode,
                meta_data=project.meta_data or {},
                created_at=project.created_at.isoformat() if project.created_at else None,
                updated_at=project.updated_at.isoformat() if project.updated_at else None,
                activated_at=project.activated_at.isoformat() if project.activated_at else None,
                completed_at=project.completed_at.isoformat() if project.completed_at else None,
                product_id=project.product_id,
                # Handover 0440a: Taxonomy fields
                project_type_id=project.project_type_id,
                project_type=project.project_type,
                series_number=project.series_number,
                subseries=project.subseries,
                taxonomy_alias=project.taxonomy_alias,
            )

    async def launch_project(
        self,
        project_id: str,
        user_id: str | None = None,
        launch_config: dict[str, Any | None] = None,
        websocket_manager: Any | None = None,
    ) -> ProjectLaunchResult:
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
            ProjectLaunchResponse data:
            - project_id: Project UUID
            - orchestrator_job_id: Created orchestrator job UUID
            - launch_prompt: Thin-client prompt for starting orchestrator
            - status: Project status after launch

        Raises:
            ResourceNotFoundError: Project not found
            ProjectStateError: Cannot activate project (propagated from activate_project)

        Example:
            >>> result = await service.launch_project("abc-123", user_id="user-456")
            >>> print(result["orchestrator_job_id"])
        """
        async with self._get_session() as session:
            # Fetch project
            result = await session.execute(
                select(Project).where(
                    and_(Project.id == project_id, Project.tenant_key == self.tenant_manager.get_current_tenant())
                )
            )
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(message="Project not found", context={"project_id": project_id})

            # Activate project if not already active (raises exceptions on error)
            if project.status != "active":
                await self.activate_project(project_id, websocket_manager=websocket_manager)

            # Fetch user field_priority_config and depth_config if user_id provided
            field_priorities = {}
            depth_config = None

            if user_id:
                from src.giljo_mcp.models import User

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

            # FIX 3 (Handover 0485): Check for existing orchestrator BEFORE creating new one
            # This prevents duplicate orchestrators when launch_project() is called multiple times
            tenant_key = self.tenant_manager.get_current_tenant()

            existing_orch_stmt = (
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    AgentJob.project_id == project_id,
                    AgentExecution.agent_display_name == "orchestrator",
                    AgentExecution.tenant_key == tenant_key,
                    ~AgentExecution.status.in_(["decommissioned"]),  # Handover 0491: Simplified statuses
                )
                .order_by(AgentExecution.started_at.desc())
            )
            existing_orch_result = await session.execute(existing_orch_stmt)
            existing_orchestrator = existing_orch_result.scalars().first()

            if existing_orchestrator:
                # Reuse existing orchestrator instead of creating new one
                self._logger.info(
                    f"[LAUNCH] Reusing existing orchestrator {existing_orchestrator.job_id} "
                    f"for project {project_id} (status={existing_orchestrator.status})"
                )

                # Return existing orchestrator info (do NOT create new one)
                return ProjectLaunchResult(
                    project_id=project.id,
                    orchestrator_job_id=existing_orchestrator.job_id,
                    launch_prompt=f"""Launch orchestrator for project: {project.name}

Project ID: {project.id}
Mission: {project.mission}
Orchestrator Job ID: {existing_orchestrator.job_id}

This is a thin-client launch. Use the get_orchestrator_instructions() MCP tool to fetch full mission details.
""",
                    status=project.status,
                    staging_status=project.staging_status,
                )

            # No existing orchestrator found - create new one

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
                status="waiting",
                progress=0,
                health_status="unknown",
            )
            session.add(agent_execution)

            # Set staging_status to 'staged' when orchestrator is launched
            project.staging_status = "staged"
            project.updated_at = datetime.now(timezone.utc)

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
                    project_data = _build_ws_project_data(project)
                    project_data["staging_status"] = project.staging_status
                    project_data["orchestrator_job_id"] = orchestrator_job_id
                    await websocket_manager.broadcast_project_update(
                        project_id=project.id,
                        update_type="launched",
                        project_data=project_data,
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                    self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

            return ProjectLaunchResult(
                project_id=project.id,
                orchestrator_job_id=orchestrator_job_id,
                launch_prompt=launch_prompt,
                status=project.status,
                staging_status=project.staging_status,
            )

    async def restore_project(self, project_id: str, tenant_key: str) -> OperationResult:
        """
        Restore a completed, cancelled, or soft-deleted project to inactive status.

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Success message dictionary

        Raises:
            ResourceNotFoundError: Project not found or access denied

        Example:
            >>> result = await service.restore_project("abc-123", "tenant-key-456")
        """
        async with self._get_session() as session:
            # TENANT ISOLATION: Filter by both project_id AND tenant_key
            result = await session.execute(
                update(Project)
                .where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                .values(
                    status="inactive",
                    completed_at=None,
                    deleted_at=None,
                    updated_at=datetime.now(timezone.utc),
                )
            )

            if result.rowcount == 0:
                raise ResourceNotFoundError(
                    message="Project not found or access denied",
                    context={"project_id": project_id, "tenant_key": tenant_key},
                )

            await session.commit()

            self._logger.info(f"Restored project {project_id}")

            return OperationResult(
                message=f"Project {project_id} restored successfully",
            )

    # ============================================================================
    # State & Metrics
    # ============================================================================

    async def switch_project(self, project_id: str, tenant_key: str | None = None) -> ProjectSwitchResult:
        """
        Switch to a different project context.

        This updates the tenant context and creates/activates a session
        for the target project.

        Args:
            project_id: Project UUID to switch to
            tenant_key: Tenant key for multi-tenant isolation (uses context if not provided)

        Returns:
            Project details dictionary

        Raises:
            ValidationError: No tenant context available
            ResourceNotFoundError: Project not found or access denied

        Example:
            >>> result = await service.switch_project("abc-123", tenant_key="tenant-abc")
            >>> print(f"Switched to: {result['name']}")
        """
        async with self._get_session() as db_session:
            # TENANT ISOLATION: Require tenant_key, fall back to context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                raise ValidationError(
                    message="No tenant context available",
                    context={"operation": "switch_project", "project_id": project_id},
                )

            result = await db_session.execute(
                select(Project).where(and_(Project.tenant_key == tenant_key, Project.id == project_id))
            )
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(
                    message="Project not found or access denied",
                    context={"project_id": project_id, "tenant_key": tenant_key},
                )

            # Set tenant context
            self.tenant_manager.set_current_tenant(project.tenant_key)

            # NOTE: Session tracking removed (Handover 0423 - dead code cleanup)

            self._logger.info(f"Switched to project '{project.name}' (ID: {project_id})")

            return ProjectSwitchResult(
                project_id=str(project.id),
                name=project.name,
                mission=project.mission,
                tenant_key=project.tenant_key,
            )

    # ============================================================================
    # Maintenance & Cleanup Methods
    # ============================================================================

    async def nuclear_delete_project(
        self, project_id: str, websocket_manager: Any | None = None
    ) -> NuclearDeleteResult:
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
            Deletion details dictionary:
            - message: str
            - deleted_counts: dict with counts of each deleted entity type
            - project_name: str (name of deleted project)

        Raises:
            ValidationError: No tenant context available
            ResourceNotFoundError: Project not found or access denied

        Example:
            >>> result = await service.nuclear_delete_project("abc-123")
            >>> print(result["deleted_counts"])
            {"agents": 5, "tasks": 12, "messages": 48, ...}
        """
        # Get current tenant from context
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(message="No tenant context available", context={"project_id": project_id})

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
                raise ResourceNotFoundError(
                    message="Project not found or access denied",
                    context={"project_id": project_id, "tenant_key": tenant_key},
                )

            project_name = project.name

            # Deactivate project if it's active (to avoid constraint issues)
            if project.status == "active":
                project.status = "inactive"
                project.updated_at = datetime.now(timezone.utc)
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
                "visions": 0,  # NOTE: Vision model deprecated (Handover 0728)
            }

            # Import additional models needed for deletion
            from src.giljo_mcp.models.context import ContextIndex, LargeDocumentIndex
            # NOTE: Session import removed (Handover 0423 - dead code cleanup)
            # NOTE: Vision import removed (Handover 0728 - Vision model deprecated)

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

            # NOTE: Session deletion removed (Handover 0423 - dead code cleanup)
            # NOTE: Vision deletion removed (Handover 0728 - Vision model deprecated)

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
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                    self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

            return NuclearDeleteResult(
                message=f"Project '{project_name}' permanently deleted",
                deleted_counts=deleted_counts,
                project_name=project_name,
            )

    async def _purge_project_records(self, session: AsyncSession, project: Project) -> dict[str, Any]:
        """Cascade delete a soft-deleted project and its child records."""
        project_info = {
            "id": project.id,
            "name": project.name,
            "tenant_key": project.tenant_key,
            "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
        }

        # Mark 360 memory entries as deleted by user (preserve historical reference)
        # Uses ProductMemoryRepository for table-based operations (Handover 0390c)
        if project.product_id:
            from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

            repo = ProductMemoryRepository()
            deleted_count = await repo.mark_entries_deleted(
                session=session,
                project_id=project.id,
                tenant_key=project.tenant_key,
            )
            if deleted_count > 0:
                self._logger.info(f"Marked {deleted_count} memory entries as deleted for project {project.id}")

        # TENANT ISOLATION: All cascade deletes filter by tenant_key
        tenant_key = project.tenant_key

        # Delete agent jobs (migrated to AgentJob - Handover 0367a)
        agent_job_stmt = select(AgentJob).where(
            and_(AgentJob.project_id == project.id, AgentJob.tenant_key == tenant_key)
        )
        agent_jobs = (await session.execute(agent_job_stmt)).scalars().all()
        for job in agent_jobs:
            await session.delete(job)

        task_stmt = select(Task).where(and_(Task.project_id == project.id, Task.tenant_key == tenant_key))
        tasks = (await session.execute(task_stmt)).scalars().all()
        for task in tasks:
            await session.delete(task)

        message_stmt = select(Message).where(and_(Message.project_id == project.id, Message.tenant_key == tenant_key))
        messages = (await session.execute(message_stmt)).scalars().all()
        for message in messages:
            await session.delete(message)

        await session.delete(project)
        return project_info

    async def delete_project(self, project_id: str) -> SoftDeleteResult:
        """
        Soft delete a project.

        Sets status='deleted' and deleted_at timestamp for the current tenant's project.
        Actual purge is handled separately by purge_expired_deleted_projects().

        Args:
            project_id: Project UUID

        Returns:
            Deletion result dictionary with deleted_at timestamp and cancelled_jobs count

        Raises:
            ValidationError: No tenant context available
            ResourceNotFoundError: Project not found or already deleted
        """
        # Get current tenant from context
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(message="No tenant context available", context={"project_id": project_id})

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
                raise ResourceNotFoundError(
                    message="Project not found or already deleted",
                    context={"project_id": project_id, "tenant_key": tenant_key},
                )

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
                        AgentExecution.status.notin_(["complete", "decommissioned"]),
                    )
                )
            )
            executions_result = await session.execute(executions_stmt)
            executions = executions_result.scalars().all()

            decommissioned_jobs_count = 0
            for execution in executions:
                execution.status = "decommissioned"
                execution.completed_at = now
                decommissioned_jobs_count += 1

            await session.commit()

            self._logger.info(
                f"Soft deleted project {project_id} for tenant {tenant_key} "
                f"at {project.deleted_at.isoformat() if project.deleted_at else 'unknown time'}. "
                f"Decommissioned {decommissioned_jobs_count} agent jobs."
            )

            return SoftDeleteResult(
                message="Project deleted successfully",
                deleted_at=project.deleted_at.isoformat() if project.deleted_at else None,
                decommissioned_jobs=decommissioned_jobs_count,
            )

    async def purge_deleted_project(self, project_id: str) -> ProjectPurgeResult:
        """
        Nuclear delete a specific soft-deleted project for the current tenant.

        Called when user clicks trash icon next to a deleted project.
        Uses nuclear_delete_project for complete immediate removal.

        Returns:
            Purge result dictionary with purged_count and project details

        Raises:
            ValidationError: No tenant context available (propagated from nuclear_delete_project)
            ResourceNotFoundError: Project not found or access denied (propagated from nuclear_delete_project)
        """
        # Simply delegate to nuclear_delete_project which handles everything
        result = await self.nuclear_delete_project(project_id)

        # Format response to match expected purge response structure
        project_info = {
            "id": project_id,
            "name": result.project_name,
            "tenant_key": "",
            "deleted_at": datetime.now(timezone.utc).isoformat(),
        }

        self._logger.info("[Nuclear Purge] Manually purged project %s via trash icon", project_id)

        return ProjectPurgeResult(purged_count=1, projects=[project_info])

    async def purge_all_deleted_projects(self) -> ProjectPurgeResult:
        """
        Nuclear delete all soft-deleted projects for the current tenant.

        Uses nuclear_delete_project for each project to ensure complete removal.
        Called when user clicks "Delete All" button in deleted projects modal.

        Returns:
            Purge result dictionary with purged_count and project details list

        Raises:
            ValidationError: No tenant context available
        """
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(message="No tenant context available", context={})

        async with self._get_session() as session:
            stmt = select(Project).where(
                and_(Project.tenant_key == tenant_key, Project.status == "deleted", Project.deleted_at.isnot(None))
            )
            result = await session.execute(stmt)
            deleted_projects = result.scalars().all()

            if not deleted_projects:
                return ProjectPurgeResult(purged_count=0, projects=[])

        # Use nuclear delete for each project
        purged_projects = []
        for project in deleted_projects:
            try:
                await self.nuclear_delete_project(project.id)
                purged_projects.append(
                    {
                        "id": project.id,
                        "name": project.name,
                        "tenant_key": project.tenant_key,
                        "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
                    }
                )
            except Exception:  # noqa: PERF203 - Nuclear delete resilience: continue on failures
                self._logger.exception("Failed to nuclear delete project {project.id}")

        self._logger.info(
            "[Nuclear Purge] Permanently deleted %s project(s) for tenant %s",
            len(purged_projects),
            tenant_key,
        )

        return ProjectPurgeResult(purged_count=len(purged_projects), projects=purged_projects)

    async def purge_expired_deleted_projects(self, days_before_purge: int = 10) -> ProjectPurgeResult:
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
            ProjectPurgeResult: Pydantic model with:
                - purged_count: int - Number of projects purged
                - projects: list[dict] - Details of purged projects

        Raises:
            BaseGiljoError: Database not available

        Example:
            >>> result = await service.purge_expired_deleted_projects()
            >>> print(f"Nuclear purged {result.purged_count} expired projects")
        """
        from datetime import timedelta, timezone

        if not self.db_manager:
            self._logger.error("[Nuclear Purge] Cannot purge - database manager not available")
            raise BaseGiljoError(message="Database not available", context={})

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
                return ProjectPurgeResult(purged_count=0, projects=[])

        # Use nuclear delete for each expired project
        purged_projects = []
        for project in expired_projects:
            try:
                await self.nuclear_delete_project(project.id)
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
            except Exception:  # noqa: PERF203 - Nuclear delete resilience: continue on failures
                self._logger.exception("Failed to nuclear delete expired project {project.id}")

        self._logger.info(f"[Nuclear Purge] Successfully purged {len(purged_projects)} expired deleted projects")

        return ProjectPurgeResult(purged_count=len(purged_projects), projects=purged_projects)

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
        self._logger.info(f"[WEBSOCKET DEBUG] About to broadcast mission_updated for project {project_id}")

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
