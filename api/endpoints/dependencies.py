"""
Dependencies for User and Auth Endpoints - Handover 0322 Phase 1C/2C

Provides dependency injection for UserService and AuthService.
"""

from fastapi import Depends

from api.dependencies import get_tenant_key
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.services import AuthService, UserService
from src.giljo_mcp.services.message_service import MessageService
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.task_service import TaskService
from src.giljo_mcp.tenant import TenantManager


async def get_db_manager() -> DatabaseManager:
    """
    Get DatabaseManager instance from app state.

    Returns the database manager from the FastAPI application state.
    """
    # Get db_manager from application state (set during startup)
    from api.app import state

    return state.db_manager


async def get_user_service(
    tenant_key: str = Depends(get_tenant_key),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> UserService:
    """
    Get UserService instance with tenant isolation.

    Args:
        tenant_key: Tenant key from request context
        db_manager: Database manager instance

    Returns:
        UserService instance configured for the current tenant
    """
    return UserService(db_manager=db_manager, tenant_key=tenant_key)


async def get_auth_service(
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> AuthService:
    """
    Get AuthService instance (no tenant isolation for auth operations).

    Args:
        db_manager: Database manager instance

    Returns:
        AuthService instance for authentication operations
    """
    return AuthService(db_manager=db_manager)


async def get_tenant_manager() -> TenantManager:
    """
    Get TenantManager instance from app state.

    Returns the tenant manager from the FastAPI application state.
    """
    # Get tenant_manager from application state (set during startup)
    from api.app import state

    return state.tenant_manager


async def get_websocket_manager():
    """Get WebSocketManager instance from app state."""
    from api.app import state

    return state.websocket_manager


async def get_task_service(
    tenant_key: str = Depends(get_tenant_key),
    db_manager: DatabaseManager = Depends(get_db_manager),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
) -> TaskService:
    """
    Get TaskService instance for task management.

    Sets the tenant context before returning the service instance.

    Args:
        tenant_key: Tenant key from request context
        db_manager: Database manager instance
        tenant_manager: Tenant manager instance

    Returns:
        TaskService instance for task operations
    """
    # Set tenant context for this request
    tenant_manager.set_current_tenant(tenant_key)
    return TaskService(db_manager=db_manager, tenant_manager=tenant_manager)


async def get_message_service(
    tenant_key: str = Depends(get_tenant_key),
    db_manager: DatabaseManager = Depends(get_db_manager),
    tenant_manager: TenantManager = Depends(get_tenant_manager),
    websocket_manager=Depends(get_websocket_manager),
) -> MessageService:
    """
    Get MessageService instance for message management.

    Sets the tenant context before returning the service instance.

    Args:
        tenant_key: Tenant key from request context
        db_manager: Database manager instance
        tenant_manager: Tenant manager instance
        websocket_manager: WebSocket manager for real-time events

    Returns:
        MessageService instance for message operations
    """
    # Set tenant context for this request
    tenant_manager.set_current_tenant(tenant_key)
    return MessageService(db_manager=db_manager, tenant_manager=tenant_manager, websocket_manager=websocket_manager)


async def get_product_service(
    tenant_key: str = Depends(get_tenant_key),
    db_manager: DatabaseManager = Depends(get_db_manager),
    websocket_manager=Depends(get_websocket_manager),
) -> ProductService:
    """
    Get ProductService instance with tenant isolation.

    Args:
        tenant_key: Tenant key from request context
        db_manager: Database manager instance
        websocket_manager: WebSocket manager for real-time events

    Returns:
        ProductService instance configured for the current tenant
    """
    return ProductService(db_manager=db_manager, tenant_key=tenant_key, websocket_manager=websocket_manager)
