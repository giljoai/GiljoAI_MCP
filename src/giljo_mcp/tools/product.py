"""
Product Configuration Tools for GiljoAI MCP
Handles product configuration access and updates with role-based filtering
"""

import logging
from typing import Any, Optional

from sqlalchemy import and_, select

from src.giljo_mcp.context_manager import (
    get_filtered_config,
    get_full_config,
    merge_config_updates,
    validate_config_data,
)
from src.giljo_mcp.database import get_db_manager
from src.giljo_mcp.models import Product, Project


logger = logging.getLogger(__name__)


# Standalone async functions for direct use and testing
async def get_product_config(
    project_id: str,
    filtered: bool = True,
    agent_name: Optional[str] = None,
    agent_role: Optional[str] = None,
    session=None,  # Optional session for testing
) -> dict[str, Any]:
    """
    Get product configuration with optional role-based filtering.

    Args:
        project_id: UUID of the project
        filtered: If True, return role-filtered config. If False, return full config.
        agent_name: Agent name (required when filtered=True)
        agent_role: Optional agent role (can be detected from agent_name)
        session: Optional SQLAlchemy session for testing

    Returns:
        Product configuration data (filtered or full based on parameters)
    """
    try:
        # Use provided session or create new one
        if session is not None:
            return await _get_product_config_with_session(session, project_id, filtered, agent_name, agent_role)

        db_manager = get_db_manager()
        async with db_manager.get_session_async() as session_ctx:  # type: ignore[var-annotated]
            return await _get_product_config_with_session(session_ctx, project_id, filtered, agent_name, agent_role)  # type: ignore[unreachable]

    except Exception as e:
        logger.exception("Failed to get product config")
        return {"success": False, "error": str(e)}


async def _get_product_config_with_session(
    session, project_id: str, filtered: bool, agent_name: Optional[str], agent_role: Optional[str]
) -> dict[str, Any]:
    """Internal helper with session for get_product_config"""
    # Find project
    project_query = select(Project).where(Project.id == project_id)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        return {
            "success": False,
            "error": f"Project {project_id} not found",
        }

    # Check if project has a product
    if not project.product_id:
        return {
            "success": False,
            "error": f"Project {project_id} has no product associated",
        }

    # Get product with TENANT VALIDATION
    # Derive tenant_key from project and validate product belongs to same tenant
    product_query = select(Product).where(
        and_(
            Product.id == project.product_id,
            Product.tenant_key == project.tenant_key,  # TENANT ISOLATION
        )
    )
    product_result = await session.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        return {
            "success": False,
            "error": f"Product {project.product_id} not found or tenant mismatch",
        }

    # Handle filtered vs unfiltered config
    if filtered:
        # Filtered mode requires agent_name
        if not agent_name:
            return {
                "success": False,
                "error": "agent_name required when filtered=True",
            }

        # Detect role from agent_name if not provided
        if not agent_role:
            # Extract role from agent name (e.g., "implementer-1" -> "implementer")
            agent_lower = agent_name.lower()
            for role in ["orchestrator", "implementer", "tester", "analyzer", "documenter", "reviewer"]:
                if role in agent_lower:
                    agent_role = role
                    break

        # Get filtered config based on role
        config = get_filtered_config(agent_name, product, agent_role)

        logger.info(
            f"Retrieved FILTERED config for agent '{agent_name}' "
            f"(role: {agent_role or 'detected'}): {len(config)} fields"
        )
    else:
        # Unfiltered mode - return full config
        config = get_full_config(product)

        logger.info(f"Retrieved FULL config for project {project_id}: {len(config)} fields")

    return {
        "success": True,
        "config": config,
        "product_id": str(product.id),
        "product_name": product.name,
        "filtered": filtered,
    }


async def update_product_config(
    project_id: str,
    config_updates: dict[str, Any],
    merge: bool = True,
    session=None,  # Optional session for testing
) -> dict[str, Any]:
    """
    Update product configuration with validation.

    Args:
        project_id: UUID of the project
        config_updates: Configuration updates to apply
        merge: If True, deep merge updates. If False, replace entire config.
        session: Optional SQLAlchemy session for testing

    Returns:
        Update confirmation with updated fields
    """
    try:
        # Use provided session or create new one
        if session is not None:
            return await _update_product_config_with_session(session, project_id, config_updates, merge)

        db_manager = get_db_manager()
        async with db_manager.get_session_async() as session_ctx:  # type: ignore[var-annotated]
            return await _update_product_config_with_session(session_ctx, project_id, config_updates, merge)  # type: ignore[unreachable]

    except Exception as e:
        logger.exception("Failed to update product config")
        return {"success": False, "error": str(e)}


async def _update_product_config_with_session(
    session, project_id: str, config_updates: dict[str, Any], merge: bool
) -> dict[str, Any]:
    """Internal helper with session for update_product_config"""
    # Find project
    project_query = select(Project).where(Project.id == project_id)
    project_result = await session.execute(project_query)
    project = project_result.scalar_one_or_none()

    if not project:
        return {
            "success": False,
            "error": f"Project {project_id} not found",
        }

    # Check if project has a product
    if not project.product_id:
        return {
            "success": False,
            "error": f"Project {project_id} has no product associated",
        }

    # Get product with TENANT VALIDATION
    # Derive tenant_key from project and validate product belongs to same tenant
    product_query = select(Product).where(
        and_(
            Product.id == project.product_id,
            Product.tenant_key == project.tenant_key,  # TENANT ISOLATION
        )
    )
    product_result = await session.execute(product_query)
    product = product_result.scalar_one_or_none()

    if not product:
        return {
            "success": False,
            "error": f"Product {project.product_id} not found or tenant mismatch",
        }

    # Prepare new config
    if merge:
        # Merge mode - deep merge updates into existing config
        existing_config = product.config_data or {}
        new_config = merge_config_updates(existing_config, config_updates)
        updated_fields = list(config_updates.keys())
    else:
        # Replace mode - validate required fields
        new_config = config_updates
        updated_fields = list(config_updates.keys())

        # Validate config in replace mode (must have required fields)
        is_valid, errors = validate_config_data(new_config)
        if not is_valid:
            return {
                "success": False,
                "error": f"Configuration validation failed: {', '.join(errors)}",
                "validation_errors": errors,
            }

    # In merge mode, validate the merged result
    if merge:
        is_valid, errors = validate_config_data(new_config)
        if not is_valid:
            # In merge mode, if validation fails, it's likely due to type errors
            # (not missing required fields, since we merged with existing)
            return {
                "success": False,
                "error": f"Configuration validation failed: {', '.join(errors)}",
                "validation_errors": errors,
            }

    # Update product config_data
    product.config_data = new_config
    await session.commit()

    logger.info(
        f"Updated product config for {product.name} "
        f"(mode: {'merge' if merge else 'replace'}): {len(updated_fields)} fields"
    )

    return {
        "success": True,
        "product_id": str(product.id),
        "product_name": product.name,
        "updated_fields": updated_fields,
        "merge_mode": merge,
    }


async def get_product_settings(project_id: str, session=None) -> dict[str, Any]:
    """
    Get full product settings (alias for get_product_config with filtered=False).

    This is a convenience function for orchestrators or when full config access is needed.

    Args:
        project_id: UUID of the project
        session: Optional SQLAlchemy session for testing

    Returns:
        Full product configuration data
    """
    # Simply delegate to get_product_config with filtered=False
    return await get_product_config(project_id=project_id, filtered=False, session=session)
