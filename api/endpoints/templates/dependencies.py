"""
Dependencies for Template Endpoints - Handover 0126

Provides dependency injection for TemplateService.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.dependencies import get_current_active_user, get_db_session
from src.giljo_mcp.models import User
from src.giljo_mcp.services.template_service import TemplateService
from api import state


def get_template_service(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db_session),
) -> TemplateService:
    """
    Dependency injection for TemplateService.

    Args:
        current_user: Authenticated user (from dependency)
        db: Database session (from dependency)

    Returns:
        TemplateService instance
    """
    return TemplateService(
        db_manager=state.db_manager,
        tenant_manager=state.tenant_manager
    )
