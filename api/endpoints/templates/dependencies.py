# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Dependencies for Template Endpoints - Handover 0126

Provides dependency injection for TemplateService.
"""

from fastapi import Depends

from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.models import User
from giljo_mcp.services.template_service import TemplateService


def get_template_service(
    current_user: User = Depends(get_current_active_user),
) -> TemplateService:
    """
    Dependency injection for TemplateService.

    Args:
        current_user: Authenticated user (from dependency)

    Returns:
        TemplateService instance

    Note:
        Service creates its own sessions via db_manager.get_session_async().
    """
    # Import state lazily to avoid circular import
    from api.app_state import state

    return TemplateService(db_manager=state.db_manager, tenant_manager=state.tenant_manager)
