# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6019 regression: startup warm-up (cold-start mitigation).

The warm-up runs in the FastAPI lifespan before the app reports ready. It must:
  * configure ORM mappers and issue a ``SELECT 1`` to warm the DB pool, and
  * NEVER propagate an error (a warm-up hiccup must not block or crash boot).

These are the load-bearing guarantees, so the guard exercises the function
directly with stubbed state.
"""

from __future__ import annotations

import logging
from types import SimpleNamespace
from typing import Self
from unittest.mock import AsyncMock, MagicMock

import pytest

from api.app import _warm_up


class _FakeAsyncSession:
    """Minimal async-context-manager session whose execute is awaitable."""

    def __init__(self) -> None:
        self.execute = AsyncMock()

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(self, *exc) -> bool:
        return False


@pytest.mark.asyncio
async def test_warm_up_pings_db_and_configures_mappers(monkeypatch):
    monkeypatch.setenv("GILJO_WARM_DB_CONNECTIONS", "1")
    called = {"configure_mappers": 0}
    monkeypatch.setattr(
        "sqlalchemy.orm.configure_mappers",
        lambda: called.__setitem__("configure_mappers", called["configure_mappers"] + 1),
    )
    session = _FakeAsyncSession()
    state = SimpleNamespace(db_manager=SimpleNamespace(AsyncSessionLocal=lambda: session))

    await _warm_up(state)

    assert called["configure_mappers"] == 1
    session.execute.assert_awaited_once()
    # The warm-up query must be a raw SELECT 1 (tenant-guard-safe).
    sent_sql = str(session.execute.await_args.args[0])
    assert "SELECT 1" in sent_sql


@pytest.mark.asyncio
async def test_warm_up_opens_multiple_pooled_connections(monkeypatch):
    # BE-6029: warm several pooled connections concurrently, not just one, so
    # the first post-deploy query burst does not pay per-connection handshakes
    # (the latency spike that let Railway reap the idle WebSocket).
    monkeypatch.setenv("GILJO_WARM_DB_CONNECTIONS", "4")
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", lambda: None)

    opened: list[_FakeAsyncSession] = []

    def _factory() -> _FakeAsyncSession:
        session = _FakeAsyncSession()
        opened.append(session)
        return session

    state = SimpleNamespace(db_manager=SimpleNamespace(AsyncSessionLocal=_factory))

    await _warm_up(state)

    # Four distinct connections opened, each issuing the warm-up SELECT 1.
    assert len(opened) == 4
    for session in opened:
        session.execute.assert_awaited_once()


@pytest.mark.asyncio
async def test_warm_up_never_raises_on_db_failure_and_logs_error(monkeypatch, caplog):
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", lambda: None)
    # AsyncSessionLocal() itself blows up — warm-up must swallow it.
    state = SimpleNamespace(
        db_manager=SimpleNamespace(AsyncSessionLocal=MagicMock(side_effect=RuntimeError("db down")))
    )
    with caplog.at_level(logging.ERROR):
        await _warm_up(state)  # must not raise
    # INF-6020: failure must log at ERROR so Sentry's LoggingIntegration alerts.
    assert any(r.levelno == logging.ERROR for r in caplog.records), "warm-up failure must log at ERROR"


@pytest.mark.asyncio
async def test_warm_up_tolerates_missing_db_manager(monkeypatch):
    calls = {"n": 0}
    monkeypatch.setattr("sqlalchemy.orm.configure_mappers", lambda: calls.__setitem__("n", calls["n"] + 1))
    state = SimpleNamespace(db_manager=None)
    await _warm_up(state)  # must not raise
    # Mappers are still configured even when there is no DB to ping.
    assert calls["n"] == 1
