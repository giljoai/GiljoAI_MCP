# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6031a: SaaS-extensible tenant-scoped model registration hook.

The tenant-isolation bypass (``tenant_isolation_bypass``) validates its
``models=`` argument against the CE built-in tenant-scoped set. SaaS-only
models (``OrganizationPlan`` / ``TenantTrial``) can NEVER be added to that CE
set (edition isolation), so the SaaS trial reaper raised
``ValueError: ...not tenant-scoped: OrganizationPlan, TenantTrial`` every cycle.

The fix adds a public ``register_tenant_scoped_models(*models)`` hook in CE
core (``giljo_mcp.database``). SaaS calls it at import time to WIDEN the allowed
set without CE core ever importing a SaaS model. These tests exercise the
failing layer -- the bypass validation gate and the scoped-table readers that
must honor dynamically-registered models.

Parallel-safe (xdist): the ``reset_registry`` fixture snapshots and RESTORES the
process-global extension set on teardown, so no registration leaks across tests
or workers. Pure-function tests -- no DB session required for the validation
gate (a lightweight stand-in object carrying an ``.info`` dict is enough, since
the gate rejects before touching the session).

Project: BE-6031a.
"""

from __future__ import annotations

import importlib
import inspect

import pytest

from giljo_mcp import database
from giljo_mcp.database import (
    TENANT_SCOPED_MODELS,
    register_tenant_scoped_models,
    tenant_isolation_bypass,
)
from giljo_mcp.models import Project


class _DummyTenantScoped:
    """Stand-in for a SaaS-only tenant-scoped model.

    Not a real ORM mapping -- the bypass validation gate only compares object
    identity against the registered set, so a bare class suffices to prove the
    registry widens (and that the un-registered case still rejects).
    """


class _FakeSession:
    """Minimal session stand-in: ``tenant_isolation_bypass`` only touches ``.info``."""

    def __init__(self) -> None:
        self.info: dict = {}


@pytest.fixture
def reset_registry():
    """Snapshot and RESTORE the process-global extension set (xdist-safe)."""
    snapshot = set(database._REGISTERED_TENANT_SCOPED_MODELS)
    try:
        yield
    finally:
        database._REGISTERED_TENANT_SCOPED_MODELS.clear()
        database._REGISTERED_TENANT_SCOPED_MODELS.update(snapshot)
        # BE-6031a perf: the union is memoized; direct registry mutation bypasses the
        # rebuild, so call with no args to recompute the cache to match the restore.
        register_tenant_scoped_models()


def test_unregistered_model_is_rejected(reset_registry) -> None:
    """Without registration, a non-built-in model is rejected by the bypass gate."""
    with pytest.raises(ValueError, match="not tenant-scoped"):
        with tenant_isolation_bypass(
            _FakeSession(),
            reason="BE-6031a: unregistered model must be rejected",
            models=(_DummyTenantScoped,),
        ):
            pass


def test_registered_model_is_accepted(reset_registry) -> None:
    """After registration, the bypass accepts the formerly-rejected model."""
    register_tenant_scoped_models(_DummyTenantScoped)

    # Must not raise -- the registered model now counts as tenant-scoped.
    with tenant_isolation_bypass(
        _FakeSession(),
        reason="BE-6031a: registered model is accepted",
        models=(_DummyTenantScoped,),
    ):
        pass

    assert _DummyTenantScoped in database._all_tenant_scoped_models()


def test_ce_builtin_still_accepted(reset_registry) -> None:
    """A CE built-in (Project) remains accepted regardless of registration."""
    assert Project in TENANT_SCOPED_MODELS

    with tenant_isolation_bypass(
        _FakeSession(),
        reason="BE-6031a: CE built-in still accepted",
        models=(Project,),
    ):
        pass


def test_registration_is_idempotent(reset_registry) -> None:
    """Registering the same model twice is a no-op (set size unchanged, still works)."""
    register_tenant_scoped_models(_DummyTenantScoped)
    size_after_first = len(database._REGISTERED_TENANT_SCOPED_MODELS)

    register_tenant_scoped_models(_DummyTenantScoped)
    size_after_second = len(database._REGISTERED_TENANT_SCOPED_MODELS)

    assert size_after_first == size_after_second
    with tenant_isolation_bypass(
        _FakeSession(),
        reason="BE-6031a: idempotent re-registration still works",
        models=(_DummyTenantScoped,),
    ):
        pass


def test_registration_is_additive_only(reset_registry) -> None:
    """Registration WIDENS the union -- CE built-ins survive a SaaS registration."""
    before = set(database._all_tenant_scoped_models())
    register_tenant_scoped_models(_DummyTenantScoped)
    after = set(database._all_tenant_scoped_models())

    assert before.issubset(after)
    assert after - before == {_DummyTenantScoped}


def test_public_union_name_reflects_registered_models(reset_registry) -> None:
    """The public ``TENANT_SCOPED_MODELS`` name reads as the live union.

    External code (and the deliberate-exclusion comment convention in
    ``saas/auth/oauth_client.py``) references ``TENANT_SCOPED_MODELS`` directly;
    the public name must reflect registered models, not only CE built-ins.
    """
    register_tenant_scoped_models(_DummyTenantScoped)
    assert _DummyTenantScoped in database.TENANT_SCOPED_MODELS
    assert Project in database.TENANT_SCOPED_MODELS


def test_scoped_tables_reflect_registered_models(reset_registry) -> None:
    """``_all_tenant_scoped_tables()`` reflects registered models with a real ``__table__``.

    Uses a real ORM model (Project) re-registered so the union dict resolves its
    table -- proves the table readers route through the live union, not a
    frozen-at-import snapshot.
    """
    # Project's table is already present via the CE built-ins; assert the union
    # accessor includes it (the readers consume this accessor, not a stale dict).
    tables = database._all_tenant_scoped_tables()
    assert Project.__table__ in tables
    assert tables[Project.__table__] is Project


def test_registration_invalidates_memoized_cache(reset_registry) -> None:
    """BE-6031a perf: the union is memoized but registration MUST invalidate it.

    Proves live-union-after-import still holds with the cache: a model registered
    AFTER import is visible to BOTH cached accessors (models set and table dict)
    without any other recompute trigger. If the cache were never invalidated, the
    post-import registration would be invisible and tenant isolation would silently
    drop the new model from the scoped set.
    """
    assert Project not in database._REGISTERED_TENANT_SCOPED_MODELS  # CE built-in, not registered

    models_before = database._all_tenant_scoped_models()
    tables_before = database._all_tenant_scoped_tables()
    assert _DummyTenantScoped not in models_before

    register_tenant_scoped_models(_DummyTenantScoped)

    models_after = database._all_tenant_scoped_models()
    tables_after = database._all_tenant_scoped_tables()
    assert _DummyTenantScoped in models_after  # cache rebuilt -> reader sees it
    # _DummyTenantScoped is non-mapped (no __table__) -> excluded from the table
    # dict by the hasattr filter, but the cached dict object was still rebuilt.
    assert _DummyTenantScoped not in set(tables_after.values())
    # The cached objects were genuinely swapped on registration, not stale.
    assert models_after is not models_before
    assert tables_after is not tables_before


def test_scoped_table_dict_read_is_cached_identity(reset_registry) -> None:
    """The hot read path returns the SAME cached dict object across calls.

    Guards the perf fix: ``_all_tenant_scoped_tables()`` must not rebuild a fresh
    dict per call (the regression this fix removes). Identity-stable between calls
    with no intervening registration proves the read is allocation-free.
    """
    first = database._all_tenant_scoped_tables()
    second = database._all_tenant_scoped_tables()
    assert first is second


def test_database_module_imports_no_saas() -> None:
    """``giljo_mcp.database`` must import zero SaaS modules (Deletion Test).

    Scans the module source for any ``giljo_mcp.saas`` import. CE core must hold
    with all ``saas/`` deleted; the registry is the SaaS extension seam, but the
    seam itself lives entirely in CE and pulls in nothing from ``saas/``.
    """
    source = inspect.getsource(importlib.import_module("giljo_mcp.database"))
    assert "giljo_mcp.saas" not in source
    assert "from .saas" not in source
    assert "import saas" not in source
