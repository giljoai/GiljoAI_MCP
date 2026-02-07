"""MCP tool for fetching 360 memory (sequential project history) with depth control.

Updated in Handover 0390b to read from product_memory_entries table instead of JSONB.

Uses ProductMemoryRepository to fetch normalized memory entries from database.

Token Budget by Depth:
- 1: Last 1 project (~500 tokens)
- 3: Last 3 projects (~1500 tokens)
- 5: Last 5 projects (~2500 tokens)
- 10: Last 10 projects (~5000 tokens)
"""

from typing import Any, Dict, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import Product
from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository


logger = structlog.get_logger(__name__)


def estimate_tokens(data: Any) -> int:
    """Rough token estimation (1 token ≈ 4 chars)."""
    import json

    text = json.dumps(data) if not isinstance(data, str) else data
    return len(text) // 4


async def get_360_memory(
    product_id: str,
    tenant_key: str,
    last_n_projects: int = 3,
    offset: int = 0,
    limit: int = None,
    db_manager: Optional[DatabaseManager] = None,
    session: Optional[AsyncSession] = None,  # For testing only
) -> Dict[str, Any]:
    """
    Fetch 360 memory (sequential project history) for given product with depth control and pagination.

    Updated in Handover 0390b to read from product_memory_entries table.
    Uses ProductMemoryRepository to fetch normalized entries instead of JSONB field.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        last_n_projects: Total projects to consider (from table)
        offset: Number of projects to skip (for pagination)
        limit: Max projects to return (None = return all up to last_n_projects)
        db_manager: Database manager instance

    Returns:
        Dict with sequential history and metadata:
        {
            "source": "360_memory",
            "depth": 3,
            "data": [
                {
                    "sequence": 3,
                    "type": "project_closeout",
                    "project_id": "uuid",
                    "project_name": "Feature X",
                    "summary": "...",
                    "key_outcomes": [...],
                    "decisions_made": [...],
                    "git_commits": [...],
                    "timestamp": "2025-11-16T10:00:00Z"
                }
            ],
            "metadata": {
                "product_id": "uuid",
                "tenant_key": "...",
                "total_projects": 12,
                "last_n_projects": 3,
                "offset": 0,
                "limit": 3,
                "returned_projects": 3,
                "has_more": false,
                "next_offset": null,
                "estimated_tokens": 1500
            }
        }

    Multi-Tenant Isolation:
        All queries filter by tenant_key and product_id.

    Pagination Example:
        # Fetch projects 0-4
        batch1 = await get_360_memory(last_n_projects=10, offset=0, limit=5)
        # Fetch projects 5-9
        batch2 = await get_360_memory(last_n_projects=10, offset=5, limit=5)

    Example:
        result = await get_360_memory(
            product_id="123e4567-e89b-12d3-a456-426614174000",
            tenant_key="tenant_abc",
            last_n_projects=3,
            offset=0,
            limit=2
        )
    """
    logger.info(
        "fetching_360_memory_context",
        product_id=product_id,
        tenant_key=tenant_key,
        depth=last_n_projects,
        offset=offset,
        limit=limit,
    )

    if db_manager is None and session is None:
        logger.error("db_manager or session is required", operation="get_360_memory")
        raise ValueError("db_manager or session parameter is required")

    # Use provided session (for testing) or create new one
    if session is not None:
        # Use provided session directly (for testing)
        session_to_use = session
        should_close = False
    else:
        # Create new session from db_manager
        session_to_use = await db_manager.get_session_async().__aenter__()
        should_close = True

    try:
        # Verify product exists for tenant isolation
        stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
        result = await session_to_use.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            logger.warning(
                "product_not_found", product_id=product_id, tenant_key=tenant_key, operation="get_360_memory"
            )
            return {
                "source": "360_memory",
                "depth": last_n_projects,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_projects": 0,
                    "last_n_projects": last_n_projects,
                    "offset": offset,
                    "limit": limit or 0,
                    "returned_projects": 0,
                    "has_more": False,
                    "next_offset": None,
                    "error": "product_not_found",
                },
            }

        # Use repository to fetch memory entries from table
        repo = ProductMemoryRepository()

        # First, get total count (fetch all to determine total)
        all_entries = await repo.get_entries_by_product(
            session=session_to_use,
            product_id=product_id,
            tenant_key=tenant_key,
            include_deleted=False,
        )
        total_projects = len(all_entries)

        if total_projects == 0:
            logger.debug("no_memory_entries", product_id=product_id, operation="get_360_memory")
            return {
                "source": "360_memory",
                "depth": last_n_projects,
                "data": [],
                "metadata": {
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "total_projects": 0,
                    "last_n_projects": last_n_projects,
                    "offset": offset,
                    "limit": limit or 0,
                    "returned_projects": 0,
                    "has_more": False,
                    "next_offset": None,
                },
            }

        # Fetch entries with pagination (repository already sorts by sequence DESC)
        entries = await repo.get_entries_by_product(
            session=session_to_use,
            product_id=product_id,
            tenant_key=tenant_key,
            limit=last_n_projects,
            offset=0,
            include_deleted=False,
        )

        # Convert to dicts (matches existing format via to_dict())
        filtered_history = [entry.to_dict() for entry in entries]

        # Apply pagination within the filtered results
        effective_limit = limit if limit is not None else last_n_projects
        paginated_history = filtered_history[offset : offset + effective_limit]

        # Calculate pagination metadata
        has_more = (offset + len(paginated_history)) < len(filtered_history)
        next_offset = offset + len(paginated_history) if has_more else None

        # Calculate token estimate
        total_tokens = estimate_tokens(paginated_history)

        logger.info(
            "360_memory_fetched",
            product_id=product_id,
            tenant_key=tenant_key,
            depth=last_n_projects,
            offset=offset,
            limit=effective_limit,
            total_projects=total_projects,
            returned_projects=len(paginated_history),
            has_more=has_more,
            estimated_tokens=total_tokens,
        )

        return {
            "source": "360_memory",
            "depth": last_n_projects,
            "data": paginated_history,
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "total_projects": total_projects,
                "last_n_projects": last_n_projects,
                "offset": offset,
                "limit": effective_limit,
                "returned_projects": len(paginated_history),
                "has_more": has_more,
                "next_offset": next_offset,
            },
        }
    finally:
        if should_close and session_to_use:
            await session_to_use.close()
