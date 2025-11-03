"""
FastAPI Dependencies Module.

Provides dependency injection for various services used throughout the API.

Handover 0086A: Production-Grade Stage Project Architecture
Created: 2025-11-02
"""

from .websocket import (
    get_websocket_manager,
    get_websocket_dependency,
    WebSocketDependency
)

__all__ = [
    "get_websocket_manager",
    "get_websocket_dependency",
    "WebSocketDependency"
]