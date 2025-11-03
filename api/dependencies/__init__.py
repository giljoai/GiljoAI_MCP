"""
FastAPI Dependencies Module.

Provides dependency injection for various services used throughout the API.

Handover 0086A: Production-Grade Stage Project Architecture
Created: 2025-11-02
"""

# Import legacy dependencies - using lazy import to avoid circular dependency
import importlib

def __getattr__(name):
    """
    Lazy import for legacy dependencies to avoid circular imports.

    This allows code to import from api.dependencies while we transition
    from the flat file (dependencies.py) to the module structure (dependencies/).
    """
    if name in ("get_tenant_key", "get_db"):
        # Import the old dependencies.py module
        legacy_module = importlib.import_module("..dependencies", __name__)
        return getattr(legacy_module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


from .websocket import (
    get_websocket_manager,
    get_websocket_dependency,
    WebSocketDependency
)

__all__ = [
    # Legacy dependencies (backwards compatibility via __getattr__)
    "get_tenant_key",
    "get_db",
    # New WebSocket dependencies
    "get_websocket_manager",
    "get_websocket_dependency",
    "WebSocketDependency"
]