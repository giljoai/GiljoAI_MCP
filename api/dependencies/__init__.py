# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
FastAPI Dependencies Module.

Provides dependency injection for various services used throughout the API.

Handover 0086A: Production-Grade Stage Project Architecture
Created: 2025-11-02
"""

from .core import get_db, get_tenant_key
from .websocket import WebSocketDependency, get_websocket_dependency, get_websocket_manager


__all__ = [
    "WebSocketDependency",
    "get_db",
    "get_tenant_key",
    "get_websocket_dependency",
    "get_websocket_manager",
]
