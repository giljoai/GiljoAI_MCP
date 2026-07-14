# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Flatten a FastAPI/Starlette route tree across fastapi 0.137's ``_IncludedRouter``.

**Edition Scope:** Both — test-only introspection helper (never shipped).

fastapi 0.137 (paired with starlette 1.3.x) changed how ``app.routes`` /
``router.routes`` represent included routers. Before, ``include_router()`` COPIED
each sub-route (prefix already baked into ``.path``) into the parent's flat
``.routes`` list. Now it appends ONE opaque ``_IncludedRouter`` — a
``starlette.routing.BaseRoute`` subclass with NO ``.path`` / ``.methods`` — whose
real routes are resolved lazily through its ``effective_candidates()`` method
(which combines the include prefix/tags/dependencies and yields
``_EffectiveRouteContext`` leaves, themselves possibly nested ``_IncludedRouter``).

Any test that iterates ``.routes`` expecting flat ``APIRoute`` objects must descend
through these wrappers, or it SILENTLY goes blind to every included sub-route — a
false green (the route is still served; the test just stops seeing it). That is the
exact breakage INF-6053 deferred and this module fixes.

``iter_effective_routes`` duck-types on the ``effective_candidates()`` method, so it
behaves identically on the old (flat) and new (nested) framework: a plain
``Route`` / ``APIRoute`` / ``WebSocketRoute`` / ``Mount`` has no such method and is
yielded as-is; an ``_IncludedRouter`` is expanded recursively. Each yielded leaf
exposes ``.path`` (full, prefix-combined), ``.methods``, and ``.dependant`` exactly
as the pre-0.137 flat list did — so callers reading those attributes (signature
snapshots, dependency-gate checks) need no further change.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any


def iter_effective_routes(routes: Iterable[Any]) -> Iterator[Any]:
    """Yield every leaf route, descending through fastapi 0.137 ``_IncludedRouter``.

    A leaf is any route object carrying a ``.path`` (a real ``APIRoute`` / ``Route``
    / ``WebSocketRoute`` / ``Mount`` on the old framework, or an
    ``_EffectiveRouteContext`` produced by an ``_IncludedRouter`` on the new one).
    Routers exposing ``effective_candidates()`` are expanded recursively; this is a
    no-op on a flat router, so the helper is safe to apply everywhere.
    """
    for route in routes:
        candidates = getattr(route, "effective_candidates", None)
        if callable(candidates):
            yield from iter_effective_routes(candidates())
        elif getattr(route, "path", None) is not None:
            yield route


def route_signatures(routes: Iterable[Any]) -> set[tuple[str, frozenset]]:
    """Build the ``(path, frozenset(methods))`` signature set over a route tree.

    Flattens ``_IncludedRouter`` wrappers first so the set equals the pre-0.137
    flat-``.routes`` signature set exactly.
    """
    return {
        (route.path, frozenset(getattr(route, "methods", None) or frozenset()))
        for route in iter_effective_routes(routes)
    }
