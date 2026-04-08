# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Integration tests for ProductService — statistics, config persistence, vision documents, and transactions.

Split from test_product_service_integration.py (Handover 0603, updated 0731b).

These tests verify:
- Product statistics and metrics
- Config data persistence through updates
- Vision document integration
- Database transaction commit behavior
"""

from uuid import uuid4

import pytest

from src.giljo_mcp.models.products import Product, VisionDocument
from src.giljo_mcp.schemas.service_responses import (
    ProductStatistics,
    VisionUploadResult,
)
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.services.product_vision_service import ProductVisionService


@pytest.mark.asyncio
class TestProductStatisticsIntegration:
    """Integration tests for product statistics and metrics"""

    async def test_get_product_statistics_with_data(self, db_manager):
        """Test statistics calculation with real data"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product (0731b: returns Product ORM model)
        product_result = await service.create_product(name="Stats Product")
        product_id = str(product_result.id)

        # Get statistics (0731b: returns ProductStatistics Pydantic model)
        stats_result = await service.get_product_statistics(product_id)
        assert isinstance(stats_result, ProductStatistics)
        assert stats_result.project_count >= 0
        assert stats_result.vision_documents_count >= 0
        assert stats_result.product_id == product_id

    async def test_get_product_with_metrics_flag(self, db_manager):
        """Test get_product returns Product ORM model regardless of metrics flag"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        product_result = await service.create_product(name="Metrics Product")
        product_id = str(product_result.id)

        # Get product (0731b: returns Product ORM model, metrics via separate call)
        get_result = await service.get_product(product_id)
        assert isinstance(get_result, Product)
        assert get_result.name == "Metrics Product"

    async def test_list_products_with_metrics(self, db_manager):
        """Test list_products returns list[Product]"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create products
        await service.create_product(name="Product A")
        await service.create_product(name="Product B")

        # List products (0731b: returns list[Product])
        list_result = await service.list_products(include_inactive=True)
        assert isinstance(list_result, list)
        assert len(list_result) == 2

        # Products are Product ORM models
        for product in list_result:
            assert isinstance(product, Product)
            assert product.id is not None
            assert product.name is not None


@pytest.mark.asyncio
class TestConfigDataPersistence:
    """Integration tests for normalized config table persistence (0840c)"""

    async def test_config_data_creates_normalized_relations(self, db_manager):
        """Test that typed config fields create normalized relations on create"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        create_result = await service.create_product(
            name="Config Test Product",
            tech_stack={
                "programming_languages": "Python 3.12",
                "backend_frameworks": "FastAPI",
            },
            architecture={
                "primary_pattern": "Layered",
                "api_style": "REST",
            },
            core_features="Agent orchestration",
        )
        product_id = str(create_result.id)

        # Verify normalized relations created
        get_result = await service.get_product(product_id)
        assert get_result.tech_stack is not None
        assert get_result.tech_stack.programming_languages == "Python 3.12"
        assert get_result.architecture is not None
        assert get_result.architecture.primary_pattern == "Layered"
        assert get_result.core_features == "Agent orchestration"

    async def test_config_data_survives_non_config_updates(self, db_manager):
        """Test that normalized config persists through unrelated updates"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        create_result = await service.create_product(
            name="Config Persist Product",
            tech_stack={"programming_languages": "Python 3.12"},
        )
        product_id = str(create_result.id)

        # Update product (without changing config)
        await service.update_product(product_id=product_id, description="Updated description")

        # Verify tech_stack preserved
        get_result = await service.get_product(product_id)
        assert get_result.tech_stack is not None
        assert get_result.tech_stack.programming_languages == "Python 3.12"

    async def test_config_data_update_modifies_relations(self, db_manager):
        """Test updating typed config fields updates normalized relations"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # Create product with initial config
        create_result = await service.create_product(
            name="Config Update Product",
            tech_stack={"programming_languages": "Python 3.11"},
        )
        product_id = str(create_result.id)

        # Update with new typed config fields
        update_result = await service.update_product(
            product_id=product_id,
            tech_stack={"programming_languages": "Python 3.12", "backend_frameworks": "FastAPI"},
        )
        assert isinstance(update_result, Product)

        # Verify config updated
        get_result = await service.get_product(product_id)
        assert get_result.tech_stack.programming_languages == "Python 3.12"
        assert get_result.tech_stack.backend_frameworks == "FastAPI"


@pytest.mark.asyncio
class TestVisionDocumentIntegration:
    """Integration tests for vision document handling"""

    async def test_upload_vision_document_integration(self, db_manager):
        """Test vision document upload with real database.

        Handover 0950i: upload_vision_document moved to ProductVisionService.
        """
        tenant_key = str(uuid4())
        product_service = ProductService(db_manager, tenant_key)
        vision_service = ProductVisionService(db_manager, tenant_key)

        # Create product (0731b: returns Product ORM model)
        product_result = await product_service.create_product(name="Vision Product")
        product_id = str(product_result.id)

        # Upload vision document (0950i: via ProductVisionService)
        upload_result = await vision_service.upload_vision_document(
            product_id=product_id,
            content="# Product Vision\n\nThis is our product vision statement.",
            filename="product_vision.md",
        )

        assert isinstance(upload_result, VisionUploadResult)
        assert upload_result.document_id is not None

        # Verify vision document created
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(VisionDocument).where(VisionDocument.product_id == product_id)
            result = await session.execute(stmt)
            vision_docs = result.scalars().all()
            assert len(vision_docs) >= 1

    async def test_upload_vision_to_nonexistent_product(self, db_manager):
        """Test vision upload fails for non-existent product.

        Handover 0950i: upload_vision_document moved to ProductVisionService.
        """
        from src.giljo_mcp.exceptions import ResourceNotFoundError

        tenant_key = str(uuid4())
        service = ProductVisionService(db_manager, tenant_key)

        # Should raise ResourceNotFoundError for non-existent product
        with pytest.raises(ResourceNotFoundError) as exc_info:
            await service.upload_vision_document(product_id=str(uuid4()), content="# Vision", filename="vision.md")
        assert "not found" in str(exc_info.value).lower()


@pytest.mark.asyncio
class TestDatabaseTransactions:
    """Integration tests for database transaction handling"""

    async def test_create_product_transaction_commit(self, db_manager):
        """Test that create_product commits to database"""
        tenant_key = str(uuid4())
        service = ProductService(db_manager, tenant_key)

        # 0731b: returns Product ORM model
        create_result = await service.create_product(name="Transaction Test")
        product_id = str(create_result.id)

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

        # Create product (0731b: returns Product ORM model)
        create_result = await service.create_product(name="Original Name")
        product_id = str(create_result.id)

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

        # Create and delete product (0731b: returns Product ORM model)
        create_result = await service.create_product(name="To Delete")
        product_id = str(create_result.id)
        await service.delete_product(product_id)

        # Verify soft delete persisted in new session
        async with db_manager.get_session_async() as session:
            from sqlalchemy import select

            stmt = select(Product).where(Product.id == product_id)
            result = await session.execute(stmt)
            product = result.scalar_one_or_none()
            assert product is not None
            assert product.deleted_at is not None
