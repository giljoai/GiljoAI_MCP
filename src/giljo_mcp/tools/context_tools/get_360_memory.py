# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""MCP tool for fetching 360 memory (sequential project history) with depth control.

Updated in Handover 0390b to read from product_memory_entries table instead of JSONB.

Uses ProductMemoryRepository to fetch normalized memory entries from database.

Token Budget by Depth:
- 1: Last 1 project (~500 tokens)
- 3: Last 3 projects (~1500 tokens)
- 5: Last 5 projects (~2500 tokens)
- 10: Last 10 projects (~5000 tokens)
"""
# Read-only tool -- uses direct session.execute() for SELECT queries (no writes)

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Product
from giljo_mcp.services.product_memory_service import ProductMemoryService


logger = logging.getLogger(__name__)


def estimate_tokens(data: Any) -> int:
    """Rough token estimation (1 token ≈ 4 chars)."""
    import json

    text = json.dumps(data) if not isinstance(data, str) else data
    return len(text) // 4


# INF-WriteShape: depth modes for response shape (separate from last_n_projects).
# - "headlines" (default): id, sequence, project_name, type, timestamp,
#   summary truncated to first 200 chars + ellipsis, tags, truncated:true|false
# - "full": existing rich shape via to_dict(), truncated:false
DEPTH_HEADLINES = "headlines"
DEPTH_FULL = "full"
SUMMARY_HEADLINE_CAP = 200

# Step C: legacy tag mapping (analyzer-ratified 2026-04-25). Junk legacy tags
# get mapped to a canonical slug or dropped (mapped to None) on serialization.
# Reads are tolerant; writes are strict (controlled vocabulary lives in
# MemoryEntryWriteSchema). Unmapped legacy tags pass through unchanged so
# pre-existing entries remain readable.
LEGACY_TAG_MAPPING: dict[str, str | None] = {
    # Domain -> canonical
    "frontend": "frontend",
    "backend": "backend",
    "service": "backend",
    "endpoint": "api",
    "tool": "backend",
    "agent": "backend",
    "orchestrator": "backend",
    "documenter": "backend",
    "analyzer": "backend",
    "tools": "backend",
    "memory": "backend",
    "protocol": "api",
    "template": "backend",
    "database": "database",
    "migration": "migration",
    "URL": "infrastructure",
    "server-side": "backend",
    "page": "frontend",
    "users": "backend",
    "flow": "feature",
    # Change type -> canonical
    "added": "feature",
    "built": "feature",
    "shipped": "feature",
    "fixed": "bug-fix",
    "Fixed": "bug-fix",
    "removed": "refactor",
    "eliminated": "refactor",
    "cleanup": "refactor",
    "standardization": "refactor",
    "discipline": "refactor",
    "audit": "security",
    "security": "security",
    "edition": "feature",
    "writes": "refactor",
    "complete": "feature",
    "closed": "chore",
    "written": "docs",
    "entry": "docs",
    "project": "chore",
    # Pure noise -> drop (None means filter out on read)
    "from": None,
    "across": None,
    "files": None,
    "commits": None,
    "with": None,
    "via": None,
    "lines": None,
    "write": None,
    "direct": None,
    "giljoai": None,
    # Edition-specific (deliberately NOT in vocab) -> drop
    "saas": None,
    "demo/saas": None,
    "v1.1.6": None,
}


def _apply_legacy_tag_mapping(raw_tags: list[str]) -> list[str]:
    """Read-time legacy tag normalization (deduplicated, order-preserving).

    Mapped legacy slugs collapse to the canonical 16-tag vocabulary; ``None``
    entries are filtered out; unmapped tags pass through unchanged so legacy
    entries stay readable. The mapping is read-only -- new writes go through
    MemoryEntryWriteSchema and are rejected if outside the vocabulary.
    """
    mapped: list[str] = []
    seen: set[str] = set()
    for t in raw_tags or []:
        if t in LEGACY_TAG_MAPPING:
            replacement = LEGACY_TAG_MAPPING[t]
            if replacement is None or replacement in seen:
                continue
            seen.add(replacement)
            mapped.append(replacement)
        else:
            if t in seen:
                continue
            seen.add(t)
            mapped.append(t)
    return mapped


def _serialize_headline(entry) -> dict[str, Any]:
    """INF-WriteShape: minimal entry shape for the headlines-only default."""
    summary = entry.summary or ""
    truncated = len(summary) > SUMMARY_HEADLINE_CAP
    headline_summary = summary[:SUMMARY_HEADLINE_CAP] + "..." if truncated else summary
    return {
        "id": str(entry.id),
        "sequence": entry.sequence,
        "project_name": entry.project_name,
        "type": entry.entry_type,
        "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
        "summary": headline_summary,
        "tags": _apply_legacy_tag_mapping(entry.tags or []),
        "truncated": truncated,
    }


def _serialize_full(entry) -> dict[str, Any]:
    """INF-WriteShape: full entry shape (existing to_dict() with truncated flag)."""
    data = entry.to_dict()
    data["tags"] = _apply_legacy_tag_mapping(data.get("tags") or [])
    data["truncated"] = False
    return data


async def get_360_memory(
    product_id: str,
    tenant_key: str,
    last_n_projects: int = 3,
    offset: int = 0,
    limit: int = None,
    depth: str = DEPTH_HEADLINES,
    db_manager: DatabaseManager | None = None,
    session: AsyncSession | None = None,  # For testing only
) -> dict[str, Any]:
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
        "fetching_360_memory_context product_id=%s tenant_key=%s depth=%s offset=%s limit=%s",
        product_id,
        tenant_key,
        last_n_projects,
        offset,
        limit,
    )

    if db_manager is None and session is None:
        logger.error("db_manager or session is required operation=get_360_memory")
        raise ValueError("db_manager or session parameter is required")

    if depth not in (DEPTH_HEADLINES, DEPTH_FULL):
        depth = DEPTH_HEADLINES

    if session is not None:
        return await _get_360_memory_impl(session, product_id, tenant_key, last_n_projects, offset, limit, depth)

    async with db_manager.get_session_async() as new_session:
        return await _get_360_memory_impl(new_session, product_id, tenant_key, last_n_projects, offset, limit, depth)


async def _get_360_memory_impl(
    session: AsyncSession,
    product_id: str,
    tenant_key: str,
    last_n_projects: int,
    offset: int,
    limit: int | None,
    depth: str,
) -> dict[str, Any]:
    """Inner implementation for get_360_memory using a provided session."""
    # Verify product exists for tenant isolation
    stmt = select(Product).where(Product.id == product_id, Product.tenant_key == tenant_key)
    result = await session.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        logger.warning("product_not_found product_id=%s tenant_key=%s operation=get_360_memory", product_id, tenant_key)
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

    # Use service to fetch entries grouped by distinct projects
    memory_service = ProductMemoryService(
        db_manager=None,  # session provided directly
        tenant_key=tenant_key,
    )

    entries, total_projects = await memory_service.get_entries_by_last_n_projects(
        product_id=product_id,
        last_n_projects=last_n_projects,
        offset=offset,
        include_deleted=False,
        session=session,
    )

    if total_projects == 0:
        logger.debug("no_memory_entries product_id=%s operation=get_360_memory", product_id)
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
                "returned_projects": 0,
                "has_more": False,
                "next_offset": None,
            },
        }

    # INF-WriteShape: serialize per depth mode (headlines default | full opt-in)
    serializer = _serialize_full if depth == DEPTH_FULL else _serialize_headline
    paginated_history = [serializer(entry) for entry in entries]

    # Count distinct projects in this page
    returned_project_ids = {e.project_id for e in entries if e.project_id}
    returned_projects = len(returned_project_ids)

    # Pagination is by distinct project count
    has_more = (offset + returned_projects) < total_projects
    next_offset = offset + returned_projects if has_more else None

    # Fetch action_required tagged entries beyond depth window
    depth_entry_ids = {str(e.id) for e in entries}
    tagged_entries = await memory_service.get_entries_by_tag_prefix(
        product_id=product_id,
        prefix="action_required",
        session=session,
    )
    # Deduplicate: exclude entries already in depth-limited results
    extra_tagged = [e for e in tagged_entries if str(e.id) not in depth_entry_ids]
    # Action-required extras serialize in headline mode regardless of depth
    # so the count stays bounded; they're a side-channel surfaced for follow-up.
    action_required_items = [_serialize_headline(e) for e in extra_tagged]

    # Calculate token estimate
    total_tokens = estimate_tokens(paginated_history)

    logger.info(
        "360_memory_fetched product_id=%s tenant_key=%s depth=%s offset=%s total_projects=%s returned_projects=%s returned_entries=%s has_more=%s estimated_tokens=%s action_required_count=%s",
        product_id,
        tenant_key,
        last_n_projects,
        offset,
        total_projects,
        returned_projects,
        len(paginated_history),
        has_more,
        total_tokens,
        len(action_required_items),
    )

    result = {
        "source": "360_memory",
        "depth": last_n_projects,
        "data": paginated_history,
        "metadata": {
            "product_id": product_id,
            "tenant_key": tenant_key,
            "total_projects": total_projects,
            "last_n_projects": last_n_projects,
            "offset": offset,
            "returned_projects": returned_projects,
            "returned_entries": len(paginated_history),
            "has_more": has_more,
            "next_offset": next_offset,
        },
    }

    # INF-WriteShape: surface action_required extras DISTINCTLY from
    # returned_projects (today they were conflated). The count is always
    # present (even when zero) so consumers can rely on the key.
    result["metadata"]["action_required_extras"] = len(action_required_items)
    if action_required_items:
        result["action_required_items"] = action_required_items
        result["metadata"]["action_required_count"] = len(action_required_items)

    return result
