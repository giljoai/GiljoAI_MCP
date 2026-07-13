# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Shared application state singleton.

Extracted from api.app to break the cyclic import chain where api.app
imports endpoint routers and those routers import state back from api.app.
This module has no imports from api.app or any endpoint module.
"""

import asyncio
import os
from typing import Any


# Edition detection: "ce" (default) or "saas". The legacy "demo" edition was
# folded into SaaS Solo (7-day trial) and fully removed (BE-6015); the demo prod
# box is decommissioned, so there is no longer a demo→saas coercion shim.
GILJO_MODE = os.environ.get("GILJO_MODE", "ce").lower()


def member_management_enabled() -> bool:
    """Whether this deployment lets an admin add or manage ADDITIONAL users in an
    existing organization (multi-seat member administration).

    Returns ``False`` for every edition that ships today:

    * **CE** — single-user, self-hosted (one operator per install).
    * **SaaS Solo** — single-seat hosted plan (one user per tenant).

    A future **SaaS Team** tier will be the first edition where this returns
    ``True``. That tier (``plan_tier == "team"``) is not built yet, so multi-user
    administration is a no-op surface across all current editions. This function
    is therefore the single, edition-wide flip point for "can an admin add other
    users": the admin user-creation endpoints (``POST /api/v1/users/`` and
    ``POST /api/auth/register``) gate on it and return 403 while it is ``False``.

    Design note (IMP-5042): policy lives HERE, at the edition boundary. The
    underlying service methods (``UserService.create_user``,
    ``AuthService.register_user``, ``create_user_in_org``) are deliberately left
    as capability-agnostic mechanisms — they are reused by signup
    (``ProvisioningService.provision_tenant``), first-admin bootstrap
    (``AuthService.create_first_admin``), and unit tests. Gating the mechanism
    would break those legitimate paths; gating the policy boundary does not.

    When SaaS Team ships, override this in the SaaS layer to consult the calling
    org's ``plan_tier`` (a SaaS-only column, so the read must live under
    ``saas/`` to honor the Deletion Test) and flip Team-tier admins to ``True``.
    """
    # No shipping edition (CE, SaaS Solo) supports multi-seat member management.
    # SaaS Team (plan_tier == "team") is not yet built — see IMP-5042.
    return False


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
        self.heartbeat_task: asyncio.Task | None = None
        self.cleanup_task: asyncio.Task | None = None
        self.metrics_sync_task: asyncio.Task | None = None
        self.api_key_expiry_task: asyncio.Task | None = None
        self.notification_purge_task: asyncio.Task | None = None  # BE-3011 retention valve
        self.mcp_session_cleanup_task: asyncio.Task | None = None  # BE-3011 retention valve
        self.oauth_code_cleanup_task: asyncio.Task | None = None  # BE-8000i retention valve
        self.health_monitor: Any = None
        self.health_monitor_task: asyncio.Task | None = None
        self.silence_detector: Any = None  # SilenceDetector (Handover 0491)
        self.api_call_count: dict[str, int] = {}
        self.mcp_call_count: dict[str, int] = {}
        self.system_prompt_service: Any = None  # SystemPromptService
        self.startup_complete: bool = False
        self.degraded_services: list[str] = []
        self.license: Any = None  # LicenseResult — set during lifespan startup
        self.pending_migration: bool = False
        self.update_available: dict | None = None  # {"commits_behind": int, "message": str}
        self.update_checker_task: asyncio.Task | None = None
        # INF-3009c: SaaS cache-backend boot mode. "unset" = REDIS_URL not
        # configured, CE in-process backend in use (default, also CE's only value).
        # "connected" = REDIS_URL verified reachable at boot; redis_client holds the
        # live client the /health endpoint reuses for a live ping.
        self.redis_mode: str = "unset"
        self.redis_client: Any = None


# Preserve the process-wide singleton across ``importlib.reload(api.app_state)``.
# Modules bind this instance BY REFERENCE at import time (``from api.app_state
# import state`` in api.app, api.wiring.events, middleware, ...). A reload that
# rebuilt ``state`` would FORK it: those earlier importers keep the old instance
# while ``api.app_state.state`` points at a new one, so a mutation on one is
# invisible to the other. reload() re-executes this module in its EXISTING
# __dict__, so reuse any instance already there; only a first import builds one.
# (TSK-9002: reload-forking left /health reading a stale APIState whose
# degraded_services was empty. GILJO_MODE above still refreshes on reload.)
state = globals().get("state") or APIState()
