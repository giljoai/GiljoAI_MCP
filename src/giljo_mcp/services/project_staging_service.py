# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectStagingService - Project staging workflow operations.

Sprint 002e: Extracted from ProjectLifecycleService to reduce god-class size.
Contains check_staging_allowed, restage, unstage, and cancel_staging.
"""

import logging
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.exceptions import ProjectStateError, ResourceNotFoundError
from giljo_mcp.models.projects import Project
from giljo_mcp.repositories.project_lifecycle_repository import ProjectLifecycleRepository
from giljo_mcp.repositories.project_repository import ProjectRepository
from giljo_mcp.schemas.service_responses import ProjectData
from giljo_mcp.services.project_helpers import _build_ws_project_data
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ProjectStagingService:
    """Service for project staging workflow operations.

    Extracted from ProjectLifecycleService (Sprint 002e).
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: AsyncSession | None = None,
        websocket_manager: Any | None = None,
        lifecycle_service: Any | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._websocket_manager = websocket_manager
        self._lifecycle = lifecycle_service
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._project_repo = ProjectRepository()
        self._lifecycle_repo = ProjectLifecycleRepository()

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    def check_staging_allowed(self, project: Project) -> None:
        """Check if a project can be staged. Raises if staging is already in progress.

        Args:
            project: The project to check.

        Raises:
            ProjectStateError: If project.staging_status is 'staging'.
        """
        if project.staging_status == "staging":
            raise ProjectStateError(
                message="Staging already in progress. Use Re-Stage to reset first.",
                context={"project_id": project.id, "staging_status": project.staging_status},
            )

    async def restage(self, project_id: str) -> dict:
        """Reset a staged project so it can be re-staged with a fresh orchestrator.

        Guards:
            1. project.staging_status must be 'staging' -- otherwise reject.
            2. The orchestrator AgentExecution must have status 'waiting'.

        Actions (single transaction):
            1. Set project.staging_status = None
            2. Set project.execution_mode = 'multi_terminal'
            3. Decommission the existing orchestrator execution
            4. Create a fresh orchestrator fixture

        Args:
            project_id: Project UUID.

        Returns:
            Dict with message, project_id, and new_orchestrator fixture info.

        Raises:
            ResourceNotFoundError: Project not found.
            ProjectStateError: Invalid state for restage.
        """
        tenant_key = self.tenant_manager.get_current_tenant()

        async with self._get_session() as session:
            project = await self._project_repo.get_by_id(session, tenant_key, project_id)

            if not project:
                raise ResourceNotFoundError(
                    message="Project not found",
                    context={"project_id": project_id},
                )

            if project.staging_status != "staging":
                raise ProjectStateError(
                    message="Project is not currently staged",
                    context={
                        "project_id": project_id,
                        "staging_status": project.staging_status,
                    },
                )

            orchestrator = await self._lifecycle_repo.find_existing_orchestrator(session, tenant_key, project_id)

            if orchestrator and orchestrator.status != "waiting":
                raise ProjectStateError(
                    message="Cannot restage: orchestrator agent is already active",
                    context={
                        "project_id": project_id,
                        "orchestrator_status": orchestrator.status,
                    },
                )

            project.staging_status = None
            project.execution_mode = "multi_terminal"
            project.updated_at = datetime.now(UTC)

            if orchestrator:
                orchestrator.status = "decommissioned"

            await self._project_repo.commit(session)

            # Use parent lifecycle service to create fresh orchestrator fixture
            new_fixture = await self._lifecycle._ensure_orchestrator_fixture(session, project)

            self._logger.info(
                "[RESTAGE] Project %s restaged, new orchestrator: %s",
                project_id,
                new_fixture,
            )

            return {
                "message": "Project restaged successfully",
                "project_id": project.id,
                "new_orchestrator": new_fixture,
            }

    async def unstage(self, project_id: str) -> dict:
        """Revert a project from 'staged' back to ready state.

        Only allowed when staging_status == 'staged' (prompt generated, agent
        has not yet made first contact).

        Actions:
            1. Reset staging_status to None
            2. Clear mission (prompt was generated but never used)

        Raises:
            ResourceNotFoundError: Project not found.
            ProjectStateError: Not in 'staged' state.
        """
        tenant_key = self.tenant_manager.get_current_tenant()

        async with self._get_session() as session:
            project = await self._project_repo.get_by_id(session, tenant_key, project_id)

            if not project:
                raise ResourceNotFoundError(
                    message="Project not found",
                    context={"project_id": project_id},
                )

            if project.staging_status != "staged":
                raise ProjectStateError(
                    message="Project is not in staged state. Cannot unstage.",
                    context={
                        "project_id": project_id,
                        "staging_status": project.staging_status,
                    },
                )

            project.staging_status = None
            project.updated_at = datetime.now(UTC)
            await self._project_repo.commit(session)

            self._logger.info("[UNSTAGE] Project %s unstaged", project_id)

            return {
                "message": "Project unstaged successfully",
                "project_id": project.id,
            }

    async def cancel_staging(self, project_id: str, websocket_manager: Any | None = None) -> ProjectData:
        """Cancel a project in staging state.

        State Transition: staging -> cancelled

        Args:
            project_id: Project UUID
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            ProjectData

        Raises:
            ResourceNotFoundError: Project not found
            ProjectStateError: Cannot cancel staging for project with current status
        """
        async with self._get_session() as session:
            project = await self._project_repo.get_by_id(session, self.tenant_manager.get_current_tenant(), project_id)

            if not project:
                raise ResourceNotFoundError(message="Project not found", context={"project_id": project_id})

            # BE-5039 Phase 2b: ``staging`` is no longer a value on the
            # canonical ``project_status`` ENUM. The actual staging
            # workflow tracker is the dedicated ``staging_status`` column
            # ('staging' | 'staging_complete' | NULL). Guard against the
            # right column so the precondition isn't dead code post-
            # migration. The project must currently be inactive AND have
            # an in-progress staging workflow.
            if project.staging_status != "staging" or project.status != ProjectStatus.INACTIVE:
                raise ProjectStateError(
                    message=(
                        f"Cannot cancel staging: project status='{project.status.value}', "
                        f"staging_status='{project.staging_status}' (need INACTIVE + staging)"
                    ),
                    context={
                        "project_id": project_id,
                        "current_status": project.status.value,
                        "staging_status": project.staging_status,
                    },
                )

            project.status = ProjectStatus.CANCELLED
            project.completed_at = datetime.now(UTC)
            project.updated_at = datetime.now(UTC)

            await self._project_repo.commit(session)
            await self._project_repo.refresh(session, project)

            self._logger.info(f"Cancelled staging for project {project_id}")

            if websocket_manager:
                try:
                    await websocket_manager.broadcast_project_update(
                        project_id=project.id,
                        update_type="cancelled",
                        project_data=_build_ws_project_data(project),
                        tenant_key=project.tenant_key,
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience
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
