# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Product Context Tool - Handover 0316, updated 0840c

Fetch general product information for context generation.
Returns Product Core fields: name, description, core_features, path, status.

Handover 0840c: core_features now read from Product.core_features column
(normalized from config_data->'features'->>'core').
"""

from typing import Any

import structlog
from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.products import Product


logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Estimate token count for data (simple heuristic: 1 token ~ 4 chars)"""
    import json

    text = json.dumps(data)
    return len(text) // 4


async def get_product_context(
    product_id: str, tenant_key: str, db_manager: DatabaseManager | None = None
) -> dict[str, Any]:
    """
    Fetch general product information (Product Core).

    Handover 0840c: core_features from Product.core_features column.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        db_manager: Database manager instance

    Returns:
        Dict with product info including core_features.

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.
    """
    logger.info("fetching_product_context", product_id=product_id, tenant_key=tenant_key)

    if db_manager is None:
        logger.error("db_manager is required", operation="get_product_context")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            logger.warning(
                "product_not_found", product_id=product_id, tenant_key=tenant_key, operation="get_product_context"
            )
            return {
                "source": "product_context",
                "data": {},
                "metadata": {"product_id": product_id, "tenant_key": tenant_key, "error": "product_not_found"},
            }

        core_features = product.core_features or ""

        data = {
            "product_name": product.name,
            "product_description": product.description or "",
            "project_path": product.project_path or "",
            "core_features": core_features,
            "brand_guidelines": product.brand_guidelines or "",
            "is_active": product.is_active,
            "created_at": product.created_at.isoformat() if product.created_at else None,
        }

        total_tokens = estimate_tokens(data)

        logger.info(
            "product_context_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            has_core_features=bool(core_features),
            estimated_tokens=total_tokens,
        )

        return {
            "source": "product_context",
            "data": data,
            "metadata": {"product_id": product_id, "tenant_key": tenant_key},
        }
