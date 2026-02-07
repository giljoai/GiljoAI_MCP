"""
Integration tests for ProductService.update_quality_standards (Handover 0316 Phase 5)

These tests use real database connections to verify:
- Quality standards field updates correctly
- Multi-tenant isolation enforced
- Database persistence verified
- WebSocket events emitted (if configured)
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.services.product_service import ProductService


@pytest.mark.asyncio
@pytest.mark.integration
class TestQualityStandardsIntegration:
    """Integration tests for quality_standards field updates"""

    async def test_update_quality_standards_full_workflow(self, db_manager):
        """Test update_quality_standards with real database"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key=tenant_key)

        # Create product
        create_result = await service.create_product(
            name="Test Product", description="Test product for quality standards"
        )
        assert create_result["success"] is True
        product_id = create_result["product_id"]

        # Update quality_standards
        update_result = await service.update_quality_standards(
            product_id=product_id, quality_standards="80% coverage, TDD required, zero P0 bugs", tenant_key=tenant_key
        )

        # Verify result
        assert update_result["product_id"] == product_id
        assert update_result["quality_standards"] == "80% coverage, TDD required, zero P0 bugs"

        # Verify database persistence - fetch product again
        get_result = await service.get_product(product_id)
        assert get_result["success"] is True
        assert get_result["product"]["quality_standards"] == "80% coverage, TDD required, zero P0 bugs"

    async def test_update_quality_standards_multi_tenant_isolation(self, db_manager):
        """Test that tenant cannot update another tenant's product quality_standards"""
        tenant1_key = str(uuid4())
        tenant2_key = str(uuid4())

        service1 = ProductService(db_manager, tenant1_key)
        service2 = ProductService(db_manager, tenant2_key)

        # Create product in tenant1
        create_result = await service1.create_product(name="Tenant1 Product")
        product_id = create_result["product_id"]

        # Try to update quality_standards from tenant2 - should fail
        with pytest.raises(ValueError, match="Product .* not found"):
            await service2.update_quality_standards(
                product_id=product_id, quality_standards="Hacked standards", tenant_key=tenant2_key
            )

        # Verify quality_standards unchanged (still None)
        get_result = await service1.get_product(product_id)
        assert get_result["product"]["quality_standards"] is None

    async def test_update_quality_standards_replaces_existing_value(self, db_manager):
        """Test that update_quality_standards can update existing quality_standards"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key=tenant_key)

        # Create product
        create_result = await service.create_product(name="Test Product")
        product_id = create_result["product_id"]

        # Set initial quality_standards
        await service.update_quality_standards(
            product_id=product_id, quality_standards="Initial: 70% coverage", tenant_key=tenant_key
        )

        # Update quality_standards with new value
        update_result = await service.update_quality_standards(
            product_id=product_id, quality_standards="Updated: 90% coverage, TDD required", tenant_key=tenant_key
        )

        # Verify new value
        assert update_result["quality_standards"] == "Updated: 90% coverage, TDD required"

        # Verify persistence
        get_result = await service.get_product(product_id)
        assert get_result["product"]["quality_standards"] == "Updated: 90% coverage, TDD required"

    async def test_update_quality_standards_nonexistent_product(self, db_manager):
        """Test that update_quality_standards handles missing product"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key=tenant_key)

        # Try to update quality_standards for nonexistent product
        nonexistent_id = str(uuid4())
        with pytest.raises(ValueError, match="Product .* not found"):
            await service.update_quality_standards(
                product_id=nonexistent_id, quality_standards="Standards", tenant_key=tenant_key
            )

    async def test_update_quality_standards_empty_string(self, db_manager):
        """Test that update_quality_standards accepts empty string"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key=tenant_key)

        # Create product with quality_standards
        create_result = await service.create_product(name="Test Product")
        product_id = create_result["product_id"]

        await service.update_quality_standards(
            product_id=product_id, quality_standards="Initial standards", tenant_key=tenant_key
        )

        # Clear quality_standards with empty string
        update_result = await service.update_quality_standards(
            product_id=product_id, quality_standards="", tenant_key=tenant_key
        )

        # Verify empty string stored
        assert update_result["quality_standards"] == ""

        get_result = await service.get_product(product_id)
        assert get_result["product"]["quality_standards"] == ""

    async def test_update_quality_standards_long_text(self, db_manager):
        """Test that update_quality_standards handles long text"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key=tenant_key)

        create_result = await service.create_product(name="Test Product")
        product_id = create_result["product_id"]

        # Create long quality standards text
        long_standards = """
        Quality Standards for Production Code:

        1. Testing Requirements:
           - Unit test coverage: 85% minimum
           - Integration test coverage: 70% minimum
           - E2E test coverage for critical workflows
           - All tests must pass before merge

        2. Code Quality:
           - Zero P0 bugs in production
           - Maximum 3 P1 bugs per release
           - Code review required for all changes
           - Linting and formatting enforced via pre-commit hooks

        3. Performance:
           - API response time <200ms for 95th percentile
           - Database queries optimized (no N+1 queries)
           - Frontend bundle size <500KB

        4. Security:
           - No hardcoded secrets or credentials
           - All user inputs validated
           - SQL injection protection
           - XSS protection in frontend

        5. Documentation:
           - All public APIs documented
           - README updated for major features
           - Migration guides for breaking changes
        """

        update_result = await service.update_quality_standards(
            product_id=product_id, quality_standards=long_standards, tenant_key=tenant_key
        )

        # Verify long text stored
        assert update_result["quality_standards"] == long_standards

        get_result = await service.get_product(product_id)
        assert get_result["product"]["quality_standards"] == long_standards
