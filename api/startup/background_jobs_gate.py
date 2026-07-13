# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Per-process background-jobs gate (INF-3009b).

A single env switch, ``GILJO_RUN_BACKGROUND_JOBS``, decides whether THIS process
runs the shared cross-tenant maintenance/reaper background loops (trial reaper,
deletion reaper, backup scheduler, token/session/notification sweeps, one-time
startup purges).

Why this exists
---------------
Every uvicorn worker today starts the full background-job fleet with no leader
election. The moment ``WEB_CONCURRENCY > 1`` that means duplicate customer
trial-warning/expiry emails and racing destructive deletion sweeps — the hard
wall between ~100-200 users and 1000+ (ARCHITECTURE_AUDIT_2026-06-11, the only
CRITICAL). The path forward is a dedicated single-replica worker service that
owns these loops while the web tier runs with them OFF.

Contract
--------
- **Default ON.** Unset or empty ``GILJO_RUN_BACKGROUND_JOBS`` returns ``True``.
  This keeps CE (single process) and any not-yet-split single-web-process SaaS
  deployment byte-identical to today — the gate only changes behaviour when an
  operator explicitly turns it OFF on the web service.
- OFF only for the explicit falsey tokens ``0 / false / no / off`` (any case).

NOT gated by this switch: the per-worker telemetry flushers
(``sync_api_metrics_to_db`` / ``sync_ws_metrics_to_db``). Those drain THIS
worker's in-memory request/WebSocket counters, so they MUST run in every web
worker — routing them to a request-less worker process would silently lose
telemetry (the audit's "justify staying per-worker" carve-out).
"""

from __future__ import annotations

import os


ENV_VAR = "GILJO_RUN_BACKGROUND_JOBS"

# Explicit opt-out tokens. Everything else (including unset/empty) means ON.
_FALSEY = {"0", "false", "no", "off"}


def should_run_background_jobs() -> bool:
    """Return whether this process should run shared background maintenance loops.

    Default ON; see module docstring for the full contract.
    """
    raw = os.environ.get(ENV_VAR, "").strip().lower()
    if raw == "":
        return True
    return raw not in _FALSEY
