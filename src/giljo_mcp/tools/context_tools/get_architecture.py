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
    db_manager: Optional[DatabaseManager] = None,
    selected_fields: Optional[Dict[str, bool]] = None
) -> Dict[str, Any]:
    """
    Fetch architecture documentation for given product with depth control.

    Handover 0316: Reads from Product.config_data.architecture JSONB object.
    Returns architecture fields: pattern, design_patterns, api_style, notes.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        depth: Detail level ("overview" or "detailed")
        offset: Skip first N items (reserved for future pagination)
        limit: Max items to return (reserved for future pagination)
        db_manager: Database manager instance
        selected_fields: Optional dict mapping field keys to bool (v3.0 granular selection)
                        Fields: pattern, design_patterns, api_style, notes, layers, components

    Pagination (Future):
        offset and limit parameters are reserved for future implementation.
        Currently ignored - full implementation deferred to future handover.

    Returns:
        Dict with architecture from config_data.architecture:
        {
            "source": "architecture",
            "depth": "overview",
            "data": {
                "primary_pattern": "Microservices",
                "design_patterns": "Repository, Service Layer",
                "api_style": "RESTful",
                "architecture_notes": "..."
            },
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

    async with db_manager.get_session_async() as session:
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

        if not full_architecture_text or full_architecture_text == "Primary Pattern: \nDesign Patterns: \nAPI Style: \nNotes:":
            logger.debug(
                "no_architecture_notes",
                product_id=product_id,
                operation="get_architecture"
            )
            return {
                "source": "architecture",
                "depth": depth,
                "data": {
                    "primary_pattern": "",
                    "design_patterns": "",
                    "api_style": "",
                    "architecture_notes": ""
                },
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "estimated_tokens": 0,
                    "truncated": False
                }
            }

        # Handover 0319: Support granular field selection (v3.0)
        truncated = False
        if selected_fields is not None:
            # Use v3.0 granular field selection
            data = {}
            if selected_fields.get("pattern", True):
                data["primary_pattern"] = primary_pattern
            if selected_fields.get("design_patterns", True):
                data["design_patterns"] = design_patterns
            if selected_fields.get("api_style", True):
                data["api_style"] = api_style
            if selected_fields.get("notes", True):
                data["architecture_notes"] = arch_notes
            # layers and components from config_data (future expansion)
            if selected_fields.get("layers", True):
                data["layers"] = architecture.get("layers", "")
            if selected_fields.get("components", True):
                data["components"] = architecture.get("components", "")
        elif depth == "overview":
            # v2.0 backward compatibility: Return abbreviated version
            data = {
                "primary_pattern": primary_pattern,
                "design_patterns": design_patterns[:100] + "..." if len(design_patterns) > 100 else design_patterns,
                "api_style": api_style,
                "architecture_notes": arch_notes[:200] + "..." if len(arch_notes) > 200 else arch_notes
            }
            truncated = len(design_patterns) > 100 or len(arch_notes) > 200
        else:  # "detailed"
            # v2.0 backward compatibility: Return full architecture
            data = {
                "primary_pattern": primary_pattern,
                "design_patterns": design_patterns,
                "api_style": api_style,
                "architecture_notes": arch_notes
            }

        # Calculate token estimate
        total_tokens = estimate_tokens(data)

        logger.info(
            "architecture_fetched_from_config_data",
            product_id=product_id,
            tenant_key=tenant_key,
            has_config_data=bool(product.config_data),
            has_architecture=bool(config_data.get("architecture")),
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
