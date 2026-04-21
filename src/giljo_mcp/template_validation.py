# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Agent template validation functions for 0103."""

import re
from typing import Optional


def slugify_name(role: str, suffix: Optional[str] = None) -> str:
    """Generate agent name from role and optional suffix.

    Args:
        role: Agent role (e.g., 'orchestrator')
        suffix: Optional custom suffix (e.g., 'AmazingGuy')

    Returns:
        Slugified name (e.g., 'orchestrator-amazing-guy')
    """
    if suffix:
        # Convert to lowercase, replace spaces/underscores with hyphens, strip leading/trailing hyphens
        suffix_clean = re.sub(r"[^a-z0-9-]", "", suffix.lower().replace("_", "-").replace(" ", "-")).strip("-")
        # Collapse consecutive hyphens
        suffix_clean = re.sub(r"-{2,}", "-", suffix_clean)
        if suffix_clean:
            return f"{role}-{suffix_clean}"
    return role


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
