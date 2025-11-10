"""
Dependencies for Product Endpoints - Handover 0127b

Provides dependency injection for ProductService.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_tenant_key
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import User
from src.giljo_mcp.services import ProductService


async def get_db_manager(db: AsyncSession = Depends(get_db_session)) -> DatabaseManager:
    """
    Get DatabaseManager instance from session.

    Note: This is a temporary helper. In production, DatabaseManager should be
    injected directly from the application context.
    """
    # For now, we'll get the db_manager from the app state
    # This assumes db_manager is available in the FastAPI app state
    from src.giljo_mcp.database import db_manager as global_db_manager
    return global_db_manager


async def get_product_service(
    tenant_key: str = Depends(get_tenant_key),
    db_manager: DatabaseManager = Depends(get_db_manager),
) -> ProductService:
    """
    Get ProductService instance with tenant isolation.

    Args:
        tenant_key: Tenant key from request context
        db_manager: Database manager instance

    Returns:
        ProductService instance configured for the current tenant
    """
    return ProductService(db_manager=db_manager, tenant_key=tenant_key)
