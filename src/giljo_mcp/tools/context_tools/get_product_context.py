"""
Product Context Tool - Handover 0316

Fetch general product information for context generation.
Returns Product Core fields: name, description, features, path, status.
"""

import structlog
from typing import Any, Dict, Optional
from sqlalchemy import select
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.database import DatabaseManager

logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Estimate token count for data (simple heuristic: 1 token ≈ 4 chars)"""
    import json
    text = json.dumps(data)
    return len(text) // 4


async def get_product_context(
    product_id: str,
    tenant_key: str,
    include_metadata: bool = False,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Fetch general product information (Product Core).

    Handover 0316: Returns basic product metadata and core features.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        include_metadata: Include meta_data JSONB field (default: False)
        db_manager: Database manager instance

    Returns:
        Dict with product info:
        {
            "source": "product_context",
            "data": {
                "product_name": "GiljoAI MCP",
                "product_description": "...",
                "project_path": "/path/to/project",
                "core_features": ["Feature 1", "Feature 2"],
                "is_active": true,
                "created_at": "2025-11-01T10:00:00",
                "meta_data": {...}  # Only if include_metadata=True
            },
            "metadata": {
                "product_id": "uuid",
                "tenant_key": "...",
                "estimated_tokens": 100
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.

    Example:
        result = await get_product_context(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc",
            include_metadata=False
        )
    """
    logger.info(
        "fetching_product_context",
        product_id=product_id,
        tenant_key=tenant_key,
        include_metadata=include_metadata
    )

    if db_manager is None:
        logger.error("db_manager is required", operation="get_product_context")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        # Fetch product with multi-tenant isolation
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
                operation="get_product_context"
            )
            return {
                "source": "product_context",
                "data": {},
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "error": "product_not_found"
                }
            }

        # Extract config_data fields
        config_data = product.config_data or {}
        features = config_data.get("features", {})
        core_features = features.get("core", [])

        # Build data dict
        data = {
            "product_name": product.name,
            "product_description": product.description or "",
            "project_path": product.project_path or "",
            "core_features": core_features,
            "is_active": product.is_active,
            "created_at": product.created_at.isoformat() if product.created_at else None
        }

        # Conditionally include metadata
        if include_metadata:
            data["meta_data"] = product.meta_data or {}

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "product_context_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            has_core_features=len(core_features) > 0,
            metadata_included=include_metadata,
            estimated_tokens=total_tokens
        )

        return {
            "source": "product_context",
            "data": data,
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key
            }
        }
