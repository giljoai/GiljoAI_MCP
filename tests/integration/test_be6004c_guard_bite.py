# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE6004C-6 guard-bite lockdown: the fail-closed tenant guard still RAISES.

This is the re-arm regression for the whole chain. Every BE6004C slice wired a
specific code path to carry tenant context so it would STOP raising under the
fail-closed guard. This test asserts the inverse for the load-bearing safety
property: a tenant-scoped ORM statement with NO provable tenant context still
raises ``TenantIsolationError`` under enforce, for SELECT *and* UPDATE *and*
DELETE -- the three statement classes ``_enforce_tenant_scope`` governs.

If a future change ever silently weakens the guard back toward fail-open (the
multi-tenant isolation hole BE-6004 closed), this test fails loudly.

Failing layer = the real ``do_orm_execute`` event listener, exercised through a
real transactional Postgres session (not a mock). Runs under the default
``enforce`` guard mode (pinned explicitly so an ambient env value cannot mask
the assertion).

Parallel-safe: ``TransactionalTestContext`` (rolled back at teardown), a unique
``tk_...`` tenant, monkeypatch-scoped env, no module-level mutable state.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy import delete, select, update

from giljo_mcp.database import TenantIsolationError
from giljo_mcp.models.products import Product
from giljo_mcp.tenant import TenantManager
from tests.helpers.test_db_helper import TransactionalTestContext


def _product(tenant_key: str) -> Product:
    return Product(
        id=str(uuid4()),
        name=f"guard-bite {uuid4().hex[:8]}",
        description="BE6004C-6 guard-bite seed",
        tenant_key=tenant_key,
        product_memory={},
    )


def _strip_context(session) -> None:
    """Drop every tenant signal so the guard sees NO resolvable context."""
    session.info.pop("tenant_key", None)
    session.info.pop("tenant_key_source", None)
    TenantManager.clear_current_tenant()


@pytest.mark.parametrize("verb", ["select", "update", "delete"])
@pytest.mark.asyncio
async def test_contextless_tenant_scoped_statement_raises_under_enforce(db_manager, monkeypatch, verb):
    """A contextless SELECT/UPDATE/DELETE on a tenant-scoped model RAISES.

    Proves the guard still bites after the BE6004C re-arm: no ambient
    ContextVar, no session.info tenant, no bypass -> TenantIsolationError.
    """
    monkeypatch.setenv("GILJO_TENANT_GUARD_MODE", "enforce")
    tenant_key = TenantManager.generate_tenant_key()

    async with TransactionalTestContext(db_manager) as session:
        product = _product(tenant_key)
        session.add(product)
        await session.flush()
        # The seed flush records single-tenant context via after_flush; strip it
        # so we assert the genuinely-contextless baseline.
        _strip_context(session)

        if verb == "select":
            stmt = select(Product)
        elif verb == "update":
            stmt = update(Product).values(description="should not apply")
        else:
            stmt = delete(Product)

        with pytest.raises(TenantIsolationError):
            await session.execute(stmt)
