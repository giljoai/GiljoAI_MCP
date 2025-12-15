"""
Default Priority Configuration for Context Management v2.0

This module defines the default priority levels for context categories used in
AI agent orchestration. The priority system controls fetch order and mandatory
flags for context sources.

Handover 0313: Priority System Refactor (v1.0 → v2.0)
- v1.0: Priority = token reduction level (10/7/4 = full/moderate/abbreviated)
- v2.0: Priority = fetch order / mandatory flag (1/2/3/4 = CRITICAL/IMPORTANT/NICE/EXCLUDED)

Priority Tiers (v2.0):
    Priority 1 (CRITICAL - Orchestrator MUST call):
        - product_core: Product name, description, core features
        - project_description: Current project metadata (locked field - always CRITICAL)
        - memory_360: Cumulative project history (sequential closeouts)

        These MCP tools are mentioned with MANDATORY framing in orchestrator
        instructions. Orchestrator is expected to call these tools every time.

    Priority 2 (IMPORTANT - Orchestrator SHOULD call):
        - tech_stack: Tech stack configuration (languages, frameworks, databases)
        - git_history: Recent commits from git integration (if enabled)

        These MCP tools are mentioned with STRONG RECOMMENDATION in orchestrator
        instructions. Orchestrator should call unless budget is constrained.

    Priority 3 (REFERENCE - Orchestrator MAY call):
        - vision_documents: Chunked vision document uploads (paginated)
        - architecture: Architecture patterns, API style, design patterns
        - agent_templates: Agent template library (for task assignment)
        - testing: Quality standards, testing strategy, frameworks

        These MCP tools are mentioned as OPTIONAL SUPPLEMENTAL context in
        orchestrator instructions. Orchestrator calls if project scope requires.

    Priority 4 (OFF - Not mentioned):
        No default fields set to OFF. Users can toggle any field to OFF via UI.

        These MCP tools are NOT MENTIONED in orchestrator instructions. They
        are excluded entirely from context assembly.

Depth Controls (v2.0 - Handover 0314):
    Each category's depth is controlled independently via depth_config JSONB column.
    Depth determines how much content is extracted (full vs abbreviated vs summary).
    See handover 0314 for depth configuration implementation.

Usage:
    from giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

    # Use as default for new users
    user.field_priority_config = DEFAULT_FIELD_PRIORITY

    # Get categories by priority level
    critical_categories = get_categories_by_priority(1)
    # Returns: ['product_core', 'agent_templates']

Version History:
    1.0 (2025-10-26): Initial implementation (13 individual fields, 10/7/4 priorities)
    1.1 (2025-10-27): Token budget increase (Handover 0049)
    1.2 (2025-11-17): Agent templates integration (Handover 0306)
    2.0 (2025-11-17): Priority system refactor (Handover 0313)
        - Changed from 13 individual fields → 6 context categories
        - Changed from priority 10/7/4 (token reduction) → priority 1/2/3/4 (fetch order)
        - Semantic shift: emphasis (what to fetch) vs trimming (how much to reduce)
        - Removed token_budget field (moved to depth controls in 0314)

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
    "version": "2.0",
    "priorities": {
        # Priority 1 (CRITICAL): Orchestrator MUST call these MCP tools
        # These tools are mentioned with mandatory framing in instructions
        "product_core": 1,        # Product name, description, core features
        "project_description": 1, # Current project metadata (locked - always CRITICAL)
        "memory_360": 1,          # Cumulative project history (sequential closeouts)

        # Priority 2 (IMPORTANT): Orchestrator SHOULD call if budget allows
        # These tools are mentioned with strong recommendation in instructions
        "tech_stack": 2,          # Tech stack configuration (languages, frameworks, databases)
        "git_history": 2,         # Recent commits from git integration (if enabled)

        # Priority 3 (REFERENCE): Orchestrator MAY call if project scope requires
        # These tools are mentioned as optional supplemental context
        "vision_documents": 3,    # Chunked vision document uploads (paginated)
        "architecture": 3,        # Architecture patterns, API style, design patterns
        "agent_templates": 3,     # Agent template library (for task assignment)
        "testing": 3,             # Quality standards, testing strategy, frameworks
    },
}


def get_categories_by_priority(priority_level: int) -> list[str]:
    """
    Get all categories matching the specified priority level.

    Args:
        priority_level: Priority tier (1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED)

    Returns:
        List of category names (e.g., ['product_core', 'agent_templates'])

    Example:
        >>> critical_categories = get_categories_by_priority(1)
        >>> print(critical_categories)
        ['product_core', 'agent_templates']
    """
    return [
        category for category, priority in DEFAULT_FIELD_PRIORITY["priorities"].items() if priority == priority_level
    ]


def get_priority_for_category(category: str) -> int | None:
    """
    Get the priority level for a specific category.

    Args:
        category: Category name (e.g., 'product_core', 'vision_documents')

    Returns:
        Priority level (1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED) or None

    Example:
        >>> priority = get_priority_for_category('product_core')
        >>> print(priority)
        1
    """
    return DEFAULT_FIELD_PRIORITY["priorities"].get(category)


def validate_priority_config() -> bool:
    """
    Validate that all priority values are within acceptable range (1-4).

    Returns:
        True if all priorities are valid, False otherwise

    Raises:
        ValueError: If any priority value is not in {1, 2, 3, 4}
    """
    valid_priorities = {1, 2, 3, 4}
    for category, priority in DEFAULT_FIELD_PRIORITY["priorities"].items():
        if priority not in valid_priorities:
            raise ValueError(
                f"Invalid priority {priority} for category '{category}'. "
                f"Must be one of: 1 (CRITICAL), 2 (IMPORTANT), 3 (NICE_TO_HAVE), 4 (EXCLUDED)"
            )

    # Ensure at least one category is CRITICAL (Priority 1)
    critical_categories = [cat for cat, pri in DEFAULT_FIELD_PRIORITY["priorities"].items() if pri == 1]
    if not critical_categories:
        raise ValueError("At least one category must have Priority 1 (CRITICAL)")

    return True


# Validate on module import to catch configuration errors early
validate_priority_config()
