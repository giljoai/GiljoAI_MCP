# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectLifecycleService - Extracted from ProjectService (Handover 0769).

Handles project lifecycle state transitions:
- activate, deactivate, cancel_staging
- complete, cancel, continue_working
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    ProjectStateError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import (
    ProjectCompleteResult,
    ProjectData,
    ProjectResumeResult,
)
from src.giljo_mcp.services.project_service import _build_ws_project_data
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ProjectLifecycleService:
    """Service for project lifecycle state transitions."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: AsyncSession | None = None,
        websocket_manager: Any | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._websocket_manager = websocket_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

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
        - staging -> active (initial launch)
        - inactive -> active (activate/resume)

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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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

        State Transition: active -> inactive

        Args:
            project_id: Project UUID
            tenant_key: Optional tenant key (uses current tenant if not provided)
            reason: Optional reason for deactivation (stored in deactivation_reason column)
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
                project.deactivation_reason = reason

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

        State Transition: staging -> cancelled

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
                cancellation_reason=project.cancellation_reason,
                deactivation_reason=project.deactivation_reason,
                early_termination=project.early_termination,
                created_at=project.created_at.isoformat() if project.created_at else None,
                updated_at=project.updated_at.isoformat() if project.updated_at else None,
                activated_at=project.activated_at.isoformat() if project.activated_at else None,
                completed_at=project.completed_at.isoformat() if project.completed_at else None,
                product_id=project.product_id,
            )

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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
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

                # Add cancellation reason if provided
                if reason:
                    update_values["cancellation_reason"] = reason

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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to cancel project")
            raise BaseGiljoError(message=f"Failed to cancel project: {e!s}", context={"project_id": project_id}) from e

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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to resume project")
            raise BaseGiljoError(
                message=f"Failed to resume project: {e!s}", context={"project_id": project_id, "tenant_key": tenant_key}
            ) from e

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
