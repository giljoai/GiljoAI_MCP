# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
SEC-0005c mode-gate regression suite -- "server-level endpoints are CE-only".

Source of truth for the endpoint inventory: handovers/SEC-0005c_sweep_taxonomy.md
(8 SERVER-LEVEL rows, all in api/endpoints/configuration.py).

For every row this suite asserts:

  (1) The route is registered at the expected method+path on the configuration
      router (catches accidental router demounts).

  (2) The route's FastAPI dependency chain includes ``require_ce_mode`` -- so
      that ``GILJO_MODE != "ce"`` causes a 404 *before* the handler runs. This
      uses the same dependency-walk technique as
      ``tests/services/test_sec0005a_verification.py``.

  (3) ``require_ce_mode()`` itself raises HTTPException 404 for every non-ce
      mode value (demo, saas, saas-production, anything other than the literal
      string "ce"). This is the behavioral assertion -- (2) only proves the
      dependency is wired; (3) proves the dependency does what the contract
      says.

The taxonomy assigns these 8 endpoints to the SERVER-LEVEL lane because they
read or mutate server-global state -- config.yaml, .env, PostgreSQL ALTER
USER, SSL certs on disk, the server-wide DB connection. They MUST NOT be
exposed to admins of their own tenant in demo or SaaS deployments.
"""

from __future__ import annotations

from collections.abc import Iterable
from unittest.mock import patch

import pytest
from fastapi import HTTPException


# ---------------------------------------------------------------------------
# Helpers (kept local to avoid cross-test imports)
# ---------------------------------------------------------------------------


def _walk_dependants(dependant) -> Iterable:
    stack = [dependant]
    while stack:
        node = stack.pop()
        yield node
        stack.extend(getattr(node, "dependencies", []) or [])


def _route_has_dependency(route, target_callable) -> bool:
    dependant = getattr(route, "dependant", None)
    if dependant is None:
        return False
    return any(getattr(node, "call", None) is target_callable for node in _walk_dependants(dependant))


def _find_route(router, method: str, path_suffix: str):
    """
    Locate a route by method + path suffix. Prefers an exact-path match (so
    suffix "/database" returns the route at "/database" and not "/health/database").
    Falls back to suffix match only when no exact match exists.
    """
    exact, suffixed = [], []
    for route in router.routes:
        route_path = getattr(route, "path", "")
        route_methods = set(getattr(route, "methods", set()) or set())
        if method.upper() not in route_methods:
            continue
        if route_path == path_suffix:
            exact.append(route)
        elif route_path.endswith(path_suffix):
            suffixed.append(route)
    matches = exact or suffixed
    if not matches:
        raise AssertionError(
            f"No configuration route ending in {path_suffix!r} with method "
            f"{method!r}. The sweep taxonomy is out of date."
        )
    if len(matches) > 1:
        raise AssertionError(
            f"Ambiguous route lookup for {method} {path_suffix!r}: "
            f"{[r.path for r in matches]}. Tighten the suffix in the inventory."
        )
    return matches[0]


# ---------------------------------------------------------------------------
# Endpoint inventory (lane-b / SERVER-LEVEL rows from SEC-0005c_sweep_taxonomy.md)
# ---------------------------------------------------------------------------
#
# Each row: (mount_prefix, method, path_suffix, taxonomy_reason)
#
# All 8 lane-(b) endpoints live in api/endpoints/configuration.py and are
# mounted under /api/v1/config (api/app.py:489).

_CE_MODE_INVENTORY: list[tuple[str, str, str, str]] = [
    ("/api/v1/config", "PUT", "/key/{key_path}", "mutates in-memory state.config (config.yaml)"),
    ("/api/v1/config", "PATCH", "/", "bulk mutates in-memory state.config"),
    ("/api/v1/config", "POST", "/reload", "reloads config.yaml from disk"),
    ("/api/v1/config", "GET", "/database", "reads .env DB_HOST/PORT/USER/NAME/PASSWORD"),
    ("/api/v1/config", "POST", "/database/password", "ALTER USER on PostgreSQL + writes .env DB_PASSWORD"),
    ("/api/v1/config", "GET", "/ssl", "reads server-global SSL paths on disk"),
    ("/api/v1/config", "POST", "/ssl", "generates server-global SSL certs + writes config.yaml"),
    ("/api/v1/config", "GET", "/health/database", "pings server-global DB connection"),
]


def _import_configuration_router():
    from api.endpoints import configuration

    return configuration.router


# ---------------------------------------------------------------------------
# (1) + (2): Each lane-(b) route is registered AND wires require_ce_mode
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("mount_prefix", "method", "path_suffix", "reason"),
    _CE_MODE_INVENTORY,
    ids=[f"{method} {mount_prefix}{suffix}" for (mount_prefix, method, suffix, _r) in _CE_MODE_INVENTORY],
)
def test_server_level_endpoint_depends_on_require_ce_mode(
    mount_prefix: str, method: str, path_suffix: str, reason: str
):
    """
    Every lane-(b) endpoint must have ``require_ce_mode`` in its dependency
    chain. If this assertion fires, a server-level configuration endpoint is
    reachable in demo/SaaS mode and the two-orthogonal-axes invariant is
    broken.
    """
    from giljo_mcp.auth.dependencies import require_ce_mode

    router = _import_configuration_router()
    route = _find_route(router, method, path_suffix)

    full = mount_prefix.rstrip("/") + route.path
    assert _route_has_dependency(route, require_ce_mode), (
        f"{method} {full} is SERVER-LEVEL ({reason}) but its dependency chain "
        "does NOT include require_ce_mode. This endpoint is reachable in "
        "demo/SaaS modes -- a violation of the two-orthogonal-axes invariant. "
        "Add ``_ce: None = Depends(require_ce_mode)`` to the handler signature."
    )


# ---------------------------------------------------------------------------
# (3) require_ce_mode behavior: raises 404 for every non-ce mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mode_value",
    ["demo", "saas", "saas-production", "saas-staging", "production", "", "CE"],
    ids=lambda v: f"mode={v!r}",
)
async def test_require_ce_mode_raises_404_when_not_ce(mode_value: str):
    """
    ``require_ce_mode`` must 404 for ANY value other than the literal string
    "ce". The "CE" case (uppercase) is included to catch a future bug where
    mode comparison becomes case-insensitive -- the contract is exact match.
    """
    from giljo_mcp.auth.dependencies import require_ce_mode

    with patch("api.app_state.GILJO_MODE", mode_value), pytest.raises(HTTPException) as exc:
        await require_ce_mode()
    assert exc.value.status_code == 404, (
        f"require_ce_mode() returned status {exc.value.status_code} for mode "
        f"{mode_value!r}; expected 404 to hide route existence in non-CE modes."
    )


@pytest.mark.asyncio
async def test_require_ce_mode_passes_when_ce():
    """In CE mode the dependency must resolve cleanly (return None)."""
    from giljo_mcp.auth.dependencies import require_ce_mode

    with patch("api.app_state.GILJO_MODE", "ce"):
        result = await require_ce_mode()
    assert result is None


# ---------------------------------------------------------------------------
# Negative: tenant-scoped configuration endpoints must NOT be CE-gated
# ---------------------------------------------------------------------------
#
# Defense against a future refactor that "helpfully" slaps require_ce_mode on
# every configuration route. /tenant CRUD is lane-(a) -- it must remain
# reachable in demo and SaaS so admins can manage their own tenant config.


@pytest.mark.parametrize(
    ("method", "path_suffix"),
    [
        ("GET", "/tenant"),
        ("PUT", "/tenant"),
        ("DELETE", "/tenant"),
        ("GET", "/frontend"),
    ],
    ids=str,
)
def test_tenant_scoped_configuration_endpoint_is_not_ce_gated(method: str, path_suffix: str):
    """Lane-(a) configuration endpoints stay reachable in all modes."""
    from giljo_mcp.auth.dependencies import require_ce_mode

    router = _import_configuration_router()
    route = _find_route(router, method, path_suffix)
    assert not _route_has_dependency(route, require_ce_mode), (
        f"{method} /api/v1/config{path_suffix} is tenant-scoped (lane-(a)) and "
        "MUST NOT depend on require_ce_mode -- doing so breaks demo/SaaS admins."
    )
