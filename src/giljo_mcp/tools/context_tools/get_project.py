# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Project Context Tool - Handover 0316

Fetch current project context for orchestrator awareness.
Returns project metadata, mission, status.
"""
# Read-only tool -- uses direct session.execute() for SELECT queries (no writes)

import logging
from typing import Any

from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models.projects import Project


logger = logging.getLogger(__name__)


def estimate_tokens(data: Any) -> int:
    """Estimate token count for data (simple heuristic: 1 token ≈ 4 chars)"""
    import json

    text = json.dumps(data)
    return len(text) // 4


async def get_project(
    project_id: str, tenant_key: str, include_summary: bool = False, db_manager: DatabaseManager | None = None
) -> dict[str, Any]:
    """
    Fetch current project context (Project Context).

    Handover 0316: Returns project metadata and mission.
    Args:
        project_id: Project UUID
        tenant_key: Tenant isolation key
        include_summary: Include orchestrator_summary if completed (default: False)
        db_manager: Database manager instance

    Returns:
        Dict with project info:
        {
            "source": "project_description",
            "data": {
                "project_name": "Test Project",
                "project_alias": "A1B2C3",
                "project_description": "...",
                "orchestrator_mission": "...",
                "status": "active",
                "staging_status": "staged",
                "orchestrator_summary": "..."  # Only if include_summary=True
            },
            "metadata": {
                "project_id": "uuid",
                "tenant_key": "...",
                "estimated_tokens": 300
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and project_id.

    Example:
        result = await get_project(
            project_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc",
            include_summary=False
        )
    """
    logger.info(
        "fetching_project_description project_id=%s tenant_key=%s include_summary=%s",
        project_id,
        tenant_key,
        include_summary,
    )

    if db_manager is None:
        logger.error("db_manager is required operation=get_project")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        # Fetch project with multi-tenant isolation
        stmt = select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            logger.warning(
                "project_not_found project_id=%s tenant_key=%s operation=get_project", project_id, tenant_key
            )
            return {
                "source": "project_description",
                "data": {},
                "metadata": {"project_id": project_id, "tenant_key": tenant_key, "error": "project_not_found"},
            }

        # Build data dict
        data = {
            "project_name": project.name,
            "project_alias": project.alias,
            "project_description": project.description,
            "orchestrator_mission": project.mission,
            "status": project.status,
            "staging_status": project.staging_status,
        }

        # Conditionally include summary
        if include_summary and project.orchestrator_summary:
            data["orchestrator_summary"] = project.orchestrator_summary

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "project_description_fetched project_id=%s tenant_key=%s status=%s summary_included=%s estimated_tokens=%s",
            project_id,
            tenant_key,
            project.status,
            include_summary and bool(project.orchestrator_summary),
            total_tokens,
        )

        return {
            "source": "project_description",
            "data": data,
            "metadata": {"project_id": project_id, "tenant_key": tenant_key},
        }
