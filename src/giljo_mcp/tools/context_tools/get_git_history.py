# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""MCP tool for fetching git commit history with depth control.

Updated in Handover 0390b to read from product_memory_entries table instead of JSONB.

Uses ProductMemoryRepository.get_git_history() to fetch aggregated commits.
BE-9103: the git-integration toggle is read from the canonical settings path
(``integrations.git_integration.enabled`` via SettingsService), NOT the legacy
per-product ``product_memory.git_integration`` blob.

Token Budget by Depth:
- 10: Last 10 commits (~500 tokens)
- 25: Last 25 commits (~1250 tokens)
- 50: Last 50 commits (~2500 tokens)
- 100: Last 100 commits (~5000 tokens)
"""
# Read-only tool -- uses direct session.execute() for SELECT queries (no writes)

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Product
from giljo_mcp.services.product_memory_service import ProductMemoryService
from giljo_mcp.services.settings_service import SettingsService


logger = logging.getLogger(__name__)


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
    db_manager: DatabaseManager | None = None,
    session: AsyncSession | None = None,  # For testing only
) -> dict[str, Any]:
    """
    Fetch git commit history for given product with depth control.

    Updated in Handover 0390b to read from product_memory_entries table.
    Uses ProductMemoryRepository.get_git_history() to aggregate commits.
    Returns empty if Git integration is disabled.

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
    logger.info("fetching_git_history_context product_id=%s tenant_key=%s depth=%s", product_id, tenant_key, commits)

    if db_manager is None and session is None:
        logger.error("db_manager or session is required operation=get_git_history")
        raise ValueError("db_manager or session parameter is required")

    if session is not None:
        return await _get_git_history_impl(session, product_id, tenant_key, commits)

    async with db_manager.get_session_async() as new_session:
        return await _get_git_history_impl(new_session, product_id, tenant_key, commits)


async def _get_git_history_impl(
    session: AsyncSession,
    product_id: str,
    tenant_key: str,
    commits: int,
) -> dict[str, Any]:
    """Inner implementation for get_git_history using a provided session."""
    # Verify product exists for tenant isolation
    stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        logger.warning(
            "product_not_found product_id=%s tenant_key=%s operation=get_git_history", product_id, tenant_key
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
                "error": "product_not_found",
            },
        }

    # BE-9103: canonical toggle read — settings integrations.git_integration.enabled,
    # not the legacy per-product product_memory blob (which the current UI never writes).
    git_enabled = await SettingsService(session, tenant_key).git_integration_enabled()

    if not git_enabled:
        logger.debug("git_integration_disabled product_id=%s operation=get_git_history", product_id)
        return {
            "source": "git_history",
            "depth": commits,
            "data": [],
            "directive": {
                "action": "fetch_from_local_repo",
                "command": f"git log --oneline -{commits}",
                "note": "Git history is not stored on the server. Run this command in the project directory.",
            },
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "total_commits": 0,
                "returned_commits": 0,
                "git_integration_enabled": False,
                "reason": "git_integration_disabled",
            },
        }

    # Use service to fetch git commits from table
    memory_service = ProductMemoryService(
        db_manager=None,  # session provided directly
        tenant_key=tenant_key,
    )
    all_commits = await memory_service.get_git_history(
        product_id=product_id,
        limit=commits,
        session=session,
    )

    if not all_commits:
        logger.debug("no_git_commits_found product_id=%s operation=get_git_history", product_id)
        return {
            "source": "git_history",
            "depth": commits,
            "data": [],
            "directive": {
                "action": "fetch_from_local_repo",
                "command": f"git log --oneline -{commits}",
                "note": "Git history is not stored on the server. Run this command in the project directory.",
            },
            "metadata": {
                "product_id": product_id,
                "tenant_key": tenant_key,
                "total_commits": 0,
                "returned_commits": 0,
                "git_integration_enabled": True,
            },
        }

    # Repository already returns sorted commits (newest first) and limited
    filtered_commits = all_commits

    # Calculate token estimate
    total_tokens = estimate_tokens(filtered_commits)

    logger.info(
        "git_history_fetched product_id=%s tenant_key=%s depth=%s total=%d returned=%d tokens=%d",
        product_id,
        tenant_key,
        commits,
        len(all_commits),
        len(filtered_commits),
        total_tokens,
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
            "pagination_supported": False,  # Reserved for future implementation
        },
    }
