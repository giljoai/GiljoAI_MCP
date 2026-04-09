# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""MCP tool for fetching tech stack information.

Handover 0840c: Reads from ProductTechStack table (normalized from config_data JSONB).
Always returns ALL tech stack fields (no truncation).
"""

from typing import Any

import structlog
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.products import Product

logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Rough token estimation (1 token ~ 4 chars)."""
    import json

    text = json.dumps(data) if not isinstance(data, str) else data
    return len(text) // 4


async def get_tech_stack(
    product_id: str, tenant_key: str, offset: int = 0, limit: int = None, db_manager: DatabaseManager | None = None
) -> dict[str, Any]:
    """
    Fetch tech stack information for given product.

    Handover 0840c: Reads from product_tech_stacks table (normalized).

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        offset: Skip first N items (reserved for future pagination)
        limit: Max items to return (reserved for future pagination)
        db_manager: Database manager instance

    Returns:
        Dict with tech stack data from product_tech_stacks table.

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.
    """
    logger.info("fetching_tech_stack_context", product_id=product_id, tenant_key=tenant_key)

    if db_manager is None:
        logger.error("db_manager is required", operation="get_tech_stack")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        stmt = (
            select(Product)
            .options(joinedload(Product.tech_stack))
            .where(Product.id == product_id, Product.tenant_key == tenant_key)
        )
        result = await session.execute(stmt)
        product = result.unique().scalar_one_or_none()

        if not product:
            logger.warning(
                "product_not_found", product_id=product_id, tenant_key=tenant_key, operation="get_tech_stack"
            )
            return {
                "source": "tech_stack",
                "data": {},
                "metadata": {"product_id": product_id, "tenant_key": tenant_key, "error": "product_not_found"},
            }

        ts = product.tech_stack
        data = {
            "programming_languages": (ts.programming_languages if ts else "") or "",
            "frontend_frameworks": (ts.frontend_frameworks if ts else "") or "",
            "backend_frameworks": (ts.backend_frameworks if ts else "") or "",
            "databases": (ts.databases_storage if ts else "") or "",
            "infrastructure": (ts.infrastructure if ts else "") or "",
            "dev_tools": (ts.dev_tools if ts else "") or "",
            "target_platforms": product.target_platforms or ["all"],
        }

        # Include platform booleans if tech stack exists
        if ts:
            data["target_windows"] = ts.target_windows
            data["target_linux"] = ts.target_linux
            data["target_macos"] = ts.target_macos
            data["target_android"] = ts.target_android
            data["target_ios"] = ts.target_ios
            data["target_cross_platform"] = ts.target_cross_platform

        total_tokens = estimate_tokens(data)

        logger.info(
            "tech_stack_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            has_tech_stack=ts is not None,
            estimated_tokens=total_tokens,
        )

        return {
            "source": "tech_stack",
            "data": data,
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "pagination_supported": False,
            },
        }
