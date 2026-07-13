# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Dependency injection for projects endpoints.

Provides FastAPI dependencies for service layer access.
"""

import logging

from fastapi import Depends

from api.dependencies import get_tenant_key
from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.models import User
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


async def get_project_service(
    tenant_key: str = Depends(get_tenant_key),
    current_user: User = Depends(get_current_active_user),
) -> ProjectService:
    """
    Get ProjectService instance for project operations.

    Args:
        tenant_key: Tenant key from request context (sets global tenant context)
        current_user: Authenticated user (authoritative tenant source)

    Returns:
        ProjectService instance

    Note:
        BE6004C-3 / RC-2: This dependency is ``async`` so that
        ``TenantManager.set_current_tenant()`` runs in the request's event loop
        and reliably propagates to the endpoint coroutine. A prior sync ``def``
        ran in a threadpool, so the ContextVar set here did not survive the
        boundary (R3). The authoritative tenant is ``current_user.tenant_key``;
        the summary sub-service is additionally threaded the explicit key by the
        endpoint, making that read fully ContextVar-independent.

        Service is request-scoped and uses global db_manager/tenant_manager from
        app state. Service creates its own sessions via
        ``db_manager.get_session_async()``.
    """
    # Import state lazily to avoid circular import
    from api.app_state import state

    if tenant_key != current_user.tenant_key:
        TenantManager.set_current_tenant(current_user.tenant_key)

    return ProjectService(
        db_manager=state.db_manager,
        tenant_manager=state.tenant_manager,
        websocket_manager=state.websocket_manager,
    )
