# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Tests for per-product taxonomy series numbering (commit 5ca1c43ff).

Verifies that the uq_project_taxonomy_active unique index is scoped per
product_id, so two products under the same tenant can independently have
BE-0001. Also verifies same-product uniqueness, cross-tenant isolation,
and subseries behaviour.
"""

from uuid import uuid4

import pytest

from giljo_mcp.exceptions import AlreadyExistsError
from giljo_mcp.models.products import Product
from giljo_mcp.models.projects import ProjectType
from giljo_mcp.services.project_service import ProjectService
from giljo_mcp.tenant import TenantManager


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
async def project_service(project_service_with_session):
    """Alias that keeps test code readable."""
    return project_service_with_session


async def _make_product(db_session, tenant_key: str) -> Product:
    """Helper: create a Product row directly in the DB.

    is_active=False to avoid violating idx_product_single_active_per_tenant
    (only one active product is allowed per tenant).  Series numbering is
    independent of is_active, so inactive products are fine for these tests.
    """
    product = Product(
        id=str(uuid4()),
        name=f"Product {uuid4().hex[:6]}",
        description="Test product",
        tenant_key=tenant_key,
        is_active=False,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


async def _make_project_type(db_session, tenant_key: str, label: str, abbreviation: str) -> ProjectType:
    """Helper: create a ProjectType row directly in the DB."""
    pt = ProjectType(
        id=str(uuid4()),
        tenant_key=tenant_key,
        label=label,
        abbreviation=abbreviation,
    )
    db_session.add(pt)
    await db_session.commit()
    await db_session.refresh(pt)
    return pt


# ---------------------------------------------------------------------------
# Scenario 1 — Per-product independence (the core fix)
# ---------------------------------------------------------------------------


class TestPerProductIndependence:
    """Two products under the same tenant start their own independent series."""

    @pytest.mark.asyncio
    async def test_two_products_same_tenant_both_get_series_1(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """Both products get series_number=1 for the same project type."""
        pt = await _make_project_type(db_session, test_tenant_key, "Backend", "BE")
        product_a = await _make_product(db_session, test_tenant_key)
        product_b = await _make_product(db_session, test_tenant_key)

        p_a = await project_service.create_project(
            name="BE Project A",
            mission="Backend work for product A",
            product_id=product_a.id,
            project_type_id=pt.id,
            tenant_key=test_tenant_key,
        )
        p_b = await project_service.create_project(
            name="BE Project B",
            mission="Backend work for product B",
            product_id=product_b.id,
            project_type_id=pt.id,
            tenant_key=test_tenant_key,
        )

        assert p_a.series_number == 1, f"Product A: expected 1, got {p_a.series_number}"
        assert p_b.series_number == 1, f"Product B: expected 1, got {p_b.series_number}"

    @pytest.mark.asyncio
    async def test_two_products_without_project_type_each_get_series_1(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """Products without a project_type_id also get independent numbering."""
        product_a = await _make_product(db_session, test_tenant_key)
        product_b = await _make_product(db_session, test_tenant_key)

        p_a = await project_service.create_project(
            name="Generic Project A",
            mission="Work for product A",
            product_id=product_a.id,
            tenant_key=test_tenant_key,
        )
        p_b = await project_service.create_project(
            name="Generic Project B",
            mission="Work for product B",
            product_id=product_b.id,
            tenant_key=test_tenant_key,
        )

        assert p_a.series_number == 1
        assert p_b.series_number == 1


# ---------------------------------------------------------------------------
# Scenario 2 — Same-product uniqueness preserved
# ---------------------------------------------------------------------------


class TestSameProductUniqueness:
    """Within a single product, series numbers are sequential and non-duplicatable."""

    @pytest.mark.asyncio
    async def test_same_product_auto_assigns_sequential_numbers(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """Two auto-assigned projects in the same product get 1 then 2."""
        pt = await _make_project_type(db_session, test_tenant_key, "Backend", "BE")
        product = await _make_product(db_session, test_tenant_key)

        p1 = await project_service.create_project(
            name="BE Project 1",
            mission="First backend project",
            product_id=product.id,
            project_type_id=pt.id,
            tenant_key=test_tenant_key,
        )
        p2 = await project_service.create_project(
            name="BE Project 2",
            mission="Second backend project",
            product_id=product.id,
            project_type_id=pt.id,
            tenant_key=test_tenant_key,
        )

        assert p1.series_number == 1
        assert p2.series_number == 2

    @pytest.mark.asyncio
    async def test_manual_duplicate_series_in_same_product_is_rejected(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """Explicitly supplying an already-used series_number in the same product raises AlreadyExistsError."""
        pt = await _make_project_type(db_session, test_tenant_key, "Backend", "BE")
        product = await _make_product(db_session, test_tenant_key)

        await project_service.create_project(
            name="BE-0001 First",
            mission="Occupies series 1",
            product_id=product.id,
            project_type_id=pt.id,
            series_number=1,
            tenant_key=test_tenant_key,
        )

        with pytest.raises(AlreadyExistsError):
            await project_service.create_project(
                name="BE-0001 Duplicate",
                mission="Should fail: same product, same type, same series",
                product_id=product.id,
                project_type_id=pt.id,
                series_number=1,
                tenant_key=test_tenant_key,
            )

    @pytest.mark.asyncio
    async def test_manual_duplicate_allowed_in_different_product(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """Same series_number is allowed in a different product under the same tenant."""
        pt = await _make_project_type(db_session, test_tenant_key, "Backend", "BE")
        product_a = await _make_product(db_session, test_tenant_key)
        product_b = await _make_product(db_session, test_tenant_key)

        p_a = await project_service.create_project(
            name="BE-0001 in Product A",
            mission="Occupies series 1 in product A",
            product_id=product_a.id,
            project_type_id=pt.id,
            series_number=1,
            tenant_key=test_tenant_key,
        )
        # Should NOT raise — different product_id
        p_b = await project_service.create_project(
            name="BE-0001 in Product B",
            mission="Series 1 is valid for product B",
            product_id=product_b.id,
            project_type_id=pt.id,
            series_number=1,
            tenant_key=test_tenant_key,
        )

        assert p_a.series_number == 1
        assert p_b.series_number == 1


# ---------------------------------------------------------------------------
# Scenario 3 — Cross-tenant isolation
# ---------------------------------------------------------------------------


class TestCrossTenantIsolation:
    """Projects in different tenants never interfere with each other's numbering."""

    @pytest.mark.asyncio
    async def test_different_tenants_get_independent_series_numbers(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """Tenant A and tenant B each get series_number=1 independently."""
        tenant_b = TenantManager.generate_tenant_key()

        # Project type and product for tenant A
        pt_a = await _make_project_type(db_session, test_tenant_key, "Backend", "BE")
        product_a = await _make_product(db_session, test_tenant_key)

        # Project type and product for tenant B
        pt_b = await _make_project_type(db_session, tenant_b, "Backend", "BE")
        product_b = await _make_product(db_session, tenant_b)

        p_a = await project_service.create_project(
            name="Tenant A BE Project",
            mission="Tenant A backend work",
            product_id=product_a.id,
            project_type_id=pt_a.id,
            tenant_key=test_tenant_key,
        )
        p_b = await project_service.create_project(
            name="Tenant B BE Project",
            mission="Tenant B backend work",
            product_id=product_b.id,
            project_type_id=pt_b.id,
            tenant_key=tenant_b,
        )

        assert p_a.series_number == 1
        assert p_b.series_number == 1

    @pytest.mark.asyncio
    async def test_tenant_a_data_invisible_to_tenant_b_series_count(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """Tenant A's projects do not inflate tenant B's auto-assigned series_number."""
        tenant_b = TenantManager.generate_tenant_key()

        # Create 3 projects for tenant A
        pt_a = await _make_project_type(db_session, test_tenant_key, "Backend", "BE")
        product_a = await _make_product(db_session, test_tenant_key)
        for i in range(3):
            await project_service.create_project(
                name=f"Tenant A Project {i}",
                mission="Tenant A work",
                product_id=product_a.id,
                project_type_id=pt_a.id,
                tenant_key=test_tenant_key,
            )

        # Tenant B starts fresh at 1 regardless of tenant A's count
        pt_b = await _make_project_type(db_session, tenant_b, "Backend", "BE")
        product_b = await _make_product(db_session, tenant_b)
        p_b = await project_service.create_project(
            name="Tenant B First Project",
            mission="Tenant B work",
            product_id=product_b.id,
            project_type_id=pt_b.id,
            tenant_key=tenant_b,
        )

        assert p_b.series_number == 1, f"Tenant B should start at 1 independently of tenant A. Got {p_b.series_number}"


# ---------------------------------------------------------------------------
# Scenario 4 — Subseries behaviour
# ---------------------------------------------------------------------------


class TestSubseriesBehaviour:
    """subseries field does not break the per-product unique index."""

    @pytest.mark.asyncio
    async def test_subseries_projects_in_different_products_coexist(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """BE-0001a in product A and BE-0001a in product B are valid simultaneously."""
        pt = await _make_project_type(db_session, test_tenant_key, "Backend", "BE")
        product_a = await _make_product(db_session, test_tenant_key)
        product_b = await _make_product(db_session, test_tenant_key)

        p_a = await project_service.create_project(
            name="BE-0001a in Product A",
            mission="Subseries a for product A",
            product_id=product_a.id,
            project_type_id=pt.id,
            series_number=1,
            subseries="a",
            tenant_key=test_tenant_key,
        )
        # Should not raise — different product_id
        p_b = await project_service.create_project(
            name="BE-0001a in Product B",
            mission="Subseries a for product B",
            product_id=product_b.id,
            project_type_id=pt.id,
            series_number=1,
            subseries="a",
            tenant_key=test_tenant_key,
        )

        assert p_a.series_number == 1
        assert p_a.subseries == "a"
        assert p_b.series_number == 1
        assert p_b.subseries == "a"

    @pytest.mark.asyncio
    async def test_subseries_duplicate_in_same_product_is_rejected(
        self,
        project_service: ProjectService,
        db_session,
        test_tenant_key: str,
    ):
        """BE-0001a used twice in the same product raises AlreadyExistsError."""
        pt = await _make_project_type(db_session, test_tenant_key, "Backend", "BE")
        product = await _make_product(db_session, test_tenant_key)

        await project_service.create_project(
            name="BE-0001a First",
            mission="Occupies 1a",
            product_id=product.id,
            project_type_id=pt.id,
            series_number=1,
            subseries="a",
            tenant_key=test_tenant_key,
        )

        with pytest.raises(AlreadyExistsError):
            await project_service.create_project(
                name="BE-0001a Duplicate",
                mission="Should fail: same product+type+series+subseries",
                product_id=product.id,
                project_type_id=pt.id,
                series_number=1,
                subseries="a",
                tenant_key=test_tenant_key,
            )
