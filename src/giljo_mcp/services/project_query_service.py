# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectQueryService - Read-only dashboard queries for projects.

Sprint 002e: Extracted from ProjectService to reduce god-class size.
These are all read-only DB queries used by the frontend dashboard.
They have no side effects and no cross-service dependencies.
"""

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import BaseGiljoError, ValidationError
from giljo_mcp.repositories.project_repository import ProjectRepository
from giljo_mcp.schemas.service_responses import ActiveProjectDetail
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ProjectQueryService:
    """Read-only query service for project dashboard data.

    Extracted from ProjectService (Sprint 002e). All methods are read-only
    DB queries with no side effects.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        self._repo = ProjectRepository()

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    async def get_active_project(self) -> ActiveProjectDetail | None:
        """Get the currently active project for the current tenant.

        Returns the active project (status='active') or None if no project is active.

        Follows Single Active Project architecture (Handover 0050b):
        - Only ONE project can be active per product at any time
        - Database enforces this via partial unique index

        Returns:
            ActiveProjectDetail with project details, or None if no active project

        Raises:
            ValidationError: When no tenant context is available
            BaseGiljoError: When operation fails
        """
        try:
            tenant_key = self.tenant_manager.get_current_tenant()

            self._logger.debug(f"[get_active_project] Retrieved tenant_key from context: {tenant_key}")

            if not tenant_key:
                self._logger.error("[get_active_project] No tenant context available!")
                raise ValidationError(
                    message="No tenant context available",
                    context={"operation": "get_active_project"},
                )

            async with self._get_session() as session:
                project = await self._repo.get_active_project(session, tenant_key)

                if not project:
                    self._logger.info(f"No active project found for tenant {tenant_key}")
                    return None

                agent_count = await self._repo.count_agent_jobs(session, tenant_key, project.id)
                message_count = await self._repo.count_messages(session, tenant_key, project.id)

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
                    project_type_id=project.project_type_id,
                    series_number=project.series_number,
                    subseries=project.subseries,
                    taxonomy_alias=project.taxonomy_alias,
                )

        except ValidationError:
            raise
        except Exception as e:
            self._logger.exception("Failed to get active project")
            raise BaseGiljoError(message=f"Failed to get active project: {e!s}", context={}) from e

    async def get_project_agent_summary(self, project_id: str, tenant_key: str) -> dict:
        """Get a lightweight summary of agent jobs for a project.

        Returns counts and types of agents spawned, without full details.

        Args:
            project_id: Project UUID.
            tenant_key: Tenant isolation key (required).

        Returns:
            Dict with agent_count and job_types list.
        """
        try:
            async with self._get_session() as session:
                rows = await self._repo.get_agent_job_type_summary(session, tenant_key, project_id)
                total = sum(r.count for r in rows)
                return {
                    "agent_count": total,
                    "job_types": [{"type": r.job_type, "count": r.count} for r in rows],
                }
        except Exception as e:  # noqa: BLE001 -- graceful degradation for optional enrichment
            self._logger.warning("Failed to get agent summary for project %s: %s", project_id, e)
            return {"agent_count": 0, "job_types": []}

    async def get_project_agent_details(self, project_id: str, tenant_key: str) -> list[dict]:
        """Get detailed agent job info for a project (depth 2).

        Returns agent display names, statuses, and results.

        Args:
            project_id: Project UUID.
            tenant_key: Tenant isolation key (required).

        Returns:
            List of agent job detail dicts.
        """
        try:
            async with self._get_session() as session:
                pairs = await self._repo.get_agent_details_for_project(session, tenant_key, project_id)
                return [
                    {
                        "job_id": job.job_id,
                        "job_type": job.job_type,
                        "status": job.status,
                        "display_name": execution.agent_display_name,
                        "agent_status": execution.status,
                        "mission": job.mission,
                        "result": execution.result,
                        "created_at": job.created_at.isoformat() if job.created_at else None,
                        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
                    }
                    for job, execution in pairs
                ]
        except Exception as e:  # noqa: BLE001 -- graceful degradation for optional enrichment
            self._logger.warning("Failed to get agent details for project %s: %s", project_id, e)
            return []

    async def get_project_memory_entries(self, project_id: str, tenant_key: str) -> list[dict]:
        """Get 360 memory entries for a project (depth 2).

        Args:
            project_id: Project UUID.
            tenant_key: Tenant isolation key (required).

        Returns:
            List of memory entry dicts with summary, outcomes, decisions, and git_commits.
        """
        try:
            async with self._get_session() as session:
                entries = await self._repo.get_memory_entries_for_project(session, tenant_key, project_id)
                return [
                    {
                        "id": str(entry.id),
                        "entry_type": entry.entry_type,
                        "sequence": entry.sequence,
                        "project_name": entry.project_name,
                        "summary": entry.summary,
                        "key_outcomes": entry.key_outcomes or [],
                        "decisions_made": entry.decisions_made or [],
                        "git_commits": entry.git_commits or [],
                        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
                    }
                    for entry in entries
                ]
        except Exception as e:  # noqa: BLE001 -- graceful degradation for optional enrichment
            self._logger.warning("Failed to get memory entries for project %s: %s", project_id, e)
            return []

    async def get_project_messages(self, project_id: str, tenant_key: str) -> list[dict]:
        """Get message history for a project (depth 3).

        Args:
            project_id: Project UUID.
            tenant_key: Tenant isolation key (required).

        Returns:
            List of message dicts with sender, content, and timestamps.
        """
        try:
            async with self._get_session() as session:
                messages = await self._repo.get_messages_for_project(session, tenant_key, project_id)
                return [
                    {
                        "id": str(msg.id),
                        "from_agent_id": msg.from_agent_id,
                        "content": msg.content,
                        "message_type": msg.message_type,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    }
                    for msg in messages
                ]
        except Exception as e:  # noqa: BLE001 -- graceful degradation for optional enrichment
            self._logger.warning("Failed to get messages for project %s: %s", project_id, e)
            return []
