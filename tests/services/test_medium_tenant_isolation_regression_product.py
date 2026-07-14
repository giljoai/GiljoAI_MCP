# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Tenant isolation regression tests for MEDIUM defense-in-depth fixes — ProductService.

Verifies that all child/derived queries include explicit tenant_key filters,
even when a parent entity was already validated. These are defense-in-depth
measures that prevent fragile isolation if parent queries are ever refactored.

Fixes covered:
1. ProductService.get_cascade_impact - 3 COUNT queries now include tenant_key
2. ProductService._get_product_metrics - 5 COUNT queries now include tenant_key

Test Strategy:
- Create entities in two tenants (A and B)
- Verify queries only return data from the requesting tenant
- Verify cross-tenant access is blocked

Follows patterns from: test_project_tenant_isolation_regression.py
"""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.exceptions import ResourceNotFoundError
from giljo_mcp.models import AgentJob, Product, Project
from giljo_mcp.services.product_lifecycle_service import ProductLifecycleService
from giljo_mcp.services.product_service import ProductService


# ============================================================================
# Fix 1: ProductService.get_cascade_impact — COUNT queries with tenant_key
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_cascade_impact_blocks_cross_tenant(two_tenant_products):
    """
    REGRESSION: get_cascade_impact() must not count entities from other tenants.

    Previously, COUNT queries for projects/tasks/vision docs filtered by
    product_id only. Now includes tenant_key for defense-in-depth.
    """
    data = two_tenant_products
    service = ProductService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=data["db_session"],
    )

    with pytest.raises(ResourceNotFoundError):
        await service.memory.get_cascade_impact(product_id=data["product_b"].id)


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_cascade_impact_same_tenant_counts_correctly(two_tenant_products):
    """Verify same-tenant cascade impact returns correct counts."""
    data = two_tenant_products
    service = ProductService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=data["db_session"],
    )

    result = await service.memory.get_cascade_impact(product_id=data["product_a"].id)

    assert result.total_projects >= 1
    assert result.total_tasks >= 1
    assert result.total_vision_documents >= 1


# ============================================================================
# Fix 3: ProductService._get_product_metrics — COUNT queries with tenant_key
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_product_statistics_blocks_cross_tenant(two_tenant_products):
    """
    REGRESSION: get_product_statistics() -> _get_product_metrics() must not
    count entities from other tenants.

    _get_product_metrics has 5 COUNT queries that previously filtered by
    product_id only. Now includes tenant_key.
    """
    data = two_tenant_products
    service = ProductService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=data["db_session"],
    )

    with pytest.raises(ResourceNotFoundError):
        await service.memory.get_product_statistics(product_id=data["product_b"].id)


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_product_statistics_same_tenant_counts_correctly(two_tenant_products):
    """Verify same-tenant product statistics returns correct counts."""
    data = two_tenant_products
    service = ProductService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=data["db_session"],
    )

    result = await service.memory.get_product_statistics(product_id=data["product_a"].id)

    assert result.project_count >= 1
    assert result.task_count >= 1
    assert result.vision_documents_count >= 1


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_deactivate_product_cascade_filters_project_and_job_tenant(db_session, two_tenant_products):
    """Product deactivation cascades only to rows in the product owner's tenant."""
    data = two_tenant_products
    data["project_a"].status = ProjectStatus.INACTIVE
    foreign_project = Project(
        id=str(uuid4()),
        name="Tenant B Stray Project",
        description="Foreign tenant row sharing tenant A product_id",
        mission="Tenant B mission",
        tenant_key=data["tenant_b"],
        product_id=data["product_a"].id,
        status=ProjectStatus.ACTIVE,
        series_number=987001,
    )
    foreign_job = AgentJob(
        job_id=str(uuid4()),
        job_type="tester",
        tenant_key=data["tenant_b"],
        project_id=foreign_project.id,
        mission="Foreign tenant job",
        status="active",
        created_at=datetime.now(UTC),
    )
    db_session.add_all([foreign_project, foreign_job])
    await db_session.commit()

    service = ProductLifecycleService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=db_session,
    )

    await service.deactivate_product(data["product_a"].id)

    await db_session.refresh(data["project_a"])
    await db_session.refresh(data["job_a"])
    await db_session.refresh(foreign_project)
    await db_session.refresh(foreign_job)

    assert data["project_a"].status == ProjectStatus.INACTIVE
    assert data["job_a"].status == "cancelled"
    assert foreign_project.status == ProjectStatus.ACTIVE
    assert foreign_job.status == "active"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_activate_product_bulk_cascade_filters_project_and_job_tenant(db_session, two_tenant_products):
    """Product activation bulk cascades only to rows in the current tenant."""
    data = two_tenant_products
    data["project_a"].status = ProjectStatus.INACTIVE
    new_product = Product(
        id=str(uuid4()),
        name="Tenant A New Product",
        description="Replacement active product",
        tenant_key=data["tenant_a"],
        is_active=False,
    )
    foreign_project = Project(
        id=str(uuid4()),
        name="Tenant B Stray Project For Bulk",
        description="Foreign tenant row sharing tenant A product_id",
        mission="Tenant B mission",
        tenant_key=data["tenant_b"],
        product_id=data["product_a"].id,
        status=ProjectStatus.ACTIVE,
        series_number=987002,
    )
    foreign_job = AgentJob(
        job_id=str(uuid4()),
        job_type="tester",
        tenant_key=data["tenant_b"],
        project_id=foreign_project.id,
        mission="Foreign tenant job",
        status="active",
        created_at=datetime.now(UTC),
    )
    db_session.add_all([new_product, foreign_project, foreign_job])
    await db_session.commit()

    service = ProductLifecycleService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=db_session,
    )

    await service.activate_product(new_product.id)

    await db_session.refresh(data["project_a"])
    await db_session.refresh(data["job_a"])
    await db_session.refresh(foreign_project)
    await db_session.refresh(foreign_job)

    assert data["project_a"].status == ProjectStatus.INACTIVE
    assert data["job_a"].status == "cancelled"
    assert foreign_project.status == ProjectStatus.ACTIVE
    assert foreign_job.status == "active"
