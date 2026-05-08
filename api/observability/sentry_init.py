# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE+SaaS] Module is import-safe in CE; init_sentry is a no-op outside saas/demo.

"""Sentry SDK initialization with PII scrubbing (INF-5063).

Edition gating lives in this module: ``init_sentry()`` is a no-op unless
``GILJO_MODE in ("saas", "demo")``. CE imports remain safe — the ``sentry_sdk``
package is only imported lazily inside the gate, so a CE deployment with no
``sentry-sdk`` installed will still start cleanly as long as ``init_sentry``
short-circuits before the import.

This is the boundary: api/observability/ lives in CE-shared territory, but
the runtime path is SaaS/Demo only.
"""

from __future__ import annotations

import logging
import os
from typing import Any


logger = logging.getLogger(__name__)


_PII_HEADERS_LOWER = frozenset(
    {
        "authorization",
        "cookie",
        "x-api-key",
        "x-csrf-token",
    }
)


def _scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any] | None:
    """Drop request body and PII headers before transmission to Sentry."""
    request = event.get("request")
    if isinstance(request, dict):
        request.pop("data", None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            scrubbed = {k: v for k, v in headers.items() if k.lower() not in _PII_HEADERS_LOWER}
            request["headers"] = scrubbed
    return event


def init_sentry(mode: str | None = None) -> bool:
    """Initialize Sentry for SaaS/Demo. No-op for CE or missing DSN.

    Returns True when ``sentry_sdk.init`` was actually called.
    """
    resolved_mode = mode if mode is not None else os.environ.get("GILJO_MODE", "ce")
    if resolved_mode not in ("saas", "demo"):
        return False

    dsn = os.environ.get("SENTRY_DSN_BACKEND")
    if not dsn:
        logger.warning(
            "SENTRY_DSN_BACKEND not set in %s mode — backend error tracking disabled",
            resolved_mode,
        )
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=resolved_mode,
        traces_sample_rate=0.1,
        sample_rate=1.0,
        send_default_pii=False,
        integrations=[FastApiIntegration()],
        before_send=_scrub_event,
    )
    logger.info("Sentry initialized (environment=%s)", resolved_mode)
    return True


def set_tenant_context(tenant_key: str | None, user_id: str | None = None) -> None:
    """Tag the current Sentry scope with tenant_key and (optionally) user id.

    Safe to call in any edition: import is local, no-op when sentry_sdk
    isn't installed or hasn't been initialized.
    """
    if not tenant_key:
        return
    try:
        import sentry_sdk
    except ImportError:
        return

    sentry_sdk.set_tag("tenant_key", tenant_key)
    if user_id:
        sentry_sdk.set_user({"id": user_id})
