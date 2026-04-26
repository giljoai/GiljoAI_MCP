# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unified context fetcher for GiljoAI MCP.

Handover 0350a: Single entry point for all context fetching.
Dispatches to internal get_* tools based on categories parameter.

Handover 0351: Removed depth params for tech_stack, architecture, testing.
Handover 0823b: Reads user depth_config from DB at runtime when not provided.
IMP-2: Batch category support -- multiple categories per call allowed.

Token Budget Savings:
- Before: 9 tool schemas x ~100 tokens = ~900 tokens consumed at agent startup
- After: 1 tool schema x ~180 tokens = ~180 tokens consumed at agent startup
- Savings: ~720 tokens available for actual work
"""
# Read-only tool -- uses direct session.execute() for SELECT queries (no writes)

import logging
from typing import Any

from giljo_mcp.config.defaults import DEFAULT_DEPTH_CONFIG as _RAW_DEPTH_CONFIG
from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import ValidationError
from giljo_mcp.tools.context_tools.get_360_memory import get_360_memory
from giljo_mcp.tools.context_tools.get_agent_templates import get_agent_templates
from giljo_mcp.tools.context_tools.get_architecture import get_architecture
from giljo_mcp.tools.context_tools.get_git_history import get_git_history

# Internal tools (NOT exposed via MCP)
from giljo_mcp.tools.context_tools.get_product_context import get_product_context
from giljo_mcp.tools.context_tools.get_project import get_project
from giljo_mcp.tools.context_tools.get_self_identity import get_self_identity
from giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack
from giljo_mcp.tools.context_tools.get_testing import get_testing
from giljo_mcp.tools.context_tools.get_vision_document import get_vision_document


logger = logging.getLogger(__name__)

# Category to internal tool mapping
CATEGORY_TOOLS = {
    "product_core": get_product_context,
    "vision_documents": get_vision_document,
    "tech_stack": get_tech_stack,
    "architecture": get_architecture,
    "testing": get_testing,
    "memory_360": get_360_memory,
    "git_history": get_git_history,
    "agent_templates": get_agent_templates,
    "project": get_project,
    "self_identity": get_self_identity,
}

# Derive from canonical source (defaults.py) - single source of truth (Handover 0823)
# Handover 0840d: DEFAULT_DEPTH_CONFIG is now a flat dict (no "depths" wrapper)
_CANONICAL_DEPTHS = _RAW_DEPTH_CONFIG
DEFAULT_DEPTHS = {
    "product_core": None,
    "vision_documents": _CANONICAL_DEPTHS.get("vision_documents", "medium"),
    "tech_stack": None,
    "architecture": None,
    "testing": None,
    "memory_360": _CANONICAL_DEPTHS.get("memory_last_n_projects", 3),
    "git_history": _CANONICAL_DEPTHS.get("git_commits", 25),
    "agent_templates": _CANONICAL_DEPTHS.get("agent_templates", "basic"),
    "project": None,
    "self_identity": None,
}

ALL_CATEGORIES = list(CATEGORY_TOOLS.keys())


# DB key -> internal key mapping for depth_config normalization (Handover 0823b).
# Shared with protocol_builder._get_user_config; defined here to avoid cross-imports.
_DEPTH_KEY_MAPPING: dict[str, str] = {
    "memory_last_n_projects": "memory_360",
    "git_commits": "git_history",
    "agent_templates": "agent_templates",
    "vision_documents": "vision_documents",
}


async def _is_category_enabled(
    category: str,
    tenant_key: str,
    db_manager: DatabaseManager,
) -> bool:
    """
    Check if a category is enabled in the user's field priority toggles.

    Categories without a toggle row (product_core, project, self_identity,
    agent_templates) are always enabled.

    Returns:
        True if enabled or no toggle exists, False if explicitly disabled.
    """
    # Categories that are always on (no toggle)
    always_on = {"product_core", "project", "self_identity", "agent_templates"}
    if category in always_on:
        return True

    from sqlalchemy import and_, select

    from giljo_mcp.models.auth import User, UserFieldPriority

    try:
        async with db_manager.get_session_async() as session:
            # Get user for this tenant
            user_result = await session.execute(
                select(User.id).where(and_(User.tenant_key == tenant_key, User.is_active)).limit(1)
            )
            user_id = user_result.scalar_one_or_none()
            if not user_id:
                return True  # No user found, allow by default

            # Check toggle
            prio_result = await session.execute(
                select(UserFieldPriority.enabled).where(
                    and_(
                        UserFieldPriority.user_id == user_id,
                        UserFieldPriority.tenant_key == tenant_key,
                        UserFieldPriority.category == category,
                    )
                )
            )
            enabled = prio_result.scalar_one_or_none()
            # No row means default enabled
            return enabled if enabled is not None else True
    except Exception as _exc:  # Broad catch: fail-open for category toggle, non-critical path
        logger.error("category_toggle_check_failed category=%s tenant_key=%s", category, tenant_key, exc_info=True)
        return True  # Fail open — don't block context on toggle errors


async def _load_user_depth_config(
    tenant_key: str,
    db_manager: DatabaseManager,
) -> dict[str, Any] | None:
    """
    Load the user's depth_config from the DB at runtime (Handover 0823b).

    Queries the first active user for the given tenant_key and normalizes
    their depth_config keys from DB format to internal format.

    Args:
        tenant_key: Tenant isolation key
        db_manager: Database manager instance

    Returns:
        Normalized depth config dict, or None if no user or no config found.
    """
    from sqlalchemy import and_, select

    from giljo_mcp.models.auth import User

    try:
        async with db_manager.get_session_async() as session:
            result = await session.execute(
                select(User)
                .where(
                    and_(
                        User.tenant_key == tenant_key,
                        User.is_active,
                    )
                )
                .limit(1)
            )
            user = result.scalar_one_or_none()

            if not user:
                logger.debug("depth_config_not_found tenant_key=%s user_found=False", tenant_key)
                return None

            # Handover 0840d: Read depth from columns, normalize keys to internal format
            raw_depth = {
                "vision_documents": user.depth_vision_documents,
                "memory_last_n_projects": user.depth_memory_last_n,
                "git_commits": user.depth_git_commits,
                "agent_templates": user.depth_agent_templates,
                "tech_stack_sections": user.depth_tech_stack_sections,
                "architecture_depth": user.depth_architecture,
            }

            normalized: dict[str, Any] = {}
            for db_key, value in raw_depth.items():
                internal_key = _DEPTH_KEY_MAPPING.get(db_key, db_key)
                normalized[internal_key] = value

            # Normalize vision_documents "optional" -> "light" (same as protocol_builder)
            if normalized.get("vision_documents") == "optional":
                normalized["vision_documents"] = "light"
                logger.debug("depth_config_vision_normalized tenant_key=%s", tenant_key)

            logger.info("depth_config_loaded_from_db tenant_key=%s depth_keys=%s", tenant_key, list(normalized.keys()))
            return normalized

    except Exception as _exc:  # Broad catch: fail-open for depth config, returns None fallback
        logger.error("depth_config_load_failed tenant_key=%s", tenant_key, exc_info=True)
        return None


async def fetch_context(
    product_id: str,
    tenant_key: str,
    project_id: str | None = None,
    categories: list[str | None] = None,
    depth_config: dict[str, Any | None] = None,
    output_format: str = "structured",
    agent_name: str | None = None,
    db_manager: DatabaseManager | None = None,
) -> dict[str, Any]:
    """
    Unified context fetcher - dispatches to internal tools.

    Handover 0350a: Single MCP tool that replaces 9 individual tools,
    saving ~720 tokens in MCP schema overhead.

    Handover 0430: Added self_identity category for agent self-awareness.

    Handover 0823b: When depth_config is not provided, reads the user's current
    depth settings from the DB via tenant_key, making depth live-tunable.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        project_id: Optional project UUID (required for 'project' category)
        categories: List of categories to fetch, or ["all"] for all categories
                   Valid: product_core, vision_documents, tech_stack, architecture,
                          testing, memory_360, git_history, agent_templates, project,
                          self_identity
        depth_config: Override depth settings per category. If None, reads from DB.
                     Example: {"vision_documents": "light", "agent_templates": "minimal"}
        format: Response format - "structured" (nested by category) or "flat" (merged)
        agent_name: Agent template name (required for 'self_identity' category)
        db_manager: Database manager instance

    Returns:
        Dict with context data organized by category, plus metadata:
        {
            "source": "fetch_context",
            "categories_requested": ["product_core", "tech_stack"],
            "categories_returned": ["product_core", "tech_stack"],
            "data": {
                "product_core": {...},
                "tech_stack": {...}
            },
            "metadata": {
                "estimated_tokens": 300,
                "format": "structured",
                "depth_config_applied": {...}
            }
        }

    Multi-Tenant Isolation:
        All internal tools enforce tenant_key filtering.

    Token Budget Reference:
        - product_core: ~100 tokens
        - vision_documents: 0-24K tokens (depth: none/light/medium/full)
        - tech_stack: 200-400 tokens (sections: required/all)
        - architecture: 300-1.5K tokens (depth: overview/detailed)
        - testing: 0-400 tokens (depth: none/basic/full)
        - memory_360: 500-5K tokens (last_n_projects: 1/3/5/10)
        - git_history: 500-5K tokens (commits: 10/25/50/100)
        - agent_templates: 400-2.4K tokens (detail: minimal/standard/full)
        - project: ~300 tokens
        - self_identity: ~1-3K tokens (Handover 0430)

    Example:
        # Fetch all context with defaults
        result = await fetch_context(
            product_id="uuid-123",
            tenant_key="tk_abc"
        )

        # Fetch specific categories with depth override
        result = await fetch_context(
            product_id="uuid-123",
            tenant_key="tk_abc",
            categories=["vision_documents", "agent_templates"],
            depth_config={"vision_documents": "light"}
        )
    """
    logger.info(
        "fetch_context_started product_id=%s tenant_key=%s project_id=%s categories=%s format=%s agent_name=%s",
        product_id,
        tenant_key,
        project_id,
        categories,
        output_format,
        agent_name,
    )

    # IMP-2: Categories parameter is required -- agents must be explicit
    if categories is None:
        logger.warning("fetch_context_missing_category tenant_key=%s", tenant_key)
        return {
            "error": "CATEGORIES_REQUIRED",
            "message": "categories parameter is required. Pass one or more category names.",
            "valid_categories": ALL_CATEGORIES,
            "example": "fetch_context(categories=['product_core', 'tech_stack'], ...)",
            "metadata": {},
        }

    # Reject "all" -- forces agents to be explicit about what they need
    if "all" in categories:
        logger.warning("fetch_context_all_rejected tenant_key=%s", tenant_key)
        return {
            "error": "ALL_NOT_ALLOWED",
            "message": (
                "categories=['all'] is not allowed. List the specific categories you need, "
                "e.g. categories=['product_core', 'tech_stack', 'architecture']."
            ),
            "valid_categories": ALL_CATEGORIES,
            "example": "fetch_context(categories=['product_core', 'tech_stack'], ...)",
            "metadata": {},
        }

    # Validate all requested categories upfront
    invalid = [c for c in categories if c not in CATEGORY_TOOLS]
    if invalid:
        logger.warning("invalid_categories invalid=%s valid=%s", invalid, ALL_CATEGORIES)
        raise ValidationError(f"Invalid categories: {invalid}. Valid categories: {ALL_CATEGORIES}")

    # Resolve effective depth settings (Handover 0823b)
    effective_depths = DEFAULT_DEPTHS.copy()

    if depth_config:
        # Agent explicitly provided depth -- use it (backwards compatibility)
        effective_depths.update(depth_config)
    elif db_manager:
        # No depth from agent -- read user's current settings from DB (Handover 0823b)
        user_depths = await _load_user_depth_config(tenant_key, db_manager)
        if user_depths:
            effective_depths.update(user_depths)

    # IMP-2: Batch fetch -- iterate over all requested categories
    all_data: dict[str, Any] = {}
    all_directives: dict[str, Any] = {}
    all_errors: list[dict[str, str]] = []
    categories_returned: list[str] = []

    for category in categories:
        # Enforce user field priority toggles -- skip disabled categories silently
        if db_manager:
            enabled = await _is_category_enabled(category, tenant_key, db_manager)
            if not enabled:
                logger.info("fetch_context_category_disabled category=%s tenant_key=%s", category, tenant_key)
                continue

        try:
            result = await _fetch_category(
                category=category,
                product_id=product_id,
                tenant_key=tenant_key,
                project_id=project_id,
                depth=effective_depths.get(category),
                agent_name=agent_name,
                db_manager=db_manager,
            )
            cat_data = result.get("data", {})
            directive = result.get("directive")

            if cat_data:
                all_data[category] = cat_data
                categories_returned.append(category)
            if directive:
                all_directives[category] = directive
        except Exception as e:  # Broad catch: tool boundary, logs per-category errors
            logger.error("category_fetch_error category=%s error=%s", category, e, exc_info=True)
            all_errors.append({"category": category, "error": str(e)})

    # Build response
    depth_applied = {c: effective_depths.get(c) for c in categories}

    if output_format == "structured":
        response_data = all_data
    else:
        # Flat format: merge all category data into a single dict
        response_data = {}
        for cat_data in all_data.values():
            if isinstance(cat_data, dict):
                response_data.update(cat_data)
            else:
                response_data[str(type(cat_data))] = cat_data

    response: dict[str, Any] = {
        "source": "fetch_context",
        "categories_requested": list(categories),
        "categories_returned": categories_returned,
        "data": response_data,
        "metadata": {
            "format": output_format,
            "depth_config_applied": depth_applied,
        },
    }

    if all_directives:
        response["directive"] = all_directives

    if all_errors:
        response["errors"] = all_errors

    # INF-WriteShape: 30K-char hard ceiling with graceful field-drop.
    response = _apply_response_ceiling(response)

    logger.info(
        "fetch_context_completed requested=%s returned=%s error_count=%d",
        list(categories),
        categories_returned,
        len(all_errors),
    )

    return response


# INF-WriteShape: 30K-char ceiling -- single safety net when the assembled
# response would otherwise blow an agent's context budget. Strategy:
#   1. Iterate categories largest -> smallest by serialized size.
#   2. Within each, drop the largest droppable field of the largest entry.
#   3. Mark the affected entry with truncated:true.
#   4. Loop until under cap or only protected fields remain.
# Hard floor: NEVER drop required identity fields.
RESPONSE_CHAR_CEILING = 30_000
PROTECTED_ENTRY_FIELDS = frozenset({"id", "sequence", "project_name", "type", "timestamp"})


def _serialized_size(obj: Any) -> int:
    import json

    return len(json.dumps(obj))


def _apply_response_ceiling(response: dict[str, Any]) -> dict[str, Any]:
    """Iteratively drop the largest droppable field until response <= cap."""
    if _serialized_size(response) <= RESPONSE_CHAR_CEILING:
        return response

    data = response.get("data")
    if not isinstance(data, dict):
        return response

    truncation_applied = False
    # Bound the loop so a degenerate payload can't spin forever.
    for _ in range(2000):
        if _serialized_size(response) <= RESPONSE_CHAR_CEILING:
            break

        # Find largest category by serialized size
        target_category = None
        target_size = -1
        for cat, cat_data in data.items():
            size = _serialized_size(cat_data)
            if size > target_size:
                target_size = size
                target_category = cat

        if target_category is None:
            break

        cat_data = data[target_category]
        if not (isinstance(cat_data, list) and cat_data):
            # Cannot drop fields out of a non-list category structure safely
            break

        # Find largest entry in that category
        largest_idx = max(range(len(cat_data)), key=lambda i: _serialized_size(cat_data[i]))
        entry = cat_data[largest_idx]
        if not isinstance(entry, dict):
            break

        # Find largest droppable field in that entry
        # Skip 'truncated' (legacy field-drop signal we set ourselves below) and
        # 'has_full_body' (BE-5031 headlines-shape flag that survives ceiling).
        droppable = [
            (k, _serialized_size(v))
            for k, v in entry.items()
            if k not in PROTECTED_ENTRY_FIELDS and k not in ("truncated", "has_full_body")
        ]
        if not droppable:
            break

        droppable.sort(key=lambda kv: kv[1], reverse=True)
        field_to_drop, _ = droppable[0]
        entry.pop(field_to_drop, None)
        entry["truncated"] = True
        truncation_applied = True

    if truncation_applied:
        meta = response.setdefault("metadata", {})
        meta["truncation_applied"] = True
        meta["truncation_reason"] = "30K char ceiling"

    return response


async def _fetch_category(
    category: str,
    product_id: str,
    tenant_key: str,
    project_id: str | None,
    depth: Any,
    agent_name: str | None,
    db_manager: DatabaseManager,
) -> dict[str, Any]:
    """
    Dispatch to internal tool based on category.

    Maps category names to internal tool functions and translates
    depth configuration to tool-specific parameters.
    """
    tool_func = CATEGORY_TOOLS[category]

    # Build kwargs based on category and its depth parameter name
    kwargs = {"db_manager": db_manager}

    if category == "project":
        if not project_id:
            logger.warning("project_category_missing_project_id")
            return {"data": {}, "metadata": {"error": "project_id required for 'project' category"}}
        kwargs["project_id"] = project_id
        kwargs["tenant_key"] = tenant_key
        # No depth param for project

    elif category == "self_identity":
        if not agent_name:
            logger.warning("self_identity_category_missing_agent_name")
            return {
                "source": "self_identity",
                "data": {},
                "metadata": {"error": "agent_name required for 'self_identity' category"},
            }
        kwargs["agent_name"] = agent_name
        kwargs["tenant_key"] = tenant_key
        # No depth param for self_identity

    elif category == "agent_templates":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        if depth:
            kwargs["detail"] = depth

    elif category == "vision_documents":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        if depth:
            kwargs["chunking"] = depth

    elif category == "memory_360":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        # INF-WriteShape: depth_config["memory_360"] accepts:
        #   * int N -- last_n_projects = N, headlines shape (default)
        #   * "full" -- full bodies, last_n_projects from default
        #   * "headlines" -- explicit headlines (matches default)
        #   * dict {"last_n_projects": N, "shape": "full"|"headlines"}
        if isinstance(depth, dict):
            if "last_n_projects" in depth:
                kwargs["last_n_projects"] = int(depth["last_n_projects"])
            shape = depth.get("shape")
            if shape in ("full", "headlines"):
                kwargs["depth"] = shape
        elif isinstance(depth, str):
            if depth in ("full", "headlines"):
                kwargs["depth"] = depth
        elif depth:
            kwargs["last_n_projects"] = int(depth)

    elif category == "git_history":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        if depth:
            kwargs["commits"] = int(depth)

    elif category == "tech_stack" or category in ("architecture", "testing"):
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        # No depth param (Handover 0351)

    else:  # product_core
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        # No depth param for product_core

    return await tool_func(**kwargs)
