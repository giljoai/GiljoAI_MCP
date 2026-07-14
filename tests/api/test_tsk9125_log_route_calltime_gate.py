# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""TSK-9125 — CE-only log-download routes must be gated at CALL time, not latched.

Failing layer this regression-locks: ``api/endpoints/downloads.py`` used to wrap
its three CE-only ``/api/download/logs/*`` routes in a module-level
``if GILJO_MODE in ("", "ce")`` evaluated at IMPORT time on a snapshotted
``api.app_state.GILJO_MODE`` constant. Because ``downloads.router`` is a shared
module singleton, whichever edition the module was FIRST imported in for the
process froze the log-route membership for the whole process — an import-order
dependency no call-time ``api.app.GILJO_MODE`` pin could undo.

Under pytest-xdist that made the route surface non-deterministic: a SaaS
middleware test (e.g. tests/saas/middleware/test_security_csp.py, which builds in
``GILJO_MODE=saas``) that happened to trigger the first import of ``downloads``
latched the log routes OUT, and tests/unit/test_be6042b_app_surface.py then saw a
CE app missing three routes and failed its strict route-surface lock.

The fix moves the routes onto an always-defined ``downloads.log_router`` and gates
its INCLUSION at call time in ``register_routers`` (reading ``api.app.GILJO_MODE``,
the same seam every other conditional router uses). These tests pin the invariant
at the router-registration layer where the bug lived: two builds in the SAME
process — CE then SaaS — produce the correct, edition-specific surface regardless
of import order. On the pre-fix import-time latch, one of the two directions is
always wrong, so this fails RED.
"""

from __future__ import annotations

from fastapi import FastAPI

import api.app as app_module
from api.wiring.routers import register_routers
from tests.helpers.route_surface import iter_effective_routes


_LOG_PATHS = frozenset(
    {
        "/api/download/logs/current",
        "/api/download/logs/archives",
        "/api/download/logs/archive/{filename}",
    }
)


def _registered_paths(*, giljo_mode: str, monkeypatch) -> set[str]:
    """Register all routers on a fresh app with GILJO_MODE pinned, return paths."""
    monkeypatch.setattr(app_module, "GILJO_MODE", giljo_mode)
    app = FastAPI()
    register_routers(app)
    return {route.path for route in iter_effective_routes(app.routes)}


def test_log_routes_present_in_ce_and_absent_in_saas_same_process(monkeypatch):
    """The decisive call-time gate: a CE build carries the log routes and a SaaS
    build in the SAME process does not. The import-time latch could satisfy at
    most one direction (whichever edition imported ``downloads`` first)."""
    ce_paths = _registered_paths(giljo_mode="", monkeypatch=monkeypatch)
    assert ce_paths >= _LOG_PATHS, f"CE build missing log routes: {sorted(_LOG_PATHS - ce_paths)}"

    saas_paths = _registered_paths(giljo_mode="saas", monkeypatch=monkeypatch)
    leaked = _LOG_PATHS & saas_paths
    assert not leaked, f"SaaS build exposed CE-only log routes: {sorted(leaked)}"


def test_ce_string_and_empty_both_include_log_routes(monkeypatch):
    """CE is represented by both "" (default/unset) and "ce"; both must expose
    the log routes."""
    assert _registered_paths(giljo_mode="", monkeypatch=monkeypatch) >= _LOG_PATHS
    assert _registered_paths(giljo_mode="ce", monkeypatch=monkeypatch) >= _LOG_PATHS


def test_log_router_defined_unconditionally_at_import():
    """Structural lock: the log routes live on ``downloads.log_router``, which is
    defined regardless of the edition ``downloads`` was imported in — that is
    what removes the import-order latch. If a future edit reintroduces a
    module-level GILJO_MODE gate around the router, this fails."""
    from api.endpoints import downloads

    assert hasattr(downloads, "log_router"), "downloads.log_router must be defined unconditionally"
    log_router_paths = {route.path for route in downloads.log_router.routes}
    assert log_router_paths >= _LOG_PATHS, f"log_router missing routes: {sorted(_LOG_PATHS - log_router_paths)}"
