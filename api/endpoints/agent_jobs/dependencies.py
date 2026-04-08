# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Dependency injection for agent_jobs endpoints.

Provides FastAPI dependencies for service layer access.
"""

import logging

from fastapi import Depends

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService


logger = logging.getLogger(__name__)


async def get_db_manager() -> DatabaseManager:
    """
    Get DatabaseManager instance from app state.

    Returns the database manager from the FastAPI application state.
    """
    # Get db_manager from application state (set during startup)
    from api.app import state

    return state.db_manager


async def get_tenant_manager():
    """
    Get TenantManager instance from app state.

    Returns the tenant manager from the FastAPI application state.
    """
    from api.app import state

    return state.tenant_manager


async def get_orchestration_service(
    current_user: User = Depends(get_current_active_user),
) -> OrchestrationService:
    """
    Get OrchestrationService instance for agent job operations.

    Args:
        current_user: Authenticated user (for tenant isolation)

    Returns:
        OrchestrationService instance

    Note:
        Service is request-scoped and uses global db_manager/tenant_manager from app state.
        Service creates its own sessions via db_manager.get_session_async().
    """
    # Import state lazily to avoid circular import
    from api.app import state

    logger.debug(f"get_orchestration_service called for user {current_user.username}")
    logger.debug(f"state.db_manager is None: {state.db_manager is None}")
    logger.debug(f"state.tenant_manager is None: {state.tenant_manager is None}")

    # OrchestrationService uses db_manager (not session) for its own session management
    return OrchestrationService(
        db_manager=state.db_manager,
        tenant_manager=state.tenant_manager,
        websocket_manager=state.websocket_manager,
    )
