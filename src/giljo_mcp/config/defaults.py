"""
Default Toggle and Depth Configuration for Context Management v3.0

This module defines the default toggle settings and depth controls for context
categories used in AI agent orchestration. Toggles control whether a category
is included (on/off). Depth controls determine how much detail is extracted.

Toggle System:
    Each context category has a boolean toggle:
    - True: Category is included in orchestrator instructions
    - False: Category is excluded from orchestrator instructions

    Categories:
        - product_core: Product name, description, core features
        - project_description: Current project metadata
        - memory_360: Cumulative project history (sequential closeouts)
        - tech_stack: Tech stack configuration (languages, frameworks, databases)
        - testing: Quality standards, testing strategy, frameworks
        - vision_documents: Chunked vision document uploads (paginated)
        - architecture: Architecture patterns, API style, design patterns
        - agent_templates: Agent template library (for task assignment)
        - git_history: Recent commits from git integration (toggle OFF by default)

Depth Controls:
    Each category's depth is controlled independently via depth_config JSONB column.
    Depth determines how much content is extracted (full vs abbreviated vs summary).

    Default Depth Settings:
        - vision_documents: "medium" (66% summary)
        - memory_360: 3 (last 3 projects)
        - git_history: 5 (last 5 commits, toggle OFF by default)
        - agent_templates: "type_only" (~250 tokens)

Usage:
    from giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY, DEFAULT_DEPTH_CONFIG

    user.field_priority_config = DEFAULT_FIELD_PRIORITY
    user.depth_config = DEFAULT_DEPTH_CONFIG

    is_enabled = get_toggle_for_category('tech_stack')  # True

Version History:
    1.0-2.1: Legacy priority system (removed in Handover 0820)
    3.0 (2026-03-15): Toggle-only system (Handover 0820)
        - Removed priority integers (1/2/3/4) and labels (CRITICAL/IMPORTANT/REFERENCE)
        - Simplified to boolean toggles per category
        - Depth controls unchanged

Related:
    - Handover 0820: Remove Context Priority Framing
    - Handover 0314: Depth Controls Implementation
    - api/endpoints/users.py: Toggle configuration endpoints
    - src/giljo_mcp/models/auth.py: User.field_priority_config column
"""

from typing import Any


DEFAULT_FIELD_PRIORITY: dict[str, Any] = {
    "version": "3.0",
    "priorities": {
        "product_core": {"toggle": True},
        "project_description": {"toggle": True},
        "memory_360": {"toggle": True},
        "tech_stack": {"toggle": True},
        "testing": {"toggle": True},
        "vision_documents": {"toggle": True},
        "architecture": {"toggle": True},
        "agent_templates": {"toggle": True},
        "git_history": {"toggle": False},  # OFF by default until Git Integration enabled
    },
}

DEFAULT_DEPTH_CONFIG: dict[str, Any] = {
    "version": "1.0",
    "depths": {
        "vision_documents": "medium",
        "memory_360": 3,
        "git_history": 25,
        "agent_templates": "type_only",
    },
}


def get_toggle_for_category(category: str) -> bool:
    """
    Get the toggle status for a specific category.

    Args:
        category: Category name (e.g., 'product_core', 'git_history')

    Returns:
        Toggle status (True=enabled, False=disabled), defaults to True if category not found
    """
    config = DEFAULT_FIELD_PRIORITY["priorities"].get(category)
    if isinstance(config, dict):
        return config.get("toggle", True)
    return True


def get_depth_for_category(category: str) -> Any:
    """
    Get the depth configuration for a specific category.

    Args:
        category: Category name (e.g., 'vision_documents', 'memory_360')

    Returns:
        Depth value (string or int depending on category), or None if not configured
    """
    return DEFAULT_DEPTH_CONFIG["depths"].get(category)


def validate_toggle_config() -> bool:
    """
    Validate that all toggle values are boolean.

    Returns:
        True if all toggles are valid

    Raises:
        TypeError: If any toggle is not boolean
        ValueError: If category config is malformed
    """
    for category, config in DEFAULT_FIELD_PRIORITY["priorities"].items():
        if not isinstance(config, dict):
            raise TypeError(f"Category '{category}' must be a dict with 'toggle' key")

        if "toggle" not in config:
            raise ValueError(f"Category '{category}' missing required key: 'toggle'")

        if not isinstance(config["toggle"], bool):
            raise TypeError(f"Invalid toggle value for category '{category}'. Must be boolean (True/False)")

    return True


# Validate on module import to catch configuration errors early
validate_toggle_config()
