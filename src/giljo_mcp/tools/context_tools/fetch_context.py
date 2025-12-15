"""
Unified context fetcher for GiljoAI MCP.

Handover 0350a: Single entry point for all context fetching.
Dispatches to internal get_* tools based on categories parameter.

Handover 0351: Removed depth params for tech_stack, architecture, testing.

Token Budget Savings:
- Before: 9 tool schemas x ~100 tokens = ~900 tokens consumed at agent startup
- After: 1 tool schema x ~180 tokens = ~180 tokens consumed at agent startup
- Savings: ~720 tokens available for actual work
"""

from typing import Any, Dict, List, Optional
import structlog

from src.giljo_mcp.database import DatabaseManager

# Internal tools (NOT exposed via MCP)
from src.giljo_mcp.tools.context_tools.get_product_context import get_product_context
from src.giljo_mcp.tools.context_tools.get_vision_document import get_vision_document
from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack
from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture
from src.giljo_mcp.tools.context_tools.get_testing import get_testing
from src.giljo_mcp.tools.context_tools.get_360_memory import get_360_memory
from src.giljo_mcp.tools.context_tools.get_git_history import get_git_history
from src.giljo_mcp.tools.context_tools.get_agent_templates import get_agent_templates
from src.giljo_mcp.tools.context_tools.get_project import get_project

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
}

# Default depth settings per category
DEFAULT_DEPTHS = {
    "product_core": None,        # No depth param
    "vision_documents": "medium",
    "tech_stack": None,          # No depth param (Handover 0351)
    "architecture": None,        # No depth param (Handover 0351)
    "testing": None,             # No depth param (Handover 0351)
    "memory_360": 5,             # last_n_projects
    "git_history": 25,           # commits
    "agent_templates": "type_only",  # Renamed from "standard" (Handover 0351)
    "project": None,             # No depth param
}

ALL_CATEGORIES = list(CATEGORY_TOOLS.keys())


async def fetch_context(
    product_id: str,
    tenant_key: str,
    project_id: Optional[str] = None,
    categories: Optional[List[str]] = None,
    depth_config: Optional[Dict[str, Any]] = None,
    apply_user_config: bool = True,
    format: str = "structured",
    db_manager: Optional[DatabaseManager] = None,
) -> Dict[str, Any]:
    """
    Unified context fetcher - dispatches to internal tools.

    Handover 0350a: Single MCP tool that replaces 9 individual tools,
    saving ~720 tokens in MCP schema overhead.

    Args:
        product_id: Product UUID
        tenant_key: Tenant isolation key
        project_id: Optional project UUID (required for 'project' category)
        categories: List of categories to fetch, or ["all"] for all categories
                   Valid: product_core, vision_documents, tech_stack, architecture,
                          testing, memory_360, git_history, agent_templates, project
        depth_config: Override depth settings per category
                     Example: {"vision_documents": "light", "agent_templates": "minimal"}
        apply_user_config: Apply user's saved priority/depth settings (default: True)
        format: Response format - "structured" (nested by category) or "flat" (merged)
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
                "apply_user_config": true,
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
        apply_user_config=apply_user_config,
        format=format
    )

    if categories is None:
        categories = ["all"]

    # Expand "all" to full category list
    if "all" in categories:
        categories = ALL_CATEGORIES.copy()

    # Validate categories
    invalid = [c for c in categories if c not in CATEGORY_TOOLS]
    if invalid:
        logger.warning(
            "invalid_categories",
            invalid_categories=invalid,
            valid_categories=ALL_CATEGORIES
        )
        return {
            "error": f"Invalid categories: {invalid}",
            "valid_categories": ALL_CATEGORIES,
            "metadata": {"estimated_tokens": 0}
        }

    # Load user config if requested
    effective_depths = DEFAULT_DEPTHS.copy()

    # Apply explicit depth overrides
    if depth_config:
        effective_depths.update(depth_config)

    # Fetch each category
    results = {}
    total_tokens = 0
    errors = []

    for category in categories:
        try:
            result = await _fetch_category(
                category=category,
                product_id=product_id,
                tenant_key=tenant_key,
                project_id=project_id,
                depth=effective_depths.get(category),
                db_manager=db_manager
            )
            results[category] = result.get("data", {})
            total_tokens += result.get("metadata", {}).get("estimated_tokens", 0)
        except Exception as e:
            logger.error(
                "category_fetch_error",
                category=category,
                error=str(e),
                exc_info=True
            )
            errors.append({"category": category, "error": str(e)})

    # Build response
    response = {
        "source": "fetch_context",
        "categories_requested": categories,
        "categories_returned": list(results.keys()),
        "data": results if format == "structured" else _flatten_results(results),
        "metadata": {
            "estimated_tokens": total_tokens,
            "format": format,
            "apply_user_config": apply_user_config,
            "depth_config_applied": effective_depths,
        }
    }

    if errors:
        response["errors"] = errors

    logger.info(
        "fetch_context_completed",
        categories_returned=len(results),
        total_tokens=total_tokens,
        had_errors=len(errors) > 0
    )

    return response


async def _fetch_category(
    category: str,
    product_id: str,
    tenant_key: str,
    project_id: Optional[str],
    depth: Any,
    db_manager: DatabaseManager,
) -> Dict[str, Any]:
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
            return {
                "data": {},
                "metadata": {
                    "error": "project_id required for 'project' category",
                    "estimated_tokens": 0
                }
            }
        kwargs["project_id"] = project_id
        kwargs["tenant_key"] = tenant_key
        # No depth param for project

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

    elif category == "tech_stack":
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        # No depth param (Handover 0351)

    elif category in ("architecture", "testing"):
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        # No depth param (Handover 0351)

    else:  # product_core
        kwargs["product_id"] = product_id
        kwargs["tenant_key"] = tenant_key
        # No depth param for product_core

    return await tool_func(**kwargs)


def _flatten_results(results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Flatten nested category results into single dict with prefixed keys.

    Transforms:
        {
            "product_core": {"name": "Test", "features": ["A"]},
            "tech_stack": {"languages": ["Python"]}
        }

    Into:
        {
            "product_core_name": "Test",
            "product_core_features": ["A"],
            "tech_stack_languages": ["Python"]
        }
    """
    flat = {}
    for category, data in results.items():
        if isinstance(data, dict):
            for key, value in data.items():
                flat[f"{category}_{key}"] = value
        else:
            flat[category] = data
    return flat
