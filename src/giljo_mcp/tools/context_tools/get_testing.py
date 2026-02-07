"""
Testing Configuration Tool - Handover 0316

Fetch testing strategy and quality standards for context generation.
Returns quality_standards (direct field) + test_config from config_data.

Handover 0351: Removed depth parameter - always returns FULL data.
"""

from typing import Any, Dict, Optional

import structlog
from sqlalchemy import select

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.products import Product


logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Estimate token count for data (simple heuristic: 1 token ≈ 4 chars)"""
    import json

    text = json.dumps(data)
    return len(text) // 4


async def get_testing(product_id: str, tenant_key: str, db_manager: Optional[DatabaseManager] = None) -> Dict[str, Any]:
    """
    Fetch testing strategy and quality standards (Testing).

    Handover 0316: Returns quality_standards (direct field) + test_config from config_data.
    Handover 0351: Removed depth parameter - always returns FULL data.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        db_manager: Database manager instance

    Returns:
        Dict with testing config:
        {
            "source": "testing",
            "data": {
                "quality_standards": "80% coverage, zero bugs",
                "testing_strategy": "TDD with unit/integration tests",
                "coverage_target": 85,
                "testing_frameworks": ["pytest", "jest"],
                "test_commands": ["pytest tests/", "npm test"]
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
        result = await get_testing(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc"
        )
    """
    logger.info("fetching_testing_context", product_id=product_id, tenant_key=tenant_key)

    if db_manager is None:
        logger.error("db_manager is required", operation="get_testing")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        # Fetch product with multi-tenant isolation
        stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            logger.warning("product_not_found", product_id=product_id, tenant_key=tenant_key, operation="get_testing")
            return {
                "source": "testing",
                "data": {},
                "metadata": {"product_id": product_id, "tenant_key": tenant_key, "error": "product_not_found"},
            }

        # Extract config_data fields
        config_data = product.config_data or {}
        test_config = config_data.get("test_config", {})

        # Handover 0351: Always return FULL data
        data = {
            "quality_standards": product.quality_standards or "",
            "testing_strategy": test_config.get("strategy", ""),
            "coverage_target": test_config.get("coverage_target", 80),
            "testing_frameworks": test_config.get("frameworks", []),
            "test_commands": config_data.get("test_commands", []),
        }

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "testing_context_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            has_quality_standards=bool(product.quality_standards),
            has_test_config=bool(test_config),
            estimated_tokens=total_tokens,
        )

        return {"source": "testing", "data": data, "metadata": {"product_id": product_id, "tenant_key": tenant_key}}
