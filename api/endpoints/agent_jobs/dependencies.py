"""
Dependency injection for agent_jobs endpoints.

Provides FastAPI dependencies for service layer access.
"""

from fastapi import Depends

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService


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


def get_orchestration_service(
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

    # OrchestrationService uses db_manager (not session) for its own session management
    return OrchestrationService(
        db_manager=state.db_manager,
        tenant_manager=state.tenant_manager,
        websocket_manager=state.websocket_manager,
    )
