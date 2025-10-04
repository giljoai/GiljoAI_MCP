"""
FastAPI dependencies for request handling
"""

import os
from fastapi import Request
from sqlalchemy.orm import Session
from giljo_mcp.tenant import TenantManager


async def get_tenant_key(request: Request) -> str:
    """
    Get tenant key from request state and ensure it's set in context.

    This dependency ensures tenant context is available in endpoints
    even if ContextVar propagation fails across async boundaries.
    """
    # For OPTIONS requests (CORS preflight), return default tenant without validation
    # OPTIONS requests should not fail due to missing tenant context
    if request.method == "OPTIONS":
        default_tenant = os.getenv("DEFAULT_TENANT_KEY", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd")
        return default_tenant

    # Get from request state (set by middleware)
    tenant_key = getattr(request.state, "tenant_key", None)

    if tenant_key:
        # Ensure context is set (in case it was lost)
        TenantManager.set_current_tenant(tenant_key)
        return tenant_key

    # Fallback: try to get from context
    tenant_key = TenantManager.get_current_tenant()
    if tenant_key:
        return tenant_key

    # Fallback to default tenant instead of raising error
    default_tenant = os.getenv("DEFAULT_TENANT_KEY", "tk_cyyOVf1HsbOCA8eFLEHoYUwiIIYhXjnd")
    TenantManager.set_current_tenant(default_tenant)
    return default_tenant


def get_db() -> Session:
    """
    Get database session dependency.
    Creates a new database session for the request and ensures it's closed after use.
    """
    from api.app import state

    if not state.db_manager:
        raise RuntimeError("Database manager not initialized")

    # Get a synchronous session for the request
    db = state.db_manager.get_session()
    try:
        yield db
    finally:
        db.close()
