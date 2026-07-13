# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
FastAPI dependencies for request handling
"""

import os

from fastapi import Request

from giljo_mcp.tenant import TenantManager


def _get_default_tenant_key() -> str:
    """Resolve default tenant key from config.yaml or environment variable.

    Resolution order:
    1. ConfigManager (loaded from config.yaml tenant.default_key)
    2. DEFAULT_TENANT_KEY environment variable
    """
    from api.app_state import state

    if hasattr(state, "config") and state.config and state.config.tenant.default_tenant_key:
        return state.config.tenant.default_tenant_key

    key = os.getenv("DEFAULT_TENANT_KEY")
    if key:
        return key

    raise RuntimeError(
        "No default tenant key configured. Set tenant.default_key in config.yaml or DEFAULT_TENANT_KEY in .env"
    )


async def get_tenant_key(request: Request) -> str:
    """
    Get tenant key from request state and ensure it's set in context.

    This dependency ensures tenant context is available in endpoints
    even if ContextVar propagation fails across async boundaries.

    In server mode (LAN/WAN), missing tenant key returns 401.
    In localhost mode, defaults to predefined tenant key.
    """
    from fastapi import HTTPException

    from api.app_state import state
    from giljo_mcp.config_manager import get_config

    # Check if we're in setup mode first
    if hasattr(state, "api_state") and hasattr(state.api_state, "config"):
        setup_mode = getattr(state.api_state.config, "setup_mode", False)
        if setup_mode:
            # In setup mode, use environment variable or proper default tenant key
            return _get_default_tenant_key()

    # For OPTIONS requests (CORS preflight), return default tenant without validation
    # OPTIONS requests should not fail due to missing tenant context
    if request.method == "OPTIONS":
        return _get_default_tenant_key()

    # Get from request state (set by middleware)
    tenant_key = getattr(request.state, "tenant_key", None)

    if tenant_key:
        # Only validate tenant if we have a database
        if hasattr(state, "db_manager") and state.db_manager:
            # Ensure context is set (in case it was lost)
            TenantManager.set_current_tenant(tenant_key)
        return tenant_key

    # Fallback: try to get from context
    tenant_key = TenantManager.get_current_tenant()
    if tenant_key:
        return tenant_key

    # Check deployment mode to determine fallback behavior
    try:
        mode = get_config().get_nested("installation.mode", "localhost")

        # In server mode (LAN/WAN), missing tenant key is a security error
        if mode in ("server", "lan", "wan"):
            raise HTTPException(
                status_code=401, detail=f"Tenant key required for {mode} mode. Include X-Tenant-Key header."
            )
    except HTTPException:
        raise
    except (OSError, ValueError, KeyError):
        pass  # If config read fails, allow fallback  # nosec B110

    # Fallback to default tenant (localhost mode only)
    default_tenant = _get_default_tenant_key()
    # Only validate tenant if we have a database
    if hasattr(state, "db_manager") and state.db_manager:
        TenantManager.set_current_tenant(default_tenant)
    return default_tenant


async def get_db(request: Request):
    """
    Get async database session dependency for FastAPI endpoints.

    This dependency provides an AsyncSession for use in async FastAPI endpoints.
    The session is automatically managed and cleaned up after the request completes.

    Tenant carrier (BE6004C-2, RC-1 + RC-3): the session is opened with the
    tenant_key taken from ``request.state.tenant_key`` (set by AuthMiddleware at
    ``api/middleware/auth.py``). ``request.state`` lives on the Request object and
    survives the BaseHTTPMiddleware->endpoint task boundary, unlike the
    TenantManager ContextVar. Threading it here stamps ``session.info["tenant_key"]``
    (source="service") before any query runs, so the fail-closed guard both applies
    the tenant filter (RC-1) and accepts CRUD helpers that carry an explicit
    ``WHERE tenant_key=`` predicate (RC-3). Genuinely public / unauthenticated
    requests have no ``request.state.tenant_key`` and open a no-tenant session — those
    endpoints must not touch tenant-scoped models (or use a bypass in a later slice).

    Returns:
        AsyncSession: SQLAlchemy async database session

    Raises:
        RuntimeError: If database manager not initialized

    Note:
        This is the async version for FastAPI endpoints. For auth-specific endpoints,
        use get_db_session() from giljo_mcp.auth.dependencies which includes
        additional HTTP exception handling.
    """
    from api.app_state import state

    if not state.db_manager:
        raise RuntimeError("Database manager not initialized")

    tenant_key = getattr(request.state, "tenant_key", None)

    # Get an async session context manager
    async with state.db_manager.get_session_async(tenant_key=tenant_key) as session:
        # Per-endpoint attribution for audit-mode warnings (Slice 0 _audit_warn reads this).
        session.info["request_path"] = request.url.path
        yield session
