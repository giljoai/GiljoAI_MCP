# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""TSK-9002 regression: re-creating ``api.app_state`` must not fork the shared
``state`` singleton.

Failing layer: the process-wide ``APIState`` singleton in ``api.app_state`` and
every module that binds it by reference (``from api.app_state import state`` in
``api.wiring.events``, ``api.app``, middleware, ...). Two test practices used to
rebuild that module and fork the singleton, so a mutation on one instance was
invisible to a handler reading the other (the /health ``degraded_services``
KeyError under pytest-xdist):

  * ``importlib.reload(api.app_state)`` — the mode-gate tests. Fixed at the
    source: ``api/app_state.py`` reuses any ``state`` already in the module
    ``__dict__`` (reload re-executes in place), so reload no longer forks.
  * ``sys.modules.pop("api.app_state")`` + re-import — ``test_giljo_mode``.
    That builds a FRESH module ``__dict__``, so the source guard cannot help;
    that test now restores the original module at teardown.

These regressions are HERMETIC: each controls its own precondition and restores
what it touches, so it can never depend on (or be broken by) a co-scheduled
test's module surgery.
"""

from __future__ import annotations

import importlib

import pytest


@pytest.mark.asyncio
async def test_reload_preserves_state_singleton_identity(monkeypatch):
    """``importlib.reload(api.app_state)`` must keep the SAME ``state`` instance
    (reload re-executes in the existing module ``__dict__``), never a fork.

    Hermetic: only touches ``api.app_state``; restores it in ``finally``."""
    import api.app_state as app_state_module

    before = app_state_module.state
    monkeypatch.setenv("GILJO_MODE", "saas")
    try:
        importlib.reload(app_state_module)
        assert app_state_module.state is before, "reload FORKED the state singleton"
        # The module-level constant still refreshes from the env on reload.
        assert app_state_module.GILJO_MODE == "saas"
    finally:
        monkeypatch.delenv("GILJO_MODE", raising=False)
        importlib.reload(app_state_module)
        assert app_state_module.state is before


@pytest.mark.asyncio
async def test_health_reports_degraded_services_across_app_state_reload(monkeypatch):
    """End-to-end failing-layer guard: after ``api.app_state`` is reloaded, the
    /health handler and its caller must still observe the SAME ``state``.

    Hermetic: forces ``api.wiring.events.state`` and ``api.app_state.state`` into
    agreement at the start (healing any fork a prior test left) and restores it,
    so this test verifies the reload-preservation property in isolation."""
    from httpx import ASGITransport, AsyncClient

    import api.app_state as app_state_module
    import api.wiring.events as events_module

    saved_events_state = events_module.state
    # Controlled precondition: the handler's module and the caller agree.
    events_module.state = app_state_module.state
    monkeypatch.setenv("GILJO_MODE", "saas")
    try:
        # reload preserves the singleton, so events_module.state stays valid.
        importlib.reload(app_state_module)
        assert events_module.state is app_state_module.state

        from fastapi import FastAPI

        app = FastAPI()
        events_module.register_event_handlers(app)

        monkeypatch.setattr(app_state_module.state, "degraded_services", ["backup_scheduler", "deletion_reaper"])

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/health")

        body = response.json()
        assert body["status"] == "degraded"
        assert body["checks"]["degraded_services"] == ["backup_scheduler", "deletion_reaper"]
    finally:
        monkeypatch.delenv("GILJO_MODE", raising=False)
        importlib.reload(app_state_module)
        events_module.state = saved_events_state
