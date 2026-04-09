# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectSummaryService - Project summary and metrics aggregation

Handover 0950n: Extracted from ProjectService to bring it under 1000 lines.

Responsibilities:
- Aggregate job counts and completion metrics for a project
- Resolve product context (name lookup)
- Return a fully typed ProjectSummaryResult

Design Principles:
- Single Responsibility: Only summary/metrics aggregation
- All DB queries filter by tenant_key
- No imports from ProjectService (avoids circular dependency)
"""

import logging
from contextlib import asynccontextmanager
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import ProjectSummaryResult
from src.giljo_mcp.tenant import TenantManager

logger = logging.getLogger(__name__)


class ProjectSummaryService:
    """
    Service for generating project summary reports with aggregated metrics.

    Produces a ProjectSummaryResult containing job statistics, completion
    percentage, activity timestamps, and product context suitable for
    dashboard display.

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
        Initialize ProjectSummaryService.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            test_session: Optional AsyncSession for tests to share the same transaction
            websocket_manager: Optional WebSocket manager (unused; accepted for API uniformity)
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

    async def get_project_summary(self, project_id: str) -> ProjectSummaryResult:
        """
        Generate project summary with metrics and status.

        Returns comprehensive project overview including job statistics,
        completion metrics, and activity timestamps for dashboard display.

        Args:
            project_id: Project UUID

        Returns:
            ProjectSummaryResult with:
            - Basic project info (id, name, status, mission)
            - Agent job counts (pending/active/completed/blocked)
            - Mission completion percentage
            - Timestamps (created, activated, last activity)
            - Product context (id, name)

        Raises:
            ResourceNotFoundError: Project not found
        """
        async with self._get_session() as session:
            tenant_key = self.tenant_manager.get_current_tenant()

            result = await session.execute(
                select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
            )
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(message="Project not found", context={"project_id": project_id})

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

            total_jobs = sum(job_counts.values())
            completed_jobs = job_counts.get("complete", 0)
            blocked_jobs = job_counts.get("blocked", 0)
            active_jobs = job_counts.get("working", 0)
            pending_jobs = job_counts.get("waiting", 0)

            completion_percentage = 0.0
            if total_jobs > 0:
                completion_percentage = (completed_jobs / total_jobs) * 100.0

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
                        AgentJob.tenant_key == tenant_key,
                    )
                )
            )
            last_activity_at = last_activity_result.scalar()

            product_name = ""
            if project.product_id:
                from src.giljo_mcp.models.products import Product

                product_result = await session.execute(
                    select(Product).where(
                        and_(
                            Product.id == project.product_id,
                            Product.tenant_key == tenant_key,
                        )
                    )
                )
                product = product_result.scalar_one_or_none()
                if product:
                    product_name = product.name

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
