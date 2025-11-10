"""
Dependency injection for agent_jobs endpoints.

Provides FastAPI dependencies for service layer access.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.app import state
from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.services.orchestration_service import OrchestrationService


def get_orchestration_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> OrchestrationService:
    """
    Get OrchestrationService instance for agent job operations.

    Args:
        current_user: Authenticated user (for tenant isolation)
        db: Database session (required by dependency)

    Returns:
        OrchestrationService instance

    Note:
        Service is request-scoped and uses global db_manager/tenant_manager from app state.
    """
    # OrchestrationService uses db_manager (not session) for its own session management
    return OrchestrationService(
        db_manager=state.db_manager,
        tenant_manager=state.tenant_manager
    )
