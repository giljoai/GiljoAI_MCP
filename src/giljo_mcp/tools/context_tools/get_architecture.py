"""MCP tool for fetching architecture documentation.

NEW TOOL - No existing code to reuse.
Fetches Product.config_data.architecture JSONB field.

Always returns FULL architecture data (no truncation).
"""

from typing import Any, Dict, Optional

import structlog
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
    product_id: str, tenant_key: str, db_manager: Optional[DatabaseManager] = None
) -> dict[str, Any]:
    """
    Fetch architecture documentation for given product.

    Handover 0316: Reads from Product.config_data.architecture JSONB object.
    Returns architecture fields: pattern, design_patterns, api_style, notes.

    Handover 0351: Removed depth parameter - always returns FULL data.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        db_manager: Database manager instance

    Returns:
        Dict with architecture from config_data.architecture:
        {
            "source": "architecture",
            "data": {
                "primary_pattern": "Microservices",
                "design_patterns": "Repository, Service Layer",
                "api_style": "RESTful",
                "architecture_notes": "Full architecture notes..."
            },
            "metadata": {
                "product_id": "uuid",
                "tenant_key": "...",
                "estimated_tokens": 300
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.

    Example:
        result = await get_architecture(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc"
        )
    """
    logger.info("fetching_architecture_context", product_id=product_id, tenant_key=tenant_key)

    if db_manager is None:
        logger.error("db_manager is required", operation="get_architecture")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        # Fetch product.architecture_notes
        stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            logger.warning(
                "product_not_found", product_id=product_id, tenant_key=tenant_key, operation="get_architecture"
            )
            return {
                "source": "architecture",
                "data": {},
                "metadata": {"product_id": product_id, "tenant_key": tenant_key, "error": "product_not_found"},
            }

        # Handover 0316: Access config_data JSONB (not architecture_notes column)
        config_data = product.config_data or {}
        architecture = config_data.get("architecture", {})

        # Extract architecture fields
        primary_pattern = architecture.get("pattern", "")
        design_patterns = architecture.get("design_patterns", "")
        api_style = architecture.get("api_style", "")
        arch_notes = architecture.get("notes", "")

        # Combine all fields for depth filtering
        full_architecture_text = f"""
Primary Pattern: {primary_pattern}
Design Patterns: {design_patterns}
API Style: {api_style}
Notes: {arch_notes}
""".strip()

        if (
            not full_architecture_text
            or full_architecture_text == "Primary Pattern: \nDesign Patterns: \nAPI Style: \nNotes:"
        ):
            logger.debug("no_architecture_notes", product_id=product_id, operation="get_architecture")
            return {
                "source": "architecture",
                "data": {"primary_pattern": "", "design_patterns": "", "api_style": "", "architecture_notes": ""},
                "metadata": {"product_id": product_id, "tenant_key": tenant_key},
            }

        # Handover 0351: Always return FULL architecture data (no truncation)
        data = {
            "primary_pattern": primary_pattern,
            "design_patterns": design_patterns,
            "api_style": api_style,
            "architecture_notes": arch_notes,
        }

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "architecture_fetched_from_config_data",
            product_id=product_id,
            tenant_key=tenant_key,
            has_config_data=bool(product.config_data),
            has_architecture=bool(config_data.get("architecture")),
            estimated_tokens=total_tokens,
        )

        return {
            "source": "architecture",
            "data": data,
            "metadata": {"product_id": product_id, "tenant_key": tenant_key},
        }
