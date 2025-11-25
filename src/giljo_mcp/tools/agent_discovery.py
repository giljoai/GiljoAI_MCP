"""
Dynamic agent discovery tool for orchestrators.

Provides on-demand access to available agent templates without
embedding them in prompts (saves 142 tokens per orchestrator instance).

Handover 0246c: Dynamic Agent Discovery & Token Reduction

Key Features:
- On-demand agent template discovery
- Multi-tenant isolation enforcement
- Version tracking with metadata
- Graceful handling of missing version fields
- Professional error handling with fallback messages
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.templates import AgentTemplate


logger = logging.getLogger(__name__)

# Constants for response formatting
MAX_DESCRIPTION_LENGTH = 200
DEFAULT_VERSION = "unknown"
DEFAULT_ROLE = "Specialized Agent"


def _format_agent_info(template: AgentTemplate) -> dict[str, Any]:
    """
    Format agent template into discovery response format.

    Args:
        template: AgentTemplate database model instance

    Returns:
        dict with formatted agent information

    Note:
        Handles missing fields gracefully with sensible defaults.
    """
    # Handle missing version gracefully
    version = template.version or DEFAULT_VERSION

    # Truncate description if too long
    description = ""
    if template.description:
        description = (
            template.description[:MAX_DESCRIPTION_LENGTH]
            if len(template.description) > MAX_DESCRIPTION_LENGTH
            else template.description
        )

    return {
        "name": template.name,
        "role": template.role or DEFAULT_ROLE,
        "description": description,
        "version_tag": version,
        "expected_filename": f"{template.name}_{version}.md",
        "created_at": template.created_at.isoformat() if template.created_at else None,
    }


async def get_available_agents(session: AsyncSession, tenant_key: str) -> dict[str, Any]:
    """
    Get available agent templates with version metadata.

    Used by orchestrators to discover available agents without
    requiring embedded templates in prompts.

    Args:
        session: Database session
        tenant_key: Tenant isolation key

    Returns:
        dict with agents list and version metadata

    Example Response:
        {
            "success": True,
            "data": {
                "agents": [
                    {
                        "name": "implementer",
                        "role": "Code Implementation Specialist",
                        "description": "...",
                        "version_tag": "1.2.0",
                        "expected_filename": "implementer_1.2.0.md",
                        "created_at": "2025-11-24T12:00:00"
                    }
                ],
                "count": 5,
                "fetched_at": "2025-11-24T12:30:00",
                "note": "Templates fetched dynamically (not embedded in prompt)"
            }
        }
    """
    try:
        # Input validation
        if not tenant_key or not isinstance(tenant_key, str):
            logger.warning("Invalid tenant_key provided to get_available_agents")
            return {
                "success": True,
                "data": {
                    "agents": [],
                    "count": 0,
                    "fetched_at": datetime.now(timezone.utc).isoformat(),
                    "note": "Invalid tenant key - no agents available",
                },
            }

        logger.info("Fetching available agents", extra={"tenant_key": tenant_key})

        # Fetch active templates for this tenant
        stmt = (
            select(AgentTemplate)
            .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active))
            .order_by(AgentTemplate.created_at)
        )

        result = await session.execute(stmt)
        templates = result.scalars().all()

        # Format response with version metadata
        agents = [_format_agent_info(template) for template in templates]

        logger.info(f"Found {len(agents)} available agents", extra={"tenant_key": tenant_key, "count": len(agents)})

        return {
            "success": True,
            "data": {
                "agents": agents,
                "count": len(agents),
                "fetched_at": datetime.now(timezone.utc).isoformat(),
                "note": "Templates fetched dynamically (not embedded in prompt)",
            },
        }

    except Exception:
        logger.exception("Failed to fetch available agents", extra={"tenant_key": tenant_key})
        return {
            "success": False,
            "error": "Database error occurred while fetching agents",
            "fallback": "Unable to discover agents. Check server connectivity.",
        }
