# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import (
    AlreadyExistsError,
    BaseGiljoError,
    ProjectStateError,
    ResourceNotFoundError,
    ValidationError,
)

# Import Pattern: Use modular imports from models package (Post-0128a)
# See models/__init__.py for migration guidance
from giljo_mcp.models.projects import Project, ProjectType
from giljo_mcp.repositories.project_repository import ProjectRepository
from giljo_mcp.schemas.service_responses import (
    ProjectCompleteResult,
    ProjectData,
    ProjectDetail,
    ProjectLaunchResult,
    ProjectListItem,
    ProjectMissionUpdateResult,
)
from giljo_mcp.services.project_helpers import _build_ws_project_data
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)

# Statuses that indicate a project is closed and must not be modified.
IMMUTABLE_PROJECT_STATUSES: frozenset[str] = frozenset({"completed", "cancelled"})

# Fields that are always writable regardless of project status.
# These are UI/display preferences (archive, visibility) — not project data.
ALWAYS_MUTABLE_FIELDS: frozenset[str] = frozenset({"hidden"})


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
        self._repo = ProjectRepository()

        # Facade sub-services (Handover 0769: ProjectService split, 0950i: launch extraction,
        #                      0950n: summary extraction)
        from giljo_mcp.services.project_closeout_service import ProjectCloseoutService
        from giljo_mcp.services.project_deletion_service import ProjectDeletionService
        from giljo_mcp.services.project_launch_service import ProjectLaunchService
        from giljo_mcp.services.project_lifecycle_service import ProjectLifecycleService
        from giljo_mcp.services.project_summary_service import ProjectSummaryService

        # Sprint 002f: Public sub-services for direct caller access (collapsed pass-throughs)
        self.lifecycle = ProjectLifecycleService(db_manager, tenant_manager, test_session, websocket_manager)
        self.closeout = ProjectCloseoutService(db_manager, tenant_manager, test_session, websocket_manager)
        self.deletion = ProjectDeletionService(db_manager, tenant_manager, test_session, websocket_manager)
        self.launch = ProjectLaunchService(db_manager, tenant_manager, test_session, websocket_manager)
        self.summary = ProjectSummaryService(db_manager, tenant_manager, test_session, websocket_manager)

        from giljo_mcp.services.project_query_service import ProjectQueryService

        self.query = ProjectQueryService(db_manager, tenant_manager, test_session)

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
                    await self._repo.lock_rows_for_series(session, tenant_key, product_id, project_type_id)
                    series_number = await self._repo.get_next_series_number(
                        session, tenant_key, product_id, project_type_id
                    )

                # Application-level duplicate check before insert
                else:
                    is_dup = await self._repo.check_duplicate_taxonomy(
                        session, tenant_key, product_id, project_type_id, series_number, subseries
                    )
                    if is_dup:
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

                await self._repo.add(session, project)
                await self._repo.commit(session)
                await self._repo.refresh(session, project)

                # Handover 0440a: Eagerly load project_type relationship for taxonomy_alias
                if project.project_type_id:
                    project = await self._repo.get_with_project_type(session, project.id)

                self._logger.info(f"Created project {project.id} with status '{status}' and tenant key {tenant_key}")

                # Broadcast WebSocket event so all browsers refresh the project list
                if self._websocket_manager:
                    try:
                        await self._websocket_manager.broadcast_project_update(
                            project_id=project.id,
                            update_type="created",
                            project_data=_build_ws_project_data(project),
                            tenant_key=tenant_key,
                        )
                    except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                        self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

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
        except BaseGiljoError:
            # Re-raise domain errors (AlreadyExistsError, ValidationError, etc.) unchanged.
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to create project")
            raise BaseGiljoError(
                message=f"Failed to create project: {e!s}", context={"name": name, "tenant_key": tenant_key}
            ) from e

    async def get_project_type_by_label(self, label: str, tenant_key: str) -> ProjectType | None:
        """Resolve a project type by label or abbreviation (case-insensitive).

        Tries label first, then abbreviation. This allows agents to use either
        "MCP test" (label) or "TST" (abbreviation) when creating projects.

        Args:
            label: Human-readable label (e.g. 'Frontend') or abbreviation (e.g. 'FE', 'TST')
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            ProjectType if found, None otherwise
        """
        async with self._get_session() as session:
            # Try label match first (Handover 0837b)
            match = await self._repo.get_project_type_by_label(session, tenant_key, label)
            if match:
                return match

            # Fall back to abbreviation match (Handover 0841)
            return await self._repo.get_project_type_by_abbreviation(session, tenant_key, label)

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

        """
        # SECURITY FIX: Require tenant_key (Handover 0424 Phase 0)
        if not tenant_key:
            raise ValidationError("tenant_key is required for security (Handover 0424 Phase 0)")

        try:
            async with self._get_session() as session:
                # Get project with mandatory tenant isolation filter (Handover 0424 Phase 0)
                # Handover 0440a: Eagerly load project_type for taxonomy_alias property
                project = await self._repo.get_by_id_with_type(session, tenant_key, project_id)

                if not project:
                    raise ResourceNotFoundError(
                        message="Project not found or access denied",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                # Get agent jobs for this project (defense-in-depth: tenant_key on join query)
                agent_pairs = await self._repo.get_agent_pairs_for_project(session, tenant_key, project_id)

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
                    auto_checkin_enabled=project.auto_checkin_enabled,
                    auto_checkin_interval=project.auto_checkin_interval,
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

    async def list_projects(
        self,
        status: str | None = None,
        tenant_key: str | None = None,
        include_cancelled: bool = False,
    ) -> list[ProjectListItem]:
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

        """
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                raise ValidationError(message="No tenant context available", context={"operation": "list_projects"})

            async with self.db_manager.get_tenant_session_async(tenant_key) as session:
                projects = await self._repo.list_projects(session, tenant_key, status, include_cancelled)

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
                        completed_at=(project.completed_at.isoformat() if project.completed_at else None),
                        # Handover 0440a: Taxonomy fields
                        project_type_id=project.project_type_id,
                        project_type=project.project_type,
                        series_number=project.series_number,
                        subseries=project.subseries,
                        taxonomy_alias=project.taxonomy_alias,
                        hidden=project.hidden is True,
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

                # Fetch project to validate state before writing
                project = await self._repo.get_by_id(session, tenant_key, project_id)

                if not project:
                    raise ResourceNotFoundError(
                        message="Project not found or access denied",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                # Guard: block writes to immutable projects
                if project.status in IMMUTABLE_PROJECT_STATUSES:
                    raise ProjectStateError(
                        message=f"Cannot modify project in '{project.status}' status. "
                        "Only inactive and active projects can be updated.",
                        context={"project_id": project_id, "status": project.status},
                    )

                # Handover 0425: Also set staging_status to 'staging' when mission is updated
                project.mission = mission
                project.staging_status = "staging"
                project.updated_at = datetime.now(timezone.utc)

                await self._repo.commit(session)

                # Broadcast mission update via WebSocketManager
                await self._broadcast_mission_update(project_id, mission, project.tenant_key)

                return ProjectMissionUpdateResult(
                    message="Mission updated successfully",
                    project_id=project_id,
                )

        except (ResourceNotFoundError, ValidationError, ProjectStateError):
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
        return await self.lifecycle.complete_project(
            project_id, summary, key_outcomes, decisions_made, tenant_key, db_session
        )

    async def activate_project(
        self,
        project_id: str,
        force: bool = False,
        websocket_manager: Any | None = None,
        tenant_key: str | None = None,
    ) -> Project:
        """Facade: delegates to ProjectLifecycleService."""
        return await self.lifecycle.activate_project(project_id, force, websocket_manager, tenant_key)

    async def deactivate_project(
        self,
        project_id: str,
        tenant_key: str | None = None,
        reason: str | None = None,
        websocket_manager: Any | None = None,
    ) -> Project:
        """Facade: delegates to ProjectLifecycleService."""
        return await self.lifecycle.deactivate_project(project_id, tenant_key, reason, websocket_manager)

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

        # Handover 0904/0960: Validate auto check-in interval (minutes)
        if "auto_checkin_interval" in updates and updates["auto_checkin_interval"] not in (5, 10, 15, 20, 30, 40, 60):
            raise ValidationError(
                message="auto_checkin_interval must be one of: 5, 10, 15, 20, 30, 40, 60 minutes",
                error_code="VALIDATION_ERROR",
                context={"project_id": str(project.id), "value": updates["auto_checkin_interval"]},
            )

        # Update allowed fields (Handover 0260: Added execution_mode)
        # Handover 0412: Added status, completed_at for archive endpoint
        # Handover 0440a: Added project_type_id, series_number, subseries for taxonomy
        # Handover 0904: Added auto_checkin_enabled, auto_checkin_interval
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
            "auto_checkin_enabled",
            "auto_checkin_interval",
            "hidden",
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
            auto_checkin_enabled=project.auto_checkin_enabled,
            auto_checkin_interval=project.auto_checkin_interval,
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
            hidden=project.hidden is True,
        )

    async def update_project(
        self,
        project_id: str,
        updates: dict[str, Any],
        websocket_manager: Any | None = None,
    ) -> ProjectData:
        """
        Update project fields.

        Updates all provided fields (name, description, mission).
        This is the fixed version that handles multiple fields, not just mission.

        Args:
            project_id: Project UUID
            updates: Dict of field updates (allowed: name, description, mission, config_data)
            websocket_manager: Deprecated -- ignored. Uses self._websocket_manager instead.

        Returns:
            Updated project data dictionary

        Raises:
            ResourceNotFoundError: Project not found
            ProjectStateError: Cannot change execution mode after staging

        """
        async with self._get_session() as session:
            # Fetch project
            # Handover 0440a: Eagerly load project_type for taxonomy_alias property
            project = await self._repo.get_by_id_with_type(
                session, self.tenant_manager.get_current_tenant(), project_id
            )

            if not project:
                raise ResourceNotFoundError(message="Project not found", context={"project_id": project_id})

            # Guard: block data writes to immutable projects.
            # ALWAYS_MUTABLE_FIELDS (e.g. hidden/archive) bypass this guard —
            # they are UI display preferences, not project data mutations.
            if project.status in IMMUTABLE_PROJECT_STATUSES and not updates.keys() <= ALWAYS_MUTABLE_FIELDS:
                raise ProjectStateError(
                    message=f"Cannot modify project in '{project.status}' status. "
                    "Only inactive and active projects can be updated.",
                    context={"project_id": project_id, "status": project.status},
                )

            self._apply_project_updates(project, updates)

            try:
                await self._repo.commit(session)
            except IntegrityError as e:
                if "uq_project_taxonomy" in str(e):
                    raise AlreadyExistsError(
                        message="Taxonomy combination already in use. Please choose a different series number or suffix.",
                        context={"project_id": project_id},
                    ) from e
                raise
            await self._repo.refresh(session, project)

            # Reload project_type relationship (expired after commit)
            if project.project_type_id:
                project = await self._repo.get_with_project_type(session, project.id)

            self._logger.info(f"Updated project {project_id}")

            # Broadcast WebSocket event (use constructor-injected manager, not method param)
            ws = self._websocket_manager
            if ws:
                try:
                    await ws.broadcast_project_update(
                        project_id=project.id,
                        update_type="updated",
                        project_data=_build_ws_project_data(project),
                        tenant_key=self.tenant_manager.get_current_tenant(),
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
        """Facade: delegates to ProjectLaunchService (Handover 0950i)."""
        return await self.launch.launch_project(
            project_id,
            user_id,
            launch_config,
            websocket_manager,
            project_service=self,
        )

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

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

    # ============================================================================
    # MCP Tool Methods (sprint 002f: pushed down from ToolAccessor)
    # ============================================================================

    _VALID_STATUS_FILTERS = frozenset({"inactive", "active", "completed", "cancelled", "all"})
    _VALID_UPDATE_STATUSES = frozenset({"inactive", "active", "completed", "cancelled"})
    _VALID_DEPTH_LEVELS = frozenset({0, 1, 2, 3})

    async def create_project_for_mcp(
        self,
        name: str,
        mission: str = "",
        description: str = "",
        product_id: str | None = None,
        tenant_key: str | None = None,
        project_type: str | None = None,
        series_number: int | None = None,
        subseries: str | None = None,
        websocket_manager: Any | None = None,
    ) -> dict[str, Any]:
        """Create a project via MCP tool (validation + active product resolution).

        Pushed down from ToolAccessor.create_project (sprint 002f).
        """
        if not name or not name.strip():
            raise ValidationError(
                "Project name is required and cannot be empty.",
                context={"operation": "create_project"},
            )
        name = name.strip()
        description = description.strip() if description else ""

        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        ws = websocket_manager or self._websocket_manager

        project_type_id = None
        resolved_type_label = ""
        if project_type:
            resolved_type = await self.get_project_type_by_label(project_type, effective_tenant_key)
            if resolved_type:
                project_type_id = resolved_type.id
                resolved_type_label = resolved_type.abbreviation or project_type

        if not product_id:
            from giljo_mcp.services.product_service import ProductService

            product_service = ProductService(
                db_manager=self.db_manager,
                tenant_key=effective_tenant_key,
                websocket_manager=ws,
            )
            active_product = await product_service.get_active_product()
            if not active_product:
                raise ValidationError(
                    "No active product set. Please activate a product first.",
                    context={"tenant_key": effective_tenant_key, "operation": "create_project"},
                )
            product_id = active_product.id

        project = await self.create_project(
            name=name,
            mission=mission,
            description=description,
            product_id=product_id,
            tenant_key=effective_tenant_key,
            status="inactive",
            project_type_id=project_type_id,
            series_number=series_number,
            subseries=subseries,
        )

        logger.info(
            "Created project %s (alias: %s) for tenant %s in product %s",
            project.id,
            project.alias,
            effective_tenant_key,
            product_id,
        )

        if ws:
            try:
                await ws.broadcast_to_tenant(
                    tenant_key=effective_tenant_key,
                    event_type="project:created",
                    data={"project_id": str(project.id), "name": project.name, "product_id": product_id},
                )
            except (RuntimeError, ValueError, OSError) as e:
                logger.warning(f"Failed to broadcast project:created event: {e}")

        return {
            "success": True,
            "project_id": project.id,
            "alias": project.alias,
            "name": project.name,
            "description": project.description,
            "mission": project.mission,
            "status": project.status,
            "product_id": project.product_id,
            "project_type": resolved_type_label,
            "series_number": project.series_number or 0,
            "taxonomy_alias": project.taxonomy_alias,
            "created_at": project.created_at.isoformat() if project.created_at else None,
            "message": f"Project '{project.name}' created successfully"
            + (
                f". NOTE: project_type '{project_type}' is not a recognized category -- "
                "project created without taxonomy. Add the category in the dashboard first, "
                "then assign it to this project."
                if project_type and not project_type_id
                else ""
            ),
        }

    async def list_projects_for_mcp(
        self,
        status_filter: str = "all",
        summary_only: bool = True,
        depth: int = 0,
        tenant_key: str | None = None,
        websocket_manager: Any | None = None,
    ) -> dict[str, Any]:
        """List projects via MCP tool (validation + depth-level assembly).

        Pushed down from ToolAccessor.list_projects (sprint 002f).
        """
        if status_filter not in self._VALID_STATUS_FILTERS:
            raise ValidationError(
                f"Invalid status_filter '{status_filter}'. "
                f"Must be one of: {', '.join(sorted(self._VALID_STATUS_FILTERS))}",
                context={"operation": "list_projects"},
            )
        if not isinstance(depth, int) or depth not in self._VALID_DEPTH_LEVELS:
            raise ValidationError(
                f"Invalid depth '{depth}'. Must be an integer 0-3.",
                context={"operation": "list_projects"},
            )

        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        ws = websocket_manager or self._websocket_manager

        from giljo_mcp.services.product_service import ProductService

        product_service = ProductService(
            db_manager=self.db_manager,
            tenant_key=effective_tenant_key,
            websocket_manager=ws,
        )
        active_product = await product_service.get_active_product()
        if not active_product:
            raise ValidationError(
                "No active product set. Please activate a product first.",
                context={"tenant_key": effective_tenant_key, "operation": "list_projects"},
            )

        svc_status = None if status_filter == "all" else status_filter
        include_cancelled = status_filter == "all"
        all_projects = await self.list_projects(
            status=svc_status,
            tenant_key=effective_tenant_key,
            include_cancelled=include_cancelled,
        )

        product_projects = [p for p in all_projects if p.product_id == active_product.id]
        effective_depth = 0 if summary_only else depth

        projects_out = await self._build_mcp_project_list(product_projects, effective_depth, effective_tenant_key)

        project_types = await self._get_valid_project_types(effective_tenant_key)

        return {
            "success": True,
            "product_id": active_product.id,
            "count": len(projects_out),
            "depth": effective_depth,
            "projects": projects_out,
            "project_types": project_types,
        }

    async def _build_mcp_project_list(
        self,
        projects: list,
        depth: int,
        tenant_key: str,
    ) -> list[dict[str, Any]]:
        """Build project list dicts with graduated detail based on depth level."""
        results = []
        for p in projects:
            item: dict[str, Any] = {
                "project_id": p.id,
                "name": p.name,
                "status": p.status,
                "project_type": getattr(p.project_type, "abbreviation", None) if p.project_type else None,
                "series_number": p.series_number,
                "taxonomy_alias": p.taxonomy_alias,
                "created_at": p.created_at,
                "completed_at": p.completed_at,
            }

            if depth >= 1:
                item["description"] = p.description or ""
                item["mission"] = getattr(p, "mission", None) or ""
                agent_summary = await self.query.get_project_agent_summary(
                    project_id=p.id,
                    tenant_key=tenant_key,
                )
                item["agent_summary"] = agent_summary

            if depth >= 2:
                memory_entries = await self.query.get_project_memory_entries(
                    project_id=p.id,
                    tenant_key=tenant_key,
                )
                item["memory_entries"] = memory_entries
                agent_details = await self.query.get_project_agent_details(
                    project_id=p.id,
                    tenant_key=tenant_key,
                )
                item["agent_details"] = agent_details

            if depth >= 3:
                item["git_commits"] = self._extract_git_commits(memory_entries if depth >= 2 else [])
                message_history = await self.query.get_project_messages(
                    project_id=p.id,
                    tenant_key=tenant_key,
                )
                item["message_history"] = message_history

            results.append(item)
        return results

    @staticmethod
    def _extract_git_commits(memory_entries: list[dict]) -> list[dict]:
        """Extract git commits from 360 memory entries."""
        commits = []
        for entry in memory_entries:
            entry_commits = entry.get("git_commits", [])
            if isinstance(entry_commits, list):
                commits.extend(entry_commits)
        return commits

    async def _get_valid_project_types(self, tenant_key: str) -> list[dict[str, Any]]:
        """Return available project types for a tenant."""
        from giljo_mcp.services.project_type_ops import ensure_default_types_seeded, list_project_types

        async with self.db_manager.get_session_async() as session:
            await ensure_default_types_seeded(session, tenant_key)
            types = await list_project_types(session, tenant_key)
            return [{"abbreviation": t.abbreviation, "label": t.label, "color": t.color} for t in types]

    async def update_project_metadata_for_mcp(
        self,
        project_id: str,
        name: str | None = None,
        description: str | None = None,
        status: str | None = None,
        tenant_key: str | None = None,
        project_type: str | None = None,
        series_number: int | None = None,
        subseries: str | None = None,
        websocket_manager: Any | None = None,
    ) -> dict[str, Any]:
        """Update project metadata via MCP tool (validation + active product enforcement).

        Pushed down from ToolAccessor.update_project_metadata (sprint 002f).
        """
        if not project_id or not project_id.strip():
            raise ValidationError(
                "Project ID is required and cannot be empty.",
                context={"operation": "update_project_metadata"},
            )
        project_id = project_id.strip()

        if all(v is None for v in (name, description, status, project_type, series_number, subseries)):
            raise ValidationError(
                "At least one field must be provided.",
                context={"operation": "update_project_metadata"},
            )

        if name is not None:
            name = name.strip()
            if len(name) > 200:
                raise ValidationError(
                    f"Name exceeds 200 character limit (got {len(name)}).",
                    context={"operation": "update_project_metadata"},
                )
            if not name:
                raise ValidationError(
                    "Name cannot be empty.",
                    context={"operation": "update_project_metadata"},
                )

        if description is not None and len(description) > 5000:
            raise ValidationError(
                f"Description exceeds 5000 character limit (got {len(description)}).",
                context={"operation": "update_project_metadata"},
            )

        if status is not None and status not in self._VALID_UPDATE_STATUSES:
            raise ValidationError(
                f"Invalid status '{status}'. Must be one of: {', '.join(sorted(self._VALID_UPDATE_STATUSES))}",
                context={"operation": "update_project_metadata"},
            )

        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()
        ws = websocket_manager or self._websocket_manager

        from giljo_mcp.services.product_service import ProductService

        product_service = ProductService(
            db_manager=self.db_manager,
            tenant_key=effective_tenant_key,
            websocket_manager=ws,
        )
        active_product = await product_service.get_active_product()
        if not active_product:
            raise ValidationError(
                "No active product set. Please activate a product first.",
                context={"tenant_key": effective_tenant_key, "operation": "update_project_metadata"},
            )

        project = await self.get_project(project_id=project_id, tenant_key=effective_tenant_key)
        if project.product_id != active_product.id:
            raise ValidationError(
                "Project does not belong to the active product.",
                context={
                    "project_id": project_id,
                    "project_product_id": project.product_id,
                    "active_product_id": active_product.id,
                },
            )

        if project_type is not None:
            resolved_type = await self.get_project_type_by_label(project_type, effective_tenant_key)
            if resolved_type:
                project_type = resolved_type.id
            else:
                valid_types = await self._get_valid_project_types(effective_tenant_key)
                valid_labels = [t["abbreviation"] for t in valid_types]
                raise ValidationError(
                    f"Unknown project type '{project_type}'. "
                    f"Valid types: {', '.join(valid_labels)}. "
                    "Use list_projects() to see all valid project_types.",
                    context={"operation": "update_project_metadata", "valid_types": valid_types},
                )

        if series_number is not None and (series_number < 1 or series_number > 9999):
            raise ValidationError(
                f"series_number must be 1-9999, got {series_number}.",
                context={"operation": "update_project_metadata"},
            )
        if subseries is not None and (len(subseries) != 1 or not subseries.isalpha() or not subseries.islower()):
            raise ValidationError(
                f"subseries must be a single lowercase letter (a-z), got '{subseries}'.",
                context={"operation": "update_project_metadata"},
            )

        updates: dict[str, Any] = {}
        if name is not None:
            updates["name"] = name
        if description is not None:
            updates["description"] = description
        if status is not None:
            updates["status"] = status
        if project_type is not None:
            updates["project_type_id"] = project_type
        if series_number is not None:
            updates["series_number"] = series_number
        if subseries is not None:
            updates["subseries"] = subseries

        updated = await self.update_project(project_id=project_id, updates=updates, websocket_manager=ws)

        return {
            "success": True,
            "project_id": updated.id,
            "name": updated.name,
            "description": updated.description,
            "status": updated.status,
            "updated_at": updated.updated_at,
            "message": f"Project '{updated.name}' updated successfully.",
        }
