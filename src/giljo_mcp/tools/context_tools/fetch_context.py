# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Unified context fetcher for GiljoAI MCP.

Handover 0350a: Single entry point for all context fetching.
Dispatches to internal get_* tools based on categories parameter.

Handover 0351: Removed depth params for tech_stack, architecture, testing.
Handover 0351: ENFORCED single-category calls to prevent token budget overflow.
Handover 0823b: Reads user depth_config from DB at runtime when not provided.

Token Budget Savings:
- Before: 9 tool schemas x ~100 tokens = ~900 tokens consumed at agent startup
- After: 1 tool schema x ~180 tokens = ~180 tokens consumed at agent startup
- Savings: ~720 tokens available for actual work

Security (SaaS):
- Single category per call enforced in code (not prompt instructions)
- Prevents token budget overflow from aggregated multi-category calls
- LLM cannot bypass - code-level enforcement
"""

from typing import Any

import structlog

from src.giljo_mcp.config.defaults import DEFAULT_DEPTH_CONFIG as _RAW_DEPTH_CONFIG
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import ValidationError
from src.giljo_mcp.tools.context_tools.get_360_memory import get_360_memory
from src.giljo_mcp.tools.context_tools.get_agent_templates import get_agent_templates
from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture
from src.giljo_mcp.tools.context_tools.get_git_history import get_git_history

# Internal tools (NOT exposed via MCP)
from src.giljo_mcp.tools.context_tools.get_product_context import get_product_context
from src.giljo_mcp.tools.context_tools.get_project import get_project
from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity
from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack
from src.giljo_mcp.tools.context_tools.get_testing import get_testing
from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document


logger = structlog.get_logger(__name__)

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
    "agent_templates": _CANONICAL_DEPTHS.get("agent_templates", "type_only"),
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

    from src.giljo_mcp.models.auth import User, UserFieldPriority

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
    except Exception:  # Broad catch: fail-open for category toggle, non-critical path
        logger.error("category_toggle_check_failed", category=category, tenant_key=tenant_key, exc_info=True)
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

    from src.giljo_mcp.models.auth import User

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
                logger.debug(
                    "depth_config_not_found",
                    tenant_key=tenant_key,
                    user_found=False,
                )
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
                logger.debug(
                    "depth_config_vision_normalized",
                    tenant_key=tenant_key,
                )

            logger.info(
                "depth_config_loaded_from_db",
                tenant_key=tenant_key,
                depth_keys=list(normalized.keys()),
            )
            return normalized

    except Exception:  # Broad catch: fail-open for depth config, returns None fallback
        logger.error(
            "depth_config_load_failed",
            tenant_key=tenant_key,
            exc_info=True,
        )
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
        "fetch_context_started",
        product_id=product_id,
        tenant_key=tenant_key,
        project_id=project_id,
        categories=categories,
        format=output_format,
        agent_name=agent_name,
    )

    # Handover 0351: ENFORCE single-category calls (SaaS security)
    # Code-level enforcement - LLM cannot bypass via prompt injection
    if categories is None:
        logger.warning("fetch_context_missing_category", tenant_key=tenant_key)
        return {
            "error": "SINGLE_CATEGORY_REQUIRED",
            "message": "fetch_context requires exactly ONE category per call. Call multiple times for multiple categories.",
            "valid_categories": ALL_CATEGORIES,
            "example": "fetch_context(categories=['tech_stack'], ...)",
            "metadata": {},
        }

    # Reject "all" - forces sequential calls
    if "all" in categories:
        logger.warning("fetch_context_all_rejected", tenant_key=tenant_key)
        return {
            "error": "ALL_NOT_ALLOWED",
            "message": "categories=['all'] is not allowed. Call fetch_context once per category to stay within token budget.",
            "valid_categories": ALL_CATEGORIES,
            "example": "fetch_context(categories=['vision_documents'], ...)",
            "metadata": {},
        }

    # Reject multi-category calls
    if len(categories) > 1:
        logger.warning("fetch_context_multi_category_rejected", tenant_key=tenant_key, categories_requested=categories)
        return {
            "error": "SINGLE_CATEGORY_REQUIRED",
            "message": f"Only ONE category per call allowed. You requested {len(categories)}: {categories}",
            "valid_categories": ALL_CATEGORIES,
            "example": "Call fetch_context separately for each category",
            "metadata": {},
        }

    # Validate the single category
    category = categories[0]
    if category not in CATEGORY_TOOLS:
        logger.warning("invalid_category", invalid_category=category, valid_categories=ALL_CATEGORIES)
        raise ValidationError(f"Invalid category: {category}. Valid categories: {ALL_CATEGORIES}")

    # Enforce user field priority toggles — block disabled categories
    if db_manager:
        enabled = await _is_category_enabled(category, tenant_key, db_manager)
        if not enabled:
            logger.info("fetch_context_category_disabled", category=category, tenant_key=tenant_key)
            return {
                "category": category,
                "data": [],
                "metadata": {"toggled_off": True, "message": f"Category '{category}' is disabled in user settings."},
            }

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

    # Fetch the single category (enforced above)
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
        data = result.get("data", {})
        directive = result.get("directive")
        error = None
    except Exception as e:  # Broad catch: tool boundary, logs and re-raises
        logger.error("category_fetch_error", category=category, error=str(e), exc_info=True)
        data = {}
        directive = None
        error = {"category": category, "error": str(e)}

    # Build response
    response = {
        "source": "fetch_context",
        "categories_requested": [category],
        "categories_returned": [category] if data else [],
        "data": {category: data} if output_format == "structured" else data,
        "metadata": {
            "format": output_format,
            "depth_config_applied": {category: effective_depths.get(category)},
        },
    }

    # Propagate directive from inner tool (e.g., git_history local repo fallback)
    if directive:
        response["directive"] = {category: directive}

    if error:
        response["errors"] = [error]

    logger.info("fetch_context_completed", category=category, had_error=error is not None)

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
        if depth:
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
