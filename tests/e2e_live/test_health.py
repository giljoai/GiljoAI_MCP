# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""(b) Health endpoint returns 200 through the full edge path.

``GET /health`` is the unauthenticated liveness probe (also Railway's
healthcheck path). Reaching it 200 over the live edge proves the proxy chain
forwards plain HTTP GETs to uvicorn and the app booted.
"""

from __future__ import annotations

import pytest


@pytest.mark.network
def test_health_endpoint_ok(http_client):
    resp = http_client.get("/health")
    assert resp.status_code == 200, resp.text

    body = resp.json()
    # Shape per api/wiring/events.py health_check(): {"status": ..., "checks": {...}}.
    # "degraded" is tolerated (e.g. a transient DB blip) — this test asserts
    # reachability + contract shape, not deep subsystem health.
    assert body.get("status") in {"healthy", "degraded"}, body
    assert isinstance(body.get("checks"), dict), body
