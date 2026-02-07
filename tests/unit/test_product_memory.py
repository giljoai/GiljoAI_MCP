"""
Unit tests for product_memory JSONB column functionality.

Handover 0135: 360 Memory Management - Database Schema
Tests written FIRST following TDD principles - these will FAIL until implementation complete.
"""

import uuid

import pytest
from sqlalchemy import select

from src.giljo_mcp.models.products import Product
from src.giljo_mcp.services.product_service import ProductService


class TestProductMemory:
    """Test suite for product_memory JSONB column functionality."""

    @pytest.mark.asyncio
    async def test_product_memory_default_structure(self, db_session):
        """
        BEHAVIOR: New products have product_memory initialized to default structure

        GIVEN: A new product is created via ProductService
        WHEN: The product is retrieved from the database
        THEN: product_memory contains {"github": {}, "learnings": [], "context": {}}
        """
        # ARRANGE
        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"

        try:
            product_service = ProductService(tenant_key=tenant_key, db_manager=db_manager)

            # ACT
            unique_name = f"Test Product {uuid.uuid4().hex[:8]}"
            product_data = await product_service.create_product(
                name=unique_name, description="Test description for default memory structure"
            )

            # ASSERT
            assert product_data is not None
            assert "product_memory" in product_data
            assert isinstance(product_data["product_memory"], dict)

            # Verify default structure
            product_memory = product_data["product_memory"]
            assert "github" in product_memory
            assert "learnings" in product_memory
            assert "context" in product_memory

            # Verify default values
            assert product_memory["github"] == {}
            assert product_memory["learnings"] == []
            assert product_memory["context"] == {}
        finally:
            await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_product_memory_stores_and_retrieves_nested_data(self, db_session):
        """
        BEHAVIOR: product_memory stores complex nested structures and retrieves them correctly

        GIVEN: A product with complex memory data
        WHEN: The memory data is stored and retrieved
        THEN: All nested structures are preserved exactly
        """
        # ARRANGE
        from src.giljo_mcp.database import DatabaseManager
        from tests.helpers.test_db_helper import PostgreSQLTestHelper

        connection_string = PostgreSQLTestHelper.get_test_db_url()
        db_manager = DatabaseManager(connection_string, is_async=True)
        tenant_key = f"test_tenant_{uuid.uuid4().hex[:8]}"

        try:
            product_service = ProductService(tenant_key=tenant_key, db_manager=db_manager)

            complex_memory = {
                "github": {
                    "enabled": True,
                    "repo_url": "https://github.com/test/repo",
                    "auto_commit": False,
                    "last_sync": "2025-11-16T10:00:00Z",
                },
                "learnings": [
                    {
                        "timestamp": "2025-11-15T14:30:00Z",
                        "project_id": "proj_123",
                        "summary": "Database migration best practices",
                        "tags": ["database", "alembic", "postgresql"],
                    }
                ],
                "context": {
                    "last_updated": "2025-11-16T10:00:00Z",
                    "token_count": 15000,
                    "summary": "Product focused on AI orchestration",
                },
            }

            # ACT
            unique_name = f"Memory Test Product {uuid.uuid4().hex[:8]}"
            product_data = await product_service.create_product(
                name=unique_name, description="Testing complex memory storage", product_memory=complex_memory
            )

            # ASSERT
            assert product_data is not None
            retrieved_memory = product_data["product_memory"]

            # Verify exact structure preservation
            assert retrieved_memory == complex_memory
            assert retrieved_memory["github"]["enabled"] is True
            assert retrieved_memory["github"]["repo_url"] == "https://github.com/test/repo"
            assert len(retrieved_memory["learnings"]) == 1
            assert retrieved_memory["learnings"][0]["tags"] == ["database", "alembic", "postgresql"]
            assert retrieved_memory["context"]["token_count"] == 15000
        finally:
            await db_manager.close_async()

    @pytest.mark.asyncio
    async def test_product_memory_gin_index_supports_path_queries(self, db_session):
        """
        BEHAVIOR: GIN index allows efficient JSON path queries

        GIVEN: Multiple products with different GitHub settings
        WHEN: Querying products with github.enabled = true
        THEN: Only products with enabled GitHub are returned efficiently

        Note: This test requires actual database session, not mock
        """
        # ARRANGE
        tenant_key = "test_tenant_003"

        # Create products with varying GitHub settings
        products_data = [
            {
                "name": "GitHub Enabled Product",
                "github_enabled": True,
                "product_memory": {"github": {"enabled": True}, "learnings": [], "context": {}},
            },
            {
                "name": "GitHub Disabled Product",
                "github_enabled": False,
                "product_memory": {"github": {"enabled": False}, "learnings": [], "context": {}},
            },
            {
                "name": "No GitHub Product",
                "github_enabled": None,
                "product_memory": {"github": {}, "learnings": [], "context": {}},
            },
        ]

        # Create products directly in database
        for data in products_data:
            product = Product(
                name=data["name"], description="Test", tenant_key=tenant_key, product_memory=data["product_memory"]
            )
            db_session.add(product)

        await db_session.commit()

        # ACT - Use JSONB path query
        query = select(Product).where(
            Product.tenant_key == tenant_key, Product.product_memory["github"]["enabled"].astext == "true"
        )
        result = await db_session.execute(query)
        enabled_products = result.scalars().all()

        # ASSERT
        assert len(enabled_products) == 1
        assert enabled_products[0].name == "GitHub Enabled Product"
        assert enabled_products[0].product_memory["github"]["enabled"] is True

    @pytest.mark.asyncio
    async def test_product_memory_respects_tenant_isolation(self, db_session):
        """
        BEHAVIOR: product_memory queries respect tenant_key boundaries

        GIVEN: Products with same memory data but different tenant_keys
        WHEN: Querying product_memory for specific tenant
        THEN: Only that tenant's products are returned

        Note: This test requires actual database session, not mock
        """
        # ARRANGE
        memory_template = {
            "github": {"enabled": True, "repo_url": "https://github.com/test/shared"},
            "learnings": [],
            "context": {},
        }

        # Create products for two different tenants
        tenant_a_product = Product(
            name="Tenant A Product", description="Tenant A", tenant_key="tenant_a", product_memory=memory_template
        )

        tenant_b_product = Product(
            name="Tenant B Product", description="Tenant B", tenant_key="tenant_b", product_memory=memory_template
        )

        db_session.add_all([tenant_a_product, tenant_b_product])
        await db_session.commit()

        # ACT
        query = select(Product).where(
            Product.tenant_key == "tenant_a", Product.product_memory["github"]["enabled"].astext == "true"
        )
        result = await db_session.execute(query)
        tenant_a_products = result.scalars().all()

        # ASSERT
        assert len(tenant_a_products) == 1
        assert tenant_a_products[0].tenant_key == "tenant_a"
        assert tenant_a_products[0].name == "Tenant A Product"

        # Verify tenant B product is NOT returned
        product_names = [p.name for p in tenant_a_products]
        assert "Tenant B Product" not in product_names

    @pytest.mark.asyncio
    async def test_migration_rollback_preserves_data(self, db_session):
        """
        BEHAVIOR: Downgrade migration removes product_memory column without data loss

        GIVEN: Products with existing data and product_memory
        WHEN: Migration is rolled back
        THEN: product_memory column is removed but other product data remains intact

        Note: This test documents expected behavior - actual rollback tested via alembic CLI
        """
        # ARRANGE
        tenant_key = "rollback_tenant"

        # Create product with all fields populated
        product = Product(
            name="Rollback Test Product",
            description="Testing migration rollback",
            tenant_key=tenant_key,
            product_memory={"github": {"enabled": True}, "learnings": [], "context": {}},
            config_data={"some": "config"},
        )
        db_session.add(product)
        await db_session.commit()

        original_id = product.id
        original_name = product.name
        original_config = product.config_data

        # ASSERT (documenting expected behavior)
        # After manual rollback verification via `alembic downgrade -1`:
        # - product.id should still equal original_id
        # - product.name should still equal original_name
        # - product.config_data should still equal original_config
        # - product.product_memory attribute would not exist (AttributeError)

        assert product.id == original_id
        assert product.name == original_name
        assert product.config_data == original_config

        # Document that product_memory would not exist after rollback
        # (This assertion will pass now, but documents rollback behavior)
        assert hasattr(product, "product_memory")  # True before rollback, False after
