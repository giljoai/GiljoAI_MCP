# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""API startup modules - Extracted from monolithic lifespan function

This package contains modularized startup/shutdown logic for the FastAPI application.
Each module is independently testable and focused on a single responsibility.

Modules:
    database: Database initialization and configuration
    core_services: Core service initialization (TenantManager, WebSocketManager, etc.)
    event_bus: Event bus and WebSocket listener setup
    background_tasks: Background task management (cleanup, metrics sync, purge)
    health_monitor: Agent health monitoring service
    silence_detector: Silent agent detection service (Handover 0491)
    validation: Setup state validation
    shutdown: Graceful shutdown procedures
"""

from api.startup.background_tasks import init_background_tasks
from api.startup.core_services import init_core_services
from api.startup.database import init_database
from api.startup.event_bus import init_event_bus
from api.startup.health_monitor import init_health_monitor
from api.startup.shutdown import shutdown
from api.startup.silence_detector import init_silence_detector
from api.startup.validation import init_validation

__all__ = [
    "init_background_tasks",
    "init_core_services",
    "init_database",
    "init_event_bus",
    "init_health_monitor",
    "init_silence_detector",
    "init_validation",
    "shutdown",
]
