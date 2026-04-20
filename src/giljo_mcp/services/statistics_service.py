# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
StatisticsService - Read-only analytics and dashboard metrics.

BE-5022b: Created to replace direct repository imports in api/endpoints/statistics.py.
Wraps JobStatisticsRepository and ProductStatisticsRepository behind the service layer.

All methods are read-only SELECT queries. No writes occur in this service.
"""

import logging
from contextlib import asynccontextmanager
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.repositories.job_statistics_repository import JobStatisticsRepository
from giljo_mcp.repositories.product_statistics_repository import (
    ProductStatisticsRepository,
)


logger = logging.getLogger(__name__)


class StatisticsService:
    """Service for read-only analytics across jobs and products.

    Wraps JobStatisticsRepository and ProductStatisticsRepository to keep
    all DB access behind the service layer. All queries filter by tenant_key.

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        test_session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self._test_session = test_session
        self._job_repo = JobStatisticsRepository(db_manager)
        self._product_repo = ProductStatisticsRepository(db_manager)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    # ---- Dashboard analytics ----

    async def get_dashboard_stats(
        self,
        tenant_key: str,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Get consolidated dashboard analytics.

        Args:
            tenant_key: Tenant isolation key
            product_id: Optional product filter

        Returns:
            Dict with project_status_dist, taxonomy_dist, agent_role_dist,
            recent_projects, recent_memories, task_status_dist,
            execution_mode_dist, products
        """
        async with self._get_session() as session:
            return {
                "project_status_dist": await self._product_repo.get_project_status_distribution(
                    session, tenant_key, product_id=product_id
                ),
                "taxonomy_dist": await self._product_repo.get_project_taxonomy_distribution(
                    session, tenant_key, product_id=product_id
                ),
                "agent_role_dist": await self._job_repo.get_agent_role_distribution(
                    session, tenant_key, product_id=product_id
                ),
                "recent_projects": await self._product_repo.get_recent_projects(
                    session, tenant_key, product_id=product_id
                ),
                "recent_memories": await self._product_repo.get_recent_memory_entries(
                    session, tenant_key, product_id=product_id
                ),
                "task_status_dist": await self._product_repo.get_task_status_distribution(
                    session, tenant_key, product_id=product_id
                ),
                "execution_mode_dist": await self._product_repo.get_execution_mode_distribution(
                    session, tenant_key, product_id=product_id
                ),
                "products": await self._product_repo.get_product_project_counts(session, tenant_key),
            }

    # ---- Call counts ----

    async def get_api_metrics(
        self,
        tenant_key: str,
    ) -> Any:
        """Get API call metrics from DB.

        Args:
            tenant_key: Tenant isolation key

        Returns:
            Metrics object with total_api_calls and total_mcp_calls, or None
        """
        async with self._get_session() as session:
            return await self._job_repo.get_api_metrics(session, tenant_key)

    # ---- System statistics ----

    async def get_system_stats(
        self,
        tenant_key: str,
    ) -> dict[str, int]:
        """Get system-level statistics.

        Args:
            tenant_key: Tenant isolation key

        Returns:
            Dict with total_projects, active_projects, completed_projects,
            total_agents, active_agents, total_messages, pending_messages,
            total_tasks, completed_tasks, total_agents_spawned,
            total_jobs_completed, projects_staged, projects_cancelled
        """
        async with self._get_session() as session:
            return {
                "total_projects": await self._product_repo.count_total_projects(session, tenant_key),
                "active_projects": await self._product_repo.count_projects_by_status(session, tenant_key, "active"),
                "completed_projects": await self._product_repo.count_projects_by_status(
                    session, tenant_key, "completed"
                ),
                "total_agents": await self._job_repo.count_total_agents(session, tenant_key),
                "active_agents": await self._job_repo.count_active_agents(session, tenant_key),
                "total_messages": await self._product_repo.count_total_messages(session, tenant_key),
                "pending_messages": await self._product_repo.count_messages_by_status(session, tenant_key, "pending"),
                "total_tasks": await self._product_repo.count_total_tasks(session, tenant_key),
                "completed_tasks": await self._product_repo.count_completed_tasks(session, tenant_key),
                "total_agents_spawned": await self._job_repo.count_total_agents(session, tenant_key),
                "total_jobs_completed": await self._job_repo.count_completed_agents(session, tenant_key),
                "projects_staged": await self._product_repo.count_projects_staged(session, tenant_key),
                "projects_cancelled": await self._product_repo.count_projects_by_status(
                    session, tenant_key, "cancelled"
                ),
            }

    # ---- Project statistics ----

    async def get_project_stats(
        self,
        tenant_key: str,
        status: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list:
        """Get projects with pagination for statistics.

        Args:
            tenant_key: Tenant isolation key
            status: Optional status filter
            limit: Max results
            offset: Skip count

        Returns:
            List of project ORM instances
        """
        async with self._get_session() as session:
            return await self._product_repo.get_projects_with_pagination(
                session, tenant_key, status=status, limit=limit, offset=offset
            )

    async def get_project_by_id(self, tenant_key: str, project_id: str) -> Any:
        """Get a single project by ID.

        Args:
            tenant_key: Tenant isolation key
            project_id: Project UUID

        Returns:
            Project ORM instance or None
        """
        async with self._get_session() as session:
            return await self._product_repo.get_project_by_id(session, tenant_key, project_id)

    async def count_agents_for_project(self, tenant_key: str, project_id: str) -> int:
        """Count agents for a project."""
        async with self._get_session() as session:
            return await self._job_repo.count_agents_for_project(session, tenant_key, project_id)

    async def count_messages_for_project(self, tenant_key: str, project_id: str) -> int:
        """Count messages for a project."""
        async with self._get_session() as session:
            return await self._product_repo.count_messages_for_project(session, tenant_key, project_id)

    async def count_tasks_for_project(self, tenant_key: str, project_id: str) -> int:
        """Count tasks for a project."""
        async with self._get_session() as session:
            return await self._product_repo.count_tasks_for_project(session, tenant_key, project_id)

    async def count_completed_tasks_for_project(self, tenant_key: str, project_id: str) -> int:
        """Count completed tasks for a project."""
        async with self._get_session() as session:
            return await self._product_repo.count_completed_tasks_for_project(session, tenant_key, project_id)

    async def get_last_activity_for_project(self, tenant_key: str, project_id: str) -> Any:
        """Get last activity timestamp for a project."""
        async with self._get_session() as session:
            return await self._product_repo.get_last_activity_for_project(session, tenant_key, project_id)

    # ---- Agent statistics ----

    async def get_agent_executions_with_filters(
        self,
        tenant_key: str,
        project_id: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100,
    ) -> list:
        """Get agent executions with optional filters."""
        async with self._get_session() as session:
            return await self._job_repo.get_agent_executions_with_filters(
                session, tenant_key, project_id=project_id, status=status, limit=limit
            )

    async def count_messages_sent_by_agent(self, tenant_key: str, agent_name: str) -> int:
        """Count messages sent by an agent."""
        async with self._get_session() as session:
            return await self._job_repo.count_messages_sent_by_agent(session, tenant_key, agent_name)

    async def count_messages_received_by_agent(self, tenant_key: str, agent_name: str) -> int:
        """Count messages received by an agent."""
        async with self._get_session() as session:
            return await self._job_repo.count_messages_received_by_agent(session, tenant_key, agent_name)

    async def get_last_message_sent_by_agent(self, tenant_key: str, agent_name: str) -> Any:
        """Get last message timestamp sent by an agent."""
        async with self._get_session() as session:
            return await self._job_repo.get_last_message_sent_by_agent(session, tenant_key, agent_name)

    async def get_agent_job_by_job_id(self, tenant_key: str, job_id: str) -> Any:
        """Get agent job by job_id."""
        async with self._get_session() as session:
            return await self._job_repo.get_agent_job_by_job_id(session, tenant_key, job_id)

    # ---- Message statistics ----

    async def get_message_stats(
        self,
        tenant_key: str,
        project_id: Optional[str] = None,
        since: Any = None,
    ) -> dict[str, int]:
        """Get message statistics with optional filters.

        Args:
            tenant_key: Tenant isolation key
            project_id: Optional project filter
            since: Optional datetime cutoff

        Returns:
            Dict with total, pending, acknowledged, completed, failed counts
        """
        async with self._get_session() as session:
            return {
                "total": await self._product_repo.count_messages_with_filters(
                    session, tenant_key, project_id=project_id, since=since
                ),
                "pending": await self._product_repo.count_messages_by_status_with_filters(
                    session, tenant_key, status="pending", project_id=project_id, since=since
                ),
                "acknowledged": await self._product_repo.count_messages_by_status_with_filters(
                    session, tenant_key, status="acknowledged", project_id=project_id, since=since
                ),
                "completed": await self._product_repo.count_messages_by_status_with_filters(
                    session, tenant_key, status="completed", project_id=project_id, since=since
                ),
                "failed": await self._product_repo.count_messages_by_status_with_filters(
                    session, tenant_key, status="failed", project_id=project_id, since=since
                ),
            }

    # ---- Performance / health ----

    async def execute_health_check(self) -> bool:
        """Execute a database health check."""
        async with self._get_session() as session:
            return await self._job_repo.execute_health_check(session)
