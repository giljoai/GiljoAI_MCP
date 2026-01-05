"""MCP tool for fetching git commit history with depth control.

Reuses logic from:
- Product.product_memory.git_integration field (GitHub integration toggle)
- Product.product_memory.sequential_history[].git_commits arrays

Token Budget by Depth:
- 10: Last 10 commits (~500 tokens)
- 25: Last 25 commits (~1250 tokens)
- 50: Last 50 commits (~2500 tokens)
- 100: Last 100 commits (~5000 tokens)
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


async def get_git_history(
    product_id: str,
    tenant_key: str,
    commits: int = 25,
    offset: int = 0,
    limit: int = None,
    db_manager: Optional[DatabaseManager] = None
) -> Dict[str, Any]:
    """
    Fetch git commit history for given product with depth control.

    Extracts git commits from product_memory.sequential_history array.
    Returns empty if GitHub integration is disabled.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        commits: Number of recent commits to return (10, 25, 50, or 100)
        offset: Skip first N items (reserved for future pagination)
        limit: Max items to return (reserved for future pagination)
        db_manager: Database manager instance

    Pagination (Future):
        offset and limit parameters are reserved for future implementation.
        Currently ignored - full implementation deferred to future handover.

    Returns:
        Dict with git commits and metadata:
        {
            "source": "git_history",
            "depth": 25,
            "data": [
                {
                    "hash": "abc123",
                    "message": "feat: Add feature X",
                    "author": "developer@example.com",
                    "timestamp": "2025-11-16T10:00:00Z"
                }
            ],
            "metadata": {
                "product_id": "uuid",
                "tenant_key": "...",
                "total_commits": 150,
                "returned_commits": 25,
                "estimated_tokens": 1250,
                "git_integration_enabled": true
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.

    Example:
        result = await get_git_history(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc",
            commits=25
        )
    """
    logger.info(
        "fetching_git_history_context",
        product_id=product_id,
        tenant_key=tenant_key,
        depth=commits
    )

    if db_manager is None:
        logger.error("db_manager is required", operation="get_git_history")
        raise ValueError("db_manager parameter is required")

    async with db_manager.get_session_async() as session:
        # Fetch product with product_memory JSONB field
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
                operation="get_git_history"
            )
            return {
                "source": "git_history",
                "depth": commits,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_commits": 0,
                    "returned_commits": 0,
                    "git_integration_enabled": False,
                    "error": "product_not_found"
                }
            }

        # Check if product has product_memory
        if not product.product_memory:
            logger.debug(
                "no_product_memory",
                product_id=product_id,
                operation="get_git_history"
            )
            return {
                "source": "git_history",
                "depth": commits,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_commits": 0,
                    "returned_commits": 0,
                    "git_integration_enabled": False
                }
            }

        # Check if GitHub integration is enabled
        git_config = product.product_memory.get("git_integration", {})
        git_enabled = git_config.get("enabled", False)

        if not git_enabled:
            logger.debug(
                "git_integration_disabled",
                product_id=product_id,
                operation="get_git_history"
            )
            return {
                "source": "git_history",
                "depth": commits,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_commits": 0,
                    "returned_commits": 0,
                    "git_integration_enabled": False,
                    "reason": "git_integration_disabled"
                }
            }

        # Extract git commits from sequential_history array
        sequential_history = product.product_memory.get("sequential_history", [])
        all_commits = []

        # Aggregate commits from all history entries
        for entry in sequential_history:
            entry_commits = entry.get("git_commits", [])
            all_commits.extend(entry_commits)

        if not all_commits:
            logger.debug(
                "no_git_commits_found",
                product_id=product_id,
                operation="get_git_history"
            )
            return {
                "source": "git_history",
                "depth": commits,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_commits": 0,
                    "returned_commits": 0,
                    "git_integration_enabled": True
                }
            }

        # Return last N commits (most recent)
        filtered_commits = all_commits[-commits:] if all_commits else []

        # Reverse to show newest first
        filtered_commits = list(reversed(filtered_commits))

        # Calculate token estimate
        total_tokens = estimate_tokens(filtered_commits)

        logger.info(
            "git_history_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            depth=commits,
            total_commits=len(all_commits),
            returned_commits=len(filtered_commits),
            estimated_tokens=total_tokens
        )

        return {
            "source": "git_history",
            "depth": commits,
            "data": filtered_commits,
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "total_commits": len(all_commits),
                "returned_commits": len(filtered_commits),
                "git_integration_enabled": True,
                "pagination_supported": False  # Reserved for future implementation
            }
        }
