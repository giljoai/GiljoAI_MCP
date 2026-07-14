# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE6004C regression: the original CE break — unauthenticated /api/setup/status
must return 200 under the fail-closed tenant guard (GILJO_TENANT_GUARD_MODE=enforce).

History (the bug this proves fixed):
    BE-6004 made the ORM tenant guard fail-closed. `get_setup_security_status`
    runs two contextless `select(func.count(User.id))` queries on a bare,
    pre-auth session (no JWT decoded yet -> no tenant context). Under enforce
    that raised TenantIsolationError -> HTTP 500 -> the CE frontend fell back to
    `is_fresh_install:true` -> the welcome/create-admin screen, login unreachable.
    This is the symptom that started the entire BE6004C repair chain.

Fix under test:
    The two system-wide counts are wrapped in `tenant_isolation_bypass(... User)`
    (mirroring AuthRepository.get_total_user_count), so the public install-state
    probe completes and returns the real signal instead of 500/fail-secure.

Failing layer = the endpoint (per CLAUDE.md BE-5042 lesson): driven through the
production ASGI app via the real FastAPI DI / middleware stack. The api_client
fixture overrides get_db_session with a BARE session (no tenant threading), so
without the bypass this query hits the guard with no context — exactly the
production pre-auth condition.

Parallel-safe: no seeded rows, no module globals, monkeypatch-scoped env only.
"""

import pytest


@pytest.mark.asyncio
async def test_setup_status_unauthenticated_returns_200_under_enforce(api_client, monkeypatch):
    """Unauth GET /api/setup/status -> 200 with a real signal under enforce.

    Asserting `total_users_count` is present is the load-bearing check: the
    success path includes it, while the fail-secure `except` fallback does NOT.
    So this distinguishes "the bypass actually ran the count" from "an exception
    was swallowed into the fallback" — proving the bypass, not just the
    broadened handler.
    """
    # Force fail-closed enforcement regardless of ambient env on this worker.
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")

    response = await api_client.get("/api/setup/status")

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    data = response.json()

    # Present ONLY on the success path; absent on the fail-secure fallback.
    assert "total_users_count" in data, (
        "Response is the fail-secure fallback, not the real signal — the "
        "contextless User count was swallowed instead of bypassed."
    )
    assert isinstance(data["total_users_count"], int)
    assert data["total_users_count"] >= 0
    # Sanity: the normal contract fields are present.
    assert "route_signal" in data
    assert "setup_complete" in data
