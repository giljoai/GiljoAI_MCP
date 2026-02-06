"""
FastAPI dependencies for request handling
"""

import os
from typing import Generator

from fastapi import Request
from sqlalchemy.orm import Session

from src.giljo_mcp.tenant import TenantManager


async def get_tenant_key(request: Request) -> str:
    """
    Get tenant key from request state and ensure it's set in context.

    This dependency ensures tenant context is available in endpoints
    even if ContextVar propagation fails across async boundaries.

    In server mode (LAN/WAN), missing tenant key returns 401.
    In localhost mode, defaults to predefined tenant key.
    """
    from pathlib import Path

    import yaml
    from fastapi import HTTPException

    from api.app import state

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
        config_path = Path(__file__).parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f)
                mode = config.get("installation", {}).get("mode", "localhost")

            # In server mode (LAN/WAN), missing tenant key is a security error
            if mode in ("server", "lan", "wan"):
                raise HTTPException(
                    status_code=401, detail=f"Tenant key required for {mode} mode. Include X-Tenant-Key header."
                )
    except HTTPException:
        raise
    except Exception:
        pass  # If config read fails, allow fallback  # nosec B110

    # Fallback to default tenant (localhost mode only)
    default_tenant = os.getenv("DEFAULT_TENANT_KEY", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd")
    # Only validate tenant if we have a database
    if hasattr(state, "db_manager") and state.db_manager:
        TenantManager.set_current_tenant(default_tenant)
    return default_tenant


def get_db() -> Generator[Session, None, None]:
    """
    Get database session dependency.
    Creates a new database session for the request and ensures it's closed after use.
    """
    from api.app import state

    if not state.db_manager:
        raise RuntimeError("Database manager not initialized")

    # Get a synchronous session context manager
    session_ctx = state.db_manager.get_session()
    db = session_ctx.__enter__()
    try:
        yield db
    finally:
        session_ctx.__exit__(None, None, None)
