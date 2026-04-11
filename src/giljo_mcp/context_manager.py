# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Context Manager for GiljoAI MCP
Provides role-based context filtering and hierarchical loading

Handover 0840c: Rewritten to use normalized product config tables
(ProductTechStack, ProductArchitecture, ProductTestConfig) instead of
config_data JSONB column.
"""

import logging
from typing import Any, Optional

from .models.products import Product


logger = logging.getLogger(__name__)


# Role-based config field mappings
# Keys map to normalized table relationships on Product
ROLE_CONFIG_FILTERS = {
    "orchestrator": "all",  # Gets ALL fields
    "implementer": ["architecture", "tech_stack"],
    "developer": ["architecture", "tech_stack"],  # Alias for implementer
    "tester": ["test_config", "tech_stack"],
    "qa": ["test_config"],  # Alias for tester
    "documenter": ["architecture"],
    "analyzer": ["architecture", "tech_stack"],
    "reviewer": ["architecture", "tech_stack"],
}


def _serialize_tech_stack(product: Product) -> dict[str, Any]:
    """Serialize ProductTechStack relationship to dict."""
    ts = product.tech_stack
    if not ts:
        return {}
    return {
        "programming_languages": ts.programming_languages or "",
        "frontend_frameworks": ts.frontend_frameworks or "",
        "backend_frameworks": ts.backend_frameworks or "",
        "databases_storage": ts.databases_storage or "",
        "infrastructure": ts.infrastructure or "",
        "dev_tools": ts.dev_tools or "",
        "target_windows": ts.target_windows,
        "target_linux": ts.target_linux,
        "target_macos": ts.target_macos,
        "target_android": ts.target_android,
        "target_ios": ts.target_ios,
        "target_cross_platform": ts.target_cross_platform,
    }


def _serialize_architecture(product: Product) -> dict[str, Any]:
    """Serialize ProductArchitecture relationship to dict."""
    arch = product.architecture
    if not arch:
        return {}
    return {
        "primary_pattern": arch.primary_pattern or "",
        "design_patterns": arch.design_patterns or "",
        "api_style": arch.api_style or "",
        "architecture_notes": arch.architecture_notes or "",
    }


def _serialize_test_config(product: Product) -> dict[str, Any]:
    """Serialize ProductTestConfig relationship to dict."""
    tc = product.test_config
    if not tc:
        return {}
    return {
        "quality_standards": tc.quality_standards or "",
        "test_strategy": tc.test_strategy or "",
        "coverage_target": tc.coverage_target or 80,
        "testing_frameworks": tc.testing_frameworks or "",
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
    Get FULL product config for orchestrator agents.

    Args:
        product: Product model instance (with relationships loaded)

    Returns:
        Complete config dictionary from normalized tables
    """
    config = {}

    tech_stack = _serialize_tech_stack(product)
    if tech_stack:
        config["tech_stack"] = tech_stack

    architecture = _serialize_architecture(product)
    if architecture:
        config["architecture"] = architecture

    if product.core_features:
        config["core_features"] = product.core_features

    test_config = _serialize_test_config(product)
    if test_config:
        config["test_config"] = test_config

    if not config:
        logger.warning(f"Product {product.id} has no config data in normalized tables")

    logger.info(f"Loading FULL config for orchestrator (product: {product.name})")
    return config


def get_filtered_config(agent_name: str, product: Product, agent_role: Optional[str] = None) -> dict[str, Any]:
    """
    Get FILTERED config based on agent role.

    Args:
        agent_name: Name of the agent
        product: Product model instance
        agent_role: Optional role from Agent model

    Returns:
        Filtered config containing only role-relevant fields
    """
    # Check if orchestrator (gets ALL fields)
    if is_orchestrator(agent_name, agent_role):
        return get_full_config(product)

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
        return get_full_config(product)

    # Build filtered config from normalized tables
    serializers = {
        "tech_stack": _serialize_tech_stack,
        "architecture": _serialize_architecture,
        "test_config": _serialize_test_config,
    }

    filtered = {}
    for field in allowed_fields:
        serializer = serializers.get(field)
        if serializer:
            data = serializer(product)
            if data:
                filtered[field] = data

    logger.info(f"Loaded FILTERED config for {agent_name} (role: {role_key}): {len(filtered)} fields")

    return filtered


def get_config_summary(product: Product) -> str:
    """
    Get human-readable summary of product config.

    Args:
        product: Product model instance

    Returns:
        Formatted summary string
    """
    if not product.has_config_data:
        return "No configuration data available"

    summary_parts = []

    arch = product.architecture
    if arch and arch.primary_pattern:
        summary_parts.append(f"Architecture: {arch.primary_pattern}")

    ts = product.tech_stack
    if ts and ts.programming_languages:
        summary_parts.append(f"Tech Stack: {ts.programming_languages}")

    if product.core_features:
        summary_parts.append("Core Features: defined")

    tc = product.test_config
    if tc and tc.test_strategy:
        summary_parts.append(f"Test Strategy: {tc.test_strategy}")

    return "\n".join(summary_parts) if summary_parts else "No configuration data available"
