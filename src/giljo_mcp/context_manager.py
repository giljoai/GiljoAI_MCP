"""
Context Manager for GiljoAI MCP
Provides role-based context filtering and hierarchical loading
"""

import logging
from typing import Any, Optional

from .models import Product


logger = logging.getLogger(__name__)


# Role-based config field mappings
ROLE_CONFIG_FILTERS = {
    "orchestrator": "all",  # Gets ALL fields
    "implementer": [
        "architecture",
        "tech_stack",
        "codebase_structure",
        "database_type",
        "backend_framework",
        "frontend_framework",
    ],
    "developer": [  # Alias for implementer
        "architecture",
        "tech_stack",
        "codebase_structure",
        "database_type",
        "backend_framework",
        "frontend_framework",
    ],
    "tester": ["test_config", "tech_stack"],
    "qa": ["test_config"],  # Alias for tester
    "documenter": ["architecture", "codebase_structure"],
    "analyzer": ["architecture", "tech_stack", "codebase_structure"],
    "reviewer": ["architecture", "tech_stack"],
}


def is_orchestrator(agent_name: str, agent_role: Optional[str] = None) -> bool:
    """
    Determine if agent is an orchestrator.

    Args:
        agent_name: Name of the agent
        agent_role: Optional role from Agent model

    Returns:
        True if agent is orchestrator
    """
    agent_lower = agent_name.lower()

    # Check by name
    if "orchestrator" in agent_lower:
        return True

    # Check by role
    return bool(agent_role and agent_role.lower() == "orchestrator")


def get_full_config(product: Product) -> dict[str, Any]:
    """
    Get FULL config_data for orchestrator agents.

    Args:
        product: Product model instance

    Returns:
        Complete config_data dictionary
    """
    if not product.config_data:
        logger.warning(f"Product {product.id} has no config_data")
        return {}

    logger.info(f"Loading FULL config for orchestrator (product: {product.name})")
    return dict(product.config_data)


def get_filtered_config(agent_name: str, product: Product, agent_role: Optional[str] = None) -> dict[str, Any]:
    """
    Get FILTERED config_data based on agent role.

    Args:
        agent_name: Name of the agent
        product: Product model instance
        agent_role: Optional role from Agent model

    Returns:
        Filtered config_data containing only role-relevant fields
    """
    # Check if orchestrator (gets ALL fields)
    if is_orchestrator(agent_name, agent_role):
        return get_full_config(product)

    if not product.config_data:
        logger.warning(f"Product {product.id} has no config_data")
        return {}

    # Determine role from agent name
    agent_lower = agent_name.lower()
    role_key = None

    for role in ROLE_CONFIG_FILTERS:
        if role in agent_lower:
            role_key = role
            break

    # Fallback to generic filtering if role unknown
    if not role_key:
        logger.warning(f"Unknown agent role for {agent_name}, using default filtering")
        role_key = "analyzer"  # Default to analyzer (broad but safe)

    # Get allowed fields for this role
    allowed_fields = ROLE_CONFIG_FILTERS[role_key]

    if allowed_fields == "all":
        # Orchestrator gets everything
        return dict(product.config_data)

    # Filter config_data to only allowed fields
    filtered = {}
    for field in allowed_fields:
        if field in product.config_data:
            filtered[field] = product.config_data[field]

    # Always include basic metadata
    if "serena_mcp_enabled" in product.config_data:
        filtered["serena_mcp_enabled"] = product.config_data["serena_mcp_enabled"]

    logger.info(
        f"Loaded FILTERED config for {agent_name} (role: {role_key}): "
        f"{len(filtered)} fields out of {len(product.config_data)}"
    )

    return filtered


def validate_config_data(config: dict[str, Any]) -> tuple[bool, list[str]]:
    """
    Validate config_data structure against schema.

    Args:
        config: Config data to validate

    Returns:
        Tuple of (is_valid, error_messages)
    """
    errors = []

    # Required fields
    if "architecture" not in config:
        errors.append("Missing required field: architecture")

    if "serena_mcp_enabled" not in config:
        errors.append("Missing required field: serena_mcp_enabled")

    # Type validation
    if "tech_stack" in config and not isinstance(config["tech_stack"], list):
        errors.append("tech_stack must be an array")

    if "codebase_structure" in config and not isinstance(config["codebase_structure"], dict):
        errors.append("codebase_structure must be an object")

    if "test_config" in config and not isinstance(config["test_config"], dict):
        errors.append("test_config must be an object")

    # Boolean validation
    if "serena_mcp_enabled" in config and not isinstance(config["serena_mcp_enabled"], bool):
        errors.append("serena_mcp_enabled must be a boolean")

    is_valid = len(errors) == 0

    if not is_valid:
        logger.error(f"config_data validation failed: {errors}")

    return is_valid, errors


def merge_config_updates(existing: dict[str, Any], updates: dict[str, Any]) -> dict[str, Any]:
    """
    Merge config updates into existing config (deep merge).

    Args:
        existing: Existing config_data
        updates: Updates to apply

    Returns:
        Merged config_data
    """
    merged = dict(existing)

    for key, value in updates.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            # Deep merge for nested objects
            merged[key] = {**merged[key], **value}
        else:
            # Direct replacement for scalars and arrays
            merged[key] = value

    return merged


def get_config_summary(product: Product) -> str:
    """
    Get human-readable summary of config_data.

    Args:
        product: Product model instance

    Returns:
        Formatted summary string
    """
    if not product.config_data:
        return "No configuration data available"

    config = product.config_data

    summary_parts = []

    if "architecture" in config:
        summary_parts.append(f"Architecture: {config['architecture']}")

    if config.get("tech_stack"):
        tech_stack = config["tech_stack"]
        if isinstance(tech_stack, list):
            summary_parts.append(f"Tech Stack: {', '.join(tech_stack[:3])}")
        elif isinstance(tech_stack, str):
            summary_parts.append(f"Tech Stack: {tech_stack}")

    if config.get("critical_features"):
        summary_parts.append(f"Critical Features: {len(config['critical_features'])} defined")

    if config.get("test_commands"):
        summary_parts.append(f"Test Commands: {len(config['test_commands'])} configured")

    if "serena_mcp_enabled" in config:
        status = "enabled" if config["serena_mcp_enabled"] else "disabled"
        summary_parts.append(f"Serena MCP: {status}")

    return "\n".join(summary_parts)
