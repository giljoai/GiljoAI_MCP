"""
Project Context Tool - Handover 0316

Fetch current project context for orchestrator awareness.
Returns project metadata, mission, status (excludes context_budget - deprecated).
"""

import structlog
from typing import Any, Dict, Optional
from sqlalchemy import select
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.database import DatabaseManager

logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Estimate token count for data (simple heuristic: 1 token ≈ 4 chars)"""
    import json
    text = json.dumps(data)
    return len(text) // 4


async def get_project(
    project_id: str,
    tenant_key: str,
    include_summary: bool = False,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Fetch current project context (Project Context).

    Handover 0316: Returns project metadata and mission.
    NOTE: Excludes context_budget (soft deprecated as of v3.1).

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
                "context_used": 50000,
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
        "fetching_project_description",
        project_id=project_id,
        tenant_key=tenant_key,
        include_summary=include_summary
    )

    if db_manager is None:
        logger.error("db_manager is required", operation="get_project")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        # Fetch project with multi-tenant isolation
        stmt = select(Project).where(
            Project.id == project_id,
            Project.tenant_key == tenant_key
        )
        result = await session.execute(stmt)
        project = result.scalar_one_or_none()

        if not project:
            logger.warning(
                "project_not_found",
                project_id=project_id,
                tenant_key=tenant_key,
                operation="get_project"
            )
            return {
                "source": "project_description",
                "data": {},
                "metadata": {
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "error": "project_not_found"
                }
            }

        # Build data dict (EXCLUDE context_budget - deprecated)
        data = {
            "project_name": project.name,
            "project_alias": project.alias,
            "project_description": project.description,
            "orchestrator_mission": project.mission,
            "status": project.status,
            "staging_status": project.staging_status,
            "context_used": project.context_used
        }

        # Conditionally include summary
        if include_summary and project.orchestrator_summary:
            data["orchestrator_summary"] = project.orchestrator_summary

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "project_description_fetched",
            project_id=project_id,
            tenant_key=tenant_key,
            status=project.status,
            summary_included=include_summary and bool(project.orchestrator_summary),
            estimated_tokens=total_tokens
        )

        return {
            "source": "project_description",
            "data": data,
            "metadata": {
                "project_id": project_id,
                "tenant_key": tenant_key
            }
        }
