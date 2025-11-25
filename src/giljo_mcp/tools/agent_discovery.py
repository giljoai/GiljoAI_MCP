"""
Dynamic agent discovery tool for orchestrators.

Provides on-demand access to available agent templates without
embedding them in prompts (saves 142 tokens per orchestrator instance).

Handover 0246c: Dynamic Agent Discovery & Token Reduction
"""

from typing import Any, Dict
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from src.giljo_mcp.models.templates import AgentTemplate

logger = logging.getLogger(__name__)


async def get_available_agents(
    session: AsyncSession,
    tenant_key: str
) -> Dict[str, Any]:
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
        logger.info(
            "Fetching available agents",
            extra={"tenant_key": tenant_key}
        )

        # Fetch active templates for this tenant
        stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active == True
            )
        ).order_by(AgentTemplate.created_at)

        result = await session.execute(stmt)
        templates = result.scalars().all()

        # Format response with version metadata
        agents = []
        for template in templates:
            # Handle missing version gracefully
            version = template.version or "unknown"

            agent_info = {
                "name": template.name,
                "role": template.role or "Specialized Agent",
                "description": template.description[:200] if template.description else "",
                "version_tag": version,
                "expected_filename": f"{template.name}_{version}.md",
                "created_at": template.created_at.isoformat() if template.created_at else None
            }
            agents.append(agent_info)

        logger.info(
            f"Found {len(agents)} available agents",
            extra={"tenant_key": tenant_key, "count": len(agents)}
        )

        return {
            "success": True,
            "data": {
                "agents": agents,
                "count": len(agents),
                "fetched_at": datetime.utcnow().isoformat(),
                "note": "Templates fetched dynamically (not embedded in prompt)"
            }
        }

    except Exception as e:
        logger.error(
            f"Failed to fetch available agents: {e}",
            extra={"tenant_key": tenant_key}
        )
        return {
            "success": False,
            "error": str(e),
            "fallback": "Unable to discover agents. Check server connectivity."
        }
