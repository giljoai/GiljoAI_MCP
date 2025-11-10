"""
Dependency injection for projects endpoints.

Provides FastAPI dependencies for service layer access.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import state
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.services.project_service import ProjectService


def get_project_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> ProjectService:
    """
    Get ProjectService instance for project operations.

    Args:
        current_user: Authenticated user (for tenant isolation)
        db: Database session (required by dependency)

    Returns:
        ProjectService instance

    Note:
        Service is request-scoped and uses global db_manager/tenant_manager from app state.
    """
    # ProjectService uses db_manager (not session) for its own session management
    return ProjectService(
        db_manager=state.db_manager,
        tenant_manager=state.tenant_manager
    )
