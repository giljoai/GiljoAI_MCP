# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SaaS enforcement-wiring boot gate — Phases 8.6 / 8.7 (SEC-9131, fail-loud).

Extracted from ``api/app.py``'s lifespan so the fail-loud policy is unit-testable
(mirrors INF-3009c's extraction of Phase 8.5 into ``cache_backends_gate.py``).

Policy: in SaaS mode a failure to register the tenant-scope widening (Phase 8.6)
or the /mcp subscription gate (Phase 8.7) ABORTS boot — the exception propagates
out of ``lifespan()`` and stops uvicorn, exactly like the Phase 0 license check
and Phase 8.5 Redis gate. Silently degrading would ship prod with enforcement
absent while looking healthy (BE-6069 incident class).

Both functions are pure no-ops for CE (``giljo_mode != "saas"``) and reach the
``saas/`` tree only through ``importlib`` — no static SaaS import crosses the
boundary, so the Deletion Test holds.
"""

from __future__ import annotations

import importlib
import logging


logger = logging.getLogger("api.app")


def register_saas_tenant_scoped_models(*, giljo_mode: str) -> None:
    """Phase 8.6 — register SaaS-only tenant-scoped models (BE-6037). Fail-loud."""
    if giljo_mode != "saas":
        return
    try:
        importlib.import_module("giljo_mcp.saas.tenant_registration").register_saas_tenant_scoped_models()
        logger.info("SaaS tenant-scoped models registered")
    except Exception:
        logger.critical(
            "SaaS Phase 8.6 [saas_tenant_registration] failed — aborting boot "
            "(SEC-9131 fail-loud): tenant-scope widening must never be silently absent."
        )
        raise


def register_mcp_subscription_gate(*, giljo_mode: str) -> None:
    """Phase 8.7 — register the /mcp subscription gate (BE-6060d). Fail-loud."""
    if giljo_mode != "saas":
        return
    try:
        importlib.import_module("giljo_mcp.saas.billing.mcp_subscription_gate").register()
        logger.info("MCP subscription gate registered")
    except Exception:
        logger.critical(
            "SaaS Phase 8.7 [mcp_subscription_gate] failed — aborting boot "
            "(SEC-9131 fail-loud): /mcp billing enforcement must never be silently absent."
        )
        raise
