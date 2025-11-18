"""
Field Metadata for Context Management v3.0

Defines granular field selection metadata for context tools.
Each field has a key, label, and token estimate.

Categories:
- tech_stack: 4 fields (languages, frameworks, databases, dependencies)
- architecture: 6 fields (pattern, design_patterns, api_style, notes, layers, components)
- testing: 3 fields (quality_standards, strategy, frameworks)

Handover 0319: Initial implementation for granular field selection.
"""

from typing import Any, Dict, List, Optional
import copy

# Field metadata defining available fields per category
# Each field has: key, label, tokens (estimated)
FIELD_METADATA: Dict[str, Dict[str, Dict[str, Any]]] = {
    "tech_stack": {
        "languages": {
            "key": "languages",
            "label": "Programming Languages",
            "tokens": 50,
            "description": "Primary programming languages used in the project",
        },
        "frameworks": {
            "key": "frameworks",
            "label": "Frameworks",
            "tokens": 100,
            "description": "Frontend and backend frameworks",
        },
        "databases": {
            "key": "databases",
            "label": "Databases",
            "tokens": 50,
            "description": "Database systems and storage solutions",
        },
        "dependencies": {
            "key": "dependencies",
            "label": "Dependencies",
            "tokens": 200,
            "description": "Infrastructure and dev tools",
        },
    },
    "architecture": {
        "pattern": {
            "key": "pattern",
            "label": "Primary Pattern",
            "tokens": 30,
            "description": "Primary architectural pattern (e.g., Microservices, Monolith)",
        },
        "design_patterns": {
            "key": "design_patterns",
            "label": "Design Patterns",
            "tokens": 100,
            "description": "Software design patterns used",
        },
        "api_style": {
            "key": "api_style",
            "label": "API Style",
            "tokens": 30,
            "description": "API architectural style (e.g., REST, GraphQL)",
        },
        "notes": {
            "key": "notes",
            "label": "Architecture Notes",
            "tokens": 500,
            "description": "Detailed architecture documentation",
        },
        "layers": {
            "key": "layers",
            "label": "Architectural Layers",
            "tokens": 150,
            "description": "System layers and boundaries",
        },
        "components": {
            "key": "components",
            "label": "Components",
            "tokens": 200,
            "description": "Major system components and modules",
        },
    },
    "testing": {
        "quality_standards": {
            "key": "quality_standards",
            "label": "Quality Standards",
            "tokens": 100,
            "description": "Code quality requirements and standards",
        },
        "strategy": {
            "key": "strategy",
            "label": "Testing Strategy",
            "tokens": 150,
            "description": "Overall testing approach and methodology",
        },
        "frameworks": {
            "key": "frameworks",
            "label": "Testing Frameworks",
            "tokens": 100,
            "description": "Testing frameworks and tools",
        },
    },
}


def get_field_metadata(category: str, field_key: str) -> Optional[Dict[str, Any]]:
    """
    Get metadata for a specific field.

    Args:
        category: Category name (tech_stack, architecture, testing)
        field_key: Field key within the category

    Returns:
        Field metadata dict or None if not found
    """
    return FIELD_METADATA.get(category, {}).get(field_key)


def get_fields_for_category(category: str) -> List[str]:
    """
    Get list of all field keys for a category.

    Args:
        category: Category name

    Returns:
        List of field keys
    """
    return list(FIELD_METADATA.get(category, {}).keys())


def get_default_field_selection(category: str) -> Dict[str, bool]:
    """
    Get default field selection for a category (all fields enabled).

    Args:
        category: Category name

    Returns:
        Dict mapping field keys to True
    """
    fields = get_fields_for_category(category)
    return {field: True for field in fields}


def migrate_v2_to_v3_fields(
    category: str,
    depth_value: str
) -> Dict[str, bool]:
    """
    Migrate v2 depth-based configuration to v3 field selection.

    Converts depth values (like "required", "all", "basic", "full", etc.)
    to granular field selection.

    Args:
        category: Category name
        depth_value: v2 depth value

    Returns:
        Dict mapping field keys to enabled/disabled state

    Migration Rules:
        tech_stack:
            - "required": Only languages, frameworks, databases
            - "all": All fields enabled

        architecture:
            - "overview": pattern, api_style only
            - "detailed": All fields enabled

        testing:
            - "none": All fields disabled
            - "basic": quality_standards, strategy
            - "full": All fields enabled
    """
    all_fields = get_fields_for_category(category)

    if category == "tech_stack":
        if depth_value == "required":
            # Only core fields
            enabled = {"languages", "frameworks", "databases"}
            return {field: field in enabled for field in all_fields}
        else:  # "all" or default
            return {field: True for field in all_fields}

    elif category == "architecture":
        if depth_value == "overview":
            # Only high-level fields
            enabled = {"pattern", "api_style"}
            return {field: field in enabled for field in all_fields}
        else:  # "detailed" or default
            return {field: True for field in all_fields}

    elif category == "testing":
        if depth_value == "none":
            # All disabled
            return {field: False for field in all_fields}
        elif depth_value == "basic":
            # Core testing info
            enabled = {"quality_standards", "strategy"}
            return {field: field in enabled for field in all_fields}
        else:  # "full" or default
            return {field: True for field in all_fields}

    # Unknown category - return all enabled as default
    return {field: True for field in all_fields}


def estimate_tokens_for_selection(
    category: str,
    selected_fields: Dict[str, bool]
) -> int:
    """
    Estimate total tokens for a field selection.

    Args:
        category: Category name
        selected_fields: Dict mapping field keys to enabled state

    Returns:
        Estimated total tokens
    """
    total = 0
    category_fields = FIELD_METADATA.get(category, {})

    for field_key, enabled in selected_fields.items():
        if enabled and field_key in category_fields:
            total += category_fields[field_key].get("tokens", 0)

    return total


def migrate_depth_config_v2_to_v3(depth_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Migrate v2 depth configuration to v3 schema with granular field selection.

    v2 format (Handover 0314):
        {
            "vision_chunking": "moderate",
            "memory_last_n_projects": 3,
            "git_commits": 25,
            "agent_template_detail": "standard",
            "tech_stack_sections": "all",
            "architecture_depth": "overview"
        }

    v3 format (Handover 0319):
        {
            "schema_version": "3.0",
            "vision_chunking": "moderate",
            "memory_last_n_projects": 3,
            "git_commits": 25,
            "agent_template_detail": "standard",
            "field_selections": {
                "tech_stack": {
                    "languages": true,
                    "frameworks": true,
                    "databases": true,
                    "dependencies": true
                },
                "architecture": {
                    "pattern": true,
                    "design_patterns": true,
                    "api_style": true,
                    "notes": true,
                    "layers": true,
                    "components": true
                },
                "testing": {
                    "quality_standards": true,
                    "strategy": true,
                    "frameworks": true
                }
            }
        }

    Args:
        depth_config: v2 depth configuration

    Returns:
        v3 depth configuration with field selections
    """
    # Check if already migrated
    if depth_config.get("schema_version") == "3.0":
        return depth_config

    # Create v3 config
    v3_config = {
        "schema_version": "3.0",
        # Preserve existing depth settings
        "vision_chunking": depth_config.get("vision_chunking", "moderate"),
        "memory_last_n_projects": depth_config.get("memory_last_n_projects", 3),
        "git_commits": depth_config.get("git_commits", 25),
        "agent_template_detail": depth_config.get("agent_template_detail", "standard"),
    }

    # Convert depth values to field selections
    tech_stack_depth = depth_config.get("tech_stack_sections", "all")
    architecture_depth = depth_config.get("architecture_depth", "overview")

    # Migrate tech_stack
    v3_config["field_selections"] = {
        "tech_stack": migrate_v2_to_v3_fields("tech_stack", tech_stack_depth),
        "architecture": migrate_v2_to_v3_fields("architecture", architecture_depth),
        # Testing defaults to all fields (no v2 depth control for testing)
        "testing": get_default_field_selection("testing"),
    }

    return v3_config


def is_v3_schema(depth_config: Optional[Dict[str, Any]]) -> bool:
    """
    Check if depth configuration is v3.0 schema.

    Args:
        depth_config: Depth configuration dict

    Returns:
        True if v3.0 schema, False otherwise
    """
    if not depth_config:
        return False
    return depth_config.get("schema_version") == "3.0"


def get_field_selections(depth_config: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, bool]]:
    """
    Get field selections from depth config, with auto-migration if needed.

    Args:
        depth_config: Depth configuration (v2 or v3)

    Returns:
        Field selections dict
    """
    if not depth_config:
        # Return default selections for all categories
        return {
            "tech_stack": get_default_field_selection("tech_stack"),
            "architecture": get_default_field_selection("architecture"),
            "testing": get_default_field_selection("testing"),
        }

    # Migrate if needed
    if not is_v3_schema(depth_config):
        depth_config = migrate_depth_config_v2_to_v3(depth_config)

    return depth_config.get("field_selections", {
        "tech_stack": get_default_field_selection("tech_stack"),
        "architecture": get_default_field_selection("architecture"),
        "testing": get_default_field_selection("testing"),
    })
