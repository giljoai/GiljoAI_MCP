# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Regression test for the 'chain' get_context category.

The CH_SUB_ORCHESTRATOR chapter prose (chapters_chain.py) has told sub-orchestrators
to "fetch the FULL chain mission via get_context" since BE-6196, but no category ever
served it -- CATEGORY_TOOLS had 12 entries, none chain-shaped, so the pointer was dead.
This test exercises the fix at the fetch_context dispatch layer: categories=["chain"]
resolves the caller's active SequenceRun by project_id (SequenceRunService.
find_active_run_for_project, tenant-scoped) and returns run_id/chain_mission/
resolved_order, with a clean empty result outside a chain.

Parallel-safety: DB-touching; uses the db_manager fixture directly (SequenceRunService
COMMITs through its own session, same as test_sequence_run_query_mixin.py) with a
function-scoped tenant-key collector that deletes only the rows this test created --
no module-level mutable state, no ordering dependency.
"""

from __future__ import annotations

import random
import uuid

import pytest
import pytest_asyncio
from sqlalchemy import delete

from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import Project
from giljo_mcp.models.sequence_runs import SequenceRun
from giljo_mcp.services.sequence_run_service import SequenceRunService
from giljo_mcp.tenant import TenantManager
from giljo_mcp.tools.context_tools.fetch_context import fetch_context
from giljo_mcp.tools.context_tools.get_chain_context import get_chain_context


pytestmark = pytest.mark.asyncio

_MODE = "claude_code_cli"


@pytest_asyncio.fixture
async def cleanup_tenants(db_manager):
    """Collect tenant_keys created by a test; delete their rows at teardown."""
    tenants: list[str] = []
    yield tenants
    for tk in tenants:
        async with db_manager.get_session_async(tenant_key=tk) as session:
            await session.execute(delete(AgentExecution).where(AgentExecution.tenant_key == tk))
            await session.execute(delete(AgentJob).where(AgentJob.tenant_key == tk))
            await session.execute(delete(SequenceRun).where(SequenceRun.tenant_key == tk))
            await session.execute(delete(Project).where(Project.tenant_key == tk))
            await session.execute(delete(Product).where(Product.tenant_key == tk))
            await session.commit()


async def _create_product(db_manager, tenant_key: str) -> str:
    product_id = str(uuid.uuid4())
    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        session.add(Product(id=product_id, tenant_key=tenant_key, name="Chain Context Test Product"))
        await session.commit()
    return product_id


async def _create_project(db_manager, tenant_key: str, product_id: str) -> str:
    project_id = str(uuid.uuid4())
    async with db_manager.get_session_async(tenant_key=tenant_key) as session:
        session.add(
            Project(
                id=project_id,
                product_id=product_id,
                name="Chain Context Test Project",
                description="chain context regression",
                mission="chain context regression mission",
                # "completed" avoids idx_project_single_active_per_product (only one
                # "active" project per product) -- the run's own project_statuses
                # tracks chain-member state independently of this column.
                status="completed",
                tenant_key=tenant_key,
                execution_mode=_MODE,
                series_number=random.randint(1, 9000),
            )
        )
        await session.commit()
    return project_id


async def test_chain_category_returns_live_chain_mission(db_manager, cleanup_tenants: list[str]) -> None:
    """categories=["chain"] resolves the caller's active run and returns the
    live chain mission, run_id, and resolved_order -- tenant-scoped."""
    tenant = TenantManager.generate_tenant_key()
    cleanup_tenants.append(tenant)

    product_id = await _create_product(db_manager, tenant)
    p1 = await _create_project(db_manager, tenant, product_id)
    p2 = await _create_project(db_manager, tenant, product_id)

    svc = SequenceRunService(db_manager=db_manager)
    run = await svc.create(
        project_ids=[p1, p2],
        resolved_order=[p1, p2],
        execution_mode=_MODE,
        status="pending",
        project_statuses={p1: "pending", p2: "pending"},
        tenant_key=tenant,
    )
    await svc.update(run_id=run["id"], tenant_key=tenant, chain_mission="### P_1 ...\n### P_2 ...")

    response = await fetch_context(
        product_id=product_id,
        tenant_key=tenant,
        project_id=p1,
        categories=["chain"],
        db_manager=db_manager,
    )

    assert "chain" in response["categories_returned"]
    assert "chain" not in response.get("categories_empty", [])
    assert response["data"]["chain"]["run_id"] == run["id"]
    assert response["data"]["chain"]["chain_mission"] == "### P_1 ...\n### P_2 ..."
    assert response["data"]["chain"]["resolved_order"] == [p1, p2]

    # Tenant isolation: a different tenant's identical project_id string cannot
    # leak this run's mission (belt-and-suspenders on top of find_active_run_for_project's
    # own tenant_key filter).
    other_tenant = TenantManager.generate_tenant_key()
    other_result = await get_chain_context(project_id=p1, tenant_key=other_tenant, db_manager=db_manager)
    assert other_result["data"] == {}
    assert other_result["metadata"]["error"] == "no_active_chain_run"


async def test_chain_category_no_active_run_returns_clean_error(db_manager, cleanup_tenants: list[str]) -> None:
    """A solo project (no active chain run) gets an empty, structured result --
    not an exception -- from both the tool and the fetch_context dispatch layer."""
    tenant = TenantManager.generate_tenant_key()
    cleanup_tenants.append(tenant)

    product_id = await _create_product(db_manager, tenant)
    solo_project = await _create_project(db_manager, tenant, product_id)

    direct = await get_chain_context(project_id=solo_project, tenant_key=tenant, db_manager=db_manager)
    assert direct["data"] == {}
    assert direct["metadata"]["error"] == "no_active_chain_run"

    response = await fetch_context(
        product_id=product_id,
        tenant_key=tenant,
        project_id=solo_project,
        categories=["chain"],
        db_manager=db_manager,
    )

    assert "chain" in response["categories_returned"]
    assert "chain" in response.get("categories_empty", [])
    assert response["data"]["chain"] == {}
