"""MCP tool for fetching tech stack information with depth control.

Reuses logic from:
- mission_planner._format_tech_stack() (lines 927-999)
- Product model tech stack fields

Token Budget by Depth:
- "required": Only required fields (programming_languages, frameworks, database) (~200 tokens)
- "all": All tech stack sections (~400 tokens)
"""

import structlog
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product

logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Rough token estimation (1 token ≈ 4 chars)."""
    import json
    text = json.dumps(data) if not isinstance(data, str) else data
    return len(text) // 4


async def get_tech_stack(
    product_id: str,
    tenant_key: str,
    sections: str = "all",
    offset: int = 0,
    limit: int = None,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Fetch tech stack information for given product with depth control.

    Reuses field extraction logic from mission_planner._format_tech_stack().
    Returns tech stack fields from Product model.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        sections: Detail level ("required" or "all")
        offset: Skip first N items (reserved for future pagination)
        limit: Max items to return (reserved for future pagination)
        db_manager: Database manager instance

    Pagination (Future):
        offset and limit parameters are reserved for future implementation.
        Currently ignored - full implementation deferred to future handover.

    Returns:
        Dict with tech stack and metadata:
        {
            "source": "tech_stack",
            "depth": "all",
            "data": {
                "programming_languages": ["Python", "TypeScript"],
                "frameworks": ["FastAPI", "Vue 3"],
                "database": ["PostgreSQL"],
                "deployment_platform": ["AWS"],
                "cloud_services": ["S3", "RDS"],
                "dev_tools": ["Git", "Docker"]
            },
            "metadata": {
                "product_id": "uuid",
                "tenant_key": "...",
                "estimated_tokens": 400
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.

    Example:
        result = await get_tech_stack(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc",
            sections="all"
        )
    """
    logger.info(
        "fetching_tech_stack_context",
        product_id=product_id,
        tenant_key=tenant_key,
        depth=sections
    )

    if db_manager is None:
        logger.error("db_manager is required", operation="get_tech_stack")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session() as session:
        # Fetch product tech stack fields
        stmt = select(Product).where(
            Product.id == product_id,
            Product.tenant_key == tenant_key
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            logger.warning(
                "product_not_found",
                product_id=product_id,
                tenant_key=tenant_key,
                operation="get_tech_stack"
            )
            return {
                "source": "tech_stack",
                "depth": sections,
                "data": {},
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "estimated_tokens": 0,
                    "error": "product_not_found"
                }
            }

        # Build tech stack data based on depth (reuse pattern from mission_planner)
        if sections == "required":
            # Return only required fields
            data = {
                "programming_languages": product.programming_languages or [],
                "frameworks": product.frameworks or [],
                "database": product.database or []
            }
        else:  # "all"
            # Return all tech stack fields
            data = {
                "programming_languages": product.programming_languages or [],
                "frameworks": product.frameworks or [],
                "database": product.database or [],
                "deployment_platform": product.deployment_platform or [],
                "cloud_services": product.cloud_services or [],
                "dev_tools": product.dev_tools or []
            }

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "tech_stack_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            depth=sections,
            estimated_tokens=total_tokens
        )

        return {
            "source": "tech_stack",
            "depth": sections,
            "data": data,
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "estimated_tokens": total_tokens,
                "pagination_supported": False  # Reserved for future implementation
            }
        }
