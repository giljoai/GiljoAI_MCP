# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Unit tests for ProductService product switching and project deactivation.

TDD (RED → GREEN → REFACTOR): Tests written FIRST following TDD discipline.

Issue: When switching products, active projects in the deactivated product remain active,
violating the non-negotiable "one active product → one active project" rule.

Expected Behavior:
- When Product A (with active Project X) is deactivated by activating Product B
- Project X should be set to status='inactive'
- WebSocket event 'projects:bulk:deactivated' should be emitted
"""

import random
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from giljo_mcp.exceptions import BaseGiljoError
from giljo_mcp.models import Product, Project
from giljo_mcp.services.product_service import ProductService
from tests.fixtures.base_fixtures import TestData


@pytest.mark.asyncio
async def test_activate_product_deactivates_projects_in_old_product(db_session, db_manager):
    """
    Test that activating a new product deactivates all projects in the old product.

    BEHAVIOR: When switching from Product A to Product B, all active projects
    in Product A should be set to status='inactive'.

    Test Steps:
    1. Create Product A with active Project X
    2. Create Product B (inactive)
    3. Activate Product B (which deactivates Product A)
    4. Verify Project X is now inactive

    This test should FAIL initially (RED ❌) because ProductService.activate_product()
    does not currently deactivate projects when deactivating products.
    """
    tenant_key = TestData.generate_tenant_key()

    # Step 1: Create Product A (active) with Project X (active)
    product_a = Product(
        id=str(uuid.uuid4()),
        name="Product A",
        description="First product",
        tenant_key=tenant_key,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_a)
    await db_session.flush()

    project_x = Project(
        id=str(uuid.uuid4()),
        name="Project X",
        description="Active project in Product A",
        mission="Test mission",
        tenant_key=tenant_key,
        product_id=product_a.id,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(project_x)
    await db_session.commit()

    # Step 2: Create Product B (inactive)
    product_b = Product(
        id=str(uuid.uuid4()),
        name="Product B",
        description="Second product",
        tenant_key=tenant_key,
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_b)
    await db_session.commit()

    # Step 3: Activate Product B using ProductService
    service = ProductService(db_manager, tenant_key=tenant_key, test_session=db_session)
    result = await service.activate_product(product_b.id)

    # Verify Product B is now active (0731b: returns Product ORM model)
    assert result.is_active is True

    # Refresh objects to get latest state
    await db_session.refresh(product_a)
    await db_session.refresh(product_b)
    await db_session.refresh(project_x)

    # Verify Product A is now inactive
    assert product_a.is_active is False

    # Step 4: CRITICAL ASSERTION - Project X should be inactive
    # This is the fix we're testing for
    assert project_x.status == "inactive", (
        f"Expected Project X to be deactivated when Product A was deactivated, but status is '{project_x.status}'"
    )


@pytest.mark.asyncio
async def test_product_switch_emits_websocket_events(db_session, db_manager):
    """
    Test that product switching emits WebSocket events for bulk project deactivation.

    BEHAVIOR: When switching products causes projects to be deactivated,
    a 'projects:bulk:deactivated' WebSocket event should be emitted.

    This test should FAIL initially (RED ❌) because the WebSocket event
    emission code doesn't exist yet.
    """
    tenant_key = TestData.generate_tenant_key()

    # Create Product A (active) with 2 active projects
    product_a = Product(
        id=str(uuid.uuid4()),
        name="Product A",
        description="First product",
        tenant_key=tenant_key,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_a)
    await db_session.flush()

    # Create two active projects in Product A
    project_1 = Project(
        id=str(uuid.uuid4()),
        name="Project 1",
        description="First project",
        mission="Test mission 1",
        tenant_key=tenant_key,
        product_id=product_a.id,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(project_1)

    project_2 = Project(
        id=str(uuid.uuid4()),
        name="Project 2",
        description="Second project",
        mission="Test mission 2",
        tenant_key=tenant_key,
        product_id=product_a.id,
        status="inactive",  # This one is already inactive
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(project_2)
    await db_session.commit()

    # Create Product B (inactive)
    product_b = Product(
        id=str(uuid.uuid4()),
        name="Product B",
        description="Second product",
        tenant_key=tenant_key,
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_b)
    await db_session.commit()

    # Create mock WebSocket manager
    mock_ws = MagicMock()
    mock_ws.broadcast_to_tenant = AsyncMock()

    # Activate Product B with mock WebSocket manager
    service = ProductService(
        db_manager,
        tenant_key=tenant_key,
        websocket_manager=mock_ws,  # Pass mock here
        test_session=db_session,
    )
    result = await service.activate_product(product_b.id)

    # 0731b: returns Product ORM model
    assert result.is_active is True

    # CRITICAL ASSERTION - WebSocket event should be emitted
    # This should FAIL initially because the code doesn't exist yet
    mock_ws.broadcast_to_tenant.assert_called_once()

    # Verify the event payload
    call_args = mock_ws.broadcast_to_tenant.call_args
    assert call_args.kwargs["tenant_key"] == tenant_key
    assert call_args.kwargs["event_type"] == "projects:bulk:deactivated"  # Fixed: event_type not event
    assert "product_ids" in call_args.kwargs["data"]
    assert str(product_a.id) in call_args.kwargs["data"]["product_ids"]


@pytest.mark.asyncio
async def test_product_switch_multi_tenant_isolation(db_session, db_manager):
    """
    Test that product switching with project deactivation respects multi-tenant isolation.

    BEHAVIOR: Switching products in tenant A should NOT affect projects in tenant B.
    """
    tenant_a = TestData.generate_tenant_key()
    tenant_b = TestData.generate_tenant_key()

    # Tenant A: Product A (active) with Project X (active)
    product_a = Product(
        id=str(uuid.uuid4()),
        name="Product A",
        tenant_key=tenant_a,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_a)
    await db_session.flush()

    project_x_tenant_a = Project(
        id=str(uuid.uuid4()),
        name="Project X",
        description="Project in Tenant A",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="active",
        mission="Test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(project_x_tenant_a)

    # Tenant A: Product B (inactive)
    product_b = Product(
        id=str(uuid.uuid4()),
        name="Product B",
        tenant_key=tenant_a,
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_b)

    # Tenant B: Product C (active) with Project Y (active)
    product_c = Product(
        id=str(uuid.uuid4()),
        name="Product C",
        tenant_key=tenant_b,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_c)
    await db_session.flush()

    project_y_tenant_b = Project(
        id=str(uuid.uuid4()),
        name="Project Y",
        description="Project in Tenant B",
        tenant_key=tenant_b,
        product_id=product_c.id,
        status="active",
        mission="Test",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(project_y_tenant_b)
    await db_session.commit()

    # Tenant A switches to Product B
    service_a = ProductService(db_manager, tenant_key=tenant_a, test_session=db_session)
    result = await service_a.activate_product(product_b.id)
    # 0731b: returns Product ORM model
    assert result.is_active is True

    # Refresh all projects
    await db_session.refresh(project_x_tenant_a)
    await db_session.refresh(project_y_tenant_b)

    # Verify: Tenant A's project is deactivated
    assert project_x_tenant_a.status == "inactive"

    # Verify: Tenant B's project is still active (multi-tenant isolation)
    assert project_y_tenant_b.status == "active", (
        "Tenant B's project should NOT be affected by Tenant A's product switch"
    )


@pytest.mark.asyncio
async def test_activate_product_does_not_emit_when_commit_fails(db_session, db_manager):
    """BE-3006c (named fix 1): projects:bulk:deactivated must NOT fire if the
    owner commit fails.

    The event previously emitted BEFORE the owner commit in
    ``ProductLifecycleService.activate_product``. If the commit then failed, the
    dashboard showed phantom "deactivated" state for rows that rolled back. The
    fix moves the emit to AFTER ``session.commit()``; this test forces the commit
    to raise and asserts the websocket broadcast is never called.

    Parallel-safe: unique tenant key, shared transactional ``db_session`` (rolled
    back at teardown); nothing is committed.
    """
    tenant_key = TestData.generate_tenant_key()

    # Product A (active) with one active project -> activation will deactivate it.
    product_a = Product(
        id=str(uuid.uuid4()),
        name="Product A",
        tenant_key=tenant_key,
        is_active=True,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_a)
    await db_session.flush()

    project_x = Project(
        id=str(uuid.uuid4()),
        name="Project X",
        description="Active project in Product A",
        mission="Test mission",
        tenant_key=tenant_key,
        product_id=product_a.id,
        status="active",
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        series_number=random.randint(1, 9000),
    )
    db_session.add(project_x)

    product_b = Product(
        id=str(uuid.uuid4()),
        name="Product B",
        tenant_key=tenant_key,
        is_active=False,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )
    db_session.add(product_b)
    await db_session.commit()

    mock_ws = MagicMock()
    mock_ws.broadcast_to_tenant = AsyncMock()
    service = ProductService(
        db_manager,
        tenant_key=tenant_key,
        websocket_manager=mock_ws,
        test_session=db_session,
    )

    # Force the owner commit (activate_product's explicit pre-emit commit) to fail.
    async def _boom():
        raise RuntimeError("commit boom")

    db_session.commit = _boom

    with pytest.raises(BaseGiljoError):
        await service.activate_product(product_b.id)

    # Phantom-state guard: no event may fire when the write never became durable.
    mock_ws.broadcast_to_tenant.assert_not_called()
