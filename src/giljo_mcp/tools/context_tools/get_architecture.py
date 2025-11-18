"""MCP tool for fetching architecture documentation with depth control.

NEW TOOL - No existing code to reuse.
Fetches Product.architecture_notes field.

Token Budget by Depth:
- "overview": First 500 chars (~300 tokens)
- "detailed": Full architecture notes (~1500 tokens)
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


async def get_architecture(
    product_id: str,
    tenant_key: str,
    depth: str = "overview",
    offset: int = 0,
    limit: int = None,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Fetch architecture documentation for given product with depth control.

    Returns Product.architecture_notes field content with truncation for overview mode.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        depth: Detail level ("overview" or "detailed")
        offset: Skip first N items (reserved for future pagination)
        limit: Max items to return (reserved for future pagination)
        db_manager: Database manager instance

    Pagination (Future):
        offset and limit parameters are reserved for future implementation.
        Currently ignored - full implementation deferred to future handover.

    Returns:
        Dict with architecture notes and metadata:
        {
            "source": "architecture",
            "depth": "overview",
            "data": "System architecture overview...",
            "metadata": {
                "product_id": "uuid",
                "tenant_key": "...",
                "estimated_tokens": 300,
                "truncated": true
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.

    Example:
        result = await get_architecture(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc",
            depth="overview"
        )
    """
    logger.info(
        "fetching_architecture_context",
        product_id=product_id,
        tenant_key=tenant_key,
        depth=depth
    )

    if db_manager is None:
        logger.error("db_manager is required", operation="get_architecture")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session() as session:
        # Fetch product.architecture_notes
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
                operation="get_architecture"
            )
            return {
                "source": "architecture",
                "depth": depth,
                "data": "",
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "estimated_tokens": 0,
                    "truncated": False,
                    "error": "product_not_found"
                }
            }

        # Check if architecture notes exist
        arch_notes = product.architecture_notes

        if not arch_notes:
            logger.debug(
                "no_architecture_notes",
                product_id=product_id,
                operation="get_architecture"
            )
            return {
                "source": "architecture",
                "depth": depth,
                "data": "",
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "estimated_tokens": 0,
                    "truncated": False
                }
            }

        # Apply depth filtering
        truncated = False
        if depth == "overview":
            # Return first 500 chars for overview
            if len(arch_notes) > 500:
                data = arch_notes[:500] + "..."
                truncated = True
            else:
                data = arch_notes
        else:  # "detailed"
            # Return full notes
            data = arch_notes

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "architecture_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            depth=depth,
            estimated_tokens=total_tokens,
            truncated=truncated
        )

        return {
            "source": "architecture",
            "depth": depth,
            "data": data,
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "estimated_tokens": total_tokens,
                "truncated": truncated,
                "pagination_supported": False  # Reserved for future implementation
            }
        }
