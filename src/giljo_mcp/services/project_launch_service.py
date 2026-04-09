# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectLaunchService - Project launch orchestration

Handover 0950i: Extracted from ProjectService to reduce god-class size.
Original launch_project was 219 lines — decomposed into named sub-methods.

Responsibilities:
- Launch orchestration (creating orchestrator agent job)
- Pre-launch validation and existing orchestrator detection
- User field priority and depth config resolution
- Thin-client prompt generation

Design Principles:
- Single Responsibility: Only launch orchestration
- ProjectLaunchService may call ProjectService for activation
- ProjectService must NOT import from this module
- All agent lifecycle operations go through AgentJob/AgentExecution models
- All DB queries filter by tenant_key
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import ProjectLaunchResult
from src.giljo_mcp.services.project_service import _build_ws_project_data
from src.giljo_mcp.tenant import TenantManager

logger = logging.getLogger(__name__)


class ProjectLaunchService:
    """
    Service for launching project orchestrators.

    Handles the complete launch lifecycle:
    1. Validate project exists and is launchable
    2. Resolve user configuration (field priorities, depth)
    3. Check for existing orchestrators (reuse if found)
    4. Create new orchestrator job + execution
    5. Generate thin-client launch prompt

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
        Initialize ProjectLaunchService.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            test_session: Optional AsyncSession for tests
            websocket_manager: Optional WebSocket manager for real-time updates
        """
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

    async def launch_project(
        self,
        project_id: str,
        user_id: str | None = None,
        launch_config: dict[str, Any | None] = None,
        websocket_manager: Any | None = None,
        project_service: Any | None = None,
    ) -> ProjectLaunchResult:
        """
        Launch project orchestrator.

        Creates orchestrator agent job and generates thin-client launch prompt.
        Activates the project if not already active.

        Args:
            project_id: Project UUID
            user_id: Optional user ID for fetching field priorities and depth config
            launch_config: Optional launch configuration
            websocket_manager: Optional WebSocket manager for real-time updates
            project_service: ProjectService instance for activation (injected to avoid circular import)

        Returns:
            ProjectLaunchResult with orchestrator job ID and launch prompt

        Raises:
            ResourceNotFoundError: Project not found
            ProjectStateError: Cannot activate project
        """
        async with self._get_session() as session:
            tenant_key = self.tenant_manager.get_current_tenant()

            project = await self._validate_launch_preconditions(
                session, project_id, tenant_key, websocket_manager, project_service
            )

            field_toggles, depth_config = await self._resolve_user_config(
                session, user_id, tenant_key
            )

            existing = await self._find_existing_orchestrator(
                session, project_id, tenant_key
            )
            if existing:
                return self._build_reuse_result(project, existing)

            return await self._spawn_orchestrator(
                session, project, project_id, tenant_key,
                field_toggles, depth_config, user_id, websocket_manager,
            )

    async def _validate_launch_preconditions(
        self,
        session: AsyncSession,
        project_id: str,
        tenant_key: str,
        websocket_manager: Any | None,
        project_service: Any | None,
    ) -> Project:
        """Fetch project and activate if needed.

        Args:
            session: Database session
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            websocket_manager: Optional WS manager for activation broadcast
            project_service: ProjectService for activation

        Returns:
            Project model instance

        Raises:
            ResourceNotFoundError: Project not found
        """
        result = await session.execute(
            select(Project).where(
                and_(Project.id == project_id, Project.tenant_key == tenant_key)
            )
        )
        project = result.scalar_one_or_none()

        if not project:
            raise ResourceNotFoundError(
                message="Project not found",
                context={"project_id": project_id},
            )

        if project.status != "active" and project_service:
            await project_service.activate_project(
                project_id, websocket_manager=websocket_manager
            )

        return project

    async def _resolve_user_config(
        self,
        session: AsyncSession,
        user_id: str | None,
        tenant_key: str,
    ) -> tuple[dict, dict]:
        """Resolve user field toggles and depth configuration.

        Handover 0840d: Fetch from normalized tables/columns.

        Args:
            session: Database session
            user_id: Optional user ID
            tenant_key: Tenant key for isolation

        Returns:
            Tuple of (field_toggles dict, depth_config dict)
        """
        field_toggles: dict = {}
        depth_config: dict | None = None

        if user_id:
            from src.giljo_mcp.models.auth import User, UserFieldPriority

            user_stmt = select(User).where(
                and_(User.id == user_id, User.tenant_key == tenant_key)
            )
            user_result = await session.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user:
                prio_result = await session.execute(
                    select(UserFieldPriority).where(
                        and_(
                            UserFieldPriority.user_id == user_id,
                            UserFieldPriority.tenant_key == tenant_key,
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

                depth_config = {
                    "vision_documents": user.depth_vision_documents,
                    "memory_last_n_projects": user.depth_memory_last_n,
                    "git_commits": user.depth_git_commits,
                    "agent_templates": user.depth_agent_templates,
                    "tech_stack_sections": user.depth_tech_stack_sections,
                    "architecture_depth": user.depth_architecture,
                }

        if not depth_config:
            depth_config = {
                "vision_documents": "medium",
                "memory_last_n_projects": 3,
                "git_commits": 25,
                "agent_templates": "type_only",
                "tech_stack_sections": "all",
                "architecture_depth": "overview",
            }

        return field_toggles, depth_config

    async def _find_existing_orchestrator(
        self,
        session: AsyncSession,
        project_id: str,
        tenant_key: str,
    ) -> AgentExecution | None:
        """Check for existing orchestrator to reuse.

        Handover 0485: Prevents duplicate orchestrators when launch_project()
        is called multiple times.

        Args:
            session: Database session
            project_id: Project UUID
            tenant_key: Tenant key for isolation

        Returns:
            Existing AgentExecution if found, None otherwise
        """
        existing_orch_stmt = (
            select(AgentExecution)
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project_id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),
            )
            .order_by(AgentExecution.started_at.desc())
        )
        result = await session.execute(existing_orch_stmt)
        return result.scalars().first()

    def _build_reuse_result(
        self, project: Project, existing: AgentExecution
    ) -> ProjectLaunchResult:
        """Build launch result for reusing an existing orchestrator.

        Args:
            project: Project model instance
            existing: Existing orchestrator AgentExecution

        Returns:
            ProjectLaunchResult with existing orchestrator info
        """
        self._logger.info(
            f"[LAUNCH] Reusing existing orchestrator {existing.job_id} "
            f"for project {project.id} (status={existing.status})"
        )

        return ProjectLaunchResult(
            project_id=project.id,
            orchestrator_job_id=existing.job_id,
            launch_prompt=self._generate_launch_prompt(
                project.name, project.id, project.mission, existing.job_id
            ),
            status=project.status,
            staging_status=project.staging_status,
        )

    async def _spawn_orchestrator(
        self,
        session: AsyncSession,
        project: Project,
        project_id: str,
        tenant_key: str,
        field_toggles: dict,
        depth_config: dict,
        user_id: str | None,
        websocket_manager: Any | None,
    ) -> ProjectLaunchResult:
        """Create new orchestrator job and execution records.

        Args:
            session: Database session
            project: Project model instance
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            field_toggles: User field priority toggles
            depth_config: User depth configuration
            user_id: Optional user ID
            websocket_manager: Optional WS manager for broadcast

        Returns:
            ProjectLaunchResult with new orchestrator info
        """
        orchestrator_job_id = str(uuid4())

        # Create AgentJob (work order) - stores mission ONCE (Handover 0358a)
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
                "created_via": "project_launch_service",
            },
        )
        session.add(agent_job)

        # Create AgentExecution (executor) - first instance (Handover 0358a)
        agent_execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=orchestrator_job_id,
            tenant_key=tenant_key,
            agent_display_name="orchestrator",
            agent_name="orchestrator",
            status="waiting",
            progress=0,
            health_status="unknown",
        )
        session.add(agent_execution)

        # Set staging_status to 'staging' when orchestrator is launched
        project.staging_status = "staging"
        project.updated_at = datetime.now(timezone.utc)

        await session.flush()

        launch_prompt = self._generate_launch_prompt(
            project.name, project.id, project.mission, orchestrator_job_id
        )

        await session.commit()

        self._logger.info(
            f"Launched project {project_id} with orchestrator job {orchestrator_job_id}"
        )

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
            except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience
                self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

        return ProjectLaunchResult(
            project_id=project.id,
            orchestrator_job_id=orchestrator_job_id,
            launch_prompt=launch_prompt,
            status=project.status,
            staging_status=project.staging_status,
        )

    @staticmethod
    def _generate_launch_prompt(
        project_name: str, project_id: str, mission: str | None, job_id: str
    ) -> str:
        """Generate thin-client launch prompt for orchestrator.

        Args:
            project_name: Human-readable project name
            project_id: Project UUID
            mission: Project mission statement
            job_id: Orchestrator job UUID

        Returns:
            Launch prompt string
        """
        return f"""Launch orchestrator for project: {project_name}

Project ID: {project_id}
Mission: {mission}
Orchestrator Job ID: {job_id}

This is a thin-client launch. Use the get_orchestrator_instructions() MCP tool to fetch full mission details.
"""
