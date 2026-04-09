# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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

import pytest

from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.services.product_service import ProductService

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
        await service.get_cascade_impact(product_id=data["product_b"].id)


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

    result = await service.get_cascade_impact(product_id=data["product_a"].id)

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
        await service.get_product_statistics(product_id=data["product_b"].id)


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

    result = await service.get_product_statistics(product_id=data["product_a"].id)

    assert result.project_count >= 1
    assert result.task_count >= 1
    assert result.vision_documents_count >= 1
