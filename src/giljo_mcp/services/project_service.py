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
from src.giljo_mcp.models.projects import Project, ProjectType
from src.giljo_mcp.models.tasks import Message
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

        # Facade sub-services (Handover 0769: ProjectService split)
        from src.giljo_mcp.services.project_closeout_service import ProjectCloseoutService
        from src.giljo_mcp.services.project_deletion_service import ProjectDeletionService
        from src.giljo_mcp.services.project_lifecycle_service import ProjectLifecycleService

        self._lifecycle = ProjectLifecycleService(db_manager, tenant_manager, test_session, websocket_manager)
        self._closeout = ProjectCloseoutService(db_manager, tenant_manager, test_session, websocket_manager)
        self._deletion = ProjectDeletionService(db_manager, tenant_manager, test_session, websocket_manager)

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

                # Validate taxonomy format: series 1-9999, subseries single letter
                if series_number is not None and (series_number < 1 or series_number > 9999):
                    raise ValidationError(
                        message="Series number must be between 1 and 9999.",
                        context={"series_number": series_number},
                    )
                if subseries is not None and (len(subseries) != 1 or not subseries.isalpha()):
                    raise ValidationError(
                        message="Subseries must be a single letter (a-z).",
                        context={"subseries": subseries},
                    )

                # Auto-assign series_number when not provided (Handover 0837a)
                # This prevents uq_project_taxonomy violations for MCP callers
                # that don't supply taxonomy fields.
                if series_number is None:
                    # Lock matching rows to prevent concurrent duplicates,
                    # then compute max. FOR UPDATE can't be used with aggregates.
                    # Include deleted rows: uq_project_taxonomy doesn't exclude them.
                    lock_query = select(Project.id).where(
                        Project.tenant_key == tenant_key,
                    )
                    if project_type_id:
                        lock_query = lock_query.where(Project.project_type_id == project_type_id)
                    else:
                        lock_query = lock_query.where(Project.project_type_id.is_(None))
                    await session.execute(lock_query.with_for_update())

                    max_query = select(func.coalesce(func.max(Project.series_number), 0) + 1).where(
                        Project.tenant_key == tenant_key,
                    )
                    if project_type_id:
                        max_query = max_query.where(Project.project_type_id == project_type_id)
                    else:
                        max_query = max_query.where(Project.project_type_id.is_(None))
                    result = await session.execute(max_query)
                    series_number = result.scalar_one()

                # Application-level duplicate check before insert
                else:
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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to create project")
            raise BaseGiljoError(
                message=f"Failed to create project: {e!s}", context={"name": name, "tenant_key": tenant_key}
            ) from e

    async def get_project_type_by_label(self, label: str, tenant_key: str) -> ProjectType | None:
        """Resolve a project type by its human-readable label (case-insensitive).

        Args:
            label: Human-readable type label (e.g. 'Frontend', 'backend')
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            ProjectType if found, None otherwise
        """
        async with self._get_session() as session:
            result = await session.execute(
                select(ProjectType).where(
                    ProjectType.tenant_key == tenant_key,
                    func.lower(ProjectType.label) == label.lower(),
                )
            )
            return result.scalar_one_or_none()

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
                    cancellation_reason=project.cancellation_reason,
                    deactivation_reason=project.deactivation_reason,
                    early_termination=project.early_termination,
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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to list projects")
            raise BaseGiljoError(message=f"Failed to list projects: {e!s}", context={"tenant_key": tenant_key}) from e

    async def update_project_mission(
        self, project_id: str, mission: str, tenant_key: str | None = None
    ) -> ProjectMissionUpdateResult:
        """
        Update the mission field after orchestrator analysis.

        This method also broadcasts the mission update via in-process WebSocketManager
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

                # Handover 0425: Also set staging_status to 'staging' when mission is updated
                result = await session.execute(
                    update(Project)
                    .where(and_(Project.tenant_key == tenant_key, Project.id == project_id))
                    .values(mission=mission, staging_status="staging", updated_at=datetime.now(timezone.utc))
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

                # Broadcast mission update via WebSocketManager
                if project:
                    await self._broadcast_mission_update(project_id, mission, project.tenant_key)

                return ProjectMissionUpdateResult(
                    message="Mission updated successfully",
                    project_id=project_id,
                )

        except (ResourceNotFoundError, ValidationError):
            # Re-raise our custom exceptions
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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
        """Facade: delegates to ProjectLifecycleService."""
        return await self._lifecycle.complete_project(
            project_id, summary, key_outcomes, decisions_made, tenant_key, db_session
        )

    async def cancel_project(self, project_id: str, tenant_key: str, reason: str | None = None) -> None:
        """Facade: delegates to ProjectLifecycleService."""
        return await self._lifecycle.cancel_project(project_id, tenant_key, reason)

    async def close_out_project(self, project_id: str, tenant_key: str) -> ProjectCloseOutResult:
        """Facade: delegates to ProjectCloseoutService."""
        return await self._closeout.close_out_project(project_id, tenant_key)

    async def continue_working(self, project_id: str, tenant_key: str) -> ProjectResumeResult:
        """Facade: delegates to ProjectLifecycleService."""
        return await self._lifecycle.continue_working(project_id, tenant_key)

    async def activate_project(
        self,
        project_id: str,
        force: bool = False,
        websocket_manager: Any | None = None,
        tenant_key: str | None = None,
    ) -> Project:
        """Facade: delegates to ProjectLifecycleService."""
        return await self._lifecycle.activate_project(project_id, force, websocket_manager, tenant_key)

    async def deactivate_project(
        self,
        project_id: str,
        tenant_key: str | None = None,
        reason: str | None = None,
        websocket_manager: Any | None = None,
    ) -> Project:
        """Facade: delegates to ProjectLifecycleService."""
        return await self._lifecycle.deactivate_project(project_id, tenant_key, reason, websocket_manager)

    async def cancel_staging(self, project_id: str, websocket_manager: Any | None = None) -> ProjectData:
        """Facade: delegates to ProjectLifecycleService."""
        return await self._lifecycle.cancel_staging(project_id, websocket_manager)

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
        """Facade: delegates to ProjectCloseoutService."""
        return await self._closeout.get_closeout_data(project_id, db_session)

    async def can_close_project(
        self, project_id: str, tenant_key: str | None = None, db_session: Any | None = None
    ) -> CanCloseResult:
        """Facade: delegates to ProjectCloseoutService."""
        return await self._closeout.can_close_project(project_id, tenant_key, db_session)

    async def generate_closeout_prompt(
        self, project_id: str, tenant_key: str | None = None, db_session: Any | None = None
    ) -> CloseoutPromptResult:
        """Facade: delegates to ProjectCloseoutService."""
        return await self._closeout.generate_closeout_prompt(project_id, tenant_key, db_session)

    async def _get_project_for_tenant(self, project_id: str, tenant_key: str, session: Any) -> Project | None:
        """
        Fetch a project scoped to tenant for closeout operations.
        """
        result = await session.execute(
            select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
        )
        return result.scalar_one_or_none()

    def _apply_project_updates(self, project, updates: dict[str, Any]) -> None:
        """Apply validated field updates to a project model.

        Args:
            project: Project SQLAlchemy model instance
            updates: Dict of field name -> value to apply

        Raises:
            ProjectStateError: Cannot change execution mode after staging
        """
        # Handover 0343: Lock execution_mode after staging (mission exists)
        if "execution_mode" in updates and project.mission and project.mission.strip():
            raise ProjectStateError(
                message="Cannot change execution mode after staging. Mission has been generated.",
                context={"project_id": str(project.id)},
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

    @staticmethod
    def _build_project_data(project) -> ProjectData:
        """Build ProjectData response from a Project model instance."""
        return ProjectData(
            id=project.id,
            name=project.name,
            status=project.status,
            mission=project.mission,
            description=project.description,
            execution_mode=project.execution_mode,
            cancellation_reason=project.cancellation_reason,
            deactivation_reason=project.deactivation_reason,
            early_termination=project.early_termination,
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

            self._apply_project_updates(project, updates)

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

            return self._build_project_data(project)

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

            # Handover 0840d: Fetch user field toggles and depth from normalized tables/columns
            field_toggles = {}
            depth_config = None

            if user_id:
                from src.giljo_mcp.models.auth import User, UserFieldPriority

                user_stmt = select(User).where(
                    and_(User.id == user_id, User.tenant_key == self.tenant_manager.get_current_tenant())
                )
                user_result = await session.execute(user_stmt)
                user = user_result.scalar_one_or_none()

                if user:
                    # Build field_toggles from user_field_priorities table
                    prio_result = await session.execute(
                        select(UserFieldPriority).where(
                            and_(
                                UserFieldPriority.user_id == user_id,
                                UserFieldPriority.tenant_key == self.tenant_manager.get_current_tenant(),
                            )
                        )
                    )
                    rows = prio_result.scalars().all()
                    if rows:
                        from src.giljo_mcp.config.defaults import DEFAULT_CATEGORY_TOGGLES

                        field_toggles = dict(DEFAULT_CATEGORY_TOGGLES)
                        for row in rows:
                            field_toggles[row.category] = row.enabled
                        field_toggles["product_core"] = True
                        field_toggles["project_description"] = True

                    # Build depth_config from columns
                    depth_config = {
                        "vision_documents": user.depth_vision_documents,
                        "memory_last_n_projects": user.depth_memory_last_n,
                        "git_commits": user.depth_git_commits,
                        "agent_templates": user.depth_agent_templates,
                        "tech_stack_sections": user.depth_tech_stack_sections,
                        "architecture_depth": user.depth_architecture,
                    }

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
                    "field_toggles": field_toggles,
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

            # Set staging_status to 'staging' when orchestrator is launched
            project.staging_status = "staging"
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
        """Facade: delegates to ProjectDeletionService."""
        return await self._deletion.restore_project(project_id, tenant_key)

    # ============================================================================
    # Maintenance & Cleanup Methods (Facade)
    # ============================================================================

    async def nuclear_delete_project(
        self, project_id: str, websocket_manager: Any | None = None
    ) -> NuclearDeleteResult:
        """Facade: delegates to ProjectDeletionService."""
        return await self._deletion.nuclear_delete_project(project_id, websocket_manager)

    async def delete_project(self, project_id: str) -> SoftDeleteResult:
        """Facade: delegates to ProjectDeletionService."""
        return await self._deletion.delete_project(project_id)

    async def purge_all_deleted_projects(self) -> ProjectPurgeResult:
        """Facade: delegates to ProjectDeletionService."""
        return await self._deletion.purge_all_deleted_projects()

    async def purge_expired_deleted_projects(self, days_before_purge: int = 10) -> ProjectPurgeResult:
        """Facade: delegates to ProjectDeletionService."""
        return await self._deletion.purge_expired_deleted_projects(days_before_purge)

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
        except Exception as ws_error:  # Broad catch: WebSocket resilience, non-critical broadcast
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

        except Exception as ws_error:  # Broad catch: WebSocket resilience, non-critical broadcast
            self._logger.error(
                f"[WEBSOCKET ERROR] Failed to broadcast project:mission_updated: {ws_error}",
                exc_info=True,
            )
