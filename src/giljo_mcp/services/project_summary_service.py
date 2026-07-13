# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

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
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.repositories.project_repository import ProjectRepository
from giljo_mcp.schemas.service_responses import ProjectSummaryResult
from giljo_mcp.services._session_helpers import optional_tenant_session
from giljo_mcp.services.project_helpers import compute_completion_percent
from giljo_mcp.tenant import TenantManager


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
        self._repo = ProjectRepository()

    def _get_session(self, tenant_key: str | None = None):
        """Yield a tenant-scoped DB session, honoring an injected test session (shared helper, BE-8000d)."""
        return optional_tenant_session(self.db_manager, tenant_key, self._test_session)

    async def get_project_summary(self, project_id: str, tenant_key: str | None = None) -> ProjectSummaryResult:
        """
        Generate project summary with metrics and status.

        Returns comprehensive project overview including job statistics,
        completion metrics, and activity timestamps for dashboard display.

        Args:
            project_id: Project UUID
            tenant_key: Explicit tenant key (BE6004C-3 / RC-2). When omitted,
                falls back to the ambient tenant context for backward
                compatibility. Callers in the request path MUST pass it
                explicitly (e.g. ``current_user.tenant_key``) so the read is
                ContextVar-independent.

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
        effective_tenant_key = tenant_key or self.tenant_manager.get_current_tenant()

        async with self._get_session(effective_tenant_key) as session:
            project = await self._repo.get_by_id(session, effective_tenant_key, project_id)

            if not project:
                raise ResourceNotFoundError(message="Project not found", context={"project_id": project_id})

            job_counts = await self._repo.get_agent_status_counts(session, effective_tenant_key, project_id)

            total_jobs = sum(job_counts.values())
            completed_jobs = job_counts.get("complete", 0)
            blocked_jobs = job_counts.get("blocked", 0)
            active_jobs = job_counts.get("working", 0)
            pending_jobs = job_counts.get("waiting", 0)

            # BE-9000k: single shared computation; denominator excludes
            # decommissioned agents (so a project with retired agents can reach
            # 100%). total_jobs is kept as the full agent count for display.
            completion_percentage = compute_completion_percent(
                completed_jobs, total_jobs, job_counts.get("decommissioned", 0)
            )

            last_activity_at = await self._repo.get_last_activity_at(session, effective_tenant_key, project_id)

            product_name = ""
            if project.product_id:
                product = await self._repo.get_product_by_id(session, effective_tenant_key, project.product_id)
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
                last_activity_at=last_activity_at.isoformat() if last_activity_at else None,
                product_id=project.product_id or "",
                product_name=product_name,
            )
