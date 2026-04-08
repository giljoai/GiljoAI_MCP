# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Agent template validation functions for 0103."""

import re
from typing import Optional

from sqlalchemy.orm import Session

from src.giljo_mcp.models import AgentTemplate


def slugify_name(role: str, suffix: Optional[str] = None) -> str:
    """Generate agent name from role and optional suffix.

    Args:
        role: Agent role (e.g., 'orchestrator')
        suffix: Optional custom suffix (e.g., 'AmazingGuy')

    Returns:
        Slugified name (e.g., 'orchestrator-amazing-guy')
    """
    if suffix:
        # Convert to lowercase and replace spaces/underscores with hyphens
        suffix_clean = re.sub(r"[^a-z0-9-]", "", suffix.lower().replace("_", "-").replace(" ", "-"))
        return f"{role}-{suffix_clean}"
    return role


def validate_agent_name(name: str, tenant_key: str, db: Session, exclude_id: Optional[str] = None) -> tuple[bool, str]:
    """Validate agent name format and uniqueness.

    Args:
        name: Proposed agent name
        tenant_key: Tenant isolation key
        db: Database session
        exclude_id: Template ID to exclude from uniqueness check (for updates)

    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check format: lowercase letters, numbers, hyphens only
    if not re.match(r"^[a-z0-9]+(-[a-z0-9]+)*$", name):
        return False, "Name must use lowercase letters, numbers, and hyphens only"

    # Check length
    if len(name) > 100:
        return False, "Name must be 100 characters or less"

    # Check uniqueness within tenant
    query = db.query(AgentTemplate).filter_by(tenant_key=tenant_key, name=name)

    if exclude_id:
        query = query.filter(AgentTemplate.id != exclude_id)

    existing = query.first()
    if existing:
        return False, f"Agent name '{name}' already exists"

    return True, ""


def validate_system_prompt(content: str) -> tuple[bool, str]:
    """Validate system prompt content.

    Args:
        content: System prompt text

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not content or not content.strip():
        return False, "System prompt is required"

    if len(content.strip()) < 20:
        return False, "System prompt is too short (minimum 20 characters)"

    return True, ""


def can_activate_role(role: str, tenant_key: str, db: Session, exclude_id: Optional[str] = None) -> tuple[bool, str]:
    """Check if activating this role would exceed 8-role limit.

    Args:
        role: Role to activate
        tenant_key: Tenant isolation key
        db: Database session
        exclude_id: Template ID to exclude from count (for updates)

    Returns:
        Tuple of (can_activate, error_message)
    """
    # Count currently active distinct roles
    query = db.query(AgentTemplate.role).filter_by(tenant_key=tenant_key, is_active=True).distinct()

    if exclude_id:
        query = query.filter(AgentTemplate.id != exclude_id)

    active_roles = {row[0] for row in query.all()}

    # If this role is already active elsewhere, allow toggle
    if role in active_roles:
        return True, ""

    # If we have 8 distinct active roles, block new role activation
    if len(active_roles) >= 8:
        return (
            False,
            f"Maximum 8 active agent roles allowed (currently {len(active_roles)}). Deactivate another role first.",
        )

    return True, ""


def get_role_color(role: str) -> str:
    """Get background color for a role.

    Args:
        role: Agent role

    Returns:
        Hex color code
    """
    color_map = {
        "orchestrator": "#D4A574",
        "analyzer": "#E74C3C",
        "designer": "#9B59B6",
        "frontend": "#3498DB",
        "backend": "#2ECC71",
        "implementer": "#3498DB",
        "tester": "#FFC300",
        "reviewer": "#9B59B6",
        "documenter": "#27AE60",
    }
    return color_map.get(role, "#90A4AE")
