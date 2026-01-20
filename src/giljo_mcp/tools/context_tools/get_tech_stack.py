"""MCP tool for fetching tech stack information.

Reuses logic from:
- mission_planner._format_tech_stack() (lines 927-999)
- Product model tech stack fields

Always returns ALL tech stack fields (no truncation).
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
    offset: int = 0,
    limit: int = None,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Fetch tech stack information for given product.

    Handover 0316: Reads from Product.config_data.tech_stack JSONB object (not direct columns).
    Handover 0351: Removed sections parameter - always returns ALL fields.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        offset: Skip first N items (reserved for future pagination)
        limit: Max items to return (reserved for future pagination)
        db_manager: Database manager instance
    Pagination (Future):
        offset and limit parameters are reserved for future implementation.
        Currently ignored - full implementation deferred to future handover.

    Returns:
        Dict with tech stack from config_data.tech_stack:
        {
            "source": "tech_stack",
            "data": {
                "programming_languages": ["Python", "TypeScript"],
                "frontend_frameworks": ["Vue 3"],
                "backend_frameworks": ["FastAPI"],
                "databases": ["PostgreSQL"],
                "infrastructure": ["Docker"],
                "dev_tools": ["Git"],
                "target_platforms": ["windows", "linux"]  # Handover 0425
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
            tenant_key="tenant_abc"
        )
    """
    logger.info(
        "fetching_tech_stack_context",
        product_id=product_id,
        tenant_key=tenant_key
    )

    if db_manager is None:
        logger.error("db_manager is required", operation="get_tech_stack")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
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
                "data": {},
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "error": "product_not_found"
                }
            }

        # Handover 0316: Access config_data JSONB (not direct columns)
        # Handover 0351: Removed sections parameter - always returns ALL fields
        config_data = product.config_data or {}
        tech_stack = config_data.get("tech_stack", {})

        # Handover 0425: Include target_platforms from Product model
        data = {
            "programming_languages": tech_stack.get("languages", []),
            "frontend_frameworks": tech_stack.get("frontend", []),
            "backend_frameworks": tech_stack.get("backend", []),
            "databases": tech_stack.get("database", []),
            "infrastructure": tech_stack.get("infrastructure", []),
            "dev_tools": tech_stack.get("dev_tools", []),
            "target_platforms": product.target_platforms or ["all"]
        }

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "tech_stack_fetched_from_config_data",
            product_id=product_id,
            tenant_key=tenant_key,
            has_config_data=bool(product.config_data),
            has_tech_stack=bool(config_data.get("tech_stack")),
            estimated_tokens=total_tokens
        )

        return {
            "source": "tech_stack",
            "data": data,
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "pagination_supported": False  # Reserved for future implementation
            }
        }
