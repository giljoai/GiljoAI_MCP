# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""CacheBackend abstraction for multi-worker-safe ephemeral state (INF-5074).

Two OAuth services (`oauth_token_idempotency`, `oauth_refresh_service`)
previously stored a few-seconds idempotency window in module-level Python
dicts. That is correct under a single uvicorn worker but silently broken
under `--workers > 1`: Worker A writes the entry, Worker B has no memory
of it, and a concurrent retry either rotates twice or trips
reuse-detection and revokes the refresh-token family.

This module is the CE-side abstraction that fixes the bug:

* `CacheBackend` — async Protocol with the minimal surface the OAuth flows
  need (`get`, `set`, `setnx`, `delete`). String values; structured
  payloads are JSON-encoded by callers.
* `InProcessDictBackend` — default implementation backed by a per-instance
  dict. Single-worker safe; documents and enforces the boundary that CE
  default deployments stay on a single worker.
* Module-level registry — `register_cache_backend(name, backend)` swaps
  the default at runtime. SaaS imports its Redis adapter at startup and
  registers under the same logical names the services request.

Tenant isolation is part of the contract: every method takes
`tenant_key` separately from `key` so backend implementations build a
namespaced, tenant-scoped storage key (`oauth:<feature>:{tenant}:{key}`)
that cannot collide across tenants even if a tool layer forgets to
prefix.

Why a Protocol and not an abstract base class: the SaaS Redis adapter
must register itself without CE knowing it exists (Deletion Test). A
runtime-checkable Protocol gives us the typing without requiring
inheritance.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable


logger = logging.getLogger(__name__)


OAUTH_IDEMPOTENCY_BACKEND_NAME = "oauth_idempotency"
OAUTH_REFRESH_BACKEND_NAME = "oauth_refresh"

# Pre-auth IP rate limiter (BE-6063f). Lives here (not in api/middleware) so the
# SaaS Redis adapter can register a shared backend under this name without an
# api/ -> saas/ import. The auth_rate_limiter module re-exports it for back-compat.
AUTH_RATE_LIMIT_BACKEND_NAME = "auth_rate_limiter"

# Global per-IP rate limiter (INF-3009d). Same decoupling rationale as the
# auth limiter above: the CE middleware requests this name, and SaaS startup
# swaps in the shared Redis backend so multi-worker deployments enforce ONE
# combined limit with TTL-evicted counters (the old per-process dict both
# multiplied the limit by worker count and leaked one entry per IP forever).
GLOBAL_RATE_LIMIT_BACKEND_NAME = "global_rate_limiter"

# Per-tenant license/trial-state cache (INF-3009d). The SaaS license cache in
# giljo_mcp/saas/licensing/cache.py requests this name; SaaS startup registers
# the Redis backend under it so an invalidation on one worker is visible to all
# workers. CE never requests this name at runtime (the cache is SaaS-only).
LICENSE_CACHE_BACKEND_NAME = "license_cache"


@runtime_checkable
class CacheBackend(Protocol):
    """Minimal async cache surface for OAuth idempotency-window state.

    All four methods take `tenant_key` as a first-class argument so the
    backend can build a tenant-scoped storage key without relying on
    callers to prefix correctly. The same logical `key` under two
    different `tenant_key` values MUST resolve to two distinct entries.
    """

    async def get(self, tenant_key: str, key: str) -> str | None:
        """Return the stored value for `(tenant_key, key)`, or None on miss/expired."""
        ...

    async def set(self, tenant_key: str, key: str, value: str, *, ttl_seconds: int) -> None:
        """Store `value` under `(tenant_key, key)` with `ttl_seconds` expiry.

        Overwrites any existing entry. Use `setnx` for first-write-wins
        semantics.
        """
        ...

    async def setnx(self, tenant_key: str, key: str, value: str, *, ttl_seconds: int) -> bool:
        """Set only if the key does not already exist.

        Returns True if the value was set (the caller "won" the race),
        False if an existing non-expired entry was already present.
        """
        ...

    async def delete(self, tenant_key: str, key: str) -> None:
        """Remove the entry for `(tenant_key, key)`. No-op on miss."""
        ...

    async def incr(self, tenant_key: str, key: str, *, ttl_seconds: int) -> int:
        """Atomically increment the integer counter at `(tenant_key, key)`.

        Returns the post-increment value. On first creation (return value 1)
        the entry is given a `ttl_seconds` expiry; later increments within that
        window leave the expiry untouched, giving fixed-window semantics. Unlike
        a `get()`+`set()` pair this is a SINGLE atomic step — concurrent callers
        each observe a distinct, monotonically increasing count with no
        read-modify-write race. This is the primitive the pre-auth IP rate
        limiter needs to enforce ONE combined limit across workers (BE-6006);
        the Redis adapter implements it as a server-side Lua INCR+EXPIRE.
        """
        ...


@dataclass(slots=True)
class _DictEntry:
    value: str
    expires_at: datetime


@dataclass
class InProcessDictBackend:
    """Single-process dict-backed `CacheBackend` (CE default).

    Each instance owns its own dict, so distinct logical caches (e.g.,
    `oauth_idempotency` and `oauth_refresh`) stay isolated. Tenant
    scoping is enforced by building the storage key as
    `f"{namespace}:{tenant_key}:{key}"`.

    This is the regression target the multi-worker bug exists to flag:
    two `InProcessDictBackend` instances DO NOT share state, which is the
    correct CE behavior (single worker) but the wrong SaaS behavior
    (multiple workers). The Redis adapter in SaaS shares state across
    instances via the Redis server.
    """

    namespace: str
    max_entries: int = 1000
    _store: dict[str, _DictEntry] = field(default_factory=dict, init=False, repr=False)

    def _storage_key(self, tenant_key: str, key: str) -> str:
        return f"{self.namespace}:{tenant_key}:{key}"

    def _evict_if_full(self, target_key: str) -> None:
        if len(self._store) < self.max_entries or target_key in self._store:
            return
        oldest_key = min(self._store, key=lambda k: self._store[k].expires_at)
        self._store.pop(oldest_key, None)

    async def get(self, tenant_key: str, key: str) -> str | None:
        storage_key = self._storage_key(tenant_key, key)
        entry = self._store.get(storage_key)
        if entry is None:
            return None
        if entry.expires_at <= datetime.now(UTC):
            self._store.pop(storage_key, None)
            return None
        return entry.value

    async def set(self, tenant_key: str, key: str, value: str, *, ttl_seconds: int) -> None:
        storage_key = self._storage_key(tenant_key, key)
        self._evict_if_full(storage_key)
        self._store[storage_key] = _DictEntry(
            value=value,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )

    async def setnx(self, tenant_key: str, key: str, value: str, *, ttl_seconds: int) -> bool:
        storage_key = self._storage_key(tenant_key, key)
        existing = self._store.get(storage_key)
        if existing is not None and existing.expires_at > datetime.now(UTC):
            return False
        self._evict_if_full(storage_key)
        self._store[storage_key] = _DictEntry(
            value=value,
            expires_at=datetime.now(UTC) + timedelta(seconds=ttl_seconds),
        )
        return True

    async def delete(self, tenant_key: str, key: str) -> None:
        self._store.pop(self._storage_key(tenant_key, key), None)

    async def incr(self, tenant_key: str, key: str, *, ttl_seconds: int) -> int:
        storage_key = self._storage_key(tenant_key, key)
        now = datetime.now(UTC)
        entry = self._store.get(storage_key)
        current = 0
        if entry is not None and entry.expires_at > now:
            try:
                current = int(entry.value)
            except (TypeError, ValueError):
                current = 0  # corrupt value -> treat as a fresh window
        if current == 0:
            # First write in this window (or expired/corrupt): start at 1 and
            # set the expiry. No await between the read above and this write, so
            # the increment is atomic within the single-process event loop.
            self._evict_if_full(storage_key)
            self._store[storage_key] = _DictEntry(
                value="1",
                expires_at=now + timedelta(seconds=ttl_seconds),
            )
            return 1
        # Subsequent write: bump the count, keep the original window expiry.
        count = current + 1
        entry.value = str(count)
        return count


_registry: dict[str, CacheBackend] = {}


def register_cache_backend(name: str, backend: CacheBackend) -> None:
    """Register `backend` under `name`, replacing any prior registration.

    SaaS calls this on import to override the CE default
    `InProcessDictBackend` with the Redis-backed adapter. CE never calls
    this — the default-factory path in `get_cache_backend` is sufficient.
    """
    _registry[name] = backend
    logger.info("cache_backend_registered name=%s impl=%s", name, type(backend).__name__)


def get_cache_backend(name: str) -> CacheBackend:
    """Return the registered backend for `name`, creating a CE default on first miss.

    The default-factory is `InProcessDictBackend(namespace=name)`. This
    means CE consumers do not need to register anything — the first
    call lazily creates a per-namespace dict-backed cache.
    """
    backend = _registry.get(name)
    if backend is None:
        backend = InProcessDictBackend(namespace=name)
        _registry[name] = backend
        logger.debug("cache_backend_default_created name=%s", name)
    return backend


def reset_registry_for_tests() -> None:
    """Test-only escape hatch: drop all registered backends.

    Production code MUST NOT call this. Tests use it to undo a SaaS
    registration so the next `get_cache_backend(name)` rebuilds a fresh
    CE default.
    """
    _registry.clear()
