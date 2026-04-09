# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
FastAPI Dependencies Module.

Provides dependency injection for various services used throughout the API.

Handover 0086A: Production-Grade Stage Project Architecture
Created: 2025-11-02
"""

# Import WebSocket dependencies from this module
# Import legacy dependencies from the sibling dependencies.py file
# Use importlib to load the .py file directly (avoiding package/module conflict)
import importlib.util
from pathlib import Path

from .websocket import WebSocketDependency, get_websocket_dependency, get_websocket_manager

_deps_file = str(Path(__file__).parent.parent / "dependencies.py")
_spec = importlib.util.spec_from_file_location("_legacy_dependencies", _deps_file)
_legacy_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_legacy_module)

# Re-export legacy dependencies for backwards compatibility
get_tenant_key = _legacy_module.get_tenant_key
get_db = _legacy_module.get_db

__all__ = [
    "WebSocketDependency",
    "get_db",
    # Legacy dependencies (backwards compatibility)
    "get_tenant_key",
    "get_websocket_dependency",
    # WebSocket dependencies
    "get_websocket_manager",
]
