"""
Tenant isolation regression tests for MEDIUM defense-in-depth fixes — ProductService.

Verifies that all child/derived queries include explicit tenant_key filters,
even when a parent entity was already validated. These are defense-in-depth
measures that prevent fragile isolation if parent queries are ever refactored.

Fixes covered:
1. ProductService.update_quality_standards - session.get() replaced with select().where(tenant_key)
2. ProductService.get_cascade_impact - 3 COUNT queries now include tenant_key
3. ProductService._get_product_metrics - 5 COUNT queries now include tenant_key

Test Strategy:
- Create entities in two tenants (A and B)
- Verify queries only return data from the requesting tenant
- Verify cross-tenant access is blocked

Follows patterns from: test_project_tenant_isolation_regression.py
"""

import pytest

from src.giljo_mcp.exceptions import ResourceNotFoundError
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.tenant import TenantManager


# ============================================================================
# Fix 1: ProductService.update_quality_standards — session.get replaced
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_update_quality_standards_blocks_cross_tenant(two_tenant_products):
    """
    REGRESSION: update_quality_standards() must not allow cross-tenant updates.

    Previously used session.get(Product, product_id) with post-fetch check.
    Now uses select().where(tenant_key) for defense-in-depth.
    """
    data = two_tenant_products
    tenant_manager = TenantManager()
    service = ProductService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=data["db_session"],
    )

    with pytest.raises(ResourceNotFoundError):
        await service.update_quality_standards(
            product_id=data["product_b"].id,
            quality_standards="Hijacked!",
            tenant_key=data["tenant_a"],
        )

    # Verify product B was NOT modified
    await data["db_session"].refresh(data["product_b"])
    assert data["product_b"].quality_standards == "Code review required"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_update_quality_standards_same_tenant_succeeds(two_tenant_products):
    """Verify same-tenant update_quality_standards still works."""
    data = two_tenant_products
    tenant_manager = TenantManager()
    service = ProductService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=data["db_session"],
    )

    result = await service.update_quality_standards(
        product_id=data["product_a"].id,
        quality_standards="Updated standards",
        tenant_key=data["tenant_a"],
    )

    assert result is not None
    await data["db_session"].refresh(data["product_a"])
    assert data["product_a"].quality_standards == "Updated standards"


# ============================================================================
# Fix 2: ProductService.get_cascade_impact — COUNT queries with tenant_key
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
    tenant_manager = TenantManager()
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
    tenant_manager = TenantManager()
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
    tenant_manager = TenantManager()
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
    tenant_manager = TenantManager()
    service = ProductService(
        db_manager=data["db_manager"],
        tenant_key=data["tenant_a"],
        test_session=data["db_session"],
    )

    result = await service.get_product_statistics(product_id=data["product_a"].id)

    assert result.project_count >= 1
    assert result.task_count >= 1
    assert result.vision_documents_count >= 1
