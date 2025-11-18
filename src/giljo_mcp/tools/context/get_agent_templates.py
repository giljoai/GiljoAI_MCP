"""MCP tool for fetching agent templates with depth control.

Reuses logic from:
- thin_prompt_generator._get_agent_templates() (line 778)
- AgentTemplate model queries with tenant isolation

Token Budget by Depth:
- "minimal": Names + 1-line purpose (~400 tokens)
- "standard": Names + purpose + key config (~800 tokens)
- "full": Complete template JSON (~2400 tokens)
"""

import structlog
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import AgentTemplate

logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Rough token estimation (1 token ≈ 4 chars)."""
    import json
    text = json.dumps(data) if not isinstance(data, str) else data
    return len(text) // 4


async def get_agent_templates(
    product_id: str,
    tenant_key: str,
    detail: str = "standard",
    offset: int = 0,
    limit: int = None,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Fetch agent templates for given tenant with depth control.

    Reuses query logic from thin_prompt_generator._get_agent_templates().
    Returns active agent templates with varying detail levels.

    Args:
        product_id: Product UUID (for context, not filtering - templates are tenant-wide)
        tenant_key: Tenant isolation key
        detail: Detail level ("minimal", "standard", "full")
        offset: Skip first N items (reserved for future pagination)
        limit: Max items to return (reserved for future pagination)
        db_manager: Database manager instance

    Pagination (Future):
        offset and limit parameters are reserved for future implementation.
        Currently ignored - full implementation deferred to future handover.

    Returns:
        Dict with agent templates and metadata:
        {
            "source": "agent_templates",
            "depth": "standard",
            "data": [
                {
                    "name": "implementer",
                    "purpose": "Backend implementation specialist",
                    "capabilities": ["Python", "FastAPI"],
                    "tools": ["git", "pytest"]
                }
            ],
            "metadata": {
                "product_id": "uuid",
                "tenant_key": "...",
                "num_templates": 8,
                "estimated_tokens": 800
            }
        }

    Multi-Tenant Isolation:
        Queries filter by tenant_key. Agent templates are tenant-wide, not product-specific.

    Example:
        result = await get_agent_templates(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc",
            detail="standard"
        )
    """
    logger.info(
        "fetching_agent_templates_context",
        product_id=product_id,
        tenant_key=tenant_key,
        depth=detail
    )

    if db_manager is None:
        logger.error("db_manager is required", operation="get_agent_templates")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session() as session:
        # Query agent templates for this tenant (reuse pattern from thin_prompt_generator)
        stmt = select(AgentTemplate).where(
            AgentTemplate.tenant_key == tenant_key,
            AgentTemplate.is_active == True
        ).order_by(AgentTemplate.name)

        result = await session.execute(stmt)
        templates = result.scalars().all()

        if not templates:
            logger.debug(
                "no_agent_templates",
                tenant_key=tenant_key,
                operation="get_agent_templates"
            )
            return {
                "source": "agent_templates",
                "depth": detail,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "num_templates": 0,
                    "estimated_tokens": 0
                }
            }

        # Convert to dict format based on detail level
        template_list = []

        for template in templates:
            if detail == "minimal":
                # Minimal: name + one-line purpose only
                template_dict = {
                    "name": template.name,
                    "purpose": (template.description or "Specialized agent")[:100]
                }

            elif detail == "standard":
                # Standard: name + purpose + key config fields (reuse from thin_prompt_generator)
                template_dict = {
                    "name": template.name,
                    "purpose": template.description or "Specialized agent",
                    "capabilities": template.meta_data.get("capabilities", []) if template.meta_data else [],
                    "tools": template.meta_data.get("tools", []) if template.meta_data else []
                }

            else:  # "full"
                # Full: complete template data
                template_dict = {
                    "name": template.name,
                    "role": template.role or "Specialized agent",
                    "description": template.description,
                    "capabilities": template.meta_data.get("capabilities", []) if template.meta_data else [],
                    "expertise": template.meta_data.get("expertise", []) if template.meta_data else [],
                    "typical_tasks": template.meta_data.get("typical_tasks", []) if template.meta_data else [],
                    "tools": template.meta_data.get("tools", []) if template.meta_data else [],
                    "is_active": template.is_active,
                    "created_at": str(template.created_at) if template.created_at else None,
                    "updated_at": str(template.updated_at) if template.updated_at else None
                }

            template_list.append(template_dict)

        # Calculate token estimate
        total_tokens = estimate_tokens(template_list)

        logger.info(
            "agent_templates_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            depth=detail,
            num_templates=len(template_list),
            estimated_tokens=total_tokens
        )

        return {
            "source": "agent_templates",
            "depth": detail,
            "data": template_list,
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "num_templates": len(template_list),
                "estimated_tokens": total_tokens,
                "pagination_supported": False  # Reserved for future implementation
            }
        }
