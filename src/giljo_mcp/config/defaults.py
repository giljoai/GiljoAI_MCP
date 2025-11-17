"""
Default Field Priority Configuration for Product Configuration Data

This module defines the default priority levels for product configuration fields
used in AI agent mission generation. The priority system controls which fields
are included when generating condensed missions with token budget constraints.

Priority Tiers:
    Priority 1 (Critical - Always Included):
        - tech_stack.languages: Primary programming languages
        - tech_stack.backend: Backend framework/runtime
        - tech_stack.frontend: Frontend framework/library
        - architecture.pattern: Core architectural pattern (MVC, microservices, etc.)
        - features.core: Essential product features

        These fields are fundamental to understanding the product's technical
        foundation and are always included regardless of token budget.

    Priority 2 (High Priority):
        - tech_stack.database: Database system and configuration
        - architecture.api_style: API architecture (REST, GraphQL, etc.)
        - test_config.strategy: Testing approach and methodology

        These fields provide critical context for development decisions and are
        included unless token budget is severely constrained.

    Priority 3 (Medium Priority):
        - tech_stack.infrastructure: Deployment and infrastructure details
        - architecture.design_patterns: Specific design patterns in use
        - architecture.notes: Additional architectural context
        - test_config.frameworks: Testing frameworks and tools
        - test_config.coverage_target: Code coverage requirements

        These fields provide additional context and best practices. They are
        dropped first when token budget is exceeded.

Token Budget:
    Default token budget of 2000 tokens for mission condensation. This limit
    ensures missions remain focused and cost-effective while providing agents
    with essential context.

Usage:
    from giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

    # Use in mission planning
    mission_planner.condense_mission(
        vision_doc=doc,
        field_priorities=DEFAULT_FIELD_PRIORITY
    )

    # Override specific priorities
    custom_priorities = DEFAULT_FIELD_PRIORITY.copy()
    custom_priorities['fields']['tech_stack.infrastructure'] = 2

Version History:
    1.0 (2025-10-26): Initial implementation
        - Three-tier priority system
        - 1500 token default budget
        - 12 prioritized configuration fields
    1.1 (2025-10-27): Token budget increase (Handover 0049)
        - Increased token budget from 1500 to 2000 tokens
        - Supports richer product configuration data
    1.2 (2025-11-17): Agent templates integration (Handover 0306)
        - Added "agent_templates" field (Priority 2)
        - Enables agent roster in orchestrator context

Related:
    - Handover 0042: Product Configuration Free-Text Migration
    - Handover 0048: Product Field Priority Configuration
    - src/giljo_mcp/mission_planner.py: Mission condensation logic
    - src/giljo_mcp/models.py: Product.config_data schema
"""

from typing import Any, Dict


DEFAULT_FIELD_PRIORITY: Dict[str, Any] = {
    "version": "1.1",
    "token_budget": 2000,
    "fields": {
        # Priority 1: Critical - Always Included
        # Core technical foundation that defines the product
        "tech_stack.languages": 1,
        "tech_stack.backend": 1,
        "tech_stack.frontend": 1,
        "architecture.pattern": 1,
        "features.core": 1,
        # Priority 2: High Priority
        # Important context for development decisions
        "tech_stack.database": 2,
        "architecture.api_style": 2,
        "test_config.strategy": 2,
        "agent_templates": 2,  # High Priority - Agent roster with capabilities
        # Priority 3: Medium Priority
        # Additional context and best practices
        "tech_stack.infrastructure": 3,
        "architecture.design_patterns": 3,
        "architecture.notes": 3,
        "test_config.frameworks": 3,
        "test_config.coverage_target": 3,
    },
}


def get_fields_by_priority(priority_level: int) -> list[str]:
    """
    Get all field paths matching the specified priority level.

    Args:
        priority_level: Priority tier (1=critical, 2=high, 3=medium)

    Returns:
        List of field paths (e.g., ['tech_stack.languages', ...])

    Example:
        >>> critical_fields = get_fields_by_priority(1)
        >>> print(critical_fields)
        ['tech_stack.languages', 'tech_stack.backend', ...]
    """
    return [
        field_path for field_path, priority in DEFAULT_FIELD_PRIORITY["fields"].items() if priority == priority_level
    ]


def get_priority_for_field(field_path: str) -> int | None:
    """
    Get the priority level for a specific field path.

    Args:
        field_path: Dot-notation field path (e.g., 'tech_stack.languages')

    Returns:
        Priority level (1-3) or None if field not in priority configuration

    Example:
        >>> priority = get_priority_for_field('tech_stack.database')
        >>> print(priority)
        2
    """
    return DEFAULT_FIELD_PRIORITY["fields"].get(field_path)


def validate_field_priorities() -> bool:
    """
    Validate that all priority values are within acceptable range (1-3).

    Returns:
        True if all priorities are valid, False otherwise

    Raises:
        ValueError: If any priority value is not in range 1-3
    """
    for field_path, priority in DEFAULT_FIELD_PRIORITY["fields"].items():
        if not isinstance(priority, int) or priority < 1 or priority > 3:
            raise ValueError(
                f"Invalid priority {priority} for field '{field_path}'. Priority must be integer between 1 and 3."
            )
    return True


# Validate on module import to catch configuration errors early
validate_field_priorities()
