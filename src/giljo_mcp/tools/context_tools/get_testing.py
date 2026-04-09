# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Testing Configuration Tool - Handover 0316, updated 0840c

Fetch testing strategy and quality standards for context generation.
Handover 0840c: Reads from product_test_configs table (normalized from config_data JSONB).
quality_standards now comes from product_test_configs table.

Always returns FULL data (no truncation).
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.products import Product

logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Estimate token count for data (simple heuristic: 1 token ~ 4 chars)"""
    import json

    text = json.dumps(data)
    return len(text) // 4


async def get_testing(product_id: str, tenant_key: str, db_manager: DatabaseManager | None = None) -> dict[str, Any]:
    """
    Fetch testing strategy and quality standards.

    Handover 0840c: Reads from product_test_configs table (normalized).

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        db_manager: Database manager instance

    Returns:
        Dict with testing config from product_test_configs table.

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.
    """
    logger.info("fetching_testing_context", product_id=product_id, tenant_key=tenant_key)

    if db_manager is None:
        logger.error("db_manager is required", operation="get_testing")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        stmt = (
            select(Product)
            .options(joinedload(Product.test_config))
            .where(Product.id == product_id, Product.tenant_key == tenant_key)
        )
        result = await session.execute(stmt)
        product = result.unique().scalar_one_or_none()

        if not product:
            logger.warning("product_not_found", product_id=product_id, tenant_key=tenant_key, operation="get_testing")
            return {
                "source": "testing",
                "data": {},
                "metadata": {"product_id": product_id, "tenant_key": tenant_key, "error": "product_not_found"},
            }

        tc = product.test_config
        data = {
            "quality_standards": (tc.quality_standards if tc else "") or "",
            "testing_strategy": (tc.test_strategy if tc else "") or "",
            "coverage_target": (tc.coverage_target if tc else 80) or 80,
            "testing_frameworks": (tc.testing_frameworks if tc else "") or "",
        }

        total_tokens = estimate_tokens(data)

        logger.info(
            "testing_context_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            has_test_config=tc is not None,
            estimated_tokens=total_tokens,
        )

        return {"source": "testing", "data": data, "metadata": {"product_id": product_id, "tenant_key": tenant_key}}
