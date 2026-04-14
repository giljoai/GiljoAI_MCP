# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Shared application state singleton.

Extracted from api.app to break the cyclic import chain where api.app
imports endpoint routers and those routers import state back from api.app.
This module has no imports from api.app or any endpoint module.
"""

import asyncio
import os
from typing import Any, Optional


# Edition detection: "ce" (default), "demo", or "saas"
GILJO_MODE = os.environ.get("GILJO_MODE", "ce").lower()


class APIState:
    """Shared application state — holds references to all core services.

    Attributes are typed as Any to avoid importing heavy modules (DatabaseManager,
    AuthManager, etc.) at module level, which would re-introduce the import cycle.
    The concrete types are set during lifespan startup in api.app.
    """

    def __init__(self):
        self.db_manager: Any = None
        self.config: Any = None  # ConfigManager
        self.auth: Any = None  # AuthManager
        self.tenant_manager: Any = None  # TenantManager
        self.tool_accessor: Any = None  # ToolAccessor
        self.websocket_manager: Any = None  # WebSocketManager
        self.websocket_broker: Any = None  # WebSocketEventBroker (0379e)
        self.event_bus: Any = None  # EventBus instance (Handover 0111 Issue #1)
        self.connections: dict[str, Any] = {}
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.cleanup_task: Optional[asyncio.Task] = None
        self.metrics_sync_task: Optional[asyncio.Task] = None
        self.health_monitor: Any = None
        self.health_monitor_task: Optional[asyncio.Task] = None
        self.silence_detector: Any = None  # SilenceDetector (Handover 0491)
        self.api_call_count: dict[str, int] = {}
        self.mcp_call_count: dict[str, int] = {}
        self.system_prompt_service: Any = None  # SystemPromptService
        self.startup_complete: bool = False
        self.degraded_services: list[str] = []
        self.license: Any = None  # LicenseResult — set during lifespan startup
        self.pending_migration: bool = False
        self.update_available: dict | None = None  # {"commits_behind": int, "message": str}
        self.update_checker_task: Optional[asyncio.Task] = None


state = APIState()
