# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""SEC-9168 — anonymous /health must not leak exception detail (CWE-209).

Failing layer this regression-locks: the /health endpoint (api/wiring/events.py)
returned ``f"unhealthy: {e!s}"`` for database and redis check failures, so an
UNAUTHENTICATED caller could read internal hostnames/ports/driver detail from
the raw exception text during an outage (CodeQL alert #4, py/stack-trace-exposure
family). The fix: /health returns the generic ``"unhealthy: database"`` /
``"unhealthy: redis"``, the full detail goes to ``logger.warning`` and to
``state.health_detail``, which only the AUTHENTICATED ``/api/system/status``
endpoint surfaces.

Exercised at the ASGI-transport endpoint layer like the sibling INF-3009c
tests in tests/api/test_inf3009c_redis_failloud.py.

Edition Scope: Both (/health is CE-shipped; the redis branch is SaaS-only).

Parallel-safe: monkeypatch-scoped state mutation only; no DB, no module-level
mutable state, no ordering dependency.
"""

from __future__ import annotations

import pytest


DB_SENTINEL = "internal-db-host-9f7.local:5432 refused"
REDIS_SENTINEL = "internal-redis-host-3c1.local:6379 reset"


class _FailingSessionCtx:
    async def __aenter__(self):
        raise ConnectionError(DB_SENTINEL)

    async def __aexit__(self, *exc_info):
        return False


class _FailingDbManager:
    def get_session_async(self):
        return _FailingSessionCtx()


class _HealthySession:
    async def execute(self, *args, **kwargs):
        return None


class _HealthySessionCtx:
    async def __aenter__(self):
        return _HealthySession()

    async def __aexit__(self, *exc_info):
        return False


class _HealthyDbManager:
    def get_session_async(self):
        return _HealthySessionCtx()


class _DyingRedisClient:
    async def ping(self):
        raise ConnectionError(REDIS_SENTINEL)


def _build_app(monkeypatch, *, giljo_mode: str, db_manager, redis_mode: str = "unset", redis_client=None):
    from fastapi import FastAPI

    from api.app_state import state
    from api.wiring import events as events_mod

    monkeypatch.setattr(events_mod, "GILJO_MODE", giljo_mode)
    monkeypatch.setattr(state, "db_manager", db_manager)
    monkeypatch.setattr(state, "websocket_manager", object())
    monkeypatch.setattr(state, "connections", {})
    monkeypatch.setattr(state, "degraded_services", [])
    monkeypatch.setattr(state, "redis_mode", redis_mode)
    monkeypatch.setattr(state, "redis_client", redis_client)
    monkeypatch.setattr(state, "health_detail", {}, raising=False)
    monkeypatch.setattr(state, "pending_migration", False)
    monkeypatch.setattr(state, "update_available", None)

    app = FastAPI()
    events_mod.register_event_handlers(app)
    return app


async def _get(app, path: str):
    from httpx import ASGITransport, AsyncClient

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


@pytest.mark.asyncio
async def test_anonymous_health_db_failure_carries_no_exception_text(monkeypatch):
    """The regression target: raw exception text must never reach /health."""
    app = _build_app(monkeypatch, giljo_mode="ce", db_manager=_FailingDbManager())

    response = await _get(app, "/health")
    body = response.json()

    assert DB_SENTINEL not in response.text
    assert body["checks"]["database"] == "unhealthy: database"
    assert body["status"] == "degraded"


@pytest.mark.asyncio
async def test_anonymous_health_redis_failure_carries_no_exception_text(monkeypatch):
    app = _build_app(
        monkeypatch,
        giljo_mode="saas",
        db_manager=_HealthyDbManager(),
        redis_mode="connected",
        redis_client=_DyingRedisClient(),
    )

    response = await _get(app, "/health")
    body = response.json()

    assert REDIS_SENTINEL not in response.text
    assert body["checks"]["redis"] == "unhealthy: redis"
    assert body["status"] == "degraded"


@pytest.mark.asyncio
async def test_authenticated_system_status_surfaces_the_detail(monkeypatch):
    """The detail is not lost: /api/system/status (authenticated) exposes it."""
    from giljo_mcp.auth.dependencies import get_current_active_user

    app = _build_app(monkeypatch, giljo_mode="ce", db_manager=_FailingDbManager())
    app.dependency_overrides[get_current_active_user] = object

    # Populate the detail exactly the way production does: via a /health poll.
    await _get(app, "/health")
    response = await _get(app, "/api/system/status")
    body = response.json()

    assert DB_SENTINEL in body["health_detail"]["database"]
    # Pre-existing contract keys are still present.
    assert "pending_migration" in body
    assert "update_available" in body


@pytest.mark.asyncio
async def test_health_recovery_clears_the_stashed_detail(monkeypatch):
    """A healthy check clears the stale detail so status reflects reality."""
    from api.app_state import state
    from giljo_mcp.auth.dependencies import get_current_active_user

    app = _build_app(monkeypatch, giljo_mode="ce", db_manager=_HealthyDbManager())
    app.dependency_overrides[get_current_active_user] = object
    state.health_detail["database"] = "stale detail from a previous outage"

    await _get(app, "/health")
    response = await _get(app, "/api/system/status")

    assert response.json()["health_detail"] == {}
