"""
Integration tests for ProductService (Handover 0603)

These tests use real database connections to verify:
- Multi-tenant isolation (zero cross-tenant leakage)
- Database transactions and rollback
- Single active product constraint (database-level)
- Product-project cascade behavior
- Vision document integration
- Full CRUD workflows

Target: Comprehensive integration coverage
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.models.products import Product, VisionDocument
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.product_service import ProductService


@pytest.mark.asyncio
class TestMultiTenantIsolation:
    """Integration tests for multi-tenant isolation"""

    async def test_create_product_tenant_isolation(self, db_manager):
        """Test that products are isolated by tenant"""
        tenant1_key = str(uuid4())
        tenant2_key = str(uuid4())

        service1 = ProductService(db_manager, tenant1_key)
        service2 = ProductService(db_manager, tenant2_key)

        # Create products in different tenants (exception-based: success is implicit)
        result1 = await service1.create_product(name="Tenant1 Product", description="Product for tenant 1")
        result2 = await service2.create_product(name="Tenant2 Product", description="Product for tenant 2")

        # Verify creation returned expected data
        assert "product_id" in result1
        assert "product_id" in result2

        # Verify tenant1 can only see their product
        list1 = await service1.list_products(include_inactive=True)
        assert len(list1["products"]) == 1
        assert list1["products"][0]["name"] == "Tenant1 Product"

        # Verify tenant2 can only see their product
        list2 = await service2.list_products(include_inactive=True)
        assert len(list2["products"]) == 1
        assert list2["products"][0]["name"] == "Tenant2 Product"

    async def test_get_product_cross_tenant_forbidden(self, db_manager):
        """Test that tenant cannot access another tenant's product"""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        tenant1_key = str(uuid4())
        tenant2_key = str(uuid4())

        service1 = ProductService(db_manager, tenant1_key)
        service2 = ProductService(db_manager, tenant2_key)

        # Create product in tenant1
        create_result = await service1.create_product(name="Tenant1 Secret Product")
        product_id = create_result["product_id"]

        # Try to access from tenant2 - should raise exception
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service2.get_product(product_id)
        assert "not found" in str(exc_info.value).lower()

    async def test_update_product_cross_tenant_forbidden(self, db_manager):
        """Test that tenant cannot update another tenant's product"""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        tenant1_key = str(uuid4())
        tenant2_key = str(uuid4())

        service1 = ProductService(db_manager, tenant1_key)
        service2 = ProductService(db_manager, tenant2_key)

        create_result = await service1.create_product(name="Protected Product")
        product_id = create_result["product_id"]

        # Try to update from tenant2 - should raise exception
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service2.update_product(product_id=product_id, name="Hacked Name")
        assert "not found" in str(exc_info.value).lower()

        # Verify name unchanged
        get_result = await service1.get_product(product_id)
        assert get_result["product"]["name"] == "Protected Product"

    async def test_delete_product_cross_tenant_forbidden(self, db_manager):
        """Test that tenant cannot delete another tenant's product"""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        tenant1_key = str(uuid4())
        tenant2_key = str(uuid4())

        service1 = ProductService(db_manager, tenant1_key)
        service2 = ProductService(db_manager, tenant2_key)

        create_result = await service1.create_product(name="Protected Product")
        product_id = create_result["product_id"]

        # Try to delete from tenant2 - should raise exception
        with pytest.raises(ResourceNotFoundError):
            await service2.delete_product(product_id)

        # Verify product still exists in tenant1 (exception-based: success is implicit)
        get_result = await service1.get_product(product_id)
        assert get_result["product"]["name"] == "Protected Product"

    async def test_activate_product_tenant_isolation(self, db_manager):
        """Test that activating product in one tenant doesn't affect others"""
        tenant1_key = str(uuid4())
        tenant2_key = str(uuid4())

        service1 = ProductService(db_manager, tenant1_key)
        service2 = ProductService(db_manager, tenant2_key)

        # Create products in both tenants
        create1 = await service1.create_product(name="Tenant1 Product A")
        create2 = await service1.create_product(name="Tenant1 Product B")
        create3 = await service2.create_product(name="Tenant2 Product")

        # Activate products in both tenants
        await service1.activate_product(create1["product_id"])
        await service2.activate_product(create3["product_id"])

        # Verify tenant1 has one active product
        active1 = await service1.get_active_product()
        assert active1["product"]["name"] == "Tenant1 Product A"

        # Verify tenant2 has one active product
        active2 = await service2.get_active_product()
        assert active2["product"]["name"] == "Tenant2 Product"

        # Activate second product in tenant1
        activate_result = await service1.activate_product(create2["product_id"])
        assert activate_result["deactivated_count"] == 1

        # Verify tenant2 product still active (not affected)
        active2_check = await service2.get_active_product()
        assert active2_check["product"]["name"] == "Tenant2 Product"


@pytest.mark.asyncio
class TestSingleActiveProductConstraint:
    """Integration tests for single active product enforcement"""

    async def test_only_one_product_active_per_tenant(self, db_manager):
        """Test database enforces only one active product per tenant"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create three products
        create1 = await service.create_product(name="Product A")
        create2 = await service.create_product(name="Product B")
        create3 = await service.create_product(name="Product C")

        # Activate first product (exception-based: success is implicit)
        activate1 = await service.activate_product(create1["product_id"])
        assert activate1["product"]["is_active"] is True

        # Verify only one active
        active = await service.get_active_product()
        assert active["product"]["name"] == "Product A"

        # Activate second product
        activate2 = await service.activate_product(create2["product_id"])
        assert activate2["product"]["is_active"] is True
        assert activate2["deactivated_count"] == 1

        # Verify only Product B is active
        active = await service.get_active_product()
        assert active["product"]["name"] == "Product B"

        # Verify Product A is deactivated
        get_a = await service.get_product(create1["product_id"])
        assert get_a["product"]["is_active"] is False

        # Activate third product
        activate3 = await service.activate_product(create3["product_id"])
        assert activate3["product"]["is_active"] is True
        assert activate3["deactivated_count"] == 1

        # Verify only Product C is active
        active = await service.get_active_product()
        assert active["product"]["name"] == "Product C"

    async def test_activate_already_active_product(self, db_manager):
        """Test activating an already active product is idempotent"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        create_result = await service.create_product(name="Single Product")
        product_id = create_result["product_id"]

        # Activate once (exception-based: success is implicit)
        activate1 = await service.activate_product(product_id)
        assert activate1["product"]["is_active"] is True

        # Activate again
        activate2 = await service.activate_product(product_id)
        assert activate2["product"]["is_active"] is True
        assert activate2["deactivated_count"] == 0

    async def test_deactivate_product_no_active_product(self, db_manager):
        """Test that deactivating leaves no active product"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        create_result = await service.create_product(name="Temporary Active")
        product_id = create_result["product_id"]

        # Activate then deactivate (exception-based: success is implicit)
        await service.activate_product(product_id)
        deactivate_result = await service.deactivate_product(product_id)
        assert deactivate_result["product"]["is_active"] is False

        # Verify no active product
        active = await service.get_active_product()
        assert active["product"] is None


@pytest.mark.asyncio
class TestProductCRUDWorkflows:
    """Integration tests for complete CRUD workflows"""

    async def test_full_product_lifecycle(self, db_manager):
        """Test complete product lifecycle: create → update → activate → deactivate → delete → restore"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # 1. Create product (exception-based: success is implicit)
        create_result = await service.create_product(
            name="Lifecycle Product",
            description="Testing full lifecycle",
            project_path="/projects/lifecycle",
            config_data={"version": "1.0"},
        )
        assert "product_id" in create_result
        product_id = create_result["product_id"]

        # 2. Update product
        update_result = await service.update_product(
            product_id=product_id,
            description="Updated description",
            config_data={"version": "2.0", "feature": "enabled"},
        )
        assert update_result["product"]["description"] == "Updated description"

        # 3. Activate product
        activate_result = await service.activate_product(product_id)
        assert activate_result["product"]["is_active"] is True

        # 4. Deactivate product
        deactivate_result = await service.deactivate_product(product_id)
        assert deactivate_result["product"]["is_active"] is False

        # 5. Soft delete product
        delete_result = await service.delete_product(product_id)
        assert "deleted_at" in delete_result

        # Verify not in regular list (even with include_inactive)
        list_result = await service.list_products(include_inactive=True)
        assert len(list_result["products"]) == 0

        # Verify in deleted list
        deleted_list = await service.list_deleted_products()
        assert len(deleted_list["products"]) >= 1
        assert any(p["id"] == product_id for p in deleted_list["products"])

        # 6. Restore product (exception-based: success is implicit)
        restore_result = await service.restore_product(product_id)
        assert "product" in restore_result

        # Verify back in regular list
        list_result = await service.list_products(include_inactive=True)
        assert len(list_result["products"]) == 1
        assert list_result["products"][0]["name"] == "Lifecycle Product"

    async def test_create_multiple_products_and_list(self, db_manager):
        """Test creating multiple products and listing them"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create five products (exception-based: success is implicit)
        products = []
        for i in range(5):
            result = await service.create_product(name=f"Product {i + 1}", description=f"Description {i + 1}")
            assert "product_id" in result
            products.append(result["product_id"])

        # List all products (including inactive since new products start inactive)
        list_result = await service.list_products(include_inactive=True)
        assert "products" in list_result
        assert len(list_result["products"]) == 5

        # Verify all names present
        names = [p["name"] for p in list_result["products"]]
        for i in range(5):
            assert f"Product {i + 1}" in names

    async def test_duplicate_name_prevention(self, db_manager):
        """Test that duplicate product names are prevented"""
        from src.giljo_mcp.exceptions import ValidationError

        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create first product (exception-based: success is implicit)
        create1 = await service.create_product(name="Unique Product")
        assert "product_id" in create1

        # Try to create second with same name - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await service.create_product(name="Unique Product")
        assert "already exists" in str(exc_info.value)

        # Verify only one product exists
        list_result = await service.list_products(include_inactive=True)
        assert len(list_result["products"]) == 1

    async def test_soft_delete_allows_name_reuse(self, db_manager):
        """Test that soft-deleted products allow name reuse"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product (exception-based: success is implicit)
        create1 = await service.create_product(name="Reusable Name")
        assert "product_id" in create1
        product1_id = create1["product_id"]

        # Soft delete
        await service.delete_product(product1_id)

        # Create new product with same name - should succeed
        create2 = await service.create_product(name="Reusable Name")
        assert "product_id" in create2
        assert create2["product_id"] != product1_id


@pytest.mark.asyncio
class TestProductProjectCascade:
    """Integration tests for product-project relationships"""

    async def test_product_with_projects_cascade_impact(self, db_manager):
        """Test getting cascade impact shows related projects"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product
        product_result = await service.create_product(name="Product with Projects")
        product_id = product_result["product_id"]

        # Create related projects
        async with db_manager.get_session_async() as session:
            for i in range(3):
                project = Project(
                    id=str(uuid4()),
                    name=f"Project {i + 1}",
                    description=f"Project {i + 1} description",
                    mission=f"Mission {i + 1}",
                    status="waiting",
                    product_id=product_id,
                    tenant_key=tenant_key,
                )
                session.add(project)
            await session.commit()

        # Get cascade impact (exception-based: success is implicit)
        impact_result = await service.get_cascade_impact(product_id)
        assert "impact" in impact_result
        assert impact_result["impact"]["total_projects"] == 3

    async def test_delete_product_with_projects(self, db_manager):
        """Test deleting product with related projects"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product
        product_result = await service.create_product(name="Product to Delete")
        product_id = product_result["product_id"]

        # Create related project
        async with db_manager.get_session_async() as session:
            project = Project(
                id=str(uuid4()),
                name="Related Project",
                description="Project description",
                mission="Project mission",
                status="waiting",
                product_id=product_id,
                tenant_key=tenant_key,
            )
            session.add(project)
            await session.commit()

        # Delete product (soft delete) - exception-based: success is implicit
        delete_result = await service.delete_product(product_id)
        assert "deleted_at" in delete_result

        # Verify product is soft-deleted (should raise ResourceNotFoundError)
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError):
            await service.get_product(product_id)

        # Note: Actual cascade behavior depends on database constraints
        # This test verifies the delete succeeds


@pytest.mark.asyncio
class TestProductStatisticsIntegration:
    """Integration tests for product statistics and metrics"""

    async def test_get_product_statistics_with_data(self, db_manager):
        """Test statistics calculation with real data"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product
        product_result = await service.create_product(name="Stats Product")
        product_id = product_result["product_id"]

        # Get statistics (exception-based: success is implicit)
        stats_result = await service.get_product_statistics(product_id)
        assert "statistics" in stats_result
        assert "project_count" in stats_result["statistics"]
        assert "vision_documents_count" in stats_result["statistics"]  # Plural form
        assert stats_result["statistics"]["product_id"] == product_id

    async def test_get_product_with_metrics_flag(self, db_manager):
        """Test get_product with include_statistics flag"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        product_result = await service.create_product(name="Metrics Product")
        product_id = product_result["product_id"]

        # Get with metrics (exception-based: success is implicit)
        get_result = await service.get_product(product_id, include_metrics=True)
        # Should include product and potentially metric fields
        assert "product" in get_result

    async def test_list_products_with_metrics(self, db_manager):
        """Test list_products with metrics included"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create products
        await service.create_product(name="Product A")
        await service.create_product(name="Product B")

        # List with metrics and include inactive (new products start inactive)
        list_result = await service.list_products(include_inactive=True, include_metrics=True)
        assert "products" in list_result
        assert len(list_result["products"]) == 2

        # Products should include metric information
        for product in list_result["products"]:
            assert "id" in product
            assert "name" in product


@pytest.mark.asyncio
class TestConfigDataPersistence:
    """Integration tests for config_data field persistence"""

    async def test_config_data_survives_updates(self, db_manager):
        """Test that config_data persists correctly through updates"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product with config_data
        initial_config = {"api_key": "test-key-123", "settings": {"debug": True, "timeout": 30}}
        create_result = await service.create_product(name="Config Test Product", config_data=initial_config)
        product_id = create_result["product_id"]

        # Update product (without changing config_data)
        await service.update_product(product_id=product_id, description="Updated description")

        # Verify config_data preserved
        get_result = await service.get_product(product_id)
        assert get_result["product"]["config_data"]["api_key"] == "test-key-123"
        assert get_result["product"]["config_data"]["settings"]["debug"] is True

    async def test_config_data_update_merging(self, db_manager):
        """Test updating config_data merges correctly"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product with initial config
        create_result = await service.create_product(
            name="Config Merge Product", config_data={"field1": "value1", "field2": "value2"}
        )
        product_id = create_result["product_id"]

        # Update with new config_data (exception-based: success is implicit)
        new_config = {"field2": "updated", "field3": "new"}
        update_result = await service.update_product(product_id=product_id, config_data=new_config)
        assert "product" in update_result

        # Verify config updated
        get_result = await service.get_product(product_id)
        config = get_result["product"]["config_data"]
        assert config["field2"] == "updated"
        assert config["field3"] == "new"


@pytest.mark.asyncio
class TestVisionDocumentIntegration:
    """Integration tests for vision document handling"""

    async def test_upload_vision_document_integration(self, db_manager):
        """Test vision document upload with real database"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product
        product_result = await service.create_product(name="Vision Product")
        product_id = product_result["product_id"]

        # Upload vision document
        upload_result = await service.upload_vision_document(
            product_id=product_id,
            content="# Product Vision\n\nThis is our product vision statement.",
            filename="product_vision.md",
        )

        # Exception-based: success is implicit
        assert "document_id" in upload_result

        # Verify vision document created
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(VisionDocument).where(VisionDocument.product_id == product_id)
            result = await session.execute(stmt)
            vision_docs = result.scalars().all()
            assert len(vision_docs) >= 1

    async def test_upload_vision_to_nonexistent_product(self, db_manager):
        """Test vision upload fails for non-existent product"""
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Should raise ResourceNotFoundError for non-existent product
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.upload_vision_document(
                product_id=str(uuid4()), content="# Vision", filename="vision.md"
            )
        assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
class TestDatabaseTransactions:
    """Integration tests for database transaction handling"""

    async def test_create_product_transaction_commit(self, db_manager):
        """Test that create_product commits to database"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        create_result = await service.create_product(name="Transaction Test")
        product_id = create_result["product_id"]

        # Verify product exists in new session
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(Product).where(Product.id == product_id)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()
            assert product is not None
            assert product.name == "Transaction Test"

    async def test_update_product_transaction_commit(self, db_manager):
        """Test that update_product commits to database"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product
        create_result = await service.create_product(name="Original Name")
        product_id = create_result["product_id"]

        # Update product
        await service.update_product(product_id=product_id, name="Updated Name")

        # Verify update persisted in new session
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(Product).where(Product.id == product_id)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()
            assert product.name == "Updated Name"

    async def test_delete_product_transaction_commit(self, db_manager):
        """Test that delete_product commits to database"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create and delete product
        create_result = await service.create_product(name="To Delete")
        product_id = create_result["product_id"]
        await service.delete_product(product_id)

        # Verify soft delete persisted in new session
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(Product).where(Product.id == product_id)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()
            assert product is not None
            assert product.deleted_at is not None
