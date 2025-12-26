"""
Dependency injection for projects endpoints.

Provides FastAPI dependencies for service layer access.
"""

import logging
from fastapi import Depends

from api.dependencies import get_tenant_key
from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import User
from src.giljo_mcp.services.project_service import ProjectService
from src.giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


def get_project_service(
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
) -> ProjectService:
    """
    Get ProjectService instance for project operations.

    Args:
        tenant_key: Tenant key from request context (sets global tenant context)
        current_user: Authenticated user (for tenant isolation)

    Returns:
        ProjectService instance

    Note:
        Service is request-scoped and uses global db_manager/tenant_manager from app state.
        Calling get_tenant_key() as dependency ensures TenantManager.set_current_tenant() is called.
        Service creates its own sessions via db_manager.get_session_async().
    """
    # Import state lazily to avoid circular import
    from api.app import state

    # DEBUG: Log tenant context state
    logger.debug(f"[get_project_service] Dependency called with tenant_key={tenant_key}")
    current_tenant = TenantManager.get_current_tenant()
    logger.debug(f"[get_project_service] TenantManager.get_current_tenant() = {current_tenant}")

    if tenant_key != current_user.tenant_key:
        TenantManager.set_current_tenant(current_user.tenant_key)
        tenant_key = current_user.tenant_key

    # Tenant context already set by get_tenant_key() - no need to set again
    # ProjectService uses db_manager (not session) for its own session management
    return ProjectService(
        db_manager=state.db_manager,
        tenant_manager=state.tenant_manager,
        websocket_manager=state.websocket_manager,
    )
