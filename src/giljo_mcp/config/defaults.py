"""
Default Priority and Depth Configuration for Context Management v2.0

This module defines the default priority levels and depth settings for context
categories used in AI agent orchestration. The priority system controls fetch
order and mandatory flags for context sources. Depth controls determine how
much detail is extracted from each category.

Handover 0313: Priority System Refactor (v1.0 → v2.0)
- v1.0: Priority = token reduction level (10/7/4 = full/moderate/abbreviated)
- v2.0: Priority = fetch order / mandatory flag (1/2/3/4 = CRITICAL/IMPORTANT/REFERENCE/OFF)

Nested Format (2025-01):
    Each field has TWO controls:
    - toggle: Boolean to enable/disable the field (True/False)
    - priority: Fetch order priority (1/2/3 = CRITICAL/IMPORTANT/REFERENCE)

    Fields with toggle=False are excluded from orchestrator instructions entirely.
    Fields with toggle=True are included based on priority tier.

Priority Tiers (v2.0):
    Priority 1 (CRITICAL - Orchestrator MUST call):
        - product_core: Product name, description, core features
        - project_description: Current project metadata (locked field - always CRITICAL)
        - memory_360: Cumulative project history (sequential closeouts)

        These MCP tools are mentioned with MANDATORY framing in orchestrator
        instructions. Orchestrator is expected to call these tools every time.

    Priority 2 (IMPORTANT - Orchestrator SHOULD call):
        - tech_stack: Tech stack configuration (languages, frameworks, databases)
        - testing: Quality standards, testing strategy, frameworks

        These MCP tools are mentioned with STRONG RECOMMENDATION in orchestrator
        instructions. Orchestrator should call unless budget is constrained.

    Priority 3 (REFERENCE - Orchestrator MAY call):
        - vision_documents: Chunked vision document uploads (paginated)
        - architecture: Architecture patterns, API style, design patterns
        - agent_templates: Agent template library (for task assignment)
        - git_history: Recent commits from git integration (toggle OFF by default)

        These MCP tools are mentioned as OPTIONAL SUPPLEMENTAL context in
        orchestrator instructions. Orchestrator calls if project scope requires.

Depth Controls (v2.0 - Handover 0314):
    Each category's depth is controlled independently via depth_config JSONB column.
    Depth determines how much content is extracted (full vs abbreviated vs summary).

    Default Depth Settings:
        - vision_documents: "medium" (66% summary)
        - memory_360: 3 (last 3 projects)
        - git_history: 5 (last 5 commits, toggle OFF by default)
        - agent_templates: "type_only" (~250 tokens)

Usage:
    from giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY, DEFAULT_DEPTH_CONFIG

    # Use as defaults for new users
    user.field_priority_config = DEFAULT_FIELD_PRIORITY
    user.depth_config = DEFAULT_DEPTH_CONFIG

    # Get categories by priority level
    critical_categories = get_categories_by_priority(1)
    # Returns: ['product_core', 'memory_360']

Version History:
    1.0 (2025-10-26): Initial implementation (13 individual fields, 10/7/4 priorities)
    1.1 (2025-10-27): Token budget increase (Handover 0049)
    1.2 (2025-11-17): Agent templates integration (Handover 0306)
    2.0 (2025-11-17): Priority system refactor (Handover 0313)
        - Changed from 13 individual fields → 6 context categories
        - Changed from priority 10/7/4 (token reduction) → priority 1/2/3/4 (fetch order)
        - Semantic shift: emphasis (what to fetch) vs trimming (how much to reduce)
        - Removed token_budget field (moved to depth controls in 0314)
    2.1 (2025-01-05): Nested format with toggle + priority keys
        - Added DEFAULT_DEPTH_CONFIG
        - git_history toggle OFF by default (until Git Integration enabled)
        - Updated helper functions for nested format

Related:
    - Handover 0312: Context Architecture v2.0 Design
    - Handover 0313: Priority System Refactor (this handover)
    - Handover 0314: Depth Controls Implementation
    - Handover 0315: MCP Thin Client Refactor
    - api/endpoints/users.py: Priority configuration endpoints
    - src/giljo_mcp/models/auth.py: User.field_priority_config column
"""

from typing import Any, Dict


DEFAULT_FIELD_PRIORITY: Dict[str, Any] = {
    "version": "2.1",
    "priorities": {
        # Priority 1 (CRITICAL): Orchestrator MUST call these MCP tools
        # These tools are mentioned with mandatory framing in instructions
        "product_core": {"toggle": True, "priority": 1},
        "project_description": {  # Locked - always CRITICAL
            "toggle": True,
            "priority": 1,
        },
        "memory_360": {"toggle": True, "priority": 1},
        # Priority 2 (IMPORTANT): Orchestrator SHOULD call if budget allows
        # These tools are mentioned with strong recommendation in instructions
        "tech_stack": {"toggle": True, "priority": 2},
        "testing": {"toggle": True, "priority": 2},
        # Priority 3 (REFERENCE): Orchestrator MAY call if project scope requires
        # These tools are mentioned as optional supplemental context
        "vision_documents": {"toggle": True, "priority": 3},
        "architecture": {"toggle": True, "priority": 3},
        "agent_templates": {"toggle": True, "priority": 3},
        "git_history": {
            "toggle": False,  # OFF by default until Git Integration enabled
            "priority": 3,
        },
    },
}


DEFAULT_DEPTH_CONFIG: Dict[str, Any] = {
    "version": "1.0",
    "depths": {
        # Vision documents: medium = 66% summary
        "vision_documents": "medium",
        # 360 Memory: last 3 projects
        "memory_360": 3,
        # Git history: last 5 commits (toggle OFF by default)
        "git_history": 5,
        # Agent templates: type_only = ~250 tokens (name, type, description only)
        "agent_templates": "type_only",
    },
}


def get_categories_by_priority(priority_level: int, include_toggled_off: bool = False) -> list[str]:
    """
    Get all categories matching the specified priority level.

    Args:
        priority_level: Priority tier (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE)
        include_toggled_off: If True, include categories with toggle=False (default: False)

    Returns:
        List of category names (e.g., ['product_core', 'memory_360'])

    Example:
        >>> critical_categories = get_categories_by_priority(1)
        >>> print(critical_categories)
        ['product_core', 'project_description', 'memory_360']
    """
    result = []
    for category, config in DEFAULT_FIELD_PRIORITY["priorities"].items():
        if config["priority"] == priority_level:
            if include_toggled_off or config["toggle"]:
                result.append(category)
    return result


def get_priority_for_category(category: str) -> int | None:
    """
    Get the priority level for a specific category.

    Args:
        category: Category name (e.g., 'product_core', 'vision_documents')

    Returns:
        Priority level (1=CRITICAL, 2=IMPORTANT, 3=REFERENCE) or None

    Example:
        >>> priority = get_priority_for_category('product_core')
        >>> print(priority)
        1
    """
    config = DEFAULT_FIELD_PRIORITY["priorities"].get(category)
    return config["priority"] if config else None


def get_toggle_for_category(category: str) -> bool:
    """
    Get the toggle status for a specific category.

    Args:
        category: Category name (e.g., 'product_core', 'git_history')

    Returns:
        Toggle status (True=enabled, False=disabled), defaults to True if category not found

    Example:
        >>> toggle = get_toggle_for_category('git_history')
        >>> print(toggle)
        False  # OFF by default until Git Integration enabled
    """
    config = DEFAULT_FIELD_PRIORITY["priorities"].get(category)
    return config["toggle"] if config else True


def get_depth_for_category(category: str) -> Any:
    """
    Get the depth configuration for a specific category.

    Args:
        category: Category name (e.g., 'vision_documents', 'memory_360')

    Returns:
        Depth value (string or int depending on category), or None if not configured

    Example:
        >>> depth = get_depth_for_category('vision_documents')
        >>> print(depth)
        'medium'
    """
    return DEFAULT_DEPTH_CONFIG["depths"].get(category)


def validate_priority_config() -> bool:
    """
    Validate that all priority values are within acceptable range (1-3) and toggle values are boolean.

    Returns:
        True if all priorities are valid, False otherwise

    Raises:
        ValueError: If any priority value is not in {1, 2, 3} or toggle is not boolean
    """
    valid_priorities = {1, 2, 3}
    for category, config in DEFAULT_FIELD_PRIORITY["priorities"].items():
        # Validate structure
        if not isinstance(config, dict):
            raise ValueError(f"Category '{category}' must be a dict with 'toggle' and 'priority' keys")

        if "toggle" not in config or "priority" not in config:
            raise ValueError(f"Category '{category}' missing required keys: 'toggle' and 'priority'")

        # Validate toggle is boolean
        if not isinstance(config["toggle"], bool):
            raise ValueError(f"Invalid toggle value for category '{category}'. Must be boolean (True/False)")

        # Validate priority is in valid range
        if config["priority"] not in valid_priorities:
            raise ValueError(
                f"Invalid priority {config['priority']} for category '{category}'. "
                f"Must be one of: 1 (CRITICAL), 2 (IMPORTANT), 3 (REFERENCE)"
            )

    # Ensure at least one category is CRITICAL (Priority 1) and toggled ON
    critical_categories = [
        cat for cat, cfg in DEFAULT_FIELD_PRIORITY["priorities"].items() if cfg["priority"] == 1 and cfg["toggle"]
    ]
    if not critical_categories:
        raise ValueError("At least one category must have Priority 1 (CRITICAL) with toggle=True")

    return True


# Validate on module import to catch configuration errors early
validate_priority_config()
