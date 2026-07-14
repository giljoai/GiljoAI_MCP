# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6208e: get_context/fetch_context resolves product_id from project_id.

A combined-chain sub-orchestrator is handed a project_id but no product_id, yet
its documented startup step calls get_context (which needs a product_id). When
product_id is absent/empty and a project_id is supplied, fetch_context resolves
the product server-side via the tenant-scoped ProjectRepository.get_by_id.

Security invariant (ADR-009): the resolution filters by tenant_key, so a
project_id belonging to another tenant must NOT resolve.
"""

from __future__ import annotations

import random
import uuid
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, patch

import pytest

from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.models import Project
from giljo_mcp.models.products import Product
from giljo_mcp.tools.context_tools.fetch_context import (
    _resolve_product_id_from_project,
    fetch_context,
)


class _SessionYieldingDBManager:
    """A db_manager stand-in whose get_session_async yields the test's
    transactional session, so the real ProjectRepository runs against the
    test-created (and rolled-back) rows on a single connection.

    The yielded session carries ``info["tenant_key"] = caller_tenant`` so the
    tenant guard sees the same caller-scoped context the production
    get_session_async installs — a cross-tenant query then simply matches no
    rows (returns None) rather than tripping the guard's explicit-predicate
    check, which is exactly the production behaviour we are asserting on."""

    def __init__(self, session, caller_tenant: str):
        self._session = session
        self._caller_tenant = caller_tenant

    def get_session_async(self):
        session = self._session
        session.info["tenant_key"] = self._caller_tenant

        @asynccontextmanager
        async def _cm():
            yield session

        return _cm()


async def _make_product(db_session, tenant_key: str) -> Product:
    product = Product(
        id=str(uuid.uuid4()),
        name="BE-6208e Product",
        description="resolution test product",
        tenant_key=tenant_key,
        is_active=True,
        product_memory={},
    )
    db_session.add(product)
    await db_session.commit()
    return product


async def _make_project(db_session, tenant_key: str, product_id: str) -> Project:
    project = Project(
        id=str(uuid.uuid4()),
        name="BE-6208e Project",
        description="resolution test project",
        mission="resolve my product",
        status="active",
        tenant_key=tenant_key,
        product_id=product_id,
        series_number=random.randint(1, 9000),
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest.mark.asyncio
async def test_resolve_helper_returns_product_for_same_tenant(db_session, test_tenant_key):
    """The tenant-scoped lookup returns the project's product_id."""
    product = await _make_product(db_session, test_tenant_key)
    project = await _make_project(db_session, test_tenant_key, product.id)

    fake_mgr = _SessionYieldingDBManager(db_session, test_tenant_key)
    resolved = await _resolve_product_id_from_project(project.id, test_tenant_key, fake_mgr)

    assert resolved == str(product.id)


@pytest.mark.asyncio
async def test_resolve_helper_blocks_cross_tenant(db_session, test_tenant_key):
    """A project_id from another tenant must NOT resolve — proves tenant scoping."""
    product = await _make_product(db_session, test_tenant_key)
    project = await _make_project(db_session, test_tenant_key, product.id)

    other_tenant = test_tenant_key + "_other"
    fake_mgr = _SessionYieldingDBManager(db_session, other_tenant)

    with pytest.raises(ResourceNotFoundError):
        await _resolve_product_id_from_project(project.id, other_tenant, fake_mgr)


@pytest.mark.asyncio
async def test_fetch_context_resolves_when_product_id_empty(db_session, test_tenant_key):
    """fetch_context with project_id and NO product_id resolves and returns context."""
    product = await _make_product(db_session, test_tenant_key)
    project = await _make_project(db_session, test_tenant_key, product.id)

    fake_mgr = _SessionYieldingDBManager(db_session, test_tenant_key)
    response = await fetch_context(
        product_id="",
        tenant_key=test_tenant_key,
        project_id=project.id,
        categories=["project"],
        db_manager=fake_mgr,
    )

    assert "errors" not in response, response.get("errors")
    assert "project" in response["categories_returned"]
    assert response["data"]["project"]["project_name"] == "BE-6208e Project"


@pytest.mark.asyncio
async def test_fetch_context_cross_tenant_does_not_resolve(db_session, test_tenant_key):
    """fetch_context with a foreign-tenant project_id raises (no silent context)."""
    product = await _make_product(db_session, test_tenant_key)
    project = await _make_project(db_session, test_tenant_key, product.id)

    fake_mgr = _SessionYieldingDBManager(db_session, test_tenant_key + "_other")
    with pytest.raises(ResourceNotFoundError):
        await fetch_context(
            product_id="",
            tenant_key=test_tenant_key + "_other",
            project_id=project.id,
            categories=["project"],
            db_manager=fake_mgr,
        )


@pytest.mark.asyncio
async def test_explicit_product_id_skips_resolution(db_session, test_tenant_key):
    """The explicit-product_id path (solo) never invokes the resolver — unchanged."""
    product = await _make_product(db_session, test_tenant_key)
    project = await _make_project(db_session, test_tenant_key, product.id)

    fake_mgr = _SessionYieldingDBManager(db_session, test_tenant_key)
    with patch(
        "giljo_mcp.tools.context_tools.fetch_context._resolve_product_id_from_project",
        new=AsyncMock(side_effect=AssertionError("resolver must not run when product_id is supplied")),
    ) as resolver:
        response = await fetch_context(
            product_id=str(product.id),
            tenant_key=test_tenant_key,
            project_id=project.id,
            categories=["project"],
            db_manager=fake_mgr,
        )

    resolver.assert_not_called()
    assert response["data"]["project"]["project_name"] == "BE-6208e Project"
