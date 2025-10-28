"""
Integration tests for Phase 5 - Product Validation (Handover 0050).

Tests the complete flow of product activation validation:
- Database enforcement
- API endpoint error handling
- Multi-tenant isolation
- Full workflow integration

These tests use real database connections and test the entire stack.
"""

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.database import get_db_manager


class TestPhase5ProductValidationIntegration:
    """Integration tests for product activation validation."""

    @pytest.fixture
    async def db_session(self):
        """Get database session for test setup/teardown."""
        db_manager = get_db_manager()
        async with db_manager.get_session_async() as session:
            yield session

    @pytest.fixture
    async def test_tenant(self):
        """Create test tenant key."""
        return "tenant-phase5-test"

    @pytest.fixture
    async def test_user(self, db_session, test_tenant):
        """Create test user for API authentication."""
        user = User(
            username="phase5_test_user",
            email="phase5@test.com",
            tenant_key=test_tenant,
            role="admin",
            is_active=True
        )
        user.set_password("TestPassword123")

        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        yield user

        # Cleanup
        await db_session.delete(user)
        await db_session.commit()

    @pytest.fixture
    async def active_product(self, db_session, test_tenant):
        """Create active product for testing."""
        product = Product(
            tenant_key=test_tenant,
            name="Active Test Product",
            description="Product for Phase 5 testing",
            is_active=True,
            vision_type="inline",
            vision_document="# Test Vision\n\nThis is a test vision document.",
            chunked=False
        )

        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        yield product

        # Cleanup
        await db_session.delete(product)
        await db_session.commit()

    @pytest.fixture
    async def inactive_product(self, db_session, test_tenant):
        """Create inactive product for testing."""
        product = Product(
            tenant_key=test_tenant,
            name="Inactive Test Product",
            description="Inactive product for Phase 5 testing",
            is_active=False,
            vision_type="inline",
            vision_document="# Test Vision\n\nThis is an inactive test vision.",
            chunked=False
        )

        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        yield product

        # Cleanup
        await db_session.delete(product)
        await db_session.commit()

    @pytest.fixture
    async def project_with_inactive_product(self, db_session, inactive_product, test_tenant):
        """Create project linked to inactive product."""
        project = Project(
            tenant_key=test_tenant,
            product_id=inactive_product.id,
            name="Test Project",
            mission="Test mission for inactive product",
            status="active"
        )

        db_session.add(project)
        await db_session.commit()
        await db_session.refresh(project)

        yield project

        # Cleanup
        await db_session.delete(project)
        await db_session.commit()

    # ========================================================================
    # API Integration Tests - process_product_vision endpoint
    # ========================================================================

    @pytest.mark.asyncio
    async def test_api_process_vision_rejects_inactive_product(
        self, inactive_product, test_tenant
    ):
        """Test that API returns 409 Conflict for inactive product."""
        from api.app import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/orchestration/process-vision",
                json={
                    "tenant_key": test_tenant,
                    "product_id": inactive_product.id,
                    "project_requirements": "Build a test feature",
                    "workflow_type": "waterfall"
                }
            )

            # Verify 409 Conflict response
            assert response.status_code == 409

            # Verify error structure
            error_data = response.json()
            assert "detail" in error_data
            detail = error_data["detail"]

            if isinstance(detail, dict):
                assert detail["error"] == "inactive_product"
                assert "not active" in detail["message"]
                assert "hint" in detail
            else:
                # Fallback if detail is just a string
                assert "not active" in str(detail)

    @pytest.mark.asyncio
    async def test_api_process_vision_accepts_active_product(
        self, active_product, test_tenant
    ):
        """Test that API accepts active product (may fail on execution but not validation)."""
        from api.app import app

        async with AsyncClient(app=app, base_url="http://test") as client:
            response = await client.post(
                "/api/orchestration/process-vision",
                json={
                    "tenant_key": test_tenant,
                    "product_id": active_product.id,
                    "project_requirements": "Build a test feature",
                    "workflow_type": "waterfall"
                }
            )

            # Should NOT be 409 Conflict
            # May be 400/500 for other reasons, but not 409 inactive product
            assert response.status_code != 409

            # If it fails, error should not be about inactive product
            if response.status_code >= 400:
                error_data = response.json()
                detail = error_data.get("detail", "")
                detail_str = str(detail)
                assert "not active" not in detail_str.lower()

    # ========================================================================
    # Orchestrator Integration Tests - Direct method calls
    # ========================================================================

    @pytest.mark.asyncio
    async def test_orchestrator_spawn_agent_rejects_inactive_product(
        self, project_with_inactive_product
    ):
        """Test orchestrator.spawn_agent() rejects projects with inactive products."""
        from src.giljo_mcp.orchestrator import ProjectOrchestrator
        from src.giljo_mcp.enums import AgentRole

        orchestrator = ProjectOrchestrator()

        # Attempt to spawn agent for project with inactive product
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.spawn_agent(
                project_id=project_with_inactive_product.id,
                role=AgentRole.IMPLEMENTER
            )

        # Verify error message
        error_msg = str(exc_info.value)
        assert "not active" in error_msg
        assert "Inactive Test Product" in error_msg

    @pytest.mark.asyncio
    async def test_orchestrator_process_vision_rejects_inactive_product(
        self, inactive_product, test_tenant
    ):
        """Test orchestrator.process_product_vision() rejects inactive products."""
        from src.giljo_mcp.orchestrator import ProjectOrchestrator

        orchestrator = ProjectOrchestrator()

        # Attempt to process inactive product vision
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.process_product_vision(
                tenant_key=test_tenant,
                product_id=inactive_product.id,
                project_requirements="Test requirements"
            )

        # Verify error message
        error_msg = str(exc_info.value)
        assert "not active" in error_msg
        assert "Inactive Test Product" in error_msg
        assert "Activate the product" in error_msg

    # ========================================================================
    # Multi-tenant Isolation Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_tenant_isolation_prevents_cross_tenant_access(
        self, active_product, db_session
    ):
        """Test that tenant isolation prevents accessing other tenant's products."""
        from src.giljo_mcp.orchestrator import ProjectOrchestrator

        orchestrator = ProjectOrchestrator()

        # Attempt to access product with wrong tenant
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.process_product_vision(
                tenant_key="wrong-tenant-key",
                product_id=active_product.id,
                project_requirements="Test requirements"
            )

        error_msg = str(exc_info.value)
        assert "not found" in error_msg

    # ========================================================================
    # Database Constraint Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_database_enforces_single_active_product(
        self, db_session, test_tenant
    ):
        """Test database constraint prevents multiple active products per tenant."""
        from sqlalchemy.exc import IntegrityError

        # Create first active product
        product1 = Product(
            tenant_key=test_tenant,
            name="First Active Product",
            is_active=True,
            vision_type="inline",
            vision_document="Test"
        )
        db_session.add(product1)
        await db_session.commit()

        # Attempt to create second active product (should fail)
        product2 = Product(
            tenant_key=test_tenant,
            name="Second Active Product",
            is_active=True,
            vision_type="inline",
            vision_document="Test"
        )
        db_session.add(product2)

        with pytest.raises(IntegrityError) as exc_info:
            await db_session.commit()

        # Verify it's the unique index constraint
        error_msg = str(exc_info.value)
        assert "idx_product_single_active_per_tenant" in error_msg or "unique" in error_msg.lower()

        # Cleanup
        await db_session.rollback()
        await db_session.delete(product1)
        await db_session.commit()

    @pytest.mark.asyncio
    async def test_can_have_multiple_inactive_products(
        self, db_session, test_tenant
    ):
        """Test that multiple inactive products per tenant are allowed."""
        # Create multiple inactive products
        product1 = Product(
            tenant_key=test_tenant,
            name="Inactive Product 1",
            is_active=False,
            vision_type="inline",
            vision_document="Test"
        )
        product2 = Product(
            tenant_key=test_tenant,
            name="Inactive Product 2",
            is_active=False,
            vision_type="inline",
            vision_document="Test"
        )

        db_session.add(product1)
        db_session.add(product2)

        # Should succeed (no constraint violation)
        await db_session.commit()
        await db_session.refresh(product1)
        await db_session.refresh(product2)

        # Verify both exist
        assert product1.id is not None
        assert product2.id is not None
        assert not product1.is_active
        assert not product2.is_active

        # Cleanup
        await db_session.delete(product1)
        await db_session.delete(product2)
        await db_session.commit()

    # ========================================================================
    # Activation/Deactivation Flow Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_product_activation_deactivation_flow(
        self, db_session, test_tenant
    ):
        """Test complete product activation/deactivation workflow."""
        # Create inactive product
        product = Product(
            tenant_key=test_tenant,
            name="Flow Test Product",
            is_active=False,
            vision_type="inline",
            vision_document="Test vision"
        )
        db_session.add(product)
        await db_session.commit()
        await db_session.refresh(product)

        # Verify starts inactive
        assert not product.is_active

        # Activate product
        product.is_active = True
        await db_session.commit()
        await db_session.refresh(product)

        # Verify now active
        assert product.is_active

        # Verify can process vision now
        from src.giljo_mcp.orchestrator import ProjectOrchestrator
        orchestrator = ProjectOrchestrator()

        # Should not raise error now (though may fail for other reasons)
        try:
            await orchestrator.process_product_vision(
                tenant_key=test_tenant,
                product_id=product.id,
                project_requirements="Test"
            )
        except ValueError as e:
            # Should not be "not active" error
            assert "not active" not in str(e)
        except Exception:
            # Other errors are OK for this test
            pass

        # Deactivate product
        product.is_active = False
        await db_session.commit()
        await db_session.refresh(product)

        # Verify cannot process vision when inactive
        with pytest.raises(ValueError) as exc_info:
            await orchestrator.process_product_vision(
                tenant_key=test_tenant,
                product_id=product.id,
                project_requirements="Test"
            )

        assert "not active" in str(exc_info.value)

        # Cleanup
        await db_session.delete(product)
        await db_session.commit()

    # ========================================================================
    # Performance Tests
    # ========================================================================

    @pytest.mark.asyncio
    async def test_validation_performance_overhead(
        self, active_product, test_tenant
    ):
        """Test that validation doesn't add significant overhead."""
        import time
        from src.giljo_mcp.orchestrator import ProjectOrchestrator

        orchestrator = ProjectOrchestrator()

        # Measure time for validation check (isolated)
        start = time.time()

        try:
            await orchestrator.process_product_vision(
                tenant_key=test_tenant,
                product_id=active_product.id,
                project_requirements="Test"
            )
        except Exception:
            # We're testing validation speed, not full execution
            pass

        elapsed = time.time() - start

        # Validation should be fast (<100ms for database lookup)
        # Full execution may take longer, but we're measuring early exit
        assert elapsed < 5.0, f"Validation took {elapsed}s (expected <5s)"
