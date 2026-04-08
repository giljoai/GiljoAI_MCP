# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Integration tests for ProductService — CRUD workflows and project cascade behavior.

Split from test_product_service_integration.py (Handover 0603, updated 0731b).

These tests verify:
- Full CRUD workflows (create, update, activate, deactivate, delete, restore)
- Product-project cascade behavior
"""

import random
from uuid import uuid4

import pytest

from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.schemas.service_responses import (
    CascadeImpact,
    DeleteResult,
)
from src.giljo_mcp.services.product_service import ProductService


@pytest.mark.asyncio
class TestProductCRUDWorkflows:
    """Integration tests for complete CRUD workflows"""

    async def test_full_product_lifecycle(self, db_manager):
        """Test complete product lifecycle: create -> update -> activate -> deactivate -> delete -> restore"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # 1. Create product (0731b: returns Product ORM model)
        create_result = await service.create_product(
            name="Lifecycle Product",
            description="Testing full lifecycle",
            project_path="/projects/lifecycle",
            tech_stack={"programming_languages": "Python"},
        )
        assert isinstance(create_result, Product)
        product_id = str(create_result.id)

        # 2. Update product (0731b: returns Product ORM model)
        update_result = await service.update_product(
            product_id=product_id,
            description="Updated description",
            tech_stack={"programming_languages": "Python 3.12", "backend_frameworks": "FastAPI"},
        )
        assert update_result.description == "Updated description"

        # 3. Activate product (0731b: returns Product ORM model)
        activate_result = await service.activate_product(product_id)
        assert activate_result.is_active is True

        # 4. Deactivate product
        deactivate_result = await service.deactivate_product(product_id)
        assert deactivate_result.is_active is False

        # 5. Soft delete product (0731b: returns DeleteResult Pydantic model)
        delete_result = await service.delete_product(product_id)
        assert isinstance(delete_result, DeleteResult)
        assert delete_result.deleted is True
        assert delete_result.deleted_at is not None

        # Verify not in regular list (even with include_inactive) (0731b: returns list[Product])
        list_result = await service.list_products(include_inactive=True)
        assert len(list_result) == 0

        # Verify in deleted list (0731b: returns list[Product])
        deleted_list = await service.list_deleted_products()
        assert len(deleted_list) >= 1
        assert any(str(p.id) == product_id for p in deleted_list)

        # 6. Restore product (0731b: returns Product ORM model)
        restore_result = await service.restore_product(product_id)
        assert isinstance(restore_result, Product)

        # Verify back in regular list (0731b: returns list[Product])
        list_result = await service.list_products(include_inactive=True)
        assert len(list_result) == 1
        assert list_result[0].name == "Lifecycle Product"

    async def test_create_multiple_products_and_list(self, db_manager):
        """Test creating multiple products and listing them"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create five products (0731b: returns Product ORM model)
        products = []
        for i in range(5):
            result = await service.create_product(name=f"Product {i + 1}", description=f"Description {i + 1}")
            assert isinstance(result, Product)
            products.append(str(result.id))

        # List all products (0731b: returns list[Product])
        list_result = await service.list_products(include_inactive=True)
        assert isinstance(list_result, list)
        assert len(list_result) == 5

        # Verify all names present
        names = [p.name for p in list_result]
        for i in range(5):
            assert f"Product {i + 1}" in names

    async def test_duplicate_name_prevention(self, db_manager):
        """Test that duplicate product names are prevented"""
        from src.giljo_mcp.exceptions import ValidationError

        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create first product (0731b: returns Product ORM model)
        create1 = await service.create_product(name="Unique Product")
        assert isinstance(create1, Product)

        # Try to create second with same name - should raise ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await service.create_product(name="Unique Product")
        assert "already exists" in str(exc_info.value)

        # Verify only one product exists (0731b: returns list[Product])
        list_result = await service.list_products(include_inactive=True)
        assert len(list_result) == 1

    async def test_soft_delete_allows_name_reuse(self, db_manager):
        """Test that soft-deleted products allow name reuse"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product (0731b: returns Product ORM model)
        create1 = await service.create_product(name="Reusable Name")
        assert isinstance(create1, Product)
        product1_id = str(create1.id)

        # Soft delete
        await service.delete_product(product1_id)

        # Create new product with same name - should succeed
        create2 = await service.create_product(name="Reusable Name")
        assert isinstance(create2, Product)
        assert str(create2.id) != product1_id


@pytest.mark.asyncio
class TestProductProjectCascade:
    """Integration tests for product-project relationships"""

    async def test_product_with_projects_cascade_impact(self, db_manager):
        """Test getting cascade impact shows related projects"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product (0731b: returns Product ORM model)
        product_result = await service.create_product(name="Product with Projects")
        product_id = str(product_result.id)

        # Create related projects (unique series_number to satisfy uq_project_taxonomy)
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
                    series_number=i + 1,
                )
                session.add(project)
            await session.commit()

        # Get cascade impact (0731b: returns CascadeImpact Pydantic model)
        impact_result = await service.get_cascade_impact(product_id)
        assert isinstance(impact_result, CascadeImpact)
        assert impact_result.total_projects == 3

    async def test_delete_product_with_projects(self, db_manager):
        """Test deleting product with related projects"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product (0731b: returns Product ORM model)
        product_result = await service.create_product(name="Product to Delete")
        product_id = str(product_result.id)

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
                series_number=random.randint(1, 999999),
            )
            session.add(project)
            await session.commit()

        # Delete product (0731b: returns DeleteResult Pydantic model)
        delete_result = await service.delete_product(product_id)
        assert isinstance(delete_result, DeleteResult)
        assert delete_result.deleted is True
        assert delete_result.deleted_at is not None

        # Verify product is soft-deleted (should raise ResourceNotFoundError)
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        with pytest.raises(ResourceNotFoundError):
            await service.get_product(product_id)

        # Note: Actual cascade behavior depends on database constraints
        # This test verifies the delete succeeds
