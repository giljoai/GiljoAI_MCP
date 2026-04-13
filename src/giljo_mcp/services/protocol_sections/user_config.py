# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""User configuration fetching and field toggle normalization."""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import and_, select

from src.giljo_mcp.config.defaults import DEFAULT_CATEGORY_TOGGLES
from src.giljo_mcp.config.defaults import DEFAULT_DEPTH_CONFIG as _DEFAULT_DEPTH_CONFIG
from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY as _DEFAULT_FIELD_PRIORITY


logger = logging.getLogger(__name__)


# Extract inner structure for backward compatibility with existing code
# defaults.py uses versioned structure: {"version": "4.0", "priorities": {...}}
# This code expects flat structure: {"field": {"toggle": True}}
DEFAULT_FIELD_PRIORITIES = _DEFAULT_FIELD_PRIORITY["priorities"]
# Handover 0840d: DEFAULT_DEPTH_CONFIG is now a flat dict (no "depths" wrapper)
DEFAULT_DEPTH_CONFIG = _DEFAULT_DEPTH_CONFIG


def _normalize_field_toggles(field_config: dict[str, Any]) -> dict[str, bool]:
    """
    Normalize field config to a flat toggle dict.

    Supports multiple input formats:
    - v3.0: {"field": {"toggle": True}}
    - v2.x legacy: {"field": {"toggle": True, "priority": X}}
    - Flat bool: {"field": True}
    - Legacy int: {"field": 1} (treated as enabled if < 4)

    Args:
        field_config: Dict with field toggle/priority values

    Returns:
        Dict mapping field names to boolean toggle values
    """
    normalized = {}
    for field_key, value in field_config.items():
        if isinstance(value, dict):
            normalized[field_key] = value.get("toggle", True)
        elif isinstance(value, bool):
            normalized[field_key] = value
        elif isinstance(value, int):
            normalized[field_key] = value < 4
        else:
            normalized[field_key] = True
    return normalized


async def _get_user_config(
    user_id: str,
    tenant_key: str,
    session: Any,  # AsyncSession type hint would create circular import
) -> dict[str, Any]:
    """
    Fetch user's field toggle config and depth config from normalized tables/columns.

    Handover 0840d: Reads from user_field_priorities table and depth columns on users.

    Args:
        user_id: User UUID
        tenant_key: Tenant isolation key
        session: SQLAlchemy AsyncSession

    Returns:
        dict with 'field_toggles' and 'depth_config' keys
    """
    from src.giljo_mcp.models.auth import User, UserFieldPriority

    try:
        result = await session.execute(
            select(User).where(and_(User.id == user_id, User.tenant_key == tenant_key, User.is_active))
        )
        user = result.scalar_one_or_none()

        if not user:
            logger.warning(
                "user_not_found_using_defaults",
                extra={"user_id": user_id, "tenant_key": tenant_key},
            )
            normalized_defaults = _normalize_field_toggles(DEFAULT_FIELD_PRIORITIES.copy())
            return {"field_toggles": normalized_defaults, "depth_config": DEFAULT_DEPTH_CONFIG.copy()}

        # Build field toggles from user_field_priorities table
        prio_result = await session.execute(
            select(UserFieldPriority).where(
                and_(UserFieldPriority.user_id == user_id, UserFieldPriority.tenant_key == tenant_key)
            )
        )
        rows = prio_result.scalars().all()

        if rows:
            # Start with defaults, override with user rows
            field_toggles = dict(DEFAULT_CATEGORY_TOGGLES)
            for row in rows:
                field_toggles[row.category] = row.enabled
            # Always-on categories
            field_toggles["product_core"] = True
            field_toggles["project_description"] = True
        else:
            field_toggles = _normalize_field_toggles(DEFAULT_FIELD_PRIORITIES.copy())

        # Build depth config from columns (normalize keys for internal use)
        key_mapping = {
            "memory_last_n_projects": "memory_360",
            "git_commits": "git_history",
            "vision_documents": "vision_documents",
        }

        raw_depth = {
            "vision_documents": user.depth_vision_documents,
            "memory_last_n_projects": user.depth_memory_last_n,
            "git_commits": user.depth_git_commits,
            "tech_stack_sections": user.depth_tech_stack_sections,
            "architecture_depth": user.depth_architecture,
        }

        depth_config = {}
        for db_key, value in raw_depth.items():
            internal_key = key_mapping.get(db_key, db_key)
            depth_config[internal_key] = value

        if depth_config.get("vision_documents") == "optional":
            depth_config["vision_documents"] = "light"

        logger.info(
            "[USER_CONFIG] Fetched user configuration",
            extra={
                "user_id": user_id,
                "tenant_key": tenant_key,
                "depth_config": depth_config,
            },
        )

        return {"field_toggles": field_toggles, "depth_config": depth_config}

    except (OSError, ValueError, KeyError) as e:
        logger.error(
            "user_config_fetch_failed",
            extra={"user_id": user_id, "tenant_key": tenant_key, "error_message": str(e)},
            exc_info=True,
        )
        normalized_defaults = _normalize_field_toggles(DEFAULT_FIELD_PRIORITIES.copy())
        return {"field_toggles": normalized_defaults, "depth_config": DEFAULT_DEPTH_CONFIG.copy()}
