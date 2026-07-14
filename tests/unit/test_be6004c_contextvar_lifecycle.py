# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
BE6004C-1: ContextVar lifecycle correctness for TenantManager.

The fail-closed tenant guard (BE-6004) makes a lingering tenant value on a
reused worker task a latent cross-tenant leak. This slice makes every set
paired with a proper reset, so the ContextVar always returns to its exact
prior value — even across nesting and exceptions.

Verifies:
- set_current_tenant returns a contextvars.Token usable for reset().
- Nested with_tenant / TenantContext unwinds A->B->exit->A->exit->None exactly.
- An exception inside a with_tenant block still restores the prior value.
- A simulated request cycle (set + reset via the returned token) leaves the
  ContextVar exactly as it found it, with no residue on the worker.
- clear_current_tenant() remains a bare hard-clear to None.

Parallel-safe: pure ContextVar contract, no DB, no module-global mutation,
each test sets up and tears down its own tenant state; no test-ordering deps.
xdist workers are separate processes, so the module-level `current_tenant`
ContextVar is not shared across workers.
"""

from contextvars import Token

import pytest

from giljo_mcp.tenant import (
    TenantManager,
    clear_current_tenant,
    current_tenant,
    get_current_tenant,
    set_current_tenant,
    with_tenant,
)


def _key() -> str:
    return TenantManager.generate_tenant_key()


@pytest.fixture(autouse=True)
def _clean_tenant_context():
    """Snapshot the ContextVar before each test and restore it after.

    Guarantees no residue leaks out of a test even if an assertion fails
    mid-flight, so tests remain independent under xdist.
    """
    token = current_tenant.set(None)
    try:
        yield
    finally:
        current_tenant.reset(token)


def test_set_current_tenant_returns_usable_token():
    """set_current_tenant must return a contextvars.Token for later reset()."""
    key = _key()
    token = TenantManager.set_current_tenant(key)
    try:
        assert isinstance(token, Token)
        assert TenantManager.get_current_tenant() == key
    finally:
        current_tenant.reset(token)
    assert TenantManager.get_current_tenant() is None


def test_reset_with_token_restores_prior_value():
    """Resetting with the returned token restores the exact prior value."""
    outer = _key()
    outer_token = TenantManager.set_current_tenant(outer)
    inner = _key()
    inner_token = TenantManager.set_current_tenant(inner)

    assert TenantManager.get_current_tenant() == inner
    current_tenant.reset(inner_token)
    assert TenantManager.get_current_tenant() == outer
    current_tenant.reset(outer_token)
    assert TenantManager.get_current_tenant() is None


def test_clear_current_tenant_is_bare_hard_clear():
    """clear_current_tenant() takes no args and forces the context to None.

    Exercises the module-level convenience function (added in BE6004C-1) and
    the classmethod; both must hard-clear to None.
    """
    set_current_tenant(_key())
    assert get_current_tenant() is not None
    clear_current_tenant()
    assert get_current_tenant() is None

    TenantManager.set_current_tenant(_key())
    assert TenantManager.get_current_tenant() is not None
    TenantManager.clear_current_tenant()
    assert TenantManager.get_current_tenant() is None


def test_nested_with_tenant_unwinds_to_exact_prior_value():
    """A -> B -> exit B -> A -> exit A -> None (classmethod context manager)."""
    tenant_a = _key()
    tenant_b = _key()

    assert TenantManager.get_current_tenant() is None
    with TenantManager.with_tenant(tenant_a):
        assert TenantManager.get_current_tenant() == tenant_a
        with TenantManager.with_tenant(tenant_b):
            assert TenantManager.get_current_tenant() == tenant_b
        assert TenantManager.get_current_tenant() == tenant_a
    assert TenantManager.get_current_tenant() is None


def test_nested_with_tenant_convenience_function_unwinds():
    """Module-level with_tenant() convenience function unwinds identically."""
    tenant_a = _key()
    tenant_b = _key()

    with with_tenant(tenant_a):
        assert get_current_tenant() == tenant_a
        with with_tenant(tenant_b):
            assert get_current_tenant() == tenant_b
        assert get_current_tenant() == tenant_a
    assert get_current_tenant() is None


def test_with_tenant_restores_after_exception():
    """An exception inside a with_tenant block still restores the prior value."""
    tenant_a = _key()
    tenant_b = _key()

    def raise_inside_context() -> None:
        with TenantManager.with_tenant(tenant_b):
            assert TenantManager.get_current_tenant() == tenant_b
            raise RuntimeError("boom inside tenant context")

    set_current_tenant(tenant_a)
    try:
        with pytest.raises(RuntimeError):
            raise_inside_context()
        assert TenantManager.get_current_tenant() == tenant_a
    finally:
        TenantManager.clear_current_tenant()
    assert TenantManager.get_current_tenant() is None


def test_with_tenant_restores_none_when_no_prior_context():
    """Entering with_tenant from a None baseline returns to None on exit."""
    assert TenantManager.get_current_tenant() is None
    with TenantManager.with_tenant(_key()):
        assert TenantManager.get_current_tenant() is not None
    assert TenantManager.get_current_tenant() is None


def test_simulated_request_cycle_leaves_no_residue():
    """Mirror the AuthMiddleware contract: capture token at entry, reset in
    finally. On a (simulated) reused worker the ContextVar returns to its
    pre-request value (None) so no later request can observe this tenant."""
    assert get_current_tenant() is None

    def handle_request(tenant_key: str) -> None:
        token = set_current_tenant(tenant_key)
        try:
            assert get_current_tenant() == tenant_key
        finally:
            current_tenant.reset(token)

    handle_request(_key())
    assert get_current_tenant() is None, "tenant leaked onto the worker after request"

    handle_request(_key())
    assert get_current_tenant() is None, "tenant leaked onto the worker after second request"


def test_simulated_request_cycle_resets_even_on_exception():
    """If the request handler raises after set, the finally-reset still fires
    and the worker is left clean (None) for the next request."""
    assert get_current_tenant() is None
    key = _key()

    def failing_request() -> None:
        token = set_current_tenant(key)
        try:
            raise RuntimeError("handler exploded")
        finally:
            current_tenant.reset(token)

    with pytest.raises(RuntimeError):
        failing_request()
    assert get_current_tenant() is None, "exception path left tenant residue on the worker"


def test_invalid_tenant_key_rejected_before_set():
    """An invalid key still raises ValueError and never mutates the context."""
    assert get_current_tenant() is None
    with pytest.raises(ValueError):
        set_current_tenant("not-a-valid-tenant-key")
    assert get_current_tenant() is None
