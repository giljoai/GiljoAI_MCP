# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectCloseoutService - Extracted from ProjectService (Handover 0769).

Handles project closeout operations:
- close_out_project, get_closeout_data, can_close_project
- generate_closeout_prompt
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import (
    CanCloseResult,
    CloseoutData,
    CloseoutPromptResult,
    ProjectCloseOutResult,
)
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ProjectCloseoutService:
    """Service for project closeout operations."""

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
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to close out project")
            raise BaseGiljoError(
                message=f"Failed to close out project: {e!s}",
                context={"project_id": project_id, "tenant_key": tenant_key},
            ) from e

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
