"""
FastAPI dependencies for request handling
"""

import os

from fastapi import Request

from src.giljo_mcp.tenant import TenantManager


async def get_tenant_key(request: Request) -> str:
    """
    Get tenant key from request state and ensure it's set in context.

    This dependency ensures tenant context is available in endpoints
    even if ContextVar propagation fails across async boundaries.

    In server mode (LAN/WAN), missing tenant key returns 401.
    In localhost mode, defaults to predefined tenant key.
    """
    from fastapi import HTTPException

    from api.app import state
    from src.giljo_mcp._config_io import read_config

    # Check if we're in setup mode first
    if hasattr(state, "api_state") and hasattr(state.api_state, "config"):
        setup_mode = getattr(state.api_state.config, "setup_mode", False)
        if setup_mode:
            # In setup mode, use environment variable or proper default tenant key
            default_tenant = os.getenv("DEFAULT_TENANT_KEY", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd")
            return default_tenant

    # For OPTIONS requests (CORS preflight), return default tenant without validation
    # OPTIONS requests should not fail due to missing tenant context
    if request.method == "OPTIONS":
        default_tenant = os.getenv("DEFAULT_TENANT_KEY", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd")
        return default_tenant

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
        config = read_config()
        mode = config.get("installation", {}).get("mode", "localhost")

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
    default_tenant = os.getenv("DEFAULT_TENANT_KEY", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd")
    # Only validate tenant if we have a database
    if hasattr(state, "db_manager") and state.db_manager:
        TenantManager.set_current_tenant(default_tenant)
    return default_tenant


async def get_db():
    """
    Get async database session dependency for FastAPI endpoints.

    This dependency provides an AsyncSession for use in async FastAPI endpoints.
    The session is automatically managed and cleaned up after the request completes.

    Returns:
        AsyncSession: SQLAlchemy async database session

    Raises:
        RuntimeError: If database manager not initialized

    Note:
        This is the async version for FastAPI endpoints. For auth-specific endpoints,
        use get_db_session() from src.giljo_mcp.auth.dependencies which includes
        additional HTTP exception handling.
    """
    from api.app import state

    if not state.db_manager:
        raise RuntimeError("Database manager not initialized")

    # Get an async session context manager
    async with state.db_manager.get_session_async() as session:
        yield session
